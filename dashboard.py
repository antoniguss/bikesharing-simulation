import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import folium
from streamlit_folium import folium_static
import os
from main import run_simulation
from config import SIMULATION_DURATION, SIMULATION_START_TIME
import time
import re
from simulation_system import BikeShareSystem

st.set_page_config(layout="wide", page_title="Bike Share Simulation Dashboard")

st.title("Bike Share System Simulation")

# Initialize session state for simulation status and bike tracking
if 'simulation_run' not in st.session_state:
    st.session_state.simulation_run = False
if 'bike_system' not in st.session_state:
    st.session_state.bike_system = None

# Sidebar controls
st.sidebar.header("Simulation Parameters")

# Duration slider (in hours)
duration_hours = st.sidebar.slider(
    "Simulation Duration (hours)",
    min_value=1,
    max_value=24,
    value=SIMULATION_DURATION // 60,
    step=1
)

# Start time slider (in hours)
start_time_hours = st.sidebar.slider(
    "Start Time (hours)",
    min_value=0,
    max_value=23,
    value=SIMULATION_START_TIME // 60,
    step=1
)

# Weights editor in expander
with st.sidebar.expander("Edit Weights", expanded=False):
    if os.path.exists('./data/poi_weights.csv'):
        poi_weights = pd.read_csv('./data/poi_weights.csv')
        edited_poi_weights = st.data_editor(poi_weights, use_container_width=True)
        if st.button("Save POI Weights"):
            edited_poi_weights.to_csv('./data/poi_weights.csv', index=False)
            st.success("POI weights saved!")
    
    if os.path.exists('./data/time_weights.csv'):
        time_weights = pd.read_csv('./data/time_weights.csv')
        edited_time_weights = st.data_editor(time_weights, use_container_width=True)
        if st.button("Save Time Weights"):
            edited_time_weights.to_csv('./data/time_weights.csv', index=False)
            st.success("Time weights saved!")

# Run simulation button
if st.sidebar.button("Run Simulation"):
    with st.spinner("Running simulation..."):
        # Update config values
        import config
        config.SIMULATION_DURATION = duration_hours * 60
        config.SIMULATION_START_TIME = start_time_hours * 60
        
        # Run simulation
        run_simulation()
        st.session_state.simulation_run = True
        st.session_state.bike_system = BikeShareSystem()  # Store the bike system in session state
        st.success("Simulation completed!")

# Only show results if simulation has been run
if st.session_state.simulation_run:
    st.header("Simulation Results")

    # Create summary metrics
    if os.path.exists('./generated/console_output.txt'):
        with open('./generated/console_output.txt', 'r') as f:
            console_output = f.read()
            
            # Extract key metrics using regex
            successful_trips = re.search(r"Successful trips: (\d+)", console_output)
            failed_trips = re.search(r"Failed trips: (\d+)", console_output)
            success_rate = re.search(r"Success rate: ([\d.]+)%", console_output)
            
            # Create metrics columns
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Successful Trips", successful_trips.group(1) if successful_trips else "0")
            with col2:
                st.metric("Failed Trips", failed_trips.group(1) if failed_trips else "0")
            with col3:
                st.metric("Success Rate", f"{success_rate.group(1)}%" if success_rate else "0%")
            
            # Extract station statistics and create DataFrames
            station_usage = []
            for line in console_output.split('\n'):
                if "Station" in line and "trips" in line:
                    parts = line.split(": ")
                    station_usage.append({
                        "Station": parts[0].replace("Station ", ""),
                        "Trips": int(parts[1].split()[0])
                    })
            
            # Create DataFrame and sort
            usage_df = pd.DataFrame(station_usage).sort_values("Trips", ascending=False)
            
            # Display station statistics in table
            st.subheader("Most Used Stations")
            st.dataframe(usage_df, use_container_width=True)
            
            # Add collapsible console output
            with st.expander("View Console Output"):
                st.code(console_output, language="text")

    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4 = st.tabs(["Trip Animation", "Trip Paths", "Heatmaps", "POI Distribution"])

    with tab1:
        st.subheader("Hourly Trip Animation")
        if os.path.exists('./generated/hourly_trip_animation.html'):
            with open('./generated/hourly_trip_animation.html', 'r') as f:
                components.html(f.read(), height=600)

    with tab2:
        st.subheader("All Trip Paths")
        if os.path.exists('./generated/all_trip_paths.html'):
            with open('./generated/all_trip_paths.html', 'r') as f:
                components.html(f.read(), height=600)

    with tab3:
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Results Heatmap")
            if os.path.exists('./generated/simulation_results_heatmap.png'):
                st.image('./generated/simulation_results_heatmap.png')
        with col4:
            st.subheader("Hourly Station Heatmap")
            if os.path.exists('./generated/hourly_station_heatmap.png'):
                st.image('./generated/hourly_station_heatmap.png')

    with tab4:
        st.subheader("POI Distribution")
        if os.path.exists('./generated/poi_and_boundaries_map.html'):
            with open('./generated/poi_and_boundaries_map.html', 'r') as f:
                components.html(f.read(), height=600)

else:
    st.info("Configure simulation parameters and click 'Run Simulation' to start.") 