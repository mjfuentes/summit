#!/usr/bin/env python3
"""
Agent Git API - Simplified Python interface for agent Git operations
This is the ONLY approved way for the agent to interact with Git

## PR Creation

The agent creates PRs with custom descriptions by providing the complete
description as a string parameter to create_pr().

Example:
    from src.agent_git_api import create_pr

    description = "# Feature: Authentication\\n\\nImplemented JWT auth system..."
    create_pr("Add auth", "Feature: JWT Authentication", description)

The agent should use the PR_TEMPLATE environment variable to format descriptions.
"""

import sys
from pathlib import Path

from scripts.agent_git import AgentGitWrapper

# Add scripts to path
repo_root = Path(__file__).parent.parent
scripts_path = repo_root / "scripts"
sys.path.insert(0, str(scripts_path))

# Import the wrapper - this will be defined in scripts


class AgentGitAPI:
    """Simplified API for agent Git operations"""

    def __init__(self):

        self.git = AgentGitWrapper()

    def quick_save(self, message: str, files: list = None) -> bool:
        """

        The main method agents should use for saving work.

        Automatically adds files, commits with validation, and pushes.



        Args:

            message: Commit message (will be validated)

            files: Optional list of files to add (default: all changed files)



        Returns:

            bool: True if successful, False otherwise

        """

        return self.git.quick_commit_push(message, files)

    def save_and_create_pr(
        self, commit_message: str, pr_title: str, pr_body: str = ""
    ) -> bool:
        """

        Save work and immediately create a PR.

        Automatically handles branch management:
        - If on main, creates a new feature branch
        - Updates main if needed
        - Commits and pushes to feature branch
        - Creates PR from feature branch to main

        Args:

            commit_message: Message for the commit

            pr_title: Title for the PR

            pr_body: Complete PR description (agent should provide this)



        Returns:

            bool: True if successful, False otherwise

        """

        current_branch = self.get_current_branch()

        # If we're on main, we need to create a feature branch
        if current_branch == "main" or current_branch == "master":
            print(
                f" Currently on {current_branch} branch - creating feature branch..."
            )

            # Update main first
            if not self.update_from_remote():
                print(" Warning: Could not update main branch")

            # Create feature branch name from PR title
            import re

            branch_name = "feature/" + re.sub(
                r"[^a-zA-Z0-9]+", "-", pr_title.lower()
            ).strip("-")
            branch_name = branch_name[:50]  # Limit length

            if not self.create_feature_branch(branch_name):
                return False

            print(f" Created feature branch: {branch_name}")

        # Save the work on the feature branch
        if not self.quick_save(commit_message):
            return False

        # Create PR from feature branch to main
        return self.git.create_pr(pr_title, pr_body)

    def check_status(self) -> None:
        """Show current git status"""

        self.git.status()

    def update_from_remote(self) -> bool:
        """Pull latest changes from remote"""

        return self.git.pull()

    def is_clean(self) -> bool:
        """Check if working directory is clean"""

        result = self.git._run_command(["git", "status", "--porcelain"])

        return len(result.stdout.strip()) == 0

    def get_current_branch(self) -> str:
        """Get current branch name"""

        return self.git._get_current_branch()

    def check_ci_status(self, commit_sha: str = None) -> dict:
        """
        Check CI/CD pipeline status for a commit.

        Args:
            commit_sha: Optional commit SHA (defaults to HEAD)

        Returns:
            dict: CI status information
        """
        if commit_sha is None:
            # Get current HEAD commit
            result = self.git._run_command(["git", "rev-parse", "HEAD"])
            commit_sha = result.stdout.strip()

        return self.git._check_ci_status(commit_sha)

    def show_failed_checks(self, commit_sha: str = None) -> None:
        """
        Show details of failed CI checks.

        Args:
            commit_sha: Optional commit SHA (defaults to HEAD)
        """
        if commit_sha is None:
            # Get current HEAD commit
            result = self.git._run_command(["git", "rev-parse", "HEAD"])
            commit_sha = result.stdout.strip()

        self.git._show_failed_checks(commit_sha)

    def wait_for_ci(self, commit_sha: str = None) -> bool:
        """
        Wait for CI/CD pipeline to complete.

        Args:
            commit_sha: Optional commit SHA (defaults to HEAD)

        Returns:
            bool: True if CI passed, False if failed/errored
        """
        if commit_sha is None:
            # Get current HEAD commit
            result = self.git._run_command(["git", "rev-parse", "HEAD"])
            commit_sha = result.stdout.strip()

        return self.git._wait_for_ci(commit_sha)

    def check_pipeline_status(self) -> None:
        """
        Check and display current CI/CD pipeline status.
        Convenience method for checking the latest commit's CI status.
        """
        # Get current HEAD commit
        result = self.git._run_command(["git", "rev-parse", "HEAD"])
        commit_sha = result.stdout.strip()
        short_sha = commit_sha[:7]

        print(f"Checking CI/CD status for commit {short_sha}...")

        status = self.git._check_ci_status(commit_sha)
        state = status.get("state", "unknown")

        if state == "success":
            print("CI/CD pipeline: PASSED")
        elif state == "pending":
            print("CI/CD pipeline: RUNNING")
        elif state == "failure":
            print("CI/CD pipeline: FAILED")
            self.git._show_failed_checks(commit_sha)
        elif state == "error":
            print("CI/CD pipeline: ERROR")
        else:
            print(f"CI/CD pipeline: {state.upper()}")

    def create_feature_branch(self, branch_name: str) -> bool:
        """

        Create and switch to a new feature branch.



        Args:

            branch_name: Name for the new branch



        Returns:

            bool: True if successful, False otherwise

        """

        # Create branch

        result = self.git._run_command(
            ["git", "checkout", "-b", branch_name], check=False
        )

        if result.returncode != 0:

            print(f" Failed to create branch: {result.stderr}")

            return False

        print(f" Created and switched to branch: {branch_name}")

        return True

    def switch_branch(self, branch_name: str) -> bool:
        """

        Switch to an existing branch.



        Args:

            branch_name: Name of the branch to switch to



        Returns:

            bool: True if successful, False otherwise

        """

        result = self.git._run_command(
            ["git", "checkout", branch_name], check=False
        )

        if result.returncode != 0:

            print(f" Failed to switch branch: {result.stderr}")

            return False

        print(f" Switched to branch: {branch_name}")

        return True


# Global instance for easy agent access

agent_git = AgentGitAPI()


# Convenience functions for the most common operations


def save_work(message: str, files: list = None) -> bool:
    """

    Quick save work - the primary function agents should use.



    This function will:

    1. Validate the commit message

    2. Run all tests (must pass)

    3. Check coverage (must be >70%)

    4. Run linting

    5. Run pre-commit hooks

    6. Commit if everything passes

    7. Push to remote



    Args:

        message: Commit message (validated - must be single line, no emojis)

        files: Optional list of files to add (default: all changed files)



    Returns:

        bool: True if successful, False otherwise

    """

    return agent_git.git.quick_commit_push(message, files)


def create_pr(commit_message: str, pr_title: str, pr_body: str = "") -> bool:
    """
    Save work and create a PR with automatic branch management.

    This function will:
    1. Check if we're on main/master branch
    2. If so, create a new feature branch automatically
    3. Update main branch if needed
    4. Commit and push to feature branch
    5. Create PR from feature branch to main

    Args:
        commit_message: Message for the commit
        pr_title: Title for the PR
        pr_body: Complete PR description

    Returns:
        bool: True if successful, False otherwise
    """

    return agent_git.save_and_create_pr(commit_message, pr_title, pr_body)


def status() -> None:
    """Show git status"""

    agent_git.check_status()


def pull() -> bool:
    """Update from remote"""

    return agent_git.update_from_remote()


def check_ci_status(commit_sha: str = None) -> dict:
    """
    Check CI/CD pipeline status for a commit.

    Args:
        commit_sha: Optional commit SHA (defaults to HEAD)

    Returns:
        dict: CI status information
    """
    return agent_git.check_ci_status(commit_sha)


def show_failed_checks(commit_sha: str = None) -> None:
    """
    Show details of failed CI checks.

    Args:
        commit_sha: Optional commit SHA (defaults to HEAD)
    """
    agent_git.show_failed_checks(commit_sha)


def wait_for_ci(commit_sha: str = None) -> bool:
    """
    Wait for CI/CD pipeline to complete.

    Args:
        commit_sha: Optional commit SHA (defaults to HEAD)

    Returns:
        bool: True if CI passed, False if failed/errored
    """
    return agent_git.wait_for_ci(commit_sha)


def check_pipeline_status() -> None:
    """
    Check and display current CI/CD pipeline status.
    Primary function for checking pipeline status - use this one.
    """
    agent_git.check_pipeline_status()
