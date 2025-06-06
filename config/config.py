#!/usr/bin/env python3

import os

# API Configuration
ANTHROPIC_API_KEY = "***REMOVED***"
OPENAI_API_KEY = "***REMOVED***"

# Summit Configuration
SUMMIT_CONFIG = {
    "daily_budget": 10.0,
    "hourly_budget": 2.0,
    "max_recursion_depth": 3,
    "embedding_model": "text-embedding-3-small",
    "chat_model": "claude-sonnet-4-20250514"
}

def setup_environment():
    """Set up environment variables from config"""
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY 