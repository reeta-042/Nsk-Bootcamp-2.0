import os
import pickle
import faiss
import motor.motor_asyncio
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from typing import List, Dict, Any

# --- Load Environment Variables ---
# This ensures we can securely access the MongoDB URI from a .env file
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "Hackathon_Project"
POI_COLLECTION_NAME = "NSK_AI"
USER_COLLECTION_NAME = "users"

# --- Database Connection ---
# We initialize the database client. Using motor for async operations with FastAPI.
# The server_api configuration is a best practice for ensuring compatibility with modern MongoDB versions.
try:
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, server_api=ServerApi('1'))
    db = client[DB_NAME]
    poi_collection = db[POI_COLLECTION_NAME]
    user_collection = db[USER_COLLECTION_NAME]
    print("✅ Successfully connected to MongoDB.")
except Exception as e:
    print(f"❌ Error connecting to MongoDB: {e}")
    # In a real app, you might want to exit or handle this more gracefully
    client, db, poi_collection, user_collection = None, None, None, None


# --- FAISS and Knowledge Base Loading ---
# Load the pre-built vector index and the corresponding text data.
# These files are expected to be in the root directory of the project.
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
    # --- FIX APPLIED HERE ---
    if poi_collection is None:
        return None
    return await poi_collection.find_one({"_id": poi_id})



# ==============================================================================
# 2. Vector Search / RAG Retrieval Functions
# ==============================================================================

def search_knowledge_base(query_embedding, k: int = 5) -> str:
    """
    Searches the FAISS index for the most relevant text chunks based on a query embedding.
    
    Args:
        query_embedding: The vectorized user query.
        k: The number of top results to retrieve.
        
    Returns:
        A single string containing the concatenated relevant text chunks,
        which will be used as context for the LLM.
    """
    if not faiss_index or not knowledge_base_texts:
        return "Knowledge base is not available."

    # Search the FAISS index for the k nearest neighbors
    distances, indices = faiss_index.search(query_embedding, k)
    
    # Retrieve the corresponding text chunks from the loaded pickle file
    retrieved_chunks = [knowledge_base_texts[i] for i in indices[0]]
    
    # Combine the chunks into a single context string
    context = "\n\n---\n\n".join(retrieved_chunks)
    return context


# ==============================================================================
# 3. User Preference Functions (Memory)
# ==============================================================================

async def get_user_preferences(user_id: str) -> Dict[str, List[str]]:
    """Fetches a user's preference profile from the 'users' collection."""
    # --- FIX APPLIED HERE ---
    if user_collection is None:
        return {"likes": [], "dislikes": []}
        
    user_profile = await user_collection.find_one({"_id": user_id})
    if user_profile:
        return user_profile.get("preferences", {"likes": [], "dislikes": []})
    
    return {"likes": [], "dislikes": []}



async def update_user_preferences(user_id: str, new_preferences: Dict[str, List[str]]):
    """Updates (or inserts) a user's preference profile in the 'users' collection."""
    # --- FIX APPLIED HERE ---
    if user_collection is None:
        print("❌ Cannot update preferences: User collection not available.")
        return

    await user_collection.update_one(
        {"_id": user_id},
        {"$set": {"preferences": new_preferences}},
        upsert=True
    )
    print(f"✅ Preferences updated for user: {user_id}")
    
