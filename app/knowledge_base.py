import os
import pickle
import faiss
import motor.motor_asyncio
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

# --- LAZY INITIALIZATION OF DATABASE CLIENT ---
@st.cache_resource
def get_db_client():
    """
    Creates and caches a MongoDB client. This function is only run once
    and the client is reused across the app.
    """
    print("--- Creating new MongoDB client connection ---")
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, server_api=ServerApi('1'))
        # You can uncomment the line below to verify the connection on startup
        # client.admin.command('ping')
        print("✅ Successfully connected to MongoDB.")
        return client
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return None

# --- FAISS and Knowledge Base Loading ---
try:
    faiss_index = faiss.read_index("faiss_index.bin")
    with open("data.pkl", "rb") as f:
        knowledge_base_texts = pickle.load(f)
    print("✅ Successfully loaded FAISS index and knowledge base texts.")
except FileNotFoundError as e:
    print(f"❌ Error loading knowledge base files: {e}")
    print("Ensure 'faiss_index.bin' and 'data.pkl' are in the project's root directory.")
    faiss_index, knowledge_base_texts = None, None

# ==============================================================================
# 1. Point of Interest (POI) Functions
# ==============================================================================

async def get_poi_by_id(poi_id: str) -> Dict[str, Any]:
    """Fetches a single Point of Interest document from the database by its _id."""
    client = get_db_client()
    if client is None:
        return None
    return await client[DB_NAME][POI_COLLECTION_NAME].find_one({"_id": poi_id})

async def get_all_pois(tags: List[str] = None, budget: str = None) -> List[Dict[str, Any]]:
    """
    Fetches all POIs from the database, with optional filtering by tags and budget.
    """
    client = get_db_client()
    if client is None:
        return []
    
    query = {}
    # Add filters to the query if they are provided
    if tags:
        # Find documents where the tags array contains any of the selected tags
        query["tags"] = {"$in": tags}
    if budget and budget != "any":
        query["budget_level"] = budget

    # Find documents matching the query, but only return the 'name' and '_id' fields for efficiency
    cursor = client[DB_NAME][POI_COLLECTION_NAME].find(query, {"name": 1, "_id": 1})
    
    # Convert the cursor to a list of all matching documents
    pois_list = await cursor.to_list(length=None)
    return pois_list

async def get_unique_tags() -> List[str]:
    """Fetches all unique tags from the POI collection."""
    client = get_db_client()
    if client is None:
        return []
    
    # The 'distinct' method is highly efficient for getting unique values for a field
    unique_tags = await client[DB_NAME][POI_COLLECTION_NAME].distinct("tags")
    return unique_tags

# ==============================================================================
# 2. Vector Search / RAG Retrieval Functions
# ==============================================================================

def search_knowledge_base(query_embedding, k: int = 5) -> str:
    """
    Searches the FAISS index for the most relevant text chunks based on a query embedding.
    """
    if not faiss_index or not knowledge_base_texts:
        return "Knowledge base is not available."

    distances, indices = faiss_index.search(query_embedding, k)
    retrieved_chunks = [knowledge_base_texts[i] for i in indices[0]]
    context = "\n\n---\n\n".join(retrieved_chunks)
    return context

# ==============================================================================
# 3. User Preference Functions (Memory)
# ==============================================================================

async def get_user_preferences(user_id: str) -> Dict[str, List[str]]:
    """Fetches a user's preference profile from the 'users' collection."""
    client = get_db_client()
    if client is None:
        return {"likes": [], "dislikes": []}
        
    user_profile = await client[DB_NAME][USER_COLLECTION_NAME].find_one({"_id": user_id})
    if user_profile:
        return user_profile.get("preferences", {"likes": [], "dislikes": []})
    
    return {"likes": [], "dislikes": []}

async def update_user_preferences(user_id: str, new_preferences: Dict[str, List[str]]):
    """Updates (or inserts) a user's preference profile in the 'users' collection."""
    client = get_db_client()
    if client is None:
        print("❌ Cannot update preferences: Database client not available.")
        return

    await client[DB_NAME][USER_COLLECTION_NAME].update_one(
        {"_id": user_id},
        {"$set": {"preferences": new_preferences}},
        upsert=True
    )
    print(f"✅ Preferences updated for user: {user_id}")
    
