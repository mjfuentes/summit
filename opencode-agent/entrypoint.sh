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

# Check for Google Application Credentials (optional for workload identity)
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo " Error: Credentials file not found at $GOOGLE_APPLICATION_CREDENTIALS"
    exit 1
fi

# Test authentication (works with both service account files and workload identity)
echo " Testing Google Cloud authentication..."
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
    echo " Active account: $ACTIVE_ACCOUNT"
elif [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo " Using service account credentials: $GOOGLE_APPLICATION_CREDENTIALS"
else
    echo " Using workload identity (metadata service)"
fi

echo " Environment configured:"
echo "   Project: $VERTEXAI_PROJECT"
echo "   Location: $VERTEXAI_LOCATION"
echo "   Auth method: $([ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && echo "Service Account" || echo "Workload Identity")"

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

# If no command provided, start interactive mode
if [ $# -eq 0 ]; then
    echo " Starting OpenCode in interactive mode..."
    echo "   Use 'opencode -h' for help"
    echo "   Available agents: coder, reviewer, debugger"
    exec /bin/bash
fi

# Execute the provided command
echo " Executing: $@"
exec "$@" 