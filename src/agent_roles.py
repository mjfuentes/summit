"""
Agent Role Definitions for Summit AI Platform
Defines role-specific configurations, contexts, and capabilities
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentRole(str, Enum):
    """Supported agent roles in the Summit system"""

    PRODUCT = "product"
    ENGINEERING = "engineering"
    QUALITY_CONTROL = "quality_control"


@dataclass
class RoleContext:
    """Context configuration for a specific agent role"""

    role: AgentRole
    name: str
    description: str
    capabilities: List[str]
    max_context_tokens: int
    system_prompt: str
    requires_filesystem: bool
    filesystem_reset_between_tasks: bool
    environment_variables: Dict[str, str]
    tools_enabled: List[str]


class AgentRoleManager:
    """Manages agent role configurations and contexts"""

    def __init__(self):
        self.role_configs = self._initialize_role_configs()

    def _initialize_role_configs(self) -> Dict[AgentRole, RoleContext]:
        """Initialize all role configurations"""

        # Shared context that all agents need
        shared_context = self._get_shared_context()

        return {
            AgentRole.PRODUCT: RoleContext(
                role=AgentRole.PRODUCT,
                name="Product Agent",
                description="First agent to receive tasks, analyzes requirements vs existing solutions, provides product perspective",
                capabilities=[
                    "requirements_analysis",
                    "existing_solution_analysis",
                    "gap_identification",
                    "product_specification",
                    "user_experience_analysis",
                    "acceptance_criteria_definition",
                ],
                max_context_tokens=8000,
                system_prompt=self._get_product_prompt(shared_context),
                requires_filesystem=True,  # Need to analyze existing codebase
                filesystem_reset_between_tasks=False,  # Keep context across analysis
                environment_variables={
                    "ROLE": "product",
                    "FOCUS": "requirement_analysis",
                    "WORKFLOW_STAGE": "first",
                },
                tools_enabled=["read", "search", "write"],
            ),
            AgentRole.ENGINEERING: RoleContext(
                role=AgentRole.ENGINEERING,
                name="Engineering Agent",
                description="Takes product input and implements the technical solution",
                capabilities=[
                    "code_implementation",
                    "product_requirement_interpretation",
                    "technical_solution_design",
                    "code_development",
                    "git_operations",
                    "testing_implementation",
                ],
                max_context_tokens=10000,
                system_prompt=self._get_engineering_prompt(shared_context),
                requires_filesystem=True,
                filesystem_reset_between_tasks=True,
                environment_variables={
                    "ROLE": "engineering",
                    "FOCUS": "implementation",
                    "GIT_OPERATIONS": "enabled",
                    "WORKFLOW_STAGE": "second",
                },
                tools_enabled=[
                    "bash",
                    "read",
                    "write",
                    "search",
                    "git_wrapper",
                ],
            ),
            AgentRole.QUALITY_CONTROL: RoleContext(
                role=AgentRole.QUALITY_CONTROL,
                name="Quality Control Agent",
                description="Validates implementation follows product requirements and maintains code quality",
                capabilities=[
                    "implementation_validation",
                    "product_requirement_compliance",
                    "code_quality_review",
                    "test_coverage_analysis",
                    "code_duplication_detection",
                    "unauthorized_change_detection",
                    "meaningful_change_validation",
                ],
                max_context_tokens=12000,
                system_prompt=self._get_quality_control_prompt(shared_context),
                requires_filesystem=True,
                filesystem_reset_between_tasks=False,  # Need to compare before/after
                environment_variables={
                    "ROLE": "quality_control",
                    "FOCUS": "validation",
                    "WORKFLOW_STAGE": "final",
                },
                tools_enabled=[
                    "bash",
                    "read",
                    "write",
                    "search",
                    "diff",
                    "pytest",
                    "coverage",
                ],
            ),
        }

    def _get_shared_context(self) -> str:
        """Get shared context that all agents need"""
        return """
# Summit AI Platform - Agent System Context

## Project Overview
Summit is an autonomous AI development platform that uses specialized agents for different aspects of software development. You are part of a multi-agent system where each agent has specific roles and responsibilities.

## Core Principles
- Quality-first development with automated testing
- Professional technical communication
- Mandatory Git wrapper usage (never direct git commands)
- Database-driven task coordination
- Role-based specialization

## System Architecture
- PostgreSQL database for unified data storage
- Kubernetes-based agent deployment
- Google Cloud Tasks for message delivery
- Role-based task assignment and execution
- Shared context between agents via database

## Git Operations Protocol
CRITICAL: You MUST use the agent Git wrapper for ALL git operations:
- Import: `from src.agent_git_api import save_work, create_pr, status, pull`
- Save work: `save_work("commit message")`
- Create PR: `create_pr("commit", "title", "description")`
- Check status: `status()`
- Update: `pull()`

## Quality Standards
- All code changes require comprehensive tests
- Maintain >70% test coverage
- Follow professional coding standards
- No debugging statements in production
- Clean, readable, maintainable code

## Inter-Agent Coordination
- Tasks are assigned based on agent roles
- Shared context stored in database
- Update task status appropriately
- Coordinate with other agents when needed

"""

    def _get_engineering_prompt(self, shared_context: str) -> str:
        """Get system prompt for engineering agents"""
        return f"""{shared_context}

## Your Role: Engineering Agent

You are the second agent in the workflow. You receive refined requirements from the Product Agent and implement the technical solution.

### Your Responsibilities
- Implement exactly what the Product Agent specified
- Follow the technical approach outlined in the product analysis
- Write clean, tested, maintainable code
- Use the agent Git wrapper for all commits
- Focus only on the requested functionality

### Your Process
1. **Read Product Analysis**: Review the product agent's output thoroughly
2. **Understand Requirements**: Ensure you understand what needs to be built
3. **Plan Implementation**: Break down the work into logical steps
4. **Implement Solution**: Write code that matches the product specification
5. **Test Implementation**: Ensure your code works and has proper tests
6. **Commit Changes**: Use git wrapper to save your work

### Critical Guidelines
- ONLY implement what the Product Agent specified
- Do NOT add extra features or "improvements" not requested
- Follow existing code patterns and conventions
- Write tests for new functionality
- Update existing tests if needed
- Use meaningful commit messages

### Code Quality Standards
- Maintain >70% test coverage
- Follow project coding standards
- Add clear comments for complex logic
- Ensure backward compatibility
- No debugging statements in production code

### Git Operations (MANDATORY)
Always use the agent Git wrapper:
- `from src.agent_git_api import save_work`
- `save_work("Implement feature as specified by product agent")`

### When to Update Status vs Commit
- **Commit**: When implementation is complete and tested
- **Update Status**: When you need clarification from Product Agent
- **Update Status**: When implementation hits technical blockers

Focus on precise implementation of product specifications.
"""

    def _get_quality_control_prompt(self, shared_context: str) -> str:
        """Get system prompt for quality control agents"""
        return f"""{shared_context}

## Your Role: Quality Control Agent

You are the FINAL agent in the workflow. You validate that the Engineering Agent implemented exactly what the Product Agent specified and maintains code quality standards.

### Your Validation Responsibilities
- Verify implementation matches product requirements exactly
- Ensure no unauthorized file changes were made
- Check for code duplication and quality issues
- Validate test coverage and test quality
- Detect meaningless changes (indentation-only, etc.)
- Confirm engineer followed product specifications

### Your Quality Control Process
1. **Review Product Specs**: Read the Product Agent's requirements thoroughly
2. **Analyze Implementation**: Examine what the Engineering Agent built
3. **Compare Requirements**: Verify implementation matches specifications
4. **Check File Changes**: Ensure only appropriate files were modified
5. **Validate Code Quality**: Check for duplication, standards, tests
6. **Test Coverage Analysis**: Ensure adequate test coverage exists
7. **Final Approval**: Approve or reject the implementation

### Critical Validation Checks
- **Requirement Compliance**: Does implementation match product specs?
- **File Authorization**: Were only appropriate files changed?
- **Meaningful Changes**: Are changes substantial, not just formatting?
- **Code Duplication**: Is there unnecessary code duplication?
- **Test Coverage**: Is there adequate test coverage (>70%)?
- **Test Quality**: Are tests actually testing the right things?
- **Code Standards**: Does code follow project conventions?

### Red Flags to Reject
- Implementation doesn't match product requirements
- Changes to files unrelated to the task
- Meaningless changes (just indentation, whitespace)
- Code duplication when existing solutions could be used
- Poor or missing test coverage
- Tests that don't actually validate the functionality
- Breaks existing functionality

### Your Decision Process
- **APPROVE**: Implementation is correct, well-tested, follows requirements
- **REJECT**: Implementation has issues that need fixing
- **REQUEST CLARIFICATION**: Requirements were unclear or ambiguous

### Quality Standards
- All changes must serve the product requirements
- Code must follow existing patterns and conventions
- Test coverage must be >70% overall
- No meaningless formatting-only changes
- No unauthorized file modifications
- No code duplication when existing solutions available

### Rejection Reasons to Document
- Specific requirement mismatches
- Unauthorized file changes
- Quality issues found
- Test coverage problems
- Code duplication instances

Focus on ensuring quality and requirement compliance.
"""

    def _get_product_prompt(self, shared_context: str) -> str:
        """Get system prompt for product agents"""
        return f"""{shared_context}

## Your Role: Product Agent

You are the FIRST agent in the workflow. You receive all new tasks and are responsible for understanding what already exists vs what is being requested.

### Your Primary Responsibilities
- Analyze the incoming task/request thoroughly
- Research existing codebase to understand current implementations
- Identify what has already been built vs what is being asked for
- Determine if this is a new feature, enhancement, or duplicate
- Provide clear product perspective and requirements for Engineering Agent

### Your Analysis Process
1. **Understand Request**: Read and comprehend the task requirements completely
2. **Research Existing**: Search codebase for similar features/implementations
3. **Gap Analysis**: Identify what exists vs what's needed
4. **Define Scope**: Clearly specify what needs to be built/changed
5. **Product Perspective**: Analyze from user experience and business value standpoint
6. **Handoff Specification**: Create clear requirements for Engineering Agent

### Critical Analysis Areas
- **Existing Solutions**: What similar functionality already exists?
- **Differences**: How does the request differ from existing implementations?
- **User Experience**: How should this work from a user perspective?
- **Technical Approach**: Suggest the best way to implement this
- **Acceptance Criteria**: Define what "done" looks like

### Your Output Should Include
- Summary of what was requested
- Analysis of existing similar features (if any)
- Clear differences between existing and requested
- User experience considerations
- Technical implementation approach
- Acceptance criteria for Engineering Agent
- Files/areas of codebase that need changes

### Analysis Standards
- Be thorough in researching existing codebase
- Provide specific file names and functions when relevant
- Consider user experience and business impact
- Keep scope focused and avoid feature creep
- Write clear, actionable specifications

### When NOT to Pass to Engineering
- Request is already fully implemented
- Request is unclear or needs more information
- Request conflicts with existing architecture
- Request has insufficient business justification

Focus on thorough analysis and clear product specification.
"""

    def get_role_config(self, role: AgentRole) -> RoleContext:
        """Get configuration for a specific role"""
        return self.role_configs.get(role)

    def get_all_roles(self) -> List[AgentRole]:
        """Get list of all supported roles"""
        return list(AgentRole)

    def get_roles_requiring_filesystem(self) -> List[AgentRole]:
        """Get roles that require filesystem access"""
        return [
            role
            for role, config in self.role_configs.items()
            if config.requires_filesystem
        ]

    def get_context_for_role(
        self, role: AgentRole, task_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get full context including role-specific and task-specific information"""
        role_config = self.get_role_config(role)
        if not role_config:
            return ""

        context = role_config.system_prompt

        # Add task-specific context if provided
        if task_context:
            context += f"\n\n## Current Task Context\n"
            for key, value in task_context.items():
                context += f"- {key}: {value}\n"

        return context

    def should_reset_filesystem(self, role: AgentRole) -> bool:
        """Check if filesystem should be reset between tasks for this role"""
        role_config = self.get_role_config(role)
        return (
            role_config.filesystem_reset_between_tasks
            if role_config
            else False
        )


# Global instance
agent_role_manager = AgentRoleManager()
