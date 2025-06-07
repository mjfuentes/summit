#!/usr/bin/env python3
"""
Debug script to diagnose PR creation issues for agents
"""

import json
import os
import subprocess
import sys
from datetime import datetime

import requests


def check_github_token():
    """Check if GitHub token exists and has proper permissions"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print(" No GITHUB_TOKEN environment variable found")
        return False

    print(f" GITHUB_TOKEN found (length: {len(token)})")

    # Test token validity and permissions
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        # Check token scopes
        response = requests.get("https://api.github.com/user", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            print(
                f" Token valid for user: {user_data.get('login', 'unknown')}"
            )

            # Check scopes from headers
            scopes = response.headers.get("X-OAuth-Scopes", "")
            print(f" Token scopes: {scopes}")

            # Check if we have repo scope (required for PR creation)
            if "repo" in scopes or "public_repo" in scopes:
                print(" Token has repository access")
                return True
            else:
                print(" Token missing 'repo' or 'public_repo' scope")
                print("   Required for creating pull requests")
                return False
        else:
            print(f" Token validation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f" Error checking token: {e}")
        return False


def get_repo_info():
    """Get current repository information"""
    try:
        # Get remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        remote_url = result.stdout.strip()
        print(f" Repository URL: {remote_url}")

        # Parse owner/repo from URL
        if "github.com" in remote_url:
            if remote_url.startswith("git@"):
                # SSH format: git@github.com:owner/repo.git
                parts = (
                    remote_url.split(":")[-1].replace(".git", "").split("/")
                )
            else:
                # HTTPS format: https://github.com/owner/repo.git
                parts = remote_url.split("/")[-2:]
                parts[-1] = parts[-1].replace(".git", "")

            owner, repo = parts
            print(f" Owner: {owner}, Repo: {repo}")
            return owner, repo, remote_url
        else:
            print(" Not a GitHub repository")
            return None, None, None
    except Exception as e:
        print(f" Error getting repo info: {e}")
        return None, None, None


def check_current_branch():
    """Check current branch and git status"""
    try:
        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        print(f" Current branch: {branch}")

        # Check if we have commits
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        commit_sha = result.stdout.strip()
        print(f" Latest commit: {commit_sha[:8]}")

        # Check git status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout.strip():
            print("  Working directory has uncommitted changes")
            print(result.stdout)
        else:
            print(" Working directory clean")

        return branch, commit_sha
    except Exception as e:
        print(f" Error checking git status: {e}")
        return None, None


def test_pr_creation_api(owner, repo, branch):
    """Test PR creation via GitHub API"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Test data for PR creation
    pr_data = {
        "title": f"[DEBUG] Test PR from {branch}",
        "head": branch,
        "base": "main",
        "body": f"Debug test PR created at {datetime.now().isoformat()}\n\nThis is a test to diagnose PR creation issues.",
        "draft": True,  # Create as draft to avoid noise
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

    try:
        print(f" Testing PR creation API call...")
        print(f"   URL: {url}")
        print(f"   Data: {json.dumps(pr_data, indent=2)}")

        response = requests.post(
            url, headers=headers, json=pr_data, timeout=30
        )

        print(f" Response status: {response.status_code}")
        print(f" Response headers: {dict(response.headers)}")

        if response.status_code == 201:
            pr_info = response.json()
            print(f" PR created successfully!")
            print(f"   PR #{pr_info['number']}: {pr_info['html_url']}")
            return True
        else:
            print(f" PR creation failed")
            print(f"   Response: {response.text}")

            # Try to parse error details
            try:
                error_data = response.json()
                if "errors" in error_data:
                    for error in error_data["errors"]:
                        print(f"   Error: {error}")
                if "message" in error_data:
                    print(f"   Message: {error_data['message']}")
            except:
                pass

            return False
    except Exception as e:
        print(f" Exception during PR creation: {e}")
        return False


def check_branch_exists_on_remote(owner, repo, branch):
    """Check if the current branch exists on remote"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print(f" Branch '{branch}' exists on remote")
            return True
        elif response.status_code == 404:
            print(f" Branch '{branch}' does not exist on remote")
            print(
                "   You need to push the branch first: git push -u origin {branch}"
            )
            return False
        else:
            print(f"  Could not check branch status: {response.status_code}")
            return False
    except Exception as e:
        print(f" Error checking branch: {e}")
        return False


def main():
    print(" DIAGNOSING PR CREATION ISSUES")
    print("=" * 50)

    # Step 1: Check GitHub token
    print("\n1⃣ Checking GitHub Token...")
    if not check_github_token():
        print(
            "\n SOLUTION: Set up a GitHub Personal Access Token with 'repo' scope"
        )
        print("   1. Go to https://github.com/settings/tokens")
        print("   2. Generate new token with 'repo' scope")
        print("   3. Export GITHUB_TOKEN=your_token_here")
        return

    # Step 2: Get repository info
    print("\n2⃣ Checking Repository...")
    owner, repo, remote_url = get_repo_info()
    if not owner or not repo:
        return

    # Step 3: Check current branch
    print("\n3⃣ Checking Git Status...")
    branch, commit_sha = check_current_branch()
    if not branch or not commit_sha:
        return

    if branch in ["main", "master"]:
        print("  You're on the main branch")
        print("   PRs should be created from feature branches")
        print(
            "   Create a feature branch first: git checkout -b feature/test-pr"
        )
        return

    # Step 4: Check if branch exists on remote
    print("\n4⃣ Checking Remote Branch...")
    if not check_branch_exists_on_remote(owner, repo, branch):
        print("\n SOLUTION: Push your branch to remote first")
        print(f"   git push -u origin {branch}")
        return

    # Step 5: Test PR creation
    print("\n5⃣ Testing PR Creation...")
    if test_pr_creation_api(owner, repo, branch):
        print("\n PR creation works! The issue might be in the agent code.")
    else:
        print("\n PR creation failed. Check the error details above.")

    print("\n" + "=" * 50)
    print(" DIAGNOSIS COMPLETE")


if __name__ == "__main__":
    main()
