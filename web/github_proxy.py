#!/usr/bin/env python3

"""
GitHub Proxy Service for Summit Autonomous AI
Provides secure, limited access to GitHub operations for Claude Code containers.
"""

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests


@dataclass
class RepositoryAccess:
    """Defines what operations are allowed on a repository"""

    repo_url: str
    owner: str
    repo_name: str
    allowed_operations: List[str]  # ['read', 'write', 'push', 'create_pr']
    max_commits_per_hour: int = 10
    expires_at: Optional[float] = None


class GitHubProxy:
    """Secure proxy for GitHub operations with limited access controls"""

    def __init__(self, github_token: str):
        self.github_token = github_token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Summit-AI-Proxy/1.0",
            }
        )

        # Track operations for rate limiting
        self.operation_log: Dict[str, List[float]] = {}

        # Allowed repositories and their permissions
        self.repository_access: Dict[str, RepositoryAccess] = {}

        # Security settings
        self.max_file_size = 10 * 1024 * 1024  # 10MB max file size
        self.blocked_paths = [
            ".env",
            ".secrets",
            "credentials.json",
            "private_key",
            "*.pem",
            "*.key",
            "*.p12",
            "*.pfx",
        ]

    def add_repository_access(
        self,
        repo_url: str,
        operations: List[str],
        max_commits_per_hour: int = 10,
        expires_in_hours: int = 24,
    ):
        """Grant access to a specific repository with limited operations"""
        parsed_url = urlparse(repo_url)
        path_parts = parsed_url.path.strip("/").split("/")

        if len(path_parts) < 2:
            raise ValueError("Invalid repository URL")

        owner, repo_name = path_parts[0], path_parts[1].replace(".git", "")

        expires_at = (
            time.time() + (expires_in_hours * 3600)
            if expires_in_hours
            else None
        )

        access = RepositoryAccess(
            repo_url=repo_url,
            owner=owner,
            repo_name=repo_name,
            allowed_operations=operations,
            max_commits_per_hour=max_commits_per_hour,
            expires_at=expires_at,
        )

        repo_key = f"{owner}/{repo_name}"
        self.repository_access[repo_key] = access

        print(f"Repository access granted: {repo_key}")
        print(f"   Operations: {', '.join(operations)}")
        print(f"   Rate limit: {max_commits_per_hour} commits/hour")
        if expires_at:
            print(f"   Expires: {time.ctime(expires_at)}")

    def check_access(self, owner: str, repo_name: str, operation: str) -> bool:
        """Check if an operation is allowed on a repository"""
        repo_key = f"{owner}/{repo_name}"
        access = self.repository_access.get(repo_key)

        if not access:
            print(f"No access configured for {repo_key}")
            return False

        if access.expires_at and time.time() > access.expires_at:
            print(f"Access expired for {repo_key}")
            return False

        if operation not in access.allowed_operations:
            print(f"Operation '{operation}' not allowed for {repo_key}")
            return False

        # Check rate limiting
        now = time.time()
        hour_ago = now - 3600

        if repo_key not in self.operation_log:
            self.operation_log[repo_key] = []

        # Clean old operations
        self.operation_log[repo_key] = [
            t for t in self.operation_log[repo_key] if t > hour_ago
        ]

        if len(self.operation_log[repo_key]) >= access.max_commits_per_hour:
            print(
                f"Rate limit exceeded for {repo_key} ({access.max_commits_per_hour}/hour)"
            )
            return False

        return True

    def log_operation(self, owner: str, repo_name: str, operation: str):
        """Log an operation for rate limiting"""
        repo_key = f"{owner}/{repo_name}"
        if repo_key not in self.operation_log:
            self.operation_log[repo_key] = []
        self.operation_log[repo_key].append(time.time())

        print(f"Logged operation: {operation} on {repo_key}")

    def is_file_allowed(self, file_path: str, content: bytes = None) -> bool:
        """Check if a file is allowed to be modified"""
        # Check blocked paths
        for pattern in self.blocked_paths:
            if pattern.startswith("*"):
                if file_path.endswith(pattern[1:]):
                    return False
            elif pattern in file_path:
                return False

        # Check file size
        if content and len(content) > self.max_file_size:
            print(
                f"File too large: {len(content)} bytes > {self.max_file_size}"
            )
            return False

        return True

    def create_limited_token(
        self, repo_url: str, operations: List[str], expires_in_hours: int = 2
    ) -> str:
        """Create a limited-scope token for specific operations"""
        # Add repository access
        self.add_repository_access(
            repo_url,
            operations,
            max_commits_per_hour=5,
            expires_in_hours=expires_in_hours,
        )

        # Generate a proxy token (not a real GitHub token)
        proxy_data = {
            "repo_url": repo_url,
            "operations": operations,
            "expires_at": time.time() + (expires_in_hours * 3600),
            "created_at": time.time(),
        }

        proxy_token = hashlib.sha256(
            f"{repo_url}{time.time()}{self.github_token}".encode()
        ).hexdigest()[:32]

        # Store proxy token mapping
        self.store_proxy_token(proxy_token, proxy_data)

        return f"summit_proxy_{proxy_token}"

    def store_proxy_token(self, proxy_token: str, data: Dict):
        """Store proxy token data securely"""
        # In production, use encrypted storage
        token_file = f"/tmp/summit_proxy_{proxy_token}.json"
        with open(token_file, "w") as f:
            json.dump(data, f)
        os.chmod(token_file, 0o600)  # Readable only by owner

    def validate_proxy_token(self, proxy_token: str) -> Optional[Dict]:
        """Validate and retrieve proxy token data"""
        if not proxy_token.startswith("summit_proxy_"):
            return None

        token_id = proxy_token.replace("summit_proxy_", "")
        token_file = f"/tmp/summit_proxy_{token_id}.json"

        try:
            with open(token_file, "r") as f:
                data = json.load(f)

            if time.time() > data["expires_at"]:
                os.unlink(token_file)  # Clean up expired token
                return None

            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return None


# Security Configuration Manager
class SecurityConfig:
    """Manages security settings for Claude Code containers"""

    @staticmethod
    def create_container_env(
        repo_url: str, task_description: str
    ) -> Dict[str, str]:
        """Create secure environment variables for container"""
        proxy = GitHubProxy(os.getenv("GITHUB_TOKEN", ""))

        # Determine required operations based on task
        operations = ["read"]
        if any(
            keyword in task_description.lower()
            for keyword in [
                "commit",
                "push",
                "save",
                "update",
                "fix",
                "add",
                "create",
            ]
        ):
            operations.extend(["write", "push"])

        if (
            "pull request" in task_description.lower()
            or "pr" in task_description.lower()
        ):
            operations.append("create_pr")

        # Create limited token
        limited_token = proxy.create_limited_token(
            repo_url, operations, expires_in_hours=4
        )

        return {
            "GITHUB_PROXY_TOKEN": limited_token,
            "GITHUB_PROXY_URL": "http://localhost:8082",  # Proxy service URL
            "ALLOWED_OPERATIONS": ",".join(operations),
            "REPOSITORY_URL": repo_url,
            "SECURITY_MODE": "proxy",
        }

    @staticmethod
    def get_claude_permissions() -> Dict:
        """Get Claude Code permission configuration"""
        return {
            "auto_approve": {
                "file_edits": False,  # Always require approval for file edits
                "command_execution": True,  # Allow standard commands
                "git_operations": False,  # Use proxy for Git operations
            },
            "allowed_commands": [
                "git status",
                "git log",
                "git diff",
                "git branch",
                "npm",
                "pip",
                "python",
                "python3",
                "node",
                "pytest",
                "black",
                "flake8",
                "mypy",
                "eslint",
                "prettier",
                "ls",
                "cat",
                "grep",
                "find",
                "echo",
                "which",
            ],
            "restricted_commands": [
                "git push",
                "git commit",  # Use proxy instead
                "sudo",
                "su",
                "rm -rf",
                "chmod +x",
                "curl",
                "wget",  # Prevent data exfiltration
            ],
            "proxy_commands": {
                "git commit": "github-proxy commit",
                "git push": "github-proxy push",
            },
        }


if __name__ == "__main__":
    # Example usage
    github_token = "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"
    proxy = GitHubProxy(github_token)

    # Grant limited access to a repository
    repo_url = "https://github.com/user/repo"
    operations = ["read", "write", "push"]

    proxy.add_repository_access(repo_url, operations, max_commits_per_hour=5)

    # Create limited token for Claude Code
    limited_token = proxy.create_limited_token(repo_url, operations)
    print(f"Limited token created: {limited_token}")

    # Security config
    config = SecurityConfig()
    env_vars = config.create_container_env(
        repo_url, "Fix the authentication bug"
    )
    print("Container environment:", env_vars)
