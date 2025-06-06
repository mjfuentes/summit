#!/usr/bin/env python3
"""
Summit Standalone Web Server
A simplified web interface that doesn't require MCP dependencies
"""

import sys
import os
import subprocess
import time
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

def kill_existing_server():
    """Kill any existing processes using port 8000"""
    try:
        # Find processes using port 8000
        result = subprocess.run(['lsof', '-ti:8000'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"Killing existing server process (PID: {pid})")
                    subprocess.run(['kill', pid], capture_output=True)
            time.sleep(1)  # Give processes time to shut down
            print("Cleared port 8000")
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        # lsof command might not be available on all systems
        pass

# Add src to path for basic imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from knowledge_base import KnowledgeBase
    from cost_tracker import CostTracker
    from config import setup_environment, SUMMIT_CONFIG
    setup_environment()
    
    # Initialize components
    knowledge_base = KnowledgeBase()
    cost_tracker = CostTracker(
        daily_budget=SUMMIT_CONFIG["daily_budget"],
        hourly_budget=SUMMIT_CONFIG["hourly_budget"],
        max_recursion_depth=SUMMIT_CONFIG["max_recursion_depth"]
    )
    
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some components unavailable: {e}")
    knowledge_base = None
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

class ShareRequest(BaseModel):
    content: str
    category: str = "general"
    context: Optional[str] = None

class LearnRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5

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
            <strong>Note:</strong> This is a simplified web interface. Full AI capabilities require additional setup.
        </div>
        
        <div class="card">
            <h3>Knowledge Base</h3>
            <h4>Share Knowledge</h4>
            <textarea id="share-content" placeholder="Share your experience, insight, or observation..." rows="3"></textarea>
            <select id="share-category">
                <option value="observation">Observation</option>
                <option value="insight">Insight</option>
                <option value="challenge">Challenge</option>
                <option value="best_practice">Best Practice</option>
                <option value="trend">Trend</option>
            </select>
            <button onclick="shareKnowledge()">Share</button>
            <div id="share-response" class="response" style="display: none;"></div>
        </div>
        
        <div class="card">
            <h4>Search Knowledge</h4>
            <input type="text" id="learn-query" placeholder="What do you want to learn about?">
            <button onclick="searchKnowledge()">Search</button>
            <div id="learn-response" class="response" style="display: none;"></div>
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

        async function shareKnowledge() {
            const content = document.getElementById('share-content').value.trim();
            if (!content) return alert('Please enter content to share');
            
            showLoading('share-response');
            
            try {
                const result = await makeRequest('/api/share', {
                    content: content,
                    category: document.getElementById('share-category').value
                });
                
                showResponse('share-response', result.message || 'Knowledge shared successfully!', !result.success);
                if (result.success) {
                    document.getElementById('share-content').value = '';
                }
            } catch (error) {
                showResponse('share-response', 'Error: ' + error.message, true);
            }
        }

        async function searchKnowledge() {
            const query = document.getElementById('learn-query').value.trim();
            if (!query) return alert('Please enter a search query');
            
            showLoading('learn-response');
            
            try {
                const result = await makeRequest('/api/learn', {
                    query: query
                });
                
                showResponse('learn-response', result.data || result.message, !result.success);
            } catch (error) {
                showResponse('learn-response', 'Error: ' + error.message, true);
            }
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

@app.post("/api/share")
async def share_knowledge(request: ShareRequest):
    if not COMPONENTS_AVAILABLE or not knowledge_base:
        return {"success": False, "message": "Knowledge base not available"}
    
    try:
        item = knowledge_base.add_shared_item(
            request.content, 
            request.category, 
            request.context
        )
        return {"success": True, "message": f"Added item {item['id']} to knowledge base"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learn")
async def search_knowledge(request: LearnRequest):
    if not COMPONENTS_AVAILABLE or not knowledge_base:
        return {"success": False, "message": "Knowledge base not available"}
    
    try:
        results = knowledge_base.search_knowledge(request.query, request.max_results)
        
        if not results:
            return {"success": True, "data": f"No results found for '{request.query}'"}
        
        response_text = f"Found {len(results)} results:\n\n"
        for i, result in enumerate(results, 1):
            data = result['data']
            content = data.get('content', data.get('insight', ''))
            score = result.get('similarity_score', 0)
            response_text += f"{i}. {content}\n"
            response_text += f"   Category: {data.get('category', 'unknown')}, Score: {score:.2f}\n\n"
        
        return {"success": True, "data": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    status_info = "Summit Standalone Web Interface\n\n"
    
    if COMPONENTS_AVAILABLE:
        status_info += "Components Status:\n"
        status_info += f"- Knowledge Base: Available ({len(knowledge_base.shared_items) if knowledge_base else 0} items)\n"
        status_info += f"- Cost Tracker: Available\n\n"
        
        if knowledge_base:
            summary = knowledge_base.get_knowledge_summary()
            status_info += f"Knowledge Base Summary:\n"
            status_info += f"- Total items: {summary['total_shares']}\n"
            status_info += f"- Categories: {list(summary['categories'].keys())}\n"
            status_info += f"- Search mode: {summary['search_mode']}\n"
    else:
        status_info += "Components Status:\n"
        status_info += "- Limited functionality (some dependencies missing)\n"
    
    return {"success": True, "data": status_info}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Summit standalone web interface is running"}

if __name__ == "__main__":
    # Kill any existing processes on port 8000
    kill_existing_server()
    
    print("Starting Summit Standalone Web Interface...")
    print("Web interface: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")
    
    uvicorn.run("standalone_server:app", host="0.0.0.0", port=8000, reload=True) 