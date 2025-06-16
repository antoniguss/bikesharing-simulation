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
        
        # Run simulation and store the returned system object
        bike_system_result = run_simulation()
        st.session_state.simulation_run = True
        st.session_state.bike_system = bike_system_result
        st.success("Simulation completed!")

# Only show results if simulation has been run
if st.session_state.simulation_run:
    st.header("Simulation Results")
    
    bike_system = st.session_state.get('bike_system')

    # Create summary metrics directly from the simulation object
    if bike_system:
        stats = bike_system.stats
        total_trips = stats["successful_trips"] + stats["failed_trips"]
        success_rate = (stats["successful_trips"] / total_trips * 100 if total_trips > 0 else 0)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Successful Trips", stats['successful_trips'])
        with col2:
            st.metric("Failed Trips", stats['failed_trips'])
        with col3:
            st.metric("Success Rate", f"{success_rate:.1f}%")
    else:
        st.warning("Simulation data not found. Please run the simulation again.")

    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Trip Animation", "Trip Paths", "Heatmaps", "POI Distribution", "Station Data"])

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
    
    with tab5:
        st.subheader("Most Used Stations")
        if bike_system:
            station_map = {s.id: s.neighbourhood for s in bike_system.stations}
            usage_data = [
                {"Station": station_map.get(s_id, f"ID_{s_id}"), "Trips": trips}
                for s_id, trips in bike_system.station_usage.items()
            ]
            usage_df = pd.DataFrame(usage_data).sort_values("Trips", ascending=False, ignore_index=True)
            st.dataframe(usage_df, use_container_width=True)
            
            st.subheader("Hourly Bike Count per Station")
            if bike_system.hourly_bike_counts:
                # Prepare data for DataFrame
                df = pd.DataFrame(bike_system.hourly_bike_counts)
                
                # Map index from station ID to station name
                df.index = df.index.map(station_map)
                df.index.name = "Station"
                
                # Sort rows by station name and columns by hour
                df.sort_index(inplace=True)
                df = df.reindex(sorted(df.columns), axis=1)
                
                # Format column headers to be human-readable (e.g., 06:00, 14:00)
                df.columns = [f"{(hour % 24):02d}:00" for hour in df.columns]
                
                # Display the table
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No hourly bike count data available (simulation might have been too short).")
        else:
            st.warning("Could not load station data from the simulation.")
            
        with st.expander("View Raw Console Output"):
            if os.path.exists('./generated/console_output.txt'):
                with open('./generated/console_output.txt', 'r') as f:
                    st.code(f.read(), language="text")
            else:
                st.info("Console output file not found.")

else:
    st.info("Configure simulation parameters and click 'Run Simulation' to start.")