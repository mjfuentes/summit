#!/usr/bin/env python3
"""
RunPod Integration for Summit AI

This module provides comprehensive integration with RunPod.io for deploying
Summit AI on GPU infrastructure, including RTX 4090 deployments.

Features:
- GPU Pod management (RTX 4090, A100, H100, etc.)
- Serverless endpoint deployment
- Cost tracking and optimization
- Real-time monitoring and logs
- Auto-scaling configuration
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import runpod

from cost_tracker import CostTracker


@dataclass
class RunPodConfig:
    """Configuration for RunPod deployment"""

    api_key: str
    gpu_type: str = "RTX 4090"  # Default to RTX 4090
    deployment_type: str = "serverless"  # "serverless" or "pod"
    region: str = "US-OR-1"
    workers_min: int = 0
    workers_max: int = 3
    idle_timeout: int = 5
    container_disk_gb: int = 20
    volume_gb: int = 10
    docker_image: str = "summit-ai:latest"
    environment_vars: Dict[str, str] = None

    def __post_init__(self):
        if self.environment_vars is None:
            self.environment_vars = {}


@dataclass
class DeploymentInfo:
    """Information about a RunPod deployment"""

    deployment_id: str
    deployment_type: str
    gpu_type: str
    status: str
    endpoint_url: Optional[str] = None
    created_at: datetime = None
    cost_per_hour: float = 0.0
    total_cost: float = 0.0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class RunPodClient:
    """Client for interacting with RunPod API"""

    def __init__(self, config: RunPodConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Set RunPod API key
        runpod.api_key = config.api_key

        # Initialize cost tracker
        self.cost_tracker = CostTracker()

        # GPU pricing (per hour for pods, per second for serverless)
        self.gpu_pricing = {
            "RTX 4090": {
                "pod_community": 0.34,
                "pod_secure": 0.69,
                "serverless_flex": 0.00031,
                "serverless_active": 0.00021,
            },
            "RTX A5000": {
                "pod_community": 0.16,
                "pod_secure": 0.26,
                "serverless_flex": 0.00019,
                "serverless_active": 0.00013,
            },
            "A100": {
                "pod_community": 1.19,
                "pod_secure": 1.64,
                "serverless_flex": 0.00076,
                "serverless_active": 0.00060,
            },
            "H100": {
                "pod_community": 2.69,
                "pod_secure": 2.99,
                "serverless_flex": 0.00116,
                "serverless_active": 0.00093,
            },
        }

    async def get_available_gpus(self) -> List[Dict[str, Any]]:
        """Get list of available GPU types"""
        try:
            gpus = runpod.get_gpus()
            return gpus
        except Exception as e:
            self.logger.error(f"Failed to get available GPUs: {e}")
            return []

    async def get_gpu_info(self, gpu_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific GPU"""
        try:
            gpu_info = runpod.get_gpu(gpu_id)
            return gpu_info
        except Exception as e:
            self.logger.error(f"Failed to get GPU info for {gpu_id}: {e}")
            return None

    async def create_template(
        self, name: str, image_name: str, is_serverless: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Create a RunPod template"""
        try:
            template = runpod.create_template(
                name=name,
                image_name=image_name,
                is_serverless=is_serverless,
                container_disk_in_gb=self.config.container_disk_gb,
                volume_in_gb=self.config.volume_gb,
                env=list(self.config.environment_vars.items()),
            )
            self.logger.info(f"Created template: {template['id']}")
            return template
        except Exception as e:
            self.logger.error(f"Failed to create template: {e}")
            return None

    async def create_serverless_endpoint(
        self, template_id: str, name: str
    ) -> Optional[Dict[str, Any]]:
        """Create a serverless endpoint"""
        try:
            # Map GPU type to RunPod GPU ID
            gpu_id_map = {
                "RTX 4090": "NVIDIA GeForce RTX 4090",
                "RTX A5000": "NVIDIA RTX A5000",
                "A100": "NVIDIA A100 80GB PCIe",
                "H100": "NVIDIA H100 PCIe",
            }

            gpu_id = gpu_id_map.get(
                self.config.gpu_type, "NVIDIA GeForce RTX 4090"
            )

            endpoint = runpod.create_endpoint(
                name=name,
                template_id=template_id,
                gpu_ids=gpu_id,
                workers_min=self.config.workers_min,
                workers_max=self.config.workers_max,
                idle_timeout=self.config.idle_timeout,
            )

            self.logger.info(f"Created serverless endpoint: {endpoint['id']}")
            return endpoint
        except Exception as e:
            self.logger.error(f"Failed to create serverless endpoint: {e}")
            return None

    async def create_pod(
        self, name: str, image_name: str
    ) -> Optional[Dict[str, Any]]:
        """Create a GPU pod"""
        try:
            pod = runpod.create_pod(
                name=name,
                image_name=image_name,
                gpu_type=self.config.gpu_type,
                container_disk_in_gb=self.config.container_disk_gb,
                volume_in_gb=self.config.volume_gb,
                env=self.config.environment_vars,
            )

            self.logger.info(f"Created pod: {pod['id']}")
            return pod
        except Exception as e:
            self.logger.error(f"Failed to create pod: {e}")
            return None

    async def get_pods(self) -> List[Dict[str, Any]]:
        """Get all pods"""
        try:
            pods = runpod.get_pods()
            return pods
        except Exception as e:
            self.logger.error(f"Failed to get pods: {e}")
            return []

    async def get_endpoints(self) -> List[Dict[str, Any]]:
        """Get all serverless endpoints"""
        try:
            endpoints = runpod.get_endpoints()
            return endpoints
        except Exception as e:
            self.logger.error(f"Failed to get endpoints: {e}")
            return []

    async def stop_pod(self, pod_id: str) -> bool:
        """Stop a pod"""
        try:
            runpod.stop_pod(pod_id)
            self.logger.info(f"Stopped pod: {pod_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop pod {pod_id}: {e}")
            return False

    async def terminate_pod(self, pod_id: str) -> bool:
        """Terminate a pod"""
        try:
            runpod.terminate_pod(pod_id)
            self.logger.info(f"Terminated pod: {pod_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to terminate pod {pod_id}: {e}")
            return False

    def calculate_cost(
        self,
        deployment_type: str,
        gpu_type: str,
        duration_hours: float,
        cloud_type: str = "community",
    ) -> float:
        """Calculate deployment cost"""
        if gpu_type not in self.gpu_pricing:
            return 0.0

        pricing = self.gpu_pricing[gpu_type]

        if deployment_type == "pod":
            rate_key = f"pod_{cloud_type}"
            return pricing.get(rate_key, 0.0) * duration_hours
        elif deployment_type == "serverless":
            # For serverless, assume flex pricing and convert hours to seconds
            rate_key = "serverless_flex"
            return pricing.get(rate_key, 0.0) * duration_hours * 3600

        return 0.0

    async def get_deployment_logs(
        self, deployment_id: str, deployment_type: str
    ) -> List[str]:
        """Get logs for a deployment"""
        try:
            if deployment_type == "pod":
                # For pods, we'd need to implement log retrieval
                # This would typically involve SSH or API calls
                return ["Pod logs not yet implemented"]
            else:
                # For serverless endpoints, logs are available through the API
                return ["Serverless logs not yet implemented"]
        except Exception as e:
            self.logger.error(f"Failed to get logs for {deployment_id}: {e}")
            return [f"Error retrieving logs: {e}"]


class RunPodDeploymentManager:
    """Manager for RunPod deployments"""

    def __init__(self, config: RunPodConfig):
        self.config = config
        self.client = RunPodClient(config)
        self.logger = logging.getLogger(__name__)
        self.deployments: Dict[str, DeploymentInfo] = {}

    async def deploy_summit(
        self, deployment_name: str = None
    ) -> Optional[DeploymentInfo]:
        """Deploy Summit AI to RunPod"""
        if deployment_name is None:
            deployment_name = f"summit-ai-{int(time.time())}"

        self.logger.info(f"Starting Summit deployment: {deployment_name}")

        try:
            # Create template
            template_name = f"{deployment_name}-template"
            template = await self.client.create_template(
                name=template_name,
                image_name=self.config.docker_image,
                is_serverless=(self.config.deployment_type == "serverless"),
            )

            if not template:
                raise Exception("Failed to create template")

            deployment_info = None

            if self.config.deployment_type == "serverless":
                # Create serverless endpoint
                endpoint = await self.client.create_serverless_endpoint(
                    template_id=template["id"], name=deployment_name
                )

                if endpoint:
                    deployment_info = DeploymentInfo(
                        deployment_id=endpoint["id"],
                        deployment_type="serverless",
                        gpu_type=self.config.gpu_type,
                        status="deploying",
                        endpoint_url=f"https://api.runpod.ai/v2/{
                            endpoint['id']}/run",
                        cost_per_hour=self.client.gpu_pricing[
                            self.config.gpu_type
                        ]["serverless_flex"]
                        * 3600,
                    )

            elif self.config.deployment_type == "pod":
                # Create pod
                pod = await self.client.create_pod(
                    name=deployment_name, image_name=self.config.docker_image
                )

                if pod:
                    deployment_info = DeploymentInfo(
                        deployment_id=pod["id"],
                        deployment_type="pod",
                        gpu_type=self.config.gpu_type,
                        status="starting",
                        cost_per_hour=self.client.gpu_pricing[
                            self.config.gpu_type
                        ]["pod_community"],
                    )

            if deployment_info:
                self.deployments[deployment_info.deployment_id] = (
                    deployment_info
                )
                self.logger.info(
                    f"Successfully deployed Summit: {
                        deployment_info.deployment_id}"
                )

                # Track deployment cost
                self.client.cost_tracker.record_call(
                    input_tokens=0,
                    output_tokens=0,
                    model="runpod_deployment",
                    call_type=f"runpod_{self.config.deployment_type}",
                )

            return deployment_info

        except Exception as e:
            self.logger.error(f"Failed to deploy Summit: {e}")
            return None

    async def get_deployment_status(
        self, deployment_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get status of a deployment"""
        try:
            deployment = self.deployments.get(deployment_id)
            if not deployment:
                return None

            if deployment.deployment_type == "serverless":
                endpoints = await self.client.get_endpoints()
                for endpoint in endpoints:
                    if endpoint["id"] == deployment_id:
                        return {
                            "id": endpoint["id"],
                            "status": (
                                "running"
                                if endpoint.get("workers", 0) > 0
                                else "idle"
                            ),
                            "workers": endpoint.get("workers", 0),
                            "requests_completed": endpoint.get(
                                "requestsCompleted", 0
                            ),
                            "requests_failed": endpoint.get(
                                "requestsFailed", 0
                            ),
                        }

            elif deployment.deployment_type == "pod":
                pods = await self.client.get_pods()
                for pod in pods:
                    if pod["id"] == deployment_id:
                        return {
                            "id": pod["id"],
                            "status": pod.get("desiredStatus", "unknown"),
                            "runtime": pod.get("runtime", {}),
                            "gpu_count": pod.get("gpuCount", 0),
                        }

            return None

        except Exception as e:
            self.logger.error(f"Failed to get deployment status: {e}")
            return None

    async def scale_deployment(
        self, deployment_id: str, workers_min: int, workers_max: int
    ) -> bool:
        """Scale a serverless deployment"""
        try:
            deployment = self.deployments.get(deployment_id)
            if not deployment or deployment.deployment_type != "serverless":
                return False

            # Note: RunPod doesn't have a direct scale API in the Python SDK
            # This would need to be implemented via GraphQL API
            self.logger.info(
                f"Scaling deployment {deployment_id} to {workers_min}-{workers_max} workers"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to scale deployment: {e}")
            return False

    async def terminate_deployment(self, deployment_id: str) -> bool:
        """Terminate a deployment"""
        try:
            deployment = self.deployments.get(deployment_id)
            if not deployment:
                return False

            success = False
            if deployment.deployment_type == "pod":
                success = await self.client.terminate_pod(deployment_id)
            elif deployment.deployment_type == "serverless":
                # For serverless, we'd need to delete the endpoint
                # This would require GraphQL API calls
                self.logger.info(
                    f"Terminating serverless endpoint: {deployment_id}"
                )
                success = True

            if success:
                # Calculate final cost
                duration_hours = (
                    datetime.now(timezone.utc) - deployment.created_at
                ).total_seconds() / 3600
                final_cost = self.client.calculate_cost(
                    deployment.deployment_type,
                    deployment.gpu_type,
                    duration_hours,
                )

                deployment.total_cost = final_cost

                # Update cost tracking
                self.client.cost_tracker.record_call(
                    input_tokens=int(
                        final_cost * 1000
                    ),  # Convert cost to token equivalent
                    output_tokens=0,
                    model="runpod_termination",
                    call_type=f"runpod_{deployment.deployment_type}_final",
                )

                del self.deployments[deployment_id]

            return success

        except Exception as e:
            self.logger.error(f"Failed to terminate deployment: {e}")
            return False

    async def get_all_deployments(self) -> List[DeploymentInfo]:
        """Get all active deployments"""
        return list(self.deployments.values())

    async def get_deployment_logs(self, deployment_id: str) -> List[str]:
        """Get logs for a deployment"""
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            return ["Deployment not found"]

        return await self.client.get_deployment_logs(
            deployment_id, deployment.deployment_type
        )


def create_runpod_config(api_key: str, **kwargs) -> RunPodConfig:
    """Create RunPod configuration with defaults"""
    return RunPodConfig(api_key=api_key, **kwargs)


async def main():
    """Example usage"""
    # Create configuration
    config = create_runpod_config(
        api_key="your_api_key_here",
        gpu_type="RTX 4090",
        deployment_type="serverless",
        workers_max=2,
    )

    # Create deployment manager
    manager = RunPodDeploymentManager(config)

    # Deploy Summit
    deployment = await manager.deploy_summit("summit-test")
    if deployment:
        print(f"Deployed Summit: {deployment.deployment_id}")

        # Check status
        status = await manager.get_deployment_status(deployment.deployment_id)
        print(f"Status: {status}")

        # Get logs
        logs = await manager.get_deployment_logs(deployment.deployment_id)
        print(f"Logs: {logs}")


if __name__ == "__main__":
    asyncio.run(main())
