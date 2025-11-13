from models import RecommendationEngine
from google_integration import RealTimeRecommendationEngine
from web_scraper import RealTimeContentFetcher
from dynamic_search import DynamicSearchEngine
from datetime import datetime, timedelta
import json

class EnhancedRecommendationEngine:
    def __init__(self):
        self.base_engine = RecommendationEngine()
        self.search_engine = RealTimeRecommendationEngine(self.base_engine)
        self.content_fetcher = RealTimeContentFetcher()
        self.dynamic_search = DynamicSearchEngine()
        
    def get_database_status(self):
        return self.base_engine.get_status()
    
    def add_user(self, user_id, preferences=None):
        return self.base_engine.add_user(user_id, preferences)
    
    def add_item(self, item_id, title, category, description, features=None):
        return self.base_engine.add_item(item_id, title, category, description, features)
    
    def record_interaction(self, user_id, item_id, interaction_type="view", rating=None):
        return self.base_engine.record_interaction(user_id, item_id, interaction_type, rating)
    
    def get_standard_recommendations(self, user_id, limit=10):
        """Get standard recommendations from database"""
        try:
            recommendations = self.base_engine.get_user_recommendations(user_id, limit)
            
            # Add source info to database recommendations
            for rec in recommendations:
                rec['source'] = 'database'
            
            # If no database recommendations, provide default content
            if not recommendations:
                default_items = [
                    {
                        'item_id': 'default_1',
                        'title': 'Getting Started Guide',
                        'category': 'education',
                        'description': 'Complete beginner guide to our platform',
                        'source': 'default'
                    },
                    {
                        'item_id': 'default_2', 
                        'title': 'Popular Content',
                        'category': 'entertainment',
                        'description': 'Most popular content on our platform',
                        'source': 'default'
                    },
                    {
                        'item_id': 'default_3',
                        'title': 'Latest Updates',
                        'category': 'technology',
                        'description': 'Recent updates and new features',
                        'source': 'default'
                    },
                    {
                        'item_id': 'default_4',
                        'title': 'Trending Topics',
                        'category': 'general',
                        'description': 'What everyone is talking about',
                        'source': 'default'
                    },
                    {
                        'item_id': 'default_5',
                        'title': 'Recommended for You',
                        'category': 'general',
                        'description': 'Personalized content suggestions',
                        'source': 'default'
                    }
                ]
                return default_items[:limit]
            
            return recommendations
        except Exception as e:
            print(f"Standard recommendations error: {e}")
            # Return fallback recommendations even on error
            return [
                {
                    'item_id': 'fallback_1',
                    'title': 'Welcome to Recommendations',
                    'category': 'general',
                    'description': 'Start exploring our recommendation system',
                    'source': 'fallback'
                }
            ]
    
    def get_search_powered_recommendations(self, user_id, limit=10, search_query=None):
        """Get recommendations powered by search history and real-time content"""
        try:
            # If search query provided, use dynamic search
            if search_query:
                search_analysis = self.dynamic_search.analyze_search_query(search_query)
                return self.dynamic_search.get_dynamic_recommendations(search_analysis, limit)
            
            # Get user's search profile
            if user_id in self.search_engine.user_profiles:
                profile = self.search_engine.user_profiles[user_id]
                search_intent = profile.get('search_intent', {})
                
                # Extract user interests safely
                keywords = search_intent.get('recent_searches', [])[:5]
                categories = [cat[0] for cat in search_intent.get('top_categories', [])]
                
                # Get personalized real-time content
                personalized_content = self.content_fetcher.get_personalized_content(
                    keywords, categories, limit//2
                )
                
                # Get database recommendations
                try:
                    db_recs = self.base_engine.get_user_recommendations(user_id, limit//2)
                    for rec in db_recs:
                        rec['source'] = 'database'
                except:
                    db_recs = []
                
                # Combine recommendations
                all_recommendations = personalized_content + db_recs
                
                # Sort by relevance score
                all_recommendations.sort(
                    key=lambda x: x.get('search_relevance_score', 0), 
                    reverse=True
                )
                
                return all_recommendations[:limit] if all_recommendations else self.get_standard_recommendations(user_id, limit)
            else:
                # No search profile, generate AI-powered content anyway
                ai_content = self.content_fetcher.get_personalized_content(
                    ['trending', 'popular', 'recommended'], 
                    ['technology', 'entertainment'], 
                    limit
                )
                return ai_content if ai_content else self.get_standard_recommendations(user_id, limit)
                
        except Exception as e:
            print(f"Search-powered recommendations error: {e}")
            return self.get_standard_recommendations(user_id, limit)
    
    def get_trending_content(self, hours=24, limit=10, category="", search_query=None):
        """Get real-time trending content"""
        try:
            # If search query provided, use dynamic search
            if search_query:
                search_analysis = self.dynamic_search.analyze_search_query(search_query)
                return self.dynamic_search.get_dynamic_trending(search_analysis, hours, limit)
            
            # Get trending content from web scraper
            trending_items = self.content_fetcher.search_trending_content(category, hours)
            
            # Get trending from database if available
            try:
                db_trending = self.base_engine.get_trending_items(hours, limit//2)
                
                # Format database trending to match expected structure
                formatted_db_trending = []
                for item in db_trending:
                    if isinstance(item, dict):
                        if 'item_details' in item:
                            formatted_item = item['item_details'].copy()
                            formatted_item['trend_score'] = item.get('trend_score', 0)
                            formatted_item['source'] = 'database'
                            formatted_db_trending.append(formatted_item)
                        else:
                            # Handle direct item format
                            item['source'] = 'database'
                            formatted_db_trending.append(item)
            except Exception as db_error:
                print(f"Database trending error: {db_error}")
                formatted_db_trending = []
            
            # Combine trending sources
            all_trending = trending_items + formatted_db_trending
            
            # Ensure all items have required fields
            for item in all_trending:
                if 'trend_score' not in item:
                    item['trend_score'] = 50
                if 'source' not in item:
                    item['source'] = 'real-time'
            
            # Sort by trend score
            all_trending.sort(key=lambda x: x.get('trend_score', 0), reverse=True)
            
            return all_trending[:limit] if all_trending else self._get_fallback_trending(limit)
            
        except Exception as e:
            print(f"Trending content error: {e}")
            return self._get_fallback_trending(limit)
    
    def _get_fallback_trending(self, limit=10):
        """Fallback trending content when all else fails"""
        return [
            {
                'item_id': 'trending_fallback_1',
                'title': 'Latest Technology Trends',
                'category': 'technology',
                'description': 'Current trends in technology and innovation',
                'trend_score': 95,
                'source': 'fallback'
            },
            {
                'item_id': 'trending_fallback_2',
                'title': 'Popular Entertainment Content',
                'category': 'entertainment',
                'description': 'Trending movies, shows, and entertainment',
                'trend_score': 90,
                'source': 'fallback'
            },
            {
                'item_id': 'trending_fallback_3',
                'title': 'Hot Shopping Deals',
                'category': 'shopping',
                'description': 'Best deals and trending products',
                'trend_score': 85,
                'source': 'fallback'
            }
        ][:limit]
    
    def update_search_profile(self, user_id, search_history):
        """Update user's search profile"""
        try:
            return self.search_engine.update_user_profile(user_id, search_history)
        except Exception as e:
            print(f"Search profile update error: {e}")
            return {'error': str(e)}
    
    def get_search_suggestions(self, partial_query, limit=5):
        """Get dynamic search suggestions"""
        try:
            return self.dynamic_search.get_search_suggestions(partial_query, limit)
        except Exception as e:
            print(f"Search suggestions error: {e}")
            return []
    
    def get_status_info(self):
        """Get comprehensive status information"""
        try:
            base_status = {
                "database": self.base_engine.get_status(),
                "search_profiles": len(self.search_engine.user_profiles),
                "real_time_enabled": True
            }
            
            if self.base_engine.use_memory:
                base_status.update({
                    "users_count": len(self.base_engine.memory_users),
                    "items_count": len(self.base_engine.memory_items),
                    "interactions_count": len(self.base_engine.memory_interactions)
                })
            else:
                base_status.update({
                    "users_count": self.base_engine.users.count_documents({}),
                    "items_count": self.base_engine.items.count_documents({}),
                    "interactions_count": self.base_engine.interactions.count_documents({})
                })
            
            return base_status
        except Exception as e:
            return {"error": str(e), "database": "Error", "real_time_enabled": False}
