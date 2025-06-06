#!/usr/bin/env python3

import json
import os
import numpy as np
import faiss
from datetime import datetime
from typing import Dict, List, Any, Optional
from openai import OpenAI

class VectorKnowledgeBase:
    """
    Vector-enabled knowledge storage with semantic search capabilities.
    
    Uses embeddings to find semantically similar experiences and insights
    even when they use different wording or concepts.
    """
    
    def __init__(self, data_file: str = None, 
                 index_file: str = None):
        # Set default paths relative to project root
        if data_file is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            data_file = os.path.join(base_dir, "data", "summit_vector_knowledge.json")
        if index_file is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            index_file = os.path.join(base_dir, "data", "summit_embeddings.index")
            
        self.data_file = data_file
        self.index_file = index_file
        self.embedding_dim = 1536  # OpenAI text-embedding-3-small dimension
        
        # Initialize OpenAI client for embeddings (if API key available)
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                self.embeddings_enabled = True
            else:
                self.openai_client = None
                self.embeddings_enabled = False
                print("Warning: OPENAI_API_KEY not set. Vector search disabled, using keyword search only.")
        except Exception as e:
            print(f"Warning: Could not initialize OpenAI client: {e}")
            self.openai_client = None
            self.embeddings_enabled = False
        
        # Initialize FAISS index for vector similarity search
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product (cosine similarity)
        
        self.load_knowledge()
    
    def load_knowledge(self):
        """Load knowledge base and vector index from files"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.shared_items = data.get('shared_items', [])
                    self.synthesized_insights = data.get('synthesized_insights', [])
                    self.categories = data.get('categories', {})
                    self.embeddings_metadata = data.get('embeddings_metadata', [])
            else:
                self.reset_knowledge()
            
            # Load FAISS index if exists
            if os.path.exists(self.index_file) and len(self.embeddings_metadata) > 0:
                self.index = faiss.read_index(self.index_file)
            
        except Exception as e:
            print(f"Error loading vector knowledge base: {e}")
            self.reset_knowledge()
    
    def reset_knowledge(self):
        """Reset knowledge base and vector index"""
        self.shared_items = []
        self.synthesized_insights = []
        self.categories = {}
        self.embeddings_metadata = []
        self.index = faiss.IndexFlatIP(self.embedding_dim)
    
    def save_knowledge(self):
        """Save knowledge base and vector index to files"""
        try:
            data = {
                'shared_items': self.shared_items,
                'synthesized_insights': self.synthesized_insights,
                'categories': self.categories,
                'embeddings_metadata': self.embeddings_metadata,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Save FAISS index
            if self.index.ntotal > 0:
                faiss.write_index(self.index, self.index_file)
                
        except Exception as e:
            print(f"Error saving vector knowledge base: {e}")
    
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text using OpenAI"""
        try:
            if not self.openai_client:
                return None
                
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            # Normalize for cosine similarity with inner product
            embedding = embedding / np.linalg.norm(embedding)
            return embedding
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def add_shared_item(self, content: str, category: str = None, context: str = None) -> Dict:
        """Add a new shared item with vector embedding"""
        
        shared_item = {
            'id': len(self.shared_items) + 1,
            'content': content,
            'category': category or 'general',
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'processed': False
        }
        
        self.shared_items.append(shared_item)
        
        # Generate embedding
        full_text = content
        if context:
            full_text += f" {context}"
            
        if self.embeddings_enabled:
            embedding = self.generate_embedding(full_text)
            if embedding is not None:
                # Add to FAISS index
                self.index.add(embedding.reshape(1, -1))
                
                # Store metadata
                embedding_metadata = {
                    'item_id': shared_item['id'],
                    'item_type': 'shared_item',
                    'text': full_text,
                    'timestamp': shared_item['timestamp']
                }
                self.embeddings_metadata.append(embedding_metadata)
        
        # Update category counts
        category_key = shared_item['category']
        self.categories[category_key] = self.categories.get(category_key, 0) + 1
        
        self.save_knowledge()
        return shared_item
    
    def add_synthesized_insight(self, insight: str, source_ids: List[int] = None):
        """Add a synthesized insight with vector embedding"""
        
        synthesized_insight = {
            'id': len(self.synthesized_insights) + 1,
            'insight': insight,
            'source_ids': source_ids or [],
            'timestamp': datetime.now().isoformat()
        }
        
        self.synthesized_insights.append(synthesized_insight)
        
        # Generate embedding for insight
        if self.embeddings_enabled:
            embedding = self.generate_embedding(insight)
            if embedding is not None:
                self.index.add(embedding.reshape(1, -1))
                
                embedding_metadata = {
                    'item_id': synthesized_insight['id'],
                    'item_type': 'synthesized_insight',
                    'text': insight,
                    'timestamp': synthesized_insight['timestamp']
                }
                self.embeddings_metadata.append(embedding_metadata)
        
        self.save_knowledge()
        return synthesized_insight
    
    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Perform semantic similarity search using vector embeddings"""
        
        if self.index.ntotal == 0:
            return []
        
        # Generate embedding for query
        query_embedding = self.generate_embedding(query)
        if query_embedding is None:
            return []
        
        # Search similar vectors
        scores, indices = self.index.search(query_embedding.reshape(1, -1), top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= len(self.embeddings_metadata):
                continue
                
            metadata = self.embeddings_metadata[idx]
            
            # Get the actual item
            if metadata['item_type'] == 'shared_item':
                item = next((item for item in self.shared_items if item['id'] == metadata['item_id']), None)
                if item:
                    results.append({
                        'type': 'shared_item',
                        'data': item,
                        'similarity_score': float(score),
                        'relevance': 'semantic_match'
                    })
            elif metadata['item_type'] == 'synthesized_insight':
                insight = next((insight for insight in self.synthesized_insights 
                              if insight['id'] == metadata['item_id']), None)
                if insight:
                    results.append({
                        'type': 'synthesized_insight',
                        'data': insight,
                        'similarity_score': float(score),
                        'relevance': 'semantic_match'
                    })
        
        return results
    
    def search_knowledge(self, query: str, use_semantic: bool = True) -> List[Dict]:
        """Search knowledge using both semantic and keyword approaches"""
        results = []
        
        # Semantic search using embeddings (only if enabled)
        if use_semantic and self.embeddings_enabled:
            semantic_results = self.semantic_search(query, top_k=3)
            results.extend(semantic_results)
        
        # Traditional keyword search as fallback
        query_lower = query.lower()
        
        for item in self.shared_items:
            if (query_lower in item['content'].lower() or 
                (item['context'] and query_lower in item['context'].lower())):
                # Check if not already in semantic results
                if not any(r['type'] == 'shared_item' and r['data']['id'] == item['id'] for r in results):
                    results.append({
                        'type': 'shared_item',
                        'data': item,
                        'similarity_score': 0.5,  # Lower score for keyword match
                        'relevance': 'keyword_match'
                    })
        
        for insight in self.synthesized_insights:
            if query_lower in insight['insight'].lower():
                if not any(r['type'] == 'synthesized_insight' and r['data']['id'] == insight['id'] for r in results):
                    results.append({
                        'type': 'synthesized_insight',
                        'data': insight,
                        'similarity_score': 0.5,
                        'relevance': 'keyword_match'
                    })
        
        # Sort by similarity score
        return sorted(results, key=lambda x: x['similarity_score'], reverse=True)
    
    def get_recent_shares(self, limit: int = 10) -> List[Dict]:
        """Get recent shared items"""
        return sorted(self.shared_items, key=lambda x: x['timestamp'], reverse=True)[:limit]
    
    def get_shares_by_category(self, category: str) -> List[Dict]:
        """Get shared items by category"""
        return [item for item in self.shared_items if item['category'] == category]
    
    def get_knowledge_summary(self) -> Dict:
        """Get summary of current knowledge base"""
        return {
            'total_shares': len(self.shared_items),
            'categories': dict(self.categories),
            'synthesized_insights': len(self.synthesized_insights),
            'total_embeddings': self.index.ntotal,
            'embedding_model': 'text-embedding-3-small',
            'last_share': self.shared_items[-1]['timestamp'] if self.shared_items else None
        }
    
    def find_similar_experiences(self, content: str, top_k: int = 5) -> List[Dict]:
        """Find experiences similar to the given content"""
        return self.semantic_search(content, top_k) 