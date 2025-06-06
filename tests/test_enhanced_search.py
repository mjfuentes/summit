#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from vector_knowledge_base import VectorKnowledgeBase
import tempfile
import json

def test_enhanced_semantic_search():
    """Test the enhanced semantic search functionality"""
    
    print("Testing Enhanced Semantic Search")
    print("=" * 50)
    
    # Create temporary files for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as data_file:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.index', delete=False) as index_file:
            # Initialize knowledge base
            kb = VectorKnowledgeBase(data_file.name, index_file.name)
            
            print("Step 1: Adding diverse test content")
            
            # Add test content with various categories
            test_items = [
                ("Machine learning models need high-quality training data to perform well", "insight"),
                ("Debugging JavaScript async functions can be challenging for developers", "challenge"),
                ("Code reviews should focus on architecture and logic, not just syntax", "best_practice"),
                ("AI tools are becoming more sophisticated in identifying code bugs", "observation"),
                ("Agile development practices improve team collaboration", "best_practice"),
                ("Database optimization requires understanding query execution plans", "insight"),
                ("Version control systems are essential for team development", "best_practice"),
                ("Natural language processing has revolutionized software interfaces", "trend"),
                ("Testing automation reduces manual QA overhead significantly", "observation"),
                ("API design patterns affect long-term maintainability", "insight")
            ]
            
            for content, category in test_items:
                kb.add_shared_item(content, category)
                print(f"  Added: {category}")
            
            print(f"\nStep 2: Testing enhanced query preprocessing")
            
            test_queries = [
                "How can AI help with debugging?",  # question
                "Find examples of best practices",   # search
                "Show me similar machine learning insights",  # similarity
                "What's the best approach for testing?",  # recommendation
                "JavaScript async challenges"  # general
            ]
            
            for query in test_queries:
                query_info = kb.preprocess_query(query)
                print(f"\nQuery: '{query}'")
                print(f"  Type: {query_info['query_type']}")
                print(f"  Key terms: {query_info['key_terms']}")
                print(f"  Suggested categories: {query_info['suggested_categories']}")
            
            print(f"\nStep 3: Testing enhanced search functionality")
            
            search_queries = [
                "debugging code issues",
                "machine learning best practices", 
                "team collaboration methods",
                "API design patterns"
            ]
            
            for query in search_queries:
                print(f"\nSearching for: '{query}'")
                results = kb.search_knowledge(query, max_results=3)
                
                print(f"  Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    data = result['data']
                    score = result['similarity_score']
                    relevance = result['relevance']
                    
                    content = data.get('content', data.get('insight', ''))[:80] + "..."
                    print(f"    {i}. {content}")
                    print(f"       Score: {score:.3f}, Relevance: {relevance}")
                    
                    if 'match_details' in result:
                        print(f"       Matches: {result['match_details']}")
            
            print(f"\nStep 4: Testing analytics and insights")
            
            # Get search analytics
            analytics = kb.get_search_analytics()
            print(f"\nSearch Analytics:")
            print(f"  Total searches: {analytics['total_searches']}")
            print(f"  Keyword searches: {analytics['keyword_searches']}")
            print(f"  Query types: {analytics['query_types']}")
            
            # Get content insights
            insights = kb.get_content_insights()
            print(f"\nContent Insights:")
            print(f"  Total items: {insights['total_items']}")
            print(f"  Categories: {insights['categories_distribution']}")
            print(f"  Content themes: {insights['content_themes']}")
            print(f"  Knowledge gaps: {insights['knowledge_gaps']}")
            
            print(f"\nStep 5: Testing query suggestions")
            
            for query in ["debugging", "best practices"]:
                suggestions = kb.suggest_related_queries(query)
                print(f"\nSuggestions for '{query}':")
                for suggestion in suggestions:
                    print(f"  - {suggestion}")
            
            print(f"\nStep 6: Testing knowledge summary")
            
            summary = kb.get_knowledge_summary()
            print(f"\nKnowledge Base Summary:")
            print(f"  Total shares: {summary['total_shares']}")
            print(f"  Search mode: {summary['search_mode']}")
            print(f"  Embedding model: {summary['embedding_model']}")
            
            # Test similarity search
            print(f"\nStep 7: Testing similar experiences")
            
            similar = kb.find_similar_experiences("finding bugs in software")
            print(f"\nSimilar experiences to 'finding bugs in software':")
            for result in similar[:2]:
                content = result['data'].get('content', result['data'].get('insight', ''))
                print(f"  - {content}")
                print(f"    Score: {result['similarity_score']:.3f}")
            
            print("\n" + "=" * 50)
            print("Enhanced semantic search test COMPLETED!")
            
            if not kb.embeddings_enabled:
                print("\nNOTE: Running in enhanced keyword mode.")
                print("Set OPENAI_API_KEY for full semantic capabilities.")
            
            # Cleanup
            os.unlink(data_file.name)
            try:
                os.unlink(index_file.name)
            except:
                pass

if __name__ == "__main__":
    test_enhanced_semantic_search() 