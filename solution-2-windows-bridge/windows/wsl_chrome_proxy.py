#!/usr/bin/env python3
"""
WSL-Chrome-Bridge: Windows Proxy
================================
A robust TCP proxy that forwards connections from WSL to Chrome's CDP port.

Usage:
    python wsl_chrome_proxy.py [--verbose]

Listens on: 0.0.0.0:9223
Forwards to: 127.0.0.1:9222
"""

import socket
import threading
import sys
import os
import signal
import argparse

# Configuration
# Configuration (can be overridden by environment variables)
LISTEN_HOST = os.environ.get('PROXY_LISTEN_HOST', '0.0.0.0')
LISTEN_PORT = int(os.environ.get('PROXY_LISTEN_PORT', 9223))
TARGET_HOST = os.environ.get('PROXY_TARGET_HOST', '127.0.0.1')
TARGET_PORT = int(os.environ.get('PROXY_TARGET_PORT', 9222))
BUFFER_SIZE = 65536

VERBOSE = False

def log(message):
    """Print message if verbose mode is enabled."""
    if VERBOSE:
        print(f"[WSL-Bridge] {message}")


def pipe(source, dest, direction=""):
    """Bidirectional data transfer between sockets."""
    try:
        source.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        dest.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        while True:
            data = source.recv(BUFFER_SIZE)
            if not data:
                log(f"{direction} connection closed")
                break
            dest.sendall(data)
    except OSError as e:
        log(f"{direction} socket error: {e}")
    except Exception as e:
        log(f"{direction} error: {e}")
    finally:
        try:
            source.close()
        except Exception:
            pass
        try:
            dest.close()
        except Exception:
            pass


def handle_client(client_socket, client_addr):
    """Handle a single client connection."""
    log(f"New connection from {client_addr}")
    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        remote.settimeout(5)  # Connection timeout
        remote.connect((TARGET_HOST, TARGET_PORT))
        remote.settimeout(None)  # Reset for normal operation
        
        t1 = threading.Thread(target=pipe, args=(client_socket, remote, "Client->Chrome"))
        t2 = threading.Thread(target=pipe, args=(remote, client_socket, "Chrome->Client"))
        t1.daemon = True
        t2.daemon = True
        t1.start()
        t2.start()
        
        # Wait for both threads to complete
        t1.join()
        t2.join()
    except socket.timeout:
        log("Connection to Chrome timed out")
        client_socket.close()
    except ConnectionRefusedError:
        log(f"Chrome not available on {TARGET_HOST}:{TARGET_PORT}")
        client_socket.close()
    except Exception as e:
        log(f"Client handler error: {e}")
        client_socket.close()


def signal_handler(_sig, _frame):
    """Handle Ctrl+C gracefully."""
    print("\n[WSL-Bridge] Shutting down...")
    sys.exit(0)


def main():
    global VERBOSE
    
    parser = argparse.ArgumentParser(description='WSL-Chrome-Bridge Proxy')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    VERBOSE = args.verbose
    
    signal.signal(signal.SIGINT, signal_handler)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((LISTEN_HOST, LISTEN_PORT))
        server.listen(10)
        print(f"[WSL-Bridge] Proxy listening on {LISTEN_HOST}:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}")
        print(f"[WSL-Bridge] Verbose mode: {'ON' if VERBOSE else 'OFF'}")
        
        while True:
            client, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client, addr))
            t.daemon = True
            t.start()
    except OSError as e:
        if e.errno == 10048 or e.errno == 98:  # Address already in use
            print(f"[WSL-Bridge] Error: Port {LISTEN_PORT} is already in use")
        else:
            print(f"[WSL-Bridge] Server error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[WSL-Bridge] Server error: {e}")
        sys.exit(1)
    finally:
        server.close()

if __name__ == '__main__':
    main()
