#!/usr/bin/env python3
"""
Claude Code Deployment CLI Tool

This script helps manage Claude Code deployments to various cloud platforms.
It works with the automated GitHub Actions workflow to trigger builds and
monitor deployment status.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests


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


def check_github_cli() -> bool:
    """Check if GitHub CLI is available"""
    code, _, _ = run_command(["gh", "--version"])
    return code == 0


def trigger_github_workflow(
    workflow_name: str = "claude-code-deploy.yml",
) -> bool:
    """Trigger the GitHub Actions workflow"""
    if not check_github_cli():
        print(" GitHub CLI (gh) is required but not found")
        print("   Install from: https://cli.github.com/")
        return False

    print(f" Triggering GitHub workflow: {workflow_name}")

    cmd = [
        "gh",
        "workflow",
        "run",
        workflow_name,
        "--field",
        "force_rebuild=true",
    ]

    code, stdout, stderr = run_command(cmd)

    if code == 0:
        print(" Workflow triggered successfully")
        return True
    else:
        print(f" Failed to trigger workflow: {stderr}")
        return False


def get_workflow_status(
    workflow_name: str = "claude-code-deploy.yml",
) -> Optional[Dict]:
    """Get the status of the latest workflow run"""
    if not check_github_cli():
        return None

    cmd = [
        "gh",
        "run",
        "list",
        "--workflow",
        workflow_name,
        "--limit",
        "1",
        "--json",
        "status,conclusion,createdAt,url,headBranch",
    ]

    code, stdout, stderr = run_command(cmd)

    if code == 0:
        try:
            runs = json.loads(stdout)
            return runs[0] if runs else None
        except json.JSONDecodeError:
            return None
    else:
        print(f" Failed to get workflow status: {stderr}")
        return None


def monitor_workflow(
    workflow_name: str = "claude-code-deploy.yml", timeout_minutes: int = 15
) -> bool:
    """Monitor workflow execution until completion"""
    print(f" Monitoring workflow: {workflow_name}")
    print(f"  Timeout: {timeout_minutes} minutes")

    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    while time.time() - start_time < timeout_seconds:
        status = get_workflow_status(workflow_name)

        if not status:
            print(" Could not get workflow status")
            return False

        current_status = status.get("status", "unknown")
        conclusion = status.get("conclusion")

        print(f" Status: {current_status}", end="")
        if conclusion:
            print(f" | Conclusion: {conclusion}")
        else:
            print()

        if current_status == "completed":
            if conclusion == "success":
                print(" Workflow completed successfully!")
                print(f" View details: {status.get('url', 'N/A')}")
                return True
            else:
                print(f" Workflow failed with conclusion: {conclusion}")
                print(f" View details: {status.get('url', 'N/A')}")
                return False
        elif current_status in ["cancelled", "failure"]:
            print(f" Workflow {current_status}")
            return False

        time.sleep(30)  # Check every 30 seconds

    print(f" Workflow monitoring timed out after {timeout_minutes} minutes")
    return False


def check_container_image(
    image_name: str = "ghcr.io/mjfuentes/summit/claude-code",
) -> bool:
    """Check if the container image exists and is accessible"""
    print(f" Checking container image: {image_name}")

    # Try to pull the image info
    cmd = ["docker", "manifest", "inspect", f"{image_name}:latest"]
    code, stdout, stderr = run_command(cmd)

    if code == 0:
        print(" Container image is accessible")
        try:
            manifest = json.loads(stdout)
            print(
                f" Image size: {manifest.get('config', {}).get('size', 'unknown')} bytes"
            )
            return True
        except json.JSONDecodeError:
            print("  Could not parse image manifest")
            return True
    else:
        print(f" Container image not accessible: {stderr}")
        return False


def validate_environment() -> bool:
    """Validate that the environment is set up correctly"""
    print(" Validating deployment environment...")

    issues = []

    # Check required files
    required_files = [
        "web/Dockerfile.autonomous",
        "web/claude_code_task.sh",
        "web/autonomous_server.py",
        "requirements.txt",
    ]

    for file_path in required_files:
        if not os.path.exists(file_path):
            issues.append(f"Missing required file: {file_path}")

    # Check GitHub CLI
    if not check_github_cli():
        issues.append(
            "GitHub CLI (gh) not found - required for workflow management"
        )

    # Check Docker
    code, _, _ = run_command(["docker", "--version"])
    if code != 0:
        issues.append("Docker not found - required for container operations")

    # Check environment variables
    required_env_vars = ["ANTHROPIC_API_KEY"]
    for var in required_env_vars:
        if not os.getenv(var):
            issues.append(f"Environment variable {var} not set")

    if issues:
        print(" Environment validation failed:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    else:
        print(" Environment validation passed")
        return True


def deploy_claude_code(
    platform: str = "render", monitor: bool = True, timeout_minutes: int = 15
) -> bool:
    """Deploy Claude Code to the specified platform"""
    print(f" Deploying Claude Code to {platform}")
    print(f" Started at: {datetime.now().isoformat()}")

    # Validate environment
    if not validate_environment():
        return False

    # Trigger the workflow
    if not trigger_github_workflow():
        return False

    # Monitor if requested
    if monitor:
        return monitor_workflow(timeout_minutes=timeout_minutes)
    else:
        print("ℹ  Workflow triggered - monitoring skipped")
        return True


def status_command() -> None:
    """Show deployment status"""
    print(" Claude Code Deployment Status")
    print("=" * 40)

    # Check workflow status
    status = get_workflow_status()
    if status:
        print(f" Latest Workflow:")
        print(f"   Status: {status.get('status', 'unknown')}")
        print(f"   Conclusion: {status.get('conclusion', 'N/A')}")
        print(f"   Branch: {status.get('headBranch', 'unknown')}")
        print(f"   Created: {status.get('createdAt', 'unknown')}")
        print(f"   URL: {status.get('url', 'N/A')}")
    else:
        print(" Could not get workflow status")

    print()

    # Check container image
    check_container_image()


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Deploy Claude Code instances to cloud platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s deploy                    # Deploy to Render.com with monitoring
  %(prog)s deploy --no-monitor       # Deploy without monitoring
  %(prog)s status                    # Show deployment status
  %(prog)s validate                  # Validate environment setup
  %(prog)s trigger                   # Just trigger the workflow
        """,
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )

    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy Claude Code")
    deploy_parser.add_argument(
        "--platform",
        choices=["render", "runpod"],
        default="render",
        help="Deployment platform (default: render)",
    )
    deploy_parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="Don't monitor workflow execution",
    )
    deploy_parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Monitoring timeout in minutes (default: 15)",
    )

    # Status command
    subparsers.add_parser("status", help="Show deployment status")

    # Validate command
    subparsers.add_parser("validate", help="Validate environment setup")

    # Trigger command
    subparsers.add_parser(
        "trigger", help="Trigger workflow without monitoring"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "deploy":
            success = deploy_claude_code(
                platform=args.platform,
                monitor=not args.no_monitor,
                timeout_minutes=args.timeout,
            )
            sys.exit(0 if success else 1)

        elif args.command == "status":
            status_command()

        elif args.command == "validate":
            success = validate_environment()
            sys.exit(0 if success else 1)

        elif args.command == "trigger":
            success = trigger_github_workflow()
            sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f" Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
