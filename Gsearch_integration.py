import json
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, unquote
from collections import Counter

class GoogleSearchAnalyzer:
    def __init__(self):
        self.search_patterns = [
            r'q=([^&]+)',  # Google search query parameter
            r'search\?.*q=([^&]+)',  # Search URL pattern
            r'google\.com.*q=([^&]+)'  # Google domain search
        ]
        self.category_keywords = {
            'technology': ['python', 'programming', 'software', 'ai', 'machine learning', 'tech', 'computer'],
            'entertainment': ['movie', 'film', 'music', 'game', 'netflix', 'youtube', 'streaming'],
            'shopping': ['buy', 'price', 'review', 'product', 'amazon', 'shop', 'deal'],
            'education': ['learn', 'course', 'tutorial', 'study', 'university', 'book'],
            'health': ['health', 'fitness', 'medical', 'doctor', 'exercise', 'diet'],
            'travel': ['travel', 'hotel', 'flight', 'vacation', 'trip', 'destination']
        }
    
    def extract_search_queries(self, browser_history):
        """Extract search queries from browser history data"""
        queries = []
        for entry in browser_history:
            url = entry.get('url', '')
            title = entry.get('title', '')
            timestamp = entry.get('timestamp', datetime.now())
            
            # Convert timestamp if it's a string
            if isinstance(timestamp, str):
                try:
                    # Handle various timestamp formats
                    if timestamp.endswith('Z'):
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', ''))
                    elif '+' in timestamp or timestamp.endswith('00:00'):
                        timestamp = datetime.fromisoformat(timestamp.split('+')[0])
                    else:
                        timestamp = datetime.fromisoformat(timestamp)
                except:
                    timestamp = datetime.now()
            
            # Extract query from URL or use title
            query_found = False
            extracted_query = None
            
            # Try to extract from URL first
            if 'google.com' in url and 'q=' in url:
                try:
                    # Extract query parameter
                    match = re.search(r'q=([^&]+)', url)
                    if match:
                        extracted_query = unquote(match.group(1)).replace('+', ' ')
                        query_found = True
                except:
                    pass
            
            # If no query from URL, use title
            if not query_found and title and not title.startswith('http'):
                extracted_query = title
                query_found = True
            
            # Add the query if we found one
            if query_found and extracted_query:
                queries.append({
                    'query': extracted_query.strip(),
                    'timestamp': timestamp,
                    'url': url,
                    'title': title
                })
        
        return queries
    
    def categorize_search(self, query):
        """Categorize search query based on keywords"""
        query_lower = query.lower()
        scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                scores[category] = score
        
        return max(scores.items(), key=lambda x: x[1])[0] if scores else 'general'
    
    def analyze_search_intent(self, queries):
        """Analyze user search intent and preferences"""
        if not queries:
            return {
                'top_categories': [],
                'search_frequency': 0,
                'keywords': '',
                'recent_searches': []
            }
        
        # Recent queries (last 7 days) - handle timezone issues
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_queries = []
        for q in queries:
            try:
                # Handle both timezone-aware and naive datetimes
                ts = q['timestamp']
                if hasattr(ts, 'replace') and ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                if ts >= recent_cutoff:
                    recent_queries.append(q)
            except (TypeError, AttributeError):
                # If timestamp comparison fails, include the query
                recent_queries.append(q)
        
        # Category analysis
        categories = {}
        valid_queries = []
        
        for query in recent_queries:
            if query.get('query') and len(query['query'].strip()) > 0:
                valid_queries.append(query)
                category = self.categorize_search(query['query'])
                if category != 'general':  # Only count non-general categories
                    categories[category] = categories.get(category, 0) + 1
        
        # Extract keywords from valid queries
        all_queries = ' '.join([q['query'] for q in valid_queries if q.get('query')])
        
        return {
            'top_categories': sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3],
            'search_frequency': len(valid_queries),
            'keywords': all_queries,
            'recent_searches': [q['query'] for q in valid_queries[-10:] if q.get('query')]
        }
    
    def generate_content_vector(self, search_intent):
        """Generate simple content profile from search intent"""
        keywords = search_intent.get('keywords', '').lower().split()
        categories = [cat[0] for cat in search_intent.get('top_categories', [])]
        return {
            'keywords': keywords,
            'categories': categories,
            'search_count': search_intent.get('search_frequency', 0)
        }

class RealTimeRecommendationEngine:
    def __init__(self, base_engine):
        self.base_engine = base_engine
        self.search_analyzer = GoogleSearchAnalyzer()
        self.user_profiles = {}  # Store user search profiles
    
    def update_user_profile(self, user_id, browser_history):
        """Update user profile with latest search history"""
        queries = self.search_analyzer.extract_search_queries(browser_history)
        search_intent = self.search_analyzer.analyze_search_intent(queries)
        content_vector = self.search_analyzer.generate_content_vector(search_intent)
        
        self.user_profiles[user_id] = {
            'search_intent': search_intent,
            'content_vector': content_vector,
            'last_updated': datetime.now(),
            'total_searches': len(queries)
        }
        
        return search_intent
    
    def get_personalized_recommendations(self, user_id, limit=10):
        """Get recommendations based on search history and behavior"""
        # Get base recommendations
        base_recs = self.base_engine.get_user_recommendations(user_id, limit * 2)
        
        # If no search profile, return base recommendations
        if user_id not in self.user_profiles:
            return base_recs[:limit]
        
        profile = self.user_profiles[user_id]
        user_vector = profile['content_vector']
        
        # Score items based on search intent
        scored_items = []
        user_keywords = user_vector.get('keywords', [])
        user_categories = user_vector.get('categories', [])
        
        for item in base_recs:
            item_text = f"{item.get('title', '')} {item.get('description', '')}".lower()
            item_category = item.get('category', '').lower()
            
            # Keyword matching score
            keyword_score = 0
            for keyword in user_keywords:
                if len(keyword) > 2 and keyword in item_text:
                    keyword_score += 0.2
            
            # Category matching score
            category_score = 0
            if item_category in [cat.lower() for cat in user_categories]:
                category_score = 0.5
            
            # Combined score
            final_score = keyword_score + category_score
            item['search_relevance_score'] = final_score
            scored_items.append(item)
        
        # Sort by search relevance
        scored_items.sort(key=lambda x: x.get('search_relevance_score', 0), reverse=True)
        
        return scored_items[:limit]
    
    def get_search_based_suggestions(self, user_id, limit=5):
        """Get content suggestions based purely on search history"""
        if user_id not in self.user_profiles:
            return [{
                'type': 'no_profile',
                'category': 'No Profile',
                'reason': 'No search history found. Upload your search history first.',
                'confidence': 0.0
            }]
        
        profile = self.user_profiles[user_id]
        search_intent = profile['search_intent']
        
        suggestions = []
        
        # Generate suggestions based on top categories
        for category, count in search_intent.get('top_categories', [])[:3]:
            suggestions.append({
                'type': 'category_suggestion',
                'category': category.title(),
                'reason': f'Based on {count} recent searches in {category}',
                'confidence': min(count / 5.0, 1.0)
            })
        
        # Generate suggestions based on recent searches
        recent_searches = search_intent.get('recent_searches', [])[:2]
        for search in recent_searches:
            suggestions.append({
                'type': 'search_suggestion',
                'query': search[:50] + '...' if len(search) > 50 else search,
                'reason': f'Related to: "{search[:30]}..."',
                'confidence': 0.7
            })
        
        return suggestions[:limit] if suggestions else [{
            'type': 'no_data',
            'category': 'No Data',
            'reason': 'No search patterns detected yet.',
            'confidence': 0.0
        }]
