#!/usr/bin/env python3
"""
Create PR for Summit API CI/CD integration
"""

import os
import subprocess
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, "src")

from agent_git_api import create_pr


def main():
    # Get current branch and commit info
    try:
        current_branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        commit_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except:
        current_branch = "main"
        commit_sha = "unknown"

    print(f"Current branch: {current_branch}")
    print(f"Current commit: {commit_sha[:7]}")

    # Get PR template from environment
    template = os.environ.get(
        "PR_TEMPLATE",
        """# {title}

**Branch**: {branch}  
**Commit**: {commit_sha}  
**Created**: {timestamp}

## Summary
{summary}

## Changes Made
{changes}

## Files Modified
{files_modified}

## Quality Assurance
{quality_assurance}

## Review Process
{review_process}
""",
    )

    # Format the template with actual values
    description = template.format(
        title="Summit API CI/CD Integration",
        branch=current_branch,
        commit_sha=commit_sha[:7],
        timestamp=datetime.utcnow().isoformat() + "Z",
        summary="Added Summit API deployment to the CI/CD pipeline alongside OpenCode agents. Both applications are now optimized for e2-small nodes with minimal resource requirements and will deploy automatically via GitHub Actions.",
        changes="""- Updated CI/CD pipeline to deploy both OpenCode agents and Summit API
- Created Dockerfile for Summit API with production optimizations
- Optimized resource requirements for e2-small nodes (64Mi memory, 50m CPU)
- Added ANTHROPIC_API_KEY secret support to deployment pipeline
- Reduced replica counts to 1 for cost-effective testing
- Updated verification steps to monitor both deployments""",
        files_modified="""- `.github/workflows/deploy-infrastructure.yml`
- `infrastructure/kubernetes/summit-app/deployment.yaml`
- `infrastructure/kubernetes/opencode/deployment.yaml`
- `infrastructure/docker/Dockerfile.summit-api` (new)""",
        quality_assurance="All configuration files validated for Kubernetes deployment. Resource requirements tested and optimized for e2-small node constraints. Docker build process verified. CI/CD pipeline updated to handle both applications with proper error handling and verification steps.",
        review_process="This PR follows Summit's quality-first approach with automated quality gates. The changes enable automatic deployment of both Summit API and OpenCode agents to the Kubernetes cluster. Will auto-merge upon successful CI completion.",
    )

    # Create the PR
    print("Creating PR...")
    result = create_pr(
        "Add Summit API to CI/CD pipeline with optimized resource requirements",
        "Feature: Summit API CI/CD Integration",
        description,
    )

    if result:
        print(" PR created successfully!")
    else:
        print(" PR creation failed")


if __name__ == "__main__":
    main()
