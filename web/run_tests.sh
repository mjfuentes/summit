#!/bin/bash

# Summit Autonomous System Test Runner
# Simple wrapper for testing the Claude Code autonomous system

set -e

echo " Summit Autonomous Claude Code System - Test Runner"
echo "======================================================"

# Check if we're in the right directory
if [ ! -f "autonomous_server.py" ]; then
    echo " Error: Must run from the web/ directory"
    echo "Current directory: $(pwd)"
    echo "Expected files: autonomous_server.py, test_e2e_autonomous_system.py"
    exit 1
fi

# Check if Python requests is available
python3 -c "import requests" 2>/dev/null || {
    echo " Error: Python 'requests' library not found"
    echo "Please install it with: pip install requests"
    exit 1
}

# Parse command line arguments
case "${1:-full}" in
    "quick" | "--quick" | "-q")
        echo " Running quick API test (no Docker required)..."
        python3 test_e2e_autonomous_system.py --quick
        ;;
    "debug" | "--debug" | "-d")
        echo " Running debug test (Docker, no git)..."
        python3 test_e2e_autonomous_system.py --debug
        ;;
    "full" | "--full" | "-f")
        echo " Running full test with Docker containers..."
        python3 test_e2e_autonomous_system.py
        ;;
    "help" | "--help" | "-h")
        echo ""
        echo "Usage: $0 [quick|debug|full|help]"
        echo ""
        echo "Options:"
        echo "  quick    - Test only the API endpoints (no Docker)"
        echo "  debug    - Test Docker and Claude Code (no git workflow)"
        echo "  full     - Complete test including Docker and git (default)"
        echo "  help     - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0           # Run full test"
        echo "  $0 quick     # Run quick test"
        echo "  $0 debug     # Run debug test"
        echo "  $0 full      # Run full test"
        echo ""
        exit 0
        ;;
    *)
        echo " Unknown option: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac 