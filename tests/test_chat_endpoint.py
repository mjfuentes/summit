#!/usr/bin/env python3
"""
Tests for the chat endpoint in autonomous_server.py
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add web directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestChatEndpoint:
    """Test cases for the /api/chat endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client with mocked dependencies"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            # Import here to avoid import issues
            from autonomous_server import app

            return TestClient(app)

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client for testing"""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock()]
        mock_message.content[0].text = "Hello! I'm Claude, how can I help you?"
        mock_client.messages.create.return_value = mock_message
        return mock_client

    def test_chat_endpoint_success(self, client, mock_anthropic_client):
        """Test successful chat interaction"""
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "os.getenv"
        ) as mock_getenv:
            mock_anthropic.return_value = mock_anthropic_client
            mock_getenv.return_value = "test-api-key"

            response = client.post(
                "/api/chat", json={"message": "Hello Claude!"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Hello! I'm Claude" in data["response"]
            assert "error" not in data or data["error"] is None

            # Verify Anthropic client was called correctly
            mock_anthropic_client.messages.create.assert_called_once()
            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args[1]["model"] == "claude-3-5-sonnet-20241022"
            assert call_args[1]["max_tokens"] == 1000
            assert len(call_args[1]["messages"]) == 1
            assert call_args[1]["messages"][0]["role"] == "user"
            assert call_args[1]["messages"][0]["content"] == "Hello Claude!"

    def test_chat_endpoint_missing_api_key(self, client):
        """Test chat endpoint when ANTHROPIC_API_KEY is missing"""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = None  # Simulate missing API key

            response = client.post(
                "/api/chat", json={"message": "Hello Claude!"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "ANTHROPIC_API_KEY not configured" in data["error"]
            assert "response" not in data or data["response"] is None

    def test_chat_endpoint_anthropic_api_error(self, client):
        """Test chat endpoint when Anthropic API returns an error"""
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "os.getenv"
        ) as mock_getenv:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception(
                "API rate limit exceeded"
            )
            mock_anthropic.return_value = mock_client
            mock_getenv.return_value = "test-api-key"

            response = client.post(
                "/api/chat", json={"message": "Hello Claude!"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "API rate limit exceeded" in data["error"]
            assert "response" not in data or data["response"] is None

    def test_chat_endpoint_empty_message(self, client, mock_anthropic_client):
        """Test chat endpoint with empty message"""
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "os.getenv"
        ) as mock_getenv:
            mock_anthropic.return_value = mock_anthropic_client
            mock_getenv.return_value = "test-api-key"

            response = client.post("/api/chat", json={"message": ""})

            assert response.status_code == 200
            # Should still process empty message
            data = response.json()
            assert data["success"] is True

    def test_chat_endpoint_missing_message_field(self, client):
        """Test chat endpoint with missing message field"""
        response = client.post("/api/chat", json={})

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
        # FastAPI validation error for missing required field

    def test_chat_endpoint_invalid_json(self, client):
        """Test chat endpoint with invalid JSON"""
        response = client.post(
            "/api/chat",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422  # Validation error

    def test_chat_endpoint_long_message(self, client, mock_anthropic_client):
        """Test chat endpoint with very long message"""
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "os.getenv"
        ) as mock_getenv:
            mock_anthropic.return_value = mock_anthropic_client
            mock_getenv.return_value = "test-api-key"

            long_message = "A" * 10000  # 10k character message
            response = client.post("/api/chat", json={"message": long_message})

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify the long message was passed to Anthropic
            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args[1]["messages"][0]["content"] == long_message

    def test_chat_endpoint_special_characters(
        self, client, mock_anthropic_client
    ):
        """Test chat endpoint with special characters and unicode"""
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "os.getenv"
        ) as mock_getenv:
            mock_anthropic.return_value = mock_anthropic_client
            mock_getenv.return_value = "test-api-key"

            special_message = "Hello!  Testing unicode: αβγ and symbols: @#$%"
            response = client.post(
                "/api/chat", json={"message": special_message}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify special characters were handled correctly
            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args[1]["messages"][0]["content"] == special_message

    def test_chat_endpoint_anthropic_response_structure(self, client):
        """Test that the endpoint handles different Anthropic response structures"""
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "os.getenv"
        ) as mock_getenv:
            # Mock a response with multiple content blocks
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_content_1 = MagicMock()
            mock_content_1.text = "First part of response. "
            mock_content_2 = MagicMock()
            mock_content_2.text = "Second part of response."
            mock_message.content = [mock_content_1, mock_content_2]
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.return_value = mock_client
            mock_getenv.return_value = "test-api-key"

            response = client.post(
                "/api/chat", json={"message": "Tell me a story"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # Should use only the first content block (current implementation)
            assert "First part of response" in data["response"]

    def test_chat_endpoint_concurrent_requests(
        self, client, mock_anthropic_client
    ):
        """Test multiple concurrent requests to chat endpoint"""
        import threading
        import time

        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "os.getenv"
        ) as mock_getenv:
            mock_anthropic.return_value = mock_anthropic_client
            mock_getenv.return_value = "test-api-key"

            results = []
            errors = []

            def make_request(message_id):
                try:
                    response = client.post(
                        "/api/chat", json={"message": f"Message {message_id}"}
                    )
                    results.append((message_id, response.status_code))
                except Exception as e:
                    errors.append((message_id, str(e)))

            # Create multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=make_request, args=(i,))
                threads.append(thread)

            # Start all threads
            for thread in threads:
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=10)

            # Verify all requests succeeded
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(results) == 5
            for message_id, status_code in results:
                assert status_code == 200

    def test_chat_request_model_validation(self):
        """Test ChatRequest model validation"""
        from autonomous_server import ChatRequest

        # Valid request
        valid_request = ChatRequest(message="Hello")
        assert valid_request.message == "Hello"

        # Test with empty string (should be valid)
        empty_request = ChatRequest(message="")
        assert empty_request.message == ""

        # Test validation error for missing message
        with pytest.raises(Exception):  # Pydantic validation error
            ChatRequest()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
