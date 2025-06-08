#!/usr/bin/env python3
"""
GitHub CI/CD Integration Module
Provides functionality to monitor GitHub Actions workflows and CI/CD status
"""

import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests


class GitHubCICDManager:
    """Manages GitHub CI/CD workflow monitoring and status tracking"""

    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = self._get_headers()

    def _get_headers(self) -> Dict[str, str]:
        """Get GitHub API headers with authentication"""
        if not self.github_token:
            return {}

        return {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _parse_repo_url(self, repo_url: str) -> Tuple[str, str]:
        """Parse GitHub repository URL to extract owner and repo name"""
        # Handle various GitHub URL formats
        patterns = [
            r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$",
            r"github\.com/([^/]+)/([^/]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, repo_url)
            if match:
                return match.group(1), match.group(2)

        raise ValueError(f"Could not parse GitHub repository URL: {repo_url}")

    async def get_pr_info(
        self, repo_url: str, pr_number: int
    ) -> Optional[Dict]:
        """Get pull request information"""
        if not self.headers:
            return None

        try:
            owner, repo = self._parse_repo_url(repo_url)
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"

            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print(f"Error fetching PR info: {e}")
            return None

    async def get_commit_status(self, repo_url: str, commit_sha: str) -> Dict:
        """Get CI/CD status for a specific commit"""
        if not self.headers:
            return {"state": "unknown", "statuses": [], "check_runs": []}

        try:
            owner, repo = self._parse_repo_url(repo_url)

            # Get commit status (legacy status API)
            status_url = f"{self.base_url}/repos/{owner}/{repo}/commits/{commit_sha}/status"
            status_response = requests.get(
                status_url, headers=self.headers, timeout=30
            )
            status_data = (
                status_response.json()
                if status_response.status_code == 200
                else {}
            )

            # Get check runs (newer checks API)
            checks_url = f"{self.base_url}/repos/{owner}/{repo}/commits/{commit_sha}/check-runs"
            checks_response = requests.get(
                checks_url, headers=self.headers, timeout=30
            )
            checks_data = (
                checks_response.json()
                if checks_response.status_code == 200
                else {}
            )

            # Combine status information
            combined_status = self._combine_status_data(
                status_data, checks_data
            )
            return combined_status

        except Exception as e:
            print(f"Error fetching commit status: {e}")
            return {"state": "error", "statuses": [], "check_runs": []}

    def _combine_status_data(
        self, status_data: Dict, checks_data: Dict
    ) -> Dict:
        """Combine legacy status and modern checks data"""
        # Determine overall state
        status_state = status_data.get("state", "pending")
        check_runs = checks_data.get("check_runs", [])

        # Check if all check runs passed
        check_conclusions = [
            run.get("conclusion")
            for run in check_runs
            if run.get("conclusion")
        ]

        if check_conclusions:
            if all(
                c in ["success", "neutral", "skipped"]
                for c in check_conclusions
            ):
                overall_state = "success"
            elif any(c == "failure" for c in check_conclusions):
                overall_state = "failure"
            elif any(
                c in ["cancelled", "timed_out"] for c in check_conclusions
            ):
                overall_state = "error"
            else:
                overall_state = "pending"
        else:
            overall_state = status_state

        return {
            "state": overall_state,
            "statuses": status_data.get("statuses", []),
            "check_runs": check_runs,
            "total_count": status_data.get("total_count", 0) + len(check_runs),
            "sha": status_data.get("sha") or checks_data.get("sha"),
        }

    async def get_workflow_runs(
        self, repo_url: str, branch: str = None, limit: int = 10
    ) -> List[Dict]:
        """Get workflow runs for a repository or specific branch"""
        if not self.headers:
            return []

        try:
            owner, repo = self._parse_repo_url(repo_url)
            url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs"

            params = {"per_page": limit}
            if branch:
                params["branch"] = branch

            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            return data.get("workflow_runs", [])

        except Exception as e:
            print(f"Error fetching workflow runs: {e}")
            return []

    async def get_workflow_run_jobs(
        self, repo_url: str, run_id: int
    ) -> List[Dict]:
        """Get jobs for a specific workflow run"""
        if not self.headers:
            return []

        try:
            owner, repo = self._parse_repo_url(repo_url)
            url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"

            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data.get("jobs", [])

        except Exception as e:
            print(f"Error fetching workflow jobs: {e}")
            return []

    async def get_pr_workflow_runs(
        self, repo_url: str, pr_number: int
    ) -> List[Dict]:
        """Get workflow runs associated with a specific PR"""
        if not self.headers:
            return []

        try:
            # First get PR info to get the head SHA
            pr_info = await self.get_pr_info(repo_url, pr_number)
            if not pr_info:
                return []

            head_sha = pr_info["head"]["sha"]
            branch = pr_info["head"]["ref"]

            # Get workflow runs for the PR branch
            workflow_runs = await self.get_workflow_runs(
                repo_url, branch, limit=20
            )

            # Filter runs that match the PR's head SHA or are pull_request
            # events
            pr_runs = []
            for run in workflow_runs:
                if (
                    run.get("head_sha") == head_sha
                    or run.get("event") == "pull_request"
                    or run.get("head_branch") == branch
                ):
                    pr_runs.append(run)

            return pr_runs

        except Exception as e:
            print(f"Error fetching PR workflow runs: {e}")
            return []

    async def monitor_task_ci_status(self, task_data: Dict) -> Dict:
        """Monitor CI/CD status for a task with PR and commit information"""
        if not task_data.get("repository_url"):
            return {"state": "unknown", "message": "No repository URL"}

        result = {
            "state": "unknown",
            "workflow_runs": [],
            "commit_status": {},
            "pr_info": {},
            "last_updated": datetime.utcnow().isoformat(),
        }

        try:
            repo_url = task_data["repository_url"]

            # Get commit status if we have a commit SHA
            if task_data.get("commit_sha"):
                commit_status = await self.get_commit_status(
                    repo_url, task_data["commit_sha"]
                )
                result["commit_status"] = commit_status
                result["state"] = commit_status.get("state", "unknown")

            # Get PR workflow runs if we have a PR number
            if task_data.get("pr_number"):
                pr_runs = await self.get_pr_workflow_runs(
                    repo_url, task_data["pr_number"]
                )
                result["workflow_runs"] = pr_runs

                # Get PR info
                pr_info = await self.get_pr_info(
                    repo_url, task_data["pr_number"]
                )
                if pr_info:
                    result["pr_info"] = {
                        "number": pr_info["number"],
                        "title": pr_info["title"],
                        "state": pr_info["state"],
                        "mergeable": pr_info.get("mergeable"),
                        "merged": pr_info.get("merged", False),
                        "html_url": pr_info["html_url"],
                    }

                # Update state based on latest workflow run
                if pr_runs:
                    latest_run = pr_runs[0]
                    if latest_run["status"] == "completed":
                        result["state"] = latest_run["conclusion"]
                    else:
                        result["state"] = latest_run["status"]

            # Get general workflow runs if we have a branch
            elif task_data.get("branch_name"):
                workflow_runs = await self.get_workflow_runs(
                    repo_url, task_data["branch_name"], limit=5
                )
                result["workflow_runs"] = workflow_runs

                if workflow_runs:
                    latest_run = workflow_runs[0]
                    if latest_run["status"] == "completed":
                        result["state"] = latest_run["conclusion"]
                    else:
                        result["state"] = latest_run["status"]

        except Exception as e:
            result["state"] = "error"
            result["error"] = str(e)
            print(f"Error monitoring CI status: {e}")

        return result

    def format_workflow_run_summary(
        self, workflow_runs: List[Dict]
    ) -> List[Dict]:
        """Format workflow runs for frontend display"""
        formatted_runs = []

        for run in workflow_runs:
            formatted_run = {
                "id": run["id"],
                "name": run["name"],
                "status": run["status"],
                "conclusion": run.get("conclusion"),
                "event": run["event"],
                "branch": run["head_branch"],
                "commit_sha": (
                    run["head_sha"][:7] if run.get("head_sha") else None
                ),
                "created_at": run["created_at"],
                "updated_at": run["updated_at"],
                "html_url": run["html_url"],
                "run_number": run["run_number"],
            }

            # Add status emoji and color
            if run["status"] == "completed":
                if run.get("conclusion") == "success":
                    formatted_run["emoji"] = ""
                    formatted_run["color"] = "green"
                elif run.get("conclusion") == "failure":
                    formatted_run["emoji"] = ""
                    formatted_run["color"] = "red"
                elif run.get("conclusion") == "cancelled":
                    formatted_run["emoji"] = ""
                    formatted_run["color"] = "gray"
                else:
                    formatted_run["emoji"] = ""
                    formatted_run["color"] = "orange"
            elif run["status"] == "in_progress":
                formatted_run["emoji"] = ""
                formatted_run["color"] = "blue"
            elif run["status"] == "queued":
                formatted_run["emoji"] = ""
                formatted_run["color"] = "yellow"
            else:
                formatted_run["emoji"] = ""
                formatted_run["color"] = "gray"

            formatted_runs.append(formatted_run)

        return formatted_runs


# Global instance
github_cicd_manager = GitHubCICDManager()


async def get_task_ci_status(task_data: Dict) -> Dict:
    """Convenience function to get CI status for a task"""
    return await github_cicd_manager.monitor_task_ci_status(task_data)


async def get_workflow_runs_for_task(task_data: Dict) -> List[Dict]:
    """Get formatted workflow runs for a task"""
    if not task_data.get("repository_url"):
        return []

    if task_data.get("pr_number"):
        runs = await github_cicd_manager.get_pr_workflow_runs(
            task_data["repository_url"], task_data["pr_number"]
        )
    elif task_data.get("branch_name"):
        runs = await github_cicd_manager.get_workflow_runs(
            task_data["repository_url"], task_data["branch_name"]
        )
    else:
        return []

    return github_cicd_manager.format_workflow_run_summary(runs)
