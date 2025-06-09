# utils.py
# Description: Utility functions and classes for data handling and calculations.

import math
import json
import random
import osmnx as ox
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point
from config import NEIGHBOURHOODS_TO_USE, NEIGHBOURHOOD_GEOJSON_PATH

def haversine_distance(p1: tuple, p2: tuple) -> float:
    lon1, lat1 = p1
    lon2, lat2 = p2
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return c * 6371 # Earth radius in kilometers

class POIDatabase:
    """Handles POI database operations by loading from file or generating from OSM."""
    
    def __init__(self, database_path: str):
        self.poi_data = {}
        self.db_file_path = Path(database_path)
        
        if self.db_file_path.exists():
            print("Loading existing POI database...")
            self.load_database(self.db_file_path)
        else:
            print("POI database not found. Generating a new one from OSM data...")
            self.generate_database()
    
    def generate_database(self):
        """Generate POI database using the centralized list of neighborhoods from config."""
        try:
            buurten = gpd.read_file(NEIGHBOURHOOD_GEOJSON_PATH)
            
            self.poi_data = {}
            print("Fetching POIs for neighborhoods defined in config.py. This may take a while...")
            
            for neighbourhood_name in NEIGHBOURHOODS_TO_USE:
                print(f"  -> Processing POIs for: {neighbourhood_name}")
                neighbourhood_gdf = buurten[buurten['buurtnaam'] == neighbourhood_name]
                
                if neighbourhood_gdf.empty:
                    print(f"    - Warning: '{neighbourhood_name}' not found in geojson. Skipping.")
                    continue
                
                geometry = neighbourhood_gdf.geometry.unary_union
                pois = self._fetch_pois_for_neighbourhood(geometry, neighbourhood_name)
                
                # Store each neighborhood as its own "group" for the data structure
                self.poi_data[neighbourhood_name] = {neighbourhood_name: pois}
        
            self.save_database(self.db_file_path)
            print(f"Successfully generated and saved POI database to {self.db_file_path}")

        except FileNotFoundError:
             raise SystemExit(f"Error: '{NEIGHBOURHOOD_GEOJSON_PATH}' not found. Please ensure the file is in the correct location.")
        except Exception as e:
            print(f"An unexpected error occurred while generating POI database: {e}")
            raise SystemExit("Could not generate POI database.")
    
    def _fetch_pois_for_neighbourhood(self, geometry, neighbourhood_name):
        """Fetch POIs for a single neighbourhood geometry."""
        poi_tags = {
            'houses': {'building': ['residential', 'house', 'detached', 'apartments']},
            'parks': {'leisure': ['park', 'playground', 'recreation_ground']},
            'hospitals': {'amenity': ['hospital', 'clinic', 'doctors']},
            'shops': {'shop': True}
        }
        
        neighbourhood_pois = {
            'neighbourhood': neighbourhood_name, 'houses': [], 'parks': [], 'hospitals': [], 'shops': []
        }
        
        for poi_type, tags in poi_tags.items():
            try:
                pois = ox.features_from_polygon(geometry, tags)
                if not pois.empty:
                    for idx, poi in pois.iterrows():
                        lon, lat = self._get_poi_centroid(poi.geometry)
                        poi_info = {
                            'id': f"{neighbourhood_name}_{poi_type}_{idx}",
                            'lat': lat, 'lon': lon,
                            'name': poi.get('name', f"Unnamed {poi_type}"),
                            'type': poi.get('building') or poi.get('shop') or 'unknown'
                        }
                        neighbourhood_pois[poi_type].append(poi_info)
            except Exception:
                continue
        return neighbourhood_pois
    
    def _get_poi_centroid(self, geometry):
        """Get centroid of a geometry, handling Points and Polygons."""
        if geometry.geom_type == 'Point':
            return geometry.x, geometry.y
        return geometry.centroid.x, geometry.centroid.y
    
    def load_database(self, path: Path):
        with open(path, 'r') as f:
            self.poi_data = json.load(f)
    
    def save_database(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.poi_data, f, indent=2)
    
    def get_random_poi(self):
        """Get a random POI from the loaded/generated database."""
        if not self.poi_data: return None, None, None, None
        
        group_name = random.choice(list(self.poi_data.keys()))
        if not self.poi_data[group_name]: return None, None, None, None

        neighbourhood_name = random.choice(list(self.poi_data[group_name].keys()))
        neighbourhood_data = self.poi_data[group_name][neighbourhood_name]
        
        poi_types = ['houses'] * 5 + ['shops'] * 3 + ['parks'] + ['hospitals']
        poi_type = random.choice(poi_types)
        
        if poi_type not in neighbourhood_data or not neighbourhood_data[poi_type]:
            available_types = [t for t, v in neighbourhood_data.items() if isinstance(v, list) and v]
            if not available_types: return None, None, None, None
            poi_type = random.choice(available_types)
        
        poi = random.choice(neighbourhood_data[poi_type])
        return poi, poi_type, neighbourhood_name, group_name