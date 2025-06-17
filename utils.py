# utils.py
import math
import json
import random
import hashlib
import pandas as pd
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon, Point, mapping
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import os
import streamlit as st

from config import (
    NEIGHBORHOOD_AREAS_GEOJSON_PATH, POI_WEIGHTS_PATH, TIME_WEIGHTS_PATH,
    POI_DATABASE_PATH, CACHE_DIR
)

ox.utils.settings.use_cache = True
ox.utils.settings.cache_folder = str(CACHE_DIR / 'osmnx')
ox.utils.settings.log_console = False

def get_file_md5(filepath: Path) -> str:
    """Calculates the MD5 hash of a file to check for changes."""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        return ""

def get_osmnx_graph(city_query: str, graph_filepath: Path):
    """Loads a street network graph from a local file or downloads it if not present."""
    if graph_filepath.exists():
        print(f"Loading graph from {graph_filepath}")
        return ox.load_graphml(filepath=str(graph_filepath))
    
    print(f"Graph file not found. Downloading network for '{city_query}'...")
    graph = ox.graph_from_place(city_query, network_type='bike')
    graph_filepath.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, filepath=str(graph_filepath))
    print(f"Saved graph to {graph_filepath}")
    return graph

def haversine_distance(p1: tuple, p2: tuple) -> float:
    """Calculates the great-circle distance between two (lon, lat) points in kilometers."""
    lon1, lat1, lon2, lat2 = map(math.radians, [p1[0], p1[1], p2[0], p2[1]])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return 6371 * (2 * math.asin(math.sqrt(a)))

def get_random_point_in_polygon(polygon: Polygon) -> tuple:
    """Generates a random point safely within the bounds of a Polygon."""
    min_x, min_y, max_x, max_y = polygon.bounds
    while True:
        point = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))
        if polygon.contains(point):
            return (point.x, point.y)

class POIDatabase:
    """Manages fetching, caching, and accessing Points of Interest (POIs)."""
    def __init__(self):
        self.poi_data: Dict[str, List[Dict]] = {}
        if POI_DATABASE_PATH.exists():
            print("Loading existing POI database...")
            self._load_from_file()
        else:
            print("POI database not found. Generating a new one from OpenStreetMap...")
            self._generate_from_osm()

    def _generate_from_osm(self):
        """Fetches POIs from OSM based on predefined tags and neighborhood areas."""
        try:
            areas_gdf = gpd.read_file(NEIGHBORHOOD_AREAS_GEOJSON_PATH)
        except Exception as e:
            raise SystemExit(f"Error reading GeoJSON '{NEIGHBORHOOD_AREAS_GEOJSON_PATH}': {e}")
        
        special_areas = {'uni': 'campus', 'station': 'station'}
        poi_tags = {
            'home': {'building': ['residential', 'house', 'apartments']},
            'shops': {'shop': True}, 'hospital': {'amenity': ['hospital', 'clinic', 'doctors']},
            'edu': {'amenity': ['school', 'kindergarten', 'college']},
            'restaurant': {'amenity': 'restaurant'}, 'park': {'leisure': ['park', 'playground', 'garden']},
            'sport': {'leisure': ['sports_centre', 'pitch', 'stadium'], 'sport': True}
        }
        self.poi_data = {key: [] for key in list(poi_tags.keys()) + list(special_areas.keys())}

        for _, area_row in areas_gdf.iterrows():
            area_name, geometry = area_row['buurtnaam'], area_row['geometry']
            
            is_special = any(
                self.poi_data[key].append({'name': area_name, 'geometry': geometry}) or True
                for key, name_val in special_areas.items() if area_name == name_val
            )
            
            if not is_special:
                self._fetch_pois_for_geometry(geometry, poi_tags)
        
        self._save_to_file()
        self._print_summary()

    def _fetch_pois_for_geometry(self, geometry: Polygon, poi_tags: Dict):
        """Fetches POIs for a given polygon geometry and appends them to the database."""
        for poi_type, tags in poi_tags.items():
            try:
                pois_gdf = ox.features_from_polygon(geometry, tags)
                if poi_type == 'home' and len(pois_gdf) > 200:
                    pois_gdf = pois_gdf.sample(n=200, random_state=42)
                
                for _, poi_row in pois_gdf.iterrows():
                    centroid = poi_row.geometry.centroid
                    self.poi_data[poi_type].append({'lat': centroid.y, 'lon': centroid.x})
            except Exception:
                continue

    def _load_from_file(self):
        """Loads the POI database from a JSON file."""
        with open(POI_DATABASE_PATH, 'r') as f:
            raw_data = json.load(f)
        for key, poi_list in raw_data.items():
            self.poi_data[key] = []
            for poi_dict in poi_list:
                if 'geometry' in poi_dict and poi_dict['geometry']:
                    poi_dict['geometry'] = Polygon(poi_dict['geometry']['coordinates'][0])
                self.poi_data[key].append(poi_dict)

    def _save_to_file(self):
        """Saves the POI database to a JSON file, serializing Shapely objects."""
        POI_DATABASE_PATH.parent.mkdir(exist_ok=True, parents=True)
        serializable_data = {}
        for key, poi_list in self.poi_data.items():
            serializable_data[key] = [
                {**poi, 'geometry': mapping(poi['geometry'])} if 'geometry' in poi else poi
                for poi in poi_list
            ]
        with open(POI_DATABASE_PATH, 'w') as f:
            json.dump(serializable_data, f, indent=2)

    def _print_summary(self):
        print("\n--- POI Database Generation Summary ---")
        for key, value in sorted(self.poi_data.items()):
            print(f"  -> Found {len(value):>5} POIs for type: '{key}'")
        print("---------------------------------------\n")

    def get_random_poi(self, poi_type: str) -> Dict:
        """Returns a random POI of a given type."""
        return random.choice(self.poi_data[poi_type.strip()])

class WeightManager:
    """Loads and provides access to trip generation weights."""
    def __init__(self):
        try:
            self.poi_weights = pd.read_csv(POI_WEIGHTS_PATH, index_col=0)
            self.poi_weights.columns = self.poi_weights.columns.map(str)
            self.time_weights = pd.read_csv(TIME_WEIGHTS_PATH, index_col='hour')
            print("Successfully loaded POI and time weights.")
        except FileNotFoundError as e:
            raise SystemExit(f"Error: Weight file not found. {e}")

    def get_poi_type_for_hour(self, hour: int) -> str:
        """Returns a POI type based on weighted probabilities for a given hour."""
        weights = self.poi_weights.get(str(hour))
        if weights is None or weights.sum() == 0:
            return random.choice(self.poi_weights.index)
        return random.choices(weights.index, weights=weights.values, k=1)[0]
    
    def get_arrival_rate_for_hour(self, hour: int) -> float:
        """Returns the user arrival rate (users per minute) for a given hour."""
        try:
            return self.time_weights.loc[f"hour_{hour}", 'estimated_trips'] / 60.0
        except KeyError:
            return 0.0

class OpenRouteServiceClient:
    """Client for the OpenRouteService API."""
    def __init__(self):
        self.api_key = st.secrets["ORS_API_KEY"]
        self.client = None
        if self.api_key:
            try:
                import openrouteservice
                self.client = openrouteservice.Client(key=self.api_key)
            except ImportError:
                print("Warning: 'openrouteservice' library not installed. Cannot use ORS.")
            except Exception as e:
                print(f"Warning: Could not initialize ORS client: {e}")

    def get_matrix(self, locations: List[Tuple[float, float]]) -> Optional[Dict]:
        """Gets a time and distance matrix between locations for cycling."""
        if not self.client:
            return None
        try:
            coords = [[lon, lat] for lon, lat in locations]
            return self.client.distance_matrix(
                locations=coords, metrics=['duration', 'distance'], profile='cycling-regular'
            )
        except Exception as e:
            print(f"Error fetching ORS matrix: {e}")
            return None