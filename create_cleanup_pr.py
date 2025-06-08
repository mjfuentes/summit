#!/usr/bin/env python3
"""
Create PR for summit interface cleanup
"""

import os
import sys
from datetime import UTC, datetime

sys.path.append("src")
from agent_git_api import create_pr

# Get PR template
template = os.environ.get(
    "PR_TEMPLATE",
    """
# {title}

## Summary
{summary}

## Changes Made
{changes}

## Files Modified
{files_modified}

## Quality Assurance
{quality_assurance}

## Review Process
{review_process}

## Branch Information
- **Branch**: {branch}
- **Commit SHA**: {commit_sha}
- **Timestamp**: {timestamp}
""",
)

# Create the PR
create_pr(
    commit_message="Clean up summit interface and consolidate functionality",
    pr_title="Cleanup: Remove summit_interface.py and consolidate functionality in autonomous_server.py",
    pr_body=template.format(
        title="Summit Interface Cleanup and Consolidation",
        branch="feature/cleanup-summit-interface",
        commit_sha="latest",
        timestamp=datetime.now(UTC).isoformat(),
        summary="Removed redundant summit_interface.py files and consolidated all functionality into autonomous_server.py. Added GET_TASKS template response functionality to autonomous server with proper structured action detection.",
        changes="- Deleted web/summit_interface.py (redundant interface file)\n- Deleted web/summit_interface_backup.py (backup file)\n- Deleted web/start_summit_interface.py (startup script)\n- Enhanced autonomous_server.py with template response functionality\n- Added structured response format to system prompt\n- Implemented GET_TASKS action detection and template generation\n- Added debug logging for task query detection",
        files_modified="- `web/summit_interface.py` (deleted)\n- `web/summit_interface_backup.py` (deleted)\n- `web/start_summit_interface.py` (deleted)\n- `web/autonomous_server.py` (enhanced with template responses)",
        quality_assurance="All functionality from summit_interface.py has been successfully transferred to autonomous_server.py. Template response system tested and working correctly with debug logs showing proper detection and generation. Server starts and responds correctly to task queries.",
        review_process="This PR consolidates the codebase by removing redundant files and ensuring all functionality is available in the single autonomous_server.py. The template response feature for GET_TASKS actions is now fully functional.",
    ),
)
