#!/usr/bin/env python3
"""
Test script for the Multi-Role PR Review System

This script demonstrates how the different reviewer personas analyze PRs
from their respective expertise areas.
"""

from pr_reviewers import pr_review_system, review_pr_with_multiple_roles
import asyncio
import os
import sys

import pytest
import pytest_asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


@pytest.mark.asyncio
async def test_single_persona_review():
    """Test a single reviewer persona"""
    print("Testing single persona review...")

    # Mock PR data for testing
    mock_pr_info = """
Title: feat: implement PR-based workflow for autonomous agent
Description: Add automated PR creation and multi-role review system for autonomous development tasks
Author: claude-ai-assistant
Branch: feature/pr-workflow -> main
Files Changed: 5
Additions: +500 | Deletions: -50
"""

    mock_file_changes = """
- MODIFIED: src/summit.py (+120 -10)
  Preview:
  @@ -200,6 +200,30 @@ async def create_pull_request(owner: str, repo: str, title: str, head: str, bas
  +    async def conduct_multi_role_review(self, owner: str, repo: str, pr_number: int):
  +        # Get PR details and conduct reviews from multiple perspectives

- ADDED: src/pr_reviewers.py (+350 -0)
  Preview:
  New file implementing multi-role PR review system with personas:
  - Engineer (Alex Chen): Technical implementation and code quality
  - Infrastructure (Jordan Kim): Security, performance, deployment

- MODIFIED: web/autonomous_server.py (+80 -20)
  Preview:
  Integration of multi-role review system into autonomous agent workflow
"""

    # Test engineer review
    engineer_review = await pr_review_system.generate_review(
        "engineer", mock_pr_info, mock_file_changes
    )
    print("\n" + "=" * 60)
    print("ENGINEER REVIEW:")
    print("=" * 60)
    print(engineer_review)

    return engineer_review


@pytest.mark.asyncio
async def test_multi_role_review_on_current_pr():
    """Test the multi-role review system on our actual PR"""
    print("\nTesting multi-role review on current PR...")

    # Test on our actual PR
    owner = "mjfuentes"
    repo = "summit"
    pr_number = 1  # Our current PR

    try:
        result = await review_pr_with_multiple_roles(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            roles=["engineer", "infrastructure"],  # Test with 2 roles first
        )

        if result.get("success"):
            print("\n" + "=" * 60)
            print("MULTI-ROLE REVIEW POSTED SUCCESSFULLY!")
            print("=" * 60)
            print(
                f"Check the PR at: https://github.com/{owner}/{repo}/pull/{pr_number}"
            )

            # Show preview of consolidated review
            if "consolidated" in result:
                print("\nConsolidated Review Preview:")
                print("-" * 40)
                print(result["consolidated"][:500] + "...")
        else:
            print(f"Review failed: {result}")

    except Exception as e:
        print(f"Error testing multi-role review: {e}")


async def demonstrate_all_personas():
    """Demonstrate all reviewer personas"""
    print("\n" + "=" * 60)
    print("DEMONSTRATING ALL REVIEWER PERSONAS")
    print("=" * 60)

    # Mock scenario: Adding AI model caching feature
    pr_info = """
Title: feat: add intelligent model response caching system
Description: Implement Redis-based caching for AI model responses to improve performance and reduce API costs
Author: developer
Branch: feature/ai-caching -> main
Files Changed: 8
Additions: +420 | Deletions: -15
"""

    file_changes = """
- ADDED: src/cache_manager.py (+180 -0)
  Preview: New Redis-based caching system for AI responses
- MODIFIED: src/summit.py (+95 -10)
  Preview: Integration of caching layer into AI advice system
- ADDED: requirements.txt dependencies: redis>=4.0.0, redis-py>=4.0.0
- MODIFIED: config/config.py (+30 -5)
  Preview: Added Redis configuration and cache settings
- ADDED: tests/test_cache_manager.py (+115 -0)
  Preview: Comprehensive test suite for caching functionality
"""

    personas = ["engineer", "infrastructure", "product", "domain_expert"]

    for persona in personas:
        print(f"\n{'-'*50}")
        print(f"GENERATING {persona.upper()} REVIEW...")
        print(f"{'-'*50}")

        review = await pr_review_system.generate_review(
            persona, pr_info, file_changes
        )
        if review:
            print(review[:800] + "..." if len(review) > 800 else review)
        else:
            print(f"Failed to generate {persona} review")

        print()


async def show_reviewer_personas():
    """Display information about available reviewer personas"""
    print("\n" + "=" * 60)
    print("AVAILABLE REVIEWER PERSONAS")
    print("=" * 60)

    for key, persona in pr_review_system.reviewers.items():
        print(f"\n{persona.name} - {persona.role}")
        print(f"Expertise: {', '.join(persona.expertise)}")
        print("Focus Areas:")
        for area in persona.focus_areas:
            print(f"  • {area}")


async def main():
    """Main test function"""
    print("Multi-Role PR Review System Test")
    print("=" * 50)

    # Check environment
    if not os.getenv("ANTHROPIC_API_KEY"):
        print(
            "WARNING: ANTHROPIC_API_KEY not found. AI reviews will not work."
        )

    if not os.getenv("GITHUB_TOKEN"):
        print(
            "WARNING: GITHUB_TOKEN not found. Cannot post reviews to GitHub."
        )

    print("\nAvailable tests:")
    print("1. Show reviewer personas")
    print("2. Test single persona review (mock data)")
    print("3. Demonstrate all personas (mock data)")
    print("4. Test on actual PR #1 (requires GitHub access)")

    try:
        choice = input("\nSelect test (1-4) or press Enter for all: ").strip()

        if not choice or choice == "1":
            await show_reviewer_personas()

        if not choice or choice == "2":
            await test_single_persona_review()

        if not choice or choice == "3":
            await demonstrate_all_personas()

        if choice == "4":
            confirm = (
                input("\nThis will post reviews to PR #1. Continue? (y/N): ")
                .strip()
                .lower()
            )
            if confirm == "y":
                await test_multi_role_review_on_current_pr()
            else:
                print("Skipped actual PR test.")

        print("\n" + "=" * 60)
        print("TEST COMPLETED")
        print("=" * 60)
        print("\nNext steps:")
        print(
            "1. The multi-role review system is integrated into autonomous_server.py"
        )
        print(
            "2. When agents create PRs, they automatically get multi-perspective reviews"
        )
        print("3. Each reviewer provides expertise-focused feedback")
        print(
            "4. Reviews help ensure code quality, security, and business alignment"
        )

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"\nTest error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
