from flask import Flask, request, jsonify, render_template
from enhanced_engine import EnhancedRecommendationEngine
from datetime import datetime
import json

app = Flask(__name__)
engine = EnhancedRecommendationEngine()

@app.route('/')
def home():
    return render_template('dynamic_index.html')

@app.route('/users', methods=['POST'])
def create_user():
    try:
        data = request.json
        engine.add_user(data['user_id'], data.get('preferences'))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/items', methods=['POST'])
def create_item():
    try:
        data = request.json
        engine.add_item(
            data['item_id'], 
            data['title'], 
            data['category'], 
            data['description'],
            data.get('features')
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/interactions', methods=['POST'])
def record_interaction():
    try:
        data = request.json
        engine.record_interaction(
            data['user_id'],
            data['item_id'],
            data.get('interaction_type', 'view'),
            data.get('rating')
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/recommendations/<user_id>')
def get_recommendations(user_id):
    try:
        limit = request.args.get('limit', 10, type=int)
        use_search_history = request.args.get('search_based', 'false').lower() == 'true'
        search_query = request.args.get('query', '').strip()
        
        print(f"Getting recommendations for user: {user_id}, search_based: {use_search_history}, query: {search_query}, limit: {limit}")
        
        if use_search_history:
            recommendations = engine.get_search_powered_recommendations(user_id, limit, search_query)
        else:
            recommendations = engine.get_standard_recommendations(user_id, limit)
        
        print(f"Found {len(recommendations)} recommendations")
        
        # Ensure JSON serializable
        clean_recommendations = []
        for rec in recommendations:
            clean_rec = {}
            for key, value in rec.items():
                if hasattr(value, 'isoformat'):
                    clean_rec[key] = value.isoformat()
                elif isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                    clean_rec[key] = value
                else:
                    clean_rec[key] = str(value)
            clean_recommendations.append(clean_rec)
        
        return jsonify(clean_recommendations)
    except Exception as e:
        print(f"Recommendations error: {e}")
        import traceback
        traceback.print_exc()
        # Return fallback recommendations instead of error
        fallback = [
            {
                'item_id': 'error_fallback',
                'title': 'Recommendation System',
                'category': 'system',
                'description': 'Our recommendation system is learning about your preferences',
                'source': 'fallback'
            }
        ]
        return jsonify(fallback)

@app.route('/trending')
def get_trending():
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 10, type=int)
        search_query = request.args.get('query', '').strip()
        
        print(f"Getting trending content: hours={hours}, limit={limit}, query={search_query}")
        
        if not search_query:
            return jsonify([{
                'item_id': 'no_query',
                'title': 'No Search Query Provided',
                'category': 'system',
                'description': 'Please enter a search query to get relevant trending content',
                'trend_score': 0,
                'source': 'system'
            }])
        
        trending = engine.get_trending_content(hours, limit, '', search_query)
        
        print(f"Found {len(trending)} trending items")
        
        # Ensure JSON serializable
        clean_trending = []
        for item in trending:
            clean_item = {}
            for key, value in item.items():
                if hasattr(value, 'isoformat'):
                    clean_item[key] = value.isoformat()
                elif isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                    clean_item[key] = value
                else:
                    clean_item[key] = str(value)
            clean_trending.append(clean_item)
        
        return jsonify(clean_trending)
    except Exception as e:
        print(f"Trending error: {e}")
        import traceback
        traceback.print_exc()
        # Return fallback trending instead of error
        fallback = [
            {
                'item_id': 'trending_error_fallback',
                'title': 'Query-Based Trending Content',
                'category': 'system',
                'description': 'Fetching trending content based on your search query',
                'trend_score': 100,
                'source': 'fallback'
            }
        ]
        return jsonify(fallback)

@app.route('/search-history', methods=['POST'])
def update_search_history():
    try:
        data = request.json
        user_id = data.get('user_id')
        browser_history = data.get('history', [])
        
        if not user_id or not browser_history:
            return jsonify({"error": "Missing user_id or history"}), 400
        
        search_intent = engine.update_search_profile(user_id, browser_history)
        return jsonify({
            "status": "Search profile updated",
            "search_intent": search_intent
        })
    except Exception as e:
        print(f"Search history error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/search-suggestions')
def get_search_suggestions():
    try:
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 5, type=int)
        
        if not query:
            return jsonify([])
        
        suggestions = engine.get_search_suggestions(query, limit)
        return jsonify(suggestions)
    except Exception as e:
        print(f"Search suggestions error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def get_status():
    try:
        return jsonify(engine.get_status_info())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sample-data', methods=['POST'])
def load_sample_data():
    try:
        # Clear existing data
        if engine.base_engine.use_memory:
            engine.base_engine.memory_users.clear()
            engine.base_engine.memory_items.clear()
            engine.base_engine.memory_interactions.clear()
        
        # Sample items
        items = [
            {"item_id": "tech_1", "title": "Python Machine Learning", "category": "technology", "description": "Advanced ML techniques with Python"},
            {"item_id": "ent_1", "title": "Sci-Fi Movie Collection", "category": "entertainment", "description": "Best science fiction movies of 2024"},
            {"item_id": "shop_1", "title": "Wireless Headphones Pro", "category": "shopping", "description": "Premium noise-canceling headphones"},
            {"item_id": "edu_1", "title": "Web Development Course", "category": "education", "description": "Complete full-stack development course"},
            {"item_id": "health_1", "title": "Fitness Tracker Guide", "category": "health", "description": "Best fitness trackers and health tips"},
            {"item_id": "travel_1", "title": "Europe Travel Guide", "category": "travel", "description": "Complete guide to European destinations"}
        ]
        
        for item in items:
            engine.add_item(**item)
        
        # Sample users
        users = ["alice", "bob", "charlie", "demo", "test_user"]
        for user_id in users:
            engine.add_user(user_id)
        
        # Sample interactions
        interactions = [
            ("alice", "tech_1", "view"), ("alice", "edu_1", "like"),
            ("bob", "shop_1", "purchase"), ("bob", "ent_1", "view"),
            ("charlie", "health_1", "like"), ("charlie", "travel_1", "view"),
            ("demo", "tech_1", "view"), ("demo", "shop_1", "like")
        ]
        
        for user_id, item_id, interaction_type in interactions:
            engine.record_interaction(user_id, item_id, interaction_type)
        
        # Sample search histories
        sample_histories = {
            "alice": [
                {"url": "https://google.com/search?q=python+machine+learning+tutorial", "title": "Python ML", "timestamp": datetime.now().isoformat()},
                {"url": "https://google.com/search?q=web+development+course", "title": "Web Dev", "timestamp": datetime.now().isoformat()},
                {"url": "https://google.com/search?q=artificial+intelligence+trends", "title": "AI Trends", "timestamp": datetime.now().isoformat()}
            ],
            "bob": [
                {"url": "https://google.com/search?q=best+wireless+headphones+2024", "title": "Headphones", "timestamp": datetime.now().isoformat()},
                {"url": "https://google.com/search?q=netflix+sci+fi+movies", "title": "Sci-fi Movies", "timestamp": datetime.now().isoformat()},
                {"url": "https://google.com/search?q=electronics+deals+online", "title": "Electronics", "timestamp": datetime.now().isoformat()}
            ],
            "demo": [
                {"url": "https://google.com/search?q=travel+destinations+2024", "title": "Travel", "timestamp": datetime.now().isoformat()},
                {"url": "https://google.com/search?q=fitness+tracker+reviews", "title": "Fitness", "timestamp": datetime.now().isoformat()}
            ]
        }
        
        for user_id, history in sample_histories.items():
            engine.update_search_profile(user_id, history)
        
        return jsonify({"status": "Enhanced sample data loaded successfully!"})
    
    except Exception as e:
        print(f"Sample data error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Enhanced Real-Time Recommendation Engine...")
    print(f"Database: {engine.get_database_status()}")
    print("Real-time content fetching: Enabled")
    print("Google Search Integration: Enhanced")
    print("Server running at: http://localhost:5001")
    app.run(debug=True, port=5001, host='0.0.0.0')
