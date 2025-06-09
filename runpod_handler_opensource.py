#!/usr/bin/env python3
"""
RunPod Serverless Handler for Summit AI with Open Source Models

This script handles incoming requests to Summit AI when deployed on RunPod
serverless infrastructure using open source models like Llama 3.1, Code Llama,
and Mistral for cost-effective AI operations.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

import runpod
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Add src to path
sys.path.insert(0, "/workspace/src")

from cost_tracker import CostTracker
from open_source_models import RunPodOpenSourceHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get model configuration from environment
MODEL_ID = os.environ.get("SUMMIT_MODEL_ID", "code-llama-13b")
logger.info(f"Initializing with model: {MODEL_ID}")

# Initialize open source model handler
model_handler = RunPodOpenSourceHandler(MODEL_ID)
cost_tracker = CostTracker()

# FastAPI app for health checks and direct API access
app = FastAPI(title="Summit AI - RunPod Open Source", version="1.0.0")

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
        "service": "summit-ai-runpod-opensource",
        "model_id": MODEL_ID,
        "gpu_available": torch.cuda.is_available(),
        "gpu_count": (
            torch.cuda.device_count() if torch.cuda.is_available() else 0
        ),
        "gpu_name": (
            torch.cuda.get_device_name(0)
            if torch.cuda.is_available()
            else None
        ),
        "timestamp": time.time(),
    }


@app.get("/info")
async def get_info():
    """Get system and model information"""
    model_info = model_handler.model_manager.get_model_info()

    return {
        "service": "Summit AI on RunPod (Open Source)",
        "model_info": model_info,
        "system_info": {
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
        },
        "cost_info": {
            "daily_spent": cost_tracker.get_daily_spent(),
            "daily_budget": cost_tracker.daily_budget,
            "hourly_spent": cost_tracker.get_hourly_spent(),
            "hourly_budget": cost_tracker.hourly_budget,
        },
    }


@app.post("/api/advice")
async def get_advice_endpoint(request: dict):
    """Direct API endpoint for getting advice"""
    try:
        question = request.get("question", "")
        context = request.get("context")

        if not question:
            raise HTTPException(
                status_code=400, detail="Missing 'question' field"
            )

        response = await model_handler.model_manager.generate_response(
            question, context
        )

        return {
            "success": True,
            "response": response,
            "model_info": model_handler.model_manager.get_model_info(),
        }
    except Exception as e:
        logger.error(f"Error in advice endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_code_endpoint(request: dict):
    """Direct API endpoint for code analysis"""
    try:
        code = request.get("code", "")
        language = request.get("language", "python")

        if not code:
            raise HTTPException(status_code=400, detail="Missing 'code' field")

        analysis = await model_handler.model_manager.analyze_code(
            code, language
        )

        return {
            "success": True,
            "analysis": analysis,
            "model_info": model_handler.model_manager.get_model_info(),
        }
    except Exception as e:
        logger.error(f"Error in analyze endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def summit_handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler for Summit AI operations on RunPod with open source models

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

        logger.info(
            f"Processing operation: {operation} with model: {MODEL_ID}"
        )

        if not operation:
            return {
                "error": "Missing 'operation' field in job input",
                "valid_operations": [
                    "get_advice",
                    "create_task",
                    "analyze_code",
                    "review_pr",
                ],
                "model_id": MODEL_ID,
            }

        # Use the open source model handler
        result = await model_handler.handle_request(job_input)

        # Add RunPod-specific metadata
        result.update(
            {
                "runpod_job_id": job.get("id", "unknown"),
                "model_id": MODEL_ID,
                "gpu_type": "RTX 4090",  # Default for RunPod
                "timestamp": time.time(),
            }
        )

        logger.info(
            f"Completed operation {operation} in {time.time() - start_time:.2f}s"
        )
        return result

    except Exception as e:
        logger.error(f"Error processing job: {e}")
        return {
            "error": str(e),
            "operation": job.get("input", {}).get("operation", "unknown"),
            "processing_time_seconds": time.time() - start_time,
            "model_id": MODEL_ID,
        }


def sync_summit_handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous wrapper for the async handler"""
    return asyncio.run(summit_handler(job))


async def start_web_server():
    """Start the FastAPI web server for direct API access"""
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def initialize_model():
    """Initialize the open source model"""
    logger.info(f"Initializing open source model: {MODEL_ID}")

    try:
        success = await model_handler.initialize()
        if success:
            logger.info(f"Model {MODEL_ID} initialized successfully")

            # Test the model with a simple query
            test_response = (
                await model_handler.model_manager.generate_response(
                    "Hello, this is a test. Please respond briefly."
                )
            )
            logger.info(f"Model test successful: {test_response[:100]}...")

            return True
        else:
            logger.error(f"Failed to initialize model {MODEL_ID}")
            return False

    except Exception as e:
        logger.error(f"Error initializing model: {e}")
        return False


def main():
    """Main entry point"""
    logger.info("Starting Summit AI on RunPod with Open Source Models")
    logger.info(f"Model: {MODEL_ID}")
    logger.info(f"GPU Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"GPU Count: {torch.cuda.device_count()}")
        logger.info(f"GPU Name: {torch.cuda.get_device_name(0)}")

    # Initialize the model first
    if not asyncio.run(initialize_model()):
        logger.error("Failed to initialize model, exiting")
        sys.exit(1)

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
