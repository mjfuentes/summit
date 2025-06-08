#!/usr/bin/env python3
"""
Remote Deployment Manager for Claude Code Instances

This module manages deployment of Claude Code instances to various cloud
platforms including Render.com, RunPod, and other providers.
"""

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

import requests


class DeploymentError(Exception):
    """Custom exception for deployment errors"""


class RemoteDeploymentManager:
    """Manages remote deployments of Claude Code instances"""

    def __init__(self):
        self.deployments = {}
        self.supported_platforms = ["render"]

    async def deploy_to_render(
        self,
        service_name: str,
        environment_vars: Dict[str, str],
        plan: str = "starter",
    ) -> Dict[str, Union[str, bool]]:
        """Deploy Claude Code instance to Render.com"""
        try:
            render_api_key = os.getenv("RENDER_API_KEY")
            if not render_api_key:
                raise DeploymentError(
                    "RENDER_API_KEY not found in environment variables"
                )

            # Prepare deployment configuration
            deployment_config = {
                "type": "web_service",
                "name": service_name,
                "repo": f"https://github.com/{os.getenv('GITHUB_REPOSITORY', 'mjfuentes/summit')}",
                "branch": "main",
                "buildCommand": (
                    "pip install -r requirements.txt && "
                    "cp requirements.txt web/ && "
                    "chmod +x web/claude_code_task.sh"
                ),
                "startCommand": "python start_server.py",
                "envVars": [
                    {"key": key, "value": value}
                    for key, value in environment_vars.items()
                ],
                "serviceDetails": {
                    "plan": plan,
                    "region": "oregon",
                    "healthCheckPath": "/health",
                },
            }

            # Create service via Render API
            headers = {
                "Authorization": f"Bearer {render_api_key}",
                "Content-Type": "application/json",
            }

            response = requests.post(
                "https://api.render.com/v1/services",
                headers=headers,
                json=deployment_config,
                timeout=30,
            )

            if response.status_code == 201:
                service_data = response.json()
                deployment_id = service_data.get("id")
                service_url = service_data.get("serviceDetails", {}).get("url")

                # Store deployment info
                self.deployments[deployment_id] = {
                    "platform": "render",
                    "service_name": service_name,
                    "deployment_id": deployment_id,
                    "service_url": service_url,
                    "status": "deploying",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }

                return {
                    "success": True,
                    "deployment_id": deployment_id,
                    "service_url": service_url,
                    "status": "deploying",
                }
            else:
                raise DeploymentError(
                    f"Render deployment failed: {
                        response.status_code} - {
                        response.text}"
                )

        except requests.RequestException as e:
            raise DeploymentError(
                f"Network error during Render deployment: {e}"
            )
        except Exception as e:
            raise DeploymentError(
                f"Unexpected error during Render deployment: {e}"
            )

    async def get_deployment_status(
        self, deployment_id: str
    ) -> Optional[Dict[str, str]]:
        """Get status of a deployment"""
        if deployment_id not in self.deployments:
            return None

        deployment = self.deployments[deployment_id]
        platform = deployment["platform"]

        try:
            if platform == "render":
                return await self._get_render_status(deployment_id)
            else:
                return {"status": "unknown", "platform": platform}

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "platform": platform,
            }

    async def _get_render_status(self, deployment_id: str) -> Dict[str, str]:
        """Get Render service status"""
        render_api_key = os.getenv("RENDER_API_KEY")
        if not render_api_key:
            return {"status": "error", "error": "No API key"}

        headers = {"Authorization": f"Bearer {render_api_key}"}
        response = requests.get(
            f"https://api.render.com/v1/services/{deployment_id}",
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "status": data.get("serviceDetails", {}).get(
                    "status", "unknown"
                ),
                "url": data.get("serviceDetails", {}).get("url"),
                "platform": "render",
            }
        else:
            return {
                "status": "error",
                "error": f"API error: {response.status_code}",
            }

    async def list_deployments(self) -> List[Dict[str, str]]:
        """List all deployments"""
        deployments = []
        for deployment_id, deployment in self.deployments.items():
            status = await self.get_deployment_status(deployment_id)
            deployment_info = deployment.copy()
            if status:
                deployment_info.update(status)
            deployments.append(deployment_info)
        return deployments

    async def delete_deployment(self, deployment_id: str) -> bool:
        """Delete a deployment"""
        if deployment_id not in self.deployments:
            return False

        deployment = self.deployments[deployment_id]
        platform = deployment["platform"]

        try:
            if platform == "render":
                return await self._delete_render_service(deployment_id)
            else:
                return False

        except Exception:
            return False
        finally:
            # Remove from local tracking
            if deployment_id in self.deployments:
                del self.deployments[deployment_id]

    async def _delete_render_service(self, deployment_id: str) -> bool:
        """Delete Render service"""
        render_api_key = os.getenv("RENDER_API_KEY")
        if not render_api_key:
            return False

        headers = {"Authorization": f"Bearer {render_api_key}"}
        response = requests.delete(
            f"https://api.render.com/v1/services/{deployment_id}",
            headers=headers,
            timeout=10,
        )

        return response.status_code == 204

    def create_deployment_config(
        self,
        task_description: str,
        repository_url: Optional[str] = None,
        target_branch: str = "main",
        timeout_minutes: int = 60,
    ) -> Dict[str, str]:
        """Create environment variables for deployment"""
        config = {
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
            "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
            "TASK_DESCRIPTION": task_description,
            "TARGET_BRANCH": target_branch,
            "TIMEOUT_MINUTES": str(timeout_minutes),
            "SUMMIT_ENV": "production",
            "SUMMIT_READONLY_MODE": "false",
            "PORT": "8000",
        }

        if repository_url:
            config["REPOSITORY_URL"] = repository_url

        return config

    async def deploy_claude_code_instance(
        self,
        platform: str,
        task_description: str,
        repository_url: Optional[str] = None,
        target_branch: str = "main",
        timeout_minutes: int = 60,
        **platform_kwargs,
    ) -> Dict[str, Union[str, bool]]:
        """Deploy a Claude Code instance to specified platform"""
        if platform not in self.supported_platforms:
            raise DeploymentError(
                f"Unsupported platform: {platform}. "
                f"Supported: {', '.join(self.supported_platforms)}"
            )

        # Create deployment configuration
        env_vars = self.create_deployment_config(
            task_description, repository_url, target_branch, timeout_minutes
        )

        # Generate unique service name
        timestamp = int(time.time())
        service_name = f"claude-code-{platform}-{timestamp}"

        # Deploy to specified platform
        if platform == "render":
            return await self.deploy_to_render(
                service_name, env_vars, **platform_kwargs
            )
        else:
            raise DeploymentError(f"Platform {platform} not implemented")

    async def monitor_deployment(
        self, deployment_id: str, check_interval: int = 30
    ) -> None:
        """Monitor a deployment until it's ready or fails"""
        print(f"Monitoring deployment {deployment_id}...")

        while True:
            status = await self.get_deployment_status(deployment_id)
            if not status:
                print(f"Deployment {deployment_id} not found")
                break

            current_status = status.get("status", "unknown")
            print(f"Status: {current_status}")

            if current_status in ["live", "deployed", "running"]:
                print(f"Deployment {deployment_id} is ready!")
                if "url" in status:
                    print(f"URL: {status['url']}")
                break
            elif current_status in ["failed", "error"]:
                print(f"Deployment {deployment_id} failed!")
                if "error" in status:
                    print(f"Error: {status['error']}")
                break

            await asyncio.sleep(check_interval)


# CLI interface for the deployment manager
async def main():
    """Main CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Deploy Claude Code instances remotely"
    )
    parser.add_argument(
        "platform",
        choices=["render"],
        help="Deployment platform",
    )
    parser.add_argument(
        "task_description", help="Description of the task for Claude Code"
    )
    parser.add_argument(
        "--repository-url", help="Git repository URL to work with"
    )
    parser.add_argument(
        "--target-branch", default="main", help="Git branch to work on"
    )
    parser.add_argument(
        "--timeout-minutes",
        type=int,
        default=60,
        help="Task timeout in minutes",
    )

    args = parser.parse_args()

    manager = RemoteDeploymentManager()

    try:
        # Deploy Claude Code instance
        result = await manager.deploy_claude_code_instance(
            platform=args.platform,
            task_description=args.task_description,
            repository_url=args.repository_url,
            target_branch=args.target_branch,
            timeout_minutes=args.timeout_minutes,
        )

        if result["success"]:
            print(f"Deployment successful!")
            print(f"Deployment ID: {result['deployment_id']}")
            if "service_url" in result:
                print(f"Service URL: {result['service_url']}")
            if "endpoint_url" in result:
                print(f"Endpoint URL: {result['endpoint_url']}")

        else:
            print(f"Deployment failed: {result}")

    except DeploymentError as e:
        print(f"Deployment error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
