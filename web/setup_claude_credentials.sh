#!/bin/bash

# Summit AI - Claude Code Credentials Setup
# This script helps configure credentials and permissions for Claude Code

echo "======================================================"
echo "  Summit AI - Claude Code Credentials Setup"
echo "======================================================"
echo ""

# Check for required credentials
MISSING_CREDS=false

echo "Checking required credentials..."
echo ""

# Check Anthropic API Key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo " ANTHROPIC_API_KEY not set"
    echo "   Get your API key from: https://console.anthropic.com/"
    echo "   Then run: export ANTHROPIC_API_KEY='your-key-here'"
    MISSING_CREDS=true
else
    echo " ANTHROPIC_API_KEY configured"
fi

# Check GitHub Token (optional but recommended)
if [ -z "$GITHUB_TOKEN" ]; then
    echo "  GITHUB_TOKEN not set (optional for public repos)"
    echo "   For private repos and push access:"
    echo "   1. Go to: https://github.com/settings/tokens"
    echo "   2. Create token with 'repo' and 'workflow' permissions"
    echo "   3. Run: export GITHUB_TOKEN='your-token-here'"
else
    echo " GITHUB_TOKEN configured"
fi

echo ""

if [ "$MISSING_CREDS" = true ]; then
    echo " Missing required credentials. Please set up credentials and try again."
    echo ""
    echo "Quick setup commands:"
    echo "export ANTHROPIC_API_KEY='your-anthropic-key'"
    echo "export GITHUB_TOKEN='your-github-token'"
    echo ""
    exit 1
fi

echo " All credentials configured!"
echo ""

# Create Claude Code configuration
echo "Setting up Claude Code permissions..."

# Create .claude directory if it doesn't exist
mkdir -p ~/.claude

# Create Claude Code configuration file
cat > ~/.claude/config.json << EOF
{
  "anthropic_api_key": "$ANTHROPIC_API_KEY",
  "auto_approve": {
    "file_edits": false,
    "command_execution": false,
    "git_operations": false
  },
  "allowed_commands": [
    "git",
    "npm",
    "pip",
    "python",
    "node",
    "pytest",
    "black",
    "flake8",
    "mypy",
    "eslint",
    "prettier",
    "docker",
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
    "mv"
  ],
  "restricted_commands": [
    "sudo",
    "su",
    "chmod +x",
    "rm -rf /",
    "dd",
    "mkfs",
    "fdisk"
  ],
  "git_config": {
    "user_name": "Summit AI Agent",
    "user_email": "summit-ai@autonomous.dev",
    "auto_commit": false,
    "auto_push": false
  }
}
EOF

echo " Claude Code configuration created at ~/.claude/config.json"
echo ""

# Test Claude Code installation
echo "Testing Claude Code installation..."
if command -v claude &> /dev/null; then
    echo " Claude Code CLI installed"
    claude --version
else
    echo " Claude Code CLI not found"
    echo "   Install with: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

echo ""
echo "======================================================"
echo "  Setup Complete!"
echo "======================================================"
echo ""
echo "Claude Code is now configured with:"
echo " Anthropic API authentication"
echo " GitHub token for repository access" 
echo " Command permissions and restrictions"
echo " Git configuration for commits"
echo ""
echo "Security settings:"
echo "• File edits require approval"
echo "• Command execution requires approval"
echo "• Git operations require approval"
echo "• Restricted dangerous commands"
echo ""
echo "To start Summit's autonomous interface:"
echo "python start_web.py"
echo "" 