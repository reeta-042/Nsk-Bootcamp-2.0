import streamlit as st
import sys
import os
from typing import List
from streamlit_folium import st_folium
import folium
from streamlit_js_eval import get_geolocation
import asyncio

# --- Project Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from app import services, models, knowledge_base

# --- Page Configuration ---
st.set_page_config(page_title="Hometown Atlas", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")

# --- Caching Functions (Calling sync knowledge_base functions) ---
@st.cache_data(ttl=3600)
def get_all_tags_from_db():
    return knowledge_base.get_unique_tags()

@st.cache_data(ttl=60)
def get_filtered_pois_from_db(tags: List[str] = None, budget: str = None):
    pois_list = knowledge_base.get_all_pois(tags=tags, budget=budget)
    if not pois_list:
        return {"No destinations found for these filters": None}
    return {poi['name']: poi['_id'] for poi in pois_list}

# --- Async Helper for services (MapTiler, Gemini) ---
async def get_journey_data(request: models.JourneyRequest):
    """
    This function now correctly separates sync and async calls.
    """
    try:
        # --- STEP 1: Perform the SYNCHRONOUS database call first ---
        # This function is NOT async and returns a dictionary directly.
        destination_poi = knowledge_base.get_poi_by_id(request.destination_poi_id)
        
        if not destination_poi:
            st.error(f"Could not find destination with ID: {request.destination_poi_id}")
            return None, None
        
        end_lon = destination_poi['location']['coordinates'][0]
        end_lat = destination_poi['location']['coordinates'][1]
        
        # --- STEP 2: Create the ASYNCHRONOUS tasks for external services ---
        # These functions in services.py are async and return awaitable objects.
        route_task = services.get_route_from_maptiler(request.longitude, request.latitude, end_lon, end_lat)
        narrative_task = services.generate_narrative_with_rag(request)
        
        # --- STEP 3: Await the results of ONLY the async tasks ---
        # We are NOT including the 'destination_poi' dict here.
        results = await asyncio.gather(route_task, narrative_task)
        
        # Unpack the results from gather
        route_data = results[0]
        structured_narrative = results[1]
        
        # --- STEP 4: Combine the results ---
        if route_data:
            route_data['destination_poi'] = destination_poi
            
        return route_data, structured_narrative
        
    except Exception as e:
        # This will now give us a more precise error if something inside fails.
        st.error(f"An error occurred in get_journey_data: {e}")
        # Also print to the console for more detail
        print(f"ERROR in get_journey_data: {e}")
        import traceback
        traceback.print_exc()
        return None, None

# --- Initialize Session State ---
if 'user_id' not in st.session_state: st.session_state.user_id = "hackathon_user_01"
if 'start_location' not in st.session_state: st.session_state.start_location = None
if 'route_data' not in st.session_state: st.session_state.route_data = None
if 'narrative' not in st.session_state: st.session_state.narrative = None
if 'map_center' not in st.session_state: st.session_state.map_center = [9.0765, 7.3986]
if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 12

# --- UI ---
st.title("🌍 Hometown Atlas")
st.markdown("Your intelligent travel companion for discovering the rich, hidden stories of cities.")

with st.sidebar:
    st.header("📍 Plan Your Journey")
    
    with st.expander("1. Choose Destination", expanded=True):
        st.subheader("Filter Options")
        budget_options = ["any", "free", "low", "medium", "high"]
        selected_budget = st.selectbox("Budget Level:", budget_options)
        all_tags = get_all_tags_from_db()
        selected_tags = st.multiselect("Interests / Tags:", all_tags)
        
        st.divider()
        
        poi_choices = get_filtered_pois_from_db(tags=selected_tags, budget=selected_budget)
        destination_name = st.selectbox("Available Destinations:", options=list(poi_choices.keys()))
        destination_poi_id = poi_choices.get(destination_name)

    with st.expander("2. Describe Your Journey", expanded=True):
        query = st.text_area(
            "What kind of journey are you looking for?",
            placeholder="e.g., A quiet walk with historical significance.",
            height=100
        )
    
    with st.expander("3. Set Your Start Location", expanded=True):
        st.info("Your browser location is used as a starting point. You can also click the map to set a new start.")
        location = get_geolocation()
        if location and not st.session_state.start_location:
            st.session_state.start_location = {"latitude": location['coords']['latitude'], "longitude": location['coords']['longitude']}
            st.session_state.map_center = [location['coords']['latitude'], location['coords']['longitude']]
            st.session_state.map_zoom = 15
            st.rerun()

        if st.session_state.start_location:
            lat, lon = st.session_state.start_location['latitude'], st.session_state.start_location['longitude']
            st.success(f"Start Location Set: ({lat:.4f}, {lon:.4f})")

    if st.button("Create My Journey", type="primary", use_container_width=True):
        if not st.session_state.start_location:
            st.warning("Please set a starting point first.")
        elif not destination_poi_id:
            st.warning("Please select a valid destination.")
        else:
            with st.spinner("Crafting your personalized story..."):
                request = models.JourneyRequest(
                    user_id=st.session_state.user_id,
                    latitude=st.session_state.start_location['latitude'],
                    longitude=st.session_state.start_location['longitude'],
                    city="Unknown",
                    query=query,
                    destination_poi_id=destination_poi_id
                )
                # Use asyncio.run for the top-level async function
                route_data, narrative = asyncio.run(get_journey_data(request))
                if route_data and narrative:
                    st.session_state.route_data = route_data
                    st.session_state.narrative = narrative
                    st.success("Your journey is ready!")
                    start, end = route_data['waypoints'][0]['location'], route_data['waypoints'][1]['location']
                    st.session_state.map_center = [(start[1] + end[1]) / 2, (start[0] + end[0]) / 2]
                    st.session_state.map_zoom = 14
                    st.rerun()

# --- Main Content (Map and Story) ---
st.subheader("Your Interactive Map")
m = folium.Map(location=st.session_state.get('map_center', [9.0765, 7.3986]), zoom_start=st.session_state.get('map_zoom', 12), tiles="cartodbpositron")
if st.session_state.start_.location:
    folium.Marker([st.session_state.start_location['latitude'], st.session_state.start_location['longitude']], popup="Your Starting Point", tooltip="Start", icon=folium.Icon(color="blue", icon="play")).add_to(m)
if st.session_state.route_data:
    try:
        dest_poi = st.session_state.route_data['destination_poi']
        dest_loc = dest_poi['location']['coordinates']
        folium.Marker([dest_loc[1], dest_loc[0]], popup=dest_poi['name'], tooltip="Destination", icon=folium.Icon(color="green", icon="flag")).add_to(m)
        points = st.session_state.route_data['routes'][0]['geometry']['coordinates']
        swapped_points = [(p[1], p[0]) for p in points]
        folium.PolyLine(swapped_points, color="#FF0000", weight=4, opacity=0.8).add_to(m)
    except (KeyError, IndexError) as e:
        st.warning(f"Could not display the full route on the map. Error: {e}")
map_data = st_folium(m, width='100%', height=450, returned_objects=[])
if map_data and map_data.get("last_clicked"):
    clicked_coords = map_data["last_clicked"]
    st.session_state.start_location = {"latitude": clicked_coords['lat'], "longitude": clicked_coords['lng']}
    st.rerun()
st.divider()
st.subheader("Your Generated Journey")
if st.session_state.narrative and st.session_state.route_data:
    narrative, route_data = st.session_state.narrative, st.session_state.route_data
    metric1, metric2 = st.columns(2)
    try:
        with metric1:
            duration_min = route_data['routes'][0]['duration'] / 60
            st.metric(label="🚶‍♀️ Est. Walk Time", value=f"{duration_min:.0f} minutes")
        with metric2:
            distance_km = route_data['routes'][0]['distance'] / 1000
            st.metric(label="📏 Distance", value=f"{distance_km:.2f} km")
    except (KeyError, IndexError): st.info("Route metrics are not available.")
    st.divider()
    st.subheader(narrative.title)
    st.markdown(f"**Awareness:** *{narrative.location_awareness}*")
    st.info(narrative.narrative)
    st.success(f"**Fun Fact:** *{narrative.fun_fact}*")
else:
    st.info("Your journey's story and details will appear here after you click 'Create My Journey'.")
                
