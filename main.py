# main.py

import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import numpy as np
from dotenv import load_dotenv
import traceback
import os

from sentence_transformers import SentenceTransformer
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser

from app import services, models, knowledge_base

# --- 1. INITIALIZATION & PAGE CONFIG ---
st.set_page_config(page_title="Hometown Atlas", page_icon="🗺️", layout="wide", initial_sidebar_state="expanded")
load_dotenv()

def initialize_models():
    """Loads and caches all necessary AI models and parsers."""
    if 'models_initialized' not in st.session_state:
        with st.spinner("Warming up The Maps 🗺️..."):
            GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
            st.session_state.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=GEMINI_API_KEY,
                transport="rest",
                model_kwargs={"request_timeout": 60}
            )
            st.session_state.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            st.session_state.parser = PydanticOutputParser(pydantic_object=models.JourneyNarrative)
            st.session_state.models_initialized = True

initialize_models()

# --- 2. SESSION STATE MANAGEMENT ---
# Initialize all necessary keys for the app's state
if "start_location" not in st.session_state: st.session_state.start_location = None
if "selected_city" not in st.session_state: st.session_state.selected_city = "Nsukka"
if "selected_destination_id" not in st.session_state: st.session_state.selected_destination_id = None
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Welcome to Hometown Atlas! Where would you like to go today?"}]
if "last_journey_info" not in st.session_state: st.session_state.last_journey_info = None

# --- 3. SIDEBAR (CONTROLS & FILTERS) ---
with st.sidebar:
    st.title("🌍 Hometown Atlas")
    st.markdown("Your AI-powered tourist companion.")
    st.divider()

    # Location and Destination Selection
    st.subheader("1. Select Your Destination")
    st.session_state.selected_city = st.selectbox("Select City/Region:", ("Nsukka", "Enugu", "Addis Ababa", "Nairobi", "Kenya","Ethiopia"))
    
    # Advanced Filters
    st.subheader("2. Filter Your Options")
    
    # Budget Filter
    available_budgets = ["Any"] + knowledge_base.get_unique_budgets_by_city(st.session_state.selected_city)
    selected_budget = st.selectbox("Budget Level:", options=available_budgets)
    
    # Tags Filter
    available_tags = knowledge_base.get_unique_tags_by_city(st.session_state.selected_city)
    selected_tags = st.multiselect("Interests / Tags:", options=available_tags)

    # Dynamically Filtered POI List
    poi_list = knowledge_base.get_pois_by_city(st.session_state.selected_city, selected_tags, selected_budget)
    poi_choices_dict = {poi['name']: poi['_id'] for poi in poi_list}
    
    if poi_list:
        destination_name = st.selectbox(
            "Choose Destination:", 
            options=list(poi_choices_dict.keys()), 
            key="destination_select"
        )
        st.session_state.selected_destination_id = poi_choices_dict.get(destination_name)
    else:
        st.warning("No destinations match your filters.")
        st.session_state.selected_destination_id = None

# --- 4. MAIN PANEL (MAP & CHAT) ---

# Get user's location once at the start
if st.session_state.start_location is None:
    location = get_geolocation()
    if location:
        st.session_state.start_location = {'lat': location['coords']['latitude'], 'lng': location['coords']['longitude']}
        st.rerun()

# Map Display
st.subheader(" HomeTown Atlas Interactive Map")
map_center = [st.session_state.start_location['lat'], st.session_state.start_location['lng']] if st.session_state.start_location else [6.855, 7.38]
m = folium.Map(location=map_center, zoom_start=14)

# Add user's start location marker
if st.session_state.start_location:
    folium.Marker([st.session_state.start_location['lat'], st.session_state.start_location['lng']], popup="Your Start", tooltip="Your Start", icon=folium.Icon(color="blue", icon="user")).add_to(m)

# Live Preview: Add destination marker if one is selected
if st.session_state.selected_destination_id:
    dest_poi = knowledge_base.get_poi_by_id(st.session_state.selected_destination_id)
    if dest_poi:
        dest_lat = dest_poi['location']['coordinates'][1]
        dest_lon = dest_poi['location']['coordinates'][0]
        folium.Marker([dest_lat, dest_lon], popup=dest_poi['name'], tooltip=dest_poi['name'], icon=folium.Icon(color="red", icon="flag")).add_to(m)

# Draw route if a journey has been created
if st.session_state.get("last_journey_info") and "route_data" in st.session_state.last_journey_info:
    route_data = st.session_state.last_journey_info["route_data"]
    points = route_data['points']
    swapped_points = [(p[1], p[0]) for p in points]
    folium.PolyLine(swapped_points, color="red", weight=5, opacity=0.8).add_to(m)
    m.fit_bounds(swapped_points)

st_folium(m, width='100%', height=350)
st.divider()

# Chat Interface
st.subheader("Talks with the Tourist guide")

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display journey details and feedback buttons if the message is a journey
        if message.get("is_journey"):
            journey_info = st.session_state.last_journey_info
            route_data = journey_info["route_data"]
            
            metric_col1, metric_col2 = st.columns(2)
            duration_min = route_data['duration'] / 60
            distance_km = route_data['distance'] / 1000
            with metric_col1: st.metric(label="🚶‍♀️ Est. Walk Time", value=f"{duration_min:.0f} min")
            with metric_col2: st.metric(label="📏 Distance", value=f"{distance_km:.2f} km")
            
            st.markdown("---")
            st.markdown("**Did you find this journey useful?**")
            feedback_col1, feedback_col2, _ = st.columns([1, 1, 4])
            
            with feedback_col1:
                if st.button("👍 Yes", key=f"like_{journey_info['id']}"):
                    with st.spinner("Learning from your feedback..."):
                        reflection_request = models.ReflectionRequest(**journey_info, user_feedback="liked")
                        services.reflect_and_update_preferences(reflection_request)
            with feedback_col2:
                if st.button("👎 No", key=f"dislike_{journey_info['id']}"):
                    with st.spinner("Learning from your feedback..."):
                        reflection_request = models.ReflectionRequest(**journey_info, user_feedback="disliked")
                        services.reflect_and_update_preferences(reflection_request)

# Accept user input
if prompt := st.chat_input("What kind of journey are you looking for?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant logic
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            if not st.session_state.selected_destination_id:
                st.error("Please select a destination from the sidebar first.")
            elif not st.session_state.start_location:
                st.error("Could not determine your starting location. Please allow location access.")
            else:
                try:
                    # 1. Get all necessary data
                    start_lat = round(st.session_state.start_location['lat'], 5)
                    start_lon = round(st.session_state.start_location['lng'], 5)
                    
                    dest_poi = knowledge_base.get_poi_by_id(st.session_state.selected_destination_id)
                    end_lat = round(dest_poi['location']['coordinates'][1], 5)
                    end_lon = round(dest_poi['location']['coordinates'][0], 5)
                    
                    # 2. Call services to get route and narrative
                    route_data = services.get_route_from_ors(start_lon, start_lat, end_lon, end_lat)
                    
                    conversation_history = " ".join([m['content'] for m in st.session_state.messages])
                    request = models.JourneyRequest(
                        user_id="hackathon_user_01", latitude=start_lat, longitude=start_lon,
                        city=st.session_state.selected_city, query=prompt, 
                        destination_poi_id=st.session_state.selected_destination_id
                    )
                    narrative = services.generate_narrative_with_rag(request, dest_poi['name'], conversation_history)
                    
                    # 3. Format the response
                    response_content = f"### {narrative.title}\n\n"
                    response_content += f"*{narrative.location_awareness}*\n\n"
                    response_content += f"{narrative.narrative}\n\n"
                    response_content += f"**Fun Fact:** {narrative.fun_fact}"
                    st.markdown(response_content)
                    
                    # 4. Store journey info for feedback
                    st.session_state.last_journey_info = {
                        "id": st.session_state.selected_destination_id,
                        "route_data": route_data,
                        "original_query": prompt,
                        "journey_title": narrative.title,
                        "user_id": "hackathon_user_01"
                    }
                    
                    # 5. Add response to chat history with journey flag
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response_content,
                        "is_journey": True # Flag to show feedback buttons
                    })
                    st.rerun() # Rerun to display the new map route and feedback buttons

                except Exception as e:
                    error_message = f"I'm sorry, I encountered an error: {e}"
                    st.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
                    
