# app/knowledge_base.py

import os
import pickle
import faiss
from pymongo import MongoClient
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
    print("--- Creating new MongoDB client connection ---")
    try:
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB.")
        return client
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return None

@st.cache_data
def load_knowledge_base_files():
    print("--- Loading FAISS index and data.pkl from disk... ---")
    try:
        faiss_index = faiss.read_index("faiss_index.bin")
        with open("data.pkl", "rb") as f:
            knowledge_base_texts = pickle.load(f)
        print("✅ Successfully loaded FAISS index and knowledge base texts.")
        return faiss_index, knowledge_base_texts
    except FileNotFoundError as e:
        print(f"❌ Error loading knowledge base files: {e}")
        return None, None

# --- POI & USER DATA FUNCTIONS ---

def get_pois_by_city(city: str) -> List[Dict[str, Any]]:
    client = get_db_client()
    if client is None: return []
    query = {"city": city}
    cursor = client[DB_NAME][POI_COLLECTION_NAME].find(query, {"name": 1, "_id": 1})
    return list(cursor)

def get_poi_by_id(poi_id: str) -> Dict[str, Any]:
    client = get_db_client()
    if client is None: return None
    return client[DB_NAME][POI_COLLECTION_NAME].find_one({"_id": poi_id})

def get_user_preferences(user_id: str) -> Dict[str, List[str]]:
    client = get_db_client()
    if client is None: return {"likes": [], "dislikes": []}
    user_profile = client[DB_NAME][USER_COLLECTION_NAME].find_one({"_id": user_id})
    return user_profile.get("preferences", {"likes": [], "dislikes": []}) if user_profile else {"likes": [], "dislikes": []}

# --- RAG RETRIEVAL FUNCTION (SIMPLIFIED) ---

def search_knowledge_base(query_embedding, k: int = 5) -> str:
    """
    Searches the FAISS index for the most relevant text chunks.
    It now expects a correctly shaped 2D NumPy array.
    """
    faiss_index, knowledge_base_texts = load_knowledge_base_files()
    if not faiss_index or not knowledge_base_texts:
        return "Knowledge base is not available."

    # THE FIX: The query_embedding is now passed directly to FAISS
    distances, indices = faiss_index.search(query_embedding, k)
    
    retrieved_chunks = [knowledge_base_texts[i] for i in indices[0]]
    context = "\n\n---\n\n".join(retrieved_chunks)
    return context
    
