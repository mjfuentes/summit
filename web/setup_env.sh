#!/bin/bash
# Environment setup for Summit AI autonomous development

# Set Anthropic API Key
export ANTHROPIC_API_KEY="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"

# Set Database URL for local development (SQLite - no server required)
export DATABASE_URL="sqlite+aiosqlite:///../data/summit_local.db"

echo "Environment loaded: ANTHROPIC_API_KEY and DATABASE_URL set" 