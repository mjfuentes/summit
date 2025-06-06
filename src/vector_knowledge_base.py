#!/usr/bin/env python3

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter

class EnhancedKnowledgeBase:
    """
    Enhanced knowledge storage with intelligent search capabilities.
    
    Uses advanced keyword search with intent detection, weighted scoring,
    and analytics for superior search experiences.
    """
    
    def __init__(self, data_file: str = None):
        # Set default path relative to project root
        if data_file is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            data_file = os.path.join(base_dir, "data", "summit_knowledge.json")
            
        self.data_file = data_file
        
        # Search analytics
        self.search_analytics = {
            'total_searches': 0,
            'empty_results': 0,
            'query_types': defaultdict(int),
            'popular_categories': defaultdict(int)
        }
        
        self.load_knowledge()
    
    def preprocess_query(self, query: str) -> Dict[str, Any]:
        """Enhanced query preprocessing to extract intent and key terms"""
        query_lower = query.lower().strip()
        
        # Detect query type/intent
        query_type = "general"
        if any(word in query_lower for word in ["how", "why", "what", "when", "where"]):
            query_type = "question"
        elif any(word in query_lower for word in ["find", "search", "show", "list"]):
            query_type = "search"
        elif any(word in query_lower for word in ["similar", "like", "related"]):
            query_type = "similarity"
        elif any(word in query_lower for word in ["best", "recommend", "suggest"]):
            query_type = "recommendation"
        
        # Extract key terms (remove stop words and clean)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'can', 'may', 'might', 'must', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        # Clean and tokenize
        clean_query = re.sub(r'[^\w\s]', ' ', query_lower)
        tokens = [word for word in clean_query.split() if word not in stop_words and len(word) > 2]
        
        # Extract potential categories
        category_keywords = {
            'observation': ['observe', 'notice', 'see', 'found', 'discover'],
            'insight': ['insight', 'understand', 'realize', 'learn', 'pattern'],
            'challenge': ['challenge', 'problem', 'issue', 'difficult', 'struggle'],
            'best_practice': ['best', 'practice', 'method', 'approach', 'way'],
            'trend': ['trend', 'changing', 'evolution', 'future', 'direction']
        }
        
        suggested_categories = []
        for category, keywords in category_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                suggested_categories.append(category)
        
        return {
            'original': query,
            'cleaned': clean_query,
            'tokens': tokens,
            'query_type': query_type,
            'suggested_categories': suggested_categories,
            'key_terms': ' '.join(tokens)
        }
    
    def enhanced_keyword_search(self, query_info: Dict[str, Any]) -> List[Dict]:
        """Enhanced keyword search with better scoring and ranking"""
        results = []
        tokens = query_info['tokens']
        suggested_categories = query_info['suggested_categories']
        
        # Search shared items
        for item in self.shared_items:
            score = 0
            matches = []
            
            # Content matching with weighted scoring
            content_lower = item['content'].lower()
            context_lower = (item.get('context') or '').lower()
            
            # Exact phrase matching (highest score)
            if query_info['key_terms'] in content_lower:
                score += 2.0
                matches.append('exact_phrase')
            
            # Individual token matching
            content_tokens = set(re.findall(r'\w+', content_lower))
            context_tokens = set(re.findall(r'\w+', context_lower))
            all_tokens = content_tokens.union(context_tokens)
            
            token_matches = sum(1 for token in tokens if token in all_tokens)
            if token_matches > 0:
                score += (token_matches / len(tokens)) * 1.5
                matches.append(f'token_match_{token_matches}')
            
            # Category bonus
            if item['category'] in suggested_categories:
                score += 0.5
                matches.append('category_match')
            
            # Recency bonus (more recent items get slight boost)
            try:
                item_date = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                days_old = (datetime.now() - item_date.replace(tzinfo=None)).days
                recency_bonus = max(0, (30 - days_old) / 100)  # Bonus decreases over 30 days
                score += recency_bonus
            except:
                pass
            
            if score > 0:
                results.append({
                    'type': 'shared_item',
                    'data': item,
                    'similarity_score': score,
                    'relevance': 'enhanced_keyword_match',
                    'match_details': matches
                })
        
        # Search synthesized insights
        for insight in self.synthesized_insights:
            score = 0
            matches = []
            
            insight_lower = insight['insight'].lower()
            
            # Exact phrase matching
            if query_info['key_terms'] in insight_lower:
                score += 2.0
                matches.append('exact_phrase')
            
            # Token matching
            insight_tokens = set(re.findall(r'\w+', insight_lower))
            token_matches = sum(1 for token in tokens if token in insight_tokens)
            if token_matches > 0:
                score += (token_matches / len(tokens)) * 1.5
                matches.append(f'token_match_{token_matches}')
            
            # Insights get a small bonus as they're synthesized knowledge
            if score > 0:
                score += 0.3
                matches.append('insight_bonus')
            
            if score > 0:
                results.append({
                    'type': 'synthesized_insight',
                    'data': insight,
                    'similarity_score': score,
                    'relevance': 'enhanced_keyword_match',
                    'match_details': matches
                })
        
        return results
    
    def rank_results(self, results: List[Dict], query_info: Dict[str, Any]) -> List[Dict]:
        """Advanced result ranking considering multiple factors"""
        if not results:
            return results
        
        # Calculate final scores
        for result in results:
            final_score = result['similarity_score']
            
            # Query type bonus
            if query_info['query_type'] == 'question' and result['type'] == 'synthesized_insight':
                final_score *= 1.2  # Insights are better for questions
            elif query_info['query_type'] == 'similarity' and result['type'] == 'shared_item':
                final_score *= 1.1  # Items are better for similarity searches
            
            # Category relevance
            if (result['type'] == 'shared_item' and 
                result['data']['category'] in query_info['suggested_categories']):
                final_score *= 1.15
            
            result['final_score'] = final_score
        
        # Sort by final score
        return sorted(results, key=lambda x: x['final_score'], reverse=True)
    
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
        try:
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
        
        # Preprocess query
        query_info = self.preprocess_query(query)
        self.search_analytics['query_types'][query_info['query_type']] += 1
        
        # Enhanced keyword search
        results = self.enhanced_keyword_search(query_info)
        
        # Advanced ranking
        results = self.rank_results(results, query_info)
        
        # Limit results
        results = results[:max_results]
        
        # Update analytics
        if not results:
            self.search_analytics['empty_results'] += 1
        else:
            # Track popular categories from results
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
        """Get search analytics and insights"""
        analytics = dict(self.search_analytics)
        
        # Calculate percentages
        total = analytics['total_searches']
        if total > 0:
            analytics['empty_rate'] = (analytics['empty_results'] / total) * 100
        else:
            analytics['empty_rate'] = 0
        
        # Convert defaultdicts to regular dicts for JSON serialization
        analytics['query_types'] = dict(analytics['query_types'])
        analytics['popular_categories'] = dict(analytics['popular_categories'])
        
        return analytics
    
    def suggest_related_queries(self, query: str, max_suggestions: int = 3) -> List[str]:
        """Suggest related queries based on content analysis"""
        query_info = self.preprocess_query(query)
        suggestions = []
        
        # Suggest based on categories
        for category in query_info['suggested_categories']:
            if category in self.categories:
                suggestions.append(f"Show me more {category} examples")
        
        # Suggest based on popular categories
        popular_cats = sorted(self.categories.items(), key=lambda x: x[1], reverse=True)[:3]
        for cat, count in popular_cats:
            if cat not in query_info['suggested_categories']:
                suggestions.append(f"What about {cat}?")
        
        # Suggest query variations
        if query_info['query_type'] == 'question':
            suggestions.append(f"Similar experiences to: {query_info['key_terms']}")
        elif query_info['query_type'] == 'search':
            suggestions.append(f"Why {query_info['key_terms']}?")
        
        return suggestions[:max_suggestions]
    
    def get_content_insights(self) -> Dict[str, Any]:
        """Analyze content to provide insights about the knowledge base"""
        insights = {
            'total_items': len(self.shared_items),
            'total_insights': len(self.synthesized_insights),
            'categories_distribution': dict(self.categories),
            'recent_activity': None,
            'content_themes': [],
            'knowledge_gaps': []
        }
        
        # Recent activity analysis
        if self.shared_items:
            recent_items = sorted(self.shared_items, key=lambda x: x['timestamp'], reverse=True)[:5]
            insights['recent_activity'] = {
                'count': len(recent_items),
                'categories': list(set(item['category'] for item in recent_items)),
                'timespan': f"Last activity: {recent_items[0]['timestamp'][:10]}"
            }
        
        # Content themes (based on common words)
        all_content = []
        for item in self.shared_items:
            all_content.append(item['content'])
        for insight in self.synthesized_insights:
            all_content.append(insight['insight'])
        
        if all_content:
            # Simple word frequency analysis
            word_counts = Counter()
            for content in all_content:
                words = re.findall(r'\w+', content.lower())
                words = [w for w in words if len(w) > 4]  # Only meaningful words
                word_counts.update(words)
            
            insights['content_themes'] = [word for word, count in word_counts.most_common(5)]
        
        # Knowledge gaps (categories with few items)
        min_items_per_category = 3
        for category, count in self.categories.items():
            if count < min_items_per_category:
                insights['knowledge_gaps'].append(f"Limited {category} content ({count} items)")
        
        return insights
    
    def get_knowledge_summary(self) -> Dict:
        """Get comprehensive summary of current knowledge base"""
        summary = {
            'total_shares': len(self.shared_items),
            'categories': dict(self.categories),
            'synthesized_insights': len(self.synthesized_insights),
            'last_share': self.shared_items[-1]['timestamp'] if self.shared_items else None,
            'search_mode': 'enhanced_keyword',
            'search_analytics': self.get_search_analytics(),
            'content_insights': self.get_content_insights()
        }
        return summary
    
    def find_similar_experiences(self, content: str, top_k: int = 5) -> List[Dict]:
        """Find experiences similar to the given content"""
        query_info = self.preprocess_query(content)
        return self.enhanced_keyword_search(query_info)[:top_k] 