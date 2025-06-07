#!/usr/bin/env python3
"""
Summit Standalone Web Server
A simplified web interface that doesn't require MCP dependencies
"""

import os
import subprocess
import sys
import time
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


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


# Add src to path for basic imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from config import SUMMIT_CONFIG, setup_environment
    from cost_tracker import CostTracker

    setup_environment()

    # Initialize components
    cost_tracker = CostTracker(
        daily_budget=SUMMIT_CONFIG["daily_budget"],
        hourly_budget=SUMMIT_CONFIG["hourly_budget"],
        max_recursion_depth=SUMMIT_CONFIG["max_recursion_depth"],
    )

    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some components unavailable: {e}")
    cost_tracker = None
    COMPONENTS_AVAILABLE = False

app = FastAPI(title="Summit AI Web Interface", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Summit AI</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f0f2f5; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #1a73e8; text-align: center; }
        .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input, textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #1a73e8; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        button:hover { background: #1557b0; }
        .response { background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 4px; white-space: pre-wrap; border-left: 4px solid #4caf50; }
        .loading { background: #fff3cd; border-left-color: #ffc107; }
        .error { background: #f8d7da; border-left-color: #dc3545; }
        .warning { background: #fff3cd; padding: 10px; border-radius: 4px; border-left: 4px solid #ffc107; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Summit AI Web Interface</h1>
        <p style="text-align: center; color: #666;">Standalone web interface for Summit AI</p>

        <div class="warning">
            <strong>Note:</strong> This is a simplified web interface. Full autonomous capabilities are available through the main API.
        </div>

        <div class="card">
            <h3>Autonomous System</h3>
            <p>This standalone interface provides basic system status. For full autonomous Claude Code functionality, use the main API at <code>/api/tasks</code>.</p>
        </div>

        <div class="card">
            <h3>System Information</h3>
            <button onclick="getStatus()">Get Status</button>
            <div id="status-response" class="response" style="display: none;"></div>
        </div>
    </div>

    <script>
        async function makeRequest(endpoint, data = null) {
            const options = {
                method: data ? 'POST' : 'GET',
                headers: { 'Content-Type': 'application/json' }
            };
            if (data) options.body = JSON.stringify(data);

            const response = await fetch(endpoint, options);
            return await response.json();
        }

        function showResponse(elementId, data, isError = false) {
            const element = document.getElementById(elementId);
            element.style.display = 'block';
            element.className = isError ? 'response error' : 'response';
            element.textContent = data;
        }

        function showLoading(elementId) {
            const element = document.getElementById(elementId);
            element.style.display = 'block';
            element.className = 'response loading';
            element.textContent = 'Loading...';
        }



        async function getStatus() {
            showLoading('status-response');

            try {
                const result = await makeRequest('/api/status');
                showResponse('status-response', result.data || result.message, !result.success);
            } catch (error) {
                showResponse('status-response', 'Error: ' + error.message, true);
            }
        }
    </script>
</body>
</html>
    """


@app.get("/api/status")
async def get_status():
    status_info = "Summit Standalone Web Interface\n\n"

    if COMPONENTS_AVAILABLE:
        status_info += "Components Status:\n"
        status_info += f"- Cost Tracker: Available\n"
        status_info += f"- Autonomous System: Ready\n\n"
    else:
        status_info += "Components Status:\n"
        status_info += "- Limited functionality (some dependencies missing)\n"

    return {"success": True, "data": status_info}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Summit standalone web interface is running",
    }


if __name__ == "__main__":
    # Kill any existing processes on port 8000
    kill_existing_server()

    print("Starting Summit Standalone Web Interface...")
    print("Web interface: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")

    uvicorn.run(
        "standalone_server:app", host="0.0.0.0", port=8000, reload=True
    )
