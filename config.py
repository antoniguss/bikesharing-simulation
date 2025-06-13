# config.py

# --- Simulation Parameters ---
SIMULATION_TIME = 1440      # Total simulation time in minutes (24 hours)

# --- Data & Model Paths ---
POI_DATABASE_PATH = './data/poi_database.json'
NEIGHBORHOOD_AREAS_GEOJSON_PATH = './data/neighbourhoods.geojson' 
STATION_GEOJSON_PATH = './data/ev_our_stations.geojson'
GRAPH_FILE_PATH = './data/eindhoven_bike_network.graphml'
POI_WEIGHTS_PATH = './data/poi_weights.csv'
TIME_WEIGHTS_PATH = './data/time_weights.csv'

# --- Geographic Configuration ---
CITY_QUERY = "Eindhoven, Netherlands"