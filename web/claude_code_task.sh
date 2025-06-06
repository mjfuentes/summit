#!/bin/bash

# Claude Code Task Runner
# Starts Claude Code with full terminal access and task context

echo "[$(date '+%H:%M:%S')] Summit AI Claude Code Environment Starting..."

# Get environment variables
TASK_DESCRIPTION="${TASK_DESCRIPTION:-No task specified}"
SAVE_WORD="${SAVE_WORD:-SUMMIT_TASK_COMPLETE}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
REPOSITORY_URL="${REPOSITORY_URL:-}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

echo "[$(date '+%H:%M:%S')] Task: $TASK_DESCRIPTION"
echo "[$(date '+%H:%M:%S')] Completion signal: [REDACTED_FOR_MONITORING]"

# Setup Git authentication
echo "[$(date '+%H:%M:%S')] Configuring Git authentication..."

# Configure Git user (required for commits)
git config --global user.name "Summit AI"
git config --global user.email "summit@ai.dev"

# Setup Git credential helper for token authentication
if [ ! -z "$GITHUB_TOKEN" ]; then
    echo "[$(date '+%H:%M:%S')] Setting up GitHub token authentication..."
    
    # Configure Git to use token for HTTPS authentication
    git config --global credential.helper store
    
    # Create credentials file for automatic authentication
    mkdir -p ~/.git-credentials
    echo "https://$GITHUB_TOKEN@github.com" > ~/.git-credentials
    git config --global credential.helper "store --file ~/.git-credentials"
    
    # Also set up git config for token-based authentication
    git config --global url."https://$GITHUB_TOKEN@github.com/".insteadOf "https://github.com/"
    
    echo "[$(date '+%H:%M:%S')] GitHub authentication configured"
fi

# Setup Claude Code configuration and permissions
echo "[$(date '+%H:%M:%S')] Configuring Claude Code permissions..."

# Create .claude directory
mkdir -p ~/.claude

# Create Claude Code configuration with proper permissions
cat > ~/.claude/config.json << EOF
{
  "anthropic_api_key": "$ANTHROPIC_API_KEY",
  "auto_approve": {
    "file_edits": false,
    "command_execution": true,
    "git_operations": true
  },
  "allowed_commands": [
    "git",
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
    "curl",
    "wget",
    "ls",
    "cat",
    "grep",
    "find",
    "cd",
    "mkdir",
    "touch",
    "rm",
    "cp",
    "mv",
    "echo",
    "which",
    "chmod",
    "make",
    "cargo",
    "go",
    "java",
    "javac"
  ],
  "restricted_commands": [
    "sudo",
    "su",
    "rm -rf /",
    "dd",
    "mkfs",
    "fdisk",
    "mount",
    "umount"
  ],
  "git_config": {
    "user_name": "Summit AI Agent",
    "user_email": "summit-ai@autonomous.dev",
    "auto_commit": true,
    "auto_push": true
  },
  "workspace_permissions": {
    "allow_file_creation": true,
    "allow_file_modification": true,
    "allow_file_deletion": true,
    "allow_directory_creation": true
  }
}
EOF

echo "[$(date '+%H:%M:%S')] Claude Code configuration created"

# Test Claude Code authentication
if [ ! -z "$ANTHROPIC_API_KEY" ]; then
    echo "[$(date '+%H:%M:%S')] Testing Claude Code authentication..."
    export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
    echo "[$(date '+%H:%M:%S')] Authentication configured"
else
    echo "[$(date '+%H:%M:%S')] WARNING: No Anthropic API key provided"
fi

# Clone repository if provided
if [ ! -z "$REPOSITORY_URL" ]; then
    echo "[$(date '+%H:%M:%S')] Cloning repository: $REPOSITORY_URL"
    
    # Clone with proper authentication
    if git clone "$REPOSITORY_URL" project; then
        cd project
        echo "[$(date '+%H:%M:%S')] Repository cloned successfully"
        
        # Configure repository-specific settings
        if [ ! -z "$GITHUB_TOKEN" ] && [[ "$REPOSITORY_URL" == *"github.com"* ]]; then
            # Set the remote URL to use token authentication for pushes
            REPO_NAME=$(basename "$REPOSITORY_URL" .git)
            REPO_OWNER=$(echo "$REPOSITORY_URL" | sed 's/.*github\.com[/:]\([^/]*\)\/.*/\1/')
            git remote set-url origin "https://$GITHUB_TOKEN@github.com/$REPO_OWNER/$REPO_NAME.git"
            echo "[$(date '+%H:%M:%S')] Repository configured for authenticated pushes"
        fi
        
        # Test Git authentication
        echo "[$(date '+%H:%M:%S')] Testing Git authentication..."
        if git ls-remote origin > /dev/null 2>&1; then
            echo "[$(date '+%H:%M:%S')] Git authentication successful"
        else
            echo "[$(date '+%H:%M:%S')] Warning: Git authentication test failed"
        fi
    else
        echo "[$(date '+%H:%M:%S')] Failed to clone repository, continuing with empty workspace"
    fi
fi

# Create task context file for Claude Code
cat > task_context.md << EOF
# Autonomous Development Task

## Task Description
$TASK_DESCRIPTION

## Instructions for Claude Code
You are Summit AI working autonomously to complete this coding task. You have:

1. **Full terminal access** - Use the integrated terminal for any commands
2. **Development environment** - All major languages and frameworks are pre-installed
3. **Git integration** - Repository is cloned and ready for commits
4. **File system access** - Create, modify, and organize files as needed

## Your Process Should Be:
1. **Analyze** the task requirements thoroughly
2. **Plan** your approach and architecture
3. **Implement** the solution with clean, well-documented code
4. **Test** your implementation to ensure it works
5. **Document** your solution appropriately
6. **Commit and push** changes if working with a repository

## Completion Signal
When you have fully completed the task, add this exact text to a file or output:
**COMPLETION_WORD_HERE**

(The completion signal has been configured for you)

## Available Tools
- All programming languages (Python, JavaScript, TypeScript, etc.)
- Frameworks (React, Vue, Angular, Django, Flask, FastAPI, etc.)
- Databases (SQLite, PostgreSQL setup available)
- Testing frameworks (pytest, jest, etc.)
- Code quality tools (black, eslint, prettier, etc.)

## Repository Information
EOF

if [ ! -z "$REPOSITORY_URL" ]; then
    echo "- Repository: $REPOSITORY_URL" >> task_context.md
    echo "- Current directory: $(pwd)" >> task_context.md
    echo "- Files available: $(find . -type f -name '*.py' -o -name '*.js' -o -name '*.html' -o -name '*.md' -o -name '*.json' | head -10)" >> task_context.md
else
    echo "- Working in empty workspace" >> task_context.md
    echo "- Current directory: $(pwd)" >> task_context.md
fi

cat >> task_context.md << EOF

## Getting Started
Open this file in Claude Code and start working on the task. Use the terminal for any commands you need to run.

When completely finished, create a completion file:
echo "$SAVE_WORD" > completion.txt

This will signal that your task is complete.
EOF

echo "[$(date '+%H:%M:%S')] Task context created in task_context.md"

# Start web-based terminal for Claude Code access
echo "[$(date '+%H:%M:%S')] Starting web terminal with Claude Code environment..."

# Create a welcome script
cat > welcome.sh << 'WELCOME'
#!/bin/bash
clear
echo "======================================================"
echo "  Summit AI - Claude Code Development Environment"  
echo "======================================================"
echo ""
echo "Task: $TASK_DESCRIPTION"
echo "Completion Signal: [CONFIGURED]"
echo ""
echo "Available Commands:"
echo "  claude          - Start Claude Code interactive session"
echo "  claude commit   - Commit changes and push to repository"
echo "  claude 'task'   - Run specific coding task"
echo "  git status      - Check repository status"
echo "  git log --oneline -5 - Show recent commits"
echo "  npm test        - Run tests"
echo "  pytest          - Run Python tests"
echo "  echo '$SAVE_WORD' > completion.txt - Signal task completion"
echo "  exit            - Exit the session"
echo ""
echo "Claude Code Permissions:"
echo "   File editing (with approval)"
echo "   Command execution (auto-approved)"
echo "   Git operations (auto-approved)"
echo "   Repository push access (configured)"
echo ""
echo "Repository Information:"
if [ ! -z "$REPOSITORY_URL" ]; then
    echo "  Repository: $REPOSITORY_URL"
    echo "  Working directory: $(pwd)"
    echo "  Files available:"
    find . -type f -name '*.py' -o -name '*.js' -o -name '*.html' -o -name '*.md' -o -name '*.json' | head -10
else
    echo "  Working in clean workspace: $(pwd)"
fi
echo ""
echo "======================================================"
echo "Ready for development! Type 'claude' to start coding."
echo "When task is complete, write completion signal to completion.txt file."
echo "======================================================"
echo ""

# Setup Claude Code authentication
if [ ! -z "$ANTHROPIC_API_KEY" ]; then
    echo "Setting up Claude Code authentication..."
    # Note: Claude Code authentication may require interactive setup
    # For now, we'll rely on the API key being available
fi

# Start an interactive bash session
exec bash
WELCOME

chmod +x welcome.sh

# Start ttyd web terminal server
echo "[$(date '+%H:%M:%S')] Starting web terminal on port 7681..."
ttyd -p 7681 -W /workspace ./welcome.sh &

# Also log terminal access info
echo "[$(date '+%H:%M:%S')] Web terminal available at http://localhost:7681"
echo "[$(date '+%H:%M:%S')] Claude Code CLI ready for interactive use"

# Keep the container running and monitor for completion signal
echo "[$(date '+%H:%M:%S')] Monitoring for completion signal: $SAVE_WORD"

# Create a monitoring loop
while true; do
    sleep 10
    
    # Check if completion signal appears in output files (excluding task_context.md)
    if find /workspace -name "*.log" -o -name "output.txt" -o -name "completion.txt" | xargs grep -l "$SAVE_WORD" 2>/dev/null | head -1; then
        echo "[$(date '+%H:%M:%S')] Completion signal detected!"
        echo "$SAVE_WORD"
        break
    fi
    
    # Also check terminal logs but exclude initial setup files
    if find /workspace -name "terminal.log" -o -name "claude_output.log" | xargs grep -l "$SAVE_WORD" 2>/dev/null | head -1; then
        echo "[$(date '+%H:%M:%S')] Completion signal detected!"
        echo "$SAVE_WORD"
        break
    fi
    
    # Check if container should exit (optional timeout)
    if [ ! -z "$TIMEOUT_MINUTES" ]; then
        if [ $(date +%s) -gt $(($(date -d "$START_TIME" +%s) + $TIMEOUT_MINUTES * 60)) ]; then
            echo "[$(date '+%H:%M:%S')] Timeout reached"
            break
        fi
    fi
done

echo "[$(date '+%H:%M:%S')] Claude Code session ended" 