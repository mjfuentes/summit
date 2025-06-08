#!/usr/bin/env python3
"""
Multi-Role PR Review System

Provides automated PR reviews from different perspectives:
- Engineer: Technical implementation and code quality
- Infrastructure: Security, performance, deploymen
- Product: User experience and business requiremen
- Domain Expert: Specific area expertise
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from anthropic import Anthropic


@dataclass
class ReviewerPersona:
    """Defines a reviewer persona with specific expertise and focus areas"""

    name: str
    role: str
    expertise: List[str]
    review_prompt_template: str
    focus_areas: List[str]


class PRReviewSystem:
    """Manages multi-perspective PR reviews using different personas"""

    def __init__(self):
        self.anthropic_client = self._get_anthropic_client()
        self.github_headers = self._get_github_headers()
        self.reviewers = self._define_reviewer_personas()

    def _get_anthropic_client(self) -> Optional[Anthropic]:
        """Get Anthropic client for AI reviews"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        return Anthropic(api_key=api_key)

    def _get_github_headers(self) -> Optional[Dict[str, str]]:
        """Get GitHub API headers"""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return None
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _define_reviewer_personas(self) -> Dict[str, ReviewerPersona]:
        """Define the different reviewer personas"""
        return {
            "engineer": ReviewerPersona(
                name="Alex Chen",
                role="Senior Software Engineer",
                expertise=[
                    "Python",
                    "Architecture",
                    "Testing",
                    "Code Quality",
                ],
                focus_areas=[
                    "Code structure and organization",
                    "Test coverage and quality",
                    "Error handling and edge cases",
                    "Performance implications",
                    "Code maintainability",
                    "Following coding standards",
                ],
                review_prompt_template="""You are Alex Chen, a Senior Software Engineer with 8+ years of experience.

Review this PR with focus on:
- Code quality and maintainability
- Test coverage and edge case
- Error handling and robustne
- Performance consideration
- Architecture and design pattern
- Coding standards compliance

PR Details:
{pr_info}

Changed Files:
{file_changes}

Provide a technical review with specific, actionable feedback. Be constructive but thorough.
Format as: ## Engineering Review by Alex Chen""",
            ),
            "infrastructure": ReviewerPersona(
                name="Jordan Kim",
                role="Infrastructure Engineer",
                expertise=["Security", "DevOps", "Performance", "Monitoring"],
                focus_areas=[
                    "Security vulnerabilities",
                    "Deployment impact",
                    "Resource usage and scaling",
                    "Monitoring and observability",
                    "CI/CD pipeline effects",
                    "Configuration management",
                ],
                review_prompt_template="""You are Jordan Kim, an Infrastructure Engineer specializing in security and deployment.

Review this PR focusing on:
- Security implications and vulnerabilitie
- Deployment and scaling consideration
- CI/CD pipeline impac
- Resource usage and performance
- Monitoring and logging need
- Configuration and environment change

PR Details:
{pr_info}

Changed Files:
{file_changes}

Provide infrastructure-focused feedback on security, deployment, and operational concerns.
Format as: ## Infrastructure Review by Jordan Kim""",
            ),
            "product": ReviewerPersona(
                name="Sam Rodriguez",
                role="Product Manager",
                expertise=[
                    "UX",
                    "Business Logic",
                    "Requirements",
                    "User Impact",
                ],
                focus_areas=[
                    "User experience impact",
                    "Business requirement alignment",
                    "Feature completeness",
                    "API usability",
                    "Documentation quality",
                    "Backward compatibility",
                ],
                review_prompt_template="""You are Sam Rodriguez, a Product Manager focused on user experience and business value.

Review this PR from a product perspective:
- Does this meet the intended user needs?
- Is the API/interface user-friendly?
- Are business requirements satisfied?
- Is documentation clear and complete?
- Any backward compatibility concerns?
- Overall user experience impac

PR Details:
{pr_info}

Changed Files:
{file_changes}

Provide product-focused feedback on usability, requirements, and user impact.
Format as: ## Product Review by Sam Rodriguez""",
            ),
            "domain_expert": ReviewerPersona(
                name="Dr. Taylor Park",
                role="AI/ML Domain Expert",
                expertise=[
                    "AI/ML",
                    "Autonomous Systems",
                    "Integration Patterns",
                ],
                focus_areas=[
                    "AI model integration",
                    "Autonomous system behavior",
                    "API design patterns",
                    "Data flow and processing",
                    "Integration architecture",
                    "System reliability",
                ],
                review_prompt_template="""You are Dr. Taylor Park, an AI/ML expert specializing in autonomous systems and intelligent agent architectures.

Review this PR for:
- AI/ML integration best practice
- Autonomous system reliability
- Agent behavior and decision making
- Integration patterns and data flow
- System architecture implication
- Scalability for AI workload

PR Details:
{pr_info}

Changed Files:
{file_changes}

Provide expert insights on AI/ML aspects, autonomous behavior, and technical architecture.
Format as: ## Domain Expert Review by Dr. Taylor Park""",
            ),
        }

    async def get_pr_details(
        self, owner: str, repo: str, pr_number: int
    ) -> Optional[Dict[str, Any]]:
        """Get PR details from GitHub API"""
        if not self.github_headers:
            return None

        base_url = "https://api.github.com/repos"
        url = f"{base_url}/{owner}/{repo}/pulls/{pr_number}"

        try:
            response = requests.get(
                url, headers=self.github_headers, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting PR details: {e}")
            return None

    async def get_pr_files(
        self, owner: str, repo: str, pr_number: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Get changed files in the PR"""
        if not self.github_headers:
            return None

        base_url = "https://api.github.com/repos"
        url = f"{base_url}/{owner}/{repo}/pulls/{pr_number}/files"

        try:
            response = requests.get(
                url, headers=self.github_headers, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting PR files: {e}")
            return None

    def _format_pr_info(self, pr_data: Dict[str, Any]) -> str:
        """Format PR information for review"""
        return f"""
Title: {pr_data['title']}
Description: {pr_data.get('body', 'No description provided')}
Author: {pr_data['user']['login']}
Branch: {pr_data['head']['ref']} -> {pr_data['base']['ref']}
Files Changed: {pr_data['changed_files']}
Additions: +{pr_data['additions']} | Deletions: -{pr_data['deletions']}
"""

    def _format_file_changes(self, files: List[Dict[str, Any]]) -> str:
        """Format file changes for review"""
        if not files:
            return "No file changes available"

        formatted = []
        for file in files[:10]:  # Limit to first 10 files for contex
            status = file["status"]
            filename = file["filename"]
            changes = f"+{file['additions']} -{file['deletions']}"

            formatted.append(f"- {status.upper()}: {filename} ({changes})")

            # Add patch preview for small change
            if file.get("patch") and len(file["patch"]) < 2000:
                formatted.append(f"  Preview:\n{file['patch'][:500]}...")

        if len(files) > 10:
            formatted.append(f"... and {len(files) - 10} more files")

        return "\n".join(formatted)

    async def generate_review(
        self, persona_key: str, pr_info: str, file_changes: str
    ) -> Optional[str]:
        """Generate a review from a specific persona"""
        if not self.anthropic_client:
            return f"Cannot generate {persona_key} review: Missing ANTHROPIC_API_KEY"

        persona = self.reviewers[persona_key]
        prompt = persona.review_prompt_template.format(
            pr_info=pr_info, file_changes=file_changes
        )

        try:
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )

            return message.content[0].text

        except Exception as e:
            return f"Error generating {persona_key} review: {e}"

    async def post_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review_body: str,
        event: str = "COMMENT",
    ) -> bool:
        """Post a review comment to the PR"""
        if not self.github_headers:
            return False

        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"

        payload = {
            "body": review_body,
            "event": event,  # COMMENT, APPROVE, REQUEST_CHANGES
        }

        try:
            response = requests.post(
                url, headers=self.github_headers, json=payload, timeout=30
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error posting review: {e}")
            return False

    async def analyze_review_sentiment(
        self, review_text: str
    ) -> Dict[str, Any]:
        """Analyze review sentiment to determine if it's an approval or request for changes"""
        if not self.anthropic_client:
            return {
                "decision": "REQUEST_CHANGES",
                "confidence": 0.0,
                "reasoning": "No Claude client available",
                "blocking_issues": ["API not configured"],
            }

        analysis_prompt = f"""Analyze this PR review and determine if the reviewer is approving or requesting changes:

Review text:
{review_text}

Consider:
- Does the reviewer suggest the code is ready to merge?
- Are the concerns minor (comments/suggestions) or major (blocking issues)?

Respond in this exact JSON format:
{{"decision": "APPROVE" or "REQUEST_CHANGES",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of the decision",
    "blocking_issues": ["list", "of", "any", "blocking", "issues"]
}}"""

        try:
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": analysis_prompt}],
            )

            import json

            result = json.loads(message.content[0].text)
            return result

        except Exception as e:
            return {
                "decision": "REQUEST_CHANGES",  # Default to cautious
                "confidence": 0.0,
                "reasoning": f"Error analyzing review: {e}",
                "blocking_issues": ["Analysis failed"],
            }

    async def conduct_multi_role_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        selected_roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Conduct a comprehensive multi-role review of the PR with automatic approval"""
        if selected_roles is None:
            selected_roles = list(self.reviewers.keys())

        # Get PR details and file
        pr_data = await self.get_pr_details(owner, repo, pr_number)
        if not pr_data:
            return {"error": "Could not fetch PR details"}

        files = await self.get_pr_files(owner, repo, pr_number)
        if not files:
            return {"error": "Could not fetch PR files"}

        # Format information for reviewer
        pr_info = self._format_pr_info(pr_data)
        file_changes = self._format_file_changes(files)

        # Generate reviews from each persona
        reviews = {}
        review_decisions = {}

        for role in selected_roles:
            if role in self.reviewers:
                print(f"Generating {role} review...")
                review = await self.generate_review(
                    role, pr_info, file_changes
                )

                if review:
                    # Analyze the review sentimen
                    sentiment = await self.analyze_review_sentiment(review)

                    reviews[role] = {
                        "reviewer": self.reviewers[role].name,
                        "role_title": self.reviewers[role].role,
                        "review": review,
                        "sentiment": sentiment,
                    }

                    review_decisions[role] = sentiment["decision"]
                    print(
                        f"{role} review: {sentiment['decision']} "
                        f"(confidence: {sentiment['confidence']:.2f})"
                    )

        # Determine overall approval statu
        all_approvals = all(
            decision == "APPROVE" for decision in review_decisions.values()
        )
        total_reviewers = len(review_decisions)
        approvals = sum(1 for d in review_decisions.values() if d == "APPROVE")

        # Create consolidated review with decision
        consolidated_review = self._create_consolidated_review_with_decision(
            reviews, all_approvals
        )

        # Post the consolidated review
        if all_approvals and total_reviewers >= 2:  # Need at least 2 approval
            # Post as APPROVE
            success = await self.post_review_comment(
                owner, repo, pr_number, consolidated_review, "APPROVE"
            )
            decision = "APPROVED"
        elif any(
            decision == "REQUEST_CHANGES"
            for decision in review_decisions.values()
        ):
            # Post as REQUEST_CHANGES
            success = await self.post_review_comment(
                owner, repo, pr_number, consolidated_review, "REQUEST_CHANGES"
            )
            decision = "CHANGES_REQUESTED"
        else:
            # Post as COMMENT (neutral)
            success = await self.post_review_comment(
                owner, repo, pr_number, consolidated_review, "COMMENT"
            )
            decision = "COMMENTED"

        return {
            "success": success,
            "decision": decision,
            "all_approved": all_approvals,
            "approval_count": f"{approvals}/{total_reviewers}",
            "reviews": reviews,
            "consolidated": consolidated_review,
            "review_decisions": review_decisions,
        }

    def _create_consolidated_review_with_decision(
        self, reviews: Dict[str, Dict[str, Any]], all_approved: bool
    ) -> str:
        """Create a consolidated review with clear approval/rejection decision"""

        # Header with decision
        if all_approved:
            header = """# Multi-Role PR Review - APPROVED

All reviewers from our expert panel have approved this PR! The changes meet quality, security, and business requirements.

"""
        else:
            header = """# Multi-Role PR Review - CHANGES REQUESTED

Our expert panel has identified issues that need to be addressed before this PR can be merged.

"""

        # Summary section
        approvals = sum(
            1
            for r in reviews.values()
            if r["sentiment"]["decision"] == "APPROVE"
        )
        total = len(reviews)

        summary = f"""## Review Summary
- **Approval Status**: {approvals}/{total} reviewers approved
- **Decision**: {"APPROVED - Ready to merge" if all_approved else "CHANGES REQUESTED - Please address issues below"}

"""

        # Individual review
        review_sections = []
        for role, review_data in reviews.items():
            sentiment = review_data["sentiment"]
            decision_icon = "" if sentiment["decision"] == "APPROVE" else ""

            section = f"""
---

{decision_icon} **{sentiment["decision"]}** - Confidence: {sentiment["confidence"]:.0%}

{review_data['review']}

*Review by {review_data['reviewer']}, {review_data['role_title']}*

"""
            review_sections.append(section)

        footer = f"""
---

**Next Steps**:
{" This PR is approved and ready for auto-merge once CI passes!" if all_approved else " Please address the requested changes and update this PR for re-review."}

**Note**: This is an automated multi-perspective review by Summit AI. Each reviewer uses their domain expertise to ensure comprehensive code quality, security, and business alignment.
"""

        return header + summary + "".join(review_sections) + footer


# Global instance for easy acce
pr_review_system = PRReviewSystem()
