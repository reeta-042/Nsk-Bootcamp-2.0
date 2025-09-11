

import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import numpy as np

# The services import will now trigger the new, safe caching
from app import services, models, knowledge_base

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="UrbanScribe",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE INITIALIZATION ---
if "start_location" not in st.session_state:
    st.session_state.start_location = None
if "journey_created" not in st.session_state:
    st.session_state.journey_created = False
if "route_data" not in st.session_state:
    st.session_state.route_data = None
if "narrative" not in st.session_state:
    st.session_state.narrative = None

# --- 3. GET USER'S LOCATION ---
if st.session_state.start_location is None:
    location = get_geolocation()
    if location:
        st.session_state.start_location = {
            'lat': location['coords']['latitude'],
            'lng': location['coords']['longitude']
        }
        st.rerun()

# --- 4. SIDEBAR (USER INPUT) ---
with st.sidebar:
    st.title("UrbanScribe")
    st.markdown("Your AI-powered travel companion.")
    st.divider()

    st.subheader("1. Describe Your Journey")
    query = st.text_area(
        "What kind of journey are you looking for?",
        "A quiet walk with lots of historical relevance",
        height=100,
        placeholder="e.g., 'A vibrant market tour' or 'A peaceful park walk'"
    )

    st.subheader("2. Choose Your Destination")
    selected_city = st.selectbox(
        "Select City/Region:",
        ("Nsukka", "Enugu", "Addis Ababa", "Nairobi", "Lagos")
    )
    
    poi_list = knowledge_base.get_pois_by_city(selected_city)
    
    if poi_list:
        poi_choices_dict = {poi['name']: poi['_id'] for poi in poi_list}
        destination_name = st.selectbox("Choose Destination:", options=list(poi_choices_dict.keys()))
        destination_poi_id = poi_choices_dict.get(destination_name)
    else:
        destination_name = None
        destination_poi_id = None
        st.warning(f"No destinations found for {selected_city}.")

    st.divider()
    if st.button("Create My Journey", type="primary", use_container_width=True, disabled=(not destination_poi_id)):
        if st.session_state.start_location:
            with st.spinner("Crafting your personalized story... This may take a moment."):
                try:
                    destination_poi = knowledge_base.get_poi_by_id(destination_poi_id)
                    end_lat = destination_poi['location']['coordinates'][1]
                    end_lon = destination_poi['location']['coordinates'][0]

                    start_lat_rounded = round(st.session_state.start_location['lat'], 5)
                    start_lon_rounded = round(st.session_state.start_location['lng'], 5)
                    end_lat_rounded = round(end_lat, 5)
                    end_lon_rounded = round(end_lon, 5)

                    request = models.JourneyRequest(
                        user_id="hackathon_user_01",
                        latitude=start_lat_rounded,
                        longitude=start_lon_rounded,
                        city=selected_city,
                        query=query,
                        destination_poi_id=destination_poi_id
                    )

                    route_data = services.get_route_from_ors(start_lon_rounded, start_lat_rounded, end_lon_rounded, end_lat_rounded)
                    narrative = services.generate_narrative_with_rag(request)

                    st.session_state.route_data = route_data
                    st.session_state.narrative = narrative
                    st.session_state.journey_created = True
                    st.success("Your journey is ready!")
                    st.rerun()

                except Exception as e:
                    st.error(f"An error occurred while creating your journey: {e}")
        else:
            st.warning("Please click on the map to set a starting point first.")

# --- 5. MAIN PANEL (MAP AND STORY) ---
st.subheader("Interactive Map")
if st.session_state.start_location:
    st.success(f"Start Location Set: {st.session_state.start_location['lat']:.4f}, {st.session_state.start_location['lng']:.4f}")
else:
    st.info("Click on the map to set your starting location.")

map_center = [st.session_state.start_location['lat'], st.session_state.start_location['lng']] if st.session_state.start_location else [6.855, 7.38]
m = folium.Map(location=map_center, zoom_start=15)

if st.session_state.start_location:
    folium.Marker(
        [st.session_state.start_location['lat'], st.session_state.start_location['lng']],
        popup="Your Start",
        tooltip="Your Start",
        icon=folium.Icon(color="blue", icon="user")
    ).add_to(m)

if st.session_state.journey_created and st.session_state.route_data:
    points = st.session_state.route_data['points']
    swapped_points = [(p[1], p[0]) for p in points]
    folium.PolyLine(swapped_points, color="red", weight=5, opacity=0.8).add_to(m)
    
    folium.Marker(
        swapped_points[-1],
        popup="Destination",
        tooltip="Destination",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(m)
    
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
    
