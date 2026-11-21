"""
AquaSure Launcher — run.py
Unified startup script for the AquaSure groundwater analytics platform.

Usage:
    python run.py              # Start Flask API + serve static frontend (default)
    python run.py api          # Same as above (explicit)
    python run.py streamlit    # Launch the Streamlit dashboard instead

Ports:
    Flask REST API  → http://localhost:5000  (health: http://localhost:5000/api/health)
    Static frontend → http://localhost:8000
    Streamlit       → http://localhost:8501  (managed by Streamlit itself)

Press Ctrl+C to shut everything down cleanly.
"""

import os
import sys
import signal
import subprocess
import threading
import time
import webbrowser
import http.server
import socketserver
import argparse

# ---------------------------------------------------------------------------
# Project root is the directory that contains this file (run.py).
# All sub-paths are resolved relative to it so the script works regardless
# of the working directory from which the user invokes it.
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Use the same Python interpreter that is running this launcher so that the
# correct virtual-environment packages are always picked up.
PYTHON = sys.executable

# Ports (change here if you need different values)
FLASK_PORT      = 5000
FRONTEND_PORT   = 8000
STREAMLIT_PORT  = 8501   # Streamlit manages its own default; shown for reference

# ---------------------------------------------------------------------------
# Shared state: list of subprocesses to terminate on shutdown
# ---------------------------------------------------------------------------
_procs: list[subprocess.Popen] = []
_shutdown_event = threading.Event()


# ---------------------------------------------------------------------------
# Signal handler — catches Ctrl+C (SIGINT) and SIGTERM on Unix
# ---------------------------------------------------------------------------
def _shutdown(sig=None, frame=None):
    if _shutdown_event.is_set():
        return
    _shutdown_event.set()
    print("\n[AquaSure] Shutting down…", flush=True)
    for proc in _procs:
        try:
            proc.terminate()
        except OSError:
            pass
    # Give processes a moment to exit gracefully before we stop waiting
    for proc in _procs:
        try:
            proc.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            try:
                proc.kill()
            except OSError:
                pass
    print("[AquaSure] All processes stopped. Goodbye.", flush=True)
    sys.exit(0)


signal.signal(signal.SIGINT, _shutdown)
# SIGTERM is not available on Windows but harmless to register
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, _shutdown)


# ---------------------------------------------------------------------------
# Helper: start a subprocess and register it for shutdown
# ---------------------------------------------------------------------------
def _spawn(args: list[str], cwd: str | None = None) -> subprocess.Popen:
    proc = subprocess.Popen(
        args,
        cwd=cwd or PROJECT_ROOT,
        # On Windows, CREATE_NEW_PROCESS_GROUP lets us send Ctrl+C to the
        # child group without killing this parent process first.
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP
            if sys.platform == "win32"
            else 0
        ),
    )
    _procs.append(proc)
    return proc


# ---------------------------------------------------------------------------
# Mode 1 — Flask API (backend/app.py) + static file server (frontend/)
# ---------------------------------------------------------------------------
def run_api_mode(open_browser: bool = True):
    """Start Flask + a lightweight HTTP server for the static frontend."""

    # -- Flask backend -------------------------------------------------------
    flask_script = os.path.join(PROJECT_ROOT, "backend", "app.py")
    print(f"[AquaSure] Starting Flask API  → http://localhost:{FLASK_PORT}", flush=True)
    print(f"[AquaSure] Health check        → http://localhost:{FLASK_PORT}/api/health", flush=True)
    flask_proc = _spawn([PYTHON, flask_script])

    # -- Static frontend served by http.server in a daemon thread ------------
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")

    def _serve_frontend():
        """Run Python's built-in HTTP server in the frontend/ directory."""
        os.chdir(frontend_dir)   # http.server serves from CWD
        handler = http.server.SimpleHTTPRequestHandler
        # Silence the per-request log lines (optional — remove to see requests)
        handler.log_message = lambda self, *args: None
        with socketserver.TCPServer(("", FRONTEND_PORT), handler) as httpd:
            httpd.serve_forever()

    fe_thread = threading.Thread(target=_serve_frontend, daemon=True)
    fe_thread.start()
    print(f"[AquaSure] Static frontend     → http://localhost:{FRONTEND_PORT}", flush=True)

    # -- Optionally open browser after a short delay (Flask needs to boot) ---
    if open_browser:
        def _open_later():
            time.sleep(2)
            if not _shutdown_event.is_set():
                webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
        threading.Thread(target=_open_later, daemon=True).start()

    print("[AquaSure] Press Ctrl+C to stop all services.\n", flush=True)

    # Keep the main thread alive; watch for the Flask process exiting
    while not _shutdown_event.is_set():
        if flask_proc.poll() is not None:
            # Flask exited on its own (e.g. import error)
            print(
                f"[AquaSure] Flask process exited with code {flask_proc.returncode}.",
                flush=True,
            )
            _shutdown()
            break
        time.sleep(1)


# ---------------------------------------------------------------------------
# Mode 2 — Streamlit dashboard (app/streamlit_app.py)
# ---------------------------------------------------------------------------
def run_streamlit_mode(open_browser: bool = True):
    """Launch the Streamlit dashboard."""

    streamlit_app = os.path.join(PROJECT_ROOT, "app", "streamlit_app.py")

    # Streamlit is invoked as a module so the venv's streamlit is used
    args = [
        PYTHON, "-m", "streamlit", "run",
        streamlit_app,
        "--server.port", str(STREAMLIT_PORT),
        # Prevent Streamlit from auto-opening its own browser window so we
        # control the timing ourselves
        "--server.headless", "true" if open_browser else "false",
    ]

    print(f"[AquaSure] Starting Streamlit  → http://localhost:{STREAMLIT_PORT}", flush=True)
    st_proc = _spawn(args)

    if open_browser:
        def _open_later():
            time.sleep(3)   # Streamlit takes a moment longer to initialise
            if not _shutdown_event.is_set():
                webbrowser.open(f"http://localhost:{STREAMLIT_PORT}")
        threading.Thread(target=_open_later, daemon=True).start()

    print("[AquaSure] Press Ctrl+C to stop Streamlit.\n", flush=True)

    while not _shutdown_event.is_set():
        if st_proc.poll() is not None:
            print(
                f"[AquaSure] Streamlit process exited with code {st_proc.returncode}.",
                flush=True,
            )
            _shutdown()
            break
        time.sleep(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="AquaSure unified launcher",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="api",
        choices=["api", "streamlit"],
        help=(
            "'api' (default) starts the Flask REST API + static frontend; "
            "'streamlit' starts the Streamlit dashboard."
        ),
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        default=False,
        help="Do not automatically open a browser window.",
    )
    args = parser.parse_args()

    print("=" * 60, flush=True)
    print(" AquaSure — Tamil Nadu Groundwater Analytics Platform", flush=True)
    print("=" * 60, flush=True)

    if args.mode == "streamlit":
        run_streamlit_mode(open_browser=not args.no_browser)
    else:
        run_api_mode(open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
