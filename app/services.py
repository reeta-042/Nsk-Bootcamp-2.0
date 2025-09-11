# app/services.py

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
        You are UrbanScribe, an intelligent city storyteller. Your task is to create a personalized journey narrative.
        **User's Goal:** "{request.query}"
        **User's Profile:** {preferences_text}
        **Retrieved Context from Knowledge Base:**
        {context}
        ---
        Based on ALL the information above, generate a compelling and tailored narrative for the user's journey.
        **Output Instructions:**
        {parser.get_format_instructions()}
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
        
