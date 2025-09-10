import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from typing import List
import traceback

# Import our application modules
from app import services, models, knowledge_base

# --- Page Config ---
st.set_page_config(page_title="Hometown Atlas", page_icon="🌍", layout="wide")

# --- Session State Initialization ---
# This ensures that our variables persist across reruns
if "start_location" not in st.session_state:
    st.session_state.start_location = None
if "map_center" not in st.session_state:
    st.session_state.map_center = [6.855, 7.38] # Default center (Nsukka)
if "route_data" not in st.session_state:
    st.session_state.route_data = None
if "narrative" not in st.session_state:
    st.session_state.narrative = None
if "user_id" not in st.session_state:
    st.session_state.user_id = "hackathon_user_01" # Default user

# --- UI Layout ---
st.title("🌍 Hometown Atlas")
st.markdown("An intelligent travel companion that tells the rich, hidden stories of African cities.")

# --- Sidebar for Controls ---
with st.sidebar:
    st.header("Plan Your Journey")
    
    # 1. Get User's Location
    location = get_geolocation()
    if location and not st.session_state.start_location:
        st.session_state.start_location = location['coords']
        st.session_state.map_center = [location['coords']['latitude'], location['coords']['longitude']]
        st.rerun()

    if st.session_state.start_location:
        st.success(f"📍 Start Location Set!")
    else:
        st.info("Waiting for your browser to provide a location...")

    # 2. User Inputs
    query = st.text_area("What kind of journey are you looking for?", "Show me an interesting and quiet walk.", placeholder="e.g., A vibrant market tour")
    
    # Manual City/Region Selection
    selected_city = st.selectbox(
        "Select your current city/region:",
        ("Nsukka", "Enugu", "Addis Ababa", "Nairobi")
    )

    # Dynamic POI choices based on selected city
    poi_choices = knowledge_base.get_pois_by_city(selected_city)
    destination_name = st.selectbox("Choose your destination:", options=list(poi_choices.keys()))

    # 3. Create Journey Button
    if st.button("Create My Journey", type="primary", use_container_width=True):
        if st.session_state.start_location and destination_name:
            with st.spinner("Crafting your personalized journey..."):
                try:
                    # Prepare the request model
                    request = models.JourneyRequest(
                        user_id=st.session_state.user_id,
                        latitude=st.session_state.start_location['latitude'],
                        longitude=st.session_state.start_location['longitude'],
                        city=selected_city,
                        query=query,
                        destination_poi_id=poi_choices[destination_name]
                    )
                    
                    # Get destination coordinates
                    destination_poi = knowledge_base.get_poi_by_id(request.destination_poi_id)
                    end_lon = destination_poi['location']['coordinates'][0]
                    end_lat = destination_poi['location']['coordinates'][1]

                    # --- CALL THE CORRECT ROUTING SERVICE ---
                    route_data = services.get_route_from_ors(request.longitude, request.latitude, end_lon, end_lat)
                    
                    # Generate the narrative
                    narrative = services.generate_narrative_with_rag(request)
                    
                    # Store results in session state to trigger UI update
                    st.session_state.route_data = route_data
                    st.session_state.narrative = narrative
                    st.success("Your journey is ready!")
                    st.rerun()

                except Exception as e:
                    st.error(f"An error occurred while creating your journey: {e}")
                    traceback.print_exc()
        else:
            st.warning("Please ensure your location is set and a destination is selected.")

# --- Main Content: Map and Story ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Your Interactive Map")
    m = folium.Map(location=st.session_state.map_center, zoom_start=15)

    # Add marker for start location
    if st.session_state.start_location:
        folium.Marker(
            [st.session_state.start_location['latitude'], st.session_state.start_location['longitude']], 
            popup="Your Start", 
            icon=folium.Icon(color="blue", icon="user")
        ).add_to(m)

    # Draw the route on the map if it exists
    if st.session_state.route_data:
        try:
            points = st.session_state.route_data['geometry']['coordinates']
            # ORS coordinates are [lon, lat], Folium needs [lat, lon], so we swap them
            swapped_points = [(p[1], p[0]) for p in points]
            folium.PolyLine(swapped_points, color="red", weight=5, opacity=0.8).add_to(m)
            
            # Add marker for destination
            dest_coords = swapped_points[-1]
            folium.Marker(
                dest_coords, 
                popup="Your Destination", 
                icon=folium.Icon(color="red", icon="flag")
            ).add_to(m)
            
            # Auto-zoom the map to fit the route
            m.fit_bounds([swapped_points[0], swapped_points[-1]])

        except (KeyError, IndexError) as e:
            st.warning(f"Could not display route on map. Error: {e}")

    st_folium(m, width='100%', height=500, returned_objects=[])

with col2:
    st.subheader("Your Generated Journey")
    if st.session_state.narrative and st.session_state.route_data:
        narrative = st.session_state.narrative
        route_data = st.session_state.route_data
        
        metric1, metric2 = st.columns(2)
        try:
            duration_min = route_data['routes'][0]['duration'] / 60
            distance_km = route_data['routes'][0]['distance'] / 1000
            metric1.metric(label="🚶‍♀️ Est. Time", value=f"{duration_min:.0f} min")
            metric2.metric(label="📏 Distance", value=f"{distance_km:.2f} km")
        except (KeyError, IndexError):
            st.info("Route metrics are not available.")
        
        st.divider()
        st.subheader(narrative.title)
        st.markdown(f"**Awareness:** *{narrative.location_awareness}*")
        st.info(narrative.narrative)
        st.success(f"**Fun Fact:** *{narrative.fun_fact}*")
    else:
        st.info("Your journey's story and details will appear here after you click 'Create My Journey'.")
    
