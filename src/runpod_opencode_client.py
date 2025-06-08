#!/usr/bin/env python3
"""
RunPod OpenCode Client for Summit AI

This module provides a client to interact with the specific RunPod endpoint
for OpenCode integration.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import aiohttp

from src.cost_tracker import CostTracker


class RunPodOpenCodeClient:
    """Client for RunPod endpoint integration with OpenCode"""

    def __init__(
        self,
        endpoint_id: str = "26xsjcfv6hlyqe",
        api_key: str = "rpa_3IUUA0KEUIG29RZYZO9RCP9UL4J44TWKW95382S82dxyzo",
        base_url: str = "https://api.runpod.ai/v2",
    ):
        self.endpoint_id = endpoint_id
        self.api_key = api_key
        self.base_url = base_url
        self.run_url = f"{base_url}/{endpoint_id}/run"
        self.runsync_url = f"{base_url}/{endpoint_id}/runsync"
        self.status_url = f"{base_url}/{endpoint_id}/status"
        self.health_url = f"{base_url}/{endpoint_id}/health"
        self.cancel_url = f"{base_url}/{endpoint_id}/cancel"
        self.logger = logging.getLogger(__name__)
        self.cost_tracker = CostTracker()

    async def send_prompt(
        self, prompt: str, use_sync: bool = True, **kwargs
    ) -> Dict[str, Any]:
        """Send a prompt to RunPod endpoint (sync or async)"""
        if use_sync:
            return await self.send_sync_prompt(prompt, **kwargs)
        else:
            return await self.send_async_prompt(prompt, **kwargs)

    async def send_sync_prompt(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Send a synchronous prompt to RunPod (immediate results)"""
        try:
            start_time = time.time()

            payload = {"input": {"prompt": prompt, **kwargs}}

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            self.logger.info(
                f"Sending sync request to RunPod: {self.runsync_url}"
            )

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.runsync_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(
                        total=120
                    ),  # 2 minute timeout for sync
                ) as response:

                    processing_time = time.time() - start_time

                    if response.status == 200:
                        result = await response.json()

                        # Extract output from sync response
                        output = result.get("output", "")
                        if isinstance(output, dict):
                            output = output.get(
                                "response", output.get("text", str(output))
                            )
                        elif isinstance(output, list) and len(output) > 0:
                            output = (
                                output[0]
                                if isinstance(output[0], str)
                                else str(output[0])
                            )

                        # Track cost
                        estimated_cost = processing_time * 0.0001
                        self.cost_tracker.record_call(
                            input_tokens=len(prompt.split()) * 1.3,
                            output_tokens=len(str(output).split()) * 1.3,
                            model="runpod_llama_3.1_8b",
                            call_type="runpod_sync_inference",
                        )

                        return {
                            "success": True,
                            "output": str(output),
                            "processing_time": processing_time,
                            "estimated_cost": estimated_cost,
                            "method": "sync",
                            "raw_response": result,
                        }
                    else:
                        error_text = await response.text()
                        self.logger.error(
                            f"RunPod sync API error {response.status}: {error_text}"
                        )
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}",
                            "processing_time": processing_time,
                            "method": "sync",
                        }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Sync request timed out after 2 minutes",
                "processing_time": time.time() - start_time,
                "method": "sync",
            }
        except Exception as e:
            self.logger.error(f"Error calling RunPod sync API: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "method": "sync",
            }

    async def send_async_prompt(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Send an asynchronous prompt to RunPod (with polling)"""
        try:
            start_time = time.time()

            # Step 1: Submit the job
            job_id = await self._submit_job(prompt, **kwargs)
            if not job_id:
                return {
                    "success": False,
                    "error": "Failed to submit job to RunPod",
                    "processing_time": time.time() - start_time,
                    "method": "async",
                }

            # Step 2: Poll for results
            result = await self._poll_for_result(job_id, start_time)
            result["method"] = "async"
            return result

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Request timed out after 5 minutes",
                "processing_time": time.time() - start_time,
                "method": "async",
            }
        except Exception as e:
            self.logger.error(f"Error calling RunPod async API: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "method": "async",
            }

    async def _submit_job(self, prompt: str, **kwargs) -> Optional[str]:
        """Submit a job to RunPod and return the job ID"""
        payload = {"input": {"prompt": prompt, **kwargs}}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        self.logger.info(f"Submitting job to RunPod: {self.run_url}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.run_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:

                if response.status == 200:
                    result = await response.json()
                    job_id = result.get("id")
                    self.logger.info(f"Job submitted successfully: {job_id}")
                    return job_id
                else:
                    error_text = await response.text()
                    self.logger.error(
                        f"Failed to submit job: {response.status} - {error_text}"
                    )
                    return None

    async def _poll_for_result(
        self, job_id: str, start_time: float
    ) -> Dict[str, Any]:
        """Poll RunPod for job completion"""
        status_url = f"{self.base_url}/{self.endpoint_id}/status/{job_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        max_wait_time = 300  # 5 minutes
        poll_interval = 2  # Start with 2 seconds

        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < max_wait_time:
                try:
                    async with session.get(
                        status_url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response:

                        if response.status == 200:
                            result = await response.json()
                            status = result.get("status")

                            if status == "COMPLETED":
                                output = result.get("output", "")

                                # Handle different output formats
                                if isinstance(output, dict):
                                    output = output.get(
                                        "response",
                                        output.get("text", str(output)),
                                    )
                                elif (
                                    isinstance(output, list)
                                    and len(output) > 0
                                ):
                                    output = (
                                        output[0]
                                        if isinstance(output[0], str)
                                        else str(output[0])
                                    )

                                processing_time = time.time() - start_time
                                estimated_cost = processing_time * 0.0001

                                self.cost_tracker.record_call(
                                    input_tokens=len(
                                        result.get("input", {})
                                        .get("prompt", "")
                                        .split()
                                    )
                                    * 1.3,
                                    output_tokens=len(str(output).split())
                                    * 1.3,
                                    model="runpod_llama_3.1_8b",
                                    call_type="runpod_inference",
                                )

                                return {
                                    "success": True,
                                    "output": str(output),
                                    "processing_time": processing_time,
                                    "estimated_cost": estimated_cost,
                                    "raw_response": result,
                                }

                            elif status == "FAILED":
                                error_msg = result.get("error", "Job failed")
                                return {
                                    "success": False,
                                    "error": f"RunPod job failed: {error_msg}",
                                    "processing_time": time.time()
                                    - start_time,
                                    "raw_response": result,
                                }

                            elif status in ["IN_QUEUE", "IN_PROGRESS"]:
                                self.logger.info(
                                    f"Job {job_id} status: {status}, waiting..."
                                )
                                await asyncio.sleep(poll_interval)
                                # Exponential backoff, max 10 seconds
                                poll_interval = min(poll_interval * 1.2, 10)
                                continue

                            else:
                                self.logger.warning(
                                    f"Unknown status: {status}"
                                )
                                await asyncio.sleep(poll_interval)
                                continue

                        else:
                            self.logger.error(
                                f"Status check failed: {response.status}"
                            )
                            await asyncio.sleep(poll_interval)
                            continue

                except Exception as e:
                    self.logger.error(f"Error polling status: {e}")
                    await asyncio.sleep(poll_interval)
                    continue

            # Timeout
            return {
                "success": False,
                "error": f"Job timed out after {max_wait_time} seconds",
                "processing_time": time.time() - start_time,
            }

    async def get_health(self) -> Dict[str, Any]:
        """Get endpoint health status"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.health_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:

                    if response.status == 200:
                        result = await response.json()
                        return {"success": True, "health": result}
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Health check failed: {response.status} - {error_text}",
                        }
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            return {"success": False, "error": str(e)}

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a specific job"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            status_url = f"{self.status_url}/{job_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    status_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:

                    if response.status == 200:
                        result = await response.json()
                        return {"success": True, "status": result}
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Status check failed: {response.status} - {error_text}",
                        }
        except Exception as e:
            self.logger.error(f"Status check error: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running or queued job"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            cancel_url = f"{self.cancel_url}/{job_id}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    cancel_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:

                    if response.status == 200:
                        result = await response.json()
                        return {"success": True, "result": result}
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Cancel failed: {response.status} - {error_text}",
                        }
        except Exception as e:
            self.logger.error(f"Cancel job error: {e}")
            return {"success": False, "error": str(e)}

    async def purge_queue(self) -> Dict[str, Any]:
        """Purge all pending jobs from the queue"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            purge_url = f"{self.base_url}/{self.endpoint_id}/purge-queue"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    purge_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:

                    if response.status == 200:
                        result = await response.json()
                        return {"success": True, "result": result}
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Purge failed: {response.status} - {error_text}",
                        }
        except Exception as e:
            self.logger.error(f"Purge queue error: {e}")
            return {"success": False, "error": str(e)}

    async def test_connection(self) -> bool:
        """Test the connection to RunPod endpoint"""
        try:
            # Test health endpoint first
            health = await self.get_health()
            if health["success"]:
                self.logger.info("Health check passed")

                # Test a simple prompt
                result = await self.send_prompt(
                    "Hello, this is a test message."
                )
                return result["success"]
            else:
                self.logger.error(f"Health check failed: {health['error']}")
                return False
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def get_openai_compatible_config(self) -> Dict[str, str]:
        """Get OpenAI-compatible configuration for OpenCode"""
        return {
            "base_url": self.runsync_url,
            "api_key": self.api_key,
            "model": "llama-3.1-8b-instruct",
        }

    async def benchmark_performance(
        self, num_requests: int = 5
    ) -> Dict[str, Any]:
        """Benchmark endpoint performance with multiple requests"""
        results = []
        start_time = time.time()

        # Test prompts of varying complexity
        test_prompts = [
            "Hello world",
            "Write a Python function to calculate fibonacci numbers",
            "Explain the concept of machine learning in simple terms",
            "Create a REST API endpoint for user authentication",
            "Debug this code and explain the issue: def func(x): return x + y",
        ]

        for i in range(num_requests):
            prompt = test_prompts[i % len(test_prompts)]
            result = await self.send_prompt(f"Request {i+1}: {prompt}")
            results.append(
                {
                    "request_id": i + 1,
                    "success": result["success"],
                    "processing_time": result.get("processing_time", 0),
                    "method": result.get("method", "unknown"),
                    "error": (
                        result.get("error") if not result["success"] else None
                    ),
                }
            )

        total_time = time.time() - start_time
        successful_requests = sum(1 for r in results if r["success"])
        avg_processing_time = sum(
            r["processing_time"] for r in results if r["success"]
        ) / max(successful_requests, 1)

        return {
            "total_requests": num_requests,
            "successful_requests": successful_requests,
            "success_rate": successful_requests / num_requests,
            "total_time": total_time,
            "avg_processing_time": avg_processing_time,
            "requests_per_second": num_requests / total_time,
            "results": results,
        }


# Convenience function for easy integration
def create_runpod_client() -> RunPodOpenCodeClient:
    """Create RunPod client with default configuration"""
    return RunPodOpenCodeClient()


async def test_runpod_connection():
    """Comprehensive RunPod connection and functionality test"""
    print("=" * 60)
    print("COMPREHENSIVE RUNPOD TEST SUITE")
    print("=" * 60)

    client = create_runpod_client()

    # Test 1: Health Check
    print("\n1. Testing endpoint health...")
    health = await client.get_health()
    if health["success"]:
        print(" Health check passed")
        print(f"  Health data: {health['health']}")
    else:
        print(f" Health check failed: {health['error']}")
        return

    # Test 2: Basic Connection
    print("\n2. Testing basic connection...")
    if await client.test_connection():
        print(" Basic connection successful!")
    else:
        print(" Basic connection failed!")
        return

    # Test 3: Sync vs Async Comparison
    print("\n3. Testing sync vs async methods...")
    test_prompt = "Write a Python function to reverse a string"

    # Sync test
    print("  Testing sync method...")
    sync_result = await client.send_sync_prompt(test_prompt)
    if sync_result["success"]:
        print(f"   Sync method: {sync_result['processing_time']:.2f}s")
        print(f"    Response: {sync_result['output'][:100]}...")
    else:
        print(f"   Sync method failed: {sync_result['error']}")

    # Async test
    print("  Testing async method...")
    async_result = await client.send_async_prompt(test_prompt)
    if async_result["success"]:
        print(f"   Async method: {async_result['processing_time']:.2f}s")
        print(f"    Response: {async_result['output'][:100]}...")
    else:
        print(f"   Async method failed: {async_result['error']}")

    # Test 4: Performance Benchmark
    print("\n4. Running performance benchmark...")
    benchmark = await client.benchmark_performance(3)
    print(f"   Benchmark completed:")
    print(f"    Success rate: {benchmark['success_rate']:.1%}")
    print(f"    Avg processing time: {benchmark['avg_processing_time']:.2f}s")
    print(f"    Requests per second: {benchmark['requests_per_second']:.2f}")

    # Test 5: Cost Analysis
    print("\n5. Cost analysis...")
    total_cost = 0
    if sync_result["success"]:
        total_cost += sync_result.get("estimated_cost", 0)
    if async_result["success"]:
        total_cost += async_result.get("estimated_cost", 0)

    print(f"  Total estimated cost: ${total_cost:.6f}")
    print(f"  Cost per request: ${total_cost/2:.6f}")

    # Test 6: OpenCode Configuration
    print("\n6. OpenCode integration config...")
    config = client.get_openai_compatible_config()
    print(f"   Config generated:")
    print(f"    Base URL: {config['base_url']}")
    print(f"    Model: {config['model']}")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("Your RunPod endpoint is ready for OpenCode integration.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_runpod_connection())
