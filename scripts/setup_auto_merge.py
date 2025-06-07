#!/usr/bin/env python3
"""
Setup script for GitHub auto-merge configuration for Summit.
This script helps configure branch protection rules and auto-merge settings.
"""

import json
import os
from typing import Dict, List

import requests


def get_github_headers() -> Dict[str, str]:
    """Get GitHub API headers with authentication"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }


def create_branch_protection_rule(
    owner: str, repo: str, branch: str = "main"
) -> bool:
    """Create branch protection rule for auto-merge"""
    headers = get_github_headers()
    url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}/protection"

    # Configuration for Summit's autonomous workflow
    protection_config = {
        "required_status_checks": {
            "strict": True,  # Require branches to be up to date
            "contexts": [
                "test",  # Add your CI check names here
                "build",
                "lint",
            ],
        },
        "enforce_admins": False,  # Allow admins to bypass (useful for emergency fixes)
        "required_pull_request_reviews": {
            "required_approving_review_count": 0,  # Auto-merge without manual approval
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "require_last_push_approval": False,
        },
        "restrictions": None,  # No push restrictions
        "allow_force_pushes": False,
        "allow_deletions": False,
    }

    try:
        response = requests.put(url, headers=headers, json=protection_config)
        response.raise_for_status()
        print(f" Branch protection rule created for {branch}")
        return True
    except requests.RequestException as e:
        print(f" Failed to create branch protection rule: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return False


def enable_auto_merge_setting(owner: str, repo: str) -> bool:
    """Enable auto-merge setting for the repository"""
    headers = get_github_headers()
    url = f"https://api.github.com/repos/{owner}/{repo}"

    # Update repository settings to allow auto-merge
    repo_config = {
        "allow_auto_merge": True,
        "allow_squash_merge": True,  # Recommended for clean history
        "allow_merge_commit": True,
        "allow_rebase_merge": True,
        "delete_branch_on_merge": True,  # Clean up feature branches
    }

    try:
        response = requests.patch(url, headers=headers, json=repo_config)
        response.raise_for_status()
        print(" Auto-merge enabled for repository")
        return True
    except requests.RequestException as e:
        print(f" Failed to enable auto-merge: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return False


def check_current_settings(
    owner: str, repo: str, branch: str = "main"
) -> Dict:
    """Check current repository and branch protection settings"""
    headers = get_github_headers()

    # Check repository settings
    repo_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        repo_response = requests.get(repo_url, headers=headers)
        repo_response.raise_for_status()
        repo_data = repo_response.json()
    except requests.RequestException as e:
        print(f" Failed to get repository settings: {e}")
        return {}

    # Check branch protection
    branch_url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}/protection"
    try:
        branch_response = requests.get(branch_url, headers=headers)
        if branch_response.status_code == 200:
            branch_data = branch_response.json()
        else:
            branch_data = {"message": "Branch protection not configured"}
    except requests.RequestException as e:
        branch_data = {"error": str(e)}

    return {
        "repository": {
            "allow_auto_merge": repo_data.get("allow_auto_merge", False),
            "allow_squash_merge": repo_data.get("allow_squash_merge", False),
            "delete_branch_on_merge": repo_data.get(
                "delete_branch_on_merge", False
            ),
        },
        "branch_protection": branch_data,
    }


def main():
    """Main setup function"""
    print(" Summit Auto-Merge Setup")
    print("=" * 50)

    # Get repository info
    owner = input("Enter GitHub owner/organization: ").strip()
    repo = input("Enter repository name: ").strip()
    branch = (
        input("Enter branch to protect (default: main): ").strip() or "main"
    )

    if not owner or not repo:
        print(" Owner and repository name are required")
        return

    print(f"\n Configuring auto-merge for {owner}/{repo} (branch: {branch})")

    # Check current settings
    print("\n Checking current settings...")
    current_settings = check_current_settings(owner, repo, branch)

    if current_settings:
        print("Current repository settings:")
        repo_settings = current_settings.get("repository", {})
        print(
            f"  - Auto-merge: {'' if repo_settings.get('allow_auto_merge') else ''}"
        )
        print(
            f"  - Squash merge: {'' if repo_settings.get('allow_squash_merge') else ''}"
        )
        print(
            f"  - Delete branch on merge: {'' if repo_settings.get('delete_branch_on_merge') else ''}"
        )

        branch_protection = current_settings.get("branch_protection", {})
        if "message" in branch_protection:
            print(f"  - Branch protection:  {branch_protection['message']}")
        elif "error" in branch_protection:
            print(f"  - Branch protection:  {branch_protection['error']}")
        else:
            print("  - Branch protection:  Configured")

    # Setup auto-merge
    print(f"\n  Setting up auto-merge for {owner}/{repo}...")

    success = True

    # Enable repository auto-merge setting
    if not enable_auto_merge_setting(owner, repo):
        success = False

    # Create branch protection rule
    if not create_branch_protection_rule(owner, repo, branch):
        success = False

    if success:
        print("\n Auto-merge setup completed successfully!")
        print("\n Next steps:")
        print(
            "1. Update your CI workflow to include the required status checks:"
        )
        print("   - test")
        print("   - build")
        print("   - lint")
        print("2. PRs created by Summit will now auto-merge when CI passes")
        print("3. Test with a sample PR to verify the setup")
    else:
        print(
            "\n Setup completed with errors. Please check the messages above."
        )

    print(
        f"\n Repository settings: https://github.com/{owner}/{repo}/settings"
    )
    print(
        f" Branch protection: https://github.com/{owner}/{repo}/settings/branches"
    )


if __name__ == "__main__":
    main()
