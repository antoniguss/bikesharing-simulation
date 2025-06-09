# live_visualization.py

import streamlit as st
import simpy
import pandas as pd
import pydeck as pdk
import time

# Import your existing simulation components
from config import ORS_API_KEY, SIMULATION_TIME, USER_ARRIVAL_RATE
from simulation_system import BikeShareSystem
from simulation_processes import user_generator

# --- Helper function to calculate current positions ---
def get_live_user_positions(system, current_time):
    """Calculates the current lon/lat of all active users."""
    user_data = []
    for user_id, data in system.active_users.items():
        # Calculate progress of the journey leg (0.0 to 1.0)
        duration = data['end_time'] - data['start_time']
        time_elapsed = current_time - data['start_time']
        progress = min(max(time_elapsed / duration, 0.0), 1.0)

        # Linear interpolation to find current position
        start_lon, start_lat = data['start_coord']
        end_lon, end_lat = data['end_coord']
        
        current_lon = start_lon + progress * (end_lon - start_lon)
        current_lat = start_lat + progress * (end_lat - start_lat)
        
        user_data.append({
            "lon": current_lon,
            "lat": current_lat,
            "mode": data['mode'],
            "size": 12 if data['mode'] == 'cycling' else 8, # Make cyclists bigger
            "color": [255, 0, 0] if data['mode'] == 'cycling' else [0, 0, 255] # Red for cycling, Blue for walking
        })
    return pd.DataFrame(user_data) if user_data else pd.DataFrame(columns=["lon", "lat", "mode", "size", "color"])

# --- Streamlit Page Configuration ---
st.set_page_config(layout="wide", page_title="Live Bike-Sharing Simulation")

st.title("Live Bike-Sharing Simulation")

# --- Simulation Initialization ---
# Use session_state to store the simulation environment and system
# so they don't get recreated on every UI update.
if 'simulation_initialized' not in st.session_state:
    st.session_state.env = simpy.Environment()
    st.session_state.system = BikeShareSystem(ors_api_key=ORS_API_KEY)
    st.session_state.env.process(user_generator(st.session_state.env, st.session_state.system, USER_ARRIVAL_RATE))
    st.session_state.simulation_initialized = True
    st.session_state.current_sim_time = 0

# Retrieve objects from session state for easier access
env = st.session_state.env
system = st.session_state.system

# --- UI Layout ---
# Create placeholders for the map and stats so we can update them
col1, col2 = st.columns([4, 1])
with col1:
    st.header("Simulation Map")
    map_placeholder = st.empty()
with col2:
    st.header("Live Stats")
    stats_placeholder = st.empty()

# Create a static DataFrame for station locations
stations_df = pd.DataFrame([{
    "lon": s.x, "lat": s.y, "id": s.id, "bikes": s.bikes, "capacity": s.capacity
} for s in system.stations])

# Set initial view for the map
view_state = pdk.ViewState(
    longitude=stations_df['lon'].mean(),
    latitude=stations_df['lat'].mean(),
    zoom=12.5,
    pitch=45,
)

# --- The Main Simulation Loop ---
# This loop drives the simulation forward in small steps
while st.session_state.current_sim_time < SIMULATION_TIME:
    # 1. Advance the simulation by 1 minute
    st.session_state.current_sim_time += 1
    env.run(until=st.session_state.current_sim_time)
    
    # 2. Get current state of the system
    live_users_df = get_live_user_positions(system, env.now)
    station_bikes_df = pd.DataFrame([{'id': s.id, 'bikes': s.bikes} for s in system.stations])

    # 3. Update the map layers
    station_layer = pdk.Layer(
        "ScatterplotLayer",
        data=stations_df,
        get_position="[lon, lat]",
        get_radius=30,
        get_fill_color=[50, 150, 50, 180], # Green for stations
        pickable=True,
    )
    
    user_layer = pdk.Layer(
        "ScatterplotLayer",
        data=live_users_df,
        get_position="[lon, lat]",
        get_radius="size",
        get_fill_color="color",
        pickable=True,
    )

    # 4. Render the map in its placeholder
    with map_placeholder.container():
        r = pdk.Deck(
            layers=[station_layer, user_layer],
            initial_view_state=view_state,
            map_style="mapbox://styles/mapbox/light-v10",
            tooltip={"html": "<b>Station ID:</b> {id}<br/><b>Bikes:</b> {bikes}/{capacity}"}
        )
        st.pydeck_chart(r)

    # 5. Update the stats in their placeholder
    with stats_placeholder.container():
        st.metric("Simulation Time (min)", f"{int(env.now)}")
        st.metric("Successful Trips", system.stats['successful_trips'])
        st.metric("Failed Trips", system.stats['failed_trips'])
        
        st.subheader("Station Bike Counts")
        st.dataframe(station_bikes_df, hide_index=True)

    # 6. Wait for a short period in REAL time to create the animation effect
    time.sleep(0.1)

st.success("Simulation Complete!")
st.balloons()