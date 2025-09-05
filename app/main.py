from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import our own application modules
from . import model
from . import service
from . import knowledge_base

# --- Application Initialization ---
# Load environment variables from the .env file
load_dotenv()

# Create the FastAPI app instance
# We can add metadata like title and version, which will show up in the auto-generated docs
app = FastAPI(
    title="UrbanScribe API",
    version="1.0.0",
    description="The backend service for UrbanScribe, the intelligent city storyteller.",
)

# --- CORS Configuration ---
origins = [
    "http://localhost",     
    "http://localhost:3000", 
    "http://localhost:8080", 
    "http://localhost:5173", 
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of origins that are allowed to make requests
    allow_credentials=True, # Allows cookies to be included in requests (useful for auth)
    allow_methods=["*"],    # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],    # Allows all headers
)


# --- API Endpoints ---

@app.post("/generate-journey", response_model=models.JourneyResponse)
async def generate_journey(request: models.JourneyRequest):
    """
    This is the primary endpoint for generating a personalized journey.
    
    It receives the user's current location, destination, and query,
    then orchestrates the full RAG pipeline to return a complete journey plan.
    """
    try:
        # 1. Get the destination POI details from the database
        destination_poi = await knowledge_base.get_poi_by_id(request.destination_poi_id)
        if not destination_poi:
            raise HTTPException(status_code=404, detail=f"Destination POI with ID '{request.destination_poi_id}' not found.")
        
        end_lon = destination_poi['location']['coordinates'][0]
        end_lat = destination_poi['location']['coordinates'][1]

        # 2. Get the walking route from the MapTiler service
        route_data = await services.get_route_from_maptiler(
            start_lon=request.longitude,
            start_lat=request.latitude,
            end_lon=end_lon,
            end_lat=end_lat
        )

        # 3. Generate the personalized, context-aware narrative using the RAG pipeline
        structured_narrative = await services.generate_narrative_with_rag(request)

        # 4. Combine the narrative and route data into the final response
        return models.JourneyResponse(
            structured_narrative=structured_narrative,
            route_data=route_data
        )
    except HTTPException as e:
        # Re-raise HTTPExceptions to let FastAPI handle them
        raise e
    except Exception as e:
        # Catch any other unexpected errors and return a generic 500 error
        print(f"An unexpected error occurred in /generate-journey: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")


@app.post("/reflect-on-journey", status_code=204)
async def reflect_on_journey(request: models.ReflectionRequest):
    """
    This endpoint enables the self-reflective memory of the application.
    
    The frontend calls this *after* a journey is completed, providing feedback.
    The backend then uses this feedback to update the user's preference profile.
    It returns a 204 "No Content" response as it's a background task.
    """
    try:
        await services.reflect_and_update_preferences(request)
        # No need to return anything, the status_code=204 handles it.
        return
    except Exception as e:
        # Even for a background task, it's good to log if something goes wrong
        print(f"An error occurred in /reflect-on-journey: {e}")
        # We don't raise an HTTPException here as the client doesn't need to know about the failure.
        # The process fails silently on the backend, but we log it for debugging.


@app.post("/plan-journey-from-image", response_model=models.JourneyResponse)
async def plan_journey_from_image(
    user_id: str = Form(...),
    city: str = Form(...),
    query: str = Form(...),
    destination_poi_id: str = Form(...),
    image: UploadFile = File(...)
):
    """
    An advanced endpoint that plans a journey starting from a location identified in an image.
    
    It uses a multipart/form-data request to accept both text fields and an image file.
    """
    try:
        # 1. Identify the starting coordinates from the uploaded image
        start_location = await services.get_location_from_image(image)
        start_lat = start_location['latitude']
        start_lon = start_location['longitude']

        # 2. Get the destination POI details from the database
        destination_poi = await knowledge_base.get_poi_by_id(destination_poi_id)
        if not destination_poi:
            raise HTTPException(status_code=404, detail=f"Destination POI with ID '{destination_poi_id}' not found.")
        
        end_lon = destination_poi['location']['coordinates'][0]
        end_lat = destination_poi['location']['coordinates'][1]

        # 3. Get the walking route from MapTiler
        route_data = await services.get_route_from_maptiler(
            start_lon=start_lon,
            start_lat=start_lat,
            end_lon=end_lon,
            end_lat=end_lat
        )

        # 4. Create a JourneyRequest object to pass to the RAG service
        # This allows us to reuse our main narrative generation logic
        journey_request_data = models.JourneyRequest(
            user_id=user_id,
            latitude=start_lat,
            longitude=start_lon,
            city=city,
            query=query,
            destination_poi_id=destination_poi_id
        )
        
        # 5. Generate the personalized narrative
        structured_narrative = await services.generate_narrative_with_rag(journey_request_data)

        # 6. Combine and return the final response
        return models.JourneyResponse(
            structured_narrative=structured_narrative,
            route_data=route_data
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"An unexpected error occurred in /plan-journey-from-image: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")


# --- Health Check Endpoint ---
@app.get("/health", status_code=200)
def health_check():
    """A simple endpoint to verify that the API is running."""
    return {"status": "ok"}

