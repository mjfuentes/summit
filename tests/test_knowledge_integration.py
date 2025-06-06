#!/usr/bin/env python3

import asyncio
import os
from summit import handle_call_tool, knowledge_base

async def test_knowledge_integration():
    """Test Summit's knowledge integration in responses"""
    
    print("Testing Summit Knowledge Integration")
    print("=" * 45)
    
    # Set API key
    os.environ["ANTHROPIC_API_KEY"] = "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"
    
    try:
        # Clear any existing knowledge for clean test
        print("Starting with fresh knowledge base")
        
        # Step 1: Share some AI development insights
        print("\nStep 1: Sharing AI development insights")
        
        await handle_call_tool("summit_share", {
            "content": "Developers are finding that AI pair programming works best when they stay in the driver's seat",
            "category": "observation"
        })
        
        await handle_call_tool("summit_share", {
            "content": "The most successful AI projects start with clear human-defined goals and constraints",
            "category": "insight"
        })
        
        # Step 2: Ask for advice on AI development (should use accumulated knowledge)
        print("\nStep 2: Asking for AI development advice")
        
        result = await handle_call_tool("summit_advice", {
            "question": "What are the best practices for AI pair programming?",
            "context": "I'm starting a new project with AI assistance"
        })
        
        response = result[0].text
        print("Response (first 300 chars):")
        print(response[:300] + "..." if len(response) > 300 else response)
        
        # Step 3: Share related experience (should connect to previous shares)
        print("\nStep 3: Sharing related experience")
        
        share_result = await handle_call_tool("summit_share", {
            "content": "I've noticed that AI is most helpful when it suggests solutions but humans make the final decisions",
            "category": "observation"
        })
        
        share_response = share_result[0].text
        print("Share response (first 300 chars):")
        print(share_response[:300] + "..." if len(share_response) > 300 else share_response)
        
        # Step 4: Check knowledge base status
        print("\nStep 4: Knowledge base status")
        summary = knowledge_base.get_knowledge_summary()
        print(f"Total shares: {summary['total_shares']}")
        print(f"Categories: {summary['categories']}")
        
        print("\nKnowledge integration test COMPLETED")
        
    except Exception as e:
        print(f"ERROR: Knowledge integration test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_knowledge_integration()) 