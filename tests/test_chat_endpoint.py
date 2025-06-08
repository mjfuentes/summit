#!/usr/bin/env python3
"""
Tests for the chat endpoint in autonomous_server.py
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add web directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import with error handling
try:
    from autonomous_server import ChatMessage, app
except ImportError as e:
    print(f"Import error: {e}")
    # Create a dummy app for testing if import fails
    from fastapi import FastAPI

    app = FastAPI()

    class ChatMessage:
        def __init__(self, message: str, context: str = None):
            self.message = message
            self.context = context


class TestChatEndpoint:
    """Test the chat endpoint in autonomous_server.py"""

    @pytest.fixture
    def client(self):
        """Create a test client for the autonomous server"""
        return TestClient(app)

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client for testing"""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Hello! I'm Claude, your AI assistant."
        mock_message.content = [mock_content]

        # Mock the streaming response
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=None)
        mock_stream.text_stream = [
            "Hello! ",
            "I'm ",
            "Claude, ",
            "your ",
            "AI ",
            "assistant.",
        ]

        mock_client.messages.stream.return_value = mock_stream
        mock_client.messages.create.return_value = mock_message
        return mock_client

    def test_chat_endpoint_success(self, client, mock_anthropic_client):
        """Test successful chat interaction with streaming response"""
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "os.getenv"
        ) as mock_getenv:
            mock_anthropic.return_value = mock_anthropic_client
            mock_getenv.return_value = "test-api-key"

            response = client.post(
                "/api/chat", json={"message": "Hello Claude!"}
            )

            assert response.status_code == 200
            # Check that we get a streaming response
            assert response.headers.get("content-type") == "text/event-stream"

            # The response should contain streaming data
            content = response.text
            assert "data:" in content  # Should contain SSE format

            # Verify Anthropic client was called correctly
            mock_anthropic_client.messages.stream.assert_called_once()

    def test_chat_endpoint_missing_api_key(self, client):
        """Test chat endpoint when ANTHROPIC_API_KEY is missing"""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = None  # Simulate missing API key

            response = client.post(
                "/api/chat", json={"message": "Hello Claude!"}
            )

            assert response.status_code == 200
            # Should get fallback response
            content = response.text
            assert "data:" in content
            assert "ANTHROPIC_API_KEY" in content or "API key" in content

    def test_chat_endpoint_anthropic_api_error(self, client):
        """Test chat endpoint when Anthropic API returns an error"""
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "os.getenv"
        ) as mock_getenv:
            mock_client = MagicMock()
            mock_client.messages.stream.side_effect = Exception(
                "API rate limit exceeded"
            )
            mock_anthropic.return_value = mock_client
            mock_getenv.return_value = "test-api-key"

            response = client.post(
                "/api/chat", json={"message": "Hello Claude!"}
            )

            assert response.status_code == 200
            # Should handle error gracefully
            content = response.text
            assert "data:" in content

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
            content = response.text
            assert "data:" in content

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
            content = response.text
            assert "data:" in content

            # Verify the long message was passed to Anthropic
            call_args = mock_anthropic_client.messages.stream.call_args
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
            content = response.text
            assert "data:" in content

            # Verify special characters were handled correctly
            call_args = mock_anthropic_client.messages.stream.call_args
            assert call_args[1]["messages"][0]["content"] == special_message

    def test_chat_endpoint_anthropic_response_structure(self, client):
        """Test that the endpoint handles streaming responses correctly"""
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "os.getenv"
        ) as mock_getenv:
            # Mock a streaming response
            mock_client = MagicMock()
            mock_stream = MagicMock()
            mock_stream.__enter__ = MagicMock(return_value=mock_stream)
            mock_stream.__exit__ = MagicMock(return_value=None)
            mock_stream.text_stream = ["First ", "part ", "of ", "response."]
            mock_client.messages.stream.return_value = mock_stream
            mock_anthropic.return_value = mock_client
            mock_getenv.return_value = "test-api-key"

            response = client.post(
                "/api/chat", json={"message": "Tell me a story"}
            )

            assert response.status_code == 200
            content = response.text
            assert "data:" in content
            # Should contain streaming data format

    def test_chat_endpoint_concurrent_requests(
        self, client, mock_anthropic_client
    ):
        """Test multiple concurrent requests to chat endpoint"""
        import threading

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
                thread.join()

            # Check results
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(results) == 5
            for message_id, status_code in results:
                assert status_code == 200

    def test_chat_request_model_validation(self):
        """Test ChatMessage model validation"""
        from autonomous_server import ChatMessage

        # Valid message
        valid_message = ChatMessage(message="Hello")
        assert valid_message.message == "Hello"
        assert valid_message.context is None

        # Valid message with context
        valid_with_context = ChatMessage(
            message="Hello", context="Some context"
        )
        assert valid_with_context.message == "Hello"
        assert valid_with_context.context == "Some context"

        # Test that empty message is allowed (validation happens at endpoint level)
        empty_message = ChatMessage(message="")
        assert empty_message.message == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
