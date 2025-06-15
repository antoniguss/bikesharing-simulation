# config.py

# --- Simulation Parameters ---
SIMULATION_DURATION = 24 * 60      # Total simulation time in minutes
SIMULATION_START_TIME = 6 * 60


MAX_TOTAL_WALK_DISTANCE_KM = 1.0 # 1 KM walking max

# --- Data & Model Paths (Updated with new cache paths) ---
# Cached data that can be regenerated
POI_DATABASE_PATH = './cache/poi_database.json'
GRAPH_FILE_PATH = './cache/eindhoven_bike_network.graphml'
STATION_ROUTES_CACHE_PATH = './cache/station_routes.pkl'
STATION_ROUTES_META_PATH = './cache/station_routes_meta.json' # Stores a hash to check if the station file has changed

# Source data that must exist
NEIGHBORHOOD_AREAS_GEOJSON_PATH = './data/neighbourhoods.geojson' 
STATION_GEOJSON_PATH = './data/ev_stations.geojson'
POI_WEIGHTS_PATH = './data/poi_weights.csv'
TIME_WEIGHTS_PATH = './data/time_weights.csv'

GENERATED_DIR = './generated'

# --- Geographic Configuration ---
CITY_QUERY = "Eindhoven, Netherlands"