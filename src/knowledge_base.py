#!/usr/bin/env python3

import json
import os
from datetime import datetime
from typing import Dict, List, Any

class KnowledgeBase:
    """
    Knowledge storage and management system for Summit.
    
    Stores shared experiences, insights, and observations from agents
    and provides methods for retrieval and synthesis.
    """
    
    def __init__(self, data_file: str = "summit_knowledge.json"):
        self.data_file = data_file
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
    
    def save_knowledge(self):
        """Save knowledge base to file"""
        try:
            data = {
                'shared_items': self.shared_items,
                'synthesized_insights': self.synthesized_insights,
                'categories': self.categories,
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
    
    def get_knowledge_summary(self) -> Dict:
        """Get summary of current knowledge base"""
        return {
            'total_shares': len(self.shared_items),
            'categories': dict(self.categories),
            'synthesized_insights': len(self.synthesized_insights),
            'unprocessed_shares': len(self.get_unprocessed_shares()),
            'last_share': self.shared_items[-1]['timestamp'] if self.shared_items else None
        }
    
    def search_knowledge(self, query: str) -> List[Dict]:
        """Simple search through shared items and insights"""
        query_lower = query.lower()
        results = []
        
        # Search shared items
        for item in self.shared_items:
            if (query_lower in item['content'].lower() or 
                (item['context'] and query_lower in item['context'].lower())):
                results.append({
                    'type': 'shared_item',
                    'data': item,
                    'relevance': 'content_match'
                })
        
        # Search synthesized insights
        for insight in self.synthesized_insights:
            if query_lower in insight['insight'].lower():
                results.append({
                    'type': 'synthesized_insight',
                    'data': insight,
                    'relevance': 'insight_match'
                })
        
        return results 