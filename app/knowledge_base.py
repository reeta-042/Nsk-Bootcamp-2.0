import os
import pickle
import faiss
import motor.motor_asyncio
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from typing import List, Dict, Any
import streamlit as st # Import Streamlit

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
        # Optional: Ping the server to confirm a successful connection.
        # client.admin.command('ping') 
        print("✅ Successfully connected to MongoDB.")
        return client
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        # Return None or raise an exception if the connection fails
        return None

# --- FAISS and Knowledge Base Loading (This can remain as is) ---
try:
    faiss_index = faiss.read_index("faiss_index.bin")
    with open("data.pkl", "rb") as f:
        knowledge_base_texts = pickle.load(f)
    print("✅ Successfully loaded FAISS index and knowledge base texts.")
except FileNotFoundError as e:
    print(f"❌ Error loading knowledge base files: {e}")
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

# ==============================================================================
# 2. Vector Search / RAG Retrieval Functions (No changes needed here)
# ==============================================================================
def search_knowledge_base(query_embedding, k: int = 5) -> str:
    # ... (code is correct)
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

