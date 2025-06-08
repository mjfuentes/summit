#!/usr/bin/env python3
"""
Create PR for frontend validation infrastructure with Render.com previews
"""

from agent_git_api import create_pr
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, "src")


def main():
    print("Creating PR for frontend validation infrastructure...")

    # Create a comprehensive PR description
    pr_description = """# Frontend Validation Infrastructure with Render.com Previews

**Branch:** main → feature/frontend-validation
**Created:** {timestamp}

## Summary

Implemented comprehensive frontend validation infrastructure using Render.com's preview feature to automatically detect and prevent JavaScript errors in pull requests. This system addresses the critical frontend issues like `tasks.filter is not a function` errors by testing changes in isolated preview environments before they reach production.

## Key Components Added

### 1. GitHub Actions Workflow (`.github/workflows/frontend-validation.yml`)
- **Automatic PR Labeling**: Adds `render-preview` label and `[render preview]` to PR titles
- **Preview Environment Setup**: Waits for Render.com to create preview environments
- **Comprehensive Testing**: Uses Playwright to test frontend functionality
- **Automated Reporting**: Comments test results directly on PRs
- **Environment Cleanup**: Removes labels and preview markers after testing

### 2. Frontend Error Fixes (`templates/index.html`)
- **API Response Handling**: Fixed `loadTasks()` to handle both array and object responses
- **Failed Tasks Loading**: Updated `loadFailedTasks()` to properly parse API responses
- **Backward Compatibility**: Maintains compatibility with existing API formats
- **Error Prevention**: Prevents `tasks.filter is not a function` JavaScript errors

### 3. Render.com Configuration (`render.yaml`)
- **Preview Environments**: Enables automatic preview creation for PRs
- **Isolated Testing**: Separate preview service with isolated database
- **Environment Variables**: Proper configuration for preview vs production
- **Auto-cleanup**: Previews expire automatically after testing

### 4. Setup and Validation (`scripts/setup_frontend_validation.py`)
- **Requirements Check**: Validates all required secrets are configured
- **Configuration Validation**: Ensures render.yaml is properly set up
- **API Testing**: Tests local endpoints for correct response format
- **Setup Instructions**: Provides clear next steps for implementation

## Frontend Tests Performed

The validation system runs comprehensive tests on every PR:

-  **Page Load Validation**: Ensures pages load without JavaScript errors
-  **API Format Testing**: Validates API endpoints return expected data structures
-  **Form Functionality**: Tests task creation and form interactions
-  **Chat System**: Validates chat functionality works without errors
-  **Voice Input**: Tests voice input button functionality
-  **Error Detection**: Specifically checks for known error patterns

## Workflow Process

1. **PR Creation** → Workflow automatically adds `render-preview` label
2. **Render.com** → Creates isolated preview environment with PR changes
3. **Automated Testing** → Playwright runs comprehensive frontend validation
4. **Result Reporting** → Test results posted as PR comment with pass/fail status
5. **Environment Cleanup** → Preview environment cleaned up automatically

## Benefits

- **Early Error Detection**: Catches frontend issues before production deployment
- **Automated Quality Gates**: Prevents merging PRs with frontend errors
- **Developer Feedback**: Immediate feedback on frontend changes
- **Production Stability**: Ensures main branch always has working frontend
- **Cost Effective**: Uses Render.com's built-in preview feature efficiently

## Integration with Existing Systems

- **Maintains Compatibility**: Works with existing Summit development workflow
- **Quality Standards**: Follows Summit's professional development standards
- **Security**: No hardcoded secrets, uses GitHub repository secrets
- **Monitoring**: Integrates with existing CI/CD monitoring

This infrastructure ensures that frontend errors like the JavaScript issues encountered are caught and fixed before reaching production, maintaining Summit's high quality standards while enabling rapid development.

## Required Setup

To use this system, ensure these GitHub repository secrets are configured:
- `RENDER_API_KEY`: Render.com API key for preview management
- `RENDER_SERVICE_ID`: Service ID for the main Summit application
- `ANTHROPIC_API_KEY`: For AI functionality in preview environments
- `GITHUB_TOKEN`: For PR management and API access

The system is designed to work seamlessly with Render.com's existing auto-deployment features while adding comprehensive frontend validation capabilities.
""".format(
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

    # Create the PR
    result = create_pr(
        "Add frontend validation infrastructure with Render.com previews",
        "Feature: Frontend Validation with Render.com Previews",
        pr_description,
    )

    if result:
        print("Pull request created successfully!")
    else:
        print("Failed to create pull request")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
