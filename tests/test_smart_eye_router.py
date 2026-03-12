import pytest
import os
import json
import socket
import threading
import time
from unittest.mock import patch, mock_open, MagicMock
import sys
import subprocess
import urllib.request
import runpy

# Add the parent directory to sys.path to import the script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import smart_eye_router
from smart_eye_router import (
    get_active_project, 
    resolve_project_name, 
    handle_http_discovery, 
    STATE_FILE, 
    LOG_FILE
)

@pytest.fixture(autouse=True)
def cleanup_log():
    if os.path.exists(LOG_FILE):
        try: os.remove(LOG_FILE)
        except: pass
    yield
    if os.path.exists(LOG_FILE):
        try: os.remove(LOG_FILE)
        except: pass

def test_get_active_project_no_file():
    with patch("os.path.exists", return_value=False):
        res = get_active_project()
        assert res["is_wsl"] is False
        assert res["name"] == "default_project"

def test_get_active_project_wsl():
    mock_data = json.dumps({"path": "/home/creator/projects/my-proj"})
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=mock_data)):
            res = get_active_project()
            assert res["is_wsl"] is True
            assert res["name"] == "my-proj"

def test_get_active_project_windows():
    mock_data = json.dumps({"path": "C:/Users/User/projects/win-proj"})
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=mock_data)):
            res = get_active_project()
            assert res["is_wsl"] is False
            assert res["name"] == "win-proj"

def test_get_active_project_failure():
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", side_effect=[IOError("Read error"), MagicMock()]):
            res = get_active_project()
            assert res["name"] == "default_project"

def test_resolve_project_name():
    assert resolve_project_name({"name": "proj1"}) == "proj1"
    with patch("os.getcwd", return_value="/home/creator/actual_dir"):
        res = resolve_project_name({"name": "antigravity-wsl-chrome-manager"})
        assert res == "actual_dir"
        res = resolve_project_name({"name": ""})
        assert res == "actual_dir"

def test_handle_http_discovery_success():
    client = MagicMock()
    project = {"is_wsl": True, "name": "p"}
    
    with patch("subprocess.check_output", return_value=b"9300\n"):
        mock_resp_obj = MagicMock()
        mock_resp_obj.read.return_value = json.dumps([
            {"webSocketDebuggerUrl": "ws://127.0.0.1:9300/devtools/page/1"}
        ]).encode()
        mock_resp_obj.__enter__.return_value = mock_resp_obj
        
        with patch("urllib.request.urlopen", return_value=mock_resp_obj):
            handle_http_discovery(client, "GET /json/list HTTP/1.1", project, "p")
            args, kwargs = client.sendall.call_args
            sent_data = args[0].decode()
            assert "ws://127.0.0.1:9222/devtools/page/1" in sent_data
            client.close.assert_called_once()

def test_handle_http_discovery_dict():
    client = MagicMock()
    project = {"is_wsl": True, "name": "p"}
    with patch("subprocess.check_output", return_value=b"9300\n"):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "webSocketDebuggerUrl": "ws://127.0.0.1:9300/devtools/browser/abc"
        }).encode()
        mock_resp.__enter__.return_value = mock_resp
        with patch("urllib.request.urlopen", return_value=mock_resp):
            handle_http_discovery(client, "GET /json/version", project, "p")
            args, kwargs = client.sendall.call_args
            sent_data = args[0].decode()
            assert "ws://127.0.0.1:9222/devtools/browser/abc" in sent_data

def test_handle_http_discovery_error():
    client = MagicMock()
    project = {"is_wsl": True, "name": "p"}
    with patch("subprocess.check_output", side_effect=Exception("Ensure failed")):
        # Normal version request
        handle_http_discovery(client, "GET /json/version\n", project, "p")
        # targets becomes default Browser dict.
        # sendall is called.
        client.sendall.assert_called()

def test_handle_http_discovery_list_error():
    client = MagicMock()
    project = {"is_wsl": True, "name": "p"}
    # line 73-74: wsl_port = 0 if subprocess raises exception
    with patch("subprocess.check_output", side_effect=Exception("bad")):
        handle_http_discovery(client, "GET /json/list\n", project, "p")
        args, kwargs = client.sendall.call_args
        sent = args[0].decode()
        assert "[]" in sent # no fallback targets for list if fail

def test_handle_http_discovery_proxy_error():
    # cover line 87: log(f"Proxy Error: {e}")
    client = MagicMock()
    project = {"is_wsl": True, "name": "p"}
    with patch("subprocess.check_output", return_value=b"9300\n"):
        with patch("urllib.request.urlopen", side_effect=Exception("urllib fail")):
            handle_http_discovery(client, "GET /json/list\n", project, "p")
            # Loop continues, targets is []
            client.sendall.assert_called()

def test_handle_http_discovery_no_port():
    client = MagicMock()
    project = {"is_wsl": True, "name": "p"}
    # Cover line 73-74: wsl_port = 0
    with patch("subprocess.check_output", return_value=b"0\n"):
        handle_http_discovery(client, "GET /json/list HTTP/1.1", project, "p")
        args, kwargs = client.sendall.call_args
        sent_data = args[0].decode()
        assert "Content-Length: 2" in sent_data # []

def test_start_tunnel():
    s1 = MagicMock()
    s2 = MagicMock()
    s1.recv.side_effect = [b"msg1", b""]
    s2.recv.side_effect = [b"msg2", b""]
    with patch("threading.Thread") as mock_thread:
        smart_eye_router.start_tunnel(s1, s2)
        target_func = mock_thread.call_args_list[0][1]['target']
        target_func(s1, s2)
        s2.sendall.assert_called_with(b"msg1")
        s1.recv.side_effect = Exception("error")
        target_func(s1, s2)

def test_handle_tunneling_wsl():
    client = MagicMock()
    project = {"is_wsl": True, "name": "p"}
    with patch("socket.socket") as mock_sock_class:
        mock_tsock = mock_sock_class.return_value
        with patch("smart_eye_router.start_tunnel") as mock_start:
            smart_eye_router.handle_tunneling(client, b"init", project, "p")
            mock_tsock.connect.assert_called_with(('127.0.0.1', 19223))
            mock_tsock.sendall.assert_called_with(b"init")
            mock_start.assert_called_once()

def test_handle_tunneling_windows():
    client = MagicMock()
    project = {"is_wsl": False, "name": "p"}
    with patch("subprocess.check_output", return_value=b"10.0.0.1\n"):
        with patch("socket.socket") as mock_sock_class:
            mock_tsock = mock_sock_class.return_value
            with patch("smart_eye_router.start_tunnel") as mock_start:
                smart_eye_router.handle_tunneling(client, b"init", project, "p")
                mock_tsock.connect.assert_called_with(('10.0.0.1', 9223))
                mock_start.assert_called_once()

def test_handle_tunneling_windows_error():
    client = MagicMock()
    project = {"is_wsl": False, "name": "p"}
    with patch("subprocess.check_output", side_effect=Exception("ip route failed")):
        with patch("socket.socket") as mock_sock_class:
            mock_tsock = mock_sock_class.return_value
            with patch("smart_eye_router.start_tunnel") as mock_start:
                smart_eye_router.handle_tunneling(client, b"init", project, "p")
                mock_tsock.connect.assert_called_with(('127.0.0.1', 9223))

def test_handle_tunneling_error():
    client = MagicMock()
    project = {"is_wsl": True, "name": "p"}
    with patch("socket.socket", side_effect=Exception("Conn failed")):
        smart_eye_router.handle_tunneling(client, b"init", project, "p")
        client.close.assert_called_once()

def test_handle_client_http():
    client = MagicMock()
    client.recv.return_value = b"GET /json/list HTTP/1.1\r\nHost: localhost\r\n\r\n"
    with patch("smart_eye_router.get_active_project", return_value={"name": "p", "is_wsl": True}):
        with patch("smart_eye_router.handle_http_discovery") as mock_disc:
            smart_eye_router.handle_client(client)
            mock_disc.assert_called_once()

def test_handle_client_tunnel():
    client = MagicMock()
    client.recv.return_value = b"\x01\x02\x03"
    with patch("smart_eye_router.get_active_project", return_value={"name": "p", "is_wsl": True}):
        with patch("smart_eye_router.handle_tunneling") as mock_tunnel:
            smart_eye_router.handle_client(client)
            mock_tunnel.assert_called_once()

def test_handle_client_empty():
    client = MagicMock()
    client.recv.return_value = b""
    smart_eye_router.handle_client(client)
    client.close.assert_called_once()

def test_handle_client_exception():
    client = MagicMock()
    client.recv.side_effect = Exception("error")
    smart_eye_router.handle_client(client)
    client.close.assert_called_once()

def test_main():
    with patch("socket.socket") as mock_sock_class:
        mock_srv = mock_sock_class.return_value
        mock_srv.accept.side_effect = [ (MagicMock(), ('127.0.0.1', 1234)), KeyboardInterrupt ]
        with patch("threading.Thread"):
            with patch("os.path.exists", return_value=True):
                with patch("os.remove"):
                    smart_eye_router.main()
                    mock_srv.bind.assert_called_with(('0.0.0.0', 9222))

def test_main_bind_fail():
    with patch("socket.socket") as mock_sock_class:
        mock_srv = mock_sock_class.return_value
        mock_srv.bind.side_effect = Exception("Bind Fail")
        smart_eye_router.main()

def test_if_name_main():
    with patch("sys.argv", ["prog"]):
        with patch("socket.socket") as mock_sock:
            mock_sock.return_value.accept.side_effect = KeyboardInterrupt
            # Need to cover main() line 181 Accept Error
            # We skip it by mocking accept to raise Exception once then KeyboardInterrupt
            mock_sock.return_value.accept.side_effect = [Exception("Accept Error"), KeyboardInterrupt]
            with patch("os.path.exists", return_value=False):
                try:
                    runpy.run_path("smart_eye_router.py", run_name="__main__")
                except (KeyboardInterrupt, SystemExit):
                    pass

def test_handle_tunneling_connect_error():
    # cover line 137: log(f"Tunnel Error: {e}")
    client = MagicMock()
    project = {"is_wsl": True, "name": "p"}
    with patch("socket.socket") as mock_sock_class:
        mock_tsock = mock_sock_class.return_value
        mock_tsock.connect.side_effect = Exception("Tunnel Connect error")
        smart_eye_router.handle_tunneling(client, b"data", project, "p")
        client.close.assert_called_once()

def test_start_tunnel_close_error():
    s1 = MagicMock()
    s2 = MagicMock()
    s1.recv.side_effect = [b"msg", b""]
    s1.close.side_effect = Exception("S1 Close Fail")
    s2.close.side_effect = Exception("S2 Close Fail")
    with patch("threading.Thread") as mock_thread:
        smart_eye_router.start_tunnel(s1, s2)
        target_func = mock_thread.call_args_list[0][1]['target']
        target_func(s1, s2)

def test_handle_client_close_exception():
    client = MagicMock()
    client.recv.side_effect = Exception("Main error")
    client.close.side_effect = Exception("Close error")
    smart_eye_router.handle_client(client)
