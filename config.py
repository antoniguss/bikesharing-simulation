# config.py
from pathlib import Path

# --- Simulation Parameters ---
SIMULATION_DURATION = 24 * 60  # Total simulation time in minutes
SIMULATION_START_TIME = 0 * 60   # Simulation start time in minutes from midnight (e.g., 6 * 60 for 6:00 AM)
MAX_TOTAL_WALK_DISTANCE_KM = 0.75 # Maximum total walking distance for a trip (to and from stations), currently 750 m which takes ~10 mins

# --- Physical Constants ---
WALKING_SPEED_KMPH = 5.0
CYCLING_SPEED_KMPH = 15.0

# --- Path Configuration ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
CACHE_DIR = BASE_DIR / 'cache'
GENERATED_DIR = BASE_DIR / 'generated'

# Source Data (must exist)
NEIGHBORHOOD_AREAS_GEOJSON_PATH = DATA_DIR / 'neighbourhoods.geojson'
STATION_GEOJSON_PATH = DATA_DIR / 'ev_stations.geojson'
POI_WEIGHTS_PATH = DATA_DIR / 'poi_weights.csv'
TIME_WEIGHTS_PATH = DATA_DIR / 'time_weights.csv'

# Cached Data (can be regenerated)
POI_DATABASE_PATH = CACHE_DIR / 'poi_database.json'
GRAPH_FILE_PATH = CACHE_DIR / 'eindhoven_bike_network.graphml'
STATION_ROUTES_CACHE_PATH = CACHE_DIR / 'station_routes.pkl'
STATION_ROUTES_META_PATH = CACHE_DIR / 'station_routes_meta.json'

# Generated Output
CONSOLE_OUTPUT_PATH = GENERATED_DIR / 'console_output.txt'
HOURLY_TRIP_ANIMATION_PATH = GENERATED_DIR / 'hourly_trip_animation.html'
STATION_AVAILABILITY_ANIMATION_PATH = GENERATED_DIR / 'station_availability_animation.html'
ALL_TRIP_PATHS_MAP_PATH = GENERATED_DIR / 'all_trip_paths.html'
RESULTS_HEATMAP_PATH = GENERATED_DIR / 'simulation_results_heatmap.png'
HOURLY_STATION_HEATMAP_PATH = GENERATED_DIR / 'hourly_station_heatmap.png'
POI_MAP_PATH = GENERATED_DIR / 'poi_and_boundaries_map.html'
REBALANCING_ROUTE_MAP_PATH = GENERATED_DIR / 'rebalancing_route.html'
HOURLY_FAILURES_PATH = GENERATED_DIR / 'hourly_failures.png'

# --- Geographic Configuration ---
CITY_QUERY = "Eindhoven, Netherlands"