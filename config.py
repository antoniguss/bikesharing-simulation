# config.py
# Description: Configuration file for the bike-sharing simulation.

# --- Simulation Parameters ---
SIMULATION_TIME = 1440      # Total simulation time in minutes (e.g., 120 for 2 hours)
USER_ARRIVAL_RATE = 0.2    # Average number of users arriving per minute

# --- Data & Model Paths ---
POI_DATABASE_PATH = './data/poi_database.json'
NEIGHBORHOOD_AREAS_GEOJSON_PATH = './data/neighbourhoods.geojson' 
STATION_GEOJSON_PATH = './data/ev_our_stations.geojson'
# Path to save/load the OSMnx street network graph
GRAPH_FILE_PATH = './data/eindhoven_bike_network.graphml'

# --- Geographic Configuration ---
# City query for OSMnx to fetch the correct street network if the graph file doesn't exist
CITY_QUERY = "Eindhoven, Netherlands"

# This list controls which neighborhoods POIs are generated in.
NEIGHBOURHOODS_TO_USE = [
    # Group 'Acht'
    'Achtse Barrier-Hoeven', 'Achtse Barrier-Spaaihoef', 'Kerkdorp Acht',
    'Achtse Barrier-Gunterslaer', 'Kapelbeemd',
    # Group 'Vredeoord'
    'Vredeoord',
    # Group 'Karpen'
    'Karpen',
]