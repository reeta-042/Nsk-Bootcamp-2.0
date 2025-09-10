import os
import httpx
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
ORS_API_KEY = os.getenv("ORS_API_KEY") # Using the OpenRouteService key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- LAZY INITIALIZATION OF AI CLIENTS ---
@st.cache_resource
def get_llm():
    """Initializes and returns the Gemini Pro chat model."""
    print("--- Initializing Gemini Pro LLM ---")
    return ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GEMINI_API_KEY)

@st.cache_resource
def get_embeddings_model():
    """Initializes and returns the Gemini embeddings model."""
    print("--- Initializing Gemini Embeddings Model ---")
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GEMINI_API_KEY)

# ==============================================================================
# Routing and Narrative Functions (All Synchronous)
# ==============================================================================

def get_route_from_ors(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> Dict:
    """
    Fetches a walking route from the OpenRouteService API with the corrected URL and headers.
    """
    # --- THIS IS THE CORRECTED API CALL ---
    headers = {
        'Authorization': ORS_API_KEY,
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        'Content-Type': 'application/json; charset=utf-8'
    }
    body = {"coordinates": [[start_lon, start_lat], [end_lon, end_lat]]}
    # The correct base URL for the directions endpoint
    ors_url = "https://api.openrouteservice.org/v2/directions/foot-walking"
    # --- END OF FIX ---

    print(f"DEBUG: Calling OpenRouteService URL: {ors_url}")

    try:
        response = httpx.post(ors_url, headers=headers, json=body, timeout=20.0)
        response.raise_for_status()
        
        ors_data = response.json()
        
        # Adapt the ORS response to a consistent format for our app
        route_info = ors_data['features'][0]['properties']['segments'][0]
        
        formatted_data = {
            "routes": [{
                "duration": route_info['duration'],
                "distance": route_info['distance'],
            }],
            # The geometry is the full route path, which we will use for drawing the line
            "geometry": {
                "coordinates": ors_data['features'][0]['geometry']['coordinates']
            }
        }
        return formatted_data
        
    except httpx.HTTPStatusError as e:
        raise Exception(f"OpenRouteService API error: {e.response.text}")
    except (httpx.RequestError, KeyError, IndexError) as e:
        raise Exception(f"Could not get or parse route from OpenRouteService: {e}")

def generate_narrative_with_rag(request: models.JourneyRequest) -> models.JourneyNarrative:
    """
    Generates a personalized journey narrative using a synchronous RAG pipeline.
    """
    llm = get_llm()
    embeddings_model = get_embeddings_model()
    
    user_prefs = knowledge_base.get_user_preferences(request.user_id)
    preferences_text = f"This user's known preferences are: Likes: {user_prefs.get('likes', [])}, Dislikes: {user_prefs.get('dislikes', [])}."

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
        ai_response = llm.invoke(prompt)
        parsed_response = parser.parse(ai_response.content)
        return parsed_response
    except ValidationError as e:
        print(f"LLM output validation error: {e}")
        raise Exception("Failed to generate a valid narrative from the AI model.")
    
