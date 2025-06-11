# GitHub CI/CD Integration for Summit

This document describes the GitHub CI/CD integration features added to Summit for real-time monitoring of task build status and workflow runs.

## Overview

The CI/CD integration provides comprehensive monitoring of GitHub Actions workflows, pull request status, and commit checks for autonomous tasks. This enables real-time visibility into the build and deployment pipeline directly from the Summit web interface.

## Features

### 1. Real-time CI/CD Status Monitoring
- **Workflow Run Tracking**: Monitor GitHub Actions workflow runs in real-time
- **Commit Status Checks**: Track status of individual commits and their associated checks
- **Pull Request Integration**: Monitor PR status, mergeability, and auto-merge progress
- **Multi-source Status**: Combines legacy status API and modern checks API for comprehensive coverage

### 2. Frontend Integration
- **Visual Status Indicators**: Color-coded status badges with emojis for quick recognition
- **Workflow Run Details**: Expandable workflow run information with links to GitHub
- **Real-time Updates**: Automatic refresh of CI/CD status with manual refresh option
- **PR Information**: Direct links to pull requests and commit details

### 3. API Endpoints

#### Task-specific CI/CD Endpoints
- `GET /api/tasks/{task_id}/ci-status` - Get current CI/CD status for a task
- `GET /api/tasks/{task_id}/workflow-runs` - Get workflow runs for a task
- `GET /api/tasks/{task_id}/pr-info` - Get pull request information for a task
- `POST /api/tasks/{task_id}/update-ci-info` - Manually refresh CI/CD information

#### Summary Endpoints
- `GET /api/ci-status/summary` - Get CI/CD status summary for all active tasks

## Database Schema

### New Task Fields
The `Task` model has been extended with CI/CD tracking fields:

```python
# CI/CD tracking fields
pr_number = Column(Integer)  # GitHub PR number
pr_url = Column(String(500))  # GitHub PR URL
commit_sha = Column(String(40))  # Git commit SHA
branch_name = Column(String(100))  # Feature branch name
ci_status = Column(String(20))  # CI/CD status: pending, success, failure, error
workflow_runs = Column(JSON, default=list)  # Store workflow run data
last_ci_check = Column(DateTime)  # Last time CI status was checked
```

## Implementation Details

### 1. GitHubCICDManager Class
Located in `src/github_cicd.py`, this class handles all GitHub API interactions:

- **Repository URL Parsing**: Supports both HTTPS and SSH GitHub URLs
- **API Authentication**: Uses GitHub token for authenticated requests
- **Rate Limiting**: Respects GitHub API rate limits
- **Error Handling**: Graceful degradation when GitHub API is unavailable

### 2. Status Combination Logic
The system combines multiple sources of CI/CD information:

- **Legacy Status API**: For older integrations and external status checks
- **Checks API**: For modern GitHub Actions and third-party checks
- **Workflow Runs API**: For detailed GitHub Actions information

### 3. Frontend Components
The web interface includes:

- **CI/CD Status Section**: Displays in task details when CI/CD data is available
- **Workflow Run List**: Shows recent workflow runs with status and links
- **Refresh Functionality**: Manual refresh button for real-time updates
- **Status Colors and Emojis**: Visual indicators for quick status recognition

## Usage Examples

### 1. Getting CI/CD Status for a Task
```python
from github_cicd import get_task_ci_status

task_data = {
    "repository_url": "https://github.com/owner/repo",
    "pr_number": 42,
    "commit_sha": "abc123def456"
}

ci_status = await get_task_ci_status(task_data)
print(f"CI Status: {ci_status['state']}")
```

### 2. Getting Workflow Runs
```python
from github_cicd import get_workflow_runs_for_task

workflow_runs = await get_workflow_runs_for_task(task_data)
for run in workflow_runs:
    print(f"{run['emoji']} {run['name']}: {run['conclusion']}")
```

### 3. Frontend Integration
The frontend automatically displays CI/CD information when available:

```javascript
// CI/CD status is automatically loaded when task has PR or CI data
if (task.pr_number || task.ci_status) {
    loadCICDInfo(task.task_id);
}
```

## Status Mapping

### CI/CD States
- **success**: All checks passed (green )
- **failure**: One or more checks failed (red )
- **pending**: Checks are running (yellow )
- **error**: System error or timeout (orange )
- **unknown**: No CI/CD information available (gray )

### Workflow Run Status
- **completed + success**: Green 
- **completed + failure**: Red 
- **completed + cancelled**: Gray 
- **in_progress**: Blue 
- **queued**: Yellow 

## Configuration

### Environment Variables
- `GITHUB_TOKEN`: GitHub personal access token for API access
- Required scopes: `repo`, `actions:read`, `checks:read`

### API Rate Limits
- GitHub API allows 5,000 requests per hour for authenticated users
- The system caches results and uses efficient polling to minimize API usage

## Testing

Comprehensive test suite in `tests/test_github_cicd.py` covers:

- **Unit Tests**: Individual component functionality
- **Integration Tests**: End-to-end workflow monitoring
- **Error Handling**: Network failures and API errors
- **Mock Testing**: GitHub API responses and edge cases

Run tests with:
```bash
python -m pytest tests/test_github_cicd.py -v
```

## Error Handling

The system gracefully handles various error conditions:

- **No GitHub Token**: Falls back to public API with limited functionality
- **Network Errors**: Returns cached data or unknown status
- **API Rate Limits**: Implements exponential backoff and caching
- **Invalid Repository URLs**: Clear error messages and validation

## Future Enhancements

Potential improvements for future versions:

1. **Webhook Integration**: Real-time updates via GitHub webhooks
2. **Custom Status Checks**: Support for custom CI/CD providers
3. **Historical Analytics**: Track CI/CD performance over time
4. **Notification System**: Alerts for failed builds or deployments
5. **Multi-repository Support**: Monitor multiple repositories simultaneously

## Security Considerations

- **Token Security**: GitHub tokens are stored securely and not logged
- **API Scope Limitation**: Uses minimal required scopes for GitHub access
- **Rate Limit Respect**: Implements proper rate limiting to avoid API abuse
- **Error Information**: Sensitive information is not exposed in error messages 