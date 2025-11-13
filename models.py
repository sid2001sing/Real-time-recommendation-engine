from pymongo import MongoClient
from datetime import datetime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
from dotenv import load_dotenv

load_dotenv()

class RecommendationEngine:
    def __init__(self):
        try:
            self.client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[os.getenv('DATABASE_NAME')]
            self.users = self.db.users
            self.items = self.db.items
            self.interactions = self.db.interactions
            self._setup_indexes()
            self.use_memory = False
            print("Connected to MongoDB successfully")
        except Exception as e:
            print(f"MongoDB connection failed: {str(e)}")
            print("Using in-memory storage instead")
            self.use_memory = True
            self.memory_users = {}
            self.memory_items = {}
            self.memory_interactions = []
    
    def get_status(self):
        return "MongoDB" if not self.use_memory else "In-Memory"
    
    def _setup_indexes(self):
        try:
            self.users.create_index("user_id")
            self.items.create_index("item_id")
            self.interactions.create_index([("user_id", 1), ("timestamp", -1)])
            self.interactions.create_index("item_id")
        except Exception as e:
            print(f"Index creation warning: {e}")
    
    def add_user(self, user_id, preferences=None):
        user = {
            "user_id": user_id,
            "preferences": preferences or [],
            "created_at": datetime.utcnow()
        }
        if self.use_memory:
            self.memory_users[user_id] = user
        else:
            self.users.update_one({"user_id": user_id}, {"$set": user}, upsert=True)
    
    def add_item(self, item_id, title, category, description, features=None):
        item = {
            "item_id": item_id,
            "title": title,
            "category": category,
            "description": description,
            "features": features or [],
            "created_at": datetime.utcnow()
        }
        if self.use_memory:
            self.memory_items[item_id] = item
        else:
            self.items.update_one({"item_id": item_id}, {"$set": item}, upsert=True)
    
    def record_interaction(self, user_id, item_id, interaction_type="view", rating=None):
        interaction = {
            "user_id": user_id,
            "item_id": item_id,
            "interaction_type": interaction_type,
            "rating": rating,
            "timestamp": datetime.utcnow()
        }
        if self.use_memory:
            self.memory_interactions.append(interaction)
        else:
            self.interactions.insert_one(interaction)
    
    def get_user_recommendations(self, user_id, limit=10):
        if self.use_memory:
            user_interactions = [i for i in self.memory_interactions if i["user_id"] == user_id][-50:]
            if not user_interactions:
                return list(self.memory_items.values())[:limit]
            interacted_items = [i["item_id"] for i in user_interactions]
            candidates = [item for item_id, item in self.memory_items.items() if item_id not in interacted_items]
            return candidates[:limit]
        else:
            user_interactions = list(self.interactions.find(
                {"user_id": user_id}
            ).sort("timestamp", -1).limit(50))
            
            if not user_interactions:
                return self._get_popular_items(limit)
            
            interacted_items = [i["item_id"] for i in user_interactions]
            
            pipeline = [
                {"$match": {"item_id": {"$nin": interacted_items}}},
                {"$lookup": {
                    "from": "interactions",
                    "localField": "item_id",
                    "foreignField": "item_id",
                    "as": "item_interactions"
                }},
                {"$addFields": {
                    "popularity_score": {"$size": "$item_interactions"}
                }},
                {"$sort": {"popularity_score": -1}},
                {"$limit": limit * 2}
            ]
            
            candidates = list(self.items.aggregate(pipeline))
            
            if len(candidates) > limit:
                candidates = self._rank_by_similarity(user_interactions, candidates)
            
            return candidates[:limit]
    
    def _rank_by_similarity(self, user_interactions, candidates):
        # Get user's preferred items
        user_item_ids = [i["item_id"] for i in user_interactions[-10:]]
        user_items = list(self.items.find({"item_id": {"$in": user_item_ids}}))
        
        if not user_items:
            return candidates
        
        # Create feature vectors from descriptions
        all_items = user_items + candidates
        descriptions = [item.get("description", "") for item in all_items]
        
        vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        vectors = vectorizer.fit_transform(descriptions)
        
        # Calculate similarity
        user_vector = np.mean(vectors[:len(user_items)].toarray(), axis=0)
        candidate_vectors = vectors[len(user_items):].toarray()
        
        similarities = cosine_similarity([user_vector], candidate_vectors)[0]
        
        # Sort candidates by similarity
        for i, candidate in enumerate(candidates):
            candidate["similarity_score"] = similarities[i]
        
        return sorted(candidates, key=lambda x: x.get("similarity_score", 0), reverse=True)
    
    def _get_popular_items(self, limit):
        if self.use_memory:
            return list(self.memory_items.values())[:limit]
        else:
            pipeline = [
                {"$lookup": {
                    "from": "interactions",
                    "localField": "item_id",
                    "foreignField": "item_id",
                    "as": "interactions"
                }},
                {"$addFields": {
                    "popularity": {"$size": "$interactions"}
                }},
                {"$sort": {"popularity": -1}},
                {"$limit": limit}
            ]
            return list(self.items.aggregate(pipeline))
    
    def get_trending_items(self, hours=24, limit=10):
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        if self.use_memory:
            recent_interactions = [i for i in self.memory_interactions if i["timestamp"] >= cutoff]
            item_counts = {}
            for interaction in recent_interactions:
                item_id = interaction["item_id"]
                if item_id not in item_counts:
                    item_counts[item_id] = {"count": 0, "users": set()}
                item_counts[item_id]["count"] += 1
                item_counts[item_id]["users"].add(interaction["user_id"])
            
            trending = []
            for item_id, data in item_counts.items():
                if item_id in self.memory_items:
                    trending.append({
                        "_id": item_id,
                        "trend_score": data["count"] * len(data["users"]),
                        "item_details": self.memory_items[item_id]
                    })
            
            return sorted(trending, key=lambda x: x["trend_score"], reverse=True)[:limit]
        else:
            pipeline = [
                {"$match": {"timestamp": {"$gte": cutoff}}},
                {"$group": {
                    "_id": "$item_id",
                    "interaction_count": {"$sum": 1},
                    "unique_users": {"$addToSet": "$user_id"}
                }},
                {"$addFields": {
                    "trend_score": {"$multiply": ["$interaction_count", {"$size": "$unique_users"}]}
                }},
                {"$sort": {"trend_score": -1}},
                {"$limit": limit},
                {"$lookup": {
                    "from": "items",
                    "localField": "_id",
                    "foreignField": "item_id",
                    "as": "item_details"
                }},
                {"$unwind": "$item_details"}
            ]
            
            return list(self.interactions.aggregate(pipeline))
