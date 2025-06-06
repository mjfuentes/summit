#!/usr/bin/env python3

import os
import asyncio
import pytest
from anthropic import Anthropic

@pytest.mark.asyncio
async def test_summit_ai():
    """Test Summit's AI capabilities directly"""
    
    # Check if API key is set
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        return
    
    print(f"API key found: {api_key[:20]}...")
    
    # Test Claude API directly
    try:
        client = Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "You are Summit, an autonomous AI. Say hello and describe your purpose in one sentence."
                }
            ]
        )
        
        print("Summit AI Response:")
        print(message.content[0].text)
        print("\nSummit AI is working correctly.")
        
    except Exception as e:
        print(f"ERROR: Summit AI test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_summit_ai()) 