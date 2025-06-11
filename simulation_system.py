# simulation_system.py
# Description: The core simulation class managing system state and logic.

import random
import openrouteservice
import osmnx as ox
import geopandas as gpd
import threading
from typing import List, Tuple, Optional, Dict

from data_models import Station, User
from utils import POIDatabase, haversine_distance
from config import POI_DATABASE_PATH, NEIGHBOURHOODS_TO_USE, NEIGHBOURHOOD_GEOJSON_PATH, CITY_QUERY

class BikeShareSystem:
    def __init__(self, ors_api_key: str):
        print("--- Initializing Bike Share System ---")
        self.poi_db = POIDatabase(POI_DATABASE_PATH)
        self.stations = self._create_stations_from_geojson()
        self.station_routes = self._precompute_station_routes(ors_api_key)
        self.stats = {
            "successful_trips": 0, "failed_trips": 0, "total_walking_distance": 0.0,
            "total_cycling_distance": 0.0, "total_trip_time": 0
        }
        self.trip_log = []
        self.active_users = {}
        self.lock = threading.Lock() # The lock now belongs to the system
        print("--- System Initialized Successfully ---")

    def _add_active_user(self, user_id, start_coord, end_coord, start_time, end_time, mode):
        """Adds or updates a user's state for live tracking."""
        if end_time > start_time:
            with self.lock:
                self.active_users[user_id] = {
                    "start_coord": start_coord, "end_coord": end_coord,
                    "start_time": start_time, "end_time": end_time, "mode": mode
                }

    def _remove_active_user(self, user_id):
        """Removes a user from tracking once they complete a leg of their journey."""
        with self.lock:
            if user_id in self.active_users:
                del self.active_users[user_id]

    def _create_stations_from_geojson(self) -> List[Station]:
        """
        Creates one station for each neighborhood defined in config.py,
        using the local geojson file as the source for geometries.
        """
        print(f"Creating stations from '{NEIGHBOURHOOD_GEOJSON_PATH}'...")
        
        try:
            buurten_gdf = gpd.read_file(NEIGHBOURHOOD_GEOJSON_PATH)
        except Exception as e:
            raise SystemExit(f"Could not read geojson file: {e}")

        target_gdf = buurten_gdf[buurten_gdf['buurtnaam'].isin(NEIGHBOURHOODS_TO_USE)].copy()
        
        if target_gdf.empty:
            raise SystemExit("Error: Could not find any of the specified neighborhoods in the geojson file. Check names in config.py.")
            
        print(f"Found {len(target_gdf)} of the {len(NEIGHBOURHOODS_TO_USE)} specified neighborhoods.")

        print("Fetching street network graph to place stations on roads...")
        graph = ox.graph_from_place(CITY_QUERY, network_type='bike')

        stations = []
        for index, row in target_gdf.iterrows():
            neighborhood_name = row['buurtnaam']
            centroid = row['geometry'].centroid
            
            nearest_node_id = ox.nearest_nodes(graph, X=centroid.x, Y=centroid.y)
            node_data = graph.nodes[nearest_node_id]
            lon, lat = node_data['x'], node_data['y']
            
            station = Station(
                id=len(stations),
                x=lon, y=lat,
                capacity=random.randint(15, 25),
                bikes=random.randint(8, 15),
                neighbourhood=neighborhood_name
            )
            stations.append(station)
            print(f"  -> Created Station {station.id} for '{neighborhood_name}'")
            
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
        route = self.station_routes[(origin_id, dest_id)]
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
        # Ensure user generation doesn't fail if one of the POI lookups returns None
        if not all([origin_poi, dest_poi]):
             # Simple retry mechanism
             print("Retrying user generation due to missing POI data...")
             return self.generate_user()

        return User(
            id=random.randint(1000, 9999), origin=(origin_poi['lon'], origin_poi['lat']),
            destination=(dest_poi['lon'], dest_poi['lat']), origin_type=origin_type,
            destination_type=dest_type, origin_neighbourhood=origin_hood,
            destination_neighbourhood=dest_hood
        )