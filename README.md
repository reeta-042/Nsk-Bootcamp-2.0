# 🌍 Hometown Atlas - Your AI Powered Tourist Companion

Hometown Atlas is an intelligent, AI-powered travel companion that creates personalized walking tours and narratives for any destination. Built with Streamlit and powered by Google's Gemini 2.5 Pro, it's designed to help users discover the hidden gems and stories of their city.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nsk-bootcamp-tourism.streamlit.app/) 👈 Check out Home town Atlas on streamlit here 
---

## Features

*   **Dynamic Journey Generation:** Simply select a destination, and the AI crafts a unique walking narrative, complete with estimated time and distance.
*   **Interactive Map:** Visualizes your starting point and the generated route to your destination, powered by OpenRouteService.
*   **AI-Powered Tourist Guide:** A built-in chatbot allows you to ask follow-up questions about your destination, look for specific things (like local delicacies!), and get context-aware answers.
*   **Advanced Filtering:** Easily filter destinations by interests, tags (e.g., "history", "bakery"), and budget level.
*   **Self-Learning Preferences:** The app learns from your feedback (👍/👎) to better tailor future suggestions to your tastes.
*   **Live Geolocation:** Automatically detects your starting location for seamless route planning.

---

## Tech Stack

*   **Frontend:** [Streamlit](https://streamlit.io/) - For the interactive web application UI.
*   **Backend & Orchestration:** Python
*   **LLM (Narrative & Chat):** [Google Gemini 2.5 Pro](https://deepmind.google/technologies/gemini/) via `langchain-google-genai`.
*   **Routing:** [OpenRouteService](https://openrouteservice.org/) - For generating pedestrian routes.
*   **Database:** [MongoDB](https://www.mongodb.com/) - For storing Point of Interest (POI) data and user preferences.
*   **Vector Search (RAG):** [FAISS](https://faiss.ai/) - For efficient similarity search on our knowledge base.
*   **Embeddings:** `Sentence-Transformers` - For converting text queries into vector embeddings locally.

---

## 🚀 How to Run

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/hometown-atlas.git
    cd hometown-atlas
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **Set up your environment variables:**
    Create a file named `.env` in the root directory and add your API keys:
    ```
    MONGO_URI="your_mongodb_connection_string"
    GOOGLE_API_KEY="your_google_gemini_api_key"
    ORS_API_KEY="your_openrouteservice_api_key"
    ```

4.  **Run the Streamlit app:**
    ```bash
    streamlit run main.py
    ```

---


