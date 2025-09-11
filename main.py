# main.py

import streamlit as st
import folium
from streamlit_folium import st_folium
import numpy as np

from app import services, models, knowledge_base

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="UrbanScribe",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE INITIALIZATION ---
# Initialize session state variables if they don't exist.
if "start_location" not in st.session_state:
    st.session_state.start_location = None
if "journey_created" not in st.session_state:
    st.session_state.journey_created = False
if "route_data" not in st.session_state:
    st.session_state.route_data = None
if "narrative" not in st.session_state:
    st.session_state.narrative = None

# --- 3. SIDEBAR (USER INPUT) ---
with st.sidebar:
    st.title("UrbanScribe")
    st.markdown("Your AI-powered travel companion.")
    st.divider()

    # --- Journey Style Tab ---
    st.subheader("1. Describe Your Journey")
    query = st.text_area(
        "What kind of journey are you looking for?",
        "A quiet walk with lots of historical relevance",
        height=100,
        placeholder="e.g., 'A vibrant market tour' or 'A peaceful park walk'"
    )

    # --- Destination Tab ---
    st.subheader("2. Choose Your Destination")
    
    # City/Region Selection
    selected_city = st.selectbox(
        "Select City/Region:",
        ("Nsukka", "Enugu", "Addis Ababa", "Nairobi", "Lagos")
    )
    
    # Fetch POIs for the selected city
    poi_list = knowledge_base.get_pois_by_city(selected_city)
    
    # THE FIX: Convert the list of dicts into a format the UI can use
    if poi_list:
        # Create a dictionary for easy lookup: {name: id}
        poi_choices_dict = {poi['name']: poi['_id'] for poi in poi_list}
        
        # Create the selectbox with just the names
        destination_name = st.selectbox("Choose Destination:", options=list(poi_choices_dict.keys()))
        
        # Get the ID from the selected name
        destination_poi_id = poi_choices_dict.get(destination_name)
    else:
        destination_name = None
        destination_poi_id = None
        st.warning(f"No destinations found for {selected_city}.")

    # --- Create Journey Button ---
    st.divider()
    if st.button("Create My Journey", type="primary", use_container_width=True, disabled=(not destination_poi_id)):
        if st.session_state.start_location:
            with st.spinner("Crafting your personalized story... This may take a moment."):
                try:
                    # Get destination details
                    destination_poi = knowledge_base.get_poi_by_id(destination_poi_id)
                    end_lat = destination_poi['location']['coordinates'][1]
                    end_lon = destination_poi['location']['coordinates'][0]

                    # Round coordinates for API compatibility
                    start_lat_rounded = round(st.session_state.start_location['lat'], 5)
                    start_lon_rounded = round(st.session_state.start_location['lng'], 5)
                    end_lat_rounded = round(end_lat, 5)
                    end_lon_rounded = round(end_lon, 5)

                    # Create the request model
                    request = models.JourneyRequest(
                        user_id="hackathon_user_01",
                        latitude=start_lat_rounded,
                        longitude=start_lon_rounded,
                        city=selected_city,
                        query=query,
                        destination_poi_id=destination_poi_id
                    )

                    # Call backend services
                    route_data = services.get_route_from_ors(start_lon_rounded, start_lat_rounded, end_lon_rounded, end_lat_rounded)
                    narrative = services.generate_narrative_with_rag(request)

                    # Store results in session state
                    st.session_state.route_data = route_data
                    st.session_state.narrative = narrative
                    st.session_state.journey_created = True
                    st.success("Your journey is ready!")
                    st.rerun() # Rerun to update the main panel

                except Exception as e:
                    st.error(f"An error occurred while creating your journey: {e}")
        else:
            st.warning("Please click on the map to set a starting point first.")

# --- 4. MAIN PANEL (MAP AND STORY) ---

# --- Map Display ---
st.subheader("Interactive Map")
if st.session_state.start_location:
    st.success(f"Start Location Set: {st.session_state.start_location['lat']:.4f}, {st.session_state.start_location['lng']:.4f}")
else:
    st.info("Click on the map to set your starting location.")

# Create a Folium map
map_center = [st.session_state.start_location['lat'], st.session_state.start_location['lng']] if st.session_state.start_location else [6.855, 7.38]
m = folium.Map(location=map_center, zoom_start=15)

# Add a marker for the start location
if st.session_state.start_location:
    folium.Marker(
        [st.session_state.start_location['lat'], st.session_state.start_location['lng']],
        popup="Your Start",
        tooltip="Your Start",
        icon=folium.Icon(color="blue", icon="user")
    ).add_to(m)

# Draw route on the map if it exists
if st.session_state.journey_created and st.session_state.route_data:
    points = st.session_state.route_data['points']
    swapped_points = [(p[1], p[0]) for p in points] # Swap (lon, lat) to (lat, lon) for Folium
    folium.PolyLine(swapped_points, color="red", weight=5, opacity=0.8).add_to(m)
    
    # Add destination marker
    folium.Marker(
        swapped_points[-1], # The last point is the destination
        popup="Destination",
        tooltip="Destination",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(m)
    
    # Auto-zoom to fit the route
    m.fit_bounds(swapped_points)

# Display the map
map_data = st_folium(m, width='100%', height=450)

# Update start location on map click
if map_data and map_data.get("last_clicked"):
    clicked_coords = map_data["last_clicked"]
    st.session_state.start_location = clicked_coords
    st.rerun()

st.divider()

# --- Story Display ---
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
    
