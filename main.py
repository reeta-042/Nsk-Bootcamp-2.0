import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import traceback

# Import our application modules
from app import services, models, knowledge_base

# --- Page Config ---
st.set_page_config(page_title="Hometown Atlas", page_icon="🌍", layout="wide")

# --- Session State Initialization ---
if "start_location" not in st.session_state:
    st.session_state.start_location = None
if "map_center" not in st.session_state:
    st.session_state.map_center = [6.855, 7.38] # Default center
if "route_data" not in st.session_state:
    st.session_state.route_data = None
if "narrative" not in st.session_state:
    st.session_state.narrative = None
if "user_id" not in st.session_state:
    st.session_state.user_id = "hackathon_user_01"

# --- Sidebar for Controls ---
with st.sidebar:
    st.title("UrbanScribe")
    st.markdown("Your AI-powered travel companion.")

    # Get User's Location
    location = get_geolocation()
    if location and not st.session_state.start_location:
        st.session_state.start_location = location['coords']
        st.session_state.map_center = [location['coords']['latitude'], location['coords']['longitude']]
        st.rerun()

    if st.session_state.start_location:
        st.success(f"📍 Location Acquired!")
    else:
        st.info("Waiting for browser location...")

    # Use Tabs for better organization
    tab1, tab2 = st.tabs(["📍 Destination", "🎨 Journey Style"])

    with tab1:
        st.subheader("Where to?")
        selected_city = st.selectbox("Select City/Region:", ("Nsukka", "Enugu", "Addis Ababa", "Nairobi"))
        
        # Get POIs for the selected city
        poi_choices = knowledge_base.get_pois_by_city(selected_city)
        if poi_choices:
            destination_name = st.selectbox("Choose Destination:", options=list(poi_choices.keys()))
        else:
            destination_name = None
            st.warning(f"No destinations found for {selected_city}.")

    with tab2:
        st.subheader("What kind of journey?")
        query = st.text_area("Describe your ideal walk:", "A quiet walk with lots of historical relevance.", height=100)

    # Create Journey Button
    if st.button("Create My Journey", type="primary", use_container_width=True):
        if st.session_state.start_location and destination_name:
            with st.spinner("Crafting your personalized journey..."):
                try:
                    request = models.JourneyRequest(
                        user_id=st.session_state.user_id,
                        latitude=st.session_state.start_location['latitude'],
                        longitude=st.session_state.start_location['longitude'],
                        city=selected_city,
                        query=query,
                        destination_poi_id=poi_choices[destination_name]
                    )
                    
                    destination_poi = knowledge_base.get_poi_by_id(request.destination_poi_id)
                    end_lon = destination_poi['location']['coordinates'][0]
                    end_lat = destination_poi['location']['coordinates'][1]

                    route_data = services.get_route_from_ors(request.longitude, request.latitude, end_lon, end_lat)
                    narrative = services.generate_narrative_with_rag(request)
                    
                    st.session_state.route_data = route_data
                    st.session_state.narrative = narrative
                    st.success("Your journey is ready!")
                    st.rerun()

                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    traceback.print_exc() # This will print the full error to the logs
        else:
            st.warning("Please ensure location is set and a destination is selected.")

# --- Main Content Area ---
st.header("Your Journey Awaits")
col1, col2 = st.columns([3, 2]) # Main 2-column layout

with col1:
    st.subheader("Interactive Map")
    m = folium.Map(location=st.session_state.map_center, zoom_start=15)

    if st.session_state.start_location:
        folium.Marker([st.session_state.start_location['latitude'], st.session_state.start_location['longitude']], popup="Your Start", icon=folium.Icon(color="blue", icon="user")).add_to(m)

    if st.session_state.route_data:
        try:
            points = st.session_state.route_data['geometry']['coordinates']
            swapped_points = [(p[1], p[0]) for p in points]
            folium.PolyLine(swapped_points, color="red", weight=5, opacity=0.8).add_to(m)
            folium.Marker(swapped_points[-1], popup="Your Destination", icon=folium.Icon(color="red", icon="flag")).add_to(m)
            m.fit_bounds([swapped_points[0], swapped_points[-1]])
        except (KeyError, IndexError) as e:
            st.warning(f"Could not display route on map. Error: {e}")

    st_folium(m, width='100%', height=500, returned_objects=[])

with col2:
    st.subheader("Generated Story")
    if st.session_state.narrative and st.session_state.route_data:
        narrative = st.session_state.narrative
        route_data = st.session_state.route_data
        
        try:
            duration_min = route_data['routes'][0]['duration'] / 60
            distance_km = route_data['routes'][0]['distance'] / 1000
            st.metric(label="🚶‍♀️ Est. Time", value=f"{duration_min:.0f} min")
            st.metric(label="📏 Distance", value=f"{distance_km:.2f} km")
        except (KeyError, IndexError):
            st.info("Route metrics not available.")
        
        st.divider()
        st.subheader(narrative.title)
        st.info(narrative.narrative)
        st.success(f"**Fun Fact:** {narrative.fun_fact}")
    else:
        st.info("Your journey's story and details will appear here.")
        
