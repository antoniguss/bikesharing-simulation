# utils.py
# Description: Utility functions and classes for data handling and calculations.

import math
import json
import random
import osmnx as ox
import geopandas as gpd
from pathlib import Path
from config import NEIGHBORHOOD_AREAS_GEOJSON_PATH

def get_osmnx_graph(city_query: str, graph_filepath: str):
    graph_path = Path(graph_filepath)
    if graph_path.exists():
        print(f"Loading graph from file: {graph_path}")
        return ox.load_graphml(filepath=graph_path)
    else:
        print(f"Graph file not found. Downloading network for '{city_query}' from OSM.")
        graph = ox.graph_from_place(city_query, network_type='bike')
        print(f"Saving graph to {graph_path} for future use.")
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        ox.save_graphml(graph, filepath=graph_path)
        return graph

def haversine_distance(p1: tuple, p2: tuple) -> float:
    lon1, lat1 = p1
    lon2, lat2 = p2
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return c * 6371

class POIDatabase:
    """
    Handles POI database operations with a flat, unbiased data structure.
    """
    
    def __init__(self, database_path: str):
        self.db_file_path = Path(database_path)
        self.poi_data = {}
        
        if self.db_file_path.exists():
            print("Loading existing POI database...")
            self.load_database(self.db_file_path)
        else:
            print("POI database not found. Generating a new one...")
            self.generate_database()
    
    def generate_database(self):
        """
        Generates a flat POI database by iterating directly over the geometries
        in the areas.geojson file.
        """
        try:
            areas_gdf = gpd.read_file(NEIGHBORHOOD_AREAS_GEOJSON_PATH)
        except Exception as e:
             raise SystemExit(f"Error reading '{NEIGHBORHOOD_AREAS_GEOJSON_PATH}': {e}")

        print(f"Found {len(areas_gdf)} area polygons to process for POIs.")

        self.poi_data = {'houses': [], 'shops': [], 'education': []}
        poi_tags = {
            'houses': {'building': ['residential', 'house', 'apartments']},
            'shops': {'shop': True},
            'education': {'amenity': ['school', 'kindergarten', 'university', 'college']}
        }
        
        print("Fetching POIs for all area geometries...")
        
        # Iterate directly over the rows of the GeoDataFrame
        for index, row in areas_gdf.iterrows():
            neighbourhood_name = row['buurtnaam']  # Get the custom name for context
            geometry = row['geometry']             # Get the geometry directly
            
            print(f"  -> Processing POIs for area '{neighbourhood_name}'")
            self._fetch_and_append_pois(geometry, neighbourhood_name, poi_tags)
    
        self.save_database(self.db_file_path)
        print(f"Successfully generated and saved new POI database.")

    def _fetch_and_append_pois(self, geometry, neighbourhood_name, poi_tags):
        """Fetches POIs for a given area geometry and appends them to the flat lists."""
        for poi_type, tags in poi_tags.items():
            try:
                pois = ox.features_from_polygon(geometry, tags)
                for idx, poi in pois.iterrows():
                    poi_info = {
                        'id': idx,
                        'lat': poi.geometry.centroid.y,
                        'lon': poi.geometry.centroid.x,
                        'neighbourhood': neighbourhood_name,
                        'poi_class': poi_type,
                    }
                    self.poi_data[poi_type].append(poi_info)
            except Exception:
                continue
    
    def load_database(self, path: Path):
        with open(path, 'r') as f:
            self.poi_data = json.load(f)
    
    def save_database(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.poi_data, f, indent=2)
    
    def get_random_poi(self, poi_type: str):
        """
        Selects a random POI from the flat list for the given type.
        """
        if poi_type in self.poi_data and self.poi_data[poi_type]:
            return random.choice(self.poi_data[poi_type])
        return None