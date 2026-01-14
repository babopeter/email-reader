import os
import socket
import sys
import threading
import time
import urllib.request
import urllib.error

import webview

from app import app


def _find_free_port() -> int:
    """Find an available localhost port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(port: int, timeout: int = 10):
    """Wait for Flask server to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, socket.error):
            time.sleep(0.1)
    return False


def _run_flask(port: int):
    """Run Flask server in a separate thread."""
    # Bind only to localhost, no debug/reloader in packaged mode.
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)


def _log_error(message: str):
    """Log errors to a file for debugging."""
    log_path = os.path.join(os.path.expanduser("~"), "Library", "Logs", "EmailReader.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


def main():
    try:
        # Upload folder is now configured in app.py before import
        _log_error("Starting Email Reader app")

        port = _find_free_port()
        _log_error(f"Using port {port}")

        # Start Flask server in background thread
        server_thread = threading.Thread(target=_run_flask, args=(port,), daemon=True)
        server_thread.start()
        _log_error("Flask server thread started")

        # Wait for Flask to be ready
        if not _wait_for_server(port):
            error_msg = "ERROR: Flask server did not start in time"
            _log_error(error_msg)
            print(error_msg, file=sys.stderr)
            sys.exit(1)

        _log_error("Flask server is ready")

        # Create and start webview window (must be on main thread)
        url = f"http://127.0.0.1:{port}/"
        _log_error(f"Creating webview window with URL: {url}")
        window = webview.create_window("Email Reader", url, width=1200, height=800)
        _log_error("Starting webview")
        webview.start(debug=False)
        _log_error("Webview closed")
    except Exception as e:
        error_msg = f"ERROR: {e}"
        _log_error(error_msg)
        import traceback
        trace_msg = traceback.format_exc()
        _log_error(trace_msg)
        print(error_msg, file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

