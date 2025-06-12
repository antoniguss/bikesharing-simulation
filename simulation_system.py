# simulation_system.py
# Description: The core simulation class managing system state and logic.

import random
import osmnx as ox
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString
from typing import List, Tuple, Optional, Dict

from data_models import Station, User
from utils import POIDatabase, haversine_distance, get_osmnx_graph
from config import POI_DATABASE_PATH, STATION_GEOJSON_PATH, GRAPH_FILE_PATH, CITY_QUERY

class BikeShareSystem:
    def __init__(self):
        print("--- Initializing Bike Share System ---")
        self.poi_db = POIDatabase(POI_DATABASE_PATH)
        self.graph = get_osmnx_graph(CITY_QUERY, GRAPH_FILE_PATH)
        self.stations = self._create_stations_from_file()
        self.station_routes = self._precompute_station_routes()
        
        self.stats = {
            "successful_trips": 0, "failed_trips": 0, "total_walking_distance": 0.0,
            "total_cycling_distance": 0.0, "total_trip_time": 0
        }
        self.trip_log = []
        self.station_usage = {s.id: 0 for s in self.stations}
        self.route_usage = {key: 0 for key in self.station_routes.keys()}

    def _create_stations_from_file(self) -> List[Station]:
        print(f"Loading stations from file: '{STATION_GEOJSON_PATH}'...")
        all_features_gdf = gpd.read_file(STATION_GEOJSON_PATH)
        stations_gdf = all_features_gdf[all_features_gdf.geom_type == 'Point'].copy()
        print(f"Found {len(stations_gdf)} Point features to use as stations.")
        stations = []
        for index, row in stations_gdf.iterrows():
            station = Station(
                id=len(stations),
                x=row.geometry.x, y=row.geometry.y,
                capacity=20, bikes=10,
                neighbourhood=row.get('name', f"Station_{index}")
            )
            stations.append(station)
        return stations

    def _precompute_station_routes(self) -> Dict[Tuple[int, int], Dict]:
        print("Precomputing station routes using OSMnx. This may take a moment...")
        routes = {}
        for origin_station in self.stations:
            for dest_station in self.stations:
                if origin_station.id == dest_station.id:
                    continue
                
                origin_node = ox.nearest_nodes(self.graph, X=origin_station.x, Y=origin_station.y)
                dest_node = ox.nearest_nodes(self.graph, X=dest_station.x, Y=dest_station.y)
                
                try:
                    path_nodes = ox.shortest_path(self.graph, origin_node, dest_node, weight='length')
                    if not path_nodes: continue

                    route_gdf = ox.routing.route_to_gdf(self.graph, path_nodes, weight='length')
                    distance_m = route_gdf['length'].sum()
                    geometry = route_gdf.unary_union
                    duration_min = (distance_m / 1000) / 15 * 60

                    routes[(origin_station.id, dest_station.id)] = {
                        'geometry': geometry,
                        'distance': distance_m / 1000,
                        'duration': duration_min
                    }
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue
        
        print(f"Successfully precomputed {len(routes)} routes.")
        return routes

    def get_walking_info(self, start: tuple, end: tuple) -> Tuple[float, float]:
        distance_km = haversine_distance(start, end)
        return distance_km, (distance_km / 5.0) * 60

    def get_cycling_info(self, origin_id: int, dest_id: int) -> Tuple[float, float, object]:
        if origin_id == dest_id: return 0.0, 0.0, None
        route = self.station_routes.get((origin_id, dest_id))
        return (route['distance'], route['duration'], route['geometry']) if route else (0.0, 0.0, None)

    def find_nearest_station_with_bike(self, loc: tuple) -> Optional[Station]:
        available = [s for s in self.stations if s.has_bike()]
        return min(available, key=lambda s: haversine_distance(loc, (s.x, s.y))) if available else None

    def find_nearest_station_with_space(self, loc: tuple) -> Optional[Station]:
        available = [s for s in self.stations if s.has_space()]
        return min(available, key=lambda s: haversine_distance(loc, (s.x, s.y))) if available else None

    def generate_user(self) -> User:
        """
        Generates a user by first selecting a realistic trip pattern,
        then fetching unbiased POIs of the required types.
        """
        # Define realistic trip patterns with weights.
        # (origin_type, destination_type)
        trip_patterns = [
            ('houses', 'shops'),      # Home to shop
            ('shops', 'houses'),      # Shop to home
            ('houses', 'education'),  # Home to school/uni
            ('education', 'houses'),  # School/uni to home
            ('houses', 'houses'),     # Visiting friends/family
        ]
        origin_type, dest_type = random.choice(trip_patterns)
        origin_poi = self.poi_db.get_random_poi(origin_type)
        dest_poi = self.poi_db.get_random_poi(dest_type)

        # If POI generation fails (e.g., empty list), retry.
        if not origin_poi or not dest_poi or origin_poi['id'] == dest_poi['id']:
            return self.generate_user()

        return User(
            id=random.randint(1000, 9999),
            origin=(origin_poi['lon'], origin_poi['lat']),
            destination=(dest_poi['lon'], dest_poi['lat']),
            origin_type=origin_type,
            destination_type=dest_type,
            origin_neighbourhood=origin_poi['neighbourhood'],
            destination_neighbourhood=dest_poi['neighbourhood']
        )