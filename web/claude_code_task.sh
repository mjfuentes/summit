#!/bin/bash
set -e

# Prevent modifications to production knowledge base during autonomous tasks
export SUMMIT_READONLY_MODE=true

# Store start time
START_TIME=$(date)
echo "[$(date '+%H:%M:%S')] Starting Claude AI autonomous development..."

# Get task parameters from environment
TASK_DESCRIPTION="${TASK_DESCRIPTION:-Complete the assigned development task}"
SAVE_WORD="${SAVE_WORD:-SUMMIT_TASK_COMPLETE}"
TIMEOUT_MINUTES="${TIMEOUT_MINUTES:-}"
REPOSITORY_URL="${REPOSITORY_URL:-}"

# Display startup info
echo "======================================================"
echo "  Summit AI - Autonomous Development Session"
echo "======================================================"
echo "Task: $TASK_DESCRIPTION"
echo "Completion Signal: $SAVE_WORD"
echo "Repository: ${REPOSITORY_URL:-'Working in clean workspace'}"
echo "Working Directory: $(pwd)"
echo "======================================================"

# Create task context for Claude
cat > task_context.md << EOF
# Autonomous Development Task

**Task:** $TASK_DESCRIPTION
**Completion Signal:** $SAVE_WORD
**Start Time:** $(date)
**Working Directory:** $(pwd)

## Repository Info
- URL: ${REPOSITORY_URL:-'N/A'}
- Branch: $(git branch --show-current 2>/dev/null || echo 'N/A')
- Modified files: $(git status --porcelain 2>/dev/null | wc -l)

## Current Files
$(find . -type f -name '*.py' -o -name '*.js' -o -name '*.html' -o -name '*.md' -o -name '*.json' -o -name '*.yml' -o -name '*.yaml' | head -20)
EOF

echo "[$(date '+%H:%M:%S')] Task context created"

# Load environment variables (including API key)
if [ -f setup_env.sh ]; then
    echo "[$(date '+%H:%M:%S')] Loading environment variables..."
    source setup_env.sh
fi

# Setup real git repository if specified
if [ ! -z "$REPOSITORY_URL" ]; then
    echo "[$(date '+%H:%M:%S')] Setting up git repository..."
    
    # Clone the repository to a subdirectory
    REPO_DIR="/workspace/repo"
    if [ -d "$REPO_DIR" ]; then
        rm -rf "$REPO_DIR"
    fi
    
    # Set up authentication if GitHub token is provided
    if [ ! -z "$GITHUB_TOKEN" ]; then
        echo "[$(date '+%H:%M:%S')] Using GitHub token for authentication"
        
        # Set up git credential store
        git config --global credential.helper store
        git config --global user.name "Claude AI Assistant"
        git config --global user.email "claude.ai@anthropic.com"
        
        # Create credentials file with token
        mkdir -p ~/.config/git
        echo "https://mjfuentes:$GITHUB_TOKEN@github.com" > ~/.git-credentials
        chmod 600 ~/.git-credentials
        
        # Try different authentication methods
        echo "[$(date '+%H:%M:%S')] Attempting clone with stored credentials..."
        git clone "$REPOSITORY_URL" "$REPO_DIR" || {
            echo "[$(date '+%H:%M:%S')] Stored credentials failed, trying token in URL..."
            AUTH_URL=$(echo "$REPOSITORY_URL" | sed "s|https://github.com/|https://$GITHUB_TOKEN@github.com/|")
            git clone "$AUTH_URL" "$REPO_DIR" || {
                echo "[$(date '+%H:%M:%S')] All authentication methods failed, trying public clone..."
                git clone "$REPOSITORY_URL" "$REPO_DIR"
            }
        }
    else
        echo "[$(date '+%H:%M:%S')] No GitHub token provided, attempting public clone"
        git clone "$REPOSITORY_URL" "$REPO_DIR"
    fi
    cd "$REPO_DIR"
    
    # Get the target branch name from environment or use main by default
    TARGET_BRANCH="${TARGET_BRANCH:-main}"
    export TARGET_BRANCH="$TARGET_BRANCH"
    
    # Check if target branch exists on remote, if not create it (if not main)
    if [ "$TARGET_BRANCH" = "main" ]; then
        echo "[$(date '+%H:%M:%S')] Checking out main branch"
        git checkout main
        git pull origin main
    elif git ls-remote --heads origin "$TARGET_BRANCH" | grep -q "$TARGET_BRANCH"; then
        echo "[$(date '+%H:%M:%S')] Checking out existing branch: $TARGET_BRANCH"
        git checkout "$TARGET_BRANCH"
        git pull origin "$TARGET_BRANCH"
    else
        echo "[$(date '+%H:%M:%S')] Creating new branch: $TARGET_BRANCH"
        git checkout -b "$TARGET_BRANCH"
        # Try to push the new branch, but don't fail if it doesn't work initially
        git push -u origin "$TARGET_BRANCH" || echo "[$(date '+%H:%M:%S')] Initial branch push failed, will retry after commits"
    fi
    
    # Ensure remote origin is properly configured
    git remote set-url origin "$REPOSITORY_URL"
    
    echo "[$(date '+%H:%M:%S')] Working in git repository: $(pwd)"
    echo "[$(date '+%H:%M:%S')] Current branch: $(git branch --show-current)"
    echo "[$(date '+%H:%M:%S')] Remote URL: $(git remote get-url origin)"
    echo "[$(date '+%H:%M:%S')] Target branch for pushing: $TARGET_BRANCH"
else
    echo "[$(date '+%H:%M:%S')] Working in clean workspace (no repository specified)"
    # Initialize a basic git repo for testing
    git init
    git config user.name "Claude AI Assistant"
    git config user.email "claude.ai@anthropic.com"
    export TARGET_BRANCH="main"
fi

# Configure git for Claude
git config user.name "Claude AI Assistant" 2>/dev/null || true
git config user.email "claude.ai@anthropic.com" 2>/dev/null || true

# Create the Claude Code interaction script outside the repository
mkdir -p /tmp/claude_tools
cat > /tmp/claude_tools/interact_with_claude.py << 'CLAUDE_SCRIPT'
#!/usr/bin/env python3
"""
Claude Code CLI interaction script for autonomous development
"""
import os
import sys
import subprocess
import time
import tempfile
from datetime import datetime

def log(message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")

def run_command(cmd, timeout=None):
    """Run a command and return its output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"

def main():
    task_description = os.environ.get('TASK_DESCRIPTION', 'Complete the assigned development task')
    save_word = os.environ.get('SAVE_WORD', 'SUMMIT_TASK_COMPLETE')
    
    log(f"Starting Claude Code interaction for task: {task_description}")
    
    # Check if Claude Code CLI is available
    log("Checking Claude Code CLI availability...")
    
    # Debug environment variables
    log("Environment check:")
    log(f"  USER: {os.environ.get('USER', 'unknown')}")
    log(f"  HOME: {os.environ.get('HOME', 'unknown')}")
    log(f"  PATH: {os.environ.get('PATH', 'unknown')[:100]}...")
    
    # Check if API key is available
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        log("ERROR: ANTHROPIC_API_KEY not found in environment")
        log("Available env vars:")
        for key in sorted(os.environ.keys()):
            if 'API' in key or 'ANTHROPIC' in key:
                log(f"  {key}: {os.environ[key][:20]}...")
        return
    
    log(f"API key found: {api_key[:15]}...")
    log(f"API key length: {len(api_key)} characters")
    
    code, stdout, stderr = run_command("which claude || command -v claude")
    if code != 0:
        log("Claude Code CLI not found. Installing...")
        code, stdout, stderr = run_command("npm install -g @anthropic-ai/claude-code", timeout=300)
        if code != 0:
            log(f"Failed to install Claude Code CLI: {stderr}")
            return
    
    log("Claude Code CLI is available")
    
    # Initialize Claude Code if needed
    log("Initializing Claude Code session...")
    
    # Test Claude Code access
    code, stdout, stderr = run_command("claude --version")
    if code != 0:
        log(f"Claude Code CLI error: {stderr}")
        log(f"STDOUT: {stdout}")
        return
    
    log(f"Using Claude Code version: {stdout.strip()}")
    
    # Test API authentication
    log("Testing Claude Code authentication...")
    code, stdout, stderr = run_command("claude --help", timeout=10)
    if code != 0:
        log(f"Claude Code help command failed: {stderr}")
    else:
        log("Claude Code help command successful")
        
    # Check workspace setup
    log(f"Current working directory: {os.getcwd()}")
    log(f"Workspace contents: {os.listdir('.')}")
    
    # Test basic file operations
    try:
        with open('test_write.txt', 'w') as f:
            f.write('test')
        os.remove('test_write.txt')
        log("File write test: successful")
    except Exception as e:
        log(f"File write test failed: {e}")
    
    # Create the prompt with coding rules
    coding_prompt = f"""
You are an AI coding assistant working on a development task in a Git repository.

**CRITICAL: EVERY TASK MUST END WITH GIT COMMIT AND PUSH**
NO TASK IS COMPLETE WITHOUT PUSHING TO GIT - THIS IS MANDATORY FOR ALL TASKS

**TASK:** {task_description}

**MANDATORY GIT WORKFLOW - ALWAYS REQUIRED:**
REGARDLESS of what the task asks for, you MUST ALWAYS finish by committing and pushing:
1. Complete the requested task (create files, modify code, etc.)
2. git add . (stage ALL changes)
3. git pull --rebase (sync with remote, resolve conflicts if any)
4. git commit -m "Your single-line commit message"
5. git push origin {os.environ.get('TARGET_BRANCH', 'main')} (push to specified branch)

**ABSOLUTE REQUIREMENTS:**
- NEVER consider a task complete without git commit + push
- ALWAYS push to git even for simple file creation tasks
- ALWAYS push to git even for documentation tasks
- ALWAYS push to git even for configuration tasks
- Git workflow is MANDATORY for EVERY task, no exceptions

**CONTAINER ISOLATION REQUIREMENTS:**
- ALL file operations must happen inside the container at /workspace/repo
- NO local host files should ever be modified outside the container
- Knowledge base updates must be contained within the repository structure
- All code changes must be committed to the git repository for persistence

**CODING STANDARDS:**
- Commit messages must be single line only (no multi-line commits)
- Never use git commit --no-verify - all commits must pass pre-commit hooks
- Maintain >70% test coverage on changes when applicable
- Use formal test suites (pytest) - no ad-hoc testing with sleep/curl
- Check how similar use cases are implemented in the repository and follow those patterns
- Only add comments that explain WHY, not WHAT the code does
- No emojis in documentation - use clear, professional text
- Keep documentation concise and focused

**WORKSPACE:**
You are working in: {os.getcwd()}

**REMEMBER: NO TASK IS COMPLETE WITHOUT GIT COMMIT AND PUSH**
Analyze the repository, complete the task, then ALWAYS commit and push your changes.
When you're completely finished with everything, you can simply end your session.
"""
    
    # Create a temporary file for the prompt
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(coding_prompt)
        prompt_file = f.name
    
    try:
        log("Sending task to Claude Code...")
        
        # Write prompt to temporary file and use shell redirection
        log("Executing Claude Code command...")
        
        # Write the full prompt to the temp file we created earlier
        with open(prompt_file, 'w') as f:
            f.write(coding_prompt)
        
        # First try a simple test to see if Claude Code responds at all
        log("Testing basic Claude Code interaction...")
        test_result = run_command('echo "Hello" | claude -p "Just say hello back"', timeout=30)
        if test_result[0] == 0:
            log("Basic Claude Code test successful")
            log(f"Test output: {test_result[1][:200]}")
        else:
            log(f"Basic Claude Code test failed: {test_result[2]}")
            log("Continuing with full task anyway...")
        
        # Use Claude Code's built-in autonomous mode (Safe YOLO + Headless)
        log("Running Claude Code in autonomous mode...")
        log(f"Task length: {len(coding_prompt)} characters")
        log("Using --dangerously-skip-permissions flag (safe as non-root user)")
        log(f"Command: claude -p --dangerously-skip-permissions [task]")
        
        # Run Claude Code with headless mode (-p) and dangerous permissions
        # (now safe since we're running as non-root claude user)
        process = subprocess.Popen(
            ['claude', '-p', '--dangerously-skip-permissions', coding_prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True
        )
        
        log("Claude Code is processing the task autonomously...")
        log("Monitoring Claude Code output in real-time...")
        
        # Set timeout (default 8 minutes if not specified)
        timeout_seconds = int(os.environ.get('TIMEOUT_MINUTES', 8)) * 60
        start_time = time.time()
        
        # Monitor Claude Code output in real-time
        return_code = 0
        output_lines = []
        error_lines = []
        last_output_time = start_time
        
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Check timeout
            if elapsed > timeout_seconds:
                log(f"Claude Code execution timed out after {timeout_seconds/60:.1f} minutes")
                process.terminate()
                return_code = -1
                break
                
            # Check if process ended
            if process.poll() is not None:
                return_code = process.returncode
                log(f"Claude Code process ended with return code: {return_code}")
                break
            
            # Show progress every 30 seconds
            if int(elapsed) % 30 == 0 and elapsed > 30:
                log(f"Claude Code still running... {elapsed:.0f}s elapsed")
                
            # Read stdout
            try:
                import select
                ready, _, _ = select.select([process.stdout, process.stderr], [], [], 1)
                
                if process.stdout in ready:
                    output = process.stdout.readline()
                    if output:
                        clean_output = output.strip()
                        if clean_output:
                            log(f"Claude STDOUT: {clean_output}")
                            output_lines.append(clean_output)
                            last_output_time = current_time
                            
                if process.stderr in ready:
                    error = process.stderr.readline()
                    if error:
                        clean_error = error.strip()
                        if clean_error:
                            log(f"Claude STDERR: {clean_error}")
                            error_lines.append(clean_error)
                            
            except ImportError:
                # Fallback for systems without select
                try:
                    output = process.stdout.readline()
                    if output:
                        clean_output = output.strip()
                        if clean_output:
                            log(f"Claude: {clean_output}")
                            output_lines.append(clean_output)
                            last_output_time = current_time
                except:
                    pass
                time.sleep(1)
            
            # Check if Claude Code seems stuck (no output for 2 minutes)
            if current_time - last_output_time > 120:
                log("Warning: No output from Claude Code for 2 minutes - may be stuck")
                log("Attempting to check Claude Code process status...")
                
                # Try to get more info about what Claude Code is doing
                try:
                    ps_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
                    if 'claude' in ps_result.stdout:
                        log("Claude Code process still found in process list")
                    else:
                        log("Claude Code process not found in process list")
                except:
                    log("Could not check process status")
                
                last_output_time = current_time  # Reset to avoid spam
        
        # Process the results
        log(f"Claude Code process finished with return code: {return_code}")
        log(f"Total output lines captured: {len(output_lines)}")
        log(f"Total error lines captured: {len(error_lines)}")
        
        if output_lines:
            log("Final output lines:")
            for line in output_lines[-5:]:  # Show last 5 lines
                log(f"  OUT: {line}")
                
        if error_lines:
            log("Error lines:")
            for line in error_lines[-5:]:  # Show last 5 error lines
                log(f"  ERR: {line}")
        
        # Check workspace after Claude Code execution
        log("Checking workspace after Claude Code execution:")
        try:
            files = os.listdir('.')
            log(f"Files created: {files}")
            
            # Look for our target file
            if 'test_autonomous_claude.py' in files:
                log("Target file 'test_autonomous_claude.py' was created!")
                with open('test_autonomous_claude.py', 'r') as f:
                    content = f.read()
                    log(f"File content preview: {content[:200]}...")
            else:
                log("Target file 'test_autonomous_claude.py' was NOT created")
                
        except Exception as e:
            log(f"Error checking workspace: {e}")
        
        if return_code == 0:
            log("Claude Code completed successfully")
        else:
            log(f"Claude Code exited with error code: {return_code}")
            log("Task finished with errors")
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(prompt_file)
        except:
            pass

if __name__ == '__main__':
    main()
CLAUDE_SCRIPT

chmod +x /tmp/claude_tools/interact_with_claude.py

echo "[$(date '+%H:%M:%S')] Running Claude Code interaction..."
python3 /tmp/claude_tools/interact_with_claude.py

# Start web terminal for monitoring
cat > welcome.sh << 'WELCOME'
#!/bin/bash
clear
echo "======================================================"
echo "  Summit AI - Development Environment"  
echo "======================================================"
echo ""
echo "Task: $TASK_DESCRIPTION" 
echo "Status: Ready for Claude development"
echo ""
echo "Commands:"
echo "  git log --oneline -5  - Recent commits"
echo "  git status            - Repository status"
echo "  cat completion.txt    - Completion signal"
echo "  ls -la                - List files"
echo "  cat task_context.md   - Task details"
echo ""
echo "======================================================"
echo "Development environment ready!"
echo "======================================================"
exec bash
WELCOME

chmod +x welcome.sh

# Start web terminal
ttyd -p 7681 -i 0.0.0.0 ./welcome.sh &
TTYD_PID=$!

echo "[$(date '+%H:%M:%S')] Web terminal started on port 7681"

# Claude Code has finished - the session will now end naturally
echo "[$(date '+%H:%M:%S')] Claude Code execution completed"
echo "[$(date '+%H:%M:%S')] Session ended" 