import os
import httpx
import numpy as np
from typing import Dict

from dotenv import load_dotenv
import streamlit as st

from . import models
from . import knowledge_base

def get_route_from_ors(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> Dict:
    ORS_API_KEY = os.getenv("ORS_API_KEY")
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
        # This error is now more specific
        raise Exception(f"[ORS_ERROR] Failed to get route from OpenRouteService. Raw error: {e}")

def generate_narrative_with_rag(request: models.JourneyRequest) -> models.JourneyNarrative:
    try:
        # Step 1: Get pre-loaded models
        llm = st.session_state.llm
        embedding_model = st.session_state.embedding_model
        parser = st.session_state.parser

        # Step 2: Get user preferences
        print("--- RAG: Getting user preferences...")
        user_prefs = knowledge_base.get_user_preferences(request.user_id)
        preferences_text = f"This user's known preferences are: Likes: {user_prefs.get('likes', [])}, Dislikes: {user_prefs.get('dislikes', [])}."
        print("--- RAG: Preferences retrieved.")

        # Step 3: Embed the user's query
        print("--- RAG: Encoding user query...")
        query_embedding = embedding_model.encode(request.query)
        query_embedding_2d = np.array([query_embedding]).astype('float32')
        print("--- RAG: Query encoded.")

        # Step 4: Search the knowledge base
        print("--- RAG: Searching knowledge base...")
        context = knowledge_base.search_knowledge_base(query_embedding_2d)
        print("--- RAG: Knowledge base search complete.")
        
        prompt = f"""
You are a Hometown Atlas, a precise and context-aware AI travel guide filled with interesting stories and facts about places people call home on the map.
Your primary goal is to generate a narrative for a user's journey within a specific city.

**CRITICAL INSTRUCTIONS:**
1.  **STAY LOCAL:** The user is in **{request.city}**. All descriptions, landmarks, and facts MUST be relevant to **{request.city}**. Do NOT mention places or people from other cities or countries.
2.  **DESTINATION FOCUS:** The user wants to go to **{destination_name_from_main_py}**. The narrative should be about the journey to this specific place.
3.  **USE THE CONTEXT:** The following 'Retrieved Context' is your primary source of truth. Base your narrative on this information.
4.  **FALLBACK PLAN:** If the 'Retrieved Context' is empty,not very helpful or not relevant to users destination, generate a rich, interesting description of the destination, **{destination_name_from_main_py}**, itself.

**User's Goal:** "{request.query}"
**User's Profile:** {preferences_text}
**Retrieved Context from Knowledge Base:**
{context}
---
Now, generate the narrative based on these strict instructions.
"""

        
        # Step 5: Invoke the LLM (the most likely point of failure)
        print("--- RAG: Invoking the Google LLM... (This may hang)")
        ai_response = llm.invoke(prompt)
        print("--- RAG: LLM invocation successful.")

        # Step 6: Parse the output
        print("--- RAG: Parsing LLM response...")
        parsed_response = parser.parse(ai_response.content)
        print("--- RAG: Response parsed successfully.")
        
        return parsed_response

    except Exception as e:
        # This error is now more specific
        raise Exception(f"[RAG_ERROR] An error occurred during narrative generation. Raw error: {e}")
        
