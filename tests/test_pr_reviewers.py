#!/usr/bin/env python3

import unittest
import os
import sys
from unittest.mock import patch, MagicMock, Mock
import json
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import modules to test
from src.pr_reviewers import (
    PRReviewSystem,
    ReviewerPersona,
    review_pr_with_multiple_roles,
)

# Add src to path for imports
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(repo_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


class TestPRReviewers:
    """Test PR review system functionality"""

    def test_reviewer_persona_creation(self):
        """Test creating a reviewer persona"""
        persona = ReviewerPersona(
            name="Test Reviewer",
            role="Test Role",
            expertise=["Python", "Testing"],
            review_prompt_template="Test template",
            focus_areas=["Code quality", "Testing"],
        )

        assert persona.name == "Test Reviewer"
        assert persona.role == "Test Role"
        assert "Python" in persona.expertise
        assert "Code quality" in persona.focus_areas

    def test_pr_review_system_init(self):
        """Test PR review system initialization"""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key", "GITHUB_TOKEN": "test-token"},
        ):
            system = PRReviewSystem()
            assert system.anthropic_client is not None
            assert system.github_headers is not None
            assert len(system.reviewers) > 0
            assert "engineer" in system.reviewers
            assert "infrastructure" in system.reviewers
            assert "product" in system.reviewers
            assert "domain_expert" in system.reviewers

    def test_pr_review_system_init_no_keys(self):
        """Test PR review system initialization without API keys"""
        with patch.dict(os.environ, {}, clear=True):
            system = PRReviewSystem()
            assert system.anthropic_client is None
            assert system.github_headers is None

    @pytest.mark.asyncio
    async def test_get_pr_details_success(self):
        """Test getting PR details successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": 123,
            "title": "Test PR",
            "body": "Test description",
            "user": {"login": "testuser"},
            "head": {"ref": "feature-branch"},
            "base": {"ref": "main"},
        }

        system = PRReviewSystem()
        system.github_headers = {"Authorization": "Bearer test-token"}

        with patch("requests.get", return_value=mock_response):
            result = await system.get_pr_details("owner", "repo", 123)
            assert result["number"] == 123
            assert result["title"] == "Test PR"

    @pytest.mark.asyncio
    async def test_get_pr_details_no_headers(self):
        """Test getting PR details without headers"""
        system = PRReviewSystem()
        system.github_headers = None

        result = await system.get_pr_details("owner", "repo", 123)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_pr_files_success(self):
        """Test getting PR files successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "filename": "test.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "patch": "@@ -1,3 +1,3 @@\n test content",
            }
        ]

        system = PRReviewSystem()
        system.github_headers = {"Authorization": "Bearer test-token"}

        with patch("requests.get", return_value=mock_response):
            result = await system.get_pr_files("owner", "repo", 123)
            assert len(result) == 1
            assert result[0]["filename"] == "test.py"

    def test_format_pr_info(self):
        """Test formatting PR information"""
        system = PRReviewSystem()
        pr_data = {
            "number": 123,
            "title": "Test PR",
            "body": "Test description",
            "user": {"login": "testuser"},
            "head": {"ref": "feature-branch"},
            "base": {"ref": "main"},
            "changed_files": 5,
            "additions": 100,
            "deletions": 50,
        }

        result = system._format_pr_info(pr_data)
        assert "Test PR" in result
        assert "Test PR" in result
        assert "testuser" in result
        assert "feature-branch" in result

    def test_format_file_changes(self):
        """Test formatting file changes"""
        system = PRReviewSystem()
        files = [
            {
                "filename": "test.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "patch": "@@ -1,3 +1,3 @@\n test content",
            },
            {
                "filename": "new_file.py",
                "status": "added",
                "additions": 20,
                "deletions": 0,
            },
        ]

        result = system._format_file_changes(files)
        assert "test.py" in result
        assert "new_file.py" in result
        assert "MODIFIED" in result
        assert "ADDED" in result

    @pytest.mark.asyncio
    async def test_generate_review_success(self):
        """Test generating a review successfully"""
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = [
            Mock(text="## Engineering Review\nThis is a test review")
        ]
        mock_client.messages.create.return_value = mock_message

        system = PRReviewSystem()
        system.anthropic_client = mock_client

        result = await system.generate_review(
            "engineer", "PR info", "File changes"
        )
        assert "Engineering Review" in result
        assert "test review" in result

    @pytest.mark.asyncio
    async def test_generate_review_no_client(self):
        """Test generating review without client"""
        system = PRReviewSystem()
        system.anthropic_client = None

        result = await system.generate_review(
            "engineer", "PR info", "File changes"
        )
        assert result is not None
        assert (
            "Cannot generate engineer review: Missing ANTHROPIC_API_KEY"
            in result
        )

    @pytest.mark.asyncio
    async def test_post_review_comment_success(self):
        """Test posting review comment successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123}

        system = PRReviewSystem()
        system.github_headers = {"Authorization": "Bearer test-token"}

        with patch("requests.post", return_value=mock_response):
            result = await system.post_review_comment(
                "owner", "repo", 123, "Test review"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_analyze_review_sentiment(self):
        """Test analyzing review sentiment"""
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = [
            Mock(
                text='{"sentiment": "positive", "score": 0.8, "key_points": ["good code"]}'
            )
        ]
        mock_client.messages.create.return_value = mock_message

        system = PRReviewSystem()
        system.anthropic_client = mock_client

        result = await system.analyze_review_sentiment("This is great code!")
        assert "sentiment" in result
        assert "score" in result

    @pytest.mark.asyncio
    async def test_conduct_multi_role_review_success(self):
        """Test conducting multi-role review successfully"""
        mock_pr_data = {
            "number": 123,
            "title": "Test PR",
            "body": "Test description",
            "user": {"login": "testuser"},
            "head": {"ref": "feature-branch"},
            "base": {"ref": "main"},
            "changed_files": 3,
            "additions": 75,
            "deletions": 25,
        }

        mock_files = [
            {
                "filename": "test.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "patch": "@@ -1,3 +1,3 @@\n test content",
            }
        ]

        system = PRReviewSystem()

        with patch.object(system, "get_pr_details", return_value=mock_pr_data):
            with patch.object(system, "get_pr_files", return_value=mock_files):
                with patch.object(
                    system, "generate_review", return_value="Test review"
                ):
                    with patch.object(
                        system,
                        "analyze_review_sentiment",
                        return_value={
                            "decision": "APPROVE",
                            "confidence": 0.8,
                            "reasoning": "Test review is positive",
                            "blocking_issues": [],
                        },
                    ):
                        with patch.object(
                            system, "post_review_comment", return_value=True
                        ):
                            result = await system.conduct_multi_role_review(
                                "owner", "repo", 123
                            )

                            assert result["success"] is True
                            assert "reviews" in result
                            assert "decision" in result
                            assert result["decision"] == "APPROVED"

    def test_create_consolidated_review_with_decision(self):
        """Test creating consolidated review with decision"""
        system = PRReviewSystem()
        reviews = {
            "engineer": {
                "reviewer": "Alex Chen",
                "role_title": "Senior Software Engineer",
                "review": "Engineering review content",
                "sentiment": {
                    "decision": "APPROVE",
                    "confidence": 0.8,
                    "reasoning": "Good code quality",
                    "blocking_issues": [],
                },
            },
            "infrastructure": {
                "reviewer": "Jordan Kim",
                "role_title": "Infrastructure Engineer",
                "review": "Infrastructure review content",
                "sentiment": {
                    "decision": "REQUEST_CHANGES",
                    "confidence": 0.6,
                    "reasoning": "Security concerns",
                    "blocking_issues": ["Security issue found"],
                },
            },
        }

        result = system._create_consolidated_review_with_decision(
            reviews, True
        )
        assert "APPROVED" in result
        assert "Engineering review content" in result
        assert "Infrastructure review content" in result

    @pytest.mark.asyncio
    async def test_review_pr_with_multiple_roles(self):
        """Test the main review function"""
        mock_return_value = {
            "success": True,
            "decision": "APPROVED",
            "all_approved": True,
            "approval_count": "4/4",
            "reviews": {},
            "consolidated": "Test consolidated review",
            "review_decisions": {},
        }

        with patch(
            "src.pr_reviewers.pr_review_system.conduct_multi_role_review",
            return_value=mock_return_value,
        ):
            result = await review_pr_with_multiple_roles("owner", "repo", 123)
            assert result["success"] is True
            assert result["decision"] == "APPROVED"
            assert "reviews" in result
