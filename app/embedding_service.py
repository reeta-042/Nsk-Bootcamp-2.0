

import os
import asyncio
from dotenv import load_dotenv
import streamlit as st

from langchain_google_genai import GoogleGenerativeAIEmbeddings
# THIS IS THE NEW IMPORT FOR THE FIX
from google.auth.credentials import AnonymousCredentials

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Cached Model Initialization ---
@st.cache_resource
def get_embeddings_model():
    """
    Initializes the Google Generative AI Embeddings model.
    
    THE FIX: We pass 'AnonymousCredentials' to prevent the library from
    trying to find default credentials on the system, which causes a timeout
    on Streamlit Cloud. It will now ONLY use the 'google_api_key'.
    """
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=GEMINI_API_KEY,
        client_options={"credentials": AnonymousCredentials()} # <-- THE FIX
    )

# --- Private Async Function ---
async def _embed_query_async(query: str) -> list[float]:
    """

    A dedicated async function to run the problematic embedding model
    within a controlled event loop.
    """
    embeddings_model = get_embeddings_model()
    # The embed_query method itself is synchronous, but the model's initialization
    # requires an event loop, which is why we wrap it like this.
    return embeddings_model.embed_query(query)

# --- Public Synchronous Function ---
def get_query_embedding(query: str) -> list[float]:
    """
    The main public function that the rest of the app will call.
    It safely runs the async embedding logic in its own event loop.
    """
    print("--- DEBUG: Running embedding function via embedding_service...")
    try:
        # Use asyncio.run() to create and manage the event loop
        embedding = asyncio.run(_embed_query_async(query))
        print("--- DEBUG: Embedding created successfully.")
        return embedding
    except Exception as e:
        print(f"--- FATAL ERROR: Failed to create embedding in embedding_service. Error: {e}")
        # Re-raise the exception to notify the caller
        raise
        
