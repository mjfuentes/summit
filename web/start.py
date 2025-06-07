#!/usr/bin/env python3
"""
Summit Web Server Startup Script
Automatically starts the Summit AI web interface
"""

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def kill_existing_server():
    """Kill any existing processes using port 8000"""
    try:
        # Find processes using port 8000
        result = subprocess.run(
            ["lsof", "-ti:8000"], capture_output=True, text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    print(f"Killing existing server process (PID: {pid})")
                    subprocess.run(["kill", pid], capture_output=True)
            time.sleep(1)  # Give processes time to shut down
            print("Cleared port 8000")

    except (subprocess.CalledProcessError, FileNotFoundError):
        # lsof command might not be available on all systems
        pass


def main():
    print("Starting Summit AI Web Server...")
    print("=" * 50)

    # Kill any existing processes on port 8000
    kill_existing_server()

    # Get the project root directory
    project_root = Path(__file__).parent.parent
    web_dir = project_root / "web"

    # Check if required files exist
    server_file = web_dir / "server.py"
    if not server_file.exists():
        print("ERROR: server.py not found in web/ directory")
        print(f"   Expected: {server_file}")
        sys.exit(1)

    # Check if requirements are installed
    try:
        import fastapi
        import uvicorn

        print("FastAPI and Uvicorn are installed")
    except ImportError:
        print("Missing dependencies. Installing...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "fastapi", "uvicorn"],
                check=True,
                capture_output=True,
            )
            print("Dependencies installed successfully")
        except subprocess.CalledProcessError:
            print("ERROR: Failed to install dependencies. Please run:")
            print("   pip install fastapi uvicorn")
            sys.exit(1)

    print(f"Project root: {project_root}")
    print(f"Starting web server from: {web_dir}")

    # Change to web directory
    os.chdir(web_dir)

    print("\nSummit AI Web Interface")
    print("   Interface: http://localhost:8000")
    print("   API Docs:  http://localhost:8000/docs")
    print("   Health:    http://localhost:8000/health")
    print("\nStarting server (this may take a few seconds)...")

    # Start the web server
    try:
        # Give it a moment then open browser
        def open_browser():
            time.sleep(2)
            try:
                webbrowser.open("http://localhost:8000")
                print("Opened web interface in your browser")
            except BaseException:
                pass

        import threading

        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()

        # Start the server
        subprocess.run([sys.executable, "standalone_server.py"], check=True)

    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        print("Summit web server shut down cleanly")
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Error starting server: {e}")
        print("\nTroubleshooting:")
        print("1. Check if port 8000 is already in use")
        print("2. Ensure all dependencies are installed")
        print("3. Try running manually: cd web && python server.py")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
