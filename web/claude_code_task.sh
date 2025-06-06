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
echo "[$(date '+%H:%M:%S')] Completion signal: $SAVE_WORD"

# Clone repository if provided
if [ ! -z "$REPOSITORY_URL" ]; then
    echo "[$(date '+%H:%M:%S')] Cloning repository: $REPOSITORY_URL"
    if [ ! -z "$GITHUB_TOKEN" ] && [[ "$REPOSITORY_URL" == *"github.com"* ]]; then
        # Use token authentication for private repos
        AUTH_URL=$(echo "$REPOSITORY_URL" | sed "s|https://github.com/|https://$GITHUB_TOKEN@github.com/|")
        git clone "$AUTH_URL" project
    else
        git clone "$REPOSITORY_URL" project
    fi
    
    if [ $? -eq 0 ]; then
        cd project
        echo "[$(date '+%H:%M:%S')] Repository cloned successfully"
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
**$SAVE_WORD**

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

Remember to output "$SAVE_WORD" when you're completely finished!
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
echo "Completion Signal: $SAVE_WORD"
echo ""
echo "Available Commands:"
echo "  claude          - Start Claude Code interactive session"
echo "  claude commit   - Commit changes"
echo "  claude 'task'   - Run specific coding task"
echo "  git status      - Check repository status"
echo "  npm test        - Run tests"
echo "  exit            - Exit the session"
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
echo "Remember to output '$SAVE_WORD' when task is complete."
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
    
    # Check if completion signal appears in any log files or terminal output
    if find /workspace -name "*.log" -o -name "*.txt" -o -name "*.md" -exec grep -l "$SAVE_WORD" {} \; 2>/dev/null | head -1; then
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