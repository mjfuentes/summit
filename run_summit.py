#!/usr/bin/env python3
"""
Summit - Living AI Repository
Main entry point for the Summit MCP server
"""

import os
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import asyncio

# Import and run Summit
from summit import main

if __name__ == "__main__":
    print("Summit AI Advisor is starting...")
    asyncio.run(main())
