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
LISTEN_HOST = '127.0.0.1'
LISTEN_PORT = 9222
START_PORT_RANGE = 9300
CHROME_START_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'start_chrome_for_antigravity.sh')
REGISTRY_FILE = "/tmp/ag_chrome_registry.json"

# Global lock for registry operations
registry_lock = threading.Lock()

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

class ChromeRegistry:
    def __init__(self):
        self.projects = {} # { "project_name": { "port": 9300, "pid": 123 } }
        self.load()

    def load(self):
        if os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE, 'r') as f:
                    self.projects = json.load(f)
            except Exception:
                self.projects = {}

    def save(self):
        try:
            with open(REGISTRY_FILE, 'w') as f:
                json.dump(self.projects, f, indent=2)
        except Exception as e:
            log(f"Error saving registry: {e}")

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
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except Exception:
            return False


def determine_project_name(client_port):
    """Attempts to find the project name based on the client process."""
    try:
        cmd = f"ss -H -t -p src 127.0.0.1 sport = {client_port}"
        result = subprocess.check_output(cmd, shell=True).decode('utf-8')
        match = re.search(r'pid=(\d+)', result)
        if match:
            pid = match.group(1)
            # Method 1: CMDLINE parsing
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmdline_bytes = f.read()
                    cmdline = cmdline_bytes.replace(b'\x00', b' ').decode('utf-8', errors='ignore')
                    ws_match = re.search(r'--workspace_id\s+([^\s]+)', cmdline)
                    if ws_match:
                        raw_id = ws_match.group(1)
                        clean_name = raw_id.replace('file_', '')
                        user_prefix = f"home_{os.environ.get('USER', 'creator')}_"
                        if clean_name.startswith(user_prefix):
                            clean_name = clean_name[len(user_prefix):]
                        if clean_name: return clean_name
            except Exception:
                pass

    except Exception:
        pass
    return "default_project"


# Global variable to store the last successfully identified project
# This helps when auxiliary processes (like Playwright/Node) connect without clear project info.
# We assume they belong to the most closely related active project.
last_detected_project = None
project_lock = threading.Lock() # Protects access to last_detected_project

def ensure_chrome_for_project(project_name):
    """Ensures a Chrome instance is running for the given project."""
    with registry_lock:
        registry = ChromeRegistry()
        project = registry.get_project(project_name)

        # Check if existing instance is alive
        if project:
            if ChromeRegistry.is_port_open('127.0.0.1', project['port']):
                return project['port']
            log(f"Project '{project_name}' port {project['port']} closed. Restarting...")

        # Need to start a new instance
        port = registry.find_free_port()
        user_data_dir = os.path.expanduser(f"~/.gemini/profiles/{project_name}")
        
        log(f"Launching Chrome for '{project_name}' on port {port}...")
        
        env = os.environ.copy()
        env['CHROME_PORT'] = str(port)
        env['CHROME_USER_DATA_DIR'] = user_data_dir
        
        try:
            proc = subprocess.Popen(
                ['bash', CHROME_START_SCRIPT],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setpgrp
            )
            
            # Wait for port to be ready
            start_time = time.time()
            while time.time() - start_time < 15:
                if ChromeRegistry.is_port_open('127.0.0.1', port):
                    log(f"Chrome started for '{project_name}' on port {port}.")
                    try:
                        cmd = f"fuser -n tcp {port} 2>/dev/null"
                        pid = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
                        if pid:
                            registry.register_project(project_name, port, pid)
                    except Exception:
                        registry.register_project(project_name, port, 0)
                    return port
                time.sleep(0.5)
        except Exception as e:
            log(f"Failed to launch Chrome: {e}")
            
    return None

def handle_client(client_socket):
    global last_detected_project
    try:
        _, client_port = client_socket.getpeername()
        project_name = determine_project_name(client_port)
        
        # Heuristic: If we couldn't determine project (e.g. generic Node process),
        # use the last known project.
        with project_lock:
            if project_name == "default_project":
                if last_detected_project:
                    project_name = last_detected_project
                    # log(f"Using fallback project '{project_name}' for generic client")
            else:
                last_detected_project = project_name
        
        log(f"Client from '{project_name}' connected.")

        target_port = ensure_chrome_for_project(project_name)

        if not target_port:
            client_socket.close()
            return

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect(('127.0.0.1', target_port))

        def forward(source, destination):
            try:
                while True:
                    data = source.recv(4096)
                    if not data: break
                    destination.send(data)
            except Exception:
                pass
            finally:
                source.close()
                destination.close()

        threading.Thread(target=forward, args=(client_socket, server_socket), daemon=True).start()
        threading.Thread(target=forward, args=(server_socket, client_socket), daemon=True).start()

    except Exception as e:
        log(f"Handler error: {e}")
        client_socket.close()


def maintain_window_titles():
    """Background thread to keep window titles correct."""
    # Ensure DISPLAY is set for xdotool
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":0"
        
    while True:
        try:
            # Create a snapshot of projects to iterate safely
            with registry_lock:
                registry = ChromeRegistry()
                current_projects = list(registry.projects.items()) # [("name", {"pid":...}), ...]
            
            for name, info in current_projects:
                pid = info.get("pid")
                if not pid or pid == 0: continue
                
                try:
                    # Search for windows by PID
                    # Using check_output to get WIDs
                    wids_out = subprocess.check_output(
                        ["xdotool", "search", "--pid", str(pid)], 
                        stderr=subprocess.DEVNULL
                    ).decode('utf-8').strip()
                    
                    if wids_out:
                        for wid in wids_out.split():
                            # Check current title
                            curr_title = subprocess.check_output(
                                ["xdotool", "getwindowname", wid],
                                stderr=subprocess.DEVNULL
                            ).decode('utf-8').strip()
                            
                            if curr_title and curr_title != name:
                                # Set new title
                                subprocess.run(
                                    ["xdotool", "set_window", "--name", name, wid],
                                    stderr=subprocess.DEVNULL
                                )
                                # log(f"Updated title for {name} (PID {pid}, WID {wid})")
                except subprocess.CalledProcessError:
                    # PID might not have windows yet or xdotool failed
                    pass
                except Exception as e:
                    # log(f"Error updating title for {name}: {e}")
                    pass
                    
        except Exception as e:
            log(f"Title maintainer crashed (restarting loop): {e}")
        
        time.sleep(2.0)

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((LISTEN_HOST, LISTEN_PORT))
    except Exception as e:
        log(f"Failed to bind: {e}")
        sys.exit(1)
        
    server.listen(5)
    log(f"Smart Router listening on {LISTEN_PORT}...")

    # Start Window Title Maintainer
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
