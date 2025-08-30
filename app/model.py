from pydantic import BaseModel, Field
from typing import List, Optional

# ==============================================================================
# 1. Models for Incoming API Requests
# ==============================================================================

class JourneyRequest(BaseModel):
    """
    Defines the exact structure of the JSON data the frontend MUST send
    when it calls the /generate-journey endpoint.
    Pydantic will automatically validate the incoming request to ensure it has
    these fields and that they are the correct data type.
    """
    latitude: float
    longitude: float
    city: str
    query: str
    destination_poi_id: str


# ==============================================================================
# 2. Models for Structuring LLM Output
# ==============================================================================

class JourneyNarrative(BaseModel):
    """
    This is our "schema" or "template" for the AI's response.
    We will use this with LangChain's PydanticOutputParser to force the LLM
    to return a JSON object that looks exactly like this.
    The 'description' in Field() helps the LLM understand what kind of content
    to generate for each field.
    """
    title: str = Field(description="A short, catchy title for the journey, like 'The Spice Route of Enugu' or 'A Walk Through History'.")
    narrative: str = Field(description="The main story for the user's walk. It should be 2-4 sentences long, engaging, and weave together the user's goal with local context.")
    fun_fact: str = Field(description="A single, interesting, and brief fun fact related to the user's location or journey.")
    location_awareness: str = Field(description="A single sentence that makes the user feel seen, mentioning a nearby landmark or street to show the AI is aware of their surroundings.")


# ==============================================================================
# 3. Models for Outgoing API Responses
# ==============================================================================

class JourneyResponse(BaseModel):
    """
    Defines the exact structure of the final JSON response our backend will
    send back to the frontend.
    This ensures the frontend team knows exactly what to expect.
    It contains the structured narrative from the LLM and the raw route data.
    """
    structured_narrative: JourneyNarrative
    route_data: dict # This will hold the full, raw JSON response from the MapTiler API.
    
