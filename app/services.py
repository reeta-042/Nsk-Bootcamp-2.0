import os
import httpx
import json
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

# --- LAZY INITIALIZATION OF AI CLIENTS ---
@st.cache_resource
def get_llm():
    print("--- Initializing Gemini Pro LLM ---")
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY)

@st.cache_resource
def get_embeddings_model():
    print("--- Initializing Gemini Embeddings Model ---")
    return GoogleGenerativeAIEmbeddings(model="gemini-embedding-001", google_api_key=GEMINI_API_KEY)

# ==============================================================================
# Geocoding and Routing Functions (All Synchronous)
# ==============================================================================

def get_city_from_coords(lon: float, lat: float) -> str:
    """
    Performs reverse geocoding to find the city name for a given set of coordinates.
    """
    geocode_url = f"https://api.maptiler.com/geocoding/{lon},{lat}.json?key={MAPTILER_API_KEY}"
    print(f"DEBUG: Calling Geocoding URL: {geocode_url}")
    try:
        response = httpx.get(geocode_url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        for feature in data.get("features", []):
            if "place_type" in feature and "city" in feature["place_type"]:
                return feature.get("text", "Unknown City")
        return "Unknown City"
    except Exception as e:
        print(f"ERROR: Could not reverse geocode coordinates: {e}")
        return "Unknown City"

def get_route_from_maptiler(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> Dict:
    """
    Fetches a walking route from the MapTiler Routing API.
    """
    start_coords = f"{start_lon},{start_lat}"
    end_coords = f"{end_lon},{end_lat}"
    coordinates_path = f"{start_coords};{end_coords}"
    
    base_url = f"https://api.maptiler.com/routes/foot-walking/{coordinates_path}"
    full_url = f"{base_url}?steps=true&overview=full&key={MAPTILER_API_KEY}"
    
    print(f"DEBUG: Final URL being called: {full_url}")

    try:
        response = httpx.get(full_url, timeout=20.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise Exception(f"MapTiler API error: {e.response.text}")
    except httpx.RequestError as e:
        raise Exception(f"Could not connect to MapTiler service: {e}")

# ==============================================================================
# Core Narrative Generation Functions (RAG) - SYNCHRONOUS
# ==============================================================================
def generate_narrative_with_rag(request: models.JourneyRequest) -> models.JourneyNarrative:
    llm = get_llm()
    embeddings_model = get_embeddings_model()
    
    user_prefs = knowledge_base.get_user_preferences(request.user_id)
    preferences_text = f"This user's known preferences are: Likes: {user_prefs.get('likes', [])}, Dislikes: {user_prefs.get('dislikes', [])}."

    query_embedding = embeddings_model.embed_query(request.query)
    context = knowledge_base.search_knowledge_base(query_embedding=[query_embedding])
    
    parser = PydanticOutputParser(pydantic_object=models.JourneyNarrative)
    
    prompt = f"""
    You are UrbanScribe... (your full prompt here)
    **Output Instructions:**
    {parser.get_format_instructions()}
    """
    
    try:
        ai_response = llm.invoke(prompt)
        parsed_response = parser.parse(ai_response.content)
        return parsed_response
    except ValidationError as e:
        print(f"LLM output validation error: {e}")
        raise Exception("Failed to generate a valid narrative from the AI model.")
        
