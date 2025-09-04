import os
import httpx
import json
import base64
from typing import Dict, Any
from fastapi import HTTPException, UploadFile
from dotenv import load_dotenv

# Import our own modules
from . import models
from . import knowledge_base

# Import LangChain and Google Generative AI components
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.output_parsers import PydanticOutputParser
from langchain_core.messages import HumanMessage
from pydantic import ValidationError

# --- Load Environment Variables & Initialize Clients ---
load_dotenv()
MAPTILER_API_KEY = os.getenv("MAPTILER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize the LLM and Embeddings models once to be reused
# We use "gemini-pro" for chat/text generation
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY)
# We use a specific embeddings model for converting text to vectors
embeddings_model = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001", google_api_key=GEMINI_API_KEY)
# We use the vision model for image analysis
vision_llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=GEMINI_API_KEY)


# ==============================================================================
# 1. External Service Functions (MapTiler)
# ==============================================================================

async def get_route_from_maptiler(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> Dict:
    """
    Makes an asynchronous API call to MapTiler to get a walking route.
    """
    start_coords = f"{start_lon},{start_lat}"
    end_coords = f"{end_lon},{end_lat}"
    route_url = f"https://api.maptiler.com/routing/v1/foot?waypoints={start_coords};{end_coords}&steps=true&overview=full&key={MAPTILER_API_KEY}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(route_url)
            response.raise_for_status()  # Raises an exception for 4XX or 5XX status codes
            return response.json()
        except httpx.HTTPStatusError as e:
            # Provide a more specific error message if MapTiler fails
            raise HTTPException(status_code=e.response.status_code, detail=f"MapTiler API error: {e.response.text}")
        except httpx.RequestError as e:
            # Handle network-related errors
            raise HTTPException(status_code=503, detail=f"Could not connect to MapTiler service: {e}")


# ==============================================================================
# 2. Core Narrative Generation Functions (RAG)
# ==============================================================================

async def generate_narrative_with_rag(request: models.JourneyRequest) -> models.JourneyNarrative:
    """
    The main RAG pipeline to generate a personalized and context-aware journey narrative.
    """
    # 1. Fetch User Preferences (Memory)
    # This is the first step to ensure the entire process is personalized.
    user_prefs = await knowledge_base.get_user_preferences(request.user_id)
    preferences_text = f"This user's known preferences are: Likes: {user_prefs.get('likes', [])}, Dislikes: {user_prefs.get('dislikes', [])}."

    # 2. Create an Embedding of the User's Query
    # This converts the natural language query into a vector for similarity search.
    query_embedding = embeddings_model.embed_query(request.query)

    # 3. Retrieve Relevant Context from the Knowledge Base
    # The vector is used to search the FAISS index for the most relevant information.
    context = knowledge_base.search_knowledge_base(query_embedding=[query_embedding])

    # 4. Set up the Pydantic Parser for Structured Output
    # This forces the LLM to return a clean JSON object matching our model.
    parser = PydanticOutputParser(pydantic_object=models.JourneyNarrative)

    # 5. Construct the Final Prompt for the LLM
    # This prompt brings everything together: the user's goal, their learned preferences,
    # the retrieved context, and the formatting instructions.
    prompt = f"""
    You are UrbanScribe, an intelligent city storyteller. Your task is to create a personalized journey narrative.

    **User's Goal:** "{request.query}"
    
    **User's Profile:** {preferences_text}
    
    **Retrieved Context from Knowledge Base:**
    ---
    {context}
    ---
    
    Based on ALL the information above, generate a compelling and tailored narrative for the user's journey.
    The narrative should directly incorporate the user's preferences and the retrieved context.
    
    **Output Instructions:**
    {parser.get_format_instructions()}
    """

    # 6. Call the LLM and Parse the Output
    try:
        ai_response = await llm.ainvoke(prompt)
        parsed_response = parser.parse(ai_response.content)
        return parsed_response
    except ValidationError as e:
        print(f"LLM output validation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate a valid narrative from the AI model.")


# ==============================================================================
# 3. User Memory and Reflection Functions
# ==============================================================================

async def reflect_and_update_preferences(request: models.ReflectionRequest):
    """
    Performs the reflection step to learn from user feedback and update their profile.
    """
    # 1. Get the user's current preferences to provide context to the LLM
    current_prefs = await knowledge_base.get_user_preferences(request.user_id)

    # 2. Construct the reflection prompt for the LLM
    reflection_prompt = f"""
    You are a user preference analysis AI. Your job is to update a user's preference profile based on their recent activity.

    **Current User Profile:** {current_prefs}
    
    **User's Recent Activity:**
    - Initial Query: "{request.original_query}"
    - Journey Title: "{request.journey_title}"
    - Feedback: "{request.user_feedback}"

    **Your Task:**
    Analyze this interaction. Based on reasonable inferences, update the user's preference profile by adding or modifying their 'likes' and 'dislikes'.
    For example, if the query was about 'quiet parks' and they 'liked' it, add 'quiet' and 'parks' to their likes.
    
    **Respond ONLY with the updated JSON object for the 'preferences' field and nothing else.**
    Example response: {{"likes": ["history", "quiet"], "dislikes": ["crowded"]}}
    """

    # 3. Call the LLM to get the updated profile
    ai_response = await llm.ainvoke(reflection_prompt)
    
    # 4. Safely parse and validate the LLM's JSON response
    try:
        updated_prefs_data = json.loads(ai_response.content)
        # Validate the structure of the LLM's output against our Pydantic model
        validated_prefs = models.UserPreferences(**updated_prefs_data)
    except (json.JSONDecodeError, ValidationError) as e:
        # If the LLM fails to return valid JSON, we log the error and do not update.
        print(f"Error: LLM returned invalid preference JSON for user {request.user_id}. Error: {e}")
        return

    # 5. Save the new, validated preferences back to the database
    await knowledge_base.update_user_preferences(request.user_id, validated_prefs.dict())


# ==============================================================================
# 4. Image-Based Location Functions
# ==============================================================================

async def get_location_from_image(image_file: UploadFile) -> Dict[str, float]:
    """
    Analyzes an image using Gemini Vision to identify the landmark and return its coordinates.
    """
    # 1. Read the image data from the upload
    image_data = await image_file.read()
    base64_image = base64.b64encode(image_data).decode("utf-8")

    # 2. Construct the prompt for the Vision LLM
    vision_prompt = HumanMessage(
        content=[
            {
                "type": "text",
                "text": "You are a world-class location identification expert. Look at this image. Identify the specific landmark, building, or monument shown. Based on your knowledge, what are the approximate latitude and longitude coordinates of this landmark? Respond ONLY with a valid JSON object containing 'latitude' and 'longitude' keys and nothing else. For example: {\"latitude\": 6.86, \"longitude\": 7.40}"
            },
            {
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{base64_image}"
            },
        ]
    )
    
    # 3. Call the Vision LLM and parse the response
    try:
        ai_response = await vision_llm.ainvoke([vision_prompt])
        location_data = json.loads(ai_response.content)
        if 'latitude' not in location_data or 'longitude' not in location_data:
            raise KeyError("Missing latitude or longitude in response.")
        return location_data
    except (json.JSONDecodeError, KeyError, ValidationError) as e:
        print(f"Error identifying location from image: {e}")
        raise HTTPException(status_code=500, detail="Could not identify a valid location from the provided image.")

