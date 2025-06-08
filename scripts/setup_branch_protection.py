#!/usr/bin/env python3
"""
Setup Branch Protection Rules for Summit Repository
Configures required status checks to prevent merging when tests fail
"""

import json
import os
import sys
from typing import Dict, List

import requests


def get_github_api_headers() -> Dict[str, str]:
    """Get GitHub API headers with authentication"""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        print("Please set your GitHub personal access token:")
        print("export GITHUB_TOKEN=your_token_here")
        sys.exit(1)

    return {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def setup_branch_protection(
    owner: str, repo: str, branch: str = "main"
) -> bool:
    """
    Set up branch protection rules for the specified branch

    Based on GitHub's status checks documentation:
    https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks
    """
    headers = get_github_api_headers()
    url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}/protection"

    # Define required status checks based on our CI workflow
    protection_rules = {
        "required_status_checks": {
            "strict": True,  # Require branches to be up to date before merging
            "contexts": [
                "Tests",  # From ci.yml - test job
                "Code Quality",  # From ci.yml - lint job
                "Build Check",  # From ci.yml - build job
                "Security Scan",  # From ci.yml - security job
            ],
        },
        # Allow admins to bypass (for emergency fixes)
        "enforce_admins": False,
        "required_pull_request_reviews": {
            # No human reviews required (AI handles this)
            "required_approving_review_count": 0,
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "require_last_push_approval": False,
        },
        "restrictions": None,  # No push restrictions
        "allow_force_pushes": False,
        "allow_deletions": False,
        "block_creations": False,
        "required_conversation_resolution": False,
    }

    print(f"Setting up branch protection for {owner}/{repo}:{branch}")
    print("Required status checks:")
    for check in protection_rules["required_status_checks"]["contexts"]:
        print(f"  - {check}")

    try:
        response = requests.put(url, headers=headers, json=protection_rules)

        if response.status_code == 200:
            print(" Branch protection rules updated successfully!")
            return True
        elif response.status_code == 201:
            print(" Branch protection rules created successfully!")
            return True
        else:
            print(
                f" Failed to set up branch protection: {response.status_code}"
            )
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f" Error setting up branch protection: {e}")
        return False


def verify_branch_protection(
    owner: str, repo: str, branch: str = "main"
) -> bool:
    """Verify that branch protection rules are correctly configured"""
    headers = get_github_api_headers()
    url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}/protection"

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            protection = response.json()
            print("\n Current branch protection settings:")

            # Check required status checks
            if "required_status_checks" in protection:
                status_checks = protection["required_status_checks"]
                print(
                    f"  Required status checks: {status_checks.get('strict', False)}"
                )
                contexts = status_checks.get("contexts", [])
                print(f"  Required contexts ({len(contexts)}):")
                for context in contexts:
                    print(f"    - {context}")
            else:
                print("   No required status checks configured")

            # Check PR review requirements
            if "required_pull_request_reviews" in protection:
                pr_reviews = protection["required_pull_request_reviews"]
                required_reviews = pr_reviews.get(
                    "required_approving_review_count", 0
                )
                print(f"  Required PR reviews: {required_reviews}")

            return True
        elif response.status_code == 404:
            print(" No branch protection rules found")
            return False
        else:
            print(f" Error checking branch protection: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f" Error verifying branch protection: {e}")
        return False


def main():
    """Main function to set up branch protection"""
    # Default to Summit repository
    owner = "mjfuentes"
    repo = "summit"
    branch = "main"

    # Allow override via command line arguments
    if len(sys.argv) >= 3:
        owner = sys.argv[1]
        repo = sys.argv[2]
    if len(sys.argv) >= 4:
        branch = sys.argv[3]

    print(" Summit Branch Protection Setup")
    print("=" * 50)
    print(f"Repository: {owner}/{repo}")
    print(f"Branch: {branch}")
    print()

    # First verify current settings
    print("Checking current branch protection...")
    verify_branch_protection(owner, repo, branch)
    print()

    # Set up new protection rules
    success = setup_branch_protection(owner, repo, branch)

    if success:
        print()
        print("Verifying new settings...")
        verify_branch_protection(owner, repo, branch)
        print()
        print(" Branch protection setup complete!")
        print()
        print("Now when you create pull requests:")
        print("   Tests must pass before merging")
        print("   Code quality checks must pass")
        print("   Security scans must complete")
        print("   Build checks must succeed")
        print()
        print("This prevents merging when tests fail, as requested!")
    else:
        print(" Failed to set up branch protection")
        sys.exit(1)


if __name__ == "__main__":
    main()
