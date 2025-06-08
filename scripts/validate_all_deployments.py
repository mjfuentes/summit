#!/usr/bin/env python3
"""
Summit Cloud Deployment Validation Tool

This script validates all Summit deployments across different cloud platforms:
- GitHub Container Registry images
- Render.com deployments
- RunPod deployments
- Kubernetes/GCP deployments
- CI/CD pipeline status
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests


# Color codes for output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN} {message}{Colors.END}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED} {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW} {message}{Colors.END}")


def run_command(cmd: List[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def check_github_container_registry():
    """Check GitHub Container Registry images"""
    print_section("GitHub Container Registry Status")

    images_to_check = [
        "ghcr.io/mjfuentes/summit/opencode:latest",
        "ghcr.io/mjfuentes/summit/summit:latest",
    ]

    all_good = True

    for image in images_to_check:
        print(f"\nChecking image: {image}")

        # Check if image exists
        cmd = ["docker", "manifest", "inspect", image]
        code, stdout, stderr = run_command(cmd)

        if code == 0:
            try:
                manifest = json.loads(stdout)
                size = manifest.get("config", {}).get("size", "unknown")
                print_success(f"Image accessible - Size: {size} bytes")

                # Get image creation date
                created = manifest.get("config", {}).get("digest", "unknown")
                print(f"  Digest: {created}")

            except json.JSONDecodeError:
                print_warning("Image exists but could not parse manifest")
        else:
            print_error(f"Image not accessible: {stderr}")
            all_good = False

    return all_good


def check_github_workflows():
    """Check GitHub Actions workflow status"""
    print_section("GitHub Actions CI/CD Status")

    # Check if GitHub CLI is available
    code, _, _ = run_command(["gh", "--version"])
    if code != 0:
        print_error("GitHub CLI not available - cannot check workflow status")
        return False

    workflows = ["ci.yml", "claude-code-deploy.yml", "summit-autodeploy.yml"]

    all_good = True

    for workflow in workflows:
        print(f"\nChecking workflow: {workflow}")

        cmd = [
            "gh",
            "run",
            "list",
            "--workflow",
            workflow,
            "--limit",
            "1",
            "--json",
            "status,conclusion,createdAt,url,headBranch",
        ]

        code, stdout, stderr = run_command(cmd)

        if code == 0:
            try:
                runs = json.loads(stdout)
                if runs:
                    run = runs[0]
                    status = run.get("status", "unknown")
                    conclusion = run.get("conclusion", "N/A")
                    branch = run.get("headBranch", "unknown")
                    created = run.get("createdAt", "unknown")

                    if status == "completed" and conclusion == "success":
                        print_success(
                            f"Status: {status} | Conclusion: {conclusion}"
                        )
                    elif status == "in_progress":
                        print_warning(f"Status: {status} (running)")
                    else:
                        print_error(
                            f"Status: {status} | Conclusion: {conclusion}"
                        )
                        all_good = False

                    print(f"  Branch: {branch}")
                    print(f"  Created: {created}")
                else:
                    print_warning("No recent runs found")
            except json.JSONDecodeError:
                print_error("Could not parse workflow status")
                all_good = False
        else:
            print_error(f"Failed to get workflow status: {stderr}")
            all_good = False

    return all_good


async def check_render_deployments():
    """Check Render.com deployments"""
    print_section("Render.com Deployment Status")

    render_api_key = os.getenv("RENDER_API_KEY")
    if not render_api_key:
        print_error("RENDER_API_KEY not set - cannot check Render deployments")
        return False

    try:
        # Import the remote deployment manager
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
        from remote_deployment_manager import RemoteDeploymentManager

        manager = RemoteDeploymentManager()
        deployments = await manager.list_deployments()

        if not deployments:
            print_warning("No Render deployments found")
            return True

        all_good = True
        for deployment in deployments:
            name = deployment.get("service_name", "unknown")
            status = deployment.get("status", "unknown")
            url = deployment.get("service_url", "N/A")

            print(f"\nService: {name}")

            if status in ["live", "deployed", "running"]:
                print_success(f"Status: {status}")
            else:
                print_error(f"Status: {status}")
                all_good = False

            if url != "N/A":
                print(f"  URL: {url}")

                # Test health endpoint
                try:
                    response = requests.get(f"{url}/health", timeout=10)
                    if response.status_code == 200:
                        print_success("Health check passed")
                    else:
                        print_warning(
                            f"Health check failed: {response.status_code}"
                        )
                except requests.RequestException as e:
                    print_warning(f"Health check failed: {e}")

        return all_good

    except ImportError as e:
        print_error(f"Could not import deployment manager: {e}")
        return False
    except Exception as e:
        print_error(f"Error checking Render deployments: {e}")
        return False


async def check_runpod_deployments():
    """Check RunPod deployments"""
    print_section("RunPod Deployment Status")

    runpod_api_key = os.getenv("RUNPOD_API_KEY")
    if not runpod_api_key:
        print_error("RUNPOD_API_KEY not set - cannot check RunPod deployments")
        return False

    try:
        # Import the RunPod deployment manager
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
        from runpod_integration import RunPodConfig, RunPodDeploymentManager

        config = RunPodConfig(
            api_key=runpod_api_key,
            gpu_type="RTX 4090",
            deployment_type="serverless",
        )

        manager = RunPodDeploymentManager(config)
        deployments = await manager.get_all_deployments()

        if not deployments:
            print_warning("No RunPod deployments found")
            return True

        all_good = True
        for deployment in deployments:
            name = deployment.deployment_id
            status = deployment.status
            gpu_type = deployment.gpu_type
            deployment_type = deployment.deployment_type

            print(f"\nDeployment: {name}")
            print(f"  Type: {deployment_type}")
            print(f"  GPU: {gpu_type}")

            if status in ["running", "live", "active"]:
                print_success(f"Status: {status}")

                # Get detailed status
                detailed_status = await manager.get_deployment_status(name)
                if detailed_status:
                    if deployment_type == "serverless":
                        workers = detailed_status.get("workers", 0)
                        requests_completed = detailed_status.get(
                            "requests_completed", 0
                        )
                        print(f"  Workers: {workers}")
                        print(f"  Requests completed: {requests_completed}")
                    elif deployment_type == "pod":
                        gpu_count = detailed_status.get("gpu_count", 0)
                        print(f"  GPU count: {gpu_count}")
            else:
                print_error(f"Status: {status}")
                all_good = False

        return all_good

    except ImportError as e:
        print_error(f"Could not import RunPod manager: {e}")
        return False
    except Exception as e:
        print_error(f"Error checking RunPod deployments: {e}")
        return False


def check_kubernetes_deployments():
    """Check Kubernetes/GCP deployments"""
    print_section("Kubernetes/GCP Deployment Status")

    # Check if kubectl is available
    code, _, _ = run_command(["kubectl", "version", "--client"])
    if code != 0:
        print_error(
            "kubectl not available - cannot check Kubernetes deployments"
        )
        return False

    # Check if we can connect to cluster
    code, _, _ = run_command(["kubectl", "cluster-info"])
    if code != 0:
        print_warning("kubectl not configured for cluster access")
        return False

    all_good = True

    # Check Summit namespace
    print("\nChecking Summit namespace...")
    code, stdout, stderr = run_command(
        ["kubectl", "get", "namespace", "summit"]
    )

    if code == 0:
        print_success("Summit namespace exists")
    else:
        print_error("Summit namespace not found")
        all_good = False
        return all_good

    # Check deployments in summit namespace
    deployments_to_check = ["opencode-agent", "summit-app"]

    for deployment in deployments_to_check:
        print(f"\nChecking deployment: {deployment}")

        cmd = [
            "kubectl",
            "get",
            "deployment",
            deployment,
            "-n",
            "summit",
            "-o",
            "json",
        ]
        code, stdout, stderr = run_command(cmd)

        if code == 0:
            try:
                deployment_info = json.loads(stdout)
                status = deployment_info.get("status", {})

                ready_replicas = status.get("readyReplicas", 0)
                replicas = status.get("replicas", 0)

                if ready_replicas == replicas and replicas > 0:
                    print_success(f"Ready: {ready_replicas}/{replicas}")
                else:
                    print_error(f"Not ready: {ready_replicas}/{replicas}")
                    all_good = False

                # Check conditions
                conditions = status.get("conditions", [])
                for condition in conditions:
                    if condition.get("type") == "Available":
                        if condition.get("status") == "True":
                            print_success("Deployment available")
                        else:
                            print_error("Deployment not available")
                            all_good = False
                        break

            except json.JSONDecodeError:
                print_error("Could not parse deployment status")
                all_good = False
        else:
            print_error(f"Deployment not found: {stderr}")
            all_good = False

    # Check services
    print(f"\nChecking services...")
    cmd = ["kubectl", "get", "services", "-n", "summit", "-o", "json"]
    code, stdout, stderr = run_command(cmd)

    if code == 0:
        try:
            services_info = json.loads(stdout)
            services = services_info.get("items", [])

            if services:
                print_success(f"Found {len(services)} services")
                for service in services:
                    name = service.get("metadata", {}).get("name", "unknown")
                    service_type = service.get("spec", {}).get(
                        "type", "unknown"
                    )
                    print(f"  {name} ({service_type})")
            else:
                print_warning("No services found")
        except json.JSONDecodeError:
            print_error("Could not parse services information")
            all_good = False
    else:
        print_error(f"Could not get services: {stderr}")
        all_good = False

    return all_good


def check_deployment_health():
    """Check health endpoints of deployed services"""
    print_section("Service Health Check")

    # List of health endpoints to check
    health_endpoints = [
        "http://localhost:8000/health",  # Local development
        "https://summit.onrender.com/health",  # Render deployment
    ]

    all_good = True

    for endpoint in health_endpoints:
        print(f"\nChecking: {endpoint}")

        try:
            response = requests.get(endpoint, timeout=10)

            if response.status_code == 200:
                print_success(f"Health check passed")

                # Try to parse response
                try:
                    health_data = response.json()
                    status = health_data.get("status", "unknown")
                    timestamp = health_data.get("timestamp", "unknown")
                    print(f"  Status: {status}")
                    print(f"  Timestamp: {timestamp}")
                except json.JSONDecodeError:
                    print(f"  Response: {response.text[:100]}")
            else:
                print_error(
                    f"Health check failed: HTTP {response.status_code}"
                )
                all_good = False

        except requests.RequestException as e:
            print_warning(f"Health check failed: {e}")
            # Don't mark as error since service might not be deployed

    return all_good


async def main():
    """Main validation function"""
    print(f"{Colors.BOLD}Summit Cloud Deployment Validation{Colors.END}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Track overall status
    all_checks_passed = True

    # Run all validation checks
    checks = [
        ("GitHub Container Registry", check_github_container_registry),
        ("GitHub Actions Workflows", check_github_workflows),
        ("Render Deployments", check_render_deployments),
        ("RunPod Deployments", check_runpod_deployments),
        ("Kubernetes Deployments", check_kubernetes_deployments),
        ("Service Health", check_deployment_health),
    ]

    results = {}

    for check_name, check_func in checks:
        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()

            results[check_name] = result
            if not result:
                all_checks_passed = False

        except Exception as e:
            print_error(f"Error during {check_name}: {e}")
            results[check_name] = False
            all_checks_passed = False

    # Print summary
    print_section("Validation Summary")

    for check_name, result in results.items():
        if result:
            print_success(f"{check_name}: PASSED")
        else:
            print_error(f"{check_name}: FAILED")

    print()
    if all_checks_passed:
        print_success("All deployment validations PASSED")
        print(
            f"{Colors.GREEN} Summit is fully deployed and operational!{Colors.END}"
        )
        return 0
    else:
        print_error("Some deployment validations FAILED")
        print(
            f"{Colors.RED}  Summit has deployment issues that need attention{Colors.END}"
        )
        return 1


def cli():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description="Validate all Summit cloud deployments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all validation checks
  
Environment Variables:
  RENDER_API_KEY                    # Required for Render deployment checks
  RUNPOD_API_KEY                    # Required for RunPod deployment checks
  ANTHROPIC_API_KEY                 # Required for service health checks
        """,
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Run the validation
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Validation cancelled by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
