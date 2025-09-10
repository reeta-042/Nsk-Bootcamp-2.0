import os
import httpx
import json
import base64
import asyncio
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

# --- LAZY INITIALIZATION OF AI CLIENTS (This part is correct) ---
@st.cache_resource
def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GEMINI_API_KEY)

@st.cache_resource
def get_embeddings_model():
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GEMINI_API_KEY)

@st.cache_resource
def get_vision_llm():
    return ChatGoogleGenerativeAI(model="gemini-pro-vision", google_api_key=GEMINI_API_KEY)

# ==============================================================================
# 1. External Service Functions (MapTiler) - CORRECT
# ==============================================================================
async def get_route_from_maptiler(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> Dict:
    start_coords = f"{start_lon},{start_lat}"
    end_coords = f"{end_lon},{end_lat}"
    route_url = f"https://api.maptiler.com/routing/v1/foot?waypoints={start_coords};{end_coords}&steps=true&overview=full&key={MAPTILER_API_KEY}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(route_url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"MapTiler API error: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Could not connect to MapTiler service: {e}")

# ==============================================================================
# 2. Core Narrative Generation Functions (RAG) - CORRECTED
# ==============================================================================
async def generate_narrative_with_rag(request: models.JourneyRequest) -> models.JourneyNarrative:
    llm = get_llm()
    embeddings_model = get_embeddings_model()
    
    # --- FIX APPLIED HERE: Removed 'await' from the sync function call ---
    user_prefs = knowledge_base.get_user_preferences(request.user_id)
    preferences_text = f"This user's known preferences are: Likes: {user_prefs.get('likes', [])}, Dislikes: {user_prefs.get('dislikes', [])}."

    # This part remains async, which is correct
    query_embedding = await embeddings_model.aembed_query(request.query)

    # This part is sync, which is correct
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
        # This part is async, which is correct
        ai_response = await llm.ainvoke(prompt)
        parsed_response = parser.parse(ai_response.content)
        return parsed_response
    except ValidationError as e:
        print(f"LLM output validation error: {e}")
        raise Exception("Failed to generate a valid narrative from the AI model.")

# ==============================================================================
# 3. User Memory and Reflection Functions - CORRECTED
# ==============================================================================
async def reflect_and_update_preferences(request: models.ReflectionRequest):
    llm = get_llm()

    # --- FIX APPLIED HERE: Removed 'await' from the sync function call ---
    current_prefs = knowledge_base.get_user_preferences(request.user_id)
    
    reflection_prompt = f"""
    You are a user preference analysis AI. Your job is to update a user's preference profile based on their recent activity.
    **Current User Profile:** {current_prefs}
    **User's Recent Activity:**
    - Initial Query: "{request.original_query}"
    - Journey Title: "{request.journey_title}"
    - Feedback: "{request.user_feedback}"
    ---
    **Your Task:**
    Analyze this interaction. Based on reasonable inferences, update the user's preference profile by adding or modifying their 'likes' and 'dislikes'.
    For example, if the query was about 'quiet parks' and they 'liked' it, add 'quiet' and 'parks' to their likes.
    **Respond ONLY with the updated JSON object for the 'preferences' field and nothing else.**
    Example response: {{"likes": ["history", "quiet"], "dislikes": ["crowded"]}}
    """
    
    ai_response = await llm.ainvoke(reflection_prompt)
    
    try:
        updated_prefs_data = json.loads(ai_response.content)
        validated_prefs = models.UserPreferences(**updated_prefs_data)
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Error: LLM returned invalid preference JSON for user {request.user_id}. Error: {e}")
        return
        
    # --- FIX APPLIED HERE: Removed 'await' from the sync function call ---
    knowledge_base.update_user_preferences(request.user_id, validated_prefs.dict())

# ==============================================================================
# 4. Image-Based Location Functions - CORRECTED
# ==============================================================================
async def get_location_from_image(image_file: Any) -> Dict[str, float]:
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
        ai_response = await vision_llm.ainvoke([vision_prompt])
        location_data = json.loads(ai_response.content)
        if 'latitude' not in location_data or 'longitude' not in location_data:
            raise KeyError("Missing latitude or longitude in response.")
        return location_data
    except (json.JSONDecodeError, KeyError, ValidationError) as e:
        print(f"Error identifying location from image: {e}")
        raise Exception("Could not identify a valid location from the provided image.")
    
