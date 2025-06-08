#!/usr/bin/env python3
"""
RunPod Serverless Handler for Summit AI

This script handles incoming requests to Summit AI when deployed on RunPod
serverless infrastructure. It provides a standardized interface for AI
operations while leveraging GPU acceleration.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

import runpod
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from cost_tracker import CostTracker
from summit import Summit
from unified_database import get_database, init_database

# Add src to path
sys.path.insert(0, "/workspace/src")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Summit AI
summit = Summit()
cost_tracker = CostTracker()

# FastAPI app for health checks and direct API access
app = FastAPI(title="Summit AI - RunPod", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "summit-ai-runpod",
        "gpu_available": os.environ.get("CUDA_VISIBLE_DEVICES") is not None,
        "timestamp": time.time(),
    }


@app.get("/info")
async def get_info():
    """Get system information"""
    import torch

    return {
        "service": "Summit AI on RunPod",
        "cuda_available": torch.cuda.is_available(),
        "gpu_count": (
            torch.cuda.device_count() if torch.cuda.is_available() else 0
        ),
        "gpu_name": (
            torch.cuda.get_device_name(0)
            if torch.cuda.is_available()
            else None
        ),
        "python_version": sys.version,
        "runpod_version": runpod.__version__,
    }


async def summit_handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler for Summit AI operations on RunPod

    Expected job input format:
    {
        "operation": "get_advice" | "create_task" | "analyze_code" | "review_pr",
        "data": {
            # Operation-specific data
        }
    }
    """
    start_time = time.time()

    try:
        job_input = job.get("input", {})
        operation = job_input.get("operation")
        data = job_input.get("data", {})

        logger.info(f"Processing operation: {operation}")

        if not operation:
            return {
                "error": "Missing 'operation' field in job input",
                "valid_operations": [
                    "get_advice",
                    "create_task",
                    "analyze_code",
                    "review_pr",
                ],
            }

        result = None

        if operation == "get_advice":
            # Get AI advice from Claude
            query = data.get("query", "")
            if not query:
                return {
                    "error": "Missing 'query' field for get_advice operation"
                }

            advice = await summit.get_advice_from_claude(query)
            result = {
                "operation": "get_advice",
                "advice": advice,
                "query": query,
            }

        elif operation == "create_task":
            # Create an autonomous task
            description = data.get("description", "")
            if not description:
                return {
                    "error": "Missing 'description' field for create_task operation"
                }

            # This would integrate with the autonomous task system
            task_id = f"runpod-task-{int(time.time())}"
            result = {
                "operation": "create_task",
                "task_id": task_id,
                "description": description,
                "status": "created",
                "message": "Task created successfully on RunPod",
            }

        elif operation == "analyze_code":
            # Analyze code quality and suggest improvements
            code = data.get("code", "")
            language = data.get("language", "python")

            if not code:
                return {
                    "error": "Missing 'code' field for analyze_code operation"
                }

            # Use Summit's AI capabilities for code analysis
            analysis_prompt = f"""
            Analyze this {language} code and provide:
            1. Code quality assessment
            2. Potential bugs or issues
            3. Performance improvements
            4. Best practices recommendations

            Code:
            ```{language}
            {code}
            ```
            """

            analysis = await summit.get_advice_from_claude(analysis_prompt)
            result = {
                "operation": "analyze_code",
                "language": language,
                "analysis": analysis,
                "code_length": len(code),
            }

        elif operation == "review_pr":
            # Review a pull request
            pr_data = data.get("pr_data", {})
            if not pr_data:
                return {
                    "error": "Missing 'pr_data' field for review_pr operation"
                }

            # This would integrate with the PR review system
            result = {
                "operation": "review_pr",
                "pr_id": pr_data.get("id", "unknown"),
                "review": "PR review functionality not yet implemented on RunPod",
                "status": "pending",
            }

        else:
            return {
                "error": f"Unknown operation: {operation}",
                "valid_operations": [
                    "get_advice",
                    "create_task",
                    "analyze_code",
                    "review_pr",
                ],
            }

        # Calculate processing time and cost
        processing_time = time.time() - start_time

        # Track cost (assuming RTX 4090 serverless pricing)
        cost = processing_time * 0.00031  # $0.00031 per second

        cost_tracker.record_call(
            input_tokens=int(
                processing_time * 100
            ),  # Convert time to token equivalent
            output_tokens=int(cost * 1000),  # Convert cost to token equivalent
            model="runpod_handler",
            call_type=f"runpod_{operation}",
        )

        # Add metadata to result
        result.update(
            {
                "processing_time_seconds": processing_time,
                "estimated_cost_usd": cost,
                "gpu_type": "RTX 4090",
                "timestamp": time.time(),
            }
        )

        logger.info(
            f"Completed operation {operation} in {processing_time:.2f}s"
        )
        return result

    except Exception as e:
        logger.error(f"Error processing job: {e}")
        return {
            "error": str(e),
            "operation": job.get("input", {}).get("operation", "unknown"),
            "processing_time_seconds": time.time() - start_time,
        }


def sync_summit_handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous wrapper for the async handler"""
    return asyncio.run(summit_handler(job))


async def start_web_server():
    """Start the FastAPI web server for health checks"""
    config = uvicorn.Config(
        app=app, host="0.0.0.0", port=8000, log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


def main():
    """Main entry point"""
    logger.info("Starting Summit AI on RunPod")

    # Check if running in RunPod serverless mode
    if os.environ.get("RUNPOD_ENDPOINT_ID"):
        logger.info("Running in RunPod serverless mode")
        # Start the RunPod serverless worker
        runpod.serverless.start(
            {"handler": sync_summit_handler, "return_aggregate_stream": True}
        )
    else:
        logger.info("Running in standalone mode")
        # Start the web server for direct API access
        asyncio.run(start_web_server())


if __name__ == "__main__":
    main()
