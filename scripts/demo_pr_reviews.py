#!/usr/bin/env python3
"""
Demo script for Summit Agent Role System and PR Reviews

This script demonstrates how different agent roles handle PR reviews
through the agent coordination system.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent_roles import AgentRoles


def demonstrate_agent_roles():
    """Demonstrate the available agent roles in Summit"""
    print("=" * 60)
    print("SUMMIT AGENT ROLE SYSTEM")
    print("=" * 60)

    agent_roles = AgentRoles()

    print("\nAvailable Agent Roles:")
    print("-" * 30)

    for role_name in agent_roles.get_all_roles():
        role_info = agent_roles.get_role_info(role_name)

        print(f"\n {role_name.upper()}")
        print(f"   Description: {role_info['description']}")
        print(f"   Capabilities: {', '.join(role_info['capabilities'])}")

        if "focus_areas" in role_info:
            print(f"   Focus Areas: {', '.join(role_info['focus_areas'])}")


def demonstrate_pr_review_workflow():
    """Demonstrate how PR reviews work through agent coordination"""
    print("\n" + "=" * 60)
    print("PR REVIEW THROUGH AGENT COORDINATION")
    print("=" * 60)

    print("\nHow PR Reviews Work in Summit:")
    print("-" * 35)

    workflow_steps = [
        "1. Agent creates a Pull Request",
        "2. System creates agent tasks for different review roles:",
        "   • Engineering review task → assigned to 'engineering' agents",
        "   • Security review task → assigned to 'security' agents",
        "   • Infrastructure review task → assigned to 'infrastructure' agents",
        "3. Available agents claim tasks based on their roles",
        "4. Each agent performs specialized review in parallel",
        "5. Reviews are consolidated and posted to the PR",
        "6. System determines approval based on review results",
    ]

    for step in workflow_steps:
        print(f"   {step}")

    print("\n Example Review Task Assignment:")
    print("   Task: 'review_pr' with PR #123")
    print("   Assigned Role: 'engineering'")
    print("   Task Data: {")
    print("     'pr_number': 123,")
    print("     'repository': 'summit',")
    print("     'focus_areas': ['code_quality', 'testing', 'architecture']")
    print("   }")


def demonstrate_role_specialization():
    """Show how different roles specialize in review areas"""
    print("\n" + "=" * 60)
    print("AGENT ROLE SPECIALIZATION")
    print("=" * 60)

    specializations = {
        "engineering": [
            "Code quality and maintainability",
            "Testing coverage and edge cases",
            "Architecture and design patterns",
            "Performance considerations",
            "Error handling and robustness",
        ],
        "security": [
            "Security vulnerabilities",
            "Authentication and authorization",
            "Data validation and sanitization",
            "Encryption and secure communication",
            "Access control and permissions",
        ],
        "infrastructure": [
            "Deployment considerations",
            "Scalability and resource usage",
            "Monitoring and observability",
            "CI/CD pipeline impact",
            "Configuration management",
        ],
        "product": [
            "User experience impact",
            "Business requirement alignment",
            "API usability and design",
            "Documentation quality",
            "Backward compatibility",
        ],
    }

    for role, areas in specializations.items():
        print(f"\n {role.upper()} AGENT FOCUS:")
        for area in areas:
            print(f"   • {area}")


def show_agent_coordination_benefits():
    """Show benefits of the agent coordination approach"""
    print("\n" + "=" * 60)
    print("BENEFITS OF AGENT COORDINATION")
    print("=" * 60)

    benefits = [
        " Scalable: Add more agents of any role as needed",
        " Parallel: Multiple agents can review simultaneously",
        " Specialized: Each agent focuses on their expertise area",
        " Flexible: Easy to add new roles and capabilities",
        " Trackable: All review tasks are logged and monitored",
        " Autonomous: Agents work independently and coordinate",
        " Efficient: No single bottleneck for reviews",
        " Reliable: Failed reviews can be reassigned automatically",
    ]

    print("\nWhy Agent Coordination > Legacy Multi-Role Reviews:")
    for benefit in benefits:
        print(f"   {benefit}")


async def show_sample_task_creation():
    """Demonstrate how review tasks are created"""
    print("\n" + "=" * 60)
    print("SAMPLE AGENT TASK CREATION")
    print("=" * 60)

    print("\nWhen a PR needs review, Summit creates tasks like this:")
    print("-" * 50)

    sample_tasks = [
        {
            "task_type": "pr_review",
            "assigned_role": "engineering",
            "task_description": "Engineering review of PR #123: Add caching system",
            "priority": 1,
            "task_data": {
                "pr_number": 123,
                "repository": "summit",
                "focus": "code_quality",
            },
        },
        {
            "task_type": "pr_review",
            "assigned_role": "security",
            "task_description": "Security review of PR #123: Add caching system",
            "priority": 1,
            "task_data": {
                "pr_number": 123,
                "repository": "summit",
                "focus": "security_analysis",
            },
        },
    ]

    for i, task in enumerate(sample_tasks, 1):
        print(f"\nTask {i}:")
        print(f"   Type: {task['task_type']}")
        print(f"   Role: {task['assigned_role']}")
        print(f"   Description: {task['task_description']}")
        print(f"   Priority: {task['priority']}")
        print(f"   Data: {task['task_data']}")


def main():
    """Main demo function"""
    print("Summit Agent-Based PR Review System Demo")
    print("=" * 50)

    print("\nThis demo shows how Summit's agent coordination system")
    print("handles PR reviews through specialized agent roles.")

    demonstrate_agent_roles()
    demonstrate_pr_review_workflow()
    demonstrate_role_specialization()
    show_agent_coordination_benefits()

    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)

    next_steps = [
        "1. Deploy agents with different roles to your cluster",
        "2. Agents will automatically register and await tasks",
        "3. When PRs are created, review tasks are assigned by role",
        "4. Agents perform specialized reviews in parallel",
        "5. Monitor agent coordination through the developer dashboard",
    ]

    for step in next_steps:
        print(f"   {step}")

    print(f"\n Developer Dashboard: http://localhost:8000/dev")
    print(f" Agent Status: http://localhost:8000/api/agents/status")

    print("\n" + "=" * 60)
    print("DEMO COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
