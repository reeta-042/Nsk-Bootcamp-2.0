import os
import httpx  # Use the synchronous client
import json
import base64
from typing import Dict, Any
from dotenv import load_dotenv
import streamlit as st

# Import our own modules
from . import models
from . import knowledge_base

# Import LangChain and Google Generative AI components
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.output_parsers import PydanticOutputParser
from pydantic import ValidationError

# --- Load Environment Variables ---
load_dotenv()
MAPTILER_API_KEY = os.getenv("MAPTILER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- LAZY INITIALIZATION OF AI CLIENTS (This is correct) ---
@st.cache_resource
def get_llm():
    """Initializes and returns the Gemini Pro chat model."""
    print("--- Initializing Gemini Pro LLM ---")
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY)

@st.cache_resource
def get_embeddings_model():
    """Initializes and returns the Gemini embeddings model."""
    print("--- Initializing Gemini Embeddings Model ---")
    return GoogleGenerativeAIEmbeddings(model="gemini-embedding-001", google_api_key=GEMINI_API_KEY)

# ==============================================================================
# 1. External Service Functions (MapTiler) - NOW SYNCHRONOUS & CORRECT URL
# ==============================================================================
def get_route_from_maptiler(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> Dict:
    """
    Fetches a walking route from the MapTiler Routing API using the correct endpoint.
    """
    start_coords = f"{start_lon},{start_lat}"
    end_coords = f"{end_lon},{end_lat}"
    
    # The coordinates are part of the URL path for the new endpoint
    coordinates_path = f"{start_coords};{end_coords}"
    
    # The other options are passed as clean URL parameters
    params = {
        "steps": "true",
        "overview": "full",
        "key": MAPTILER_API_KEY
    }
    
    # The new, correct base URL for the foot-walking profile
    base_url = f"https://api.maptiler.com/routes/foot-walking/{coordinates_path}"
    
    print(f"DEBUG: Calling New MapTiler URL: {base_url}")

    try:
        # Use the synchronous httpx.get() with the 'params' argument
        response = httpx.get(base_url, params=params, timeout=20.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"ERROR: MapTiler responded with status {e.response.status_code} and text: {e.response.text}")
        raise Exception(f"MapTiler API error: {e.response.text}")
    except httpx.RequestError as e:
        print(f"ERROR: Could not connect to MapTiler: {e}")
        raise Exception(f"Could not connect to MapTiler service: {e}")

# ==============================================================================
# 2. Core Narrative Generation Functions (RAG) - NOW SYNCHRONOUS
# ==============================================================================
def generate_narrative_with_rag(request: models.JourneyRequest) -> models.JourneyNarrative:
    llm = get_llm()
    embeddings_model = get_embeddings_model()
    
    user_prefs = knowledge_base.get_user_preferences(request.user_id)
    preferences_text = f"This user's known preferences are: Likes: {user_prefs.get('likes', [])}, Dislikes: {user_prefs.get('dislikes', [])}."

    # Use the synchronous .embed_query() method
    query_embedding = embeddings_model.embed_query(request.query)

    context = knowledge_base.search_knowledge_base(query_embedding=[query_embedding])
    
    parser = PydanticOutputParser(pydantic_object=models.JourneyNarrative)
    
    prompt = f"""
    You are UrbanScribe, an intelligent city storyteller. Your task is to create a personalized journey narrative.
    **User's Goal:** "{request.query}"
    **User's Profile:** {preferences_text}
    **Retrieved Context from Knowledge Base:**
    {context}
    ---
    Based on ALL the information above, generate a compelling and tailored narrative for the user's journey.
    The narrative should directly incorporate the user's preferences and the retrieved context.
    **Output Instructions:**
    {parser.get_format_instructions()}
    """
    
    try:
        # Use the synchronous .invoke() method
        ai_response = llm.invoke(prompt)
        parsed_response = parser.parse(ai_response.content)
        return parsed_response
    except ValidationError as e:
        print(f"LLM output validation error: {e}")
        raise Exception("Failed to generate a valid narrative from the AI model.")

# NOTE: Other async functions like reflect_and_update_preferences would also need to be converted
# to synchronous if you decide to use them later.
