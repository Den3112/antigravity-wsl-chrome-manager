#!/usr/bin/env python3
import socket
import threading
import time
import subprocess
import os
import signal
import sys
import re
import json

# Configuration
LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 9221
START_PORT_RANGE = 9300
CHROME_START_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'start_chrome_for_antigravity.sh')
REGISTRY_FILE = "/tmp/ag_chrome_registry.json"

def log(msg):
    # If we are in 'ensure' or 'check' mode (CLI), write logs to stderr to keep stdout clean for the port number
    if len(sys.argv) > 1 and sys.argv[1] in ["ensure", "check"]:
        sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")

class ChromeRegistry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ChromeRegistry, cls).__new__(cls)
                cls._instance.projects = {}
                cls._instance.load()
            return cls._instance

    def load(self):
        if os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE, 'r') as f:
                    self.projects = json.load(f)
            except Exception:
                self.projects = {}

    def save(self):
        try:
            temp_file = REGISTRY_FILE + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.projects, f, indent=2)
            os.replace(temp_file, REGISTRY_FILE)
        except Exception as e:
            log(f"Error saving registry: {e}")

    def cleanup_stale_projects(self):
        """Removes projects that are no longer running."""
        changed = False
        to_delete = []
        for name, info in self.projects.items():
            port = info.get("port")
            if not self.is_port_open('127.0.0.1', port):
                to_delete.append(name)
        
        for name in to_delete:
            log(f"Cleaning up stale project: {name}")
            del self.projects[name]
            changed = True
        
        if changed:
            self.save()

    def get_project(self, name):
        return self.projects.get(name)

    def register_project(self, name, port, pid):
        self.projects[name] = {"port": port, "pid": pid}
        self.save()

    def find_free_port(self):
        used_ports = {p['port'] for p in self.projects.values()}
        port = START_PORT_RANGE
        while port in used_ports or self.is_port_open('127.0.0.1', port):
            port += 1
        return port

    @staticmethod
    def is_port_open(host, port):
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except Exception:
            return False

# Global lock for managing the launch locks dictionary safely
_global_launch_lock = threading.Lock()
_launch_locks = {}

def ensure_chrome_for_project(project_name):
    """Ensures a Chrome instance is running for the given project."""
    registry = ChromeRegistry()
    
    # First check WITHOUT global lock (fast path)
    project = registry.get_project(project_name)
    if project:
        if ChromeRegistry.is_port_open('127.0.0.1', project['port']):
            return project['port']

    # Use a specific lock for THIS project to prevent parallel launches
    with _global_launch_lock:
        if project_name not in _launch_locks:
            _launch_locks[project_name] = threading.Lock()
        lock = _launch_locks[project_name]
        
    with lock:
        # Double-check after acquiring lock
        registry.load() # Refresh registry
        registry.cleanup_stale_projects()
        project = registry.get_project(project_name)
        if project and ChromeRegistry.is_port_open('127.0.0.1', project['port']):
            return project['port']

        port = registry.find_free_port()
        user_data_dir = os.path.expanduser(f"~/.gemini/profiles/{project_name}")
        
        log(f"Launching Chrome for '{project_name}' on port {port}...")
        
        env = os.environ.copy()
        env['CHROME_PORT'] = str(port)
        env['CHROME_USER_DATA_DIR'] = user_data_dir
        
        try:
            # We use shell=False and pass arguments as list for safety
            proc = subprocess.Popen(
                ['bash', CHROME_START_SCRIPT],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Wait for port to become ready
            start_time = time.time()
            while time.time() - start_time < 40: # 40 seconds total timeout
                if ChromeRegistry.is_port_open('127.0.0.1', port):
                    log(f"Chrome started for '{project_name}' on port {port} (Bridge Active).")
                    # Try to find real chrome pid for registry
                    try:
                        # Improved PID discovery: look for the chrome process specifically on this internal port
                        # Internal port is PORT + 10000 per start script
                        internal_port = port + 10000
                        cmd = ["pgrep", "-f", f"remote-debugging-port={internal_port}"]
                        pid_bytes = subprocess.check_output(cmd)
                        pids = pid_bytes.decode().split()
                        pid = int(pids[0]) if pids else 0
                        registry.register_project(project_name, port, pid)
                    except Exception:
                        registry.register_project(project_name, port, 0)
                    return port
                time.sleep(0.5)
            log(f"Timeout waiting for port {port} to open.")
        except Exception as e:
            log(f"Failed to launch Chrome: {e}")
            
    return None

def forward(source, destination):
    try:
        while True:
            data = source.recv(16384)
            if not data: break
            destination.sendall(data)
    except Exception:
        pass
    finally:
        source.close()
        destination.close()

def handle_client(client_socket):
    try:
        # For legacy compatibility, default to "default_project" if can't determine
        # But for Windows Bridge, we now use CLI 'ensure' which handles everything.
        project_name = "default_project"
        
        target_port = ensure_chrome_for_project(project_name)
        if not target_port:
            client_socket.close()
            return

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect(('127.0.0.1', target_port))

        threading.Thread(target=forward, args=(client_socket, server_socket), daemon=True).start()
        threading.Thread(target=forward, args=(server_socket, client_socket), daemon=True).start()

    except Exception as e:
        log(f"Handler error: {e}")
        client_socket.close()

def maintain_window_titles():
    """Background thread to keep window titles correct."""
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":0"
        
    registry = ChromeRegistry()
    while True:
        try:
            with registry._lock:
                current_projects = list(registry.projects.items())
            
            for name, info in current_projects:
                pid = info.get("pid")
                if not pid or pid == 0: continue
                
                try:
                    wids_out = subprocess.check_output(
                        ["xdotool", "search", "--pid", str(pid)], 
                        stderr=subprocess.DEVNULL
                    ).decode('utf-8').strip()
                    
                    if wids_out:
                        for wid in wids_out.split():
                            curr_title = subprocess.check_output(
                                ["xdotool", "getwindowname", wid],
                                stderr=subprocess.DEVNULL
                            ).decode('utf-8').strip()
                            
                            if curr_title and curr_title != name:
                                subprocess.run(["xdotool", "set_window", "--name", name, wid], stderr=subprocess.DEVNULL)
                except Exception:
                    pass
        except Exception as e:
            log(f"Title maintainer error: {e}")
        
        time.sleep(5.0) # Less frequent updates to save CPU

def main():
    if len(sys.argv) > 2:
        cmd = sys.argv[1]
        project_name = sys.argv[2]
        
        if cmd == "ensure":
            port = ensure_chrome_for_project(project_name)
            if port:
                print(port)
                sys.exit(0)
            else:
                sys.exit(1)
        elif cmd == "check":
            registry = ChromeRegistry()
            project = registry.get_project(project_name)
            if project and ChromeRegistry.is_port_open('127.0.0.1', project['port']):
                print(project['port'])
                sys.exit(0)
            else:
                print(0)
                sys.exit(0)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((LISTEN_HOST, LISTEN_PORT))
    except Exception as e:
        log(f"Failed to bind: {e}")
        sys.exit(1)
        
    server.listen(10)
    log(f"Smart Router listening on {LISTEN_PORT}...")

    threading.Thread(target=maintain_window_titles, daemon=True).start()

    try:
        while True:
            client_sock, addr = server.accept()
            threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()
    except KeyboardInterrupt:
        log("Stopping...")
    finally:
        server.close()

if __name__ == "__main__":
    main()
