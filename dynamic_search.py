import re
from datetime import datetime
from web_scraper import RealTimeContentFetcher

class DynamicSearchEngine:
    def __init__(self):
        self.content_fetcher = RealTimeContentFetcher()
        self.category_keywords = {
            'technology': ['python', 'javascript', 'programming', 'ai', 'machine learning', 'web development', 'software', 'coding', 'tech', 'computer', 'algorithm', 'data science'],
            'entertainment': ['movie', 'film', 'netflix', 'tv show', 'series', 'streaming', 'music', 'game', 'gaming', 'entertainment', 'video', 'cinema'],
            'shopping': ['buy', 'purchase', 'deal', 'product', 'review', 'amazon', 'shop', 'store', 'price', 'discount', 'sale', 'electronics'],
            'education': ['learn', 'course', 'tutorial', 'study', 'education', 'university', 'school', 'training', 'certification', 'book', 'knowledge'],
            'health': ['health', 'fitness', 'exercise', 'diet', 'nutrition', 'wellness', 'medical', 'doctor', 'workout', 'medicine', 'mental health'],
            'travel': ['travel', 'vacation', 'trip', 'hotel', 'flight', 'destination', 'tourism', 'holiday', 'adventure', 'explore', 'journey']
        }
    
    def analyze_search_query(self, query):
        """Analyze search query to extract intent and categories"""
        query_lower = query.lower().strip()
        
        # Extract keywords
        keywords = re.findall(r'\b\w+\b', query_lower)
        keywords = [k for k in keywords if len(k) > 2]  # Filter short words
        
        # Determine categories based on keywords
        category_scores = {}
        for category, cat_keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                for cat_keyword in cat_keywords:
                    if keyword in cat_keyword or cat_keyword in keyword:
                        score += 1
            if score > 0:
                category_scores[category] = score
        
        # Get top categories
        top_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Determine primary category
        primary_category = top_categories[0][0] if top_categories else 'general'
        
        return {
            'query': query,
            'keywords': keywords,
            'primary_category': primary_category,
            'categories': [cat[0] for cat in top_categories],
            'intent': self._determine_intent(query_lower)
        }
    
    def _determine_intent(self, query):
        """Determine user intent from query"""
        if any(word in query for word in ['how to', 'tutorial', 'learn', 'guide']):
            return 'learning'
        elif any(word in query for word in ['best', 'top', 'recommend', 'suggestion']):
            return 'recommendation'
        elif any(word in query for word in ['buy', 'purchase', 'deal', 'price']):
            return 'shopping'
        elif any(word in query for word in ['latest', 'new', 'trending', 'popular']):
            return 'trending'
        elif any(word in query for word in ['review', 'opinion', 'compare']):
            return 'research'
        else:
            return 'general'
    
    def get_dynamic_recommendations(self, search_analysis, limit=10):
        """Generate recommendations based purely on search query"""
        query = search_analysis['query']
        keywords = search_analysis['keywords']
        intent = search_analysis['intent']
        
        # Generate query-specific recommendations
        query_recommendations = self._generate_query_recommendations(query, keywords, intent, limit)
        
        # Sort by relevance to search query
        for rec in query_recommendations:
            rec['search_relevance_score'] = self._calculate_query_relevance(
                rec, query, keywords
            )
        
        query_recommendations.sort(
            key=lambda x: x.get('search_relevance_score', 0), 
            reverse=True
        )
        
        return query_recommendations[:limit]
    
    def get_dynamic_trending(self, search_analysis, hours=24, limit=10):
        """Generate trending content based purely on search query"""
        query = search_analysis['query']
        keywords = search_analysis['keywords']
        
        # Generate query-specific trending content
        query_trending = self._generate_query_trending(query, keywords, hours, limit)
        
        # Sort by relevance to search query
        for item in query_trending:
            item['search_relevance_score'] = self._calculate_query_relevance(
                item, query, keywords
            )
        
        query_trending.sort(
            key=lambda x: (x.get('search_relevance_score', 0), x.get('trend_score', 0)), 
            reverse=True
        )
        
        return query_trending[:limit]
    
    def _get_intent_specific_content(self, search_analysis, limit):
        """Generate content specific to user intent"""
        intent = search_analysis['intent']
        keywords = search_analysis['keywords']
        primary_category = search_analysis['primary_category']
        
        intent_templates = {
            'learning': [
                'How to Learn {}',
                '{} Tutorial for Beginners',
                'Complete {} Guide',
                '{} Step-by-Step Course'
            ],
            'recommendation': [
                'Best {} Recommendations',
                'Top {} Picks 2024',
                'Recommended {} Resources',
                'Expert {} Suggestions'
            ],
            'shopping': [
                'Best {} to Buy',
                '{} Deals and Offers',
                'Where to Buy {}',
                '{} Price Comparison'
            ],
            'trending': [
                'Trending {} Topics',
                'Latest {} News',
                'Popular {} Content',
                'What\'s Hot in {}'
            ],
            'research': [
                '{} Reviews and Analysis',
                '{} Comparison Guide',
                '{} Pros and Cons',
                'Expert {} Opinions'
            ]
        }
        
        templates = intent_templates.get(intent, intent_templates['recommendation'])
        intent_content = []
        
        for i, template in enumerate(templates[:limit]):
            keyword = keywords[i % len(keywords)] if keywords else primary_category
            
            # Generate appropriate URL based on intent
            url = self._generate_intent_url(intent, keyword, primary_category)
            
            intent_content.append({
                'item_id': f'intent_{intent}_{i}',
                'title': template.format(keyword.title()),
                'category': primary_category,
                'description': f'{intent.title()}-focused content about {keyword}',
                'search_relevance_score': 0.9,
                'source': f'intent-{intent}',
                'url': url,
                'source_name': f'{intent.title()} Resource',
                'timestamp': datetime.now().isoformat()
            })
        
        return intent_content
    
    def _generate_intent_url(self, intent, keyword, category):
        """Generate appropriate URL based on intent"""
        intent_urls = {
            'learning': {
                'technology': f'https://www.codecademy.com/learn/{keyword.replace(" ", "-")}',
                'default': f'https://www.khanacademy.org/search?page_search_query={keyword.replace(" ", "+")}'
            },
            'shopping': {
                'default': f'https://www.amazon.com/s?k={keyword.replace(" ", "+")}'
            },
            'trending': {
                'default': f'https://trends.google.com/trends/explore?q={keyword.replace(" ", "+")}'
            },
            'research': {
                'default': f'https://scholar.google.com/scholar?q={keyword.replace(" ", "+")}'
            },
            'recommendation': {
                'technology': f'https://stackoverflow.com/questions/tagged/{keyword.replace(" ", "-")}',
                'entertainment': f'https://www.imdb.com/find?q={keyword.replace(" ", "+")}',
                'default': f'https://www.reddit.com/search/?q={keyword.replace(" ", "+")}'
            }
        }
        
        intent_mapping = intent_urls.get(intent, intent_urls['recommendation'])
        return intent_mapping.get(category, intent_mapping.get('default', 
            f'https://www.google.com/search?q={keyword.replace(" ", "+")}'))
    
    def _calculate_relevance_score(self, item, search_analysis):
        """Calculate relevance score for recommendations"""
        score = 0.5  # Base score
        
        # Keyword matching
        item_text = f"{item.get('title', '')} {item.get('description', '')}".lower()
        for keyword in search_analysis['keywords']:
            if keyword in item_text:
                score += 0.2
        
        # Category matching
        if item.get('category') == search_analysis['primary_category']:
            score += 0.3
        elif item.get('category') in search_analysis['categories']:
            score += 0.1
        
        return min(score, 1.0)
    
    def _generate_query_recommendations(self, query, keywords, intent, limit):
        """Generate recommendations specifically for the search query"""
        recommendations = []
        
        # Intent-based templates
        intent_templates = {
            'learning': [
                f'How to Learn {query.title()}',
                f'{query.title()} Tutorial for Beginners',
                f'Complete {query.title()} Guide',
                f'{query.title()} Step-by-Step Course',
                f'Master {query.title()} Skills'
            ],
            'recommendation': [
                f'Best {query.title()} Recommendations',
                f'Top {query.title()} Picks 2024',
                f'Expert {query.title()} Suggestions',
                f'Recommended {query.title()} Resources',
                f'Ultimate {query.title()} List'
            ],
            'shopping': [
                f'Best {query.title()} to Buy',
                f'{query.title()} Deals and Offers',
                f'Where to Buy {query.title()}',
                f'{query.title()} Price Comparison',
                f'Cheap {query.title()} Options'
            ],
            'trending': [
                f'Trending {query.title()} Topics',
                f'Latest {query.title()} News',
                f'Popular {query.title()} Content',
                f'What\'s Hot in {query.title()}',
                f'{query.title()} Viral Content'
            ],
            'research': [
                f'{query.title()} Reviews and Analysis',
                f'{query.title()} Comparison Guide',
                f'{query.title()} Pros and Cons',
                f'Expert {query.title()} Opinions',
                f'{query.title()} Research Papers'
            ],
            'general': [
                f'Everything About {query.title()}',
                f'{query.title()} Complete Guide',
                f'{query.title()} Tips and Tricks',
                f'{query.title()} Best Practices',
                f'Advanced {query.title()} Techniques'
            ]
        }
        
        templates = intent_templates.get(intent, intent_templates['general'])
        
        for i, title in enumerate(templates[:limit]):
            url = self._generate_query_url(query, intent)
            
            recommendations.append({
                'item_id': f'query_rec_{i}',
                'title': title,
                'category': 'query-based',
                'description': f'Personalized content about {query} based on your search intent',
                'search_relevance_score': 0.95 - (i * 0.05),
                'source': f'query-{intent}',
                'url': url,
                'source_name': f'{query.title()} Resource',
                'timestamp': datetime.now().isoformat()
            })
        
        return recommendations
    
    def _generate_query_trending(self, query, keywords, hours, limit):
        """Generate trending content specifically for the search query"""
        trending = []
        
        # Query-specific trending templates
        trending_templates = [
            f'Trending: {query.title()} News',
            f'Latest {query.title()} Updates',
            f'Breaking: {query.title()} Developments',
            f'Viral {query.title()} Content',
            f'Popular {query.title()} Discussions',
            f'{query.title()} Social Media Buzz',
            f'Hot {query.title()} Topics',
            f'{query.title()} Community Trends',
            f'Emerging {query.title()} Trends',
            f'{query.title()} Industry News'
        ]
        
        for i, title in enumerate(trending_templates[:limit]):
            # Generate trending-specific URLs
            trending_url = f'https://trends.google.com/trends/explore?q={query.replace(" ", "+")}'
            if 'news' in title.lower():
                trending_url = f'https://news.google.com/search?q={query.replace(" ", "+")}'
            elif 'social' in title.lower():
                trending_url = f'https://twitter.com/search?q={query.replace(" ", "+")}'
            elif 'reddit' in title.lower() or 'discussion' in title.lower():
                trending_url = f'https://www.reddit.com/search/?q={query.replace(" ", "+")}'
            
            trending.append({
                'item_id': f'query_trending_{i}',
                'title': title,
                'category': 'query-trending',
                'description': f'Real-time trending content about {query}',
                'trend_score': 100 - (i * 5),
                'source': 'query-trending',
                'url': trending_url,
                'source_name': 'Trending Source',
                'timestamp': datetime.now().isoformat()
            })
        
        return trending
    
    def _generate_query_url(self, query, intent):
        """Generate appropriate URL for the query and intent"""
        intent_urls = {
            'learning': f'https://www.coursera.org/search?query={query.replace(" ", "+")}',
            'shopping': f'https://www.amazon.com/s?k={query.replace(" ", "+")}',
            'trending': f'https://trends.google.com/trends/explore?q={query.replace(" ", "+")}',
            'research': f'https://scholar.google.com/scholar?q={query.replace(" ", "+")}',
            'recommendation': f'https://www.reddit.com/search/?q={query.replace(" ", "+")}+recommendations',
            'general': f'https://www.google.com/search?q={query.replace(" ", "+")}'}
        
        return intent_urls.get(intent, intent_urls['general'])
    
    def _calculate_query_relevance(self, item, query, keywords):
        """Calculate relevance score based purely on query matching"""
        score = 0.3  # Base score
        
        item_text = f"{item.get('title', '')} {item.get('description', '')}".lower()
        query_lower = query.lower()
        
        # Direct query matching (highest weight)
        if query_lower in item_text:
            score += 0.5
        
        # Keyword matching
        for keyword in keywords:
            if keyword in item_text:
                score += 0.1
        
        # Partial word matching
        query_words = query_lower.split()
        for word in query_words:
            if len(word) > 3 and word in item_text:
                score += 0.05
        
        return min(score, 1.0)
    
    def get_search_suggestions(self, partial_query, limit=5):
        """Get search suggestions for autocomplete"""
        suggestions = []
        
        # Popular search templates
        templates = [
            "best {} 2024",
            "how to learn {}",
            "{} tutorial",
            "{} vs alternatives",
            "latest {} trends",
            "{} for beginners",
            "top {} tools",
            "{} reviews"
        ]
        
        # Category-based suggestions
        category_suggestions = {
            'tech': ['python programming', 'web development', 'machine learning', 'javascript'],
            'entertainment': ['netflix shows', 'latest movies', 'streaming services', 'gaming'],
            'shopping': ['best deals', 'product reviews', 'electronics', 'gadgets'],
            'education': ['online courses', 'tutorials', 'certifications', 'learning'],
            'health': ['fitness tips', 'nutrition', 'workout plans', 'wellness'],
            'travel': ['destinations', 'travel guides', 'hotels', 'flights']
        }
        
        # Generate suggestions based on partial query
        if len(partial_query) > 2:
            # Template-based suggestions
            for template in templates[:3]:
                suggestions.append(template.format(partial_query))
            
            # Category-based suggestions
            for category, items in category_suggestions.items():
                for item in items:
                    if partial_query.lower() in item or item in partial_query.lower():
                        suggestions.append(f"{partial_query} {item}")
        
        return suggestions[:limit]
