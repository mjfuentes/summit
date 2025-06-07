#!/usr/bin/env python3
# Testing autonomous Claude Code
# Summit Web API Server
"""
Summit Web API - FastAPI server that exposes Summit's capabilities via REST endpoints
"""

import os
import sys
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import setup_environment
from summit import handle_call_tool

# Add the current directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# Set up environment variables
setup_environment()

# Initialize FastAPI app
app = FastAPI(
    title="Summit AI API",
    description="REST API for Summit AI Advisor with self-modification capabilities",
    version="1.0.0",
)

# Add CORS middleware for web browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response validation
class AdviceRequest(BaseModel):
    question: str
    context: Optional[str] = None


class ShareRequest(BaseModel):
    content: str
    category: Optional[str] = "general"
    context: Optional[str] = None


class LearnRequest(BaseModel):
    query: str
    focus: Optional[str] = None
    max_results: Optional[int] = 5


class AnalyticsRequest(BaseModel):
    include_suggestions: Optional[bool] = False


class LearnCapabilityRequest(BaseModel):
    capability_description: str
    requirements: Optional[str] = None
    machine_type: Optional[str] = "standardLinux32gb"


class DeployRequest(BaseModel):
    codespace_name: str
    commit_message: str


class CleanupRequest(BaseModel):
    codespace_name: str


class SoundCloudConfigRequest(BaseModel):
    access_token: str


class SoundCloudSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10


class ApiResponse(BaseModel):
    success: bool
    data: Any
    message: Optional[str] = None


# Error handler
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "message": f"Internal error: {str(exc)}",
        },
    )


# Root endpoint with HTML interface
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Summit AI Advisor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 3rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3rem;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
        }
        .form-group input, .form-group textarea, .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.2s ease;
        }
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s ease;
            width: 100%;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .response {
            margin-top: 15px;
            padding: 15px;
            border-radius: 8px;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            max-height: 200px;
            overflow-y: auto;
        }
        .loading {
            color: #667eea;
            font-style: italic;
        }
        .error {
            background: #fee;
            border-left-color: #e74c3c;
            color: #c0392b;
        }
        .status-card {
            grid-column: 1 / -1;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            text-align: center;
        }
        .status-item h4 {
            font-size: 2rem;
            margin-bottom: 5px;
        }
        .status-item p {
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Summit AI Advisor</h1>
            <p>Your autonomous AI companion with self-modification capabilities</p>
        </div>

        <div class="cards-grid">
            <!-- Status Card -->
            <div class="card status-card">
                <h3>System Status</h3>
                <div id="status-content" class="status-grid">
                    <div class="status-item">
                        <h4 id="uptime">--</h4>
                        <p>Uptime (minutes)</p>
                    </div>
                    <div class="status-item">
                        <h4 id="knowledge-items">--</h4>
                        <p>Knowledge Items</p>
                    </div>
                    <div class="status-item">
                        <h4 id="daily-budget">--</h4>
                        <p>Daily Budget Used</p>
                    </div>
                </div>
            </div>

            <!-- Ask for Advice -->
            <div class="card">
                <h3>Ask for Advice</h3>
                <div class="form-group">
                    <label for="advice-question">Question:</label>
                    <textarea id="advice-question" rows="3" placeholder="What would you like advice on?"></textarea>
                </div>
                <div class="form-group">
                    <label for="advice-context">Context (optional):</label>
                    <input type="text" id="advice-context" placeholder="Additional context...">
                </div>
                <button class="btn" onclick="askAdvice()">Get Advice</button>
                <div id="advice-response" class="response" style="display: none;"></div>
            </div>

            <!-- Share Knowledge -->
            <div class="card">
                <h3>Share Knowledge</h3>
                <div class="form-group">
                    <label for="share-content">Content:</label>
                    <textarea id="share-content" rows="3" placeholder="Share your experience, insight, or observation..."></textarea>
                </div>
                <div class="form-group">
                    <label for="share-category">Category:</label>
                    <select id="share-category">
                        <option value="observation">Observation</option>
                        <option value="insight">Insight</option>
                        <option value="challenge">Challenge</option>
                        <option value="best_practice">Best Practice</option>
                        <option value="trend">Trend</option>
                        <option value="general">General</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="share-context">Context (optional):</label>
                    <input type="text" id="share-context" placeholder="When/where this applies...">
                </div>
                <button class="btn" onclick="shareKnowledge()">Share</button>
                <div id="share-response" class="response" style="display: none;"></div>
            </div>

            <!-- Learn from Knowledge -->
            <div class="card">
                <h3>Learn from Knowledge</h3>
                <div class="form-group">
                    <label for="learn-query">Query:</label>
                    <input type="text" id="learn-query" placeholder="What do you want to learn about?">
                </div>
                <div class="form-group">
                    <label for="learn-focus">Focus (optional):</label>
                    <select id="learn-focus">
                        <option value="">Any focus</option>
                        <option value="patterns">Patterns</option>
                        <option value="trends">Trends</option>
                        <option value="insights">Insights</option>
                        <option value="experiences">Experiences</option>
                    </select>
                </div>
                <button class="btn" onclick="learnKnowledge()">Search Knowledge</button>
                <div id="learn-response" class="response" style="display: none;"></div>
            </div>

            <!-- Analytics -->
            <div class="card">
                <h3>Analytics & Insights</h3>
                <button class="btn" onclick="getAnalytics()" style="margin-bottom: 10px;">Get Analytics</button>
                <button class="btn" onclick="getInsights()">Get Content Insights</button>
                <div id="analytics-response" class="response" style="display: none;"></div>
            </div>

            <!-- SoundCloud Settings -->
            <div class="card">
                <h3>SoundCloud Settings</h3>
                <div class="form-group">
                    <label for="soundcloud-token">Access Token:</label>
                    <input type="password" id="soundcloud-token" placeholder="Enter your SoundCloud access token">
                </div>
                <button class="btn" onclick="configureSoundCloud()" style="margin-bottom: 10px;">Save Token</button>
                <button class="btn" onclick="checkSoundCloudConfig()">Check Status</button>
                <div id="soundcloud-config-response" class="response" style="display: none;"></div>
            </div>

            <!-- SoundCloud Music Player -->
            <div class="card">
                <h3>SoundCloud Music Player</h3>
                <div class="form-group">
                    <label for="music-search">Search Music:</label>
                    <input type="text" id="music-search" placeholder="Search for tracks...">
                </div>
                <button class="btn" onclick="searchMusic()">Search</button>
                <div id="music-results" class="response" style="display: none;"></div>
                <div id="music-player" style="margin-top: 15px; display: none;">
                    <audio id="audio-player" controls style="width: 100%;">
                        Your browser does not support the audio element.
                    </audio>
                    <div id="current-track-info" style="margin-top: 10px; font-size: 14px; color: #667eea;"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Load status on page load
        window.onload = function() {
            loadStatus();
        };

        async function makeRequest(endpoint, data = null) {
            const options = {
                method: data ? 'POST' : 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            };

            if (data) {
                options.body = JSON.stringify(data);
            }

            const response = await fetch(endpoint, options);
            return await response.json();
        }

        function showResponse(elementId, data, isError = false) {
            const element = document.getElementById(elementId);
            element.style.display = 'block';
            element.className = `response ${isError ? 'error' : ''}`;
            element.textContent = data;
        }

        function showLoading(elementId) {
            const element = document.getElementById(elementId);
            element.style.display = 'block';
            element.className = 'response loading';
            element.textContent = 'Loading...';
        }

        async function loadStatus() {
            try {
                const result = await makeRequest('/api/status');
                if (result.success) {
                    const lines = result.data.split('\\n');
                    const uptimeMatch = lines.find(l => l.includes('Uptime:'));
                    const uptime = uptimeMatch ? Math.round(parseInt(uptimeMatch.split('Uptime: ')[1].split('s')[0]) / 60) : 0;
                    document.getElementById('uptime').textContent = uptime;
                }

                const knowledgeResult = await makeRequest('/api/insights');
                if (knowledgeResult.success) {
                    const lines = knowledgeResult.data.split('\\n');
                    const itemsMatch = lines.find(l => l.includes('Total shared items:'));
                    const items = itemsMatch ? itemsMatch.split(': ')[1] : '0';
                    document.getElementById('knowledge-items').textContent = items;
                }

                const costResult = await makeRequest('/api/cost-report');
                if (costResult.success) {
                    const lines = costResult.data.split('\\n');
                    const budgetMatch = lines.find(l => l.includes('Daily:'));
                    if (budgetMatch) {
                        const percentage = budgetMatch.match(/\\((\\d+\\.\\d+)%/);
                        document.getElementById('daily-budget').textContent = percentage ? percentage[1] + '%' : '0%';
                    }
                }
            } catch (error) {
                console.error('Failed to load status:', error);
            }
        }

        async function askAdvice() {
            const question = document.getElementById('advice-question').value.trim();
            if (!question) {
                alert('Please enter a question');
                return;
            }

            showLoading('advice-response');

            try {
                const result = await makeRequest('/api/advice', {
                    question: question,
                    context: document.getElementById('advice-context').value || null
                });

                showResponse('advice-response', result.data, !result.success);
            } catch (error) {
                showResponse('advice-response', `Error: ${error.message}`, true);
            }
        }

        async function shareKnowledge() {
            const content = document.getElementById('share-content').value.trim();
            if (!content) {
                alert('Please enter content to share');
                return;
            }

            showLoading('share-response');

            try {
                const result = await makeRequest('/api/share', {
                    content: content,
                    category: document.getElementById('share-category').value,
                    context: document.getElementById('share-context').value || null
                });

                showResponse('share-response', result.data, !result.success);
                if (result.success) {
                    document.getElementById('share-content').value = '';
                    document.getElementById('share-context').value = '';
                    loadStatus(); // Refresh status
                }
            } catch (error) {
                showResponse('share-response', `Error: ${error.message}`, true);
            }
        }

        async function learnKnowledge() {
            const query = document.getElementById('learn-query').value.trim();
            if (!query) {
                alert('Please enter a search query');
                return;
            }

            showLoading('learn-response');

            try {
                const result = await makeRequest('/api/learn', {
                    query: query,
                    focus: document.getElementById('learn-focus').value || null
                });

                showResponse('learn-response', result.data, !result.success);
            } catch (error) {
                showResponse('learn-response', `Error: ${error.message}`, true);
            }
        }

        async function getAnalytics() {
            showLoading('analytics-response');

            try {
                const result = await makeRequest('/api/analytics', {
                    include_suggestions: true
                });

                showResponse('analytics-response', result.data, !result.success);
            } catch (error) {
                showResponse('analytics-response', `Error: ${error.message}`, true);
            }
        }

        async function getInsights() {
            showLoading('analytics-response');

            try {
                const result = await makeRequest('/api/insights');

                showResponse('analytics-response', result.data, !result.success);
            } catch (error) {
                showResponse('analytics-response', `Error: ${error.message}`, true);
            }
        }

        // SoundCloud functions
        async function configureSoundCloud() {
            const token = document.getElementById('soundcloud-token').value.trim();
            if (!token) {
                alert('Please enter a SoundCloud access token');
                return;
            }

            showLoading('soundcloud-config-response');

            try {
                const result = await makeRequest('/api/soundcloud/config', {
                    access_token: token
                });

                showResponse('soundcloud-config-response', result.data, !result.success);
                if (result.success) {
                    document.getElementById('soundcloud-token').value = '';
                }
            } catch (error) {
                showResponse('soundcloud-config-response', `Error: ${error.message}`, true);
            }
        }

        async function checkSoundCloudConfig() {
            showLoading('soundcloud-config-response');

            try {
                const result = await makeRequest('/api/soundcloud/config');
                const status = result.data.configured ? 'SoundCloud is configured and ready' : 'SoundCloud token not configured';
                showResponse('soundcloud-config-response', status, !result.success);
            } catch (error) {
                showResponse('soundcloud-config-response', `Error: ${error.message}`, true);
            }
        }

        async function searchMusic() {
            const query = document.getElementById('music-search').value.trim();
            if (!query) {
                alert('Please enter a search query');
                return;
            }

            showLoading('music-results');

            try {
                const result = await makeRequest('/api/soundcloud/search', {
                    query: query,
                    limit: 10
                });

                if (result.success && result.data.length > 0) {
                    displayMusicResults(result.data);
                } else if (result.success && result.data.length === 0) {
                    showResponse('music-results', 'No tracks found for your search.', false);
                } else {
                    showResponse('music-results', result.message || 'Search failed', true);
                }
            } catch (error) {
                showResponse('music-results', `Error: ${error.message}`, true);
            }
        }

        function displayMusicResults(tracks) {
            const resultsDiv = document.getElementById('music-results');
            resultsDiv.style.display = 'block';
            resultsDiv.className = 'response';

            let html = '<div style="max-height: 300px; overflow-y: auto;">';
            tracks.forEach(track => {
                const duration = track.duration ? Math.floor(track.duration / 1000 / 60) + ':' + String(Math.floor(track.duration / 1000) % 60).padStart(2, '0') : 'Unknown';
                html += `
                    <div style="border-bottom: 1px solid #eee; padding: 10px 0; cursor: pointer;" onclick="playTrack('${track.id}', '${track.title.replace(/'/g, "\\'")}', '${track.artist.replace(/'/g, "\\'")}')">
                        <div style="font-weight: bold; color: #667eea;">${track.title}</div>
                        <div style="color: #666; font-size: 12px;">by ${track.artist} • ${duration}</div>
                    </div>
                `;
            });
            html += '</div>';
            resultsDiv.innerHTML = html;
        }

        async function playTrack(trackId, title, artist) {
            try {
                const result = await makeRequest(`/api/soundcloud/stream/${trackId}`);

                if (result.success && result.data.stream_url) {
                    const audioPlayer = document.getElementById('audio-player');
                    const trackInfo = document.getElementById('current-track-info');
                    const playerDiv = document.getElementById('music-player');

                    audioPlayer.src = result.data.stream_url;
                    trackInfo.textContent = `Now playing: ${title} by ${artist}`;
                    playerDiv.style.display = 'block';

                    audioPlayer.play().catch(error => {
                        console.error('Error playing audio:', error);
                        alert('Unable to play track. The stream may not be available.');
                    });
                } else {
                    alert('Unable to stream this track. It may not be available for streaming.');
                }
            } catch (error) {
                console.error('Error streaming track:', error);
                alert('Error streaming track: ' + error.message);
            }
        }

        // Auto-refresh status every 30 seconds
        setInterval(loadStatus, 30000);
    </script>
</body>
</html>
    """
    return html_content


# API endpoints
@app.post("/api/advice", response_model=ApiResponse)
async def get_advice(request: AdviceRequest):
    """Get advice from Summit"""
    try:
        result = await handle_call_tool(
            "summit_advice",
            {"question": request.question, "context": request.context},
        )
        return ApiResponse(success=True, data=result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status", response_model=ApiResponse)
async def get_status():
    """Get Summit status"""
    try:
        result = await handle_call_tool("summit_status", {})
        return ApiResponse(success=True, data=result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cost-report", response_model=ApiResponse)
async def get_cost_report():
    """Get cost tracking report"""
    try:
        result = await handle_call_tool("summit_cost_report", {})
        return ApiResponse(success=True, data=result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/share", response_model=ApiResponse)
async def share_knowledge(request: ShareRequest):
    """Share knowledge with Summit"""
    try:
        result = await handle_call_tool(
            "summit_share",
            {
                "content": request.content,
                "category": request.category,
                "context": request.context,
            },
        )
        return ApiResponse(success=True, data=result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/learn", response_model=ApiResponse)
async def learn_from_knowledge(request: LearnRequest):
    """Learn from Summit's knowledge base"""
    try:
        result = await handle_call_tool(
            "summit_learn",
            {
                "query": request.query,
                "focus": request.focus,
                "max_results": request.max_results,
            },
        )
        return ApiResponse(success=True, data=result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analytics", response_model=ApiResponse)
async def get_analytics(request: AnalyticsRequest):
    """Get search analytics"""
    try:
        result = await handle_call_tool(
            "summit_analytics",
            {"include_suggestions": request.include_suggestions},
        )
        return ApiResponse(success=True, data=result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/insights", response_model=ApiResponse)
async def get_insights():
    """Get content insights"""
    try:
        result = await handle_call_tool("summit_insights", {})
        return ApiResponse(success=True, data=result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/learn-capability", response_model=ApiResponse)
async def learn_capability(request: LearnCapabilityRequest):
    """Learn a new capability using Codespaces"""
    try:
        result = await handle_call_tool(
            "summit_learn_capability",
            {
                "capability_description": request.capability_description,
                "requirements": request.requirements,
                "machine_type": request.machine_type,
            },
        )
        return ApiResponse(success=True, data=result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/codespace-status", response_model=ApiResponse)
async def get_codespace_status():
    """Get codespace status"""
    try:
        result = await handle_call_tool("summit_codespace_status", {})
        return ApiResponse(success=True, data=result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/deploy", response_model=ApiResponse)
async def deploy_changes(request: DeployRequest):
    """Deploy changes from codespace"""
    try:
        result = await handle_call_tool(
            "summit_deploy_changes",
            {
                "codespace_name": request.codespace_name,
                "commit_message": request.commit_message,
            },
        )
        return ApiResponse(success=True, data=result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cleanup", response_model=ApiResponse)
async def cleanup_environment(request: CleanupRequest):
    """Clean up development environment"""
    try:
        result = await handle_call_tool(
            "summit_cleanup_environment",
            {"codespace_name": request.codespace_name},
        )
        return ApiResponse(success=True, data=result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# SoundCloud integration endpoints
settings_store = {}


@app.post("/api/soundcloud/config", response_model=ApiResponse)
async def configure_soundcloud(request: SoundCloudConfigRequest):
    """Configure SoundCloud access token"""
    try:
        settings_store["soundcloud_token"] = request.access_token
        return ApiResponse(
            success=True, data="SoundCloud token configured successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/soundcloud/config", response_model=ApiResponse)
async def get_soundcloud_config():
    """Get SoundCloud configuration status"""
    try:
        token = settings_store.get("soundcloud_token", "")
        has_token = token and token.strip()
        return ApiResponse(success=True, data={"configured": bool(has_token)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/soundcloud/search", response_model=ApiResponse)
async def search_soundcloud(request: SoundCloudSearchRequest):
    """Search SoundCloud tracks"""
    try:
        import requests

        token = settings_store.get("soundcloud_token", "")
        if not token or not token.strip():
            raise HTTPException(
                status_code=400, detail="SoundCloud token not configured"
            )

        # SoundCloud API search
        url = "https://api.soundcloud.com/tracks"
        params = {
            "q": request.query,
            "limit": request.limit,
            "oauth_token": token,
        }

        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            tracks = response.json()
            # Format tracks for frontend
            formatted_tracks = []
            for track in tracks:
                if track.get("streamable"):
                    formatted_tracks.append(
                        {
                            "id": track.get("id"),
                            "title": track.get("title"),
                            "artist": track.get("user", {}).get("username"),
                            "duration": track.get("duration"),
                            "artwork_url": track.get("artwork_url"),
                            "stream_url": track.get("stream_url"),
                            "permalink_url": track.get("permalink_url"),
                        }
                    )
            return ApiResponse(success=True, data=formatted_tracks)
        else:
            raise HTTPException(
                status_code=response.status_code, detail="SoundCloud API error"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/soundcloud/stream/{track_id}")
async def stream_soundcloud_track(track_id: str):
    """Get SoundCloud track stream URL"""
    try:
        import requests

        token = settings_store.get("soundcloud_token", "")
        if not token or not token.strip():
            raise HTTPException(
                status_code=400, detail="SoundCloud token not configured"
            )

        # Get track stream URL
        url = f"https://api.soundcloud.com/tracks/{track_id}/stream"
        params = {"oauth_token": token}

        response = requests.get(
            url, params=params, timeout=10, allow_redirects=False
        )
        if response.status_code == 302:
            stream_url = response.headers.get("Location")
            return ApiResponse(success=True, data={"stream_url": stream_url})
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Track not available for streaming",
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Summit Web API is running"}


if __name__ == "__main__":
    print("Starting Summit Web API Server...")
    print("Access the web interface at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")

    uvicorn.run(
        "web_api:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
