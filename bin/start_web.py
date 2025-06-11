#!/usr/bin/env python3
"""
Summit Web Server Launcher
Simple launcher that delegates to the organized web server
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    # Get the project root directory
    project_root = Path(__file__).parent
    web_start_script = project_root / "web" / "start.py"

    if not web_start_script.exists():
        print(
            "ERROR: Web server not found. Please ensure the web/ directory exists."
        )
        sys.exit(1)

    # Run the web server startup script
    try:
        subprocess.run([sys.executable, str(web_start_script)], check=True)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to start web server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
