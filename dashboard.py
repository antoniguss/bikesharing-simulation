# dashboard.py

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path

from main import run_simulation
from config import (
    SIMULATION_DURATION, SIMULATION_START_TIME, POI_WEIGHTS_PATH,
    TIME_WEIGHTS_PATH, CONSOLE_OUTPUT_PATH, HOURLY_TRIP_ANIMATION_PATH,
    ALL_TRIP_PATHS_MAP_PATH, RESULTS_HEATMAP_PATH,
    HOURLY_STATION_HEATMAP_PATH, POI_MAP_PATH
)

st.set_page_config(layout="wide", page_title="Bike Share Simulation Dashboard")

def display_html_file(file_path: Path):
    """Checks if a file exists and displays it as HTML in the dashboard."""
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            components.html(f.read(), height=600)
    else:
        st.warning(f"Visualization not found: {file_path.name}")

def display_image_file(file_path: Path):
    """Checks if a file exists and displays it as an image."""
    if file_path.exists():
        st.image(str(file_path))
    else:
        st.warning(f"Image not found: {file_path.name}")

# --- Session State Initialization ---
if 'simulation_run' not in st.session_state:
    st.session_state.simulation_run = False
if 'bike_system' not in st.session_state:
    st.session_state.bike_system = None

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Simulation Parameters")

    duration_hours = st.slider(
        "Simulation Duration (hours)",
        min_value=1, max_value=48, value=SIMULATION_DURATION // 60, step=1
    )
    start_time_hours = st.slider(
        "Start Time (24-hour format)",
        min_value=0, max_value=23, value=SIMULATION_START_TIME // 60, step=1
    )

    with st.expander("Edit Weights", expanded=False):
        try:
            poi_weights_df = pd.read_csv(POI_WEIGHTS_PATH)
            edited_poi_weights = st.data_editor(poi_weights_df, use_container_width=True, key="poi_editor")
            if st.button("Save POI Weights"):
                edited_poi_weights.to_csv(POI_WEIGHTS_PATH, index=False)
                st.success("POI weights saved!")
        except FileNotFoundError:
            st.error(f"File not found: {POI_WEIGHTS_PATH}")
        
        try:
            time_weights_df = pd.read_csv(TIME_WEIGHTS_PATH)
            edited_time_weights = st.data_editor(time_weights_df, use_container_width=True, key="time_editor")
            if st.button("Save Time Weights"):
                edited_time_weights.to_csv(TIME_WEIGHTS_PATH, index=False)
                st.success("Time weights saved!")
        except FileNotFoundError:
            st.error(f"File not found: {TIME_WEIGHTS_PATH}")

    if st.button("Run Simulation", type="primary", use_container_width=True):
        with st.spinner("Running simulation... This may take a few minutes."):
            import config
            config.SIMULATION_DURATION = duration_hours * 60
            config.SIMULATION_START_TIME = start_time_hours * 60
            
            bike_system_result = run_simulation()
            
            st.session_state.simulation_run = True
            st.session_state.bike_system = bike_system_result
        st.success("Simulation completed!")
        st.rerun()

# --- Main Content Area ---
st.title("Bike Share System Simulation")

if not st.session_state.simulation_run:
    st.info("Configure simulation parameters in the sidebar and click 'Run Simulation' to start.")
else:
    st.header("Simulation Results")
    bike_system = st.session_state.bike_system

    if not bike_system:
        st.error("Simulation data is missing. Please try running the simulation again.")
    else:
        # Key Metrics
        stats = bike_system.stats
        total_trips = stats["successful_trips"] + stats["failed_trips"]
        success_rate = (stats["successful_trips"] / total_trips * 100) if total_trips > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Successful Trips", f"{stats['successful_trips']:,}")
        col2.metric("Failed Trips", f"{stats['failed_trips']:,}")
        col3.metric("Success Rate", f"{success_rate:.1f}%")

        # Visualization and Data Tabs
        tabs = ["Station Data", "Trip Animation", "All Trip Paths", "Heatmaps", "POI Distribution", "Logs"]
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(tabs)

        with tab1:
            st.subheader("Hourly Bike Availability per Station")
            station_map = {s.id: s.neighbourhood for s in bike_system.stations}
            
            if bike_system.hourly_bike_counts:
                counts_df = pd.DataFrame(bike_system.hourly_bike_counts).sort_index()
                counts_df.index = counts_df.index.map(station_map)
                counts_df.index.name = "Station"
                counts_df.columns = [f"{(h % 24):02d}:00" for h in sorted(counts_df.columns)]
                counts_df = counts_df.reindex(sorted(counts_df.columns), axis=1)

                # --- NEW STYLING LOGIC ---
                station_capacities = {s.neighbourhood: s.capacity for s in bike_system.stations}
                
                def style_bike_counts(row):
                    """Applies CSS styling to a row based on bike counts vs. capacity."""
                    capacity = station_capacities.get(row.name)
                    if not capacity:
                        return ['' for _ in row] # No styling if capacity is unknown
                    
                    styles = []
                    for bikes in row:
                        style = ''
                        if bikes == 0:
                            style = 'background-color: #ffadad' # Light Red: Empty
                        elif bikes == capacity:
                            style = 'background-color: #add8e6' # Light Blue: Full
                        elif bikes <= 2:
                            style = 'background-color: #ffd6a5' # Light Orange: Low Stock
                    
                        styles.append(style)
                    return styles

                styled_df = counts_df.style.apply(style_bike_counts, axis=1)
                st.dataframe(styled_df, use_container_width=True)
                # --- END NEW STYLING LOGIC ---

            else:
                st.info("No hourly bike count data was recorded.")
            
            st.subheader("Station Trip Counts")
            usage_data = [
                {"Station": station_map.get(s_id, f"ID_{s_id}"), "Trips": trips}
                for s_id, trips in bike_system.station_usage.items()
            ]
            usage_df = pd.DataFrame(usage_data).sort_values("Trips", ascending=False, ignore_index=True)
            st.dataframe(usage_df, use_container_width=True)

        with tab2:
            st.subheader("Hourly Trip Animation")
            display_html_file(HOURLY_TRIP_ANIMATION_PATH)

        with tab3:
            st.subheader("All Trip Paths")
            display_html_file(ALL_TRIP_PATHS_MAP_PATH)

        with tab4:
            col_heat1, col_heat2 = st.columns(2)
            with col_heat1:
                st.subheader("Route Usage Heatmap")
                display_image_file(RESULTS_HEATMAP_PATH)
            with col_heat2:
                st.subheader("Hourly Station Activity")
                display_image_file(HOURLY_STATION_HEATMAP_PATH)

        with tab5:
            st.subheader("POI Distribution")
            display_html_file(POI_MAP_PATH)

        with tab6:
            st.subheader("Console Log")
            try:
                with open(CONSOLE_OUTPUT_PATH, 'r') as f:
                    st.code(f.read(), language="text")
            except FileNotFoundError:
                st.warning("Console output file not found.")