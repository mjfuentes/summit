#!/usr/bin/env python3
"""
Deploy Summit AI to RunPod

This script deploys Summit AI to RunPod infrastructure using your RTX 4090 deployment.
"""

import asyncio
import os
import sys
import time
from datetime import datetime

from runpod_integration import RunPodDeploymentManager, create_runpod_config

# Add src to path
sys.path.insert(0, "src")


async def main():
    """Deploy Summit AI to RunPod"""
    print(" Summit AI - RunPod Deployment")
    print("=" * 50)

    # Your RunPod API key
    api_key = "***REMOVED***"

    # Create configuration for RTX 4090 deployment
    config = create_runpod_config(
        api_key=api_key,
        gpu_type="RTX 4090",
        deployment_type="serverless",  # Use serverless for cost efficiency
        workers_min=0,  # Scale to zero when not in use
        workers_max=2,  # Maximum 2 workers for your deployment
        idle_timeout=5,  # 5 seconds idle timeout
        container_disk_gb=20,  # 20GB container disk
        volume_gb=10,  # 10GB volume
        docker_image="summit-ai:latest",  # We'll need to build and push this
        environment_vars={
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
            "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
            "RUNPOD_DEPLOYMENT": "true",
        },
    )

    print(f" Configuration:")
    print(f"   GPU Type: {config.gpu_type}")
    print(f"   Deployment Type: {config.deployment_type}")
    print(f"   Workers: {config.workers_min}-{config.workers_max}")
    print(f"   Container Disk: {config.container_disk_gb}GB")
    print(f"   Volume: {config.volume_gb}GB")
    print()

    # Create deployment manager
    manager = RunPodDeploymentManager(config)

    try:
        # Check RunPod connection
        print(" Checking RunPod connection...")
        gpus = await manager.client.get_available_gpus()
        print(f" Connected to RunPod - {len(gpus)} GPU types available")

        # Find RTX 4090 pricing
        rtx_4090_info = None
        for gpu in gpus:
            if "4090" in gpu.get("displayName", ""):
                rtx_4090_info = gpu
                break

        if rtx_4090_info:
            print(f" RTX 4090 Pricing:")
            pricing = manager.client.gpu_pricing.get("RTX 4090", {})
            print(
                f"   Serverless Flex: ${pricing.get('serverless_flex', 0):.5f}/second"
            )
            print(
                f"   Serverless Active: ${pricing.get('serverless_active', 0):.5f}/second"
            )
            print(
                f"   Pod Community: ${pricing.get('pod_community', 0):.2f}/hour"
            )
            print()

        # Deploy Summit
        deployment_name = f"summit-ai-{int(time.time())}"
        print(f" Deploying Summit AI as '{deployment_name}'...")

        deployment = await manager.deploy_summit(deployment_name)

        if deployment:
            print(" Deployment successful!")
            print(f"   Deployment ID: {deployment.deployment_id}")
            print(f"   Type: {deployment.deployment_type}")
            print(f"   GPU: {deployment.gpu_type}")
            print(f"   Status: {deployment.status}")
            if deployment.endpoint_url:
                print(f"   Endpoint URL: {deployment.endpoint_url}")
            print(f"   Cost per hour: ${deployment.cost_per_hour:.4f}")
            print()

            # Wait a moment and check status
            print(" Checking deployment status...")
            await asyncio.sleep(5)

            status = await manager.get_deployment_status(
                deployment.deployment_id
            )
            if status:
                print(f" Current Status:")
                for key, value in status.items():
                    print(f"   {key}: {value}")
                print()

            # Test the deployment (mock for now)
            print(" Testing deployment...")
            print("   (This would send a test request to the endpoint)")
            print("   Test operation: get_advice")
            print("   Test query: 'Hello from Summit AI on RunPod!'")
            print("   Expected response: AI advice with cost tracking")
            print()

            print(" Summit AI is now running on RunPod!")
            print(f" To interact with your deployment:")
            print(f"   1. Use the endpoint URL: {deployment.endpoint_url}")
            print(f"   2. Send POST requests with operation and data")
            print(f"   3. Monitor costs and scaling in RunPod console")
            print()
            print(f" Estimated costs:")
            print(f"   Idle (0 workers): $0.00/hour")
            print(
                f"   Active (1 worker): ${deployment.cost_per_hour:.4f}/hour"
            )
            print(f"   Per request: ~$0.001-0.01 depending on processing time")

        else:
            print(" Deployment failed!")
            return 1

    except Exception as e:
        print(f" Error: {e}")
        return 1

    return 0


def build_docker_image():
    """Build the Docker image for RunPod deployment"""
    print(" Building Docker image for RunPod...")

    # For now, just show the commands needed
    print(" To build and push the Docker image:")
    print("   1. docker build -f deployment/docker/Dockerfile.runpod -t summit-ai:latest .")
    print("   2. docker tag summit-ai:latest your-registry/summit-ai:latest")
    print("   3. docker push your-registry/summit-ai:latest")
    print(
        "   4. Update docker_image in config to your-registry/summit-ai:latest"
    )
    print()


def show_usage_examples():
    """Show examples of how to use the deployed Summit AI"""
    print(" Usage Examples:")
    print()
    print("1. Get AI Advice:")
    print(
        """
    curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run" \\
      -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \\
      -H "Content-Type: application/json" \\
      -d '{
        "input": {
          "operation": "get_advice",
          "data": {
            "query": "How do I optimize Python code for GPU processing?"
          }
        }
      }'
    """
    )

    print("2. Analyze Code:")
    print(
        """
    curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run" \\
      -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \\
      -H "Content-Type: application/json" \\
      -d '{
        "input": {
          "operation": "analyze_code",
          "data": {
            "code": "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
            "language": "python"
          }
        }
      }'
    """
    )

    print("3. Create Task:")
    print(
        """
    curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run" \\
      -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \\
      -H "Content-Type: application/json" \\
      -d '{
        "input": {
          "operation": "create_task",
          "data": {
            "description": "Optimize database queries in the user service"
          }
        }
      }'
    """
    )


if __name__ == "__main__":
    print("Summit AI - RunPod Deployment Script")
    print("====================================")
    print()

    # Check environment variables
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("  Warning: ANTHROPIC_API_KEY not set in environment")

    if not os.environ.get("GITHUB_TOKEN"):
        print("  Warning: GITHUB_TOKEN not set in environment")

    print()

    # Show Docker build info
    build_docker_image()

    # Run deployment
    exit_code = asyncio.run(main())

    if exit_code == 0:
        print()
        show_usage_examples()

    sys.exit(exit_code)
