# main.py

import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import numpy as np
from dotenv import load_dotenv
import traceback
import os # <-- Import os

from sentence_transformers import SentenceTransformer
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser

from app import services, models, knowledge_base

# --- 1. INITIALIZATION ---
load_dotenv()
if 'models_initialized' not in st.session_state:
    with st.spinner("Warming up the AI storyteller... This may take a moment on first load."):
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        
        # THE FIX: Add a timeout to the Google LLM client
        client_options = {"api_key": GEMINI_API_KEY}
        transport_options = {"timeout": 60} # Give up after 60 seconds
        
        st.session_state.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            transport="rest", # Use REST instead of gRPC for better compatibility
            client_options=client_options,
            transport_options=transport_options
        )
        
        st.session_state.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        st.session_state.parser = PydanticOutputParser(pydantic_object=models.JourneyNarrative)
        st.session_state.models_initialized = True

# --- 2. PAGE CONFIGURATION ---
st.set_page_config(page_title="UrbanScribe", page_icon="🗺️", layout="wide", initial_sidebar_state="expanded")

# --- 3. SESSION STATE FOR JOURNEY DATA ---
if "start_location" not in st.session_state: st.session_state.start_location = None
if "journey_created" not in st.session_state: st.session_state.journey_created = False
if "route_data" not in st.session_state: st.session_state.route_data = None
if "narrative" not in st.session_state: st.session_state.narrative = None
if "last_error" not in st.session_state: st.session_state.last_error = None

# --- 4. GET USER'S LOCATION ---
if st.session_state.start_location is None:
    location = get_geolocation()
    if location:
        st.session_state.start_location = {'lat': location['coords']['latitude'], 'lng': location['coords']['longitude']}
        st.rerun()

# --- 5. SIDEBAR (USER INPUT) ---
with st.sidebar:
    st.title("UrbanScribe")
    st.markdown("Your AI-powered travel companion.")
    st.divider()

    st.subheader("1. Describe Your Journey")
    query = st.text_area("What kind of journey?", "A quiet walk with lots of historical relevance", height=100, placeholder="e.g., 'A vibrant market tour'")

    st.subheader("2. Choose Your Destination")
    selected_city = st.selectbox("Select City/Region:", ("Nsukka", "Enugu", "Addis Ababa", "Nairobi", "Lagos"))
    
    poi_list = knowledge_base.get_pois_by_city(selected_city)
    
    if poi_list:
        poi_choices_dict = {poi['name']: poi['_id'] for poi in poi_list}
        destination_name = st.selectbox("Choose Destination:", options=list(poi_choices_dict.keys()))
        destination_poi_id = poi_choices_dict.get(destination_name)
    else:
        destination_name, destination_poi_id = None, None
        st.warning(f"No destinations found for {selected_city}.")

    st.divider()
    if st.button("Create My Journey", type="primary", use_container_width=True, disabled=(not destination_poi_id)):
        st.session_state.last_error = None
        st.session_state.journey_created = False
        
        if st.session_state.start_location:
            with st.spinner("Crafting your personalized story..."):
                # We now wrap each step in its own try/except block
                route_data = None
                narrative = None
                
                try:
                    # --- STEP A: GET ROUTE ---
                    print("--- MAIN: Getting route...")
                    destination_poi = knowledge_base.get_poi_by_id(destination_poi_id)
                    end_lat = destination_poi['location']['coordinates'][1]
                    end_lon = destination_poi['location']['coordinates'][0]
                    start_lat_rounded = round(st.session_state.start_location['lat'], 5)
                    start_lon_rounded = round(st.session_state.start_location['lng'], 5)
                    end_lat_rounded = round(end_lat, 5)
                    end_lon_rounded = round(end_lon, 5)
                    
                    route_data = services.get_route_from_ors(start_lon_rounded, start_lat_rounded, end_lon_rounded, end_lat_rounded)
                    print("--- MAIN: Route received successfully.")

                    # --- STEP B: GET NARRATIVE ---
                    print("--- MAIN: Getting narrative...")
                    request = models.JourneyRequest(
                        user_id="hackathon_user_01", latitude=start_lat_rounded, longitude=start_lon_rounded,
                        city=selected_city, query=query, destination_poi_id=destination_poi_id
                    )
                    narrative = services.generate_narrative_with_rag(request)
                    print("--- MAIN: Narrative received successfully.")

                    # --- STEP C: SUCCESS ---
                    if route_data and narrative:
                        st.session_state.route_data = route_data
                        st.session_state.narrative = narrative
                        st.session_state.journey_created = True
                        print("--- MAIN: Journey created. Rerunning.")
                        st.rerun()
                    else:
                        # This case should not happen, but it's good practice
                        st.session_state.last_error = "Failed to get both route and narrative."
                        st.rerun()

                except Exception as e:
                    print("---! MAIN: AN ERROR OCCURRED !---")
                    traceback.print_exc()
                    st.session_state.last_error = f"{e}"
                    st.rerun()
        else:
            st.warning("Please click on the map to set a starting point first.")

    if st.session_state.last_error:
        st.error(st.session_state.last_error)

# --- 6. MAIN PANEL (MAP AND STORY) ---
# (This part of the code is correct and does not need changes)
st.subheader("Interactive Map")
if st.session_state.start_location:
    st.success(f"Start Location Set: {st.session_state.start_location['lat']:.4f}, {st.session_state.start_location['lng']:.4f}")
else:
    st.info("Click on the map to set your starting location.")

map_center = [st.session_state.start_location['lat'], st.session_state.start_location['lng']] if st.session_state.start_location else [6.855, 7.38]
m = folium.Map(location=map_center, zoom_start=15)

if st.session_state.start_location:
    folium.Marker([st.session_state.start_location['lat'], st.session_state.start_location['lng']], popup="Your Start", tooltip="Your Start", icon=folium.Icon(color="blue", icon="user")).add_to(m)

if st.session_state.journey_created and st.session_state.route_data:
    points = st.session_state.route_data['points']
    swapped_points = [(p[1], p[0]) for p in points]
    folium.PolyLine(swapped_points, color="red", weight=5, opacity=0.8).add_to(m)
    folium.Marker(swapped_points[-1], popup="Destination", tooltip="Destination", icon=folium.Icon(color="red", icon="flag")).add_to(m)
    m.fit_bounds(swapped_points)

map_data = st_folium(m, width='100%', height=450)

if map_data and map_data.get("last_clicked"):
    clicked_coords = map_data["last_clicked"]
    st.session_state.start_location = clicked_coords
    st.rerun()

st.divider()

st.subheader("Your Generated Journey")
if st.session_state.journey_created and st.session_state.narrative:
    narrative = st.session_state.narrative
    route_data = st.session_state.route_data
    metric_col1, metric_col2 = st.columns(2)
    try:
        duration_min = route_data['duration'] / 60
        distance_km = route_data['distance'] / 1000
        with metric_col1: st.metric(label="🚶‍♀️ Est. Walk Time", value=f"{duration_min:.0f} min")
        with metric_col2: st.metric(label="📏 Distance", value=f"{distance_km:.2f} km")
    except (KeyError, IndexError):
        st.info("Route metrics not available.")
    st.subheader(narrative.title)
    st.info(narrative.narrative)
    st.success(f"**Fun Fact:** {narrative.fun_fact}")
else:
    st.info("Your journey's story and details will appear here.")
