#!/bin/bash

# Summit AI Web Server Startup Script
echo "Starting Summit AI Web Server..."
echo "=================================================="

# Kill any existing processes on port 8000
echo "Checking for existing servers on port 8000..."
EXISTING_PIDS=$(lsof -ti:8000 2>/dev/null)
if [ ! -z "$EXISTING_PIDS" ]; then
    echo "Killing existing server processes: $EXISTING_PIDS"
    echo "$EXISTING_PIDS" | xargs kill 2>/dev/null
    sleep 1
    echo "Cleared port 8000"
fi

# Check if we're in the right directory
if [ ! -f "server.py" ]; then
    echo "ERROR: server.py not found in current directory"
    echo "   Make sure you're running this from the Summit web directory"
    exit 1
fi

echo "Found server.py"

# Check if dependencies are installed
echo "Checking dependencies..."
python3 -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Missing dependencies. Installing FastAPI and Uvicorn..."
    pip install fastapi uvicorn
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies"
        echo "   Please run: pip install fastapi uvicorn"
        exit 1
    fi
fi

echo "Dependencies are installed"
echo ""
echo "Summit AI Web Interface"
echo "   Interface: http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs" 
echo "   Health:    http://localhost:8000/health"
echo ""
echo "Starting server... (Press Ctrl+C to stop)"
echo ""

# Start server (already in web directory)
python3 standalone_server.py 