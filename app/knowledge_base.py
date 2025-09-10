import os
import pickle
import faiss
from pymongo import MongoClient
from dotenv import load_dotenv
from typing import List, Dict, Any
import streamlit as st

# --- Load Environment Variables ---
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "Hackathon_Project"
POI_COLLECTION_NAME = "NSK_AI"
USER_COLLECTION_NAME = "users"

# --- LAZY INITIALIZATION OF DATABASE CLIENT (Synchronous) ---
@st.cache_resource
def get_db_client():
    """Creates and caches a synchronous MongoDB client."""
    print("--- Creating new MongoDB client connection ---")
    try:
        client = MongoClient(MONGO_URI)
        client.admin.command('ping') # Check the connection
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
    faiss_index, knowledge_base_texts = None, None

# ==============================================================================
# Point of Interest (POI) Functions
# ==============================================================================

def get_poi_by_id(poi_id: str) -> Dict[str, Any]:
    """Fetches a single POI document from the database by its _id."""
    client = get_db_client()
    if client is None: return None
    return client[DB_NAME][POI_COLLECTION_NAME].find_one({"_id": poi_id})

# --- THIS IS THE MISSING FUNCTION ---
def get_pois_by_city(city: str) -> Dict[str, str]:
    """Fetches all POIs for a specific city and formats them for a dropdown."""
    client = get_db_client()
    if client is None: return {}
    
    query = {"city": city}
    cursor = client[DB_NAME][POI_COLLECTION_NAME].find(query, {"name": 1, "_id": 1})
    
    # Create a dictionary like {"POI Name": "poi_id"}
    poi_choices = {poi["name"]: poi["_id"] for poi in cursor}
    return poi_choices
# --- END OF FIX ---

# ==============================================================================
# Vector Search / RAG Retrieval Functions
# ==============================================================================
def search_knowledge_base(query_embedding, k: int = 5) -> str:
    if not faiss_index or not knowledge_base_texts:
        return "Knowledge base is not available."
    distances, indices = faiss_index.search(query_embedding, k)
    retrieved_chunks = [knowledge_base_texts[i] for i in indices[0]]
    context = "\n\n---\n\n".join(retrieved_chunks)
    return context

# ==============================================================================
# User Preference Functions
# ==============================================================================
def get_user_preferences(user_id: str) -> Dict[str, List[str]]:
    client = get_db_client()
    if client is None: return {"likes": [], "dislikes": []}
    user_profile = client[DB_NAME][USER_COLLECTION_NAME].find_one({"_id": user_id})
    return user_profile.get("preferences", {"likes": [], "dislikes": []}) if user_profile else {"likes": [], "dislikes": []}
    
