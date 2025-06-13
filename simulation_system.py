# simulation_system.py

import random
import osmnx as ox
import geopandas as gpd
import networkx as nx
from typing import List, Tuple, Optional, Dict

from data_models import Station, User
from utils import POIDatabase, WeightManager, haversine_distance, get_osmnx_graph, get_random_point_in_polygon
from config import POI_DATABASE_PATH, STATION_GEOJSON_PATH, GRAPH_FILE_PATH, CITY_QUERY

class BikeShareSystem:
    def __init__(self):
        print("--- Initializing Bike Share System ---")
        self.poi_db = POIDatabase(POI_DATABASE_PATH)
        self.weights = WeightManager()
        self.graph = get_osmnx_graph(CITY_QUERY, GRAPH_FILE_PATH)
        self.stations = self._create_stations_from_file()
        self.station_routes = self._precompute_station_routes()
        
        self.stats = {
            "successful_trips": 0, "failed_trips": 0,
            "total_walking_distance": 0.0, "total_cycling_distance": 0.0
        }
        self.trip_log = []
        self.station_usage = {s.id: 0 for s in self.stations}
        self.route_usage = {key: 0 for key in self.station_routes}

    def _create_stations_from_file(self) -> List[Station]:
        print(f"Loading stations from file: '{STATION_GEOJSON_PATH}'...")
        stations_gdf = gpd.read_file(STATION_GEOJSON_PATH)
        stations = []
        for index, row in stations_gdf.iterrows():
            # --- FIX: Use the centroid to get a point for any geometry type ---
            centroid = row.geometry.centroid
            station = Station(
                id=index, x=centroid.x, y=centroid.y,
                capacity=20, bikes=10,
                neighbourhood=row.get('name', f"Station_{index}")
            )
            stations.append(station)
        return stations

    def _precompute_station_routes(self) -> Dict[Tuple[int, int], Dict]:
        print("Precomputing station routes using OSMnx...")
        routes = {}
        for origin in self.stations:
            for dest in self.stations:
                if origin.id == dest.id: continue
                try:
                    o_node = ox.nearest_nodes(self.graph, origin.x, origin.y)
                    d_node = ox.nearest_nodes(self.graph, dest.x, dest.y)
                    path = ox.shortest_path(self.graph, o_node, d_node, weight='length')
                    if not path: continue
                    route_gdf = ox.routing.route_to_gdf(self.graph, path)
                    routes[(origin.id, dest.id)] = {
                        'geometry': route_gdf.unary_union,
                        'distance': route_gdf['length'].sum() / 1000,
                        'duration': (route_gdf['length'].sum() / 1000) / 15 * 60
                    }
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue
        print(f"Successfully precomputed {len(routes)} routes.")
        return routes

    def generate_user(self, current_sim_time: float) -> Optional[User]:
        hour = int((current_sim_time / 60) % 24)
        
        origin_type = self.weights.get_poi_type_for_hour(hour)
        dest_type = self.weights.get_poi_type_for_hour(hour)

        origin_poi = self.poi_db.get_random_poi(origin_type)
        dest_poi = self.poi_db.get_random_poi(dest_type)
        if not origin_poi or not dest_poi or origin_poi == dest_poi:
            return None # Return None if generation fails, to be handled by caller

        origin_coords = get_random_point_in_polygon(origin_poi['geometry']) if 'geometry' in origin_poi else (origin_poi['lon'], origin_poi['lat'])
        dest_coords = get_random_point_in_polygon(dest_poi['geometry']) if 'geometry' in dest_poi else (dest_poi['lon'], dest_poi['lat'])

        return User(
            id=random.randint(1000, 9999),
            origin=origin_coords, destination=dest_coords,
            origin_type=origin_type, destination_type=dest_type
        )

    def get_walking_info(self, start: tuple, end: tuple) -> Tuple[float, float]:
        dist_km = haversine_distance(start, end)
        return dist_km, (dist_km / 5.0) * 60

    def get_cycling_info(self, o_id: int, d_id: int) -> Tuple[float, float, object]:
        route = self.station_routes.get((o_id, d_id))
        return (route['distance'], route['duration'], route['geometry']) if route else (0, 0, None)

    def find_nearest_station_with_bike(self, loc: tuple) -> Optional[Station]:
        available = [s for s in self.stations if s.has_bike()]
        return min(available, key=lambda s: haversine_distance(loc, (s.x, s.y)), default=None)

    def find_nearest_station_with_space(self, loc: tuple) -> Optional[Station]:
        available = [s for s in self.stations if s.has_space()]
        return min(available, key=lambda s: haversine_distance(loc, (s.x, s.y)), default=None)