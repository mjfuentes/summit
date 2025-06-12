# GitHub CI/CD Monitor

A real-time monitoring tool for GitHub Actions workflows with continuous terminal output. This tool provides live status updates, workflow monitoring, and comprehensive CI/CD visibility for the Summit project.

## Features

### Real-time Monitoring
- **Continuous Updates**: Refreshes every 30 seconds (configurable)
- **Live Status**: Shows running, queued, and completed workflows
- **Color-coded Output**: Visual indicators for quick status recognition
- **Auto-detection**: Automatically detects current repository

### Comprehensive Visibility
- **Workflow Summary**: Overview of all workflows with latest status
- **Active Runs**: Currently running or queued workflows
- **Recent Failures**: Last 5 failed workflow runs with timing
- **Detailed History**: Recent workflow runs with commit info and duration

### Flexible Usage
- **Continuous Mode**: Real-time monitoring with screen refresh
- **Single Check**: One-time status check
- **Simple Mode**: Minimal output for quick checks
- **Custom Repository**: Monitor any GitHub repository

## Installation

The tool is located at `scripts/github_cicd_monitor.py` and requires:

```bash
pip install requests
```

Make sure you have a GitHub token set up for authenticated API access:

```bash
export GITHUB_TOKEN="your_github_token_here"
```

### Shortcut Script

For convenience, a shortcut script is provided at `scripts/cicd` that wraps the main tool:

```bash
# Make sure it's executable (should already be)
chmod +x scripts/cicd

# Use the shortcut instead of the full python command
./scripts/cicd --once
```

The shortcut accepts all the same arguments as the main script but with less typing.

## Usage

### Basic Usage

```bash
# Monitor current repository continuously
python scripts/github_cicd_monitor.py
# OR use the shortcut
./scripts/cicd

# Single status check
python scripts/github_cicd_monitor.py --once
# OR
./scripts/cicd --once

# Monitor specific repository
python scripts/github_cicd_monitor.py --repo owner/repo
# OR
./scripts/cicd --repo owner/repo

# Custom refresh interval (60 seconds)
python scripts/github_cicd_monitor.py --interval 60
# OR
./scripts/cicd --interval 60

# Simple output without details
python scripts/github_cicd_monitor.py --simple
# OR
./scripts/cicd --simple
```

### Quick Reference

```bash
# Most common usage patterns
./scripts/cicd                    # Start continuous monitoring
./scripts/cicd --once             # Quick status check
./scripts/cicd --once --simple    # Minimal status check
./scripts/cicd --interval 15      # Fast refresh (15 seconds)
./scripts/cicd --interval 120     # Slow refresh (2 minutes)
```

### Advanced Usage

```bash
# Monitor with custom token
python scripts/github_cicd_monitor.py --token ghp_your_token

# Quick check of another repository
python scripts/github_cicd_monitor.py --repo microsoft/vscode --once --simple

# Long-term monitoring with slower refresh
python scripts/github_cicd_monitor.py --interval 120
```

## Output Sections

### Header
- Repository name and current branch
- Last update timestamp
- GitHub token status (authenticated vs anonymous)

### Workflow Summary
- All workflows with their latest run status
- Duration of latest run
- Visual status indicators:
  -  (Green) - Success
  -  (Red) - Failure
  -  (Blue) - Running
  -  (Yellow) - Queued
  -  (Yellow) - Cancelled
  - ? (Purple) - Unknown

### Active Runs
- Currently running or queued workflows
- Branch and duration information
- Real-time status updates

### Recent Failures
- Last 5 failed workflow runs
- Time since failure
- Commit and branch information

### Recent Workflow Runs
- Detailed view of recent runs (last 8-10)
- Run number, workflow name, and status
- Branch, commit SHA, and trigger event
- Duration and start time

### Footer
- Control information (refresh interval, exit instructions)
- API rate limit status

## Status Indicators

| Symbol | Color | Meaning |
|--------|-------|---------|
|  | Green | Completed successfully |
|  | Red | Failed |
|  | Blue | Currently running |
|  | Yellow | Queued |
|  | Yellow | Cancelled |
| ? | Purple/White | Unknown status |

## Command Line Options

```
usage: github_cicd_monitor.py [-h] [--repo REPO] [--token TOKEN] 
                              [--interval INTERVAL] [--once] [--simple]

GitHub CI/CD Continuous Monitor

optional arguments:
  -h, --help           show this help message and exit
  --repo REPO          Repository in format 'owner/repo' (auto-detected if not specified)
  --token TOKEN        GitHub token (or set GITHUB_TOKEN env var)
  --interval INTERVAL  Refresh interval in seconds (default: 30)
  --once               Run once instead of continuous monitoring
  --simple             Simple output without detailed sections
```

## Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token for authenticated API access
  - **Recommended**: Provides higher rate limits (5,000 requests/hour vs 60/hour)
  - **Scopes needed**: `repo`, `actions:read`

## Examples

### Development Workflow Monitoring

Monitor your development workflow while working:

```bash
# Start continuous monitoring
python scripts/github_cicd_monitor.py

# In another terminal, make changes and push
git add .
git commit -m "Update feature"
git push

# Watch the CI/CD status update in real-time
```

### Quick Status Check

```bash
# Quick check before leaving for the day
python scripts/github_cicd_monitor.py --once --simple
```

### Monitor Specific Workflows

```bash
# Monitor a specific repository
python scripts/github_cicd_monitor.py --repo kubernetes/kubernetes --once

# Monitor with faster refresh for active development
python scripts/github_cicd_monitor.py --interval 15
```

### Integration with Other Tools

```bash
# Use in scripts or automation
if python scripts/github_cicd_monitor.py --once --simple | grep -q ""; then
    echo "There are failed workflows!"
fi
```

## Troubleshooting

### Common Issues

**"Could not detect repository"**
- Make sure you're in a git repository
- Or specify the repository with `--repo owner/repo`

**"API rate limit or authentication issue"**
- Set up a GitHub token: `export GITHUB_TOKEN="your_token"`
- Check token permissions (needs `repo` and `actions:read` scopes)

**"No workflows found"**
- Repository might not have GitHub Actions workflows
- Check if `.github/workflows/` directory exists

**Network timeouts**
- Check internet connection
- GitHub API might be experiencing issues

### Rate Limits

- **With Token**: 5,000 requests per hour
- **Without Token**: 60 requests per hour
- **Recommendation**: Always use a token for continuous monitoring

### Performance Tips

- Use `--simple` mode for faster updates
- Increase `--interval` for less frequent API calls
- Use `--once` for scripting and automation

## Integration with Summit Workflow

This tool integrates seamlessly with Summit's development workflow:

1. **Pre-commit**: Check status before making changes
2. **Post-push**: Monitor CI/CD progress after pushing
3. **PR Review**: Monitor workflow status during code review
4. **Deployment**: Watch deployment pipelines in real-time

### Recommended Workflow

```bash
# 1. Check current status
python scripts/github_cicd_monitor.py --once

# 2. Make changes and commit
# ... development work ...

# 3. Start monitoring before push
python scripts/github_cicd_monitor.py &
MONITOR_PID=$!

# 4. Push changes
git push

# 5. Watch CI/CD progress
# (monitor runs automatically)

# 6. Stop monitoring when done
kill $MONITOR_PID
```

## Technical Details

### API Usage
- Uses GitHub REST API v4
- Efficient caching to minimize API calls
- Graceful error handling and retry logic

### Terminal Features
- ANSI color codes for cross-platform compatibility
- Screen clearing for continuous updates
- Keyboard interrupt handling (Ctrl+C)

### Data Sources
- GitHub Actions workflows API
- Workflow runs API
- Repository information API
- Git repository detection

## Future Enhancements

Potential improvements for future versions:

1. **Webhook Integration**: Real-time updates via GitHub webhooks
2. **Notification System**: Desktop/email notifications for status changes
3. **Historical Analytics**: Track CI/CD performance over time
4. **Custom Filters**: Filter by workflow, branch, or status
5. **Export Options**: Save status reports to files
6. **Multi-repository**: Monitor multiple repositories simultaneously 