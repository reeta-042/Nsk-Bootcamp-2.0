import os
import httpx
import json
import base64
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv
import streamlit as st # We can import streamlit here for caching

# Import our own modules
from . import models
from . import knowledge_base

# Import LangChain and Google Generative AI components
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.output_parsers import PydanticOutputParser
from langchain_core.messages import HumanMessage
from pydantic import ValidationError

# --- Load Environment Variables ---
load_dotenv()
MAPTILER_API_KEY = os.getenv("MAPTILER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- LAZY INITIALIZATION OF AI CLIENTS ---
# This is the new pattern to prevent the event loop error.
# We use Streamlit's cache to ensure each model is only loaded once.

@st.cache_resource
def get_llm():
    """Initializes and returns the Gemini Pro chat model."""
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY)

@st.cache_resource
def get_embeddings_model():
    """Initializes and returns the Gemini embeddings model."""
    # This is the line that was causing the crash. Now it's safely inside a function.
    return GoogleGenerativeAIEmbeddings(model="gemini-embedding-001", google_api_key=GEMINI_API_KEY)

@st.cache_resource
def get_vision_llm():
    """Initializes and returns the Gemini Pro Vision model."""
    return ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=GEMINI_API_KEY)


# ==============================================================================
# 1. External Service Functions (MapTiler)
# ==============================================================================
# (This function remains unchanged)
async def get_route_from_maptiler(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> Dict:
    # ... same code as before ...
    start_coords = f"{start_lon},{start_lat}"
    end_coords = f"{end_lon},{end_lat}"
    route_url = f"https://api.maptiler.com/routing/v1/foot?waypoints={start_coords};{end_coords}&steps=true&overview=full&key={MAPTILER_API_KEY}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(route_url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(status_code=e.response.status_code, detail=f"MapTiler API error: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(status_code=503, detail=f"Could not connect to MapTiler service: {e}")


# ==============================================================================
# 2. Core Narrative Generation Functions (RAG)
# ==============================================================================

async def generate_narrative_with_rag(request: models.JourneyRequest) -> models.JourneyNarrative:
    """
    The main RAG pipeline to generate a personalized and context-aware journey narrative.
    """
    # --- MODIFICATION: Get models from the cached functions ---
    llm = get_llm()
    embeddings_model = get_embeddings_model()
    
    # 1. Fetch User Preferences
    user_prefs = await knowledge_base.get_user_preferences(request.user_id)
    preferences_text = f"This user's known preferences are: Likes: {user_prefs.get('likes', [])}, Dislikes: {user_prefs.get('dislikes', [])}."

    # 2. Create an Embedding of the User's Query
    query_embedding = embeddings_model.embed_query(request.query)

    # (The rest of the function is the same)
    # ...
    context = knowledge_base.search_knowledge_base(query_embedding=[query_embedding])
    parser = PydanticOutputParser(pydantic_object=models.JourneyNarrative)
    prompt = f"""...""" # Your full prompt
    try:
        ai_response = await llm.ainvoke(prompt)
        parsed_response = parser.parse(ai_response.content)
        return parsed_response
    except ValidationError as e:
        print(f"LLM output validation error: {e}")
        raise Exception(status_code=500, detail="Failed to generate a valid narrative from the AI model.")


# ==============================================================================
# 3. User Memory and Reflection Functions
# ==============================================================================

async def reflect_and_update_preferences(request: models.ReflectionRequest):
    """
    Performs the reflection step to learn from user feedback and update their profile.
    """
    # --- MODIFICATION: Get model from the cached function ---
    llm = get_llm()

    # (The rest of the function is the same)
    # ...
    current_prefs = await knowledge_base.get_user_preferences(request.user_id)
    reflection_prompt = f"""...""" # Your full reflection prompt
    ai_response = await llm.ainvoke(reflection_prompt)
    try:
        updated_prefs_data = json.loads(ai_response.content)
        validated_prefs = models.UserPreferences(**updated_prefs_data)
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Error: LLM returned invalid preference JSON for user {request.user_id}. Error: {e}")
        return
    await knowledge_base.update_user_preferences(request.user_id, validated_prefs.dict())


# ==============================================================================
# 4. Image-Based Location Functions
# ==============================================================================

async def get_location_from_image(image_file: Any) -> Dict[str, float]:
    """
    Analyzes an image using Gemini Vision to identify the landmark and return its coordinates.
    """
    # --- MODIFICATION: Get model from the cached function ---
    vision_llm = get_vision_llm()

    # (The rest of the function is the same)
    # ...
    image_data = await image_file.read()
    base64_image = base64.b64encode(image_data).decode("utf-8")
    vision_prompt = HumanMessage(...) # Your full vision prompt
    try:
        ai_response = await vision_llm.ainvoke([vision_prompt])
        location_data = json.loads(ai_response.content)
        if 'latitude' not in location_data or 'longitude' not in location_data:
            raise KeyError("Missing latitude or longitude in response.")
        return location_data
    except (json.JSONDecodeError, KeyError, ValidationError) as e:
        print(f"Error identifying location from image: {e}")
        raise Exception(status_code=500, detail="Could not identify a valid location from the provided image.")
        
