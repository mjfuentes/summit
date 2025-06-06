#!/usr/bin/env python3

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from knowledge_base import KnowledgeBase

def test_knowledge_base():
    """Test the knowledge base functionality"""
    
    print("Testing Summit Knowledge Base")
    print("=" * 35)
    
    # Use a test file to avoid interfering with real data
    test_file = "test_knowledge.json"
    
    try:
        # Initialize knowledge base
        kb = KnowledgeBase(test_file)
        
        print("Knowledge base initialized")
        
        # Test adding shared items
        item1 = kb.add_shared_item(
            "I noticed developers are struggling with async patterns lately",
            "observation",
            "From multiple conversations this week"
        )
        print(f"Added item 1: ID {item1['id']}")
        
        item2 = kb.add_shared_item(
            "There's an emerging trend in using AI for code reviews",
            "trend"
        )
        print(f"Added item 2: ID {item2['id']}")
        
        # Test getting summary
        summary = kb.get_knowledge_summary()
        print(f"Knowledge summary: {summary['total_shares']} shares across {len(summary['categories'])} categories")
        
        # Test recent shares
        recent = kb.get_recent_shares(5)
        print(f"Recent shares: {len(recent)} items")
        
        # Test search
        search_results = kb.search_knowledge("async")
        print(f"Search for 'async': {len(search_results)} results")
        
        # Test categories
        print(f"Categories: {list(summary['categories'].keys())}")
        
        print("\nKnowledge base test PASSED")
        
    except Exception as e:
        print(f"ERROR: Knowledge base test failed: {e}")
        
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_knowledge_base() 