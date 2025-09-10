import os
import pickle
import faiss
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from typing import List, Dict, Any
import streamlit as st

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "Hackathon_Project"
POI_COLLECTION_NAME = "NSK_AI"
USER_COLLECTION_NAME = "users"

@st.cache_resource
def get_db_client():
    print("--- Creating new SYNC MongoDB client connection ---")
    try:
        client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB (sync).")
        return client
    except Exception as e:
        print(f"❌ Error connecting to MongoDB (sync): {e}")
        return None

try:
    faiss_index = faiss.read_index("faiss_index.bin")
    with open("data.pkl", "rb") as f:
        knowledge_base_texts = pickle.load(f)
    print("✅ Successfully loaded FAISS index and knowledge base texts.")
except FileNotFoundError as e:
    print(f"❌ Error loading knowledge base files: {e}")
    faiss_index, knowledge_base_texts = None, None

def get_poi_by_id(poi_id: str) -> Dict[str, Any]:
    client = get_db_client()
    if client is None: return None
    db = client[DB_NAME]
    return db[POI_COLLECTION_NAME].find_one({"_id": poi_id})

def get_all_pois(tags: List[str] = None, budget: str = None) -> List[Dict[str, Any]]:
    client = get_db_client()
    if client is None: return []
    db = client[DB_NAME]
    query = {}
    if tags: query["tags"] = {"$in": tags}
    if budget and budget != "any": query["budget_level"] = budget
    cursor = db[POI_COLLECTION_NAME].find(query, {"name": 1, "_id": 1})
    return list(cursor)

def get_unique_tags() -> List[str]:
    client = get_db_client()
    if client is None: return []
    db = client[DB_NAME]
    return db[POI_COLLECTION_NAME].distinct("tags")

def search_knowledge_base(query_embedding, k: int = 5) -> str:
    if not faiss_index or not knowledge_base_texts: return "Knowledge base is not available."
    distances, indices = faiss_index.search(query_embedding, k)
    retrieved_chunks = [knowledge_base_texts[i] for i in indices[0]]
    context = "\n\n---\n\n".join(retrieved_chunks)
    return context

def get_user_preferences(user_id: str) -> Dict[str, List[str]]:
    client = get_db_client()
    if client is None: return {"likes": [], "dislikes": []}
    db = client[DB_NAME]
    user_profile = db[USER_COLLECTION_NAME].find_one({"_id": user_id})
    if user_profile: return user_profile.get("preferences", {"likes": [], "dislikes": []})
    return {"likes": [], "dislikes": []}

def update_user_preferences(user_id: str, new_preferences: Dict[str, List[str]]):
    client = get_db_client()
    if client is None: return
    db = client[DB_NAME]
    db[USER_COLLECTION_NAME].update_one({"_id": user_id}, {"$set": {"preferences": new_preferences}}, upsert=True)
    print(f"✅ Preferences updated for user: {user_id}")
    
