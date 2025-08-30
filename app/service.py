# app/services.py
import os
import httpx
from . import models
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser

# Initialize clients once
llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=os.getenv("GEMINI_API_KEY"))
MAPTILER_API_KEY = os.getenv("MAPTILER_API_KEY")

async def get_route_from_maptiler(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> dict:
    """Makes an API call to MapTiler to get the route."""
    start_coords = f"{start_lon},{start_lat}"
    end_coords = f"{end_lon},{end_lat}"
    route_url = f"https://api.maptiler.com/routing/v1/foot?waypoints={start_coords};{end_coords}&steps=true&overview=full&key={MAPTILER_API_KEY}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(route_url)
        response.raise_for_status()
        return response.json()

async def generate_simplified_narrative(request: models.JourneyRequest, destination_name: str) -> models.JourneyNarrative:
    """Generates a simple narrative using the LLM with structured output."""
    
    # 1. Set up the Pydantic parser to structure the LLM's output
    parser = PydanticOutputParser(pydantic_object=models.JourneyNarrative)

    # 2. Create a simple prompt without knowledge base context
    prompt = f"""
    You are UrbanScribe, a city guide. Create a short, encouraging narrative for a user starting a walk in {request.city}.
    The user's goal is: "{request.query}"
    They are walking towards: "{destination_name}"

    {parser.get_format_instructions()}
    """

    # 3. Call the LLM and parse the output
    response = await llm.ainvoke(prompt)
    parsed_response = parser.parse(response.content)
    
    return parsed_response
  
