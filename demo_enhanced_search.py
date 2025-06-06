#!/usr/bin/env python3
"""
Demo of Enhanced Semantic Search in Summit
Showcases the new search capabilities and analytics
"""

import asyncio
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from summit import handle_call_tool

async def demo_enhanced_search():
    """Comprehensive demo of enhanced semantic search features"""
    
    print(" Summit Enhanced Semantic Search Demo")
    print("=" * 60)
    
    # Step 1: Share diverse content to build knowledge base
    print("\n Step 1: Building Knowledge Base with Diverse Content")
    print("-" * 50)
    
    demo_content = [
        {
            "content": "Machine learning models require high-quality, diverse training datasets to avoid bias and improve generalization",
            "category": "insight",
            "context": "AI/ML best practices"
        },
        {
            "content": "Debugging asynchronous JavaScript code can be challenging due to callback hell and promise chains",
            "category": "challenge", 
            "context": "Frontend development"
        },
        {
            "content": "Code reviews should prioritize architectural decisions and business logic over minor style issues",
            "category": "best_practice",
            "context": "Software engineering process"
        },
        {
            "content": "AI-powered debugging tools are becoming more sophisticated at identifying logical errors and suggesting fixes",
            "category": "observation",
            "context": "Developer tools evolution"
        },
        {
            "content": "Agile development methodologies improve team collaboration and project adaptability",
            "category": "best_practice",
            "context": "Project management"
        },
        {
            "content": "Database query optimization requires understanding execution plans and indexing strategies",
            "category": "insight",
            "context": "Backend performance"
        },
        {
            "content": "API design patterns significantly impact long-term maintainability and developer experience",
            "category": "insight",
            "context": "Software architecture"
        }
    ]
    
    for item in demo_content:
        result = await handle_call_tool("summit_share", item)
        print(f" Shared: {item['category']} - {item['content'][:50]}...")
    
    # Step 2: Demonstrate enhanced search capabilities
    print(f"\n Step 2: Enhanced Search Demonstrations")
    print("-" * 50)
    
    search_queries = [
        {
            "query": "How can AI help with debugging code?",
            "description": "Question-type query (should find AI debugging content)"
        },
        {
            "query": "best practices for software development",
            "description": "Search-type query with category matching"
        },
        {
            "query": "machine learning training challenges",
            "description": "Complex multi-term query"
        },
        {
            "query": "API design optimization",
            "description": "Architecture-focused query"
        }
    ]
    
    for query_info in search_queries:
        print(f"\n Query: '{query_info['query']}'")
        print(f"   Type: {query_info['description']}")
        
        result = await handle_call_tool("summit_learn", {
            "query": query_info['query'],
            "max_results": 3
        })
        
        response = result[0].text
        print("   Results:")
        # Show first 300 characters to keep demo readable
        print("   " + response[:400] + "..." if len(response) > 400 else "   " + response)
    
    # Step 3: Show analytics capabilities
    print(f"\n Step 3: Search Analytics & Insights")
    print("-" * 50)
    
    # Get search analytics
    analytics_result = await handle_call_tool("summit_analytics", {
        "include_suggestions": True
    })
    print(" Search Analytics:")
    print(analytics_result[0].text[:500] + "..." if len(analytics_result[0].text) > 500 else analytics_result[0].text)
    
    # Get content insights
    print(f"\n Content Insights:")
    insights_result = await handle_call_tool("summit_insights", {})
    print(insights_result[0].text[:500] + "..." if len(insights_result[0].text) > 500 else insights_result[0].text)
    
    # Step 4: Demonstrate query suggestions and edge cases
    print(f"\n Step 4: Advanced Features")
    print("-" * 50)
    
    # Try a query that might not find results
    print(" Testing query with no direct matches:")
    no_match_result = await handle_call_tool("summit_learn", {
        "query": "blockchain cryptocurrency trading",
        "max_results": 2
    })
    print("   " + no_match_result[0].text[:300] + "...")
    
    # Try focused search
    print(f"\n Testing focused search with patterns analysis:")
    focused_result = await handle_call_tool("summit_learn", {
        "query": "development practices",
        "focus": "patterns",
        "max_results": 2
    })
    print("   " + focused_result[0].text[:300] + "...")
    
    # Step 5: Show status and summary
    print(f"\n Step 5: System Status")
    print("-" * 50)
    
    status_result = await handle_call_tool("summit_status", {})
    print(" Summit Status:")
    print("   " + status_result[0].text[:400] + "..." if len(status_result[0].text) > 400 else "   " + status_result[0].text)
    
    print(f"\n Demo Complete!")
    print("=" * 60)
    print("Enhanced semantic search features demonstrated:")
    print(" Enhanced query preprocessing with intent detection")
    print(" Improved keyword search with weighted scoring")
    print(" Advanced result ranking and relevance scoring")
    print(" Search analytics and performance tracking")
    print(" Content insights and knowledge gap analysis")
    print(" Query suggestions for better search experience")
    print(" Hybrid search combining semantic and keyword approaches")
    print(f"\n Note: Currently running in enhanced keyword mode.")
    print("   Set OPENAI_API_KEY for full semantic vector search capabilities.")

if __name__ == "__main__":
    asyncio.run(demo_enhanced_search()) 