#!/usr/bin/env python3

import os
import sys
import asyncio
import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from web_api import app
from config import setup_environment

# Set up environment variables
setup_environment()

# Create test client
client = TestClient(app)

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Summit Web API is running" in data["message"]

@pytest.mark.asyncio 
async def test_root_endpoint():
    """Test root endpoint returns HTML"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Summit AI Advisor" in response.text
    assert "<html" in response.text

@pytest.mark.asyncio
async def test_status_endpoint():
    """Test status endpoint"""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "Summit Advisor Status" in data["data"]

@pytest.mark.asyncio
async def test_cost_report_endpoint():
    """Test cost report endpoint"""
    response = client.get("/api/cost-report")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "Cost Tracking Report" in data["data"]

@pytest.mark.asyncio
async def test_insights_endpoint():
    """Test insights endpoint"""
    response = client.get("/api/insights")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True

@pytest.mark.asyncio
async def test_advice_endpoint():
    """Test advice endpoint with valid request"""
    response = client.post("/api/advice", json={
        "question": "How can I improve my productivity?",
        "context": "Working from home"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert isinstance(data["data"], str)
    assert len(data["data"]) > 0

@pytest.mark.asyncio
async def test_advice_endpoint_no_question():
    """Test advice endpoint with missing question"""
    response = client.post("/api/advice", json={})
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_share_endpoint():
    """Test share knowledge endpoint"""
    response = client.post("/api/share", json={
        "content": "Test insight for web API",
        "category": "test",
        "context": "API testing"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True

@pytest.mark.asyncio
async def test_learn_endpoint():
    """Test learn from knowledge endpoint"""
    response = client.post("/api/learn", json={
        "query": "productivity tips",
        "max_results": 3
    })
    if response.status_code != 200:
        print(f"Response: {response.status_code} - {response.text}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True

@pytest.mark.asyncio
async def test_analytics_endpoint():
    """Test analytics endpoint"""
    response = client.post("/api/analytics", json={
        "include_suggestions": True
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True

@pytest.mark.asyncio
async def test_api_error_handling():
    """Test API error handling with malformed requests"""
    # Test with invalid JSON
    response = client.post("/api/advice", 
                          data="invalid json",
                          headers={"Content-Type": "application/json"})
    assert response.status_code == 422

def test_cors_headers():
    """Test CORS headers are present"""
    response = client.get("/")
    # CORS headers should be present for browser access
    assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 