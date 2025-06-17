# dashboard.py

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path

from main import run_simulation
import config
import visualizations

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
    walking_threshold = st.slider(
        "Maximum Walking Distance (km)",
        min_value=0.1, max_value=2.0, value=config.MAX_TOTAL_WALK_DISTANCE_KM, step=0.1
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

        # Create station map for lookups
        station_map = {s.id: s.neighbourhood for s in bike_system.stations}

        # Key metrics at the top
        col1, col2, col3 = st.columns(3)
        col1.metric("Successful Trips", f"{stats['successful_trips']:,}")
        col2.metric("Failed Trips", f"{stats['failed_trips']:,}")
        col3.metric("Success Rate", f"{success_rate:.1f}%")

        # Main tabs for different aspects of the simulation
        tabs = ["System Overview", "Station Analysis", "Trip Analysis", "System Maps", "Rebalancing"]
        tab1, tab2, tab3, tab4, tab5 = st.tabs(tabs)

        with tab1:
            # System Overview tab - Key visualizations and metrics
            st.subheader("System Performance")
            col_overview1, col_overview2 = st.columns(2)
            with col_overview1:
                st.subheader("Failed Trips by Hour")
                display_image_file(config.HOURLY_FAILURES_PATH)
            with col_overview2:
                st.subheader("Hourly Station Activity")
                display_image_file(config.HOURLY_STATION_HEATMAP_PATH)

            st.subheader("Station Usage Statistics")
            usage_data = [
                {"Station": station_map.get(s_id, f"ID_{s_id}"), "Trips": trips}
                for s_id, trips in bike_system.station_usage.items()
            ]
            usage_df = pd.DataFrame(usage_data).sort_values("Trips", ascending=False, ignore_index=True)
            st.dataframe(usage_df, use_container_width=True)

        with tab2:
            # Station Analysis tab - Detailed station data
            st.subheader("Station Data")
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

        with tab3:
            # Trip Analysis tab - Trip-related visualizations
            st.subheader("Trip Patterns")
            col_trip1, col_trip2 = st.columns(2)
            with col_trip1:
                st.subheader("Route Usage Heatmap")
                display_image_file(config.RESULTS_HEATMAP_PATH)
            with col_trip2:
                st.subheader("All Trip Paths")
                display_html_file(config.ALL_TRIP_PATHS_MAP_PATH)

        with tab4:
            # System Maps tab - Interactive maps and animations
            st.subheader("Interactive Maps")
            map_tabs = ["Trip Animation", "Station Availability", "POI Distribution"]
            map_tab1, map_tab2, map_tab3 = st.tabs(map_tabs)
            
            with map_tab1:
                st.subheader("Hourly Trip Animation")
                display_html_file(config.HOURLY_TRIP_ANIMATION_PATH)
            
            with map_tab2:
                st.subheader("Hourly Station Availability Animation")
                display_html_file(config.STATION_AVAILABILITY_ANIMATION_PATH)
            
            with map_tab3:
                st.subheader("POI Distribution")
                display_html_file(config.POI_MAP_PATH)

        with tab5:
            # Rebalancing tab
            st.subheader("Bike Rebalancing")
            
            # Threshold slider
            min_threshold, max_threshold = st.slider(
                "Station Fill Ratio Thresholds",
                min_value=0.0,
                max_value=1.0,
                value=(0.3, 0.7),
                step=0.05,
                help="Stations with fill ratio below min or above max will be included in rebalancing"
            )

            # Show stations needing rebalancing
            stations_to_rebalance = bike_system.get_stations_needing_rebalancing(min_threshold, max_threshold)
            if stations_to_rebalance:
                st.write(f"Found {len(stations_to_rebalance)} stations needing rebalancing:")
                rebalance_data = [
                    {
                        "Station": s.neighbourhood,
                        "Current Bikes": s.bikes,
                        "Capacity": s.capacity,
                        "Fill Ratio": f"{(s.bikes / s.capacity) * 100:.1f}%"
                    }
                    for s in stations_to_rebalance
                ]
                st.dataframe(pd.DataFrame(rebalance_data), use_container_width=True)

                if st.button("Generate Rebalancing Route"):
                    with st.spinner("Generating optimal rebalancing route..."):
                        route_path = visualizations.create_rebalancing_route_map(
                            bike_system, min_threshold, max_threshold
                        )
                        if route_path:
                            st.success("Route generated successfully!")
                            display_html_file(Path(route_path))
                            
                            # Display the visit order table
                            order_path = config.GENERATED_DIR / 'rebalancing_order.html'
                            if order_path.exists():
                                st.subheader("Visit Order")
                                with open(order_path, 'r') as f:
                                    st.components.html(f.read(), height=400, scrolling=True)
                        else:
                            st.error("Failed to generate rebalancing route. Check if OpenRouteService is available.")
            else:
                st.info("No stations need rebalancing with current thresholds.")

        # Console log at the bottom
        with st.expander("View Console Log"):
            try:
                with open(config.CONSOLE_OUTPUT_PATH, 'r') as f:
                    st.code(f.read(), language="text")
            except FileNotFoundError:
                st.warning("Console output file not found.")