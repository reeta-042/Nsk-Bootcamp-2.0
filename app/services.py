# app/services.py

import os
import httpx
import numpy as np
from typing import Dict

from dotenv import load_dotenv
import streamlit as st

from . import models
from . import knowledge_base

from sentence_transformers import SentenceTransformer
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import ValidationError

load_dotenv()
ORS_API_KEY = os.getenv("ORS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- NEW CACHING STRATEGY (THE FIX) ---
# We use a simple, thread-safe pattern instead of @st.cache_resource
# to avoid deadlocks with model loading.

# Check if the models are already in Streamlit's session state
if 'llm' not in st.session_state:
    print("--- Initializing Gemini LLM... ---")
    st.session_state.llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GEMINI_API_KEY)

if 'embedding_model' not in st.session_state:
    print("--- Initializing Sentence Transformer model... ---")
    st.session_state.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def get_llm():
    """Gets the initialized LLM from session state."""
    return st.session_state.llm

def get_embedding_model():
    """Gets the initialized Sentence Transformer model from session state."""
    return st.session_state.embedding_model

# --- ROUTING SERVICE (No changes needed) ---
def get_route_from_ors(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> Dict:
    ors_url = f"https://api.openrouteservice.org/v2/directions/foot-walking?api_key={ORS_API_KEY}&start={start_lon},{start_lat}&end={end_lon},{end_lat}"
    try:
        response = httpx.get(ors_url)
        response.raise_for_status()
        ors_data = response.json()
        route_info = ors_data['features'][0]['properties']['segments'][0]
        geometry = ors_data['features'][0]['geometry']['coordinates']
        return {
            "duration": route_info['duration'],
            "distance": route_info['distance'],
            "points": geometry
        }
    except Exception as e:
        raise Exception(f"Could not get or parse route from OpenRouteService. Error: {e}")

# --- NARRATIVE GENERATION (No changes needed) ---
def generate_narrative_with_rag(request: models.JourneyRequest) -> models.JourneyNarrative:
    llm = get_llm()
    embedding_model = get_embedding_model()

    user_prefs = knowledge_base.get_user_preferences(request.user_id)
    preferences_text = f"This user's known preferences are: Likes: {user_prefs.get('likes', [])}, Dislikes: {user_prefs.get('dislikes', [])}."

    query_embedding = embedding_model.encode(request.query)
    query_embedding_2d = np.array([query_embedding]).astype('float32')
    context = knowledge_base.search_knowledge_base(query_embedding_2d)
    
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
        raise Exception(f"Failed to generate a valid narrative from the AI model: {e}")
    
