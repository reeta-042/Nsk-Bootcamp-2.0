import os
import httpx
from typing import Dict, Any
from dotenv import load_dotenv
import streamlit as st

from . import models, knowledge_base
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.output_parsers import PydanticOutputParser
from pydantic import ValidationError

load_dotenv()
ORS_API_KEY = os.getenv("ORS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

@st.cache_resource
def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GEMINI_API_KEY)

@st.cache_resource
def get_embeddings_model():
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GEMINI_API_KEY)

def get_route_from_ors(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> Dict:
    """Fetches a walking route from ORS with robust error handling and debugging."""
    headers = {
        'Authorization': ORS_API_KEY,
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        'Content-Type': 'application/json; charset=utf-8'
    }
    body = {"coordinates": [[start_lon, start_lat], [end_lon, end_lat]]}
    ors_url = "https://api.openrouteservice.org/v2/directions/foot-walking"

    try:
        response = httpx.post(ors_url, headers=headers, json=body, timeout=20.0)
        
        print(f"--- ORS API RESPONSE ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        print(f"------------------------")

        # --- THE TYPO IS FIXED HERE ---
        response.raise_for_status() # Corrected method name
        
        ors_data = response.json()
        route_info = ors_data['features'][0]['properties']['segments'][0]
        
        formatted_data = {
            "routes": [{"duration": route_info['duration'], "distance": route_info['distance']}],
            "geometry": {"coordinates": ors_data['features'][0]['geometry']['coordinates']}
        }
        return formatted_data
        
    except httpx.HTTPStatusError as e:
        raise Exception(f"OpenRouteService API error: {e.response.text}")
    except (KeyError, IndexError) as e:
        raise Exception(f"Could not parse route from OpenRouteService. Unexpected data structure. Error: {e}")
    except httpx.RequestError as e:
        raise Exception(f"Could not connect to OpenRouteService: {e}")

def generate_narrative_with_rag(request: models.JourneyRequest) -> models.JourneyNarrative:
    llm = get_llm()
    embeddings_model = get_embeddings_model()
    user_prefs = knowledge_base.get_user_preferences(request.user_id)
    preferences_text = f"This user's known preferences are: Likes: {user_prefs.get('likes', [])}, Dislikes: {user_prefs.get('dislikes', [])}."
    query_embedding = embeddings_model.embed_query(request.query)
    context = knowledge_base.search_knowledge_base(query_embedding=[query_embedding])
    parser = PydanticOutputParser(pydantic_object=models.JourneyNarrative)
    prompt = f"""...""" # Your full prompt
    try:
        ai_response = llm.invoke(prompt)
        parsed_response = parser.parse(ai_response.content)
        return parsed_response
    except ValidationError as e:
        raise Exception(f"Failed to generate a valid narrative from the AI model: {e}")
        
