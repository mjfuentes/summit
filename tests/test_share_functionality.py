#!/usr/bin/env python3

import asyncio
import os
import sys
import pytest
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from summit import handle_call_tool
from knowledge_base import KnowledgeBase

@pytest.mark.asyncio
async def test_summit_share():
    """Test Summit's share functionality"""
    
    print("Testing Summit Share Functionality")
    print("=" * 40)
    
    # Create temporary knowledge base for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_kb_path = temp_file.name
    
    # Import summit module and temporarily replace its knowledge_base
    import summit
    original_kb = summit.knowledge_base
    summit.knowledge_base = KnowledgeBase(temp_kb_path)
    
    try:
        # Set API key for AI responses
        os.environ["ANTHROPIC_API_KEY"] = "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"
        # Test 1: Share an observation
        print("Test 1: Sharing an observation")
        
        result1 = await handle_call_tool("summit_share", {
            "content": "I've noticed that developers are increasingly using AI for debugging rather than just code generation",
            "category": "observation", 
            "context": "Based on conversations this week"
        })
        
        response1 = result1[0].text
        print("Response received (first 200 chars):")
        print(response1[:200] + "..." if len(response1) > 200 else response1)
        
        # Test 2: Share an insight
        print("\nTest 2: Sharing an insight")
        
        result2 = await handle_call_tool("summit_share", {
            "content": "The most effective AI collaborations happen when humans focus on high-level strategy while AI handles implementation details",
            "category": "insight"
        })
        
        response2 = result2[0].text
        print("Response received (first 200 chars):")
        print(response2[:200] + "..." if len(response2) > 200 else response2)
        
        # Test 3: Check knowledge base state
        print("\nTest 3: Checking knowledge base")
        summary = summit.knowledge_base.get_knowledge_summary()
        print(f"Total shares: {summary['total_shares']}")
        print(f"Categories: {summary['categories']}")
        
        print("\nSummit Share functionality test COMPLETED")
        
    except Exception as e:
        print(f"ERROR: Summit Share test failed: {e}")
    finally:
        # Restore original knowledge base and clean up temp file
        summit.knowledge_base = original_kb
        try:
            os.unlink(temp_kb_path)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_summit_share()) 