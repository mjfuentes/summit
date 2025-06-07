#!/usr/bin/env python3

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict, Counter

class KnowledgeBase:
    """
    Simple knowledge storage and management system for Summit.
    
    Stores shared experiences, insights, and observations with basic search
    and analytics capabilities.
    """
    
    def __init__(self, data_file: str = None):
        # Set default path relative to project root
        if data_file is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            data_file = os.path.join(base_dir, "data", "summit_knowledge.json")
            
        self.data_file = data_file
        
        # Simple search analytics
        self.search_analytics = {
            'total_searches': 0,
            'empty_results': 0,
            'query_types': defaultdict(int),
            'popular_categories': defaultdict(int)
        }
        
        self.load_knowledge()
    
    def load_knowledge(self):
        """Load knowledge base from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.shared_items = data.get('shared_items', [])
                    self.synthesized_insights = data.get('synthesized_insights', [])
                    self.categories = data.get('categories', {})
                    self.search_analytics = data.get('search_analytics', self.search_analytics)
            else:
                self.reset_knowledge()
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            self.reset_knowledge()
    
    def reset_knowledge(self):
        """Reset knowledge base"""
        self.shared_items = []
        self.synthesized_insights = []
        self.categories = {}
        self.search_analytics = {
            'total_searches': 0,
            'empty_results': 0,
            'query_types': defaultdict(int),
            'popular_categories': defaultdict(int)
        }
    
    def save_knowledge(self):
        """Save knowledge base to file"""
        # Skip saving if we're in test mode or autonomous task mode
        if os.getenv('SUMMIT_READONLY_MODE') == 'true':
            return
            
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            data = {
                'shared_items': self.shared_items,
                'synthesized_insights': self.synthesized_insights,
                'categories': self.categories,
                'search_analytics': dict(self.search_analytics),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving knowledge base: {e}")
    
    def add_shared_item(self, content: str, category: str = None, context: str = None) -> Dict:
        """Add a new shared item to the knowledge base"""
        
        shared_item = {
            'id': len(self.shared_items) + 1,
            'content': content,
            'category': category or 'general',
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'processed': False
        }
        
        self.shared_items.append(shared_item)
        
        # Update category counts
        category_key = shared_item['category']
        self.categories[category_key] = self.categories.get(category_key, 0) + 1
        
        self.save_knowledge()
        return shared_item
    
    def add_synthesized_insight(self, insight: str, source_ids: List[int] = None):
        """Add a synthesized insight derived from shared items"""
        
        synthesized_insight = {
            'id': len(self.synthesized_insights) + 1,
            'insight': insight,
            'source_ids': source_ids or [],
            'timestamp': datetime.now().isoformat()
        }
        
        self.synthesized_insights.append(synthesized_insight)
        self.save_knowledge()
        return synthesized_insight
    
    def search_knowledge(self, query: str, max_results: int = 10) -> List[Dict]:
        """Enhanced search with analytics tracking"""
        
        # Update search analytics
        self.search_analytics['total_searches'] += 1
        
        query_lower = query.lower()
        results = []
        
        # Search shared items with simple scoring
        for item in self.shared_items:
            score = 0
            content_lower = item['content'].lower()
            context_lower = (item.get('context') or '').lower()
            
            # Exact phrase matching gets highest score
            if query_lower in content_lower:
                score += 2.0
            elif query_lower in context_lower:
                score += 1.5
            
            # Word matching
            query_words = query_lower.split()
            for word in query_words:
                if word in content_lower:
                    score += 1.0
                elif word in context_lower:
                    score += 0.5
            
            if score > 0:
                results.append({
                    'type': 'shared_item',
                    'data': item,
                    'similarity_score': score,
                    'relevance': 'keyword_match'
                })
        
        # Search synthesized insights
        for insight in self.synthesized_insights:
            score = 0
            insight_lower = insight['insight'].lower()
            
            if query_lower in insight_lower:
                score += 2.0
            
            query_words = query_lower.split()
            for word in query_words:
                if word in insight_lower:
                    score += 1.0
            
            if score > 0:
                results.append({
                    'type': 'synthesized_insight',
                    'data': insight,
                    'similarity_score': score,
                    'relevance': 'keyword_match'
                })
        
        # Sort by score and limit results
        results = sorted(results, key=lambda x: x['similarity_score'], reverse=True)[:max_results]
        
        # Update analytics
        if not results:
            self.search_analytics['empty_results'] += 1
        else:
            # Track popular categories
            for result in results:
                if result['type'] == 'shared_item':
                    category = result['data']['category']
                    self.search_analytics['popular_categories'][category] += 1
        
        # Save analytics periodically
        if self.search_analytics['total_searches'] % 10 == 0:
            self.save_knowledge()
        
        return results
    
    def get_recent_shares(self, limit: int = 10) -> List[Dict]:
        """Get recent shared items"""
        return sorted(self.shared_items, key=lambda x: x['timestamp'], reverse=True)[:limit]
    
    def get_shares_by_category(self, category: str) -> List[Dict]:
        """Get shared items by category"""
        return [item for item in self.shared_items if item['category'] == category]
    
    def get_unprocessed_shares(self) -> List[Dict]:
        """Get shares that haven't been processed yet"""
        return [item for item in self.shared_items if not item.get('processed', False)]
    
    def mark_as_processed(self, share_id: int):
        """Mark a shared item as processed"""
        for item in self.shared_items:
            if item['id'] == share_id:
                item['processed'] = True
                break
        self.save_knowledge()
    
    def get_search_analytics(self) -> Dict[str, Any]:
        """Get search analytics"""
        analytics = dict(self.search_analytics)
        
        # Calculate percentages
        total = analytics['total_searches']
        if total > 0:
            analytics['empty_rate'] = (analytics['empty_results'] / total) * 100
        else:
            analytics['empty_rate'] = 0
        
        # Convert defaultdicts to regular dicts
        analytics['query_types'] = dict(analytics['query_types'])
        analytics['popular_categories'] = dict(analytics['popular_categories'])
        
        return analytics
    
    def suggest_related_queries(self, query: str, max_suggestions: int = 3) -> List[str]:
        """Suggest related queries"""
        suggestions = []
        
        # Suggest based on popular categories
        popular_cats = sorted(self.categories.items(), key=lambda x: x[1], reverse=True)[:3]
        for cat, count in popular_cats:
            suggestions.append(f"Show me {cat} examples")
        
        return suggestions[:max_suggestions]
    
    def get_content_insights(self) -> Dict[str, Any]:
        """Analyze content to provide insights"""
        insights = {
            'total_items': len(self.shared_items),
            'total_insights': len(self.synthesized_insights),
            'categories_distribution': dict(self.categories),
            'recent_activity': None,
            'content_themes': [],
            'knowledge_gaps': []
        }
        
        # Recent activity
        if self.shared_items:
            recent_items = sorted(self.shared_items, key=lambda x: x['timestamp'], reverse=True)[:5]
            insights['recent_activity'] = {
                'count': len(recent_items),
                'categories': list(set(item['category'] for item in recent_items)),
                'timespan': f"Last activity: {recent_items[0]['timestamp'][:10]}"
            }
        
        # Content themes (simple word frequency)
        all_content = []
        for item in self.shared_items:
            all_content.append(item['content'])
        for insight in self.synthesized_insights:
            all_content.append(insight['insight'])
        
        if all_content:
            word_counts = Counter()
            for content in all_content:
                words = re.findall(r'\w+', content.lower())
                words = [w for w in words if len(w) > 4]
                word_counts.update(words)
            
            insights['content_themes'] = [word for word, count in word_counts.most_common(5)]
        
        # Knowledge gaps
        min_items = 3
        for category, count in self.categories.items():
            if count < min_items:
                insights['knowledge_gaps'].append(f"Limited {category} content ({count} items)")
        
        return insights
    
    def get_knowledge_summary(self) -> Dict:
        """Get comprehensive summary"""
        summary = {
            'total_shares': len(self.shared_items),
            'categories': dict(self.categories),
            'synthesized_insights': len(self.synthesized_insights),
            'last_share': self.shared_items[-1]['timestamp'] if self.shared_items else None,
            'search_mode': 'keyword_search',
            'search_analytics': self.get_search_analytics(),
            'content_insights': self.get_content_insights()
        }
        return summary
    
    def find_similar_experiences(self, content: str, top_k: int = 5) -> List[Dict]:
        """Find experiences similar to the given content"""
        return self.search_knowledge(content, max_results=top_k) 