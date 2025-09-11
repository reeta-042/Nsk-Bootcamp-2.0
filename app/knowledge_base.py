# app/knowledge_base.py

import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from typing import List, Dict, Any
import streamlit as st
import faiss
import pickle
import numpy as np

# --- Database and FAISS Initialization ---

@st.cache_resource
def get_db_client():
    """
    Establishes and caches a connection to the MongoDB database.
    Includes error handling for connection failures.
    """
    try:
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            st.error("MONGO_URI environment variable not set. Please configure it.")
            return None
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        return client
    except ConnectionFailure as e:
        st.error(f"MongoDB connection failed: {e}. Please check your connection string and network access.")
        return None

@st.cache_resource
def load_faiss_index():
    """Loads the FAISS index from the specified file."""
    try:
        return faiss.read_index("faiss_index.bin")
    except Exception as e:
        st.error(f"Failed to load FAISS index from 'faiss_index.bin': {e}")
        return None

@st.cache_resource
def load_knowledge_base_texts():
    """Loads the knowledge base text chunks from the pickle file."""
    try:
        with open("data.pkl", "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        st.error("Failed to load knowledge base texts: 'data.pkl' not found.")
        return []
    except Exception as e:
        st.error(f"An error occurred while loading 'data.pkl': {e}")
        return []

# --- Point of Interest (POI) Functions ---

def get_pois_by_city(city: str, tags: List[str] = None, budget: str = None) -> List[Dict]:
    """
    Fetches POIs for a given city, with optional filtering by tags and budget.
    Returns an empty list if the database client is unavailable.
    """
    client = get_db_client()
    if not client: return []
    db = client["Hackathon_Project"]

    query = {"city": city}
    if tags:
        query["tags"] = {"$all": tags} # Use $all for more precise tag matching
    if budget and budget != "Any":
        query["budget_level"] = budget

    cursor = db["NSK_AI"].find(query, {"name": 1, "_id": 1})
    return list(cursor)

def get_poi_by_id(poi_id: str) -> Dict[str, Any]:
    """
    Fetches a single, complete POI document by its ID.
    Returns None if the database client is unavailable or POI is not found.
    """
    client = get_db_client()
    if not client: return None
    db = client["Hackathon_Project"]
    return db["NSK_AI"].find_one({"_id": poi_id})

def get_unique_tags_by_city(city: str) -> List[str]:
    """
    Fetches a list of all unique tags for a given city.
    Returns an empty list if the database client is unavailable.
    """
    client = get_db_client()
    if not client: return []
    db = client["Hackathon_Project"]
    return db["NSK_AI"].distinct("tags", {"city": city})

def get_unique_budgets_by_city(city: str) -> List[str]:
    """
    Fetches a list of all unique budget levels for a given city.
    Returns an empty list if the database client is unavailable.
    """
    client = get_db_client()
    if not client: return []
    db = client["Hackathon_Project"]
    budgets = db["NSK_AI"].distinct("budget_level", {"city": city})
    # Define a sort order to ensure consistent presentation
    sort_order = {'free': 0, 'low': 1, 'medium': 2, 'high': 3}
    return sorted(budgets, key=lambda x: sort_order.get(x, 99))

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
    """
    Fetches a user's preference profile from the database.
    Returns a default empty profile if the user is not found or DB is unavailable.
    """
    client = get_db_client()
    if not client: return {"likes": [], "dislikes": []}
    db = client["Hackathon_Project"]
    user_profile = db["users"].find_one({"_id": user_id})
    return user_profile.get("preferences", {"likes": [], "dislikes": []}) if user_profile else {"likes": [], "dislikes": []}

def update_user_preferences(user_id: str, new_preferences: Dict[str, List[str]]):
    """
    Updates or inserts a user's preference profile in the database.
    Does nothing if the database client is unavailable.
    """
    client = get_db_client()
    if not client:
        st.warning("Database connection is unavailable. Preferences not saved.")
        return
    db = client["Hackathon_Project"]
    db["users"].update_one(
        {"_id": user_id},
        {"$set": {"preferences": new_preferences}},
        upsert=True
)
    
