import os
import pickle
import faiss
from pymongo import MongoClient  
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from typing import List, Dict, Any
import streamlit as st

# --- Load Environment Variables ---
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "Hackathon_Project"
POI_COLLECTION_NAME = "NSK_AI"
USER_COLLECTION_NAME = "users"

# --- LAZY INITIALIZATION OF SYNC DATABASE CLIENT ---
@st.cache_resource
def get_db_client():
    """
    Creates and caches a SYNCHRONOUS MongoDB client using pymongo.
    This avoids all asyncio event loop issues.
    """
    print("--- Creating new SYNC MongoDB client connection ---")
    try:
        # <--- CHANGE: Use the synchronous MongoClient
        client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
        # Verify connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB (sync).")
        return client
    except Exception as e:
        print(f"❌ Error connecting to MongoDB (sync): {e}")
        return None

# --- FAISS and Knowledge Base Loading (No changes needed) ---
try:
    faiss_index = faiss.read_index("faiss_index.bin")
    with open("data.pkl", "rb") as f:
        knowledge_base_texts = pickle.load(f)
    print("✅ Successfully loaded FAISS index and knowledge base texts.")
except FileNotFoundError as e:
    print(f"❌ Error loading knowledge base files: {e}")
    faiss_index, knowledge_base_texts = None, None

# ==============================================================================
# 1. Point of Interest (POI) Functions (Now Synchronous)
# ==============================================================================

# <--- CHANGE: Removed 'async'
def get_poi_by_id(poi_id: str) -> Dict[str, Any]:
    """Fetches a single POI from the database by its _id."""
    client = get_db_client()
    if client is None: return None
    db = client[DB_NAME]
    # <--- CHANGE: Removed 'await'
    return db[POI_COLLECTION_NAME].find_one({"_id": poi_id})

# <--- CHANGE: Removed 'async'
def get_all_pois(tags: List[str] = None, budget: str = None) -> List[Dict[str, Any]]:
    """Fetches all POIs from the database, with optional filtering."""
    client = get_db_client()
    if client is None: return []
    db = client[DB_NAME]
    
    query = {}
    if tags:
        query["tags"] = {"$in": tags}
    if budget and budget != "any":
        query["budget_level"] = budget

    # <--- CHANGE: Removed 'await', find returns a cursor directly
    cursor = db[POI_COLLECTION_NAME].find(query, {"name": 1, "_id": 1})
    # Convert cursor to list
    return list(cursor)

# <--- CHANGE: Removed 'async'
def get_unique_tags() -> List[str]:
    """Fetches all unique tags from the POI collection."""
    client = get_db_client()
    if client is None: return []
    db = client[DB_NAME]
    # <--- CHANGE: Removed 'await'
    return db[POI_COLLECTION_NAME].distinct("tags")

# ==============================================================================
# 2. Vector Search / RAG Retrieval Functions (No changes needed)
# ==============================================================================
def search_knowledge_base(query_embedding, k: int = 5) -> str:
    # This function was already synchronous, so no changes are needed.
    if not faiss_index or not knowledge_base_texts:
        return "Knowledge base is not available."
    distances, indices = faiss_index.search(query_embedding, k)
    retrieved_chunks = [knowledge_base_texts[i] for i in indices[0]]
    context = "\n\n---\n\n".join(retrieved_chunks)
    return context

# ==============================================================================
# 3. User Preference Functions (Now Synchronous)
# ==============================================================================

# <--- CHANGE: Removed 'async'
def get_user_preferences(user_id: str) -> Dict[str, List[str]]:
    """Fetches a user's preference profile."""
    client = get_db_client()
    if client is None: return {"likes": [], "dislikes": []}
    db = client[DB_NAME]
    # <--- CHANGE: Removed 'await'
    user_profile = db[USER_COLLECTION_NAME].find_one({"_id": user_id})
    if user_profile:
        return user_profile.get("preferences", {"likes": [], "dislikes": []})
    return {"likes": [], "dislikes": []}

# <--- CHANGE: Removed 'async'
def update_user_preferences(user_id: str, new_preferences: Dict[str, List[str]]):
    """Updates (or inserts) a user's preference profile."""
    client = get_db_client()
    if client is None:
        print("❌ Cannot update preferences: Database client not available.")
        return
    db = client[DB_NAME]
    # <--- CHANGE: Removed 'await'
    db[USER_COLLECTION_NAME].update_one(
        {"_id": user_id},
        {"$set": {"preferences": new_preferences}},
        upsert=True
    )
    print(f"✅ Preferences updated for user: {user_id}")
    
