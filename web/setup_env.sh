#!/bin/bash
# Environment setup for Summit AI autonomous development

# Set Anthropic API Key
export ANTHROPIC_API_KEY="***REMOVED***"

# Set Database URL for local development (SQLite - no server required)
export DATABASE_URL="sqlite+aiosqlite:///../data/summit_local.db"

echo "Environment loaded: ANTHROPIC_API_KEY and DATABASE_URL set" 