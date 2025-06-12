#!/usr/bin/env python3
"""
GitHub CI/CD Continuous Monitor

Real-time monitoring tool for GitHub Actions workflows with continuous terminal output.
Provides live status updates, workflow monitoring, and comprehensive CI/CD visibility.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from src.github_cicd import GitHubCICDManager
except ImportError:
    # Fallback if import fails
    GitHubCICDManager = None


class Colors:
    """Terminal colors for output formatting"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"
    CLEAR_LINE = "\033[K"
    CLEAR_SCREEN = "\033[2J"
    CURSOR_HOME = "\033[H"


class GitHubCICDMonitor:
    """Continuous GitHub CI/CD monitoring tool"""

    def __init__(
        self,
        github_token: Optional[str] = None,
        repo_url: Optional[str] = None,
    ):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.repo_url = repo_url or self._detect_repo_url()
        self.base_url = "https://api.github.com"
        self.headers = self._get_headers()
        self.owner, self.repo = (
            self._parse_repo_url(self.repo_url)
            if self.repo_url
            else (None, None)
        )
        self.last_update = None
        self.workflow_cache = {}
        self.run_cache = {}

    def _get_headers(self) -> Dict[str, str]:
        """Get GitHub API headers with authentication"""
        if not self.github_token:
            return {"Accept": "application/vnd.github+json"}

        return {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _detect_repo_url(self) -> Optional[str]:
        """Detect repository URL from git remote"""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _parse_repo_url(self, repo_url: str) -> Tuple[str, str]:
        """Parse GitHub repository URL to extract owner and repo name"""
        import re

        patterns = [
            r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$",
            r"github\.com/([^/]+)/([^/]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, repo_url)
            if match:
                return match.group(1), match.group(2)

        raise ValueError(f"Could not parse GitHub repository URL: {repo_url}")

    def _make_request(
        self, url: str, params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make GitHub API request with error handling"""
        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=10
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                # Rate limit or auth issue
                return {"error": "API rate limit or authentication issue"}
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def get_workflows(self) -> List[Dict]:
        """Get all workflows for the repository"""
        if not self.owner or not self.repo:
            return []

        url = (
            f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/workflows"
        )
        result = self._make_request(url)

        if result and "workflows" in result:
            return result["workflows"]
        return []

    def get_workflow_runs(
        self, workflow_id: Optional[str] = None, limit: int = 10
    ) -> List[Dict]:
        """Get recent workflow runs"""
        if not self.owner or not self.repo:
            return []

        if workflow_id:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/workflows/{workflow_id}/runs"
        else:
            url = (
                f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/runs"
            )

        params = {"per_page": limit}
        result = self._make_request(url, params)

        if result and "workflow_runs" in result:
            return result["workflow_runs"]
        return []

    def get_current_branch(self) -> str:
        """Get current git branch"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"

    def format_status_emoji(
        self, status: str, conclusion: Optional[str] = None
    ) -> str:
        """Get emoji for workflow status"""
        if status == "completed":
            if conclusion == "success":
                return f"{Colors.GREEN}{Colors.END}"
            elif conclusion == "failure":
                return f"{Colors.RED}{Colors.END}"
            elif conclusion == "cancelled":
                return f"{Colors.YELLOW}{Colors.END}"
            else:
                return f"{Colors.PURPLE}?{Colors.END}"
        elif status == "in_progress":
            return f"{Colors.BLUE}{Colors.END}"
        elif status == "queued":
            return f"{Colors.YELLOW}{Colors.END}"
        else:
            return f"{Colors.WHITE}?{Colors.END}"

    def format_duration(
        self, start_time: str, end_time: Optional[str] = None
    ) -> str:
        """Format duration between timestamps"""
        try:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            if end_time:
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            else:
                end = datetime.now(start.tzinfo)

            duration = end - start
            total_seconds = int(duration.total_seconds())

            if total_seconds < 60:
                return f"{total_seconds}s"
            elif total_seconds < 3600:
                return f"{total_seconds // 60}m {total_seconds % 60}s"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}h {minutes}m"
        except Exception:
            return "unknown"

    def clear_screen(self):
        """Clear terminal screen"""
        print(f"{Colors.CLEAR_SCREEN}{Colors.CURSOR_HOME}", end="")

    def print_header(self):
        """Print monitoring header"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_branch = self.get_current_branch()

        print(f"{Colors.BOLD}{Colors.CYAN}GitHub CI/CD Monitor{Colors.END}")
        print("=" * 60)
        print(
            f"Repository: {Colors.WHITE}{self.owner}/{self.repo}{Colors.END}"
        )
        print(f"Branch: {Colors.WHITE}{current_branch}{Colors.END}")
        print(f"Last Update: {Colors.WHITE}{current_time}{Colors.END}")
        print(
            f"Token: {Colors.GREEN}{Colors.END}"
            if self.github_token
            else f"{Colors.RED} (Limited API access){Colors.END}"
        )
        print("=" * 60)

    def print_workflow_summary(self, workflows: List[Dict], runs: List[Dict]):
        """Print workflow summary section"""
        print(f"\n{Colors.BOLD}Workflow Summary{Colors.END}")
        print("-" * 40)

        if not workflows:
            print(f"{Colors.YELLOW}No workflows found{Colors.END}")
            return

        # Group runs by workflow
        workflow_runs = {}
        for run in runs:
            workflow_id = run.get("workflow_id")
            if workflow_id not in workflow_runs:
                workflow_runs[workflow_id] = []
            workflow_runs[workflow_id].append(run)

        for workflow in workflows:
            workflow_id = workflow["id"]
            workflow_name = workflow["name"]
            workflow_file = workflow["path"].split("/")[-1]

            recent_runs = workflow_runs.get(workflow_id, [])
            if recent_runs:
                latest_run = recent_runs[0]
                status_emoji = self.format_status_emoji(
                    latest_run["status"], latest_run.get("conclusion")
                )
                duration = self.format_duration(
                    latest_run["created_at"], latest_run.get("updated_at")
                )
                print(
                    f"{status_emoji} {Colors.WHITE}{workflow_name}{Colors.END} ({workflow_file}) - {duration}"
                )
            else:
                print(
                    f"{Colors.WHITE}{Colors.END} {Colors.WHITE}{workflow_name}{Colors.END} ({workflow_file}) - No recent runs"
                )

    def print_recent_runs(self, runs: List[Dict], limit: int = 10):
        """Print recent workflow runs"""
        print(
            f"\n{Colors.BOLD}Recent Workflow Runs (Last {limit}){Colors.END}"
        )
        print("-" * 60)

        if not runs:
            print(f"{Colors.YELLOW}No recent runs found{Colors.END}")
            return

        for i, run in enumerate(runs[:limit]):
            status_emoji = self.format_status_emoji(
                run["status"], run.get("conclusion")
            )
            workflow_name = run["name"]
            branch = run["head_branch"]
            commit_sha = (
                run["head_sha"][:7] if run.get("head_sha") else "unknown"
            )
            duration = self.format_duration(
                run["created_at"], run.get("updated_at")
            )

            # Format run number and event
            run_number = run.get("run_number", "?")
            event = run.get("event", "unknown")

            print(
                f"{status_emoji} #{run_number} {Colors.WHITE}{workflow_name}{Colors.END}"
            )
            print(
                f"    Branch: {Colors.CYAN}{branch}{Colors.END} | "
                f"Commit: {Colors.PURPLE}{commit_sha}{Colors.END} | "
                f"Event: {Colors.YELLOW}{event}{Colors.END}"
            )
            print(
                f"    Duration: {duration} | "
                f"Started: {datetime.fromisoformat(run['created_at'].replace('Z', '+00:00')).strftime('%H:%M:%S')}"
            )

            if i < len(runs) - 1:
                print()

    def print_active_runs(self, runs: List[Dict]):
        """Print currently active (running/queued) workflow runs"""
        active_runs = [
            run for run in runs if run["status"] in ["in_progress", "queued"]
        ]

        if not active_runs:
            return

        print(f"\n{Colors.BOLD}{Colors.BLUE}Active Runs{Colors.END}")
        print("-" * 30)

        for run in active_runs:
            status_emoji = self.format_status_emoji(run["status"])
            workflow_name = run["name"]
            branch = run["head_branch"]
            duration = self.format_duration(run["created_at"])

            print(
                f"{status_emoji} {Colors.WHITE}{workflow_name}{Colors.END} on {Colors.CYAN}{branch}{Colors.END}"
            )
            print(
                f"    Status: {run['status'].title()} | Duration: {duration}"
            )

    def print_failed_runs(self, runs: List[Dict]):
        """Print recent failed workflow runs"""
        failed_runs = [
            run
            for run in runs
            if run["status"] == "completed"
            and run.get("conclusion") == "failure"
        ][
            :5
        ]  # Show last 5 failures

        if not failed_runs:
            return

        print(f"\n{Colors.BOLD}{Colors.RED}Recent Failures{Colors.END}")
        print("-" * 30)

        for run in failed_runs:
            workflow_name = run["name"]
            branch = run["head_branch"]
            commit_sha = (
                run["head_sha"][:7] if run.get("head_sha") else "unknown"
            )
            failed_time = datetime.fromisoformat(
                run["updated_at"].replace("Z", "+00:00")
            )
            time_ago = datetime.now(failed_time.tzinfo) - failed_time

            if time_ago.days > 0:
                time_str = f"{time_ago.days}d ago"
            elif time_ago.seconds > 3600:
                time_str = f"{time_ago.seconds // 3600}h ago"
            else:
                time_str = f"{time_ago.seconds // 60}m ago"

            print(
                f"{Colors.RED}{Colors.END} {Colors.WHITE}{workflow_name}{Colors.END} on {Colors.CYAN}{branch}{Colors.END}"
            )
            print(
                f"    Commit: {Colors.PURPLE}{commit_sha}{Colors.END} | Failed: {time_str}"
            )

    def print_footer(self, refresh_interval: int):
        """Print monitoring footer"""
        print(f"\n{Colors.BOLD}Controls{Colors.END}")
        print("-" * 20)
        print(f"Refresh: Every {refresh_interval}s | Press Ctrl+C to exit")
        print(
            f"GitHub API Rate Limit: {'Authenticated' if self.github_token else 'Anonymous (60/hour)'}"
        )

    async def monitor_continuous(
        self, refresh_interval: int = 30, show_details: bool = True
    ):
        """Run continuous monitoring with regular updates"""
        print(f"{Colors.BOLD}Starting GitHub CI/CD Monitor...{Colors.END}")

        if not self.owner or not self.repo:
            print(
                f"{Colors.RED}Error: Could not detect repository. Please specify --repo{Colors.END}"
            )
            return

        try:
            while True:
                self.clear_screen()
                self.print_header()

                # Fetch data
                workflows = self.get_workflows()
                runs = self.get_workflow_runs(limit=20)

                if "error" in str(workflows) or "error" in str(runs):
                    print(
                        f"\n{Colors.RED}API Error: Check your GitHub token and network connection{Colors.END}"
                    )
                    await asyncio.sleep(refresh_interval)
                    continue

                # Display sections
                self.print_workflow_summary(workflows, runs)

                if show_details:
                    self.print_active_runs(runs)
                    self.print_failed_runs(runs)
                    self.print_recent_runs(runs, limit=8)

                self.print_footer(refresh_interval)

                # Wait for next refresh
                await asyncio.sleep(refresh_interval)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Monitoring stopped by user{Colors.END}")
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.END}")

    def monitor_once(self, show_details: bool = True):
        """Run monitoring once (non-continuous)"""
        if not self.owner or not self.repo:
            print(
                f"{Colors.RED}Error: Could not detect repository. Please specify --repo{Colors.END}"
            )
            return

        self.print_header()

        # Fetch data
        workflows = self.get_workflows()
        runs = self.get_workflow_runs(limit=20)

        if "error" in str(workflows) or "error" in str(runs):
            print(
                f"\n{Colors.RED}API Error: Check your GitHub token and network connection{Colors.END}"
            )
            return

        # Display sections
        self.print_workflow_summary(workflows, runs)

        if show_details:
            self.print_active_runs(runs)
            self.print_failed_runs(runs)
            self.print_recent_runs(runs, limit=10)


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="GitHub CI/CD Continuous Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Monitor current repository continuously
  %(prog)s --once                   # Single status check
  %(prog)s --repo owner/repo        # Monitor specific repository
  %(prog)s --interval 60            # Refresh every 60 seconds
  %(prog)s --simple                 # Simple output without details

Environment Variables:
  GITHUB_TOKEN                      # GitHub personal access token (recommended)
        """,
    )

    parser.add_argument(
        "--repo",
        help="Repository in format 'owner/repo' (auto-detected if not specified)",
    )
    parser.add_argument(
        "--token", help="GitHub token (or set GITHUB_TOKEN env var)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Refresh interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once instead of continuous monitoring",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Simple output without detailed sections",
    )

    args = parser.parse_args()

    # Determine repository URL
    repo_url = None
    if args.repo:
        repo_url = f"https://github.com/{args.repo}"

    # Create monitor
    monitor = GitHubCICDMonitor(github_token=args.token, repo_url=repo_url)

    # Run monitoring
    if args.once:
        monitor.monitor_once(show_details=not args.simple)
    else:
        await monitor.monitor_continuous(
            refresh_interval=args.interval, show_details=not args.simple
        )


if __name__ == "__main__":
    asyncio.run(main())
