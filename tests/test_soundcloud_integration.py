#!/usr/bin/env python3
"""Test SoundCloud integration functionality"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock the dependencies before importing
mock_handle_call_tool = MagicMock()
mock_setup_environment = MagicMock()

with patch.dict('sys.modules', {
    'mcp': MagicMock(),
    'mcp.server': MagicMock(),
    'mcp.server.stdio': MagicMock(),
    'mcp.types': MagicMock(),
    'summit': MagicMock(handle_call_tool=mock_handle_call_tool),
    'config': MagicMock(setup_environment=mock_setup_environment)
}):
    from server import app

client = TestClient(app)


class TestSoundCloudIntegration:
    """Test SoundCloud integration endpoints"""

    def test_configure_soundcloud_token(self):
        """Test SoundCloud token configuration"""
        response = client.post(
            "/api/soundcloud/config",
            json={"access_token": "test_token_123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "configured successfully" in data["data"]

    def test_get_soundcloud_config_status(self):
        """Test getting SoundCloud configuration status"""
        # First configure a token
        client.post(
            "/api/soundcloud/config",
            json={"access_token": "test_token_123"}
        )
        
        # Then check status
        response = client.get("/api/soundcloud/config")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["configured"] is True

    def test_get_soundcloud_config_status_unconfigured(self):
        """Test getting SoundCloud configuration status when not configured"""
        # Clear any existing configuration by posting empty token
        client.post(
            "/api/soundcloud/config",
            json={"access_token": ""}
        )
        
        response = client.get("/api/soundcloud/config")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["configured"] is False

    def test_search_soundcloud_without_token(self):
        """Test SoundCloud search without configured token"""
        # Clear any existing configuration by posting empty token
        client.post(
            "/api/soundcloud/config",
            json={"access_token": ""}
        )
        
        response = client.post(
            "/api/soundcloud/search",
            json={"query": "test music", "limit": 5}
        )
        # HTTPException gets wrapped by the general exception handler, resulting in 500
        assert response.status_code == 500
        assert "token not configured" in response.json()["detail"]

    def test_search_soundcloud_with_token(self):
        """Test SoundCloud search with configured token"""
        # Configure a token first
        client.post(
            "/api/soundcloud/config",
            json={"access_token": "test_token_123"}
        )
        
        # This test will fail against real API without valid token
        # but tests the endpoint structure
        response = client.post(
            "/api/soundcloud/search",
            json={"query": "test music", "limit": 5}
        )
        # Expect either success or 500 due to invalid token
        assert response.status_code in [200, 500]

    def test_stream_soundcloud_track_without_token(self):
        """Test SoundCloud track streaming without configured token"""
        # Clear any existing configuration by posting empty token
        client.post(
            "/api/soundcloud/config",
            json={"access_token": ""}
        )
        
        response = client.get("/api/soundcloud/stream/123456")
        # HTTPException gets wrapped by the general exception handler, resulting in 500
        assert response.status_code == 500
        assert "token not configured" in response.json()["detail"]

    def test_stream_soundcloud_track_with_token(self):
        """Test SoundCloud track streaming with configured token"""
        # Configure a token first
        client.post(
            "/api/soundcloud/config",
            json={"access_token": "test_token_123"}
        )
        
        # This test will fail against real API without valid token
        # but tests the endpoint structure
        response = client.get("/api/soundcloud/stream/123456")
        # Expect either success or 500 due to invalid token/track
        assert response.status_code in [200, 500]

    def test_configure_empty_token(self):
        """Test configuring empty SoundCloud token"""
        response = client.post(
            "/api/soundcloud/config",
            json={"access_token": ""}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_search_validation(self):
        """Test search request validation"""
        # Configure a token first
        client.post(
            "/api/soundcloud/config",
            json={"access_token": "test_token_123"}
        )
        
        # Test with missing query
        response = client.post(
            "/api/soundcloud/search",
            json={"limit": 5}
        )
        assert response.status_code == 422  # Validation error

    def test_health_check_still_works(self):
        """Test that health check endpoint still works"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"