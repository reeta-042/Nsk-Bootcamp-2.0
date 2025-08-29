#Import the necessary libraries
import os
from fastapi import FastAPI
from dotenv import load_dotenv

# 2. Load the environment variables from the .env file
load_dotenv()

# 3. Create an instance of the FastAPI application
app = FastAPI()

# 4. Retrieve the API keys from the environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MAPTILER_API_KEY = os.getenv("MAPTILER_API_KEY")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 5. Define a basic "root" endpoint
@app.get("/")
def read_root():
    # This function returns a simple JSON response.
    return {"status": "ok", "message": "Welcome to the our NSK Bootcamp project!"}

# 6. An endpoint to check if keys are loaded

@app.get("/debug-keys")
def check_keys():
    # We check if the key is not None and show only the first few characters
    return {
        "groq_key_loaded": "Yes" if GROQ_API_KEY else "No",
        "maptiler_key_loaded": "Yes" if MAPTILER_API_KEY else "No",
        "cloudinary_key_loaded": "Yes" if CLOUDINARY_API_KEY else "No",
        "gemini_key_loaded": "Yes" if GEMINI_API_KEY else "No",
    }

