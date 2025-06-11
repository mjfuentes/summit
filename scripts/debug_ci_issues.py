#!/usr/bin/env python3
"""
Debug CI/CD Issues Script
Helps diagnose common GitHub Actions workflow problems
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def run_command(cmd):
    """Run a command and return output"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"


def check_github_cli():
    """Check if GitHub CLI is available"""
    code, _, _ = run_command("gh --version")
    return code == 0


def get_recent_workflow_runs(limit=5):
    """Get recent workflow runs"""
    if not check_github_cli():
        print(" GitHub CLI not available. Install with: brew install gh")
        return []

    cmd = f"gh run list --limit {limit} --json status,conclusion,name,createdAt,url,headBranch"
    code, stdout, stderr = run_command(cmd)

    if code != 0:
        print(f" Failed to get workflow runs: {stderr}")
        return []

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        print(" Failed to parse workflow run data")
        return []


def check_workflow_files():
    """Check for common workflow file issues"""
    print(" Checking workflow files...")

    workflow_dir = Path(".github/workflows")
    if not workflow_dir.exists():
        print(" .github/workflows directory not found")
        return

    workflow_files = list(workflow_dir.glob("*.yml")) + list(
        workflow_dir.glob("*.yaml")
    )

    if not workflow_files:
        print(" No workflow files found")
        return

    print(f" Found {len(workflow_files)} workflow files:")

    for file in workflow_files:
        print(f"   {file.name}")

        # Check for common issues
        content = file.read_text()

        # Check for missing file references
        if "trivy-results.sarif" in content and "if:" not in content:
            print(
                f"      {file.name}: Potential missing file issue with trivy-results.sarif"
            )

        # Check for missing permissions
        if (
            "upload-sarif" in content
            and "security-events: write" not in content
        ):
            print(
                f"      {file.name}: Missing security-events permission for SARIF upload"
            )

        # Check for missing continue-on-error
        if "trivy-action" in content and "continue-on-error" not in content:
            print(
                f"      {file.name}: Consider adding continue-on-error for Trivy scan"
            )


def check_missing_files():
    """Check for files that workflows might expect"""
    print("\n  Checking for missing files...")

    expected_files = [
        "requirements.txt",
        "Dockerfile",
        "opencode-bridge/Dockerfile",
        "infrastructure/docker/Dockerfile.mcp-server",
        "infrastructure/docker/Dockerfile.summit-api",
    ]

    for file_path in expected_files:
        if Path(file_path).exists():
            print(f"   {file_path}")
        else:
            print(f"   {file_path} (missing)")


def check_environment_variables():
    """Check for required environment variables"""
    print("\n Checking environment variables...")

    required_vars = [
        "GITHUB_TOKEN",
        "ANTHROPIC_API_KEY",
    ]

    for var in required_vars:
        if os.getenv(var):
            print(f"   {var} is set")
        else:
            print(f"   {var} is not set")


def analyze_recent_failures():
    """Analyze recent workflow failures"""
    print("\n Recent workflow runs:")

    runs = get_recent_workflow_runs()
    if not runs:
        return

    for run in runs:
        status = run.get("status", "unknown")
        conclusion = run.get("conclusion", "unknown")
        name = run.get("name", "unknown")
        created_at = run.get("createdAt", "")
        url = run.get("url", "")
        branch = run.get("headBranch", "unknown")

        # Format datetime
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            time_str = created_at

        # Status emoji
        if conclusion == "success":
            emoji = ""
        elif conclusion == "failure":
            emoji = ""
        elif conclusion == "cancelled":
            emoji = ""
        elif status == "in_progress":
            emoji = ""
        else:
            emoji = ""

        print(f"  {emoji} {name} ({branch}) - {time_str}")
        if conclusion == "failure":
            print(f"     {url}")


def get_workflow_logs(workflow_name):
    """Get logs for a specific workflow"""
    if not check_github_cli():
        return

    cmd = f"gh run list --workflow {workflow_name} --limit 1 --json databaseId"
    code, stdout, _ = run_command(cmd)

    if code != 0:
        print(f" Failed to get workflow ID for {workflow_name}")
        return

    try:
        runs = json.loads(stdout)
        if runs:
            run_id = runs[0]["databaseId"]
            cmd = f"gh run view {run_id} --log"
            code, stdout, _ = run_command(cmd)
            if code == 0:
                print(f"\n Recent logs for {workflow_name}:")
                print(stdout[-2000:])  # Last 2000 characters
    except:
        print(f" Failed to parse workflow data for {workflow_name}")


def main():
    """Main function"""
    print(" Summit CI/CD Debug Tool")
    print("=" * 50)

    # Change to repository root if needed
    if not Path(".git").exists():
        print(" Not in a git repository")
        sys.exit(1)

    check_workflow_files()
    check_missing_files()
    check_environment_variables()
    analyze_recent_failures()

    # Get specific workflow logs if available
    failed_workflows = ["build-opencode-bridge.yml", "ci.yml"]
    for workflow in failed_workflows:
        if Path(f".github/workflows/{workflow}").exists():
            get_workflow_logs(workflow)

    print("\n Common fixes:")
    print("  • Add 'continue-on-error: true' to steps that might fail")
    print("  • Check file exists before uploading with 'if:' conditions")
    print("  • Ensure proper permissions in workflow files")
    print("  • Verify all referenced files exist in repository")
    print("  • Check GitHub secrets are properly configured")


if __name__ == "__main__":
    main()
