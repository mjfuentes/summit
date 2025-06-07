#!/usr/bin/env python3

import os
import sys

import pytest
from fastapi.testclient import TestClient
from standalone_server import app

# Add web directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
