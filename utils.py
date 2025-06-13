# utils.py

import math
import json
import random
import osmnx as ox
import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely.geometry import Polygon, Point
from config import NEIGHBORHOOD_AREAS_GEOJSON_PATH, POI_WEIGHTS_PATH, TIME_WEIGHTS_PATH

def get_osmnx_graph(city_query: str, graph_filepath: str):
    graph_path = Path(graph_filepath)
    if graph_path.exists():
        print(f"Loading graph from file: {graph_path}")
        return ox.load_graphml(filepath=graph_path)
    else:
        print(f"Graph file not found. Downloading network for '{city_query}'.")
        graph = ox.graph_from_place(city_query, network_type='bike')
        print(f"Saving graph to {graph_path} for future use.")
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        ox.save_graphml(graph, filepath=graph_path)
        return graph

def haversine_distance(p1: tuple, p2: tuple) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, [p1[0], p1[1], p2[0], p2[1]])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 6371 * (2 * math.asin(math.sqrt(a)))

def get_random_point_in_polygon(polygon: Polygon) -> tuple:
    """Generates a random longitude/latitude point within a given Shapely Polygon."""
    min_x, min_y, max_x, max_y = polygon.bounds
    while True:
        point = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))
        if polygon.contains(point):
            return (point.x, point.y)

class POIDatabase:
    def __init__(self, database_path: str):
        self.db_file_path = Path(database_path)
        self.poi_data = {}
        
        if self.db_file_path.exists():
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

        # Define which names from the geojson are special large areas
        special_areas = {
            'uni': 'campus',
            'station_area': 'Station' 
        }
        
        # Define tags for standard POI queries
        poi_tags = {
            'home': {'building': ['residential', 'house', 'apartments']},
            'shops': {'shop': True},
            'hospital': {'amenity': ['hospital', 'clinic', 'doctors']},
            'edu': {'amenity': ['school', 'kindergarten', 'college']},
            'restaurant': {'amenity': 'restaurant'},
            'park': {'leisure': ['park', 'playground', 'garden']},
            'sport': {'leisure': ['sports_centre', 'pitch', 'stadium'], 'sport': True}
        }

        self.poi_data = {key: [] for key in poi_tags}
        self.poi_data.update({key: [] for key in special_areas})

        for _, row in areas_gdf.iterrows():
            area_name = row['buurtnaam']
            geometry = row['geometry']
            
            is_special = False
            for key, val in special_areas.items():
                if area_name == val:
                    print(f"  -> Storing special area polygon: '{area_name}' as '{key}'")
                    self.poi_data[key].append({'name': area_name, 'geometry': geometry})
                    is_special = True
                    break
            
            if not is_special:
                print(f"  -> Querying standard POIs within: '{area_name}'")
                self._fetch_and_append_pois(geometry, poi_tags)
        
        self.save_database()
        print("Successfully generated and saved new POI database.")

    def _fetch_and_append_pois(self, geometry, poi_tags):
        for poi_type, tags in poi_tags.items():
            try:
                pois = ox.features_from_polygon(geometry, tags)
                
                # Apply sampling for 'home' POIs to keep the list manageable
                if poi_type == 'home' and len(pois) > 200:
                    pois = pois.sample(n=200)

                for _, poi in pois.iterrows():
                    self.poi_data[poi_type].append({
                        'lat': poi.geometry.centroid.y,
                        'lon': poi.geometry.centroid.x,
                    })
            except Exception:
                continue
    
    def load_database(self):
        with open(self.db_file_path, 'r') as f:
            # For polygons, we need to convert them back from a list representation
            raw_data = json.load(f)
            for key, poi_list in raw_data.items():
                for poi in poi_list:
                    if 'geometry' in poi:
                        poi['geometry'] = Polygon(poi['geometry']['coordinates'][0])
            self.poi_data = raw_data
    
    def save_database(self):
        # Create a serializable copy of the data
        serializable_data = {}
        for key, poi_list in self.poi_data.items():
            serializable_data[key] = []
            for poi in poi_list:
                if 'geometry' in poi:
                    # Convert Shapely Polygon to a GeoJSON-like dict
                    serializable_data[key].append({
                        'name': poi['name'],
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [list(poi['geometry'].exterior.coords)]
                        }
                    })
                else:
                    serializable_data[key].append(poi)

        self.db_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_file_path, 'w') as f:
            json.dump(serializable_data, f, indent=2)

    def get_random_poi(self, poi_type: str):
        if poi_type in self.poi_data and self.poi_data[poi_type]:
            return random.choice(self.poi_data[poi_type])
        return None

class WeightManager:
    """Loads and provides access to trip generation weights."""
    def __init__(self):
        try:
            self.poi_weights = pd.read_csv(POI_WEIGHTS_PATH, index_col=0)
            self.time_weights = pd.read_csv(TIME_WEIGHTS_PATH, index_col='hour')
            # Normalize poi_weights columns so they sum to 1, making them probabilities
            self.poi_weights = self.poi_weights.div(self.poi_weights.sum(axis=0), axis=1).fillna(0)
            print("Successfully loaded POI and time weights.")
        except FileNotFoundError as e:
            raise SystemExit(f"Error: Weight file not found. {e}")

    def get_poi_type_for_hour(self, hour: int) -> str:
        """Returns a POI type based on weighted probabilities for a given hour."""
        hour_str = str(hour)
        if hour_str not in self.poi_weights.columns:
            return random.choice(self.poi_weights.index) # Fallback for hours with no data
        
        weights = self.poi_weights[hour_str]
        return random.choices(weights.index, weights=weights.values, k=1)[0]
    
    def get_arrival_rate_for_hour(self, hour: int) -> float:
        """Returns the user arrival rate per minute for a given hour."""
        key = f"hour_{hour}"
        if key in self.time_weights.index:
            # Convert hourly trips to per-minute rate
            return self.time_weights.loc[key, 'estimated_trips'] / 60
        return 0.01 # Default low arrival rate if hour is missing