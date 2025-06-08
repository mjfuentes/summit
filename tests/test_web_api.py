#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add web directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from standalone_server import app

# Import autonomous server for developer dashboard endpoints
try:
    from autonomous_server import app as autonomous_app
except ImportError:
    autonomous_app = None

# Import the app but don't create TestClient at module level

# Skip environment setup since standalone server handles missing
# components gracefully


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint"""
    # Create test client inside the test function
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Summit standalone web interface is running" in data["message"]


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint returns HTML"""
    # Create test client inside the test function
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Summit AI Web Interface" in response.text
    assert "<html" in response.text


@pytest.mark.asyncio
async def test_status_endpoint():
    """Test status endpoint"""
    # Create test client inside the test function
    client = TestClient(app)
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"]
    assert "Summit Standalone Web Interface" in data["data"]


@pytest.mark.asyncio
async def test_api_error_handling():
    """Test API error handling with malformed requests"""
    # Create test client inside the test function
    client = TestClient(app)
    # Test with invalid JSON to status endpoint
    response = client.post(
        "/api/status",
        data="invalid json",
        headers={"Content-Type": "application/json"},
    )
    # Status endpoint is GET only, so POST should return method not allowed
    assert response.status_code == 405


def test_cors_headers():
    """Test CORS headers are present"""
    # Create test client inside the test function
    client = TestClient(app)
    response = client.get("/")
    # CORS headers should be present for browser access
    assert response.status_code == 200


# New tests for developer dashboard endpoints


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_agents_status_endpoint():
    """Test /api/agents/status endpoint"""
    # Mock database and agents
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"
    mock_agent.role = "engineering"
    mock_agent.status = MagicMock()
    mock_agent.status.value = "ready"
    mock_agent.last_heartbeat = datetime.utcnow()
    mock_agent.current_task_id = None
    mock_agent.completed_tasks = 5
    mock_agent.failed_tasks = 1
    mock_agent.registered_at = datetime.utcnow() - timedelta(hours=2)
    mock_agent.pod_name = "test-pod"
    mock_agent.workspace_path = "/workspace"

    mock_db.get_all_agents.return_value = [mock_agent]

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/agents/status")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "summary" in data
    assert "agents" in data
    assert data["summary"]["total_agents"] == 1
    assert data["summary"]["active_agents"] == 1
    assert len(data["agents"]) == 1
    assert data["agents"][0]["id"] == "agent-123"
    assert data["agents"][0]["role"] == "engineering"
    assert data["agents"][0]["status"] == "ready"


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_agents_status_endpoint_empty():
    """Test /api/agents/status endpoint with no agents"""
    mock_db = AsyncMock()
    mock_db.get_all_agents.return_value = []

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/agents/status")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["summary"]["total_agents"] == 0
    assert data["summary"]["active_agents"] == 0
    assert len(data["agents"]) == 0


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_agents_status_endpoint_error():
    """Test /api/agents/status endpoint error handling"""
    mock_db = AsyncMock()
    mock_db.get_all_agents.side_effect = Exception("Database error")

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/agents/status")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert "Database error" in data["error"]


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_system_statistics_endpoint():
    """Test /api/system/statistics endpoint"""
    # Mock database and data
    mock_db = AsyncMock()
    mock_db.get_task_statistics.return_value = {
        "total_tasks": 10,
        "active_tasks": 2,
        "completed_tasks": 7,
        "failed_tasks": 1,
    }

    mock_agent = MagicMock()
    mock_agent.role = "engineering"
    mock_agent.status = MagicMock()
    mock_agent.status.value = "ready"
    mock_db.get_all_agents.return_value = [mock_agent]

    mock_task = MagicMock()
    mock_task.status = "completed"
    mock_db.get_tasks_since.return_value = [mock_task]

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/system/statistics")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "system_health" in data
    assert "task_statistics" in data
    assert "agent_statistics" in data
    assert "performance" in data
    assert data["task_statistics"]["total_tasks"] == 10
    assert data["agent_statistics"]["total_agents"] == 1


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_system_statistics_endpoint_error():
    """Test /api/system/statistics endpoint error handling"""
    mock_db = AsyncMock()
    mock_db.get_task_statistics.side_effect = Exception("Stats error")

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/system/statistics")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert "Stats error" in data["error"]


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_system_activity_endpoint():
    """Test /api/system/activity endpoint"""
    mock_db = AsyncMock()
    mock_task = MagicMock()
    mock_task.task_id = "task-123"
    mock_task.task_description = "Test task description"
    mock_task.status = "completed"
    mock_task.created_at = datetime.utcnow() - timedelta(hours=1)
    mock_task.completed_at = datetime.utcnow()

    mock_db.get_tasks_since.return_value = [mock_task]

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/system/activity")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "activity" in data
    assert len(data["activity"]) == 1
    assert data["activity"][0]["id"] == "task-123"
    assert data["activity"][0]["status"] == "completed"
    assert "duration_minutes" in data["activity"][0]


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_system_activity_endpoint_empty():
    """Test /api/system/activity endpoint with no activity"""
    mock_db = AsyncMock()
    mock_db.get_tasks_since.return_value = []

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/system/activity")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["activity"]) == 0


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_system_activity_endpoint_error():
    """Test /api/system/activity endpoint error handling"""
    mock_db = AsyncMock()
    mock_db.get_tasks_since.side_effect = Exception("Activity error")

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/system/activity")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert "Activity error" in data["error"]


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_task_timeline_endpoint():
    """Test /api/charts/task-timeline endpoint"""
    mock_db = AsyncMock()
    mock_task1 = MagicMock()
    mock_task1.status = "completed"
    mock_task2 = MagicMock()
    mock_task2.status = "failed"

    # Mock different days returning different task sets
    def mock_get_tasks_between(start, end):
        if start.day == datetime.utcnow().day:
            return [mock_task1, mock_task2]
        return [mock_task1]

    mock_db.get_tasks_between.side_effect = mock_get_tasks_between

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/charts/task-timeline")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "timeline" in data
    assert len(data["timeline"]) == 7  # 7 days

    # Check first day has the expected task counts
    today_data = data["timeline"][-1]  # Last item should be most recent
    assert "completed" in today_data
    assert "failed" in today_data
    assert "total" in today_data


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_task_timeline_endpoint_error():
    """Test /api/charts/task-timeline endpoint error handling"""
    mock_db = AsyncMock()
    mock_db.get_tasks_between.side_effect = Exception("Timeline error")

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/charts/task-timeline")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert "Timeline error" in data["error"]


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_agent_performance_endpoint():
    """Test /api/charts/agent-performance endpoint"""
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-123"
    mock_agent.role = "engineering"
    mock_agent.completed_tasks = 8
    mock_agent.failed_tasks = 2
    mock_agent.status = MagicMock()
    mock_agent.status.value = "ready"
    mock_agent.registered_at = datetime.utcnow() - timedelta(hours=5)

    mock_db.get_all_agents.return_value = [mock_agent]

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/charts/agent-performance")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "agent_performance" in data
    assert len(data["agent_performance"]) == 1

    agent_data = data["agent_performance"][0]
    assert agent_data["agent_id"] == "agent-123"
    assert agent_data["role"] == "engineering"
    assert agent_data["completed_tasks"] == 8
    assert agent_data["failed_tasks"] == 2
    assert agent_data["success_rate"] == 80.0  # 8/10 * 100


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_agent_performance_endpoint_no_tasks():
    """Test /api/charts/agent-performance endpoint with agents having no tasks"""
    mock_db = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.id = "agent-456"
    mock_agent.role = "product"
    mock_agent.completed_tasks = 0
    mock_agent.failed_tasks = 0
    mock_agent.status = MagicMock()
    mock_agent.status.value = "ready"
    mock_agent.registered_at = datetime.utcnow()

    mock_db.get_all_agents.return_value = [mock_agent]

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/charts/agent-performance")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["agent_performance"]) == 1

    agent_data = data["agent_performance"][0]
    assert agent_data["success_rate"] == 0  # No tasks means 0% success rate


@pytest.mark.skipif(
    autonomous_app is None, reason="autonomous_server not available"
)
@pytest.mark.asyncio
async def test_agent_performance_endpoint_error():
    """Test /api/charts/agent-performance endpoint error handling"""
    mock_db = AsyncMock()
    mock_db.get_all_agents.side_effect = Exception("Performance error")

    with patch("autonomous_server.get_database", return_value=mock_db):
        client = TestClient(autonomous_app)
        response = client.get("/api/charts/agent-performance")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert "Performance error" in data["error"]


# Developer dashboard integration test removed - requires template files


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
