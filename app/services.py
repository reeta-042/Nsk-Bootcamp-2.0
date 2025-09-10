import os
import httpx
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
from langchain_core.messages import HumanMessage
from pydantic import ValidationError

# --- Load Environment Variables ---
load_dotenv()
MAPTILER_API_KEY = os.getenv("MAPTILER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- LAZY INITIALIZATION OF AI CLIENTS ---
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

@st.cache_resource
def get_vision_llm():
    """Initializes and returns the Gemini Pro Vision model."""
    print("--- Initializing Gemini Vision LLM ---")
    return ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=GEMINI_API_KEY)


# ==============================================================================
# 1. External Service Functions (MapTiler) - SYNCHRONOUS & CORRECT URL
# ==============================================================================
def get_route_from_maptiler(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> Dict:
    """
    Fetches a walking route from the MapTiler Routing API using the correct endpoint.
    """
    print(f"DEBUG: get_route_from_maptiler received: start=({start_lon}, {start_lat}), end=({end_lon}, {end_lat})")

    if not all(isinstance(v, (int, float)) for v in [start_lon, start_lat, end_lon, end_lat]):
        raise ValueError("Invalid coordinate type received. All coordinates must be numbers.")

    start_coords = f"{start_lon},{start_lat}"
    end_coords = f"{end_lon},{end_lat}"
    coordinates_path = f"{start_coords};{end_coords}"
    
    # Manually building the full URL with the key directly included.
    base_url = f"https://api.maptiler.com/routes/foot-walking/{coordinates_path}"
    full_url = f"{base_url}?steps=true&overview=full&key={MAPTILER_API_KEY}"
    
    print(f"DEBUG: Final URL being called: {full_url}")

    try:
        # We now call the full_url directly, with no extra params.
        response = httpx.get(full_url, timeout=20.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print("--- FULL HTTPX ERROR ---")
        print(f"Request URL: {e.request.url}")
        print(f"Response Status Code: {e.response.status_code}")
        print(f"Response Content: {e.response.text}")
        print("--- END FULL HTTPX ERROR ---")
        raise Exception(f"MapTiler API error: {e.response.text}")
    except httpx.RequestError as e:
        raise Exception(f"Could not connect to MapTiler service: {e}")

# ==============================================================================
# 2. Core Narrative Generation Functions (RAG) - SYNCHRONOUS
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

# ==============================================================================
# 3. Image-Based Location Functions - NOW SYNCHRONOUS
# ==============================================================================
def get_location_from_image(image_file: Any) -> Dict[str, float]:
    """
    Analyzes an image using Gemini Vision to identify the landmark and return its coordinates.
    This is now a synchronous function.
    """
    vision_llm = get_vision_llm()

    # The .read() method on Streamlit's UploadedFile is synchronous
    image_data = image_file.read()
    base64_image = base64.b64encode(image_data).decode("utf-8")
    
    vision_prompt = HumanMessage(
        content=[
            {"type": "text", "text": "You are a world-class location identification expert. Look at this image. Identify the specific landmark, building, or monument shown. Based on your knowledge, what are the approximate latitude and longitude coordinates of this landmark? Respond ONLY with a valid JSON object containing 'latitude' and 'longitude' keys and nothing else. For example: {\"latitude\": 6.86, \"longitude\": 7.40}"},
            {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"},
        ]
    )
    
    try:
        # Use the synchronous .invoke() method
        ai_response = vision_llm.invoke([vision_prompt])
        location_data = json.loads(ai_response.content)
        if 'latitude' not in location_data or 'longitude' not in location_data:
            raise KeyError("Missing latitude or longitude in response.")
        return location_data
    except (json.JSONDecodeError, KeyError, ValidationError) as e:
        print(f"Error identifying location from image: {e}")
        raise Exception("Could not identify a valid location from the provided image.")

# NOTE: The user reflection function would also need to be converted to synchronous if used.
