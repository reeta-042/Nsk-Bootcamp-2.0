

import os
import httpx
from typing import Dict

from dotenv import load_dotenv
import streamlit as st

from . import models
from . import knowledge_base
from . import embedding_service  # <-- IMPORT OUR NEW MODULE

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import ValidationError

load_dotenv()
ORS_API_KEY = os.getenv("ORS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- AI CLIENT INITIALIZATION ---
@st.cache_resource
def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY)

# --- ROUTING SERVICE ---
def get_route_from_ors(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> Dict:
    # This function uses the GET method as we confirmed
    ors_url = f"https://api.openrouteservice.org/v2/directions/foot-walking?api_key={ORS_API_KEY}&start={start_lon},{start_lat}&end={end_lon},{end_lat}"
    
    print(f"--- DEBUG: Calling OpenRouteService with URL: {ors_url}")
    
    try:
        response = httpx.get(ors_url)
        print(f"--- DEBUG: ORS Response Status Code: {response.status_code}")
        response.raise_for_status()
        ors_data = response.json()
        print("--- DEBUG: ORS Response JSON received successfully.")
        
        route_info = ors_data['features'][0]['properties']['segments'][0]
        geometry = ors_data['features'][0]['geometry']['coordinates']
        
        return {
            "duration": route_info['duration'],
            "distance": route_info['distance'],
            "points": geometry
        }
    except (httpx.HTTPStatusError, KeyError, IndexError) as e:
        print(f"--- ERROR: An error occurred with OpenRouteService. Error: {e}")
        if 'response' in locals() and response:
            print(f"--- ERROR: Raw ORS Response Text: {response.text}")
        raise Exception(f"Could not get or parse route from OpenRouteService. Error: {e}")
    except httpx.RequestError as e:
        raise Exception(f"Could not connect to OpenRouteService: {e}")

# --- NARRATIVE GENERATION ---
def generate_narrative_with_rag(request: models.JourneyRequest) -> models.JourneyNarrative:
    llm = get_llm()
    
    # 1. Fetch User Preferences (Synchronous)
    user_prefs = knowledge_base.get_user_preferences(request.user_id)
    preferences_text = f"This user's known preferences are: Likes: {user_prefs.get('likes', [])}, Dislikes: {user_prefs.get('dislikes', [])}."

    # 2. Create Embedding (Using our new, safe service)
    query_embedding = embedding_service.get_query_embedding(request.query)

    # 3. Search Knowledge Base (Synchronous)
    context = knowledge_base.search_knowledge_base(query_embedding=[query_embedding])
    
    # 4. Generate Narrative (Synchronous)
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

