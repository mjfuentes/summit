#!/usr/bin/env python3
"""
Comprehensive tests for RunPod OpenCode Client

Tests all functionality including sync/async methods, health checks,
job management, and error handling.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from src.runpod_opencode_client import (
    RunPodOpenCodeClient,
    create_runpod_client,
)


class TestRunPodOpenCodeClient:
    """Test suite for RunPod OpenCode Client"""

    def setup_method(self):
        """Set up test client"""
        self.client = RunPodOpenCodeClient(
            endpoint_id="test_endpoint",
            api_key="test_key",
            base_url="https://api.test.com/v2",
        )

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization with correct URLs"""
        assert self.client.endpoint_id == "test_endpoint"
        assert self.client.api_key == "test_key"
        assert (
            self.client.run_url == "https://api.test.com/v2/test_endpoint/run"
        )
        assert (
            self.client.runsync_url
            == "https://api.test.com/v2/test_endpoint/runsync"
        )
        assert (
            self.client.health_url
            == "https://api.test.com/v2/test_endpoint/health"
        )

    @pytest.mark.asyncio
    async def test_send_sync_prompt_success(self):
        """Test successful synchronous prompt"""
        mock_response = {"output": "Hello! This is a test response."}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value = mock_resp

            result = await self.client.send_sync_prompt("Hello")

            assert result["success"] is True
            assert result["output"] == "Hello! This is a test response."
            assert result["method"] == "sync"
            assert "processing_time" in result
            assert "estimated_cost" in result

    @pytest.mark.asyncio
    async def test_send_sync_prompt_with_dict_output(self):
        """Test sync prompt with dictionary output format"""
        mock_response = {
            "output": {
                "response": "This is the actual response",
                "metadata": "extra data",
            }
        }

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value = mock_resp

            result = await self.client.send_sync_prompt("Test")

            assert result["success"] is True
            assert result["output"] == "This is the actual response"

    @pytest.mark.asyncio
    async def test_send_sync_prompt_with_list_output(self):
        """Test sync prompt with list output format"""
        mock_response = {"output": ["First response", "Second response"]}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value = mock_resp

            result = await self.client.send_sync_prompt("Test")

            assert result["success"] is True
            assert result["output"] == "First response"

    @pytest.mark.asyncio
    async def test_send_sync_prompt_api_error(self):
        """Test sync prompt with API error"""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 500
            mock_resp.text = AsyncMock(return_value="Internal Server Error")
            mock_post.return_value.__aenter__.return_value = mock_resp

            result = await self.client.send_sync_prompt("Test")

            assert result["success"] is False
            assert "API error 500" in result["error"]
            assert result["method"] == "sync"

    @pytest.mark.asyncio
    async def test_send_sync_prompt_timeout(self):
        """Test sync prompt timeout"""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()

            result = await self.client.send_sync_prompt("Test")

            assert result["success"] is False
            assert "timed out" in result["error"]
            assert result["method"] == "sync"

    @pytest.mark.asyncio
    async def test_send_async_prompt_success(self):
        """Test successful asynchronous prompt"""
        job_id = "test_job_123"

        # Mock job submission
        with patch.object(self.client, "_submit_job", return_value=job_id):
            # Mock polling result
            with patch.object(self.client, "_poll_for_result") as mock_poll:
                mock_poll.return_value = {
                    "success": True,
                    "output": "Async response",
                    "processing_time": 1.5,
                    "estimated_cost": 0.0001,
                }

                result = await self.client.send_async_prompt("Test async")

                assert result["success"] is True
                assert result["output"] == "Async response"
                assert result["method"] == "async"

    @pytest.mark.asyncio
    async def test_submit_job_success(self):
        """Test successful job submission"""
        mock_response = {"id": "job_123", "status": "IN_QUEUE"}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value = mock_resp

            job_id = await self.client._submit_job("Test prompt")

            assert job_id == "job_123"

    @pytest.mark.asyncio
    async def test_submit_job_failure(self):
        """Test failed job submission"""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 400
            mock_resp.text = AsyncMock(return_value="Bad Request")
            mock_post.return_value.__aenter__.return_value = mock_resp

            job_id = await self.client._submit_job("Test prompt")

            assert job_id is None

    @pytest.mark.asyncio
    async def test_poll_for_result_completed(self):
        """Test polling for completed job"""
        job_id = "test_job"
        start_time = 1000.0

        mock_response = {
            "status": "COMPLETED",
            "output": "Job completed successfully",
            "input": {"prompt": "test prompt"},
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value = mock_resp

            with patch("time.time", return_value=1001.0):
                result = await self.client._poll_for_result(job_id, start_time)

                assert result["success"] is True
                assert result["output"] == "Job completed successfully"

    @pytest.mark.asyncio
    async def test_poll_for_result_failed(self):
        """Test polling for failed job"""
        job_id = "test_job"
        start_time = 1000.0

        mock_response = {"status": "FAILED", "error": "Job execution failed"}

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value = mock_resp

            with patch("time.time", return_value=1001.0):
                result = await self.client._poll_for_result(job_id, start_time)

                assert result["success"] is False
                assert "Job execution failed" in result["error"]

    @pytest.mark.asyncio
    async def test_get_health_success(self):
        """Test successful health check"""
        mock_health = {
            "workers": {"active": 2, "total": 5},
            "queue": {"pending": 0, "running": 1},
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_health)
            mock_get.return_value.__aenter__.return_value = mock_resp

            result = await self.client.get_health()

            assert result["success"] is True
            assert result["health"] == mock_health

    @pytest.mark.asyncio
    async def test_get_health_failure(self):
        """Test failed health check"""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 503
            mock_resp.text = AsyncMock(return_value="Service Unavailable")
            mock_get.return_value.__aenter__.return_value = mock_resp

            result = await self.client.get_health()

            assert result["success"] is False
            assert "503" in result["error"]

    @pytest.mark.asyncio
    async def test_get_job_status_success(self):
        """Test successful job status check"""
        job_id = "test_job"
        mock_status = {"id": job_id, "status": "IN_PROGRESS", "progress": 50}

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_status)
            mock_get.return_value.__aenter__.return_value = mock_resp

            result = await self.client.get_job_status(job_id)

            assert result["success"] is True
            assert result["status"] == mock_status

    @pytest.mark.asyncio
    async def test_cancel_job_success(self):
        """Test successful job cancellation"""
        job_id = "test_job"
        mock_result = {"id": job_id, "status": "CANCELLED"}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_result)
            mock_post.return_value.__aenter__.return_value = mock_resp

            result = await self.client.cancel_job(job_id)

            assert result["success"] is True
            assert result["result"] == mock_result

    @pytest.mark.asyncio
    async def test_purge_queue_success(self):
        """Test successful queue purge"""
        mock_result = {"purged": 5, "message": "Queue purged successfully"}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_result)
            mock_post.return_value.__aenter__.return_value = mock_resp

            result = await self.client.purge_queue()

            assert result["success"] is True
            assert result["result"] == mock_result

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test"""
        # Mock health check
        with patch.object(self.client, "get_health") as mock_health:
            mock_health.return_value = {"success": True, "health": {}}

            # Mock prompt test
            with patch.object(self.client, "send_prompt") as mock_prompt:
                mock_prompt.return_value = {"success": True}

                result = await self.client.test_connection()

                assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_health_failure(self):
        """Test connection test with health check failure"""
        with patch.object(self.client, "get_health") as mock_health:
            mock_health.return_value = {
                "success": False,
                "error": "Health check failed",
            }

            result = await self.client.test_connection()

            assert result is False

    def test_get_openai_compatible_config(self):
        """Test OpenAI compatible configuration"""
        config = self.client.get_openai_compatible_config()

        assert config["base_url"] == self.client.runsync_url
        assert config["api_key"] == self.client.api_key
        assert config["model"] == "llama-3.1-8b-instruct"

    @pytest.mark.asyncio
    async def test_benchmark_performance(self):
        """Test performance benchmarking"""
        # Mock successful responses
        with patch.object(self.client, "send_prompt") as mock_prompt:
            mock_prompt.return_value = {
                "success": True,
                "processing_time": 1.0,
                "method": "sync",
            }

            result = await self.client.benchmark_performance(3)

            assert result["total_requests"] == 3
            assert result["successful_requests"] == 3
            assert result["success_rate"] == 1.0
            assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_benchmark_performance_with_failures(self):
        """Test performance benchmarking with some failures"""
        responses = [
            {"success": True, "processing_time": 1.0, "method": "sync"},
            {"success": False, "error": "Test error", "processing_time": 0.5},
            {"success": True, "processing_time": 1.5, "method": "sync"},
        ]

        with patch.object(self.client, "send_prompt") as mock_prompt:
            mock_prompt.side_effect = responses

            result = await self.client.benchmark_performance(3)

            assert result["total_requests"] == 3
            assert result["successful_requests"] == 2
            assert result["success_rate"] == 2 / 3

    @pytest.mark.asyncio
    async def test_send_prompt_default_sync(self):
        """Test that send_prompt defaults to sync method"""
        with patch.object(self.client, "send_sync_prompt") as mock_sync:
            mock_sync.return_value = {"success": True, "method": "sync"}

            result = await self.client.send_prompt("Test")

            mock_sync.assert_called_once_with("Test")
            assert result["method"] == "sync"

    @pytest.mark.asyncio
    async def test_send_prompt_explicit_async(self):
        """Test send_prompt with explicit async method"""
        with patch.object(self.client, "send_async_prompt") as mock_async:
            mock_async.return_value = {"success": True, "method": "async"}

            result = await self.client.send_prompt("Test", use_sync=False)

            mock_async.assert_called_once_with("Test")
            assert result["method"] == "async"

    def test_create_runpod_client(self):
        """Test convenience function for creating client"""
        client = create_runpod_client()

        assert isinstance(client, RunPodOpenCodeClient)
        assert client.endpoint_id == "26xsjcfv6hlyqe"
        assert (
            client.api_key
            == "rpa_3IUUA0KEUIG29RZYZO9RCP9UL4J44TWKW95382S82dxyzo"
        )

    @pytest.mark.asyncio
    async def test_cost_tracking_integration(self):
        """Test that cost tracking is properly integrated"""
        mock_response = {"output": "Test response"}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value = mock_resp

            with patch.object(
                self.client.cost_tracker, "record_call"
            ) as mock_record:
                await self.client.send_sync_prompt("Test prompt")

                mock_record.assert_called_once()
                call_args = mock_record.call_args[1]
                assert call_args["model"] == "runpod_llama_3.1_8b"
                assert call_args["call_type"] == "runpod_sync_inference"

    @pytest.mark.asyncio
    async def test_error_handling_network_exception(self):
        """Test error handling for network exceptions"""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.side_effect = aiohttp.ClientError("Network error")

            result = await self.client.send_sync_prompt("Test")

            assert result["success"] is False
            assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_poll_timeout_handling(self):
        """Test polling timeout handling"""
        job_id = "test_job"
        start_time = 1000.0

        # Mock responses that never complete
        mock_response = {"status": "IN_PROGRESS"}

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value = mock_resp

            # Mock time to simulate timeout
            with patch("time.time", return_value=1400.0):  # 400 seconds later
                result = await self.client._poll_for_result(job_id, start_time)

                assert result["success"] is False
                assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_poll_for_result_with_dict_output(self):
        """Test polling with dictionary output format"""
        job_id = "test_job"
        start_time = 1000.0

        mock_response = {
            "status": "COMPLETED",
            "output": {"response": "Dict response", "metadata": "extra"},
            "input": {"prompt": "test"},
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value = mock_resp

            with patch("time.time", return_value=1001.0):
                result = await self.client._poll_for_result(job_id, start_time)

                assert result["success"] is True
                assert result["output"] == "Dict response"

    @pytest.mark.asyncio
    async def test_poll_for_result_with_list_output(self):
        """Test polling with list output format"""
        job_id = "test_job"
        start_time = 1000.0

        mock_response = {
            "status": "COMPLETED",
            "output": ["First item", "Second item"],
            "input": {"prompt": "test"},
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value = mock_resp

            with patch("time.time", return_value=1001.0):
                result = await self.client._poll_for_result(job_id, start_time)

                assert result["success"] is True
                assert result["output"] == "First item"

    @pytest.mark.asyncio
    async def test_poll_for_result_unknown_status(self):
        """Test polling with unknown status"""
        job_id = "test_job"
        start_time = 1000.0

        responses = [
            {"status": "UNKNOWN_STATUS"},
            {
                "status": "COMPLETED",
                "output": "Final result",
                "input": {"prompt": "test"},
            },
        ]

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(side_effect=responses)
            mock_get.return_value.__aenter__.return_value = mock_resp

            with patch("time.time", return_value=1001.0):
                with patch("asyncio.sleep"):  # Mock sleep to speed up test
                    result = await self.client._poll_for_result(
                        job_id, start_time
                    )

                    assert result["success"] is True
                    assert result["output"] == "Final result"

    @pytest.mark.asyncio
    async def test_poll_for_result_status_check_error(self):
        """Test polling with status check HTTP error"""
        job_id = "test_job"
        start_time = 1000.0

        responses = [
            (500, "Server Error"),  # First call fails
            (
                200,
                {
                    "status": "COMPLETED",
                    "output": "Success",
                    "input": {"prompt": "test"},
                },
            ),  # Second succeeds
        ]

        call_count = 0

        async def mock_get_side_effect(*args, **kwargs):
            nonlocal call_count
            mock_resp = AsyncMock()
            if call_count == 0:
                mock_resp.status = responses[call_count][0]
                mock_resp.text = AsyncMock(
                    return_value=responses[call_count][1]
                )
            else:
                mock_resp.status = responses[call_count][0]
                mock_resp.json = AsyncMock(
                    return_value=responses[call_count][1]
                )
            call_count += 1
            return mock_resp

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.side_effect = mock_get_side_effect

            with patch("time.time", return_value=1001.0):
                with patch("asyncio.sleep"):  # Mock sleep to speed up test
                    result = await self.client._poll_for_result(
                        job_id, start_time
                    )

                    assert result["success"] is True
                    assert result["output"] == "Success"

    @pytest.mark.asyncio
    async def test_poll_for_result_exception_handling(self):
        """Test polling with exception during status check"""
        job_id = "test_job"
        start_time = 1000.0

        call_count = 0

        async def mock_get_side_effect(*args, **kwargs):
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                raise aiohttp.ClientError("Network error")
            else:
                mock_resp = AsyncMock()
                mock_resp.status = 200
                mock_resp.json = AsyncMock(
                    return_value={
                        "status": "COMPLETED",
                        "output": "Success after error",
                        "input": {"prompt": "test"},
                    }
                )
                return mock_resp

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.side_effect = mock_get_side_effect

            with patch("time.time", return_value=1001.0):
                with patch("asyncio.sleep"):  # Mock sleep to speed up test
                    result = await self.client._poll_for_result(
                        job_id, start_time
                    )

                    assert result["success"] is True
                    assert result["output"] == "Success after error"

    @pytest.mark.asyncio
    async def test_send_async_prompt_submit_failure(self):
        """Test async prompt when job submission fails"""
        with patch.object(self.client, "_submit_job", return_value=None):
            result = await self.client.send_async_prompt("Test prompt")

            assert result["success"] is False
            assert "Failed to submit job" in result["error"]
            assert result["method"] == "async"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
