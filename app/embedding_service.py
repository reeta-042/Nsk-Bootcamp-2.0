

import os
import asyncio
from dotenv import load_dotenv
import streamlit as st

from langchain_google_genai import GoogleGenerativeAIEmbeddings
# This import is still needed for the fix
from google.auth.credentials import AnonymousCredentials

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Cached Model Initialization ---
@st.cache_resource
def get_embeddings_model():
    """
    Initializes the Google Generative AI Embeddings model.
    
    THE FINAL FIX: We pass 'AnonymousCredentials' directly as a top-level
    argument. This prevents the library from trying to find default credentials
    on the system, which causes the timeout on Streamlit Cloud.
    """
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=GEMINI_API_KEY,
        credentials=AnonymousCredentials() # <-- THE FIX IS NOW HERE
    )

# --- Private Async Function ---
async def _embed_query_async(query: str) -> list[float]:
    """
    A dedicated async function to run the problematic embedding model
    within a controlled event loop.
    """
    embeddings_model = get_embeddings_model()
    return embeddings_model.embed_query(query)

# --- Public Synchronous Function ---
def get_query_embedding(query: str) -> list[float]:
    """
    The main public function that the rest of the app will call.
    It safely runs the async embedding logic in its own event loop.
    """
    print("--- DEBUG: Running embedding function via embedding_service...")
    try:
        embedding = asyncio.run(_embed_query_async(query))
        print("--- DEBUG: Embedding created successfully.")
        return embedding
    except Exception as e:
        print(f"--- FATAL ERROR: Failed to create embedding in embedding_service. Error: {e}")
        raise
        
