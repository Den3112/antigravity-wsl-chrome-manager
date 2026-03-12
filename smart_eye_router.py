#!/usr/bin/env python3
import socket
import threading
import sys
import time
import json
import os
import subprocess
import urllib.request

# Configuration
LISTEN_PORT = 9222
WINDOWS_CHROME_PORT = 9223
STATE_FILE = "/mnt/c/Users/Creator/.gemini/antigravity/active_project.json"
LOG_FILE = "/home/creator/smart_router_debug.log"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def get_active_project():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                project_path = data.get('path', '').lower()
                is_wsl = any(x in project_path for x in ['wsl', 'ubuntu', '/home/creator', 'ubuntu-24.04'])
                project_name = os.path.basename(project_path.rstrip('/\\')) or 'default_project'
                return {"is_wsl": is_wsl, "path": project_path, "name": project_name}
        except Exception as e:
            log(f"Error reading state file: {e}")
    return {"is_wsl": False, "path": "", "name": "default_project"}

def resolve_project_name(project):
    """Determines the active project name from state or current directory."""
    name = project['name']
    if name == "antigravity-wsl-chrome-manager" or not name:
        name = os.path.basename(os.getcwd())
    return name

def handle_http_discovery(client_socket, request_text, project, project_name):
    """Handles /json auxiliary requests for CDP discovery."""
    log(f"JSON REQUEST: {project_name} (WSL={project['is_wsl']})")
    
    # Resolve WSL Port
    wsl_port = 0
    try:
        cmd = ["python3", "/home/creator/antigravity-wsl-chrome-manager/smart_chrome_proxy.py", "ensure", project_name]
        port_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
        wsl_port = int(port_out) if port_out.isdigit() else 0
    except Exception as e:
        log(f"WSL Ensure Error: {e}")

    endpoint = request_text.split('\n')[0].split(' ')[1] if '\n' in request_text else "/json/list"
    targets = []
    
    if wsl_port > 0:
        try:
            url = f"http://127.0.0.1:{wsl_port}{endpoint}"
            with urllib.request.urlopen(url, timeout=2) as r:
                resp = json.loads(r.read().decode())
                # Rewrite URLs to point back to our router port
                if isinstance(resp, list):
                    for t in resp:
                        if 'webSocketDebuggerUrl' in t:
                            t['webSocketDebuggerUrl'] = t['webSocketDebuggerUrl'].replace(f"127.0.0.1:{wsl_port}", f"127.0.0.1:{LISTEN_PORT}")
                    targets = resp
                elif isinstance(resp, dict):
                    if 'webSocketDebuggerUrl' in resp:
                        resp['webSocketDebuggerUrl'] = resp['webSocketDebuggerUrl'].replace(f"127.0.0.1:{wsl_port}", f"127.0.0.1:{LISTEN_PORT}")
                    targets = resp
        except Exception as e:
            log(f"Proxy Error: {e}")

    if "/json/version" in endpoint and not targets:
        targets = {
            "Browser": "Chrome/WSL-Proxy",
            "Protocol-Version": "1.3",
            "webSocketDebuggerUrl": f"ws://127.0.0.1:{LISTEN_PORT}/devtools/browser/proxy"
        }

    body = json.dumps(targets).encode()
    response = (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Connection: close\r\n\r\n"
    ).encode('utf-8') + body
    client_socket.sendall(response)
    client_socket.close()

def start_tunnel(s1, s2):
    """Pipes data between two sockets with robust error handling."""
    def pipe(source, destination):
        try:
            while True:
                chunk = source.recv(32768)
                if not chunk: break
                destination.sendall(chunk)
        except: pass
        finally:
            try: source.close()
            except: pass
            try: destination.close()
            except: pass

    threading.Thread(target=pipe, args=(s1, s2), daemon=True).start()
    threading.Thread(target=pipe, args=(s2, s1), daemon=True).start()

def handle_tunneling(client_socket, initial_data, project, project_name):
    """Establishes a transparent tunnel to the target Chrome instance."""
    target_host = '127.0.0.1'
    # Use internal port 19223 directly to bypass unstable intermediate socat bridge
    is_wsl_mode = project['is_wsl'] or project_name == "slovor-mp"
    target_port = 19223 if is_wsl_mode else WINDOWS_CHROME_PORT

    if not is_wsl_mode:
        try:
            target_host = subprocess.check_output("ip route | grep default | awk '{print $3}'", shell=True).decode().strip()
        except:
            target_host = '127.0.0.1'
    
    log(f"Tunneling -> {target_host}:{target_port}")

    try:
        tsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tsock.settimeout(3.0)
        tsock.connect((target_host, target_port))
        tsock.settimeout(None)
        client_socket.settimeout(None)
        
        tsock.sendall(initial_data)
        start_tunnel(client_socket, tsock)
    except Exception as e:
        log(f"Tunnel Error: {e}")
        client_socket.close()

def handle_client(client_socket):
    """Main client handler: dispatches between HTTP discovery and WebSocket tunneling."""
    try:
        client_socket.settimeout(2.0)
        data = client_socket.recv(16384)
        if not data:
            client_socket.close()
            return

        request_text = data.decode('utf-8', errors='ignore')
        project = get_active_project()
        project_name = resolve_project_name(project)

        if "GET /json" in request_text:
            handle_http_discovery(client_socket, request_text, project, project_name)
        else:
            handle_tunneling(client_socket, data, project, project_name)

    except Exception as e:
        log(f"Global Handler Error: {e}")
        try: client_socket.close()
        except: pass

def main():
    if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
    log("Starting WSL Smart Router on port 9222...")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', LISTEN_PORT))
    except Exception as e:
        log(f"FATAL: Could not bind to {LISTEN_PORT}: {e}")
        return

    server.listen(50)
    while True:
        try:
            client, addr = server.accept()
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()
        except KeyboardInterrupt: break
        except Exception as e: log(f"Accept Error: {e}")


if __name__ == "__main__":
    main()
