#!/usr/bin/env python3

import asyncio
import os
import pytest
from summit import handle_call_tool, knowledge_base

@pytest.mark.asyncio
async def test_vector_knowledge():
    """Test Summit's vector knowledge base and semantic search"""
    
    print("Testing Summit Vector Knowledge Base")
    print("=" * 50)
    
    # Set API keys
    os.environ["ANTHROPIC_API_KEY"] = "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"
    # Note: You'll need to set OPENAI_API_KEY for embeddings
    
    try:
        print("Step 1: Sharing diverse experiences")
        
        # Share some diverse AI/development experiences
        experiences = [
            ("AI debugging tools are becoming more sophisticated and can now identify complex logical errors", "observation"),
            ("Machine learning models perform better when trained on diverse, high-quality datasets", "insight"),
            ("Developers are struggling with async programming patterns in JavaScript", "challenge"),
            ("Code reviews are more effective when they focus on architecture rather than syntax", "best_practice"),
            ("Natural language processing has revolutionized how we interact with software", "trend")
        ]
        
        for content, category in experiences:
            await handle_call_tool("summit_share", {
                "content": content,
                "category": category
            })
            print(f"Shared: {category}")
        
        print(f"\nStep 2: Testing semantic search")
        
        # Test queries that should find semantically similar content
        test_queries = [
            "How can AI help with finding bugs in code?",
            "What makes machine learning models work better?", 
            "JavaScript async challenges",
            "Effective code review strategies"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            
            result = await handle_call_tool("summit_learn", {
                "query": query
            })
            
            response = result[0].text
            print("Response (first 200 chars):")
            print(response[:200] + "..." if len(response) > 200 else response)
        
        print(f"\nStep 3: Knowledge base summary")
        summary = knowledge_base.get_knowledge_summary()
        print(f"Total shares: {summary['total_shares']}")
        print(f"Total embeddings: {summary['total_embeddings']}")
        print(f"Embedding model: {summary['embedding_model']}")
        print(f"Categories: {summary['categories']}")
        
        print("\nVector knowledge base test COMPLETED")
        
    except Exception as e:
        print(f"ERROR: Vector knowledge test failed: {e}")
        if "OPENAI_API_KEY" not in os.environ:
            print("NOTE: Set OPENAI_API_KEY environment variable for full vector functionality")

if __name__ == "__main__":
    asyncio.run(test_vector_knowledge()) 