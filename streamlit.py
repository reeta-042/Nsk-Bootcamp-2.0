import streamlit as st
import asyncio
from app import services, models, knowledge_base
import pandas as pd

# --- Page Configuration ---
# This should be the first Streamlit command in your script
st.set_page_config(
    page_title="Hometown Atlas",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Main App Logic ---

# Use st.cache_data to prevent re-running these functions on every interaction
@st.cache_data
def get_all_pois_as_choices():
    """
    Fetches all POIs from MongoDB to populate a dropdown menu.
    This is a synchronous wrapper for the async DB call.
    """
    # We need a way to run an async function from a sync context
    async def fetch():
        # In a real app, you'd have a function in knowledge_base.py to get all POIs
        # For now, we'll simulate it. Let's assume you add this function:
        # pois = await knowledge_base.get_all_pois()
        # For the demo, let's create some placeholder POIs.
        # Replace this with your actual POI IDs and Names from your database.
        return {
            "University of Nigeria, Nsukka": "poi_unn_01",
            "Freedom Park, Lagos": "poi_lag_01",
            "Nike Art Gallery, Lagos": "poi_lag_02",
        }
    return asyncio.run(fetch())

# --- UI Layout ---

st.title("🌍 Hometown Atlas")
st.markdown("An intelligent travel companion that tells the rich, hidden stories of African cities.")

# Create two columns for a cleaner layout
col1, col2 = st.columns([1, 1])

with col1:
    st.header("Plan Your Journey")

    # --- User Inputs ---
    # Using st.session_state to hold values
    if 'user_id' not in st.session_state:
        st.session_state.user_id = "hackathon_user_01" # Default user for the demo

    query = st.text_area(
        "What kind of journey are you looking for?",
        "Show me an interesting and quiet walk.",
        height=100
    )

    # Use the cached function to get POI choices
    poi_choices = get_all_pois_as_choices()
    destination_name = st.selectbox(
        "Choose your destination:",
        options=list(poi_choices.keys())
    )
    destination_poi_id = poi_choices[destination_name]

    # For simplicity, we'll use text input for lat/lon.
    # In a real app, you might use st.map or a location component.
    latitude = st.number_input("Your current Latitude:", value=6.855, format="%.4f")
    longitude = st.number_input("Your current Longitude:", value=7.38, format="%.4f")
    city = st.text_input("Your current City:", value="Nsukka")

    # The main action button
    if st.button("Create My Journey", type="primary", use_container_width=True):
        with st.spinner("Crafting your personalized story... This may take a moment."):
            try:
                # 1. Create the request model, just like FastAPI did
                request = models.JourneyRequest(
                    user_id=st.session_state.user_id,
                    latitude=latitude,
                    longitude=longitude,
                    city=city,
                    query=query,
                    destination_poi_id=destination_poi_id
                )

                # 2. Call your existing service functions directly!
                # We run the main async logic using asyncio.run()
                async def get_journey_data():
                    # Get destination details
                    destination_poi = await knowledge_base.get_poi_by_id(request.destination_poi_id)
                    if not destination_poi:
                        st.error(f"Could not find destination with ID: {request.destination_poi_id}")
                        return None, None

                    end_lon = destination_poi['location']['coordinates'][0]
                    end_lat = destination_poi['location']['coordinates'][1]

                    # Get route and narrative in parallel
                    route_task = services.get_route_from_maptiler(
                        start_lon=request.longitude, start_lat=request.latitude,
                        end_lon=end_lon, end_lat=end_lat
                    )
                    narrative_task = services.generate_narrative_with_rag(request)

                    route_data, structured_narrative = await asyncio.gather(route_task, narrative_task)
                    return route_data, structured_narrative

                # Run the async function and get the results
                route_data, structured_narrative = asyncio.run(get_journey_data())

                # 3. Store results in session state to display them
                if route_data and structured_narrative:
                    st.session_state.route_data = route_data
                    st.session_state.narrative = structured_narrative
                    st.success("Your journey is ready!")

            except Exception as e:
                st.error(f"An error occurred: {e}")


with col2:
    st.header("Your Generated Journey")

    # --- Display Results ---
    # Only show this section if a journey has been generated
    if 'narrative' in st.session_state and 'route_data' in st.session_state:
        narrative = st.session_state.narrative
        route_data = st.session_state.route_data

        st.subheader(narrative.title)
        st.markdown(f"**Awareness:** *{narrative.location_awareness}*")
        st.info(narrative.narrative)
        st.success(f"**Fun Fact:** {narrative.fun_fact}")

        # --- Display Map ---
        # Extract coordinates from the route data to display on a map
        try:
            # Create a DataFrame for the map component
            waypoints = route_data['waypoints']
            start_point = pd.DataFrame([{'latitude': waypoints[0]['location'][1], 'longitude': waypoints[0]['location'][0]}])
            end_point = pd.DataFrame([{'latitude': waypoints[1]['location'][1], 'longitude': waypoints[1]['location'][0]}])
            
            st.map(start_point) # You can add more points to draw a path
            st.write(f"**Walk Time:** Approximately {route_data['routes'][0]['duration'] / 60:.0f} minutes.")
        except (KeyError, IndexError) as e:
            st.warning("Could not display map from route data.")

        # --- Display Raw JSON for debugging/transparency ---
        with st.expander("Show Raw Route Data (JSON)"):
            st.json(route_data)

        # --- Feedback Mechanism ---
        st.subheader("Did you enjoy this journey?")
        feedback_col1, feedback_col2 = st.columns(2)
        
        if feedback_col1.button("👍 Yes, I liked it!", use_container_width=True):
            with st.spinner("Thanks! Updating your preferences..."):
                reflection_request = models.ReflectionRequest(
                    user_id=st.session_state.user_id,
                    original_query=query,
                    journey_title=narrative.title,
                    user_feedback="liked"
                )
                asyncio.run(services.reflect_and_update_preferences(reflection_request))
                st.toast("Your preferences have been updated!", icon="💖")

        if feedback_col2.button("👎 Not for me", use_container_width=True):
            with st.spinner("Thanks for the feedback! Learning..."):
                reflection_request = models.ReflectionRequest(
                    user_id=st.session_state.user_id,
                    original_query=query,
                    journey_title=narrative.title,
                    user_feedback="disliked"
                )
                asyncio.run(services.reflect_and_update_preferences(reflection_request))
                st.toast("Your preferences have been updated.", icon="🧠")

                  
