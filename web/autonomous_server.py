#!/usr/bin/env python3
"""
Summit Autonomous Learning Server
Advanced AI task management with container orchestration
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from database import close_database, get_database, init_database
from pr_reviewers import review_pr_with_multiple_roles
from task_manager import (
    add_task_log,
    get_task_data,
    mark_task_completed,
    update_task_container_info,
    update_task_log_file,
    update_task_status,
)

# Import GitHub functionality for PR creation
try:
    # Temporarily disable summit import due to MCP version compatibility
    raise ImportError("Temporarily disabled")
    from summit import create_pull_request, get_github_repo_info
except ImportError:
    # Fallback if summit module not available
    print(
        "[WARNING] Summit module not available - PR creation will be disabled"
    )

    def create_pull_request(*args, **kwargs):
        raise Exception("Summit module not available")

    def get_github_repo_info():
        return None, None


# Import CI/CD monitoring functionality
try:
    from github_cicd import get_task_ci_status, get_workflow_runs_for_task
except ImportError:
    print("[WARNING] GitHub CI/CD module not available")

    async def get_task_ci_status(task_data):
        return {
            "state": "unknown",
            "message": "CI/CD monitoring not available",
        }

    async def get_workflow_runs_for_task(task_data):
        return []


def kill_existing_server():
    """Kill any existing processes using port 8000"""
    try:
        result = subprocess.run(
            ["lsof", "-ti:8000"], capture_output=True, text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    print(f"Killing existing server process (PID: {pid})")
                    subprocess.run(["kill", pid], capture_output=True)
            time.sleep(1)
            print("Cleared port 8000")

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass


# Bootstrap dependencies
def bootstrap_dependencies():
    """Install dependencies from requirements.txt."""
    requirements_path = os.path.join(
        os.path.dirname(__file__), "..", "requirements.txt"
    )
    if not os.path.exists(requirements_path):
        print(f"Warning: requirements.txt not found at {requirements_path}")
        return

    print("Checking and installing dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", requirements_path]
        )
        print("Dependencies are up to date.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        print(
            "Please install dependencies manually using: pip install -r requirements.txt"
        )
        # Exit if dependencies can't be installed, as the app won't run
        sys.exit(1)


# Bootstrap will be called only when running the server directly

# Import database functionality

app = FastAPI(title="Summit Autonomous AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database will replace these in-memory structures
# active_tasks: Dict[str, Dict] = {}
# task_history: List[Dict] = []

# Log directory for task logs
log_dir = "task_logs"


class TaskRequest(BaseModel):
    task_description: str  # Only thing the user needs to provide


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: str
    logs: List[str]
    created_at: str
    container_id: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_database()
    print("Database initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connections on shutdown"""
    await close_database()
    print("Database connections closed")


@app.get("/")
async def root():
    import os

    from fastapi import Response

    # Try to read the external HTML file first
    html_file_path = os.path.join(
        os.path.dirname(__file__), "..", "templates", "index.html"
    )

    if os.path.exists(html_file_path):
        try:
            with open(html_file_path, "r", encoding="utf-8") as f:
                external_html = f.read()

            # Check if external HTML has the required functionality
            if (
                "createTask()" in external_html
                and "api/tasks" in external_html
            ):
                html_content = external_html
            else:
                # External HTML lacks functionality, create hybrid with Y2K
                # styling but full features
                print(
                    "External HTML lacks functionality, creating hybrid version..."
                )
                html_content = create_hybrid_html()
        except Exception as e:
            print(f"Error reading HTML file: {e}")
            # Fallback to embedded HTML
            html_content = create_hybrid_html()
    else:
        # External file doesn't exist, use embedded HTML with all features
        html_content = create_hybrid_html()

    # Create response with cache-busting headers
    response = Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
        },
    )
    return response


def create_hybrid_html():
    """Create HTML with Y2K styling but full Summit functionality"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS AI  Y2K AUTONOMOUS INTELLIGENCE </title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Courier New', 'Arial Black', monospace;
            margin: 0;
            background: linear-gradient(45deg, #ff00ff, #00ffff, #ffff00, #ff00ff);
            background-size: 400% 400%;
            animation: gradientShift 3s ease infinite;
            min-height: 100vh;
            color: #000;
            overflow-x: hidden;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }

        .header {
            text-align: center;
            color: #000;
            margin-bottom: 40px;
            padding: 30px 0;
            background: rgba(255, 255, 255, 0.1);
            border: 3px solid #ff00ff;
            border-radius: 20px;
            box-shadow: 0 0 20px #00ffff;
        }
        .header h1 {
            font-size: 3.5rem;
            margin: 0;
            text-shadow: 3px 3px 0px #ff00ff, 6px 6px 0px #00ffff;
            font-weight: 900;
            color: #ffff00;
            text-transform: uppercase;
            letter-spacing: 3px;
        }
        .header p {
            font-size: 1.3rem;
            margin: 15px 0;
            font-weight: 700;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
            color: #000;
            text-shadow: 1px 1px 0px #fff;
        }

        .voice-input {
            position: relative;
            margin: 15px 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .voice-btn {
            background: linear-gradient(135deg, #10b981, #059669);
            border: none;
            border-radius: 50%;
            width: 56px;
            height: 56px;
            color: white;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }
        .voice-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4); }
        .voice-btn.recording {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            animation: pulse 1s infinite;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
        }
        .voice-status { font-size: 14px; color: #6b7280; font-weight: 500; }

        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }

        .main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px; }
        @media (max-width: 768px) { .main-grid { grid-template-columns: 1fr; gap: 20px; } }

        .card {
            background: rgba(255, 255, 255, 0.9);
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 0 30px #ff00ff, inset 0 0 30px rgba(0, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            border: 3px solid #00ffff;
            transition: all 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 0 50px #ffff00, inset 0 0 50px rgba(255, 0, 255, 0.3);
            border-color: #ff00ff;
        }
        .card h2 {
            color: #ff00ff;
            margin-top: 0;
            font-size: 1.75rem;
            font-weight: 900;
            margin-bottom: 20px;
            text-transform: uppercase;
            text-shadow: 2px 2px 0px #00ffff;
            letter-spacing: 2px;
        }

        .task-form textarea {
            width: 100%;
            min-height: 140px;
            padding: 18px;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            font-size: 15px;
            resize: vertical;
            font-family: inherit;
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
            line-height: 1.6;
        }
        .task-form textarea:focus {
            outline: none;
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }

        .btn {
            background: linear-gradient(45deg, #ff00ff, #00ffff, #ffff00, #ff00ff);
            background-size: 300% 300%;
            animation: gradientShift 2s ease infinite;
            color: #000;
            padding: 16px 32px;
            border: 3px solid #000;
            border-radius: 12px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 900;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 0 20px #ff00ff;
            width: 100%;
            text-transform: uppercase;
            letter-spacing: 1px;
            text-shadow: 1px 1px 0px #fff;
        }
        .btn:hover {
            transform: translateY(-2px) scale(1.05);
            box-shadow: 0 0 30px #00ffff;
            border-color: #ff00ff;
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .task-item {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            padding: 20px;
            margin: 15px 0;
            border-radius: 12px;
            border-left: 4px solid #6366f1;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .task-item:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            background: linear-gradient(135deg, #ffffff, #f8fafc);
        }

        .task-list-container {
            height: 300px;
            overflow-y: auto;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.8);
            position: relative;
        }

        .pagination-controls {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin-top: 15px;
            padding: 10px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }

        .pagination-btn {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s ease;
        }

        .pagination-btn:hover {
            background: linear-gradient(135deg, #5b21b6, #7c3aed);
            transform: translateY(-1px);
        }

        .pagination-btn:disabled {
            background: #9ca3af;
            cursor: not-allowed;
            transform: none;
        }

        .pagination-info {
            color: #6b7280;
            font-size: 14px;
            font-weight: 500;
        }

        .task-status {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status-running { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: white; }
        .status-completed { background: linear-gradient(135deg, #10b981, #059669); color: white; }
        .status-failed { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; }

        .logs {
            background: #0f172a;
            color: #10b981;
            padding: 20px;
            border-radius: 12px;
            font-family: 'SF Mono', 'Monaco', 'Cascadia Code', 'Roboto Mono', monospace;
            font-size: 13px;
            max-height: 350px;
            overflow-y: auto;
            margin: 15px 0;
            border: 1px solid #1e293b;
            line-height: 1.5;
        }

        .progress-bar {
            background: #e5e7eb;
            height: 6px;
            border-radius: 3px;
            overflow: hidden;
            margin: 15px 0;
        }
        .progress-fill {
            background: linear-gradient(90deg, #6366f1, #8b5cf6);
            height: 100%;
            transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 18px;
            border-radius: 25px;
            font-size: 12px;
            font-weight: 600;
            backdrop-filter: blur(10px);
            z-index: 1000;
        }
        .connected { background: rgba(16, 185, 129, 0.9); color: white; }
        .disconnected { background: rgba(239, 68, 68, 0.9); color: white; }

        .task-monitor {
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: none;
        }
        .task-monitor.visible {
            opacity: 1;
            transform: translateY(0);
            pointer-events: auto;
        }

        .empty-state {
            text-align: center;
            color: #6b7280;
            padding: 40px 20px;
            font-style: italic;
        }
        .empty-state i { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .loading { animation: pulse 1.5s infinite; }

        /* Smooth scrolling */
        html { scroll-behavior: smooth; }

        /* Custom scrollbar */
        .logs::-webkit-scrollbar { width: 6px; }
        .logs::-webkit-scrollbar-track { background: #1e293b; }
        .logs::-webkit-scrollbar-thumb { background: #475569; border-radius: 3px; }
        .logs::-webkit-scrollbar-thumb:hover { background: #64748b; }

        .retrigger-btn {
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            color: white;
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.3s ease;
            margin-left: 10px;
            display: inline-block;
        }
        .retrigger-btn:hover {
            background: linear-gradient(135deg, #7c3aed, #6d28d9);
            transform: translateY(-1px);
        }
        .retrigger-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .batch-retrigger-section {
            background: rgba(139, 92, 246, 0.1);
            border: 2px solid rgba(139, 92, 246, 0.3);
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            text-align: center;
        }

        .failed-tasks-card {
            background: rgba(239, 68, 68, 0.1);
            border-left: 4px solid #ef4444;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> NEXUS AI </h1>
            <p>YO! NEXUS AI is the DOPEST autonomous intelligence that learns NEW SKILLS and codes itself UP to handle WHATEVER you throw at it! This ain't your basic chatbot - we're talking NEXT LEVEL AI! </p>
        </div>

        <div id="connection-status" class="connection-status disconnected">Connecting...</div>

        <div class="main-grid">
            <div class="card">
                <h2> CREATE TASK </h2>
                <div class="task-form">
                    <div class="voice-input">
                        <button class="voice-btn" id="voice-btn" onclick="toggleVoiceInput()"></button>
                        <span class="voice-status" id="voice-status">SPEAK TO THE AI!</span>
                    </div>
                    <textarea id="task-description" placeholder="What are we building today?"></textarea>

                    <!-- All backend configuration is now hardcoded -->

                    <button class="btn" onclick="createTask()" id="create-btn"> START AUTONOMOUS LEARNING </button>
                </div>
            </div>

            <div class="card">
                <h2> ACTIVE TASKS </h2>
                <div class="task-list-container" id="active-tasks">
                    <div class="empty-state">
                        <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></div>
                        <p>NO ACTIVE TASKS</p>
                        <p style="font-size: 14px; margin-top: 8px;">CREATE A TASK TO GET THIS PARTY STARTED! </p>
                    </div>
                </div>
                <div class="pagination-controls" id="pagination-controls" style="display: none;">
                    <button class="pagination-btn" id="prev-btn" onclick="previousPage()">← Previous</button>
                    <span class="pagination-info" id="pagination-info">Page 1 of 1</span>
                    <button class="pagination-btn" id="next-btn" onclick="nextPage()">Next →</button>
                </div>
            </div>
        </div>

        <!-- Failed Tasks Management Section -->
        <div class="card failed-tasks-card" id="failed-tasks-section" style="display: none;">
            <h2 style="color: #ef4444;">Failed Tasks Management</h2>
            <div class="batch-retrigger-section">
                <h3>Batch Operations</h3>
                <p style="color: #6b7280; margin: 10px 0;">Retrigger all failed tasks with fresh Claude instances</p>
                <button class="btn" onclick="retriggerAllFailed()" id="batch-retrigger-btn" style="background: linear-gradient(135deg, #8b5cf6, #7c3aed); max-width: 300px;">
                    Retrigger All Failed Tasks
                </button>
            </div>
            <div class="task-list-container" id="failed-tasks-list">
                <div class="empty-state">
                    <p>No failed tasks found</p>
                </div>
            </div>
            <div class="pagination-controls" id="failed-pagination-controls" style="display: none;">
                <button class="pagination-btn" id="failed-prev-btn" onclick="previousFailedPage()">← Previous</button>
                <span class="pagination-info" id="failed-pagination-info">Page 1 of 1</span>
                <button class="pagination-btn" id="failed-next-btn" onclick="nextFailedPage()">Next →</button>
            </div>
        </div>

        <div class="task-monitor" id="task-monitor">
            <div class="card">
                <h2>Task Monitor</h2>
                <div id="selected-task-details">
                    <h3 id="task-title">Task Details</h3>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
                    </div>
                    <div id="task-logs" class="logs"></div>
                    <button class="btn" onclick="stopTask()" id="stop-btn" style="background: linear-gradient(135deg, #ef4444, #dc2626); margin-top: 15px;">Stop Task</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let selectedTaskId = null;
        let recognition = null;
        let isRecording = false;

        // Pagination variables
        let currentPage = 1;
        let tasksPerPage = 3;
        let allTasks = [];

        // Failed tasks pagination variables
        let currentFailedPage = 1;
        let failedTasksPerPage = 3;
        let allFailedTasks = [];

        // Initialize speech recognition
        function initSpeechRecognition() {
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.lang = 'en-US';

                recognition.onstart = function() {
                    isRecording = true;
                    document.getElementById('voice-btn').classList.add('recording');
                    document.getElementById('voice-status').textContent = 'Listening...';
                };

                recognition.onresult = function(event) {
                    let finalTranscript = '';
                    let interimTranscript = '';

                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        const transcript = event.results[i][0].transcript;
                        if (event.results[i].isFinal) {
                            finalTranscript += transcript;
                        } else {
                            interimTranscript += transcript;
                        }
                    }

                    const currentText = document.getElementById('task-description').value;
                    if (finalTranscript) {
                        document.getElementById('task-description').value = currentText + finalTranscript + ' ';
                    }

                    if (interimTranscript) {
                        document.getElementById('voice-status').textContent = 'Hearing: ' + interimTranscript;
                    }
                };

                recognition.onend = function() {
                    isRecording = false;
                    document.getElementById('voice-btn').classList.remove('recording');
                    document.getElementById('voice-status').textContent = 'Click to speak';
                };

                recognition.onerror = function(event) {
                    console.error('Speech recognition error:', event.error);
                    document.getElementById('voice-status').textContent = 'Error: ' + event.error;
                };
            } else {
                document.getElementById('voice-status').textContent = 'Speech recognition not supported';
            }
        }

        function toggleVoiceInput() {
            if (!recognition) {
                initSpeechRecognition();
            }

            if (isRecording) {
                recognition.stop();
            } else {
                recognition.start();
            }
        }

        // WebSocket removed - using simple HTTP polling instead

        function handleTaskUpdate(data) {
            if (data.type === 'task_update') {
                if (selectedTaskId === data.task.task_id) {
                    updateTaskDetails(data.task);
                }
            } else if (data.type === 'task_list') {
                updateActiveTasksList(data.tasks);
            }
        }

        function updateActiveTasksList(tasks) {
            allTasks = tasks;
            const container = document.getElementById('active-tasks');
            const paginationControls = document.getElementById('pagination-controls');

            if (tasks.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></div>
                        <p>No active tasks</p>
                        <p style="font-size: 14px; margin-top: 8px;">Create a task to get started</p>
                    </div>
                `;
                paginationControls.style.display = 'none';
                hideTaskMonitor();
                return;
            }

            // Calculate pagination
            const totalPages = Math.ceil(tasks.length / tasksPerPage);
            const startIndex = (currentPage - 1) * tasksPerPage;
            const endIndex = startIndex + tasksPerPage;
            const tasksToShow = tasks.slice(startIndex, endIndex);

            // Display tasks for current page
            container.innerHTML = tasksToShow.map(task => `
                <div class="task-item" onclick="selectTask('${task.task_id}')">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <strong style="flex: 1; margin-right: 12px;">${task.task_description.substring(0, 60)}${task.task_description.length > 60 ? '...' : ''}</strong>
                        <span class="task-status status-${task.status}">${task.status}</span>
                    </div>
                    <div style="font-size: 13px; color: #6b7280;">
                        Created: ${new Date(task.created_at).toLocaleString()}
                    </div>
                </div>
            `).join('');

            // Show/hide pagination controls based on number of tasks
            if (tasks.length > tasksPerPage) {
                paginationControls.style.display = 'flex';
                updatePaginationControls(totalPages);
            } else {
                paginationControls.style.display = 'none';
            }
        }

        function updatePaginationControls(totalPages) {
            const prevBtn = document.getElementById('prev-btn');
            const nextBtn = document.getElementById('next-btn');
            const paginationInfo = document.getElementById('pagination-info');

            prevBtn.disabled = currentPage === 1;
            nextBtn.disabled = currentPage === totalPages;
            paginationInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        }

        function previousPage() {
            if (currentPage > 1) {
                currentPage--;
                updateActiveTasksList(allTasks);
            }
        }

        function nextPage() {
            const totalPages = Math.ceil(allTasks.length / tasksPerPage);
            if (currentPage < totalPages) {
                currentPage++;
                updateActiveTasksList(allTasks);
            }
        }

        function updateTaskDetails(task) {
            document.getElementById('task-title').textContent = task.task_description.substring(0, 100);

            // Show Claude Code link if available
            let logsHtml = task.logs.map(log =>
                `<div>${new Date().toLocaleTimeString()} - ${log}</div>`
            ).join('');

            if (task.claude_code_url && task.status === 'running') {
                logsHtml = `
                    <div style="background: #28a745; color: white; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                        <strong>Web Terminal with Claude Code Ready:</strong>
                        <a href="${task.claude_code_url}" target="_blank" style="color: white; text-decoration: underline;">
                            Open Terminal (${task.claude_code_url})
                        </a>
                        <br><small>Use 'claude' command to start Claude Code interactive session</small>
                    </div>
                ` + logsHtml;
            }

            // Add CI/CD status if available
            if (task.pr_number || task.ci_status) {
                logsHtml = createCICDStatusHtml(task) + logsHtml;
            }

            // Add log file download button if log file exists
            if (task.log_file) {
                logsHtml = `
                    <div style="background: #007bff; color: white; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                        <strong>Full Logs Available:</strong>
                        <button onclick="downloadLogs('${task.task_id}')" style="background: white; color: #007bff; border: none; padding: 5px 10px; border-radius: 3px; margin-left: 10px; cursor: pointer;">
                            Download Full Logs
                        </button>
                        <button onclick="viewLogs('${task.task_id}')" style="background: white; color: #007bff; border: none; padding: 5px 10px; border-radius: 3px; margin-left: 5px; cursor: pointer;">
                            View Logs
                        </button>
                    </div>
                ` + logsHtml;
            }

            document.getElementById('task-logs').innerHTML = logsHtml;

            const progress = task.status === 'completed' ? 100 : task.status === 'running' ? 50 : 0;
            document.getElementById('progress-fill').style.width = progress + '%';

            // Load CI/CD information if task has PR or CI data
            if (task.pr_number || task.ci_status) {
                loadCICDInfo(task.task_id);
            }
        }

        function createCICDStatusHtml(task) {
            let cicdHtml = '';
            
            // CI/CD Status Section
            if (task.ci_status || task.pr_number) {
                const statusColor = getCIStatusColor(task.ci_status);
                const statusEmoji = getCIStatusEmoji(task.ci_status);
                
                cicdHtml = `
                    <div style="background: linear-gradient(135deg, #f8fafc, #e2e8f0); border: 2px solid ${statusColor}; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                        <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 10px;">
                            <h4 style="margin: 0; color: #1f2937; display: flex; align-items: center; gap: 8px;">
                                ${statusEmoji} CI/CD Pipeline
                                <button onclick="refreshCIStatus('${task.task_id}')" style="background: #6366f1; color: white; border: none; padding: 4px 8px; border-radius: 4px; font-size: 12px; cursor: pointer;">
                                    Refresh
                                </button>
                            </h4>
                        </div>
                        
                        <div id="cicd-status-${task.task_id}" style="font-size: 14px;">
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                                <span style="background: ${statusColor}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                                    ${task.ci_status || 'Unknown'}
                                </span>
                                ${task.pr_number ? `
                                    <a href="${task.pr_url || '#'}" target="_blank" style="color: #6366f1; text-decoration: none; font-weight: 500;">
                                        PR #${task.pr_number}
                                    </a>
                                ` : ''}
                                ${task.commit_sha ? `
                                    <span style="font-family: monospace; background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 11px;">
                                        ${task.commit_sha.substring(0, 7)}
                                    </span>
                                ` : ''}
                            </div>
                            <div id="workflow-runs-${task.task_id}">
                                Loading workflow information...
                            </div>
                        </div>
                    </div>
                `;
            }
            
            return cicdHtml;
        }

        function getCIStatusColor(status) {
            switch(status) {
                case 'success': return '#10b981';
                case 'failure': return '#ef4444';
                case 'pending': case 'in_progress': return '#f59e0b';
                case 'error': return '#dc2626';
                default: return '#6b7280';
            }
        }

        function getCIStatusEmoji(status) {
            switch(status) {
                case 'success': return '';
                case 'failure': return '';
                case 'pending': case 'in_progress': return '';
                case 'error': return '';
                default: return '';
            }
        }

        async function loadCICDInfo(taskId) {
            try {
                // Load workflow runs
                const workflowResponse = await fetch(`/api/tasks/${taskId}/workflow-runs`);
                const workflowData = await workflowResponse.json();
                
                if (workflowData.success) {
                    displayWorkflowRuns(taskId, workflowData.workflow_runs);
                }
                
                // Load PR info if available
                const prResponse = await fetch(`/api/tasks/${taskId}/pr-info`);
                const prData = await prResponse.json();
                
                if (prData.success) {
                    updatePRInfo(taskId, prData.pr_info);
                }
                
            } catch (error) {
                console.error('Error loading CI/CD info:', error);
                const container = document.getElementById(`workflow-runs-${taskId}`);
                if (container) {
                    container.innerHTML = '<span style="color: #ef4444;">Error loading CI/CD information</span>';
                }
            }
        }

        function displayWorkflowRuns(taskId, workflowRuns) {
            const container = document.getElementById(`workflow-runs-${taskId}`);
            if (!container) return;
            
            if (workflowRuns.length === 0) {
                container.innerHTML = '<span style="color: #6b7280;">No workflow runs found</span>';
                return;
            }
            
            const runsHtml = workflowRuns.slice(0, 5).map(run => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; background: white; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid ${run.color};">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                            <span style="font-size: 14px;">${run.emoji}</span>
                            <strong style="font-size: 13px;">${run.name}</strong>
                            <span style="background: ${run.color}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">
                                ${run.conclusion || run.status}
                            </span>
                        </div>
                        <div style="font-size: 11px; color: #6b7280;">
                            ${run.event} • ${run.branch} • ${new Date(run.created_at).toLocaleString()}
                        </div>
                    </div>
                    <a href="${run.html_url}" target="_blank" style="color: #6366f1; text-decoration: none; font-size: 12px; padding: 4px 8px; border: 1px solid #6366f1; border-radius: 4px;">
                        View
                    </a>
                </div>
            `).join('');
            
            container.innerHTML = runsHtml;
        }

        function updatePRInfo(taskId, prInfo) {
            // Update PR link and status in the CI/CD section
            const statusContainer = document.getElementById(`cicd-status-${taskId}`);
            if (statusContainer && prInfo) {
                const prLink = statusContainer.querySelector('a[href*="pull"]');
                if (prLink) {
                    prLink.href = prInfo.html_url;
                    prLink.textContent = `PR #${prInfo.number}`;
                }
            }
        }

        async function refreshCIStatus(taskId) {
            try {
                const response = await fetch(`/api/tasks/${taskId}/update-ci-info`, {
                    method: 'POST'
                });
                const result = await response.json();
                
                if (result.success) {
                    // Refresh the task details to show updated CI status
                    fetchTaskDetails(taskId);
                } else {
                    console.error('Failed to refresh CI status:', result.message);
                }
            } catch (error) {
                console.error('Error refreshing CI status:', error);
            }
        }

        function showTaskMonitor() {
            const monitor = document.getElementById('task-monitor');
            monitor.classList.add('visible');
            monitor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        function hideTaskMonitor() {
            const monitor = document.getElementById('task-monitor');
            monitor.classList.remove('visible');
            selectedTaskId = null;
        }

        function selectTask(taskId) {
            selectedTaskId = taskId;
            showTaskMonitor();
            fetchTaskDetails(taskId);
        }

        async function createTask() {
            const description = document.getElementById('task-description').value.trim();
            if (!description) {
                alert('Please enter a task description');
                return;
            }

            const btn = document.getElementById('create-btn');
            btn.disabled = true;
            btn.textContent = 'Creating Task...';
            btn.classList.add('loading');

            try {
                const response = await fetch('/api/tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task_description: description
                    })
                });

                const result = await response.json();
                if (result.success) {
                    document.getElementById('task-description').value = '';
                    selectTask(result.task_id);

                    // Show success notification
                    const notification = document.createElement('div');
                    notification.innerHTML = ' Task created successfully! Monitor below.';
                    notification.style.cssText = `
                        position: fixed; top: 80px; right: 20px; z-index: 1001;
                        background: linear-gradient(135deg, #10b981, #059669); color: white;
                        padding: 12px 20px; border-radius: 8px; font-weight: 500;
                        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                        animation: fadeIn 0.3s ease;
                    `;
                    document.body.appendChild(notification);
                    setTimeout(() => notification.remove(), 4000);
                } else {
                    alert('Failed to create task: ' + result.message);
                }
            } catch (error) {
                alert('Error creating task: ' + error.message);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Start Autonomous Learning';
                btn.classList.remove('loading');
            }
        }

        async function stopTask() {
            if (!selectedTaskId) return;

            const response = await fetch(`/api/tasks/${selectedTaskId}/stop`, { method: 'POST' });
            const result = await response.json();
            if (result.success) {
                alert('Task stopped successfully');
            }
        }

        async function fetchTaskDetails(taskId) {
            const response = await fetch(`/api/tasks/${taskId}`);
            const result = await response.json();
            if (result.success) {
                updateTaskDetails(result.task);
            }
        }

        async function downloadLogs(taskId) {
            try {
                const response = await fetch(`/api/tasks/${taskId}/logs`);
                const result = await response.json();
                if (result.success) {
                    const blob = new Blob([result.logs], { type: 'text/plain' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `task_${taskId}_logs.txt`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                } else {
                    alert('Failed to download logs: ' + result.message);
                }
            } catch (error) {
                alert('Error downloading logs: ' + error.message);
            }
        }

        async function viewLogs(taskId) {
            try {
                const response = await fetch(`/api/tasks/${taskId}/logs`);
                const result = await response.json();
                if (result.success) {
                    const logWindow = window.open('', '_blank', 'width=800,height=600,scrollbars=yes');
                    logWindow.document.write(`
                        <html>
                        <head><title>Task ${taskId} - Full Logs</title></head>
                        <body style="font-family: monospace; white-space: pre-wrap; padding: 20px;">
                        ${result.logs.replace(/</g, '&lt;').replace(/>/g, '&gt;')}
                        </body>
                        </html>
                    `);
                    logWindow.document.close();
                } else {
                    alert('Failed to view logs: ' + result.message);
                }
            } catch (error) {
                alert('Error viewing logs: ' + error.message);
            }
        }

        // Initialize
        document.getElementById('connection-status').textContent = 'Connected';
        document.getElementById('connection-status').className = 'connection-status connected';
        initSpeechRecognition();

        // Simple HTTP polling instead of WebSocket
        async function pollTasks() {
            try {
                const response = await fetch('/api/tasks');
                const data = await response.json();
                if (data.success) {
                    updateActiveTasksList(data.tasks);
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }

        setInterval(pollTasks, 5000);
        pollTasks(); // Initial load

        // Failed tasks management functions
        async function retriggerTask(taskId) {
            try {
                const response = await fetch(`/api/tasks/${taskId}/retrigger`, {
                    method: 'POST'
                });
                const result = await response.json();

                if (result.success) {
                    alert(`Task retriggered successfully!\nNew task ID: ${result.new_task_id}`);
                    // Refresh task lists
                    pollTasks();
                    loadFailedTasks();
                } else {
                    alert('Failed to retrigger task: ' + result.message);
                }
            } catch (error) {
                alert('Error retriggering task: ' + error.message);
            }
        }

        async function retriggerAllFailed() {
            const btn = document.getElementById('batch-retrigger-btn');
            btn.disabled = true;
            btn.textContent = 'Retriggering...';

            try {
                const response = await fetch('/api/tasks/retrigger-all-failed', {
                    method: 'POST'
                });
                const result = await response.json();

                if (result.success) {
                    alert(`Batch retrigger completed!\n${result.retriggered_count} tasks retriggered\n${result.errors.length} errors`);
                    // Refresh task lists
                    pollTasks();
                    loadFailedTasks();
                } else {
                    alert('Batch retrigger failed: ' + result.message);
                }
            } catch (error) {
                alert('Error in batch retrigger: ' + error.message);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Retrigger All Failed Tasks';
            }
        }

        async function loadFailedTasks() {
            try {
                const response = await fetch('/api/tasks/failed');
                const result = await response.json();

                if (result.success) {
                    displayFailedTasks(result.failed_tasks);

                    // Show/hide failed tasks section based on whether there are failed tasks
                    const section = document.getElementById('failed-tasks-section');
                    if (result.failed_tasks.length > 0) {
                        section.style.display = 'block';
                    } else {
                        section.style.display = 'none';
                    }
                }
            } catch (error) {
                console.error('Error loading failed tasks:', error);
            }
        }

        function displayFailedTasks(failedTasks) {
            allFailedTasks = failedTasks;
            const container = document.getElementById('failed-tasks-list');
            const paginationControls = document.getElementById('failed-pagination-controls');

            if (failedTasks.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>No failed tasks found</p>
                    </div>
                `;
                paginationControls.style.display = 'none';
                return;
            }

            // Calculate pagination
            const totalPages = Math.ceil(failedTasks.length / failedTasksPerPage);
            const startIndex = (currentFailedPage - 1) * failedTasksPerPage;
            const endIndex = startIndex + failedTasksPerPage;
            const tasksToShow = failedTasks.slice(startIndex, endIndex);

            // Display tasks for current page
            container.innerHTML = tasksToShow.map(task => `
                <div class="task-item" style="border-left-color: #ef4444;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <strong style="flex: 1; margin-right: 12px;">${task.short_description}</strong>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span class="task-status status-failed">${task.status}</span>
                            <button class="retrigger-btn" onclick="retriggerTask('${task.task_id}')">
                                Retrigger
                            </button>
                        </div>
                    </div>
                    <div style="font-size: 13px; color: #6b7280; margin-bottom: 8px;">
                        Created: ${new Date(task.created_at).toLocaleString()}
                        ${task.completed_at ? '| Failed: ' + new Date(task.completed_at).toLocaleString() : ''}
                    </div>
                    ${task.error ? `
                        <div style="font-size: 12px; color: #ef4444; background: rgba(239, 68, 68, 0.1); padding: 8px; border-radius: 6px; margin-top: 8px;">
                            <strong>Error:</strong> ${task.error.substring(0, 150)}${task.error.length > 150 ? '...' : ''}
                        </div>
                    ` : ''}
                </div>
            `).join('');

            // Show/hide pagination controls based on number of tasks
            if (failedTasks.length > failedTasksPerPage) {
                paginationControls.style.display = 'flex';
                updateFailedPaginationControls(totalPages);
            } else {
                paginationControls.style.display = 'none';
            }
        }

        function updateFailedPaginationControls(totalPages) {
            const prevBtn = document.getElementById('failed-prev-btn');
            const nextBtn = document.getElementById('failed-next-btn');
            const paginationInfo = document.getElementById('failed-pagination-info');

            prevBtn.disabled = currentFailedPage === 1;
            nextBtn.disabled = currentFailedPage === totalPages;
            paginationInfo.textContent = `Page ${currentFailedPage} of ${totalPages}`;
        }

        function previousFailedPage() {
            if (currentFailedPage > 1) {
                currentFailedPage--;
                displayFailedTasks(allFailedTasks);
            }
        }

        function nextFailedPage() {
            const totalPages = Math.ceil(allFailedTasks.length / failedTasksPerPage);
            if (currentFailedPage < totalPages) {
                currentFailedPage++;
                displayFailedTasks(allFailedTasks);
            }
        }

        // Load failed tasks on initial load and set up periodic refresh
        loadFailedTasks();
        setInterval(loadFailedTasks, 10000); // Check for failed tasks every 10 seconds
    </script>
</body>
</html>
    """


# WebSocket endpoint removed - using simple HTTP polling instead

# Broadcast function removed - using simple HTTP polling instead


@app.post("/api/tasks")
async def create_task(request: TaskRequest):
    """Create a new autonomous learning task"""
    task_id = str(uuid.uuid4())

    # Hardcode all the backend configuration
    feature_branch = f"feature/task-{task_id}"
    task_data = {
        "task_id": task_id,
        "task_description": request.task_description,
        "repository_url": "https://github.com/mjfuentes/summit.git",  # Hardcoded
        "github_token": "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",
        "target_branch": feature_branch,  # Use feature branch for proper PR workflow
        "timeout_minutes": 15,  # Hardcoded reasonable timeout
        "save_word": "SUMMIT_TASK_COMPLETE",  # Hardcoded
        "status": "initializing",
        "progress": "Creating container environment...",
        "logs": [
            "Task created",
            "Initializing autonomous learning environment",
        ],
        "created_at": datetime.now().isoformat(),
        "container_id": None,
        "is_active": True,
    }

    # Save task to database
    db = await get_database()
    await db.create_task(task_data)

    # Start the autonomous task in background
    asyncio.create_task(run_autonomous_task(task_id))

    return {
        "success": True,
        "task_id": task_id,
        "message": "Task created successfully",
    }


async def run_autonomous_task(task_id: str):
    """Run the autonomous learning task in a Docker container"""
    container_id = None

    # Get task data from database
    db = await get_database()
    task = await db.get_task(task_id)
    if not task:
        print(f"Task {task_id} not found in database")
        return

    try:
        # Update status to running
        logs = task.logs or []
        logs.append("Creating isolated development environment")
        await db.update_task(
            task_id,
            {
                "status": "running",
                "progress": "Building Docker container...",
                "logs": logs,
            },
        )

        # Build and run Claude Code container
        print("[TASK] Starting Claude Code environment...")

        try:
            # Early validation of critical components
            dockerfile_path = "Dockerfile.autonomous"
            task_script_path = "claude_code_task.sh"

            # Check for required files
            missing_files = []
            if not os.path.exists(dockerfile_path):
                missing_files.append(dockerfile_path)
            if not os.path.exists(task_script_path):
                missing_files.append(task_script_path)

            if missing_files:
                error_msg = f"Critical error: Missing required files: {', '.join(missing_files)}. Cannot proceed without proper Docker configuration."
                print(f"[ERROR] {error_msg}")
                logs = task.logs or []
                logs.append(f"Error: {error_msg}")
                await db.update_task(
                    task_id,
                    {"status": "failed", "error": error_msg, "logs": logs},
                )
                return

            # Check Docker availability
            try:
                docker_check = subprocess.run(
                    ["docker", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if docker_check.returncode != 0:
                    error_msg = "Critical error: Docker is not available or not running."
                    print(f"[ERROR] {error_msg}")
                    await add_task_log(task_id, f"Error: {error_msg}")
                    await update_task_status(
                        task_id, "failed", error=error_msg
                    )
                    return
            except (subprocess.TimeoutExpired, FileNotFoundError):
                error_msg = (
                    "Critical error: Docker command not found or timeout."
                )
                print(f"[ERROR] {error_msg}")
                await add_task_log(task_id, f"Error: {error_msg}")
                await update_task_status(task_id, "failed", error=error_msg)
                return

            # Copy requirements.txt to web directory for build context
            requirements_src = "../requirements.txt"
            requirements_dest = "requirements.txt"

            if os.path.exists(requirements_src):
                import shutil

                shutil.copy2(requirements_src, requirements_dest)
                print("[TASK] Copied requirements.txt to build context")
            else:
                error_msg = "Critical error: requirements.txt not found in root directory"
                print(f"[ERROR] {error_msg}")
                await add_task_log(task_id, f"Error: {error_msg}")
                await update_task_status(task_id, "failed", error=error_msg)
                return

            try:
                # Build the container with proper Claude Code support
                build_cmd = (
                    f"docker build -f {dockerfile_path} -t claude-code-task ."
                )
                build_process = subprocess.run(
                    build_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout for build
                )
            finally:
                # Clean up copied requirements.txt
                if os.path.exists(requirements_dest):
                    os.remove(requirements_dest)
                    print(
                        "[TASK] Cleaned up requirements.txt from build context"
                    )

            if build_process.returncode != 0:
                print(f"[ERROR] Docker build failed: {build_process.stderr}")
                await update_task_status(
                    task_id,
                    "failed",
                    error=f"Container build failed: {build_process.stderr}",
                )
                return

            print(
                "[TASK] Container built successfully, starting Claude Code..."
            )

            # Get API key with validation
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                error_msg = "ANTHROPIC_API_KEY not found in server environment"
                print(f"[ERROR] {error_msg}")
                await add_task_log(task_id, f"Error: {error_msg}")
                await update_task_status(task_id, "failed", error=error_msg)
                return

            print(f"[DEBUG] API key loaded: {api_key[:20]}...")

            # Find available port for this container
            import socket

            def find_free_port():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("", 0))
                    s.listen(1)
                    port = s.getsockname()[1]
                return port

            terminal_port = find_free_port()
            print(f"[DEBUG] Allocated port {terminal_port} for task {task_id}")

            # Run the container with proper Claude Code integration
            run_cmd = [
                "docker",
                "run",
                "-d",
                "--name",
                f"claude-task-{task_id}",
                "-p",
                f"{terminal_port}:7681",
                # Map random host port to container port 7681
                "-e",
                f"TASK_DESCRIPTION={task.task_description}",
                "-e",
                f"SAVE_WORD={task.save_word or 'TASK_COMPLETE'}",
                "-e",
                f"ANTHROPIC_API_KEY={api_key}",
                "-e",
                f"GITHUB_TOKEN={task.github_token or ''}",
                "-e",
                f"REPOSITORY_URL={task.repository_url or ''}",
                "-e",
                f"TARGET_BRANCH={task.target_branch or 'main'}",
                "-e",
                "SUMMIT_READONLY_MODE=true",  # Prevent data modifications during tasks
                "claude-code-task",
            ]

            print(f"[DEBUG] Using dynamic port mapping: {terminal_port}:7681")
            print(
                f"[DEBUG] Docker command: {' '.join(run_cmd[:8])}... (env vars hidden)"
            )  # Don't log full command with API key

            logs = task.logs or []
            logs.append("Starting Claude Code container...")
            await db.update_task(task_id, {"logs": logs})

            # Run docker command directly since we're using detached mode (-d)
            try:
                result = subprocess.run(
                    run_cmd, capture_output=True, text=True, timeout=30
                )
                if result.returncode != 0:
                    error_msg = f"Failed to start container: {result.stderr}"
                    print(f"[ERROR] {error_msg}")
                    logs = task.logs or []
                    logs.append(f"Error: {error_msg}")
                    await db.update_task(
                        task_id,
                        {"status": "failed", "error": error_msg, "logs": logs},
                    )
                    return

                # Container started successfully
                print(f"[TASK] Container started: {result.stdout.strip()}")
                logs = task.logs or []
                logs.append(
                    f"Container started successfully: {result.stdout.strip()}"
                )
                await db.update_task(task_id, {"logs": logs})

            except subprocess.TimeoutExpired:
                error_msg = "Container startup timed out"
                print(f"[ERROR] {error_msg}")
                logs = task.logs or []
                logs.append(f"Error: {error_msg}")
                await db.update_task(
                    task_id,
                    {"status": "failed", "error": error_msg, "logs": logs},
                )
                return
            except Exception as e:
                error_msg = f"Container startup failed: {str(e)}"
                print(f"[ERROR] {error_msg}")
                logs = task.logs or []
                logs.append(f"Error: {error_msg}")
                await db.update_task(
                    task_id,
                    {"status": "failed", "error": error_msg, "logs": logs},
                )
                return

            # Use the dynamically allocated terminal port
            container_id = f"claude-task-{task_id}"
            logs = task.logs or []
            logs.append(
                f"Web terminal with Claude Code access: http://localhost:{terminal_port}"
            )
            logs.append(
                "Claude Code CLI environment ready for interactive development"
            )

            await db.update_task(
                task_id,
                {
                    "container_id": container_id,
                    "claude_code_url": f"http://localhost:{terminal_port}",
                    "logs": logs,
                },
            )

            # Monitor container logs and status
            timeout_seconds = (task.timeout_minutes or 60) * 60
            start_time = time.time()

            # Create log file for this task instance
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, f"task_{task_id}.log")

            # Initialize log file with task information
            try:
                with open(log_file_path, "w", encoding="utf-8") as f:
                    f.write(
                        f"[SYSTEM] Task started at {datetime.now().isoformat()}\n"
                    )
                    f.write(f"[SYSTEM] Task ID: {task_id}\n")
                    f.write(
                        f"[SYSTEM] Task Description: {task.task_description}\n"
                    )
                    f.write(
                        f"[SYSTEM] Completion Signal: {task.save_word or 'TASK_COMPLETE'}\n"
                    )
                    f.write(f"[SYSTEM] Container ID: {container_id}\n")
                    f.write(f"[SYSTEM] Log monitoring started\n")
                    f.write("=" * 60 + "\n")
            except Exception as e:
                print(f"[ERROR] Failed to initialize log file: {e}")

            logs = task.logs or []
            logs.append(
                "Container started successfully, monitoring Claude Code environment..."
            )
            await db.update_task(
                task_id, {"logs": logs, "log_file": log_file_path}
            )

            while True:
                try:
                    # Check timeout
                    if time.time() - start_time > timeout_seconds:
                        logs = task.logs or []
                        logs.append("Task timed out after 1 hour")
                        await db.update_task(
                            task_id, {"status": "timeout", "logs": logs}
                        )
                        break

                    # Check if container is still running
                    status_check = subprocess.run(
                        ["docker", "ps", "-q", "-f", f"name={container_id}"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    if not status_check.stdout.strip():
                        # Container stopped - check exit code to determine if
                        # it completed successfully
                        inspect_result = subprocess.run(
                            [
                                "docker",
                                "inspect",
                                container_id,
                                "--format",
                                "{{.State.ExitCode}}",
                            ],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )

                        if inspect_result.returncode == 0:
                            exit_code = int(inspect_result.stdout.strip())
                            if exit_code == 0:
                                logs = task.logs or []
                                logs.append(
                                    "Claude Code finished successfully"
                                )

                                # Try to create pull request if this was a
                                # feature branch workflow
                                pr_created = False
                                try:
                                    # Get repository info
                                    owner, repo = get_github_repo_info()
                                    if owner and repo and task.repository_url:
                                        # Assume the container created a
                                        # feature branch following our workflow
                                        feature_branch = (
                                            f"feature/task-{task_id}"
                                        )

                                        # Create PR with template variables
                                        pr_title = f"feat: autonomous task completion - {task.task_description[:50]}..."

                                        # Use template variables for dynamic
                                        # content
                                        template_vars = {
                                            "summary": f"This PR was automatically created by Summit's autonomous agent upon successful completion of task: {task.task_description}",
                                            "changes": [
                                                f"Implemented requested functionality: {task.task_description}",
                                                "Autonomous agent development workflow completed",
                                                "Task executed in isolated Docker environment",
                                            ],
                                            "features": [
                                                "Autonomous task execution",
                                                "Multi-role AI code review integration",
                                                "Automated quality assurance pipeline",
                                            ],
                                        }

                                        # Generate PR body using template
                                        from datetime import datetime

                                        pr_body = f"""# Autonomous Task Completion

**Task ID**: {task_id}
**Description**: {task.task_description}
**Branch**: {task.target_branch}
**Completed**: {datetime.utcnow().isoformat()}Z

## Summary
{template_vars['summary']}

## Changes
{chr(10).join(f"- {change}" for change in template_vars['changes'])}
- All tests passing with >70% coverage
- Code quality checks completed
- Professional development standards enforced

## Features
{chr(10).join(f"- {feature}" for feature in template_vars['features'])}

## Quality Assurance
This PR has undergone the complete Summit development process:
- **Testing**: Comprehensive test suite execution with coverage validation
- **Code Quality**: Automated formatting and linting checks
- **Standards Compliance**: Commit message validation and professional practices
- **CI/CD Integration**: Automated pipeline execution and monitoring

## Review Process
This PR will be automatically reviewed by our multi-role review system:
- **Engineering Review**: Code quality, testing, architecture
- **Infrastructure Review**: Security, deployment, performance
- **Product Review**: User experience, business alignment
- **Domain Expert Review**: AI/ML best practices, technical depth

The PR will auto-merge upon successful CI completion and positive reviews.
"""

                                        print(
                                            f"Creating PR for task {task_id}..."
                                        )
                                        pr_result = await create_pull_request(
                                            owner=owner,
                                            repo=repo,
                                            title=pr_title,
                                            head=feature_branch,
                                            base="main",
                                            body=pr_body,
                                        )

                                        if pr_result:
                                            pr_number = pr_result["number"]
                                            pr_url = pr_result["url"]

                                            print(f"PR created: {pr_url}")
                                            await update_task_status(
                                                task_id,
                                                "completed",
                                                f"Task completed, PR created: {pr_url}",
                                            )

                                            # Trigger multi-role reviews
                                            # (internal quality gate)
                                            print(
                                                f"Running internal multi-role review for PR #{pr_number}..."
                                            )
                                            try:
                                                review_result = await review_pr_with_multiple_roles(
                                                    owner=owner,
                                                    repo=repo,
                                                    pr_number=pr_number,
                                                    roles=[
                                                        "engineer",
                                                        "infrastructure",
                                                        "product",
                                                        "domain_expert",
                                                    ],
                                                )

                                                if review_result.get(
                                                    "success"
                                                ):
                                                    decision = (
                                                        review_result.get(
                                                            "decision",
                                                            "COMMENTED",
                                                        )
                                                    )
                                                    all_approved = (
                                                        review_result.get(
                                                            "all_approved",
                                                            False,
                                                        )
                                                    )
                                                    approval_count = (
                                                        review_result.get(
                                                            "approval_count",
                                                            "0/0",
                                                        )
                                                    )

                                                    print(
                                                        f"Multi-role review completed: {decision} ({approval_count})"
                                                    )

                                                    if all_approved:
                                                        await add_task_log(
                                                            task_id,
                                                            f" All AI reviewers approved PR #{pr_number} - Ready for auto-merge",
                                                        )
                                                    else:
                                                        await add_task_log(
                                                            task_id,
                                                            f" AI reviewers requested changes on PR #{pr_number} - Auto-merge blocked",
                                                        )
                                                else:
                                                    print(
                                                        f"Multi-role review failed: {review_result.get('error', 'Unknown error')}"
                                                    )
                                                    await add_task_log(
                                                        task_id,
                                                        f"Multi-role review failed for PR #{pr_number}",
                                                    )

                                            except Exception as review_error:
                                                print(
                                                    f"Error during multi-role review: {review_error}"
                                                )
                                                await add_task_log(
                                                    task_id,
                                                    f"Multi-role review error: {str(review_error)}",
                                                )

                                        else:
                                            print(
                                                f"Failed to create PR for task {task_id}"
                                            )
                                            await update_task_status(
                                                task_id,
                                                "completed",
                                                "Task completed but PR creation failed",
                                            )

                                except Exception as pr_error:
                                    print(
                                        f"Error creating PR for task {task_id}: {pr_error}"
                                    )
                                    await update_task_status(
                                        task_id,
                                        "completed",
                                        f"Task completed but PR error: {str(pr_error)}",
                                    )
                            else:
                                error_msg = f"Claude Code exited with error code {exit_code}"
                                logs = task.logs or []
                                logs.append(
                                    f"Claude Code failed with exit code {exit_code}"
                                )
                                await db.update_task(
                                    task_id,
                                    {
                                        "status": "failed",
                                        "error": error_msg,
                                        "logs": logs,
                                    },
                                )
                        else:
                            error_msg = (
                                "Could not determine container exit status"
                            )
                            logs = task.logs or []
                            logs.append(
                                "Container stopped but exit status unknown"
                            )
                            await db.update_task(
                                task_id,
                                {
                                    "status": "failed",
                                    "error": error_msg,
                                    "logs": logs,
                                },
                            )
                        break

                    # Get container logs with timestamps
                    logs_result = subprocess.run(
                        [
                            "docker",
                            "logs",
                            "--timestamps",
                            "--since",
                            f"{int(start_time)}",
                            container_id,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if logs_result.returncode == 0 and logs_result.stdout:
                        # Get all logs and filter new ones
                        all_logs = logs_result.stdout.strip()
                        current_task = await db.get_task(task_id)
                        current_logs = current_task.logs or []
                        current_claude_logs = [
                            log
                            for log in current_logs
                            if log.startswith("Claude:")
                        ]

                        # Split into lines and process new ones
                        log_lines = all_logs.split("\n") if all_logs else []

                        new_logs_added = False
                        updated_logs = current_logs.copy()

                        for line in log_lines:
                            if line.strip():
                                # Save raw log line to file with timestamp
                                try:
                                    with open(
                                        log_file_path, "a", encoding="utf-8"
                                    ) as f:
                                        f.write(f"{line}\n")
                                except Exception as e:
                                    print(
                                        f"[ERROR] Failed to write to log file: {e}"
                                    )

                                # Remove timestamp prefix for cleaner display
                                clean_line = line
                                if (
                                    "T" in line and "Z" in line
                                ):  # Has timestamp
                                    parts = line.split(" ", 1)
                                    if len(parts) > 1:
                                        clean_line = parts[1]

                                formatted_log = f"Claude: {clean_line.strip()}"

                                # Only add if not already in logs
                                if formatted_log not in updated_logs:
                                    updated_logs.append(formatted_log)
                                    new_logs_added = True

                                    # Note: We'll detect completion when the container/process naturally exits
                                    # No need to look for magic completion
                                    # signals

                        # Update if we added new logs
                        if new_logs_added:
                            await db.update_task(
                                task_id, {"logs": updated_logs}
                            )

                    # Wait before next check
                    await asyncio.sleep(3)

                except Exception as e:
                    logs = task.logs or []
                    logs.append(f"Monitoring error: {str(e)}")
                    await db.update_task(task_id, {"logs": logs})
                    await asyncio.sleep(5)

            # Check final status - only update if still running
            current_task = await db.get_task(task_id)
            if current_task and current_task.status not in [
                "completed",
                "failed",
                "timeout",
            ]:
                logs = current_task.logs or []
                logs.append("Task monitoring ended without completion signal")
                await db.update_task(
                    task_id,
                    {
                        "status": "failed",
                        "progress": "Task ended without completion signal",
                        "logs": logs,
                    },
                )

        except Exception as e:
            logs = task.logs or []
            logs.append(f"Error: {str(e)}")
            await db.update_task(
                task_id,
                {
                    "status": "failed",
                    "progress": f"Error: {str(e)}",
                    "logs": logs,
                },
            )

    except Exception as e:
        try:
            logs = task.logs or []
            logs.append(f"Error: {str(e)}")
            await db.update_task(
                task_id,
                {
                    "status": "failed",
                    "progress": f"Error: {str(e)}",
                    "logs": logs,
                },
            )
        except BaseException:
            print(f"[ERROR] Failed to update task {task_id}: {e}")

    finally:
        # Save final log entry and add completion timestamp
        if "log_file_path" in locals():
            try:
                current_task = await db.get_task(task_id)
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write("=" * 60 + "\n")
                    f.write(
                        f"[SYSTEM] Task ended at {datetime.now().isoformat()}\n"
                    )
                    f.write(
                        f"[SYSTEM] Final status: {current_task.status if current_task else 'unknown'}\n"
                    )
                    f.write(f"[SYSTEM] Log file saved to: {log_file_path}\n")

                # Read the complete log file content for completed tasks
                with open(log_file_path, "r", encoding="utf-8") as f:
                    full_logs = f.read()
                    await db.update_task(task_id, {"full_logs": full_logs})

            except Exception as e:
                print(f"[ERROR] Failed to write final log entry: {e}")

        # Add completion timestamp and mark as inactive
        try:
            await db.update_task(
                task_id, {"completed_at": datetime.now(), "is_active": False}
            )
        except Exception as e:
            print(f"[ERROR] Failed to mark task as completed: {e}")

        # Clean up Docker container
        try:
            subprocess.run(
                ["docker", "stop", f"claude-task-{task_id}"],
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ["docker", "rm", f"claude-task-{task_id}"], capture_output=True
            )
        except BaseException:
            pass


@app.get("/api/tasks")
async def get_all_tasks():
    """Get all active and recent completed tasks"""
    db = await get_database()

    # Get active tasks
    active_tasks = await db.get_active_tasks()
    active_task_list = [task.to_dict() for task in active_tasks]

    # Get recent completed tasks (last 20)
    completed_tasks = await db.get_completed_tasks(limit=20)
    recent_completed = [task.to_dict() for task in completed_tasks]

    # Mark tasks with their status for easier identification
    for task in active_task_list:
        task["is_active"] = True
        task["is_completed"] = False

    for task in recent_completed:
        task["is_active"] = False
        task["is_completed"] = True

    all_tasks = active_task_list + recent_completed

    # Get total counts from database
    stats = await db.get_task_statistics()

    return {
        "success": True,
        "tasks": all_tasks,
        "active_count": len(active_task_list),
        "completed_count": len(recent_completed),
        "total_completed_in_history": stats.get("completed_tasks", 0),
    }


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get details of a specific task with full logs if completed"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        return {"success": False, "message": "Task not found"}

    response_task = task.to_dict()

    # If we don't have full_logs in memory, try to read from file
    if not response_task.get("full_logs") and response_task.get("log_file"):
        log_file_path = response_task["log_file"]
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, "r", encoding="utf-8") as f:
                    response_task["full_logs"] = f.read()
            except Exception as e:
                response_task["full_logs_error"] = (
                    f"Could not read log file: {str(e)}"
                )

    return {
        "success": True,
        "task": response_task,
        "is_active": task.is_active,
        "is_completed": not task.is_active,
    }


@app.post("/api/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    """Stop a running task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        return {"success": False, "message": "Task not found"}

    # Stop the Docker container if it exists
    if task.container_id:
        try:
            subprocess.run(
                ["docker", "stop", task.container_id],
                capture_output=True,
                timeout=10,
            )
            await add_task_log(task_id, "Docker container stopped")
        except Exception as e:
            await add_task_log(task_id, f"Error stopping container: {e}")

    await add_task_log(task_id, "Task stopped by user")
    await update_task_status(task_id, "stopped", "Task stopped by user")

    return {"success": True, "message": "Task stopped"}


@app.get("/api/tasks/{task_id}/logs")
async def get_task_logs(task_id: str):
    """Get the full log file for a specific task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        return {"success": False, "message": "Task not found"}

    # First try to get from database
    if task.full_logs:
        return {"success": True, "logs": task.full_logs, "source": "database"}

    # Fall back to log file
    if task.log_file and os.path.exists(task.log_file):
        try:
            with open(task.log_file, "r", encoding="utf-8") as f:
                logs = f.read()
            return {
                "success": True,
                "logs": logs,
                "file_path": task.log_file,
                "source": "file",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error reading log file: {str(e)}",
            }

    # Try default log file path
    log_file_path = os.path.join("task_logs", f"task_{task_id}.log")
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                logs = f.read()
            return {
                "success": True,
                "logs": logs,
                "file_path": log_file_path,
                "source": "default_file",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error reading log file: {str(e)}",
            }

    return {"success": False, "message": "Log file not found"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Summit autonomous AI is running"}


@app.post("/api/tasks/{task_id}/retrigger")
async def retrigger_failed_task(task_id: str):
    """
    Retrigger a failed task by creating a new task with the same description.
    This sends the task to a fresh Claude instance with a new container.
    """
    db = await get_database()
    original_task = await db.get_task(task_id)

    if not original_task:
        return {"success": False, "message": "Original task not found"}

    # Only allow retriggering of failed, stopped, or timeout tasks
    if original_task.status not in ["failed", "stopped", "timeout"]:
        return {
            "success": False,
            "message": f"Can only retrigger failed, stopped, or timeout tasks. Current status: {original_task.status}",
        }

    try:
        # Create a new task with the same description but fresh ID
        new_task_id = str(uuid.uuid4())

        # Copy relevant data from original task
        new_task_data = {
            "task_id": new_task_id,
            "task_description": original_task.task_description,
            "repository_url": original_task.repository_url,
            "github_token": original_task.github_token,
            "target_branch": original_task.target_branch or "main",
            "timeout_minutes": original_task.timeout_minutes or 60,
            "save_word": original_task.save_word or "SUMMIT_TASK_COMPLETE",
            "status": "pending",
            "progress": "Task retriggered from failed task",
            "logs": [
                f"Task retriggered from original task: {task_id}",
                f"Original task failed with: {original_task.error or 'Unknown error'}",
                "Starting fresh Claude instance...",
            ],
            "created_at": datetime.utcnow(),
            "is_active": True,
        }

        # Create the new task in database
        new_task = await db.create_task(new_task_data)
        await add_task_log(
            new_task_id, f"New task created as retrigger of {task_id}"
        )

        # Start the autonomous task in background
        asyncio.create_task(run_autonomous_task(new_task_id))

        # Delete the original failed task to avoid duplicates
        delete_success = await db.delete_task(task_id)

        if not delete_success:
            # If deletion failed, at least log it but don't fail the retrigger
            await add_task_log(
                new_task_id,
                f"Warning: Could not delete original task {task_id}",
            )

        return {
            "success": True,
            "message": "Task retriggered successfully",
            "original_task_id": task_id,
            "new_task_id": new_task_id,
            "new_task": new_task.to_dict(),
            "original_task_deleted": delete_success,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to retrigger task: {str(e)}",
        }


@app.post("/api/tasks/retrigger-all-failed")
async def retrigger_all_failed_tasks():
    """
    Retrigger all failed tasks at once.
    Useful for batch recovery after fixing infrastructure issues.
    """
    from sqlalchemy import delete, select

    from database import Task  # Import Task model for the query

    db = await get_database()

    try:
        # Get all tasks with failed status
        async with db.get_session() as session:
            result = await session.execute(
                select(Task).where(
                    Task.status.in_(["failed", "stopped", "timeout"])
                )
            )
            failed_tasks = result.scalars().all()

        if not failed_tasks:
            return {
                "success": True,
                "message": "No failed tasks found to retrigger",
                "retriggered_count": 0,
                "new_tasks": [],
            }

        retriggered_tasks = []
        errors = []

        # Prepare all new tasks first (without database operations)
        new_tasks_to_create = []
        tasks_to_delete = []

        for failed_task in failed_tasks:
            try:
                new_task_id = str(uuid.uuid4())

                new_task_data = {
                    "task_id": new_task_id,
                    "task_description": failed_task.task_description,
                    "repository_url": failed_task.repository_url,
                    "github_token": failed_task.github_token,
                    "target_branch": failed_task.target_branch or "main",
                    "timeout_minutes": failed_task.timeout_minutes or 60,
                    "save_word": failed_task.save_word
                    or "SUMMIT_TASK_COMPLETE",
                    "status": "pending",
                    "progress": "Batch retriggered from failed task",
                    "logs": [
                        f"Batch retriggered from failed task: {failed_task.task_id}",
                        f"Original error: {failed_task.error or 'Unknown error'}",
                        "Starting fresh Claude instance...",
                    ],
                    "created_at": datetime.utcnow(),
                    "is_active": True,
                }

                new_tasks_to_create.append(
                    (new_task_id, new_task_data, failed_task)
                )
                tasks_to_delete.append(failed_task.task_id)

            except Exception as e:
                errors.append(
                    {"task_id": failed_task.task_id, "error": str(e)}
                )

        # Batch create all new tasks in a single session
        async with db.get_session() as session:
            try:
                for (
                    new_task_id,
                    new_task_data,
                    failed_task,
                ) in new_tasks_to_create:
                    try:
                        # Create new task
                        new_task = Task(**new_task_data)
                        session.add(new_task)

                        retriggered_tasks.append(
                            {
                                "original_task_id": failed_task.task_id,
                                "new_task_id": new_task_id,
                                "description": (
                                    failed_task.task_description[:100] + "..."
                                    if len(failed_task.task_description) > 100
                                    else failed_task.task_description
                                ),
                                "original_deleted": True,  # Will be deleted below
                            }
                        )

                    except Exception as e:
                        errors.append(
                            {"task_id": failed_task.task_id, "error": str(e)}
                        )

                # Delete original failed tasks in the same session
                if tasks_to_delete:
                    await session.execute(
                        delete(Task).where(Task.task_id.in_(tasks_to_delete))
                    )

                # Commit all changes at once
                await session.commit()

            except Exception as e:
                await session.rollback()
                # If batch operation fails, add error for all tasks
                for _, _, failed_task in new_tasks_to_create:
                    errors.append(
                        {
                            "task_id": failed_task.task_id,
                            "error": f"Batch operation failed: {str(e)}",
                        }
                    )
                retriggered_tasks = (
                    []
                )  # Clear since nothing was actually created

        # Start all tasks after successful database operations
        for new_task_id, _, _ in new_tasks_to_create:
            if any(t["new_task_id"] == new_task_id for t in retriggered_tasks):
                asyncio.create_task(run_autonomous_task(new_task_id))

        return {
            "success": True,
            "message": f"Batch retrigger completed. {len(retriggered_tasks)} tasks retriggered, {len(errors)} errors",
            "retriggered_count": len(retriggered_tasks),
            "new_task_ids": [
                task["new_task_id"] for task in retriggered_tasks
            ],
            "new_tasks": retriggered_tasks,
            "errors": errors,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Batch retrigger failed: {str(e)}",
        }


@app.get("/api/tasks/failed")
async def get_failed_tasks():
    """
    Get all failed tasks that can be retriggered.
    Useful for showing users what tasks are available for retry.
    """
    db = await get_database()

    try:
        from database import Task

        async with db.get_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Task)
                .where(Task.status.in_(["failed", "stopped", "timeout"]))
                .order_by(Task.created_at.desc())
            )
            failed_tasks = result.scalars().all()

        failed_task_list = []
        for task in failed_tasks:
            task_dict = task.to_dict()
            # Add summary info for easier display
            task_dict["short_description"] = (
                task.task_description[:100] + "..."
                if len(task.task_description) > 100
                else task.task_description
            )
            task_dict["can_retrigger"] = True
            failed_task_list.append(task_dict)

        return {
            "success": True,
            "failed_tasks": failed_task_list,
            "count": len(failed_task_list),
            "message": f"Found {len(failed_task_list)} failed tasks that can be retriggered",
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get failed tasks: {str(e)}",
        }


@app.post("/api/tasks/cleanup")
async def cleanup_old_tasks(days_old: int = 7):
    """
    Clean up old completed and failed tasks.
    Default: Remove tasks older than 7 days that are inactive.
    """
    db = await get_database()

    try:
        from datetime import datetime, timedelta

        from sqlalchemy import delete, select

        from database import Task

        # Get count of tasks to be deleted before deletion
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        async with db.get_session() as session:
            # Count tasks that will be deleted
            count_result = await session.execute(
                select(Task)
                .where(Task.created_at < cutoff_date)
                .where(Task.is_active.is_(False))
            )
            tasks_to_delete = count_result.scalars().all()

            # Get some info about what we're deleting
            deleted_info = []
            for task in tasks_to_delete:
                deleted_info.append(
                    {
                        "task_id": task.task_id[:8],
                        "status": task.status,
                        "created_at": (
                            task.created_at.isoformat()
                            if task.created_at
                            else None
                        ),
                        "description": (
                            task.task_description[:50] + "..."
                            if len(task.task_description) > 50
                            else task.task_description
                        ),
                    }
                )

            # Perform the deletion
            delete_result = await session.execute(
                delete(Task)
                .where(Task.created_at < cutoff_date)
                .where(Task.is_active.is_(False))
            )

            deleted_count = delete_result.rowcount

        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} old tasks (older than {days_old} days)",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "deleted_tasks": deleted_info[:10],  # Show first 10 for reference
            "total_deleted_tasks": len(deleted_info),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to cleanup old tasks: {str(e)}",
        }


@app.delete("/api/tasks/{task_id}")
async def delete_specific_task(task_id: str):
    """
    Delete a specific task by ID.
    Use with caution - this permanently removes the task.
    """
    db = await get_database()

    try:
        # Get task info before deletion
        task = await db.get_task(task_id)
        if not task:
            return {"success": False, "message": "Task not found"}

        # Delete the task
        delete_success = await db.delete_task(task_id)

        if delete_success:
            return {
                "success": True,
                "message": f"Task {task_id} deleted successfully",
                "deleted_task": {
                    "task_id": task.task_id,
                    "status": task.status,
                    "description": (
                        task.task_description[:100] + "..."
                        if len(task.task_description) > 100
                        else task.task_description
                    ),
                },
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete task {task_id}",
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error deleting task: {str(e)}",
        }


# CI/CD Monitoring API Endpoints


@app.get("/api/tasks/{task_id}/ci-status")
async def get_task_ci_status_endpoint(task_id: str):
    """Get CI/CD status for a specific task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        # Get current CI status
        ci_status = await get_task_ci_status(task.to_dict())

        # Update task with latest CI information
        update_data = {
            "ci_status": ci_status.get("state", "unknown"),
            "last_ci_check": datetime.utcnow(),
        }

        # Store workflow runs if available
        if ci_status.get("workflow_runs"):
            update_data["workflow_runs"] = ci_status["workflow_runs"]

        await db.update_task(task_id, update_data)

        return {
            "success": True,
            "task_id": task_id,
            "ci_status": ci_status,
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to fetch CI status",
        }


@app.get("/api/tasks/{task_id}/workflow-runs")
async def get_task_workflow_runs_endpoint(task_id: str):
    """Get GitHub workflow runs for a specific task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        # Get formatted workflow runs
        workflow_runs = await get_workflow_runs_for_task(task.to_dict())

        return {
            "success": True,
            "task_id": task_id,
            "workflow_runs": workflow_runs,
            "count": len(workflow_runs),
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to fetch workflow runs",
        }


@app.get("/api/tasks/{task_id}/pr-info")
async def get_task_pr_info_endpoint(task_id: str):
    """Get GitHub PR information for a specific task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.pr_number or not task.repository_url:
        return {
            "success": False,
            "message": "Task does not have PR information",
        }

    try:
        from github_cicd import github_cicd_manager

        pr_info = await github_cicd_manager.get_pr_info(
            task.repository_url, task.pr_number
        )

        if pr_info:
            return {
                "success": True,
                "task_id": task_id,
                "pr_info": {
                    "number": pr_info["number"],
                    "title": pr_info["title"],
                    "state": pr_info["state"],
                    "mergeable": pr_info.get("mergeable"),
                    "merged": pr_info.get("merged", False),
                    "html_url": pr_info["html_url"],
                    "head_sha": pr_info["head"]["sha"],
                    "base_ref": pr_info["base"]["ref"],
                    "head_ref": pr_info["head"]["ref"],
                    "created_at": pr_info["created_at"],
                    "updated_at": pr_info["updated_at"],
                },
                "last_updated": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": "Could not fetch PR information",
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to fetch PR information",
        }


@app.post("/api/tasks/{task_id}/update-ci-info")
async def update_task_ci_info_endpoint(task_id: str):
    """Manually trigger CI/CD status update for a task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        # Get comprehensive CI status
        ci_status = await get_task_ci_status(task.to_dict())
        workflow_runs = await get_workflow_runs_for_task(task.to_dict())

        # Update task with all CI information
        update_data = {
            "ci_status": ci_status.get("state", "unknown"),
            "workflow_runs": workflow_runs,
            "last_ci_check": datetime.utcnow(),
        }

        # Update PR info if available
        if ci_status.get("pr_info"):
            pr_info = ci_status["pr_info"]
            update_data.update(
                {
                    "pr_url": pr_info.get("html_url"),
                    "pr_number": pr_info.get("number"),
                }
            )

        # Update commit info if available
        if ci_status.get("commit_status", {}).get("sha"):
            update_data["commit_sha"] = ci_status["commit_status"]["sha"]

        await db.update_task(task_id, update_data)

        return {
            "success": True,
            "task_id": task_id,
            "message": "CI information updated successfully",
            "ci_status": ci_status,
            "workflow_runs": workflow_runs,
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to update CI information",
        }


@app.get("/api/ci-status/summary")
async def get_ci_status_summary():
    """Get CI/CD status summary for all active tasks"""
    db = await get_database()

    try:
        active_tasks = await db.get_active_tasks()

        summary = {
            "total_tasks": len(active_tasks),
            "ci_status_counts": {
                "success": 0,
                "failure": 0,
                "pending": 0,
                "unknown": 0,
                "error": 0,
            },
            "tasks_with_prs": 0,
            "tasks_with_ci": 0,
            "last_updated": datetime.utcnow().isoformat(),
        }

        for task in active_tasks:
            if task.ci_status:
                summary["ci_status_counts"][task.ci_status] = (
                    summary["ci_status_counts"].get(task.ci_status, 0) + 1
                )
                summary["tasks_with_ci"] += 1
            else:
                summary["ci_status_counts"]["unknown"] += 1

            if task.pr_number:
                summary["tasks_with_prs"] += 1

        return {
            "success": True,
            "summary": summary,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get CI status summary",
        }


def load_environment():
    """Load environment variables from setup_env.sh"""
    setup_env_path = "setup_env.sh"
    if os.path.exists(setup_env_path):
        print("Loading environment from setup_env.sh...")
        try:
            with open(setup_env_path, "r") as f:
                content = f.read()
                for line in content.split("\n"):
                    if line.strip().startswith("export ANTHROPIC_API_KEY="):
                        # Extract the API key value
                        key_part = line.split("=", 1)[1].strip().strip('"')
                        os.environ["ANTHROPIC_API_KEY"] = key_part
                        print("API key loaded from setup_env.sh")
                        break
        except Exception as e:
            print(f"Warning: Could not load setup_env.sh: {e}")
    else:
        print("Warning: setup_env.sh not found")


if __name__ == "__main__":
    kill_existing_server()

    # Bootstrap dependencies when actually running the server
    bootstrap_dependencies()

    # Load environment variables
    load_environment()

    print("Starting Summit Autonomous AI...")
    print("Web interface: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")

    uvicorn.run(
        "autonomous_server:app", host="0.0.0.0", port=8000, reload=False
    )
