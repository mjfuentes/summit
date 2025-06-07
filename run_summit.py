#!/usr/bin/env python3
"""
Summit - Living AI Repository
Main entry point for the Summit MCP server
"""

from summit import main
import asyncio
import os
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


# Import and run Summit

if __name__ == "__main__":
    print("Summit AI Advisor is starting...")
    asyncio.run(main())
