import streamlit as st
import asyncio
import sys
import os
import pandas as pd
from streamlit_folium import st_folium
import folium
from streamlit_js_eval import streamlit_js_eval, get_geolocation

# --- FIX FOR ModuleNotFoundError ---
# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
# -----------------------------------

from app import services, models, knowledge_base

# --- Page Configuration ---
st.set_page_config(
    page_title="Hometown Atlas",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Asynchronous Helper to run backend logic ---
async def get_journey_data(request: models.JourneyRequest):
    """
    Asynchronously fetches route and narrative data.
    """
    try:
        # Fetch destination details first
        destination_poi = await knowledge_base.get_poi_by_id(request.destination_poi_id)
        if not destination_poi:
            st.error(f"Could not find destination with ID: {request.destination_poi_id}")
            return None, None

        end_lon = destination_poi['location']['coordinates'][0]
        end_lat = destination_poi['location']['coordinates'][1]

        # Create and run tasks concurrently
        route_task = services.get_route_from_maptiler(
            start_lon=request.longitude, start_lat=request.latitude,
            end_lon=end_lon, end_lat=end_lat
        )
        narrative_task = services.generate_narrative_with_rag(request)

        route_data, structured_narrative = await asyncio.gather(route_task, narrative_task)
        
        # Add destination POI to route_data for easy access
        route_data['destination_poi'] = destination_poi

        return route_data, structured_narrative

    except Exception as e:
        st.error(f"An error occurred while creating your journey: {e}")
        return None, None

# --- Caching Functions ---
@st.cache_data
def get_all_pois_as_choices():
    """
    Fetches all Points of Interest to be used as destination choices.
    In a real app, this would fetch from a database.
    """
    # This is a placeholder. In a real app, you would call a function
    # from your knowledge_base or services module.
    return {
        "University of Nigeria, Nsukka": "poi_unn_01",
        "Freedom Park, Lagos": "poi_lag_01",
        "Nike Art Gallery, Lagos": "poi_lag_02",
    }

# --- Initialize Session State ---
# This ensures variables persist across reruns
if 'user_id' not in st.session_state:
    st.session_state.user_id = "hackathon_user_01" # Default user
if 'start_location' not in st.session_state:
    st.session_state.start_location = None
if 'route_data' not in st.session_state:
    st.session_state.route_data = None
if 'narrative' not in st.session_state:
    st.session_state.narrative = None
if 'map_center' not in st.session_state:
    st.session_state.map_center = [6.855, 7.38] # Default center (Nsukka, Nigeria)
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 13

# --- UI Layout ---

st.title("🌍 Hometown Atlas")
st.markdown("Your intelligent travel companion for discovering the rich, hidden stories of cities.")

# --- Sidebar for Journey Configuration ---
with st.sidebar:
    st.header("📍 Plan Your Journey")

    # Get destination from user
    poi_choices = get_all_pois_as_choices()
    destination_name = st.selectbox(
        "Choose your destination:",
        options=list(poi_choices.keys()),
        index=0
    )
    destination_poi_id = poi_choices[destination_name]

    # Get journey preference from user
    query = st.text_area(
        "What kind of journey are you looking for?",
        "Show me an interesting and quiet walk.",
        height=100
    )

    st.divider()

    # Automatically fetch user's location
    st.info("Your browser location is used as a starting point. You can also click the map to set a new start.")
    location = get_geolocation()
    if location and not st.session_state.start_location:
        st.session_state.start_location = {
            "latitude": location['coords']['latitude'],
            "longitude": location['coords']['longitude']
        }
        # Center map on user's new location
        st.session_state.map_center = [location['coords']['latitude'], location['coords']['longitude']]
        st.session_state.map_zoom = 15
        st.rerun() # Rerun to update the map with the new location

    if st.session_state.start_location:
        lat = st.session_state.start_location['latitude']
        lon = st.session_state.start_location['longitude']
        st.success(f"Start Location Set: ({lat:.4f}, {lon:.4f})")

    # Journey creation button
    if st.button("Create My Journey", type="primary", use_container_width=True):
        if st.session_state.start_location:
            with st.spinner("Crafting your personalized story... This may take a moment."):
                # Prepare the request model
                request = models.JourneyRequest(
                    user_id=st.session_state.user_id,
                    latitude=st.session_state.start_location['latitude'],
                    longitude=st.session_state.start_location['longitude'],
                    city="Unknown", # City can be derived or requested if needed
                    query=query,
                    destination_poi_id=destination_poi_id
                )
                
                # Run the async data fetching function
                route_data, narrative = asyncio.run(get_journey_data(request))

                # Store results in session state
                if route_data and narrative:
                    st.session_state.route_data = route_data
                    st.session_state.narrative = narrative
                    st.success("Your journey is ready!")
                    # Center map on the new route
                    start = route_data['waypoints'][0]['location']
                    end = route_data['waypoints'][1]['location']
                    st.session_state.map_center = [(start[1] + end[1]) / 2, (start[0] + end[0]) / 2]
                    st.session_state.map_zoom = 14
                    st.rerun()
        else:
            st.warning("Please set a starting point by enabling location or clicking the map.")


# --- Main Content: Map and Story ---
map_col, story_col = st.columns([3, 2]) # Give more space to the map

with map_col:
    st.subheader("Your Interactive Map")

    # Create a Folium map centered on the session state location
    m = folium.Map(
        location=st.session_state.map_center,
        zoom_start=st.session_state.map_zoom,
        tiles="cartodbpositron"
    )

    # Add a marker for the start location
    if st.session_state.start_location:
        folium.Marker(
            [st.session_state.start_location['latitude'], st.session_state.start_location['longitude']],
            popup="Your Starting Point",
            tooltip="Start",
            icon=folium.Icon(color="blue", icon="play")
        ).add_to(m)

    # Draw the route and destination marker if data is available
    if st.session_state.route_data:
        try:
            # Add destination marker
            dest_poi = st.session_state.route_data['destination_poi']
            dest_loc = dest_poi['location']['coordinates']
            folium.Marker(
                [dest_loc[1], dest_loc[0]], # Folium uses (lat, lon)
                popup=dest_poi['name'],
                tooltip="Destination",
                icon=folium.Icon(color="green", icon="flag")
            ).add_to(m)

            # Draw the walking path
            points = st.session_state.route_data['routes'][0]['geometry']['coordinates']
            swapped_points = [(p[1], p[0]) for p in points] # Swap (lon, lat) to (lat, lon)
            folium.PolyLine(swapped_points, color="#FF0000", weight=4, opacity=0.8).add_to(m)

        except (KeyError, IndexError) as e:
            st.warning(f"Could not display the full route on the map. Error: {e}")

    # Display the map and capture clicks
    map_data = st_folium(m, width='100%', height=500, returned_objects=[])

    # Update start location if map is clicked
    if map_data and map_data.get("last_clicked"):
        clicked_coords = map_data["last_clicked"]
        st.session_state.start_location = {
            "latitude": clicked_coords['lat'],
            "longitude": clicked_coords['lng']
        }
        st.rerun() # Rerun to update the start marker and text

with story_col:
    st.subheader("Your Generated Journey")

    if st.session_state.narrative and st.session_state.route_data:
        narrative = st.session_state.narrative
        route_data = st.session_state.route_data
        
        # Display walk time and distance
        try:
            duration_min = route_data['routes'][0]['duration'] / 60
            distance_km = route_data['routes'][0]['distance'] / 1000
            st.metric(label="🚶‍♀️ Est. Walk Time", value=f"{duration_min:.0f} minutes")
            st.metric(label="📏 Distance", value=f"{distance_km:.2f} km")
        except (KeyError, IndexError):
            st.info("Route metrics are not available.")

        st.divider()

        # Display the AI-generated narrative
        st.subheader(narrative.title)
        st.markdown(f"**Awareness:** *{narrative.location_awareness}*")
        st.info(narrative.narrative)
        st.success(f"**Fun Fact:** {narrative.fun_fact}")

    else:
        st.info("Your journey's story and details will appear here after you click 'Create My Journey'.")

            
