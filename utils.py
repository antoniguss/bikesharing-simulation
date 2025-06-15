# utils.py

import math
import json
import random
import os
import osmnx as ox
import geopandas as gpd
import pandas as pd
import hashlib
import csv
from shapely.geometry import Polygon, Point
from config import NEIGHBORHOOD_AREAS_GEOJSON_PATH, POI_WEIGHTS_PATH, TIME_WEIGHTS_PATH

# Configure OSMNX Caching
ox.utils.settings.use_cache = True
ox.utils.settings.cache_folder = './cache/osmnx'
ox.utils.settings.log_console = False

# Fallback Map
FALLBACK_POI_MAP = {
    'sport': 'park',
    'restaurant': 'shops',
    'uni': 'edu',
    'hospital': 'shops',
    'edu': 'home',
}

def get_file_md5(filepath: str) -> str:
    """Calculates the MD5 hash of a file."""
    try:
        with open(filepath, 'rb') as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        return file_hash.hexdigest()
    except FileNotFoundError:
        return ""

def get_osmnx_graph(city_query: str, graph_filepath: str):
    if os.path.exists(graph_filepath):
        print(f"Loading graph from file: {graph_filepath}")
        return ox.load_graphml(filepath=graph_filepath)
    else:
        print(f"Graph file not found. Downloading network for '{city_query}'.")
        graph = ox.graph_from_place(city_query, network_type='bike')
        os.makedirs(os.path.dirname(graph_filepath), exist_ok=True)
        print(f"Saving graph to {graph_filepath} for future use.")
        ox.save_graphml(graph, filepath=graph_filepath)
        return graph

def haversine_distance(p1: tuple, p2: tuple) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, [p1[0], p1[1], p2[0], p2[1]])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 6371 * (2 * math.asin(math.sqrt(a)))

def get_random_point_in_polygon(polygon: Polygon) -> tuple:
    min_x, min_y, max_x, max_y = polygon.bounds
    while True:
        point = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))
        if polygon.contains(point):
            return (point.x, point.y)

class POIDatabase:
    def __init__(self, database_path: str):
        self.db_file_path = database_path
        self.poi_data = {}
        if os.path.exists(self.db_file_path):
            print("Loading existing POI database...")
            self.load_database()
        else:
            print("POI database not found. Generating a new one...")
            self.generate_database()

    def generate_database(self):
        print("Generating new POI database from source files...")
        try:
            areas_gdf = gpd.read_file(NEIGHBORHOOD_AREAS_GEOJSON_PATH)
        except Exception as e:
            raise SystemExit(f"Error reading '{NEIGHBORHOOD_AREAS_GEOJSON_PATH}': {e}")
        
        # 'uni' (campus) is a special case where the polygon itself is the POI
        special_areas = {'uni': 'campus', 'station':'station'}
        
        # 'station' is now a standard query type, but with its own logic
        poi_tags = {
            'home': {'building': ['residential', 'house', 'apartments']},
            'shops': {'shop': True}, 'hospital': {'amenity': ['hospital', 'clinic', 'doctors']},
            'edu': {'amenity': ['school', 'kindergarten', 'college']},
            'restaurant': {'amenity': 'restaurant'}, 'park': {'leisure': ['park', 'playground', 'garden']},
            'sport': {'leisure': ['sports_centre', 'pitch', 'stadium'], 'sport': True}
        }
        # Initialize all lists, including 'station'
        self.poi_data = {key: [] for key in poi_tags}
        self.poi_data.update({key: [] for key in special_areas})
        self.poi_data['station'] = []

        for _, row in areas_gdf.iterrows():
            area_name, geometry = row['buurtnaam'], row['geometry']
            
            # Handle special area polygons first (like 'uni')
            is_special_area = False
            for key, val in special_areas.items():
                if area_name == val:
                    self.poi_data[key].append({'name': area_name, 'geometry': geometry})
                    is_special_area = True
                    break
            if is_special_area:
                continue


            # Handle all other regular neighborhoods
            self._fetch_and_append_pois(geometry, poi_tags)
        
        self.save_database()
        print("Successfully generated and saved new POI database.")
        self._print_generation_summary()

    def _print_generation_summary(self):
        print("\n--- POI Database Generation Summary ---")
        for key, value in sorted(self.poi_data.items()):
            print(f"  -> Found {len(value):>5} POIs for type: '{key}'")
        print("------------------------------------\n")

    def _fetch_and_append_buildings_for_station(self, geometry):
        """Fetches all building centroids within the 'Station' area polygon."""
        try:
            # The tag {'building': True} gets all types of buildings
            pois = ox.features_from_polygon(geometry, tags={'building': True})
            for _, poi in pois.iterrows():
                self.poi_data['station'].append({'lat': poi.geometry.centroid.y, 'lon': poi.geometry.centroid.x})
        except Exception as e:
            print(f"    - Could not fetch buildings for station area: {e}")

    def _fetch_and_append_pois(self, geometry, poi_tags):
        for poi_type, tags in poi_tags.items():
            try:
                pois = ox.features_from_polygon(geometry, tags)
                if poi_type == 'home' and len(pois) > 200:
                    pois = pois.sample(n=200)
                for _, poi in pois.iterrows():
                    self.poi_data[poi_type].append({'lat': poi.geometry.centroid.y, 'lon': poi.geometry.centroid.x})
            except Exception:
                continue
    
    def load_database(self):
        with open(self.db_file_path, 'r') as f:
            raw_data = json.load(f)
            self.poi_data = {}
            for key, poi_list in raw_data.items():
                self.poi_data[key] = []
                for poi_dict in poi_list:
                    if 'geometry' in poi_dict and poi_dict.get('geometry'):
                        poi_dict['geometry'] = Polygon(poi_dict['geometry']['coordinates'][0])
                    self.poi_data[key].append(poi_dict)
    
    def save_database(self):
        os.makedirs(os.path.dirname(self.db_file_path), exist_ok=True)
        serializable_data = {}
        for key, poi_list in self.poi_data.items():
            serializable_data[key] = []
            for poi in poi_list:
                if 'geometry' in poi:
                    serializable_data[key].append({'name': poi['name'], 'geometry': {'type': 'Polygon', 'coordinates': [list(poi['geometry'].exterior.coords)]}})
                else:
                    serializable_data[key].append(poi)
        with open(self.db_file_path, 'w') as f:
            json.dump(serializable_data, f, indent=2)

    def get_random_poi(self, poi_type: str):
        # print(poi_type, "GETTING RANDOM POI OF TYPE {poi_type}")
        return random.choice(self.poi_data[poi_type.strip()])

class WeightManager:
    def __init__(self):
        try:
            # Read CSV into DataFrame, index_col=0 to use first column as amenity index
            self.poi_weights = pd.read_csv(POI_WEIGHTS_PATH, index_col=0)
            
            # Ensure column names are strings (hours as '0'...'23')
            self.poi_weights.columns = self.poi_weights.columns.map(str)
            
            # Load time weights as before
            self.time_weights = pd.read_csv(TIME_WEIGHTS_PATH, index_col='hour')

            print("Successfully loaded POI and time weights.")
        
        except FileNotFoundError as e:
            raise SystemExit(f"Error: Weight file not found. {e}")

    def get_poi_type_for_hour(self, hour: int) -> str:
        hour_str = str(hour)
        
        if hour_str not in self.poi_weights.columns:
            # fallback
            return random.choice(self.poi_weights.index)
        
        weights = self.poi_weights[hour_str]
        
        if weights.sum() == 0:
            # fallback if all weights zero
            return random.choice(self.poi_weights.index)
        
        # weighted random choice among amenities
        choices = random.choices(weights.index, weights=list(weights.values), k=1)
        return str(choices[0])
    
    def get_arrival_rate_for_hour(self, hour: int) -> float:
        key = f"hour_{hour}"
        if key in self.time_weights.index:
            value = self.time_weights.loc[key, 'estimated_trips']
            return float(value) / 60
        else:
            return 0.01
