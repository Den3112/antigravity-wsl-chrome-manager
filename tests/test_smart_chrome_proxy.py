import pytest
import os
import json
import socket
import threading
import time
from unittest.mock import patch, mock_open, MagicMock
import sys
import subprocess
import runpy

# Add the parent directory to sys.path to import the script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import smart_chrome_proxy
from smart_chrome_proxy import ChromeRegistry, REGISTRY_FILE

@pytest.fixture(autouse=True)
def reset_globals():
    # Reset Singleton for tests
    ChromeRegistry._instance = None
    smart_chrome_proxy._launch_locks = {}
    if os.path.exists(REGISTRY_FILE):
        try: os.remove(REGISTRY_FILE)
        except: pass
    yield
    if os.path.exists(REGISTRY_FILE):
        try: os.remove(REGISTRY_FILE)
        except: pass

@pytest.fixture
def registry():
    return ChromeRegistry()

def test_registry_singleton(registry):
    r2 = ChromeRegistry()
    assert registry is r2

def test_registry_load_empty(registry):
    with patch("os.path.exists", return_value=False):
        registry.projects = {"dummy": "data"}
        registry.load()
        assert registry.projects == {"dummy": "data"}

def test_registry_load_success(registry):
    mock_data = '{"test": {"port": 1234, "pid": 5678}}'
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=mock_data)):
            registry.load()
            assert registry.projects == {"test": {"port": 1234, "pid": 5678}}

def test_registry_load_failure(registry):
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data="invalid json")):
            registry.load()
            assert registry.projects == {}

def test_registry_save_success(registry):
    registry.projects = {"test": {"port": 1234}}
    with patch("builtins.open", mock_open()) as mocked_file:
        with patch("os.replace") as mock_replace:
            registry.save()
            mock_replace.assert_called_once()

def test_registry_save_failure(registry):
    registry.projects = {"test": {"port": 1234}}
    with patch("builtins.open", side_effect=IOError("Permission denied")):
        with patch("smart_chrome_proxy.log") as mock_log:
            registry.save()
            mock_log.assert_called()

def test_registry_get_project(registry):
    registry.projects = {"p1": {"port": 80}}
    assert registry.get_project("p1") == {"port": 80}
    assert registry.get_project("nonexistent") is None

def test_registry_register_project(registry):
    with patch.object(registry, 'save') as mock_save:
        registry.register_project("new", 9000, 123)
        assert registry.projects["new"] == {"port": 9000, "pid": 123}
        mock_save.assert_called_once()

def test_registry_is_port_open():
    with patch("socket.create_connection") as mock_conn:
        mock_conn.return_value.__enter__.return_value = MagicMock()
        assert ChromeRegistry.is_port_open("localhost", 80) is True
        
        mock_conn.side_effect = Exception("Closed")
        assert ChromeRegistry.is_port_open("localhost", 80) is False

def test_registry_cleanup_stale_projects(registry):
    registry.projects = {
        "active": {"port": 8000},
        "stale": {"port": 9000}
    }
    
    def side_effect(host, port):
        return port == 8000
        
    with patch.object(ChromeRegistry, "is_port_open", side_effect=side_effect):
        with patch.object(registry, "save") as mock_save:
            registry.cleanup_stale_projects()
            assert "active" in registry.projects
            assert "stale" not in registry.projects
            mock_save.assert_called_once()

def test_registry_find_free_port(registry):
    registry.projects = {"p1": {"port": 9300}}
    
    def side_effect(host, port):
        if port == 9301: return True
        return False

    with patch.object(ChromeRegistry, "is_port_open", side_effect=side_effect):
        port = registry.find_free_port()
        assert port == 9302

def test_ensure_chrome_for_project_existing(registry):
    registry.projects = {"p": {"port": 9300}}
    with patch.object(ChromeRegistry, "is_port_open", return_value=True):
        port = smart_chrome_proxy.ensure_chrome_for_project("p")
        assert port == 9300

def test_ensure_chrome_for_project_race_condition(registry):
    registry.projects = {"p": {"port": 9301}}
    # Calls: 
    # 1. line 105 (fast check) -> False
    # 2. line 117 (cleanup) -> True (to keep it)
    # 3. line 119 (double check) -> True
    with patch.object(ChromeRegistry, "is_port_open", side_effect=[False, True, True]):
        with patch.object(registry, "load"):
            port = smart_chrome_proxy.ensure_chrome_for_project("p")
            assert port == 9301

def test_ensure_chrome_for_project_launch(registry):
    registry.projects = {}
    # 1. line 105 -> False
    # 2. find_free_port (port 9300) -> is_port_open? False
    # 3. while loop wait -> True
    with patch.object(ChromeRegistry, "is_port_open", side_effect=[False, False, True]):
        with patch("subprocess.Popen") as mock_popen:
            with patch("subprocess.check_output", return_value=b"1234\n"):
                port = smart_chrome_proxy.ensure_chrome_for_project("new_p")
                assert port == 9300
                mock_popen.assert_called_once()
                assert registry.projects["new_p"]["port"] == 9300
                assert registry.projects["new_p"]["pid"] == 1234

def test_ensure_chrome_for_project_launch_no_pid(registry):
    registry.projects = {}
    with patch.object(ChromeRegistry, "is_port_open", side_effect=[False, False, True]):
        with patch("subprocess.Popen"):
            with patch("subprocess.check_output", side_effect=Exception("pgrep failed")):
                port = smart_chrome_proxy.ensure_chrome_for_project("new_no_pid")
                assert port == 9300
                assert registry.projects["new_no_pid"]["pid"] == 0

def test_ensure_chrome_for_project_timeout(registry):
    registry.projects = {}
    with patch.object(ChromeRegistry, "is_port_open", return_value=False):
        with patch("subprocess.Popen"):
            with patch("time.time", side_effect=[0, 1, 2, 45]):
                port = smart_chrome_proxy.ensure_chrome_for_project("timeout_p")
                assert port is None

def test_ensure_chrome_for_project_exception(registry):
    registry.projects = {}
    with patch.object(ChromeRegistry, "is_port_open", return_value=False):
        with patch("subprocess.Popen", side_effect=Exception("Spawn failed")):
            port = smart_chrome_proxy.ensure_chrome_for_project("fail_p")
            assert port is None

def test_handle_client(registry):
    mock_socket = MagicMock()
    with patch("smart_chrome_proxy.ensure_chrome_for_project", return_value=9300):
        with patch("socket.socket") as mock_sock_class:
            mock_srv_sock = mock_sock_class.return_value
            with patch("threading.Thread") as mock_thread:
                smart_chrome_proxy.handle_client(mock_socket)
                mock_srv_sock.connect.assert_called_with(('127.0.0.1', 9300))
                assert mock_thread.call_count == 2

def test_handle_client_ensure_fails(registry):
    mock_socket = MagicMock()
    with patch("smart_chrome_proxy.ensure_chrome_for_project", return_value=None):
        smart_chrome_proxy.handle_client(mock_socket)
        mock_socket.close.assert_called_once()

def test_handle_client_exception(registry):
    mock_socket = MagicMock()
    with patch("smart_chrome_proxy.ensure_chrome_for_project", side_effect=Exception("Error")):
        smart_chrome_proxy.handle_client(mock_socket)
        mock_socket.close.assert_called_once()

def test_forward():
    src = MagicMock()
    dst = MagicMock()
    src.recv.side_effect = [b"data", b""]
    smart_chrome_proxy.forward(src, dst)
    dst.sendall.assert_called_with(b"data")
    src.close.assert_called_once()
    dst.close.assert_called_once()

def test_forward_exception():
    src = MagicMock()
    dst = MagicMock()
    src.recv.side_effect = Exception("error")
    smart_chrome_proxy.forward(src, dst)
    src.close.assert_called_once()
    dst.close.assert_called_once()

def test_maintain_window_titles(registry):
    registry.projects = {"p1": {"pid": 123, "port": 9300}}
    with patch("subprocess.check_output") as mock_out:
        mock_out.side_effect = [
            b"456\n", # xdotool search
            b"wrong_title\n" # xdotool getwindowname
        ]
        with patch("subprocess.run") as mock_run:
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                with pytest.raises(KeyboardInterrupt):
                    smart_chrome_proxy.maintain_window_titles()
                mock_run.assert_called()

def test_maintain_window_titles_missing_display(registry):
    with patch.dict(os.environ, {}, clear=True):
        with patch("time.sleep", side_effect=KeyboardInterrupt):
            with patch("subprocess.check_output", side_effect=KeyboardInterrupt):
                with pytest.raises(KeyboardInterrupt):
                    smart_chrome_proxy.maintain_window_titles()
                assert os.environ["DISPLAY"] == ":0"

def test_maintain_window_titles_xdotool_exception(registry):
    registry.projects = {"p1": {"pid": 123, "port": 9300}}
    with patch("subprocess.check_output") as mock_out:
        mock_out.side_effect = [
            b"456\n", # xdotool search
            Exception("xdotool failed") # hit line 229
        ]
        with patch("time.sleep", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                smart_chrome_proxy.maintain_window_titles()

def test_maintain_window_titles_global_exception(registry):
    # Trigger exception at the top of the loop to cover line 231-232
    with patch.object(registry, "projects", new_callable=MagicMock) as mock_projects:
        mock_projects.items.side_effect = Exception("Global loop error")
        with patch("time.sleep", side_effect=[None, KeyboardInterrupt]): # Run once then exit
            with patch("smart_chrome_proxy.log") as mock_log:
                with pytest.raises(KeyboardInterrupt):
                    smart_chrome_proxy.maintain_window_titles()
                mock_log.assert_any_call("Title maintainer error: Global loop error")

def test_log():
    with patch("sys.argv", ["script.py"]):
        with patch("builtins.print") as mock_print:
            smart_chrome_proxy.log("test msg")
            mock_print.assert_called()
    
    with patch("sys.argv", ["script.py", "ensure"]):
        with patch("sys.stderr.write") as mock_write:
            smart_chrome_proxy.log("test msg stderr")
            mock_write.assert_called()

def test_main_server_loop():
    with patch("socket.socket") as mock_sock_class:
        mock_srv = mock_sock_class.return_value
        mock_srv.accept.side_effect = [ (MagicMock(), ('127.0.0.1', 1234)), KeyboardInterrupt ]
        with patch("threading.Thread"):
            with patch("sys.argv", ["prog"]):
                smart_chrome_proxy.main()
                mock_srv.bind.assert_called()

def test_main_bind_fail():
    with patch("socket.socket") as mock_sock_class:
        mock_srv = mock_sock_class.return_value
        mock_srv.bind.side_effect = Exception("Bind failed")
        with patch("sys.argv", ["prog"]):
            with pytest.raises(SystemExit):
                smart_chrome_proxy.main()

def test_main_cli_ensure_success():
    with patch("sys.argv", ["prog", "ensure", "proj"]):
        with patch("smart_chrome_proxy.ensure_chrome_for_project", return_value=9300):
            with patch("builtins.print") as mock_print:
                with pytest.raises(SystemExit) as e:
                    smart_chrome_proxy.main()
                assert e.value.code == 0
                mock_print.assert_called_with(9300)

def test_main_cli_ensure_fail():
    with patch("sys.argv", ["prog", "ensure", "proj"]):
        with patch("smart_chrome_proxy.ensure_chrome_for_project", return_value=None):
            with pytest.raises(SystemExit) as e:
                smart_chrome_proxy.main()
            assert e.value.code == 1

def test_main_cli_check_success(registry):
    registry.projects = {"proj": {"port": 9300}}
    with patch("sys.argv", ["prog", "check", "proj"]):
        with patch.object(ChromeRegistry, "is_port_open", return_value=True):
            with patch("builtins.print") as mock_print:
                with pytest.raises(SystemExit) as e:
                    smart_chrome_proxy.main()
                assert e.value.code == 0
                mock_print.assert_called_with(9300)

def test_main_cli_check_fail(registry):
    registry.projects = {"proj": {"port": 9300}}
    with patch("sys.argv", ["prog", "check", "proj"]):
        with patch.object(ChromeRegistry, "is_port_open", return_value=False):
            with patch("builtins.print") as mock_print:
                with pytest.raises(SystemExit) as e:
                    smart_chrome_proxy.main()
                assert e.value.code == 0
                mock_print.assert_called_with(0)

def test_if_name_main():
    # Use runpy to cover the 'if __name__ == "__main__":' block
    # We patch the server parts so main doesn't block or fail
    with patch("sys.argv", ["prog"]):
        with patch("socket.socket") as mock_sock:
            mock_sock.return_value.accept.side_effect = KeyboardInterrupt
            # We also need to mock maintain_window_titles so it doesn't loop
            with patch("threading.Thread"):
                try:
                    runpy.run_path("smart_chrome_proxy.py", run_name="__main__")
                except (SystemExit, KeyboardInterrupt):
                    pass
