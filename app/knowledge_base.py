# app/knowledge_base.py

import os
from pymongo import MongoClient
from typing import List, Dict, Any
import streamlit as st
import faiss
import pickle
import numpy as np
# --- Database and FAISS Initialization ---
# Uses Streamlit's caching for efficient, one-time loading.

@st.cache_resource
def get_db_client():
    """Establishes and caches a connection to the MongoDB database."""
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    return client

@st.cache_resource
def load_faiss_index():
    """Loads the FAISS index from the specified file."""
    try:
        return faiss.read_index("faiss_index.bin")
    except Exception as e:
        st.error(f"Failed to load FAISS index: {e}")
        return None

@st.cache_resource
def load_knowledge_base_texts():
    """Loads the knowledge base text chunks from the pickle file."""
    try:
        with open("data.pkl", "rb") as f:
            return pickle.load(f)
    except Exception as e:
        st.error(f"Failed to load knowledge base texts: {e}")
        return []

# --- Point of Interest (POI) Functions ---

def get_pois_by_city(city: str, tags: List[str] = None, budget: str = None) -> List[Dict]:
    """
    Fetches POIs for a given city, with optional filtering by tags and budget.
    """
    client = get_db_client()
    db = client["Hackathon_Project"]
    
    # Base query matches the selected city
    query = {"city": city}
    
    # Add tag filter if tags are provided
    if tags:
        query["tags"] = {"$in": tags}
        
    # Add budget filter if a budget is provided and it's not 'Any'
    if budget and budget != "Any":
        query["budget_level"] = budget
        
    # Fetch matching POIs, returning only their name and ID for the dropdown
    cursor = db["NSK_AI"].find(query, {"name": 1, "_id": 1})
    return list(cursor)

def get_poi_by_id(poi_id: str) -> Dict[str, Any]:
    """Fetches a single, complete POI document by its ID."""
    client = get_db_client()
    db = client["Hackathon_Project"]
    return db["NSK_AI"].find_one({"_id": poi_id})

def get_unique_tags_by_city(city: str) -> List[str]:
    """Fetches a list of all unique tags for a given city."""
    client = get_db_client()
    db = client["Hackathon_Project"]
    return db["NSK_AI"].distinct("tags", {"city": city})

def get_unique_budgets_by_city(city: str) -> List[str]:
    """Fetches a list of all unique budget levels for a given city."""
    client = get_db_client()
    db = client["Hackathon_Project"]
    budgets = db["NSK_AI"].distinct("budget_level", {"city": city})
    # Ensure a consistent and logical order
    return sorted(budgets, key=lambda x: (x != 'free', x != 'low', x != 'medium', x != 'high'))

# --- Vector Search / RAG Functions ---

def search_knowledge_base(query_embedding: np.ndarray, k: int = 5) -> str:
    """Searches the FAISS index for the most relevant text chunks."""
    faiss_index = load_faiss_index()
    knowledge_base_texts = load_knowledge_base_texts()
    
    if faiss_index is None or not knowledge_base_texts:
        return "Knowledge base is currently unavailable."

    distances, indices = faiss_index.search(query_embedding, k)
    retrieved_chunks = [knowledge_base_texts[i] for i in indices[0]]
    context = "\n\n---\n\n".join(retrieved_chunks)
    return context

# --- User Preference Functions ---

def get_user_preferences(user_id: str) -> Dict[str, List[str]]:
    """Fetches a user's preference profile from the database."""
    client = get_db_client()
    db = client["Hackathon_Project"]
    user_profile = db["users"].find_one({"_id": user_id})
    return user_profile.get("preferences", {"likes": [], "dislikes": []}) if user_profile else {"likes": [], "dislikes": []}

def update_user_preferences(user_id: str, new_preferences: Dict[str, List[str]]):
    """Updates or inserts a user's preference profile in the database."""
    client = get_db_client()
    db = client["Hackathon_Project"]
    db["users"].update_one(
        {"_id": user_id},
        {"$set": {"preferences": new_preferences}},
        upsert=True
    )
    
