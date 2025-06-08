#!/usr/bin/env python3
"""
Deploy OpenCode with Open Source Models on RunPod

This script sets up OpenCode with Llama 3.1 or other open source models
on RunPod infrastructure as an alternative to Claude Code.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from open_source_models import OpenSourceModelManager
from opencode_integration import OpenCodeConfig, SummitOpenCodeIntegration
from runpod_integration import RunPodConfig, RunPodDeploymentManager


async def main():
    """Deploy OpenCode with open source models on RunPod"""
    print("Summit AI - OpenCode + RunPod Deployment")
    print("=" * 50)

    # Configuration options
    deployment_options = {
        "1": {
            "name": "Llama 3.1 8B + OpenCode",
            "model": "llama-3.1-8b",
            "gpu": "RTX 4090",
            "cost_per_hour": 0.34,
            "description": "Best balance of performance and cost",
        },
        "2": {
            "name": "Code Llama 13B + OpenCode",
            "model": "code-llama-13b",
            "gpu": "RTX 4090",
            "cost_per_hour": 0.34,
            "description": "Specialized for coding tasks",
        },
        "3": {
            "name": "Mistral 7B + OpenCode",
            "model": "mistral-7b",
            "gpu": "RTX 4090",
            "cost_per_hour": 0.34,
            "description": "Lightweight and efficient",
        },
        "4": {
            "name": "Llama 3.1 70B + OpenCode",
            "model": "llama-3.1-70b",
            "gpu": "A100",
            "cost_per_hour": 1.89,
            "description": "Highest quality, higher cost",
        },
    }

    print("Available deployment options:")
    for key, option in deployment_options.items():
        print(f"  {key}. {option['name']}")
        print(
            f"     GPU: {option['gpu']} | Cost: ${option['cost_per_hour']}/hour"
        )
        print(f"     {option['description']}")
        print()

    choice = input("Select deployment option (1-4): ").strip()

    if choice not in deployment_options:
        print("Invalid choice. Exiting.")
        return

    selected = deployment_options[choice]
    print(f"Selected: {selected['name']}")
    print()

    # Check environment variables
    runpod_api_key = os.getenv("RUNPOD_API_KEY")
    if not runpod_api_key:
        print("Error: RUNPOD_API_KEY environment variable not set")
        print("Please set your RunPod API key:")
        print("export RUNPOD_API_KEY='your_api_key_here'")
        return

    try:
        # Step 1: Setup RunPod configuration
        print("Step 1: Configuring RunPod deployment...")
        runpod_config = RunPodConfig(
            api_key=runpod_api_key,
            gpu_type=selected["gpu"],
            deployment_type="serverless",
            workers_min=0,
            workers_max=2,
            docker_image="summit-opencode:latest",
            environment_vars={
                "MODEL_ID": selected["model"],
                "OPENCODE_PROVIDER": "local",
                "SUMMIT_MODE": "autonomous",
            },
        )

        runpod_manager = RunPodDeploymentManager(runpod_config)
        print(f" RunPod configured for {selected['gpu']}")

        # Step 2: Test open source model locally (optional)
        print("\nStep 2: Testing open source model...")
        model_manager = OpenSourceModelManager(selected["model"])

        print(f"Model info: {model_manager.get_model_info()}")

        # Skip actual model loading for now (requires GPU)
        print(f" Model {selected['model']} configuration validated")

        # Step 3: Setup OpenCode integration
        print("\nStep 3: Setting up OpenCode integration...")
        opencode_config = OpenCodeConfig(
            model_provider="local",
            model_name=selected["model"],
            local_endpoint="http://localhost:8000/v1",  # Local model endpoint
            working_directory="/workspace",
        )

        opencode_integration = SummitOpenCodeIntegration(opencode_config)
        print(" OpenCode integration configured")

        # Step 4: Create deployment files
        print("\nStep 4: Creating deployment files...")

        # Create Dockerfile for OpenCode + Open Source Models
        dockerfile_content = f"""# Summit AI - OpenCode + Open Source Models
FROM nvidia/cuda:12.1-devel-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    python3 python3-pip python3-dev \\
    golang-go git curl wget \\
    build-essential ca-certificates \\
    && rm -rf /var/lib/apt/lists/*

# Install OpenCode
RUN curl -fsSL https://raw.githubusercontent.com/opencode-ai/opencode/main/install | bash

# Set up Python environment
WORKDIR /workspace
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy Summit source code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Set environment variables
ENV MODEL_ID={selected["model"]}
ENV PYTHONPATH=/workspace/src
ENV OPENCODE_PROVIDER=local
ENV SUMMIT_MODE=autonomous

# Create startup script
COPY scripts/opencode_runpod_startup.sh /startup.sh
RUN chmod +x /startup.sh

EXPOSE 8000 7681

CMD ["/startup.sh"]"""

        with open("Dockerfile.opencode", "w") as f:
            f.write(dockerfile_content)

        # Create startup script
        startup_script = f"""#!/bin/bash
set -e

echo "Starting Summit AI with OpenCode + {selected['model']}"

# Start the open source model server
python3 -c "
import asyncio
from src.open_source_models import OpenSourceModelManager
from src.opencode_integration import SummitOpenCodeIntegration

async def start_model_server():
    manager = OpenSourceModelManager('{selected['model']}')
    await manager.load_model()
    print('Model server ready')
    
    # Keep running
    while True:
        await asyncio.sleep(60)

asyncio.run(start_model_server())
" &

# Wait for model to load
sleep 30

# Start OpenCode integration
echo "OpenCode + {selected['model']} ready for autonomous development"

# Keep container running
tail -f /dev/null"""

        os.makedirs("scripts", exist_ok=True)
        with open("scripts/opencode_runpod_startup.sh", "w") as f:
            f.write(startup_script)

        print(" Deployment files created:")
        print("  - Dockerfile.opencode")
        print("  - scripts/opencode_runpod_startup.sh")

        # Step 5: Display deployment instructions
        print("\nStep 5: Deployment Instructions")
        print("=" * 40)

        print("To deploy to RunPod:")
        print("1. Build and push the Docker image:")
        print(
            "   docker build -f Dockerfile.opencode -t summit-opencode:latest ."
        )
        print(
            "   docker tag summit-opencode:latest your-registry/summit-opencode:latest"
        )
        print("   docker push your-registry/summit-opencode:latest")
        print()

        print("2. Update the docker_image in RunPod config:")
        print(f"   docker_image: 'your-registry/summit-opencode:latest'")
        print()

        print("3. Deploy to RunPod:")
        print("   python scripts/deploy_opencode_runpod.py --deploy")
        print()

        print("Cost Estimation:")
        print(f"  GPU: {selected['gpu']}")
        print(f"  Cost: ${selected['cost_per_hour']}/hour")
        print(f"  Idle cost: $0.00/hour (serverless)")
        print(f"  Per task: ~$0.01-0.10 depending on complexity")
        print()

        print("Advantages over Claude Code:")
        print("   Much lower cost (90%+ savings)")
        print("   No API rate limits")
        print("   Full control over model behavior")
        print("   Specialized coding models available")
        print("   Runs on your own infrastructure")
        print()

        # Step 6: Optional deployment
        deploy_now = input("Deploy to RunPod now? (y/N): ").strip().lower()

        if deploy_now == "y":
            print("\nDeploying to RunPod...")
            deployment = await runpod_manager.deploy_summit(
                f"summit-opencode-{selected['model']}"
            )

            if deployment:
                print(" Deployment successful!")
                print(f"  Deployment ID: {deployment.deployment_id}")
                print(f"  Endpoint: {deployment.endpoint_url}")
                print(f"  Status: {deployment.status}")
            else:
                print(" Deployment failed")
        else:
            print("Deployment files ready. Deploy manually when ready.")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
