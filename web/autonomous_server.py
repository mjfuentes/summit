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
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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

app = FastAPI(title="Summit Autonomous AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global task management
active_tasks: Dict[str, Dict] = {}
task_history: List[Dict] = []
connected_clients: List[WebSocket] = []

class TaskRequest(BaseModel):
    task_description: str
    repository_url: Optional[str] = None
    github_token: Optional[str] = None
    timeout_minutes: Optional[int] = 60
    save_word: Optional[str] = "SUMMIT_TASK_COMPLETE"

class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: str
    logs: List[str]
    created_at: str
    container_id: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Summit Autonomous AI</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .header p { font-size: 1.2em; opacity: 0.9; margin: 10px 0; }
        
        .voice-input { position: relative; margin: 10px 0; }
        .voice-btn { background: #28a745; border: none; border-radius: 50%; width: 50px; height: 50px; color: white; font-size: 12px; cursor: pointer; transition: all 0.3s; }
        .voice-btn.recording { background: #dc3545; animation: pulse 1s infinite; }
        .voice-status { margin-left: 10px; font-size: 14px; color: #666; }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        .main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
        .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
        .card h2 { color: #333; margin-top: 0; font-size: 1.5em; }
        
        .task-form textarea { width: 100%; min-height: 120px; padding: 15px; border: 2px solid #e1e5e9; border-radius: 8px; font-size: 14px; resize: vertical; }
        .task-form input { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #e1e5e9; border-radius: 8px; font-size: 14px; }
        
        .btn { background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600; transition: all 0.3s; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        
        .task-item { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #667eea; cursor: pointer; }
        .task-status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase; }
        .status-running { background: #fff3cd; color: #856404; }
        .status-completed { background: #d4edda; color: #155724; }
        .status-failed { background: #f8d7da; color: #721c24; }
        
        .logs { background: #1e1e1e; color: #00ff00; padding: 15px; border-radius: 8px; font-family: 'Courier New', monospace; font-size: 12px; max-height: 300px; overflow-y: auto; margin: 10px 0; }
        .progress-bar { background: #e9ecef; height: 8px; border-radius: 4px; overflow: hidden; margin: 10px 0; }
        .progress-fill { background: linear-gradient(45deg, #667eea, #764ba2); height: 100%; transition: width 0.3s; }
        
        .connection-status { position: fixed; top: 20px; right: 20px; padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .connected { background: #d4edda; color: #155724; }
        .disconnected { background: #f8d7da; color: #721c24; }
        
        .advanced-options { margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px; }
        .advanced-options summary { cursor: pointer; font-weight: 600; color: #667eea; }
        
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
        .loading { animation: pulse 1.5s infinite; }
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
                    
                    <details class="advanced-options">
                        <summary>Advanced Options</summary>
                        <input type="text" id="repository-url" placeholder="GitHub repository URL (optional)">
                        <input type="password" id="github-token" placeholder="GitHub token for private repos (optional)">
                        <input type="number" id="timeout" placeholder="Timeout in minutes (default: 60)" value="60" min="5" max="240">
                        <input type="text" id="save-word" placeholder="Completion safe word (default: SUMMIT_TASK_COMPLETE)" value="SUMMIT_TASK_COMPLETE">
                    </details>
                    
                    <button class="btn" onclick="createTask()" id="create-btn">Start Autonomous Learning</button>
                </div>
            </div>
            
            <div class="card">
                <h2>Active Tasks</h2>
                <div id="active-tasks">
                    <p style="color: #666; text-align: center; padding: 20px;">No active tasks</p>
                </div>
            </div>
        </div>
        
        <div style="margin-top: 30px;">
            <div class="card">
                <h2>Task Monitor</h2>
                <div id="selected-task-details" style="display: none;">
                    <h3 id="task-title">Task Details</h3>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
                    </div>
                    <div id="task-logs" class="logs"></div>
                    <button class="btn" onclick="stopTask()" id="stop-btn" style="background: #dc3545;">Stop Task</button>
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
        
        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onopen = function() {
                document.getElementById('connection-status').textContent = 'Connected';
                document.getElementById('connection-status').className = 'connection-status connected';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleTaskUpdate(data);
            };
            
            ws.onclose = function() {
                document.getElementById('connection-status').textContent = 'Disconnected';
                document.getElementById('connection-status').className = 'connection-status disconnected';
                setTimeout(connectWebSocket, 3000);
            };
        }
        
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
                container.innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">No active tasks</p>';
                return;
            }
            
            container.innerHTML = tasks.map(task => `
                <div class="task-item" onclick="selectTask('${task.task_id}')">
                    <strong>${task.task_description.substring(0, 60)}...</strong>
                    <span class="task-status status-${task.status}">${task.status}</span>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">
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
            
            document.getElementById('task-logs').innerHTML = logsHtml;
            
            const progress = task.status === 'completed' ? 100 : task.status === 'running' ? 50 : 0;
            document.getElementById('progress-fill').style.width = progress + '%';
        }
        
        function selectTask(taskId) {
            selectedTaskId = taskId;
            document.getElementById('selected-task-details').style.display = 'block';
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
                        task_description: description,
                        repository_url: document.getElementById('repository-url').value || null,
                        github_token: document.getElementById('github-token').value || null,
                        timeout_minutes: parseInt(document.getElementById('timeout').value) || 60,
                        save_word: document.getElementById('save-word').value || 'SUMMIT_TASK_COMPLETE'
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    document.getElementById('task-description').value = '';
                    selectTask(result.task_id);
                    alert('Task created successfully! Watch the progress below.');
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
        
        // Initialize
        connectWebSocket();
        initSpeechRecognition();
        setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'get_tasks'}));
            }
        }, 5000);
    </script>
</body>
</html>
    """

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    
    try:
        # Send current tasks on connection
        await websocket.send_text(json.dumps({
            "type": "task_list",
            "tasks": list(active_tasks.values())
        }))
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "get_tasks":
                await websocket.send_text(json.dumps({
                    "type": "task_list", 
                    "tasks": list(active_tasks.values())
                }))
                
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

async def broadcast_task_update(task_data):
    """Broadcast task updates to all connected clients"""
    message = json.dumps({"type": "task_update", "task": task_data})
    disconnected = []
    
    for client in connected_clients:
        try:
            await client.send_text(message)
        except:
            disconnected.append(client)
    
    for client in disconnected:
        connected_clients.remove(client)

@app.post("/api/tasks")
async def create_task(request: TaskRequest):
    """Create a new autonomous learning task"""
    task_id = str(uuid.uuid4())
    
    task_data = {
        "task_id": task_id,
        "task_description": request.task_description,
        "repository_url": request.repository_url,
        "github_token": request.github_token,
        "timeout_minutes": request.timeout_minutes,
        "save_word": request.save_word,
        "status": "initializing",
        "progress": "Creating container environment...",
        "logs": ["Task created", "Initializing autonomous learning environment"],
        "created_at": datetime.now().isoformat(),
        "container_id": None
    }
    
    active_tasks[task_id] = task_data
    
    # Start the autonomous task in background
    asyncio.create_task(run_autonomous_task(task_id, task_data))
    
    await broadcast_task_update(task_data)
    
    return {"success": True, "task_id": task_id, "message": "Task created successfully"}

async def run_autonomous_task(task_id: str, task_data: Dict):
    """Run the autonomous learning task in a Docker container"""
    container_id = None
    
    try:
        # Update status to running
        task_data["status"] = "running"
        task_data["progress"] = "Building Docker container..."
        task_data["logs"].append("Creating isolated development environment")
        await broadcast_task_update(task_data)
        
        # Build and run Claude Code container
        print("[TASK] Starting Claude Code environment...")
        
        try:
            # Use the proper Dockerfile with full Claude Code integration
            dockerfile_path = "Dockerfile.autonomous"
            if not os.path.exists(dockerfile_path):
                print(f"[ERROR] {dockerfile_path} not found. Using basic container setup.")
                dockerfile_path = "Dockerfile.simple"
            
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
                task_data["status"] = "failed"
                task_data["error"] = f"Container build failed: {build_process.stderr}"
                return
            
            print("[TASK] Container built successfully, starting Claude Code...")
            
            # Run the container with proper Claude Code integration
            run_cmd = [
                "docker", "run", "-d",
                "--name", f"claude-task-{task_id}",
                "-p", "7681:7681",
                "-e", f"TASK_DESCRIPTION={task_data['task_description']}",
                "-e", f"SAVE_WORD={task_data['save_word']}",
                "-e", f"ANTHROPIC_API_KEY={os.getenv('ANTHROPIC_API_KEY')}",
                "-e", f"GITHUB_TOKEN={task_data.get('github_token', '')}",
                "-e", f"REPOSITORY_URL={task_data.get('repository_url', '')}",
                "claude-code-task"
            ]
            
            task_data["logs"].append("Starting Claude Code container...")
            await broadcast_task_update(task_data)
            
            container_process = await asyncio.create_subprocess_exec(
                *run_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            # Calculate the web terminal port
            terminal_port = 7681
            task_data["container_id"] = f"claude-task-{task_id}"
            task_data["claude_code_url"] = f"http://localhost:{terminal_port}"
            task_data["logs"].append(f"Web terminal with Claude Code access: http://localhost:{terminal_port}")
            task_data["logs"].append("Claude Code CLI environment ready for interactive development")
            await broadcast_task_update(task_data)
            
            # Monitor container output with timeout
            timeout_seconds = task_data.get('timeout_minutes', 60) * 60
            start_time = time.time()
            
            while True:
                try:
                    # Check if process is still running
                    if container_process.returncode is not None:
                        break
                    
                    # Check timeout
                    if time.time() - start_time > timeout_seconds:
                        task_data["logs"].append("Task timed out")
                        container_process.terminate()
                        await asyncio.sleep(5)
                        if container_process.returncode is None:
                            container_process.kill()
                        break
                    
                    # Read output line
                    try:
                        line = await asyncio.wait_for(
                            container_process.stdout.readline(), 
                            timeout=5.0
                        )
                        
                        if not line:
                            break
                            
                        log_line = line.decode().strip()
                        if log_line:
                            task_data["logs"].append(log_line)
                            
                            # Check for completion signal
                            if task_data["save_word"] in log_line:
                                task_data["status"] = "completed"
                                task_data["progress"] = "Task completed successfully!"
                                task_data["logs"].append("Task completed! Safe word detected.")
                                await broadcast_task_update(task_data)
                                break
                            
                            await broadcast_task_update(task_data)
                            
                    except asyncio.TimeoutError:
                        # Continue if no output for 5 seconds
                        continue
                    
                except Exception as e:
                    task_data["logs"].append(f"Monitoring error: {str(e)}")
                    break
            
            # Wait for container to finish
            await container_process.wait()
            
            if task_data["status"] != "completed":
                if container_process.returncode == 0:
                    task_data["status"] = "completed"
                    task_data["progress"] = "Task finished"
                    task_data["logs"].append("Container finished successfully")
                else:
                    task_data["status"] = "failed"
                    task_data["progress"] = f"Container exited with code {container_process.returncode}"
                    task_data["logs"].append(f"Container failed with exit code {container_process.returncode}")
            
        except Exception as e:
            task_data["status"] = "failed"
            task_data["progress"] = f"Error: {str(e)}"
            task_data["logs"].append(f"Error: {str(e)}")
        
    except Exception as e:
        task_data["status"] = "failed"
        task_data["progress"] = f"Error: {str(e)}"
        task_data["logs"].append(f"Error: {str(e)}")
    
    finally:
        await broadcast_task_update(task_data)
        
        # Ensure container cleanup
        if task_id in active_tasks:
            del active_tasks[task_id]
        
        # Clean up Docker container
        try:
            subprocess.run(['docker', 'stop', f"claude-task-{task_id}"], 
                          capture_output=True, timeout=10)
            subprocess.run(['docker', 'rm', f"claude-task-{task_id}"], 
                          capture_output=True)
        except:
            pass

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get details of a specific task"""
    if task_id in active_tasks:
        return {"success": True, "task": active_tasks[task_id]}
    
    # Check history
    for task in task_history:
        if task["task_id"] == task_id:
            return {"success": True, "task": task}
    
    return {"success": False, "message": "Task not found"}

@app.post("/api/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    """Stop a running task"""
    if task_id not in active_tasks:
        return {"success": False, "message": "Task not found"}
    
    task_data = active_tasks[task_id]
    
    # Stop the Docker container if it exists
    if task_data.get("container_id"):
        try:
            subprocess.run(['docker', 'stop', task_data["container_id"]], 
                         capture_output=True, timeout=10)
            task_data["logs"].append("Docker container stopped")
        except Exception as e:
            task_data["logs"].append(f"Error stopping container: {e}")
    
    task_data["status"] = "stopped"
    task_data["progress"] = "Task stopped by user"
    task_data["logs"].append("Task stopped by user")
    await broadcast_task_update(task_data)
    
    return {"success": True, "message": "Task stopped"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Summit autonomous AI is running"}

if __name__ == "__main__":
    kill_existing_server()
    
    print("Starting Summit Autonomous AI...")
    print("Web interface: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")
    
    uvicorn.run("autonomous_server:app", host="0.0.0.0", port=8000, reload=True) 