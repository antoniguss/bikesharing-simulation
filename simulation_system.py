# simulation_system.py
# Description: The core simulation class managing system state and logic.

import random
import openrouteservice
import geopandas as gpd
from typing import List, Tuple, Optional, Dict

from data_models import Station, User
from utils import POIDatabase, haversine_distance
from config import POI_DATABASE_PATH, STATION_GEOJSON_PATH

class BikeShareSystem:
    def __init__(self, ors_api_key: str):
        print("--- Initializing Bike Share System ---")
        self.poi_db = POIDatabase(POI_DATABASE_PATH)
        self.stations = self._create_stations_from_file()
        self.station_routes = self._precompute_station_routes(ors_api_key)
        self.stats = {
            "successful_trips": 0, "failed_trips": 0, "total_walking_distance": 0.0,
            "total_cycling_distance": 0.0, "total_trip_time": 0
        }
        self.trip_log = []
        print("--- System Initialized Successfully ---")

    def _create_stations_from_file(self) -> List[Station]:
        """
        Creates stations from a predefined GeoJSON file, ensuring only
        Point geometries are processed.
        """
        print(f"Loading stations from file: '{STATION_GEOJSON_PATH}'...")
        
        try:
            all_features_gdf = gpd.read_file(STATION_GEOJSON_PATH)
        except Exception as e:
            raise SystemExit(f"Could not read station geojson file: {e}")

        # --- THIS IS THE FIX ---
        # Filter for only Point geometries, ignoring any Polygons in the file.
        stations_gdf = all_features_gdf[all_features_gdf.geom_type == 'Point'].copy()
        
        print(f"Found {len(stations_gdf)} Point features to use as stations.")

        stations = []
        for index, row in stations_gdf.iterrows():
            # Extract coordinates from the point geometry
            lon, lat = row.geometry.x, row.geometry.y
            
            # Use the 'name' property from the file (e.g., "A1", "C")
            station_name = row.get('name', f"Station_{index}")

            station = Station(
                id=len(stations),
                x=lon, y=lat,
                capacity=20, # Default capacity
                bikes=10,    # Default number of bikes
                neighbourhood=station_name # Using the feature's name as an identifier
            )
            stations.append(station)
        
        if not stations:
            raise SystemExit("Error: Station file was read, but no Point features were found. Check file content.")
            
        return stations

    def _precompute_station_routes(self, api_key: str) -> Dict[Tuple[int, int], Dict[str, float]]:
        print("Precomputing station routes using ORS distance matrix...")
        client = openrouteservice.Client(key=api_key)
        coords = [[s.x, s.y] for s in self.stations]
        try:
            matrix = client.distance_matrix(
                locations=coords, profile='cycling-regular', metrics=['duration', 'distance']
            )
        except openrouteservice.exceptions.ApiError as e:
            raise SystemExit(f"ORS API Error: {e}. Cannot precompute routes. Check API key.")
        
        routes = {}
        durations_min = [[s / 60.0 for s in row] for row in matrix['durations']]
        distances_km = [[m / 1000.0 for m in row] for row in matrix['distances']]
        for i, origin in enumerate(self.stations):
            for j, dest in enumerate(self.stations):
                if i == j: continue
                routes[(origin.id, dest.id)] = {
                    'duration': durations_min[i][j], 'distance': distances_km[i][j]
                }
        print(f"Precomputed {len(routes)} station-to-station routes with 1 API call.")
        return routes

    def get_walking_info(self, start: tuple, end: tuple) -> Tuple[float, float]:
        distance_km = haversine_distance(start, end)
        return distance_km, (distance_km / 5.0) * 60

    def get_cycling_info(self, origin_id: int, dest_id: int) -> Tuple[float, float]:
        if origin_id == dest_id: return 0.0, 0.0
        route = self.station_routes.get((origin_id, dest_id))
        if route is None: return 0.0, 0.0
        return route['distance'], route['duration']

    def find_nearest_station_with_bike(self, loc: tuple) -> Optional[Station]:
        available = [s for s in self.stations if s.has_bike()]
        return min(available, key=lambda s: haversine_distance(loc, (s.x, s.y))) if available else None

    def find_nearest_station_with_space(self, loc: tuple) -> Optional[Station]:
        available = [s for s in self.stations if s.has_space()]
        return min(available, key=lambda s: haversine_distance(loc, (s.x, s.y))) if available else None

    def generate_user(self) -> User:
        origin_poi, origin_type, origin_hood, _ = self.poi_db.get_random_poi()
        dest_poi, dest_type, dest_hood, _ = self.poi_db.get_random_poi()
        if not all([origin_poi, dest_poi]):
             print("Retrying user generation due to missing POI data...")
             return self.generate_user()

        return User(
            id=random.randint(1000, 9999), origin=(origin_poi['lon'], origin_poi['lat']),
            destination=(dest_poi['lon'], dest_poi['lat']), origin_type=origin_type,
            destination_type=dest_type, origin_neighbourhood=origin_hood,
            destination_neighbourhood=dest_hood
        )