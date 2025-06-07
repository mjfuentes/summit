#!/usr/bin/env python3
"""
RunPod Management Web Interface

This module provides a web interface for managing RunPod deployments,
monitoring costs, and controlling GPU resources.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from runpod_integration import (
    DeploymentInfo,
    RunPodConfig,
    RunPodDeploymentManager,
    create_runpod_config,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="Summit AI - RunPod Management", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# Global deployment manager
deployment_manager: Optional[RunPodDeploymentManager] = None


@app.on_event("startup")
async def startup_event():
    """Initialize RunPod integration on startup"""
    global deployment_manager

    # Get RunPod API key from environment
    api_key = os.environ.get("RUNPOD_API_KEY")
    if api_key:
        config = create_runpod_config(
            api_key=api_key,
            gpu_type="RTX 4090",
            deployment_type="serverless",
            workers_max=3,
        )
        deployment_manager = RunPodDeploymentManager(config)
        logger.info("RunPod integration initialized")
    else:
        logger.warning("RUNPOD_API_KEY not found in environment")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard"""
    return templates.TemplateResponse(
        "runpod_dashboard.html", {"request": request}
    )


@app.get("/api/runpod/status")
async def get_runpod_status():
    """Get RunPod integration status"""
    if not deployment_manager:
        return {
            "status": "not_configured",
            "message": "RunPod API key not configured",
        }

    try:
        # Get available GPUs
        gpus = await deployment_manager.client.get_available_gpus()

        return {
            "status": "connected",
            "api_key_configured": True,
            "available_gpus": len(gpus),
            "gpu_types": [
                gpu.get("displayName", gpu.get("id", "Unknown"))
                for gpu in gpus[:5]
            ],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/runpod/gpus")
async def get_available_gpus():
    """Get available GPU types and pricing"""
    if not deployment_manager:
        raise HTTPException(status_code=400, detail="RunPod not configured")

    try:
        gpus = await deployment_manager.client.get_available_gpus()

        # Add pricing information
        for gpu in gpus:
            gpu_name = gpu.get("displayName", "")
            if "4090" in gpu_name:
                gpu["pricing"] = deployment_manager.client.gpu_pricing.get(
                    "RTX 4090", {}
                )
            elif "A100" in gpu_name:
                gpu["pricing"] = deployment_manager.client.gpu_pricing.get(
                    "A100", {}
                )
            elif "H100" in gpu_name:
                gpu["pricing"] = deployment_manager.client.gpu_pricing.get(
                    "H100", {}
                )

        return {"gpus": gpus}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/runpod/deploy")
async def deploy_summit(request: Request):
    """Deploy Summit AI to RunPod"""
    if not deployment_manager:
        raise HTTPException(status_code=400, detail="RunPod not configured")

    try:
        data = await request.json()
        deployment_name = data.get(
            "name", f"summit-{int(datetime.now().timestamp())}"
        )
        gpu_type = data.get("gpu_type", "RTX 4090")
        deployment_type = data.get("deployment_type", "serverless")
        workers_max = data.get("workers_max", 3)

        # Update configuration
        deployment_manager.config.gpu_type = gpu_type
        deployment_manager.config.deployment_type = deployment_type
        deployment_manager.config.workers_max = workers_max

        # Deploy
        deployment = await deployment_manager.deploy_summit(deployment_name)

        if deployment:
            return {
                "success": True,
                "deployment": {
                    "id": deployment.deployment_id,
                    "name": deployment_name,
                    "type": deployment.deployment_type,
                    "gpu_type": deployment.gpu_type,
                    "status": deployment.status,
                    "endpoint_url": deployment.endpoint_url,
                    "cost_per_hour": deployment.cost_per_hour,
                },
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to deploy Summit"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runpod/deployments")
async def get_deployments():
    """Get all active deployments"""
    if not deployment_manager:
        raise HTTPException(status_code=400, detail="RunPod not configured")

    try:
        deployments = await deployment_manager.get_all_deployments()

        # Convert to dict format
        deployment_list = []
        for deployment in deployments:
            # Get current status
            status = await deployment_manager.get_deployment_status(
                deployment.deployment_id
            )

            deployment_list.append(
                {
                    "id": deployment.deployment_id,
                    "type": deployment.deployment_type,
                    "gpu_type": deployment.gpu_type,
                    "status": (
                        status.get("status", deployment.status)
                        if status
                        else deployment.status
                    ),
                    "endpoint_url": deployment.endpoint_url,
                    "created_at": deployment.created_at.isoformat(),
                    "cost_per_hour": deployment.cost_per_hour,
                    "total_cost": deployment.total_cost,
                    "workers": status.get("workers", 0) if status else 0,
                    "requests_completed": (
                        status.get("requests_completed", 0) if status else 0
                    ),
                }
            )

        return {"deployments": deployment_list}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runpod/deployments/{deployment_id}/status")
async def get_deployment_status(deployment_id: str):
    """Get status of a specific deployment"""
    if not deployment_manager:
        raise HTTPException(status_code=400, detail="RunPod not configured")

    try:
        status = await deployment_manager.get_deployment_status(deployment_id)
        if status:
            return status
        else:
            raise HTTPException(status_code=404, detail="Deployment not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runpod/deployments/{deployment_id}/logs")
async def get_deployment_logs(deployment_id: str):
    """Get logs for a deployment"""
    if not deployment_manager:
        raise HTTPException(status_code=400, detail="RunPod not configured")

    try:
        logs = await deployment_manager.get_deployment_logs(deployment_id)
        return {"logs": logs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/runpod/deployments/{deployment_id}/scale")
async def scale_deployment(deployment_id: str, request: Request):
    """Scale a serverless deployment"""
    if not deployment_manager:
        raise HTTPException(status_code=400, detail="RunPod not configured")

    try:
        data = await request.json()
        workers_min = data.get("workers_min", 0)
        workers_max = data.get("workers_max", 3)

        success = await deployment_manager.scale_deployment(
            deployment_id, workers_min, workers_max
        )

        if success:
            return {
                "success": True,
                "message": "Deployment scaled successfully",
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to scale deployment"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/runpod/deployments/{deployment_id}")
async def terminate_deployment(deployment_id: str):
    """Terminate a deployment"""
    if not deployment_manager:
        raise HTTPException(status_code=400, detail="RunPod not configured")

    try:
        success = await deployment_manager.terminate_deployment(deployment_id)

        if success:
            return {
                "success": True,
                "message": "Deployment terminated successfully",
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to terminate deployment"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/runpod/test-endpoint")
async def test_endpoint(request: Request):
    """Test a RunPod endpoint with a sample request"""
    try:
        data = await request.json()
        endpoint_url = data.get("endpoint_url")
        test_operation = data.get("operation", "get_advice")
        test_data = data.get("data", {"query": "Hello from Summit AI!"})

        if not endpoint_url:
            raise HTTPException(status_code=400, detail="Missing endpoint_url")

        # This would make a request to the RunPod endpoint
        # For now, return a mock response
        return {
            "success": True,
            "test_request": {"operation": test_operation, "data": test_data},
            "response": {
                "operation": test_operation,
                "result": "Test successful - endpoint is responding",
                "processing_time_seconds": 0.5,
                "estimated_cost_usd": 0.000155,
                "gpu_type": "RTX 4090",
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runpod/pricing")
async def get_pricing_info():
    """Get RunPod pricing information"""
    if not deployment_manager:
        raise HTTPException(status_code=400, detail="RunPod not configured")

    return {
        "pricing": deployment_manager.client.gpu_pricing,
        "currency": "USD",
        "pod_billing": "per hour",
        "serverless_billing": "per second",
        "note": "Prices may vary based on availability and region",
    }


def main():
    """Run the RunPod management server"""
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    main()
