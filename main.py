# main.py

import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import numpy as np
from dotenv import load_dotenv
import traceback
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from sentence_transformers import SentenceTransformer
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser

from app import services, models, knowledge_base

# --- 1. INITIALIZATION & PAGE CONFIG ---
st.set_page_config(page_title="Hometown Atlas", page_icon="🗺️", layout="wide", initial_sidebar_state="expanded")
load_dotenv()

@st.cache_resource
def initialize_models():
    """
    Loads and caches all necessary AI models, parsers, and credentials.
    This function runs only once per session.
    """
    # --- PERMANENT AUTHENTICATION FIX ---
    # Create a dummy credentials object. This forces the Google library to bypass
    # the metadata server check and rely solely on the provided API key.
    # This is the definitive fix for the `metadata.google.internal` timeout error.
    dummy_credentials = Credentials(
        token=None,
        refresh_token=None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id="dummy",
        client_secret="dummy",
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    st.session_state.llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=GEMINI_API_KEY,
        credentials=dummy_credentials, # Use the dummy credentials
        transport="rest",
        request_timeout=120 # Increased timeout for long generations
    )
    st.session_state.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    st.session_state.parser = PydanticOutputParser(pydantic_object=models.JourneyNarrative)

# Run model initialization
initialize_models()

# --- 2. SESSION STATE MANAGEMENT ---
# Initialize all necessary keys for the app's state to prevent errors on first run.
if "start_location" not in st.session_state: st.session_state.start_location = None
if "selected_city" not in st.session_state: st.session_state.selected_city = "Nsukka"
if "selected_destination_id" not in st.session_state: st.session_state.selected_destination_id = None
if "journey_narrative" not in st.session_state: st.session_state.journey_narrative = None
if "journey_route_data" not in st.session_state: st.session_state.journey_route_data = None
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Welcome! I am your personal tour guide. Ask me anything about your journey."}]
if "user_id" not in st.session_state: st.session_state.user_id = "hackathon_user_01" # Static user ID for this version

# --- 3. SIDEBAR (CONTROLS & FILTERS) ---
with st.sidebar:
    st.title("🌍 Hometown Atlas")
    st.markdown("Your AI-powered tourist companion.")
    st.divider()

    # Section 1: Destination Selection
    st.subheader("1. Select Your Destination")
    st.session_state.selected_city = st.selectbox("Select City/Region:", ("Nsukka", "Enugu", "Addis Ababa", "Nairobi", "Kenya","Ethiopia"))

    # Section 2: Advanced Filtering
    st.subheader("2. Filter Your Options")
    available_budgets = ["Any"] + knowledge_base.get_unique_budgets_by_city(st.session_state.selected_city)
    selected_budget = st.selectbox("Budget Level:", options=available_budgets)

    available_tags = knowledge_base.get_unique_tags_by_city(st.session_state.selected_city)
    selected_tags = st.multiselect("Interests / Tags:", options=available_tags)

    # Dynamically filtered list of Points of Interest (POIs)
    poi_list = knowledge_base.get_pois_by_city(st.session_state.selected_city, selected_tags, selected_budget)
    poi_choices_dict = {poi['name']: poi['_id'] for poi in poi_list}

    if poi_list:
        destination_name = st.selectbox(
            "Choose Destination:",
            options=[""] + list(poi_choices_dict.keys()), # Add a blank default option
            key="destination_select",
            index=0 # Default to the blank option
        )
        if destination_name:
            st.session_state.selected_destination_id = poi_choices_dict.get(destination_name)
        else:
            st.session_state.selected_destination_id = None
    else:
        st.warning("No destinations match your filters.")
        st.session_state.selected_destination_id = None

    # Journey description input
    st.subheader("3. Describe Your Journey")
    journey_query = st.text_area(
        "What kind of experience are you looking for?",
        "A quiet and scenic walk with some historical context.",
        height=100
    )

    # Main action button
    st.divider()
    create_journey_button = st.button("Create My Journey", type="primary", use_container_width=True)

# --- 4. MAIN PANEL (UI TABS) ---
# Use tabs to separate the main journey view from the conversational chat
tab1, tab2 = st.tabs(["📍 Your Journey", "💬 Talk with the Guide"])

# --- TAB 1: JOURNEY DISPLAY ---
with tab1:
    st.subheader("🗺️ Hometown Atlas Interactive Map")

    # Get user's location once at the start of the session
    if st.session_state.start_location is None:
        location = get_geolocation()
        if location:
            st.session_state.start_location = {'lat': location['coords']['latitude'], 'lng': location['coords']['longitude']}
            st.rerun() # Rerun to update the map with the new location

    # Set default map center or use user's location
    map_center = [st.session_state.start_location['lat'], st.session_state.start_location['lng']] if st.session_state.start_location else [6.855, 7.38]
    m = folium.Map(location=map_center, zoom_start=14)

    # Add user's start location marker if available
    if st.session_state.start_location:
        folium.Marker(
            [st.session_state.start_location['lat'], st.session_state.start_location['lng']],
            popup="Your Location", tooltip="Your Location", icon=folium.Icon(color="blue", icon="user")
        ).add_to(m)

    # --- JOURNEY CREATION LOGIC ---
    # This block runs when the user clicks the main button in the sidebar
    if create_journey_button:
        if not st.session_state.selected_destination_id:
            st.error("Please choose a destination from the sidebar.")
        elif not st.session_state.start_location:
            st.error("Could not determine your starting location. Please allow location access and refresh.")
        else:
            with st.spinner("Crafting your personalized journey... This may take a moment."):
                try:
                    # 1. Fetch all necessary data points
                    start_lat = round(st.session_state.start_location['lat'], 5)
                    start_lon = round(st.session_state.start_location['lng'], 5)
                    dest_poi = knowledge_base.get_poi_by_id(st.session_state.selected_destination_id)
                    end_lat = round(dest_poi['location']['coordinates'][1], 5)
                    end_lon = round(dest_poi['location']['coordinates'][0], 5)

                    # 2. Call services to get route and generate narrative
                    route_data = services.get_route_from_ors(start_lon, start_lat, end_lon, end_lat)
                    request = models.JourneyRequest(
                        user_id=st.session_state.user_id, latitude=start_lat, longitude=start_lon,
                        city=st.session_state.selected_city, query=journey_query,
                        destination_poi_id=st.session_state.selected_destination_id
                    )
                    narrative = services.generate_narrative_with_rag(request, dest_poi['name'])

                    # 3. Store results in session state to display them
                    st.session_state.journey_narrative = narrative
                    st.session_state.journey_route_data = route_data
                    st.rerun() # Rerun to display the new results

                except Exception as e:
                    st.error(f"An error occurred while creating your journey: {e}")
                    traceback.print_exc()

    # --- DISPLAY THE GENERATED JOURNEY ---
    # This block draws the route and narrative if they exist in the session state
    if st.session_state.journey_route_data and st.session_state.journey_narrative:
        # Draw destination marker
        dest_poi = knowledge_base.get_poi_by_id(st.session_state.selected_destination_id)
        folium.Marker(
            [dest_poi['location']['coordinates'][1], dest_poi['location']['coordinates'][0]],
            popup=dest_poi['name'], tooltip=dest_poi['name'], icon=folium.Icon(color="red", icon="flag")
        ).add_to(m)

        # Draw route polyline
        points = st.session_state.journey_route_data['points']
        swapped_points = [(p[1], p[0]) for p in points]
        folium.PolyLine(swapped_points, color="red", weight=5, opacity=0.8).add_to(m)
        m.fit_bounds(swapped_points) # Auto-zoom to fit the entire route

    # Render the Folium map
    st_folium(m, width='100%', height=350)
    st.divider()

    # Display the narrative and metrics below the map
    if st.session_state.journey_narrative and st.session_state.journey_route_data:
        narrative = st.session_state.journey_narrative
        route_data = st.session_state.journey_route_data

        st.subheader("Your Generated Journey")

        # Display metrics (Time and Distance)
        metric_col1, metric_col2 = st.columns(2)
        duration_min = route_data['duration'] / 60
        distance_km = route_data['distance'] / 1000
        metric_col1.metric(label="🚶‍♀️ Est. Walk Time", value=f"{duration_min:.0f} min")
        metric_col2.metric(label="📏 Distance", value=f"{distance_km:.2f} km")

        # Display narrative content
        st.markdown(f"### {narrative.title}")
        st.markdown(f"*{narrative.location_awareness}*")
        st.markdown(narrative.narrative)
        st.success(f"**Fun Fact:** {narrative.fun_fact}")

        # Display feedback buttons
        st.divider()
        st.markdown("**Did you find this journey useful?**")
        feedback_col1, feedback_col2, _ = st.columns([1, 1, 4])

        if feedback_col1.button("👍 Yes", key="like_journey"):
            with st.spinner("Learning from your feedback..."):
                reflection_request = models.ReflectionRequest(
                    user_id=st.session_state.user_id,
                    original_query=journey_query,
                    journey_title=narrative.title,
                    user_feedback="liked"
                )
                services.reflect_and_update_preferences(reflection_request)

        if feedback_col2.button("👎 No", key="dislike_journey"):
            with st.spinner("Learning from your feedback..."):
                reflection_request = models.ReflectionRequest(
                    user_id=st.session_state.user_id,
                    original_query=journey_query,
                    journey_title=narrative.title,
                    user_feedback="disliked"
                )
                services.reflect_and_update_preferences(reflection_request)
    else:
        st.info("Click 'Create My Journey' in the sidebar to generate your personalized travel narrative.")


# --- TAB 2: CHAT INTERFACE ---
with tab2:
    st.subheader("Talk with the Tourist Guide")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle new chat input
    if prompt := st.chat_input("Ask a follow-up question..."):
        # Add user message to history and display it
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate assistant's response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # The context for the chat is the previously generated journey
                    if st.session_state.journey_narrative:
                        conversation_history = " ".join([m['content'] for m in st.session_state.messages])
                        dest_poi = knowledge_base.get_poi_by_id(st.session_state.selected_destination_id)

                        # Use a dedicated chat generation service function
                        response_content = services.generate_chat_response(
                            user_id=st.session_state.user_id,
                            city=st.session_state.selected_city,
                            destination_name=dest_poi['name'],
                            journey_narrative=st.session_state.journey_narrative,
                            conversation_history=conversation_history
                        )
                        st.markdown(response_content)
                        st.session_state.messages.append({"role": "assistant", "content": response_content})
                    else:
                        st.warning("Please create a journey first before asking questions.")
                        st.session_state.messages.append({"role": "assistant", "content": "I can only answer questions about a journey after you've created one. Please go to the 'Your Journey' tab and click 'Create My Journey'."})

                except Exception as e:
                    error_message = f"I'm sorry, I encountered an error: {e}"
                    st.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
                    traceback.print_exc()
            
