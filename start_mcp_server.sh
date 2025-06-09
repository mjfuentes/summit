#!/bin/bash
# Script to start the Summit FastMCP server with the specified transport

# Default values
PORT=8080
TRANSPORT="sse"
HOST="0.0.0.0"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --port)
      PORT="$2"
      shift 2
      ;;
    --transport)
      TRANSPORT="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --port PORT        Port to listen on (default: 8080)"
      echo "  --transport TYPE   Transport type: stdio, sse, streamable-http (default: sse)"
      echo "  --host HOST        Host to bind to (default: 0.0.0.0)"
      echo "  --help             Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Set environment variables
export MCP_TRANSPORT="$TRANSPORT"
export PORT="$PORT"
export HOST="$HOST"

echo "Starting Summit FastMCP server..."
echo "Transport: $TRANSPORT"
if [ "$TRANSPORT" != "stdio" ]; then
  echo "Host: $HOST"
  echo "Port: $PORT"
fi

# Start the server
python -m src.fastmcp_server 