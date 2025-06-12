#!/bin/bash
set -e

echo " Starting OpenCode Agent with Vertex AI"

# Check for required environment variables
if [ -z "$VERTEXAI_PROJECT" ]; then
    echo " Error: VERTEXAI_PROJECT environment variable is required"
    exit 1
fi

if [ -z "$VERTEXAI_LOCATION" ]; then
    echo " Error: VERTEXAI_LOCATION environment variable is required"
    exit 1
fi

# Check for Google Application Credentials
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo " Error: GOOGLE_APPLICATION_CREDENTIALS environment variable is required"
    echo "   This should point to a mounted service account JSON file"
    exit 1
fi

if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo " Error: Credentials file not found at $GOOGLE_APPLICATION_CREDENTIALS"
    exit 1
fi

echo " Environment configured:"
echo "   Project: $VERTEXAI_PROJECT"
echo "   Location: $VERTEXAI_LOCATION"
echo "   Credentials: $GOOGLE_APPLICATION_CREDENTIALS"

# Verify OpenCode installation
if [ ! -f "/root/.opencode/bin/opencode" ]; then
    echo " Error: OpenCode binary not found"
    exit 1
fi

echo " OpenCode binary found"

# Verify config file
if [ ! -f "/root/.config/opencode/config.json" ]; then
    echo " Error: OpenCode config not found"
    exit 1
fi

echo " OpenCode configuration loaded"
echo " Config contents:"
cat /root/.config/opencode/config.json

# If no command provided, start automated task processing
if [ $# -eq 0 ]; then
    echo " Starting OpenCode Agent in automated mode..."
    echo "   Available agents: coder, reviewer, debugger"
    echo "   Connecting to Summit MCP server..."
    
    # Run initial registration and then start task processing loop
    while true; do
        echo " $(date): Starting task processing cycle..."
        
        # Try to register and get tasks
        /root/.opencode/bin/opencode -p "Please register yourself with the Summit platform using summit_register_agent with role 'coder', then check for available tasks using summit_get_next_task. If you get a task, work on it and complete it using summit_complete_task. If no tasks are available, just report the status." -f json || echo " Task cycle completed with errors"
        
        echo " Waiting 30 seconds before next cycle..."
        sleep 30
    done
fi

# Execute the provided command
echo " Executing: $@"
exec "$@"