#!/usr/bin/env python3
"""
Summit Autonomous Learning Server
Advanced AI task management with container orchestration
"""

import sys
import os
import subprocess
import time
import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

def kill_existing_server():
    """Kill any existing processes using port 8000"""
    try:
        result = subprocess.run(['lsof', '-ti:8000'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"Killing existing server process (PID: {pid})")
                    subprocess.run(['kill', pid], capture_output=True)
            time.sleep(1)
            print("Cleared port 8000")
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

# Add src to path for basic imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import database functionality
from database import get_database, init_database, close_database
from task_manager import (
    update_task_status, add_task_log, update_task_container_info,
    update_task_log_file, mark_task_completed, get_task_data
)

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

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Summit Autonomous AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; 
            margin: 0; 
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%); 
            min-height: 100vh; 
            color: #1f2937;
        }
        
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        
        .header { 
            text-align: center; 
            color: white; 
            margin-bottom: 40px; 
            padding: 30px 0;
        }
        .header h1 { 
            font-size: 3.5rem; 
            margin: 0; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3); 
            font-weight: 700;
            background: linear-gradient(45deg, #ffffff, #f1f5f9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .header p { 
            font-size: 1.3rem; 
            opacity: 0.95; 
            margin: 15px 0; 
            font-weight: 300;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
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
            background: rgba(255, 255, 255, 0.95); 
            padding: 30px; 
            border-radius: 20px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.1); 
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 25px 50px rgba(0,0,0,0.15); 
        }
        .card h2 { 
            color: #1f2937; 
            margin-top: 0; 
            font-size: 1.75rem; 
            font-weight: 600; 
            margin-bottom: 20px;
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
            background: linear-gradient(135deg, #6366f1, #8b5cf6); 
            color: white; 
            padding: 16px 32px; 
            border: none; 
            border-radius: 12px; 
            cursor: pointer; 
            font-size: 16px; 
            font-weight: 600; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
            width: 100%;
        }
        .btn:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4); 
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Summit Autonomous AI</h1>
            <p>Give me a coding task and I'll complete it autonomously using Claude Code in a secure container</p>
        </div>
        
        <div id="connection-status" class="connection-status disconnected">Connecting...</div>
        
        <div class="main-grid">
            <div class="card">
                <h2>Create Learning Task</h2>
                <div class="task-form">
                    <div class="voice-input">
                        <button class="voice-btn" id="voice-btn" onclick="toggleVoiceInput()">MIC</button>
                        <span class="voice-status" id="voice-status">Click to speak</span>
                    </div>
                    <textarea id="task-description" placeholder="Describe the coding task you want me to learn and complete...

Examples:
- Build a REST API for a todo application using FastAPI
- Create a React component for user authentication  
- Write a Python script to analyze CSV data and generate charts
- Fix bugs in the payment processing module
- Implement a caching layer using Redis"></textarea>
                    
                    <!-- All backend configuration is now hardcoded -->
                    
                    <button class="btn" onclick="createTask()" id="create-btn">Start Autonomous Learning</button>
                </div>
            </div>
            
            <div class="card">
                <h2>Active Tasks</h2>
                <div id="active-tasks">
                    <div class="empty-state">
                        <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></div>
                        <p>No active tasks</p>
                        <p style="font-size: 14px; margin-top: 8px;">Create a task to get started</p>
                    </div>
                </div>
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
            const container = document.getElementById('active-tasks');
            if (tasks.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></div>
                        <p>No active tasks</p>
                        <p style="font-size: 14px; margin-top: 8px;">Create a task to get started</p>
                    </div>
                `;
                hideTaskMonitor();
                return;
            }
            
            container.innerHTML = tasks.map(task => `
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
    task_data = {
        "task_id": task_id,
        "task_description": request.task_description,
        "repository_url": "https://github.com/mjfuentes/summit.git",  # Hardcoded
        "github_token": "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",
        "target_branch": "main",  # Hardcoded
        "timeout_minutes": 15,  # Hardcoded reasonable timeout
        "save_word": "SUMMIT_TASK_COMPLETE",  # Hardcoded
        "status": "initializing",
        "progress": "Creating container environment...",
        "logs": ["Task created", "Initializing autonomous learning environment"],
        "created_at": datetime.now().isoformat(),
        "container_id": None,
        "is_active": True
    }
    
    # Save task to database
    db = await get_database()
    await db.create_task(task_data)
    
    # Start the autonomous task in background
    asyncio.create_task(run_autonomous_task(task_id))
    
    return {"success": True, "task_id": task_id, "message": "Task created successfully"}

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
        await db.update_task(task_id, {
            "status": "running",
            "progress": "Building Docker container...",
            "logs": logs
        })
        
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
                await db.update_task(task_id, {
                    "status": "failed",
                    "error": error_msg,
                    "logs": logs
                })
                return
            
            # Check Docker availability
            try:
                docker_check = subprocess.run(['docker', '--version'], 
                                            capture_output=True, text=True, timeout=5)
                if docker_check.returncode != 0:
                    error_msg = "Critical error: Docker is not available or not running."
                    print(f"[ERROR] {error_msg}")
                    await add_task_log(task_id, f"Error: {error_msg}")
                    await update_task_status(task_id, "failed", error=error_msg)
                    return
            except (subprocess.TimeoutExpired, FileNotFoundError):
                error_msg = "Critical error: Docker command not found or timeout."
                print(f"[ERROR] {error_msg}")
                await add_task_log(task_id, f"Error: {error_msg}")
                await update_task_status(task_id, "failed", error=error_msg)
                return
            
            # Build the container with proper Claude Code support
            build_cmd = f"docker build -f {dockerfile_path} -t claude-code-task ."
            build_process = subprocess.run(
                build_cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=600  # 10 minute timeout for build
            )
            
            if build_process.returncode != 0:
                print(f"[ERROR] Docker build failed: {build_process.stderr}")
                await update_task_status(task_id, "failed", error=f"Container build failed: {build_process.stderr}")
                return
            
            print("[TASK] Container built successfully, starting Claude Code...")
            
            # Get API key with validation
            api_key = os.getenv('ANTHROPIC_API_KEY')
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
                    s.bind(('', 0))
                    s.listen(1)
                    port = s.getsockname()[1]
                return port
            
            terminal_port = find_free_port()
            print(f"[DEBUG] Allocated port {terminal_port} for task {task_id}")
            
            # Run the container with proper Claude Code integration
            run_cmd = [
                "docker", "run", "-d",
                "--name", f"claude-task-{task_id}",
                "-p", f"{terminal_port}:7681",  # Map random host port to container port 7681
                "-e", f"TASK_DESCRIPTION={task_data['task_description']}",
                "-e", f"SAVE_WORD={task_data['save_word']}",
                "-e", f"ANTHROPIC_API_KEY={api_key}",
                "-e", f"GITHUB_TOKEN={task_data.get('github_token', '')}",
                "-e", f"REPOSITORY_URL={task_data.get('repository_url', '')}",
                "-e", f"TARGET_BRANCH={task_data.get('target_branch', 'main')}",
                "-e", "SUMMIT_READONLY_MODE=true",  # Prevent knowledge base modifications
                "claude-code-task"
            ]
            
            print(f"[DEBUG] Using dynamic port mapping: {terminal_port}:7681")
            print(f"[DEBUG] Docker command: {' '.join(run_cmd[:8])}... (env vars hidden)")  # Don't log full command with API key
            
            task_data["logs"].append("Starting Claude Code container...")
            
            # Run docker command directly since we're using detached mode (-d)
            try:
                result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    error_msg = f"Failed to start container: {result.stderr}"
                    print(f"[ERROR] {error_msg}")
                    task_data["status"] = "failed"
                    task_data["error"] = error_msg
                    task_data["logs"].append(f"Error: {error_msg}")
                    return
                    
                # Container started successfully
                print(f"[TASK] Container started: {result.stdout.strip()}")
                task_data["logs"].append(f"Container started successfully: {result.stdout.strip()}")
                
            except subprocess.TimeoutExpired:
                error_msg = "Container startup timed out"
                print(f"[ERROR] {error_msg}")
                task_data["status"] = "failed"
                task_data["error"] = error_msg
                task_data["logs"].append(f"Error: {error_msg}")
                return
            except Exception as e:
                error_msg = f"Container startup failed: {str(e)}"
                print(f"[ERROR] {error_msg}")
                task_data["status"] = "failed"
                task_data["error"] = error_msg
                task_data["logs"].append(f"Error: {error_msg}")
                return
            
            # Use the dynamically allocated terminal port
            task_data["container_id"] = f"claude-task-{task_id}"
            task_data["claude_code_url"] = f"http://localhost:{terminal_port}"
            task_data["logs"].append(f"Web terminal with Claude Code access: http://localhost:{terminal_port}")
            task_data["logs"].append("Claude Code CLI environment ready for interactive development")
            
            # Get container ID (command runs in detached mode)
            container_id = f"claude-task-{task_id}"
            
            # Monitor container logs and status
            timeout_seconds = task_data.get('timeout_minutes', 60) * 60
            start_time = time.time()
            
            # Create log file for this task instance
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, f"task_{task_id}.log")
            
            # Initialize log file with task information
            try:
                with open(log_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"[SYSTEM] Task started at {datetime.now().isoformat()}\n")
                    f.write(f"[SYSTEM] Task ID: {task_id}\n")
                    f.write(f"[SYSTEM] Task Description: {task_data['task_description']}\n")
                    f.write(f"[SYSTEM] Completion Signal: {task_data['save_word']}\n")
                    f.write(f"[SYSTEM] Container ID: {container_id}\n")
                    f.write(f"[SYSTEM] Log monitoring started\n")
                    f.write("=" * 60 + "\n")
            except Exception as e:
                print(f"[ERROR] Failed to initialize log file: {e}")
            
            task_data["logs"].append("Container started successfully, monitoring Claude Code environment...")
            task_data["log_file"] = log_file_path
            
            while True:
                try:
                    # Check timeout
                    if time.time() - start_time > timeout_seconds:
                        task_data["logs"].append("Task timed out after 1 hour")
                        task_data["status"] = "timeout"
                        break
                    
                    # Check if container is still running
                    status_check = subprocess.run(
                        ["docker", "ps", "-q", "-f", f"name={container_id}"],
                        capture_output=True, text=True, timeout=5
                    )
                    
                    if not status_check.stdout.strip():
                        # Container stopped - check exit code to determine if it completed successfully
                        inspect_result = subprocess.run(
                            ["docker", "inspect", container_id, "--format", "{{.State.ExitCode}}"],
                            capture_output=True, text=True, timeout=5
                        )
                        
                        if inspect_result.returncode == 0:
                            exit_code = int(inspect_result.stdout.strip())
                            if exit_code == 0:
                                task_data["status"] = "completed"
                                task_data["progress"] = "Task completed successfully!"
                                task_data["logs"].append("Claude Code finished successfully")
                                
                                # Save completion status to log file
                                try:
                                    with open(log_file_path, 'a', encoding='utf-8') as f:
                                        f.write(f"[SYSTEM] Task completed at {datetime.now().isoformat()}\n")
                                        f.write(f"[SYSTEM] Container exited with code {exit_code} (success)\n")
                                except Exception as e:
                                    print(f"[ERROR] Failed to write completion to log file: {e}")
                            else:
                                task_data["status"] = "failed"
                                task_data["error"] = f"Claude Code exited with error code {exit_code}"
                                task_data["logs"].append(f"Claude Code failed with exit code {exit_code}")
                        else:
                            task_data["status"] = "failed"
                            task_data["error"] = "Could not determine container exit status"
                            task_data["logs"].append("Container stopped but exit status unknown")
                        break
                    
                    # Get container logs with timestamps
                    logs_result = subprocess.run(
                        ["docker", "logs", "--timestamps", "--since", f"{int(start_time)}", container_id],
                        capture_output=True, text=True, timeout=10
                    )
                    
                    if logs_result.returncode == 0 and logs_result.stdout:
                        # Get all logs and filter new ones
                        all_logs = logs_result.stdout.strip()
                        current_logs = [log for log in task_data["logs"] if log.startswith("Claude:")]
                        
                        # Split into lines and process new ones
                        log_lines = all_logs.split('\n') if all_logs else []
                        
                        new_logs_added = False
                        
                        for line in log_lines:
                            if line.strip():
                                # Save raw log line to file with timestamp
                                try:
                                    with open(log_file_path, 'a', encoding='utf-8') as f:
                                        f.write(f"{line}\n")
                                except Exception as e:
                                    print(f"[ERROR] Failed to write to log file: {e}")
                                
                                # Remove timestamp prefix for cleaner display
                                clean_line = line
                                if 'T' in line and 'Z' in line:  # Has timestamp
                                    parts = line.split(' ', 1)
                                    if len(parts) > 1:
                                        clean_line = parts[1]
                                
                                formatted_log = f"Claude: {clean_line.strip()}"
                                
                                # Only add if not already in logs
                                if formatted_log not in task_data["logs"]:
                                    task_data["logs"].append(formatted_log)
                                    new_logs_added = True
                                    
                                    # Note: We'll detect completion when the container/process naturally exits
                                    # No need to look for magic completion signals
                        
                        # Update if we added new logs
                        if new_logs_added:
                            pass  # Task data updated in memory, will be available via HTTP polling
                    
                    # Wait before next check
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    task_data["logs"].append(f"Monitoring error: {str(e)}")
                    await asyncio.sleep(5)
            
            if task_data["status"] != "completed":
                task_data["status"] = "failed"
                task_data["progress"] = "Task ended without completion signal"
                task_data["logs"].append("Task monitoring ended without completion signal")
            
        except Exception as e:
            task_data["status"] = "failed"
            task_data["progress"] = f"Error: {str(e)}"
            task_data["logs"].append(f"Error: {str(e)}")
        
    except Exception as e:
        task_data["status"] = "failed"
        task_data["progress"] = f"Error: {str(e)}"
        task_data["logs"].append(f"Error: {str(e)}")
    
    finally:
        # Save final log entry and add completion timestamp
        if 'log_file_path' in locals():
            try:
                with open(log_file_path, 'a', encoding='utf-8') as f:
                    f.write("=" * 60 + "\n")
                    f.write(f"[SYSTEM] Task ended at {datetime.now().isoformat()}\n")
                    f.write(f"[SYSTEM] Final status: {task_data.get('status', 'unknown')}\n")
                    f.write(f"[SYSTEM] Log file saved to: {log_file_path}\n")
                
                # Read the complete log file content for completed tasks
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    task_data["full_logs"] = f.read()
                    
            except Exception as e:
                print(f"[ERROR] Failed to write final log entry: {e}")
        
        # Add completion timestamp
        task_data["completed_at"] = datetime.now().isoformat()
        
        # Move completed/failed tasks to history instead of deleting them
        if task_id in active_tasks:
            task_history.append(active_tasks[task_id])
            del active_tasks[task_id]
            
            # Keep only last 50 completed tasks to avoid memory issues
            if len(task_history) > 50:
                task_history.pop(0)
        
        # Clean up Docker container
        try:
            subprocess.run(['docker', 'stop', f"claude-task-{task_id}"], 
                          capture_output=True, timeout=10)
            subprocess.run(['docker', 'rm', f"claude-task-{task_id}"], 
                          capture_output=True)
        except:
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
        "total_completed_in_history": stats.get("completed_tasks", 0)
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
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    response_task["full_logs"] = f.read()
            except Exception as e:
                response_task["full_logs_error"] = f"Could not read log file: {str(e)}"
    
    return {
        "success": True, 
        "task": response_task, 
        "is_active": task.is_active,
        "is_completed": not task.is_active
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
            subprocess.run(['docker', 'stop', task.container_id], 
                         capture_output=True, timeout=10)
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
            with open(task.log_file, 'r', encoding='utf-8') as f:
                logs = f.read()
            return {"success": True, "logs": logs, "file_path": task.log_file, "source": "file"}
        except Exception as e:
            return {"success": False, "message": f"Error reading log file: {str(e)}"}
    
    # Try default log file path
    log_file_path = os.path.join("task_logs", f"task_{task_id}.log")
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                logs = f.read()
            return {"success": True, "logs": logs, "file_path": log_file_path, "source": "default_file"}
        except Exception as e:
            return {"success": False, "message": f"Error reading log file: {str(e)}"}
    
    return {"success": False, "message": "Log file not found"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Summit autonomous AI is running"}

def load_environment():
    """Load environment variables from setup_env.sh"""
    setup_env_path = "setup_env.sh"
    if os.path.exists(setup_env_path):
        print("Loading environment from setup_env.sh...")
        try:
            with open(setup_env_path, 'r') as f:
                content = f.read()
                for line in content.split('\n'):
                    if line.strip().startswith('export ANTHROPIC_API_KEY='):
                        # Extract the API key value
                        key_part = line.split('=', 1)[1].strip().strip('"')
                        os.environ['ANTHROPIC_API_KEY'] = key_part
                        print("API key loaded from setup_env.sh")
                        break
        except Exception as e:
            print(f"Warning: Could not load setup_env.sh: {e}")
    else:
        print("Warning: setup_env.sh not found")

if __name__ == "__main__":
    kill_existing_server()
    
    # Load environment variables
    load_environment()
    
    print("Starting Summit Autonomous AI...")
    print("Web interface: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")
    
    uvicorn.run("autonomous_server:app", host="0.0.0.0", port=8000, reload=False) 