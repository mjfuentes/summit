#!/usr/bin/env python3
"""
Startup script for Summit server on Render.com
Handles environment setup and path configuration
"""

import os
import subprocess
import sys


def setup_environment():
    """Set up the environment for the Summit server"""

    # Get the current directory (where this script is located)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Add src directory to Python path
    src_dir = os.path.join(current_dir, "src")
    if os.path.exists(src_dir):
        sys.path.insert(0, src_dir)
        os.environ["PYTHONPATH"] = (
            src_dir + ":" + os.environ.get("PYTHONPATH", "")
        )
        print(f"[STARTUP] Added {src_dir} to PYTHONPATH")
    else:
        print(f"[STARTUP] Warning: src directory not found at {src_dir}")

    # Set working directory to project root
    os.chdir(current_dir)
    print(f"[STARTUP] Changed working directory to {current_dir}")

    # Print debug information
    print(f"[STARTUP] Current working directory: {os.getcwd()}")
    print(f"[STARTUP] Python path: {sys.path[:3]}...")  # Show first 3 entries
    print(
        f"[STARTUP] PYTHONPATH environment: {os.environ.get('PYTHONPATH', 'Not set')}"
    )

    # Check if required modules exist
    required_files = [
        os.path.join(src_dir, "database.py"),
        os.path.join(src_dir, "task_manager.py"),
        os.path.join("web", "autonomous_server.py"),
    ]

    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"[STARTUP]  Found {file_path}")
        else:
            print(f"[STARTUP]  Missing {file_path}")


def main():
    """Main startup function"""
    print("[STARTUP] Starting Summit server...")

    # Set up environment
    setup_environment()

    # Start the server
    server_script = os.path.join("web", "autonomous_server.py")

    if not os.path.exists(server_script):
        print(f"[STARTUP] Error: Server script not found at {server_script}")
        sys.exit(1)

    print(f"[STARTUP] Launching server: {server_script}")

    # Use exec to replace the current process
    os.execv(sys.executable, [sys.executable, server_script])


if __name__ == "__main__":
    main()
