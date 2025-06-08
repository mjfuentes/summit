#!/bin/bash
set -e

echo " Setting up OpenCode with your RunPod endpoint..."
echo "=================================================="

# Check if OpenCode is installed
if ! command -v opencode &> /dev/null; then
    echo " Installing OpenCode..."
    curl -fsSL https://raw.githubusercontent.com/opencode-ai/opencode/main/install | bash
    
    # Add to PATH if needed
    if ! command -v opencode &> /dev/null; then
        echo "Adding OpenCode to PATH..."
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        export PATH="$HOME/.local/bin:$PATH"
    fi
else
    echo " OpenCode is already installed"
fi

# Create OpenCode config directory
echo " Creating OpenCode configuration..."
mkdir -p ~/.config/opencode

# Copy the configuration file
cp opencode_config.json ~/.config/opencode/config.json

echo " OpenCode configuration created at ~/.config/opencode/config.json"

# Set environment variables
echo " Setting up environment variables..."

# Add to bashrc/zshrc
if [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_RC="$HOME/.zshrc"
else
    SHELL_RC="$HOME/.bashrc"
fi

# Add environment variables if not already present
if ! grep -q "RUNPOD_ENDPOINT_URL" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# OpenCode + RunPod Configuration" >> "$SHELL_RC"
    echo 'export RUNPOD_ENDPOINT_URL="https://api.runpod.ai/v2/26xsjcfv6hlyqe/run"' >> "$SHELL_RC"
    echo 'export RUNPOD_API_KEY="***REMOVED***"' >> "$SHELL_RC"
    echo 'export USE_OPENCODE=true' >> "$SHELL_RC"
    echo " Environment variables added to $SHELL_RC"
else
    echo " Environment variables already configured"
fi

# Set for current session
export RUNPOD_ENDPOINT_URL="https://api.runpod.ai/v2/26xsjcfv6hlyqe/run"
export RUNPOD_API_KEY="***REMOVED***"
export USE_OPENCODE=true

echo ""
echo " Setup complete! Here's how to use it:"
echo "========================================"
echo ""
echo "1. Test the connection:"
echo "   python -c \"import asyncio; from src.runpod_opencode_client import test_runpod_connection; asyncio.run(test_runpod_connection())\""
echo ""
echo "2. Use OpenCode directly:"
echo "   opencode \"Analyze this codebase and suggest improvements\""
echo ""
echo "3. Use with Summit web interface:"
echo "   python start_web.py"
echo "   # Then use the chat interface - it will automatically use OpenCode + RunPod"
echo ""
echo "4. Example development tasks:"
echo "   opencode \"Add error handling to the authentication module\""
echo "   opencode \"Fix the failing tests in tests/test_auth.py\""
echo "   opencode \"Implement JWT token refresh functionality\""
echo ""
echo " Cost savings: ~90% compared to Claude Code!"
echo " Your model will scale to zero when not in use"
echo ""
echo " Restart your terminal or run: source $SHELL_RC" 