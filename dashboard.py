# dashboard.py

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path

from main import run_simulation
import config

st.set_page_config(layout="wide", page_title="Bike Share Simulation Dashboard")

def display_html_file(file_path: Path):
    """Checks if a file exists and displays it as HTML in the dashboard."""
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            components.html(f.read(), height=600, scrolling=True)
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
        min_value=1, max_value=48, value=config.SIMULATION_DURATION // 60, step=1
    )
    start_time_hours = st.slider(
        "Start Time (24-hour format)",
        min_value=0, max_value=23, value=config.SIMULATION_START_TIME // 60, step=1
    )

    with st.expander("Edit Weights", expanded=False):
        try:
            poi_weights_df = pd.read_csv(config.POI_WEIGHTS_PATH)
            edited_poi_weights = st.data_editor(poi_weights_df, use_container_width=True, key="poi_editor")
            if st.button("Save POI Weights"):
                edited_poi_weights.to_csv(config.POI_WEIGHTS_PATH, index=False)
                st.success("POI weights saved!")
        except FileNotFoundError:
            st.error(f"File not found: {config.POI_WEIGHTS_PATH}")
        
        try:
            time_weights_df = pd.read_csv(config.TIME_WEIGHTS_PATH)
            edited_time_weights = st.data_editor(time_weights_df, use_container_width=True, key="time_editor")
            if st.button("Save Time Weights"):
                edited_time_weights.to_csv(config.TIME_WEIGHTS_PATH, index=False)
                st.success("Time weights saved!")
        except FileNotFoundError:
            st.error(f"File not found: {config.TIME_WEIGHTS_PATH}")

    if st.button("Run Simulation", type="primary", use_container_width=True):
        st.info("Starting simulation initialization... This may take a few minutes if data needs to be downloaded.")
        with st.spinner("Running simulation... This may take a few minutes."):
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
        stats = bike_system.stats
        total_trips = stats["successful_trips"] + stats["failed_trips"]
        success_rate = (stats["successful_trips"] / total_trips * 100) if total_trips > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Successful Trips", f"{stats['successful_trips']:,}")
        col2.metric("Failed Trips", f"{stats['failed_trips']:,}")
        col3.metric("Success Rate", f"{success_rate:.1f}%")

        tabs = ["Station Data", "Trip Animation", "Station Availability", "All Trip Paths", "Heatmaps", "POI Distribution", "Logs", "Rebalancing Route"]
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(tabs)

        with tab1:
            st.subheader("Hourly Bike Availability per Station")
            station_map = {s.id: s.neighbourhood for s in bike_system.stations}
            
            if bike_system.hourly_bike_counts:
                counts_df = pd.DataFrame(bike_system.hourly_bike_counts).sort_index()
                counts_df.index = counts_df.index.map(station_map)
                counts_df.index.name = "Station"
                counts_df.columns = [f"{(h % 24):02d}:00" for h in sorted(counts_df.columns)]
                counts_df = counts_df.reindex(sorted(counts_df.columns), axis=1)

                station_capacities = {s.neighbourhood: s.capacity for s in bike_system.stations}
                
                def style_bike_counts(row):
                    """Applies CSS styling to a row based on bike counts vs. capacity percentage."""
                    capacity = station_capacities.get(row.name)
                    if not capacity: return ['' for _ in row]
                    
                    styles = []
                    for bikes in row:
                        style = ''
                        fill_ratio = bikes / capacity
                        if bikes == 0:
                            style = 'background-color: #ffadad'  # Light Red: Empty
                        elif bikes == capacity:
                            style = 'background-color: #a2d2ff'  # Light Blue: Full
                        elif fill_ratio <= 0.3:
                            style = 'background-color: #ffd6a5'  # Light Orange: Almost Empty
                        elif fill_ratio >= 0.8:
                            style = 'background-color: #bde0fe'  # Lighter Blue: Almost Full
                        styles.append(style)
                    return styles

                styled_df = counts_df.style.apply(style_bike_counts, axis=1)
                st.dataframe(styled_df, use_container_width=True)

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
            display_html_file(config.HOURLY_TRIP_ANIMATION_PATH)

        with tab3:
            st.subheader("Hourly Station Availability Animation")
            display_html_file(config.STATION_AVAILABILITY_ANIMATION_PATH)

        with tab4:
            st.subheader("All Trip Paths")
            display_html_file(config.ALL_TRIP_PATHS_MAP_PATH)

        with tab5:
            col_heat1, col_heat2 = st.columns(2)
            with col_heat1:
                st.subheader("Route Usage Heatmap")
                display_image_file(config.RESULTS_HEATMAP_PATH)
            with col_heat2:
                st.subheader("Hourly Station Activity")
                display_image_file(config.HOURLY_STATION_HEATMAP_PATH)

        with tab6:
            st.subheader("POI Distribution")
            display_html_file(config.POI_MAP_PATH)

        with tab7:
            st.subheader("Console Log")
            try:
                with open(config.CONSOLE_OUTPUT_PATH, 'r') as f:
                    st.code(f.read(), language="text")
            except FileNotFoundError:
                st.warning("Console output file not found.")

        with tab8:
            st.subheader("Rebalancing Route Optimization")
            
            col1, col2 = st.columns(2)
            with col1:
                low_threshold = st.slider("Low Bike Threshold (%)", 0, 50, 30)
            with col2:
                high_threshold = st.slider("High Bike Threshold (%)", 50, 100, 70)

            if st.button("Calculate Rebalancing Route"):
                stations_to_visit = []
                for station in bike_system.stations:
                    fill_ratio = station.bikes / station.capacity
                    if fill_ratio < (low_threshold / 100) or fill_ratio > (high_threshold / 100):
                        stations_to_visit.append(station)

                if not stations_to_visit:
                    st.info("No stations need rebalancing with current thresholds.")
                else:
                    # Get coordinates for route optimization
                    station_coords = [(s.x, s.y) for s in stations_to_visit]
                    route_data = bike_system.ors_client.optimize_rebalancing_route(station_coords)

                    if route_data:
                        from visualizations import create_rebalancing_route_map
                        create_rebalancing_route_map(bike_system, route_data, stations_to_visit)
                        
                        # Display the route map
                        display_html_file(config.REBALANCING_ROUTE_MAP_PATH)
                        
                        # Display station visit order
                        st.subheader("Station Visit Order")
                        visit_data = []
                        for i, station in enumerate(stations_to_visit, 1):
                            fill_ratio = station.bikes / station.capacity
                            reason = "Low bikes" if fill_ratio < (low_threshold / 100) else "High bikes"
                            visit_data.append({
                                "Order": i,
                                "Station": station.neighbourhood,
                                "Current Bikes": station.bikes,
                                "Capacity": station.capacity,
                                "Fill Ratio": f"{fill_ratio:.1%}",
                                "Reason": reason
                            })
                        st.dataframe(pd.DataFrame(visit_data), use_container_width=True)
                    else:
                        st.error("Failed to calculate optimized route. Please check your ORS API key.")