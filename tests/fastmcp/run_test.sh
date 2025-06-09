#!/bin/bash
# Script to run the FastMCP 2.0 test

set -e

echo "===== Testing FastMCP 2.0 Integration ====="

# Navigate to the project root
cd "$(dirname "$0")/../.."

# Set up Python path
export PYTHONPATH="$PYTHONPATH:$(pwd)"

# Run the test
python tests/fastmcp/fastmcp_only_test.py

echo "===== FastMCP 2.0 Test Complete =====" 