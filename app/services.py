# app/services.py

import os
import httpx
import numpy as np
from typing import Dict, List
import json

from dotenv import load_dotenv
import streamlit as st

from . import models
from . import knowledge_base

# --- Routing Service Function ---

# The function now accepts a 'travel_mode' argument
def get_route_from_ors(start_lon: float, start_lat: float, end_lon: float, end_lat: float, travel_mode: str = "foot-walking") -> Dict:
    """
    Fetches route data from OpenRouteService API for a given travel mode.
    Valid modes include 'foot-walking', 'driving-car', etc.
    """
    ORS_API_KEY = os.getenv("ORS_API_KEY")
    
    # The travel_mode is now a variable in the URL string
    ors_url = f"https://api.openrouteservice.org/v2/directions/{travel_mode}?api_key={ORS_API_KEY}&start={start_lon},{start_lat}&end={end_lon},{end_lat}"

    try:
        with httpx.Client() as client:
            response = client.get(ors_url, timeout=30.0)
            response.raise_for_status()
            ors_data = response.json()

        route_info = ors_data['features'][0]['properties']['segments'][0]
        geometry = ors_data['features'][0]['geometry']['coordinates']

        return {
            "duration": route_info['duration'],
            "distance": route_info['distance'],
            "points": geometry
        }
    except httpx.RequestError as e:
        raise Exception(f"Network error calling OpenRouteService: {e}")
    except httpx.HTTPStatusError as e:
        raise Exception(f"API error from OpenRouteService: {e.response.status_code} - {e.response.text}")
    except (KeyError, IndexError) as e:
        raise Exception(f"Unexpected data format from OpenRouteService. Raw error: {e}")


# --- Narrative and Chat Generation Functions ---
# (The rest of the file remains exactly the same)

def generate_narrative_with_rag(llm, embedding_model, parser, request: models.JourneyRequest, destination_name: str) -> models.JourneyNarrative:
    """
    Generates the primary, personalized journey narrative using a RAG model.
    This function is for the initial journey creation.
    """
    # The models are now passed in directly, not called from session_state.

    # Fetch user preferences to tailor the narrative
    user_prefs = knowledge_base.get_user_preferences(request.user_id)
    preferences_text = f"This user's known preferences are: Likes: {user_prefs.get('likes', [])}, Dislikes: {user_prefs.get('dislikes', [])}."

    # Embed the user's query and search the knowledge base
    query_embedding = embedding_model.encode(request.query)
    query_embedding_2d = np.array([query_embedding]).astype('float32')
    context = knowledge_base.search_knowledge_base(query_embedding_2d)

    prompt = f"""
    You are a Hometown Atlas, a precise and context-aware AI travel guide.
     for African Cities and Cultures
    Your primary goal is to generate a narrative for a user's journey to a specific destination and enrich the journey with fascinating stories like a tourist guide.

    **CRITICAL INSTRUCTIONS:**
    1.  **STAY LOCAL:** The user is in **{request.city}**. All descriptions, landmarks, and facts MUST be relevant to **{request.city}**. Do NOT mention places from other cities or countries.
    2.  **DESTINATION FOCUS:** The user wants to go to **{destination_name}**. The narrative should be about the journey TO this specific place.
    3.  **USE THE CONTEXT:** The following 'Retrieved Context' is your primary source of truth. Base your narrative on this information.
    4.  **FALLBACK PLAN:** If the 'Retrieved Context' is empty or not helpful, generate a rich, interesting description of the destination, **{destination_name}**, itself.
    5.  **USER PROFILE:** Consider the user's preferences: {preferences_text}.

    **User's Goal:** "{request.query}"
    **Retrieved Context from Knowledge Base:**
    {context}
    ---
    Now, generate the narrative based on these strict instructions.
    {parser.get_format_instructions()}
    """

    ai_response = llm.invoke(prompt)
    return parser.parse(ai_response.content)


def generate_chat_response(llm, user_id: str, city: str, destination_name: str, journey_narrative: models.JourneyNarrative, conversation_history: str) -> str:
    """
    Generates a conversational response for the 'Talk with the Guide' tab.
    This function uses the context of the already-created journey.
    """
    # The llm model is now passed in directly.
    user_prefs = knowledge_base.get_user_preferences(user_id)
    preferences_text = f"User Likes: {user_prefs.get('likes', [])}, User Dislikes: {user_prefs.get('dislikes', [])}."

    prompt = f"""
    You are a helpful and conversational AI tour guide for the city of {city}.
    The user has already generated a journey to "{destination_name}" and is now asking follow-up questions.
    Your personality is friendly, knowledgeable, and concise.

    **CONTEXT OF THE CURRENT JOURNEY:**
    - Title: {journey_narrative.title}
    - Summary: {journey_narrative.narrative}
    - User Preferences: {preferences_text}

    **CONVERSATION HISTORY (latest message is from the user):**
    {conversation_history}

    **YOUR TASK:**
    Based on the journey context and conversation history, provide a helpful and relevant answer to the user's last message.
    - If the user asks about something on the route, be descriptive.
    - If the user asks for an alternative, you can suggest one, but keep it within {city}.
    - Keep your answers brief and to the point.
    """

    ai_response = llm.invoke(prompt)
    return ai_response.content


def reflect_and_update_preferences(llm, request: models.ReflectionRequest):
    """Uses an LLM to analyze user feedback and update their preference profile."""
    # The llm model is now passed in directly.
    current_prefs = knowledge_base.get_user_preferences(request.user_id)

    reflection_prompt = f"""
    You are a user preference analysis AI. Your job is to update a user's preference profile based on their recent activity.
    Analyze the interaction below and update the 'likes' and 'dislikes' lists.
    - Infer general topics from the query and title (e.g., 'quiet walk' -> 'quiet', 'historical tour' -> 'history').
    - If the user 'liked' the journey, add the inferred topics to their 'likes'.
    - If they 'disliked' it, add the inferred topics to their 'dislikes'.
    - Do not add duplicate items. Keep the lists concise and lowercase.

    **Current User Profile:** {current_prefs}
    **User's Recent Activity:**
    - Initial Query: "{request.original_query}"
    - Journey Title: "{request.journey_title}"
    - Feedback: "{request.user_feedback}"

    **Your Task:** Respond ONLY with the updated JSON object for the 'preferences' field and nothing else.
    Example response: {{"likes": ["history", "quiet"], "dislikes": ["crowded"]}}
    """

    ai_response = llm.invoke(reflection_prompt)

    try:
        # Clean the response to ensure it's valid JSON
        cleaned_response = ai_response.content.strip().replace("```json", "").replace("```", "")
        updated_prefs_data = json.loads(cleaned_response)

        # Validate with Pydantic model before saving
        validated_prefs = models.UserPreferences(**updated_prefs_data)
        knowledge_base.update_user_preferences(request.user_id, validated_prefs.dict())
        st.toast("✅ Your preferences have been updated!", icon="🧠")
    except (json.JSONDecodeError, Exception) as e:
        st.warning(f"Could not update preferences due to an AI response error. Raw error: {e}")
        print(f"Failed to parse preference update: {ai_response.content}")
    
