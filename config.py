# config.py
# Description: Configuration file for the bike-sharing simulation.

# --- API Configuration ---
# IMPORTANT: Replace with your actual OpenRouteService API key
ORS_API_KEY = "5b3ce3597851110001cf624840280065392845ed8f651a2e15a81dd8"

# --- Simulation Parameters ---
SIMULATION_TIME = 120      # Total simulation time in minutes (e.g., 120 for 2 hours)
USER_ARRIVAL_RATE = 0.2    # Average number of users arriving per minute

# --- Data Paths ---
POI_DATABASE_PATH = './data/poi_database.json'
NEIGHBOURHOOD_GEOJSON_PATH = './data/buurten.geojson'

# --- Geographic Configuration ---
# City query for OSMnx to fetch the correct street network
CITY_QUERY = "Eindhoven, Netherlands"

# This list is the single source of truth for which neighborhoods to use
# for both station placement and POI generation.
# Names must exactly match the 'buurtnaam' field in the geojson file.
NEIGHBOURHOODS_TO_USE = [
    # Group 'Acht'
    'Achtse Barrier-Hoeven',
    'Achtse Barrier-Spaaihoef',
    'Kerkdorp Acht',
    'Achtse Barrier-Gunterslaer',
    'Kapelbeemd',
    # Group 'Vredeoord'
    'Vredeoord',
    # Group 'Karpen'
    'Karpen',
]