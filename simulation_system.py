# simulation_system.py

import random
import json
import pickle
import simpy
import osmnx as ox
import geopandas as gpd
import networkx as nx
from typing import Dict, Tuple, Optional, List
import streamlit as st

import config
from data_models import Station, User
from utils import (
    POIDatabase,
    WeightManager,
    haversine_distance,
    get_osmnx_graph,
    get_random_point_in_polygon,
    get_file_md5,
    OpenRouteServiceClient,
)
from config import (
    CITY_QUERY,
    STATION_GEOJSON_PATH,
    GRAPH_FILE_PATH,
    STATION_ROUTES_CACHE_PATH,
    STATION_ROUTES_META_PATH,
    CYCLING_SPEED_KMPH,
    WALKING_SPEED_KMPH,
)


class BikeShareSystem:
    """Manages the state and logic of the entire bike-sharing system."""

    def __init__(self):
        st.info("Initializing Bike Share System...")
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("Loading POI database...")
        self.poi_db = POIDatabase()
        progress_bar.progress(20)

        status_text.text("Loading weights...")
        self.weights = WeightManager()
        progress_bar.progress(40)

        status_text.text("Loading street network...")
        self.graph = get_osmnx_graph(CITY_QUERY, GRAPH_FILE_PATH)
        progress_bar.progress(60)

        status_text.text("Loading stations...")
        self.stations: List[Station] = self._load_stations()
        progress_bar.progress(80)

        status_text.text("Initializing route service...")
        self.ors_client = OpenRouteServiceClient()
        progress_bar.progress(90)

        status_text.text("Computing station routes...")
        self.station_routes = self._precompute_or_load_station_routes()
        progress_bar.progress(100)

        # Simulation statistics
        self.stats = {
            "successful_trips": 0,
            "failed_trips": 0,
            "total_walking_distance": 0.0,
            "total_cycling_distance": 0.0,
        }
        self.trip_log: List[Dict] = []
        self.station_state_log: List[Dict] = []
        self.station_usage: Dict[int, int] = {s.id: 0 for s in self.stations}
        self.station_failures: Dict[int, int] = {s.id: 0 for s in self.stations}
        self.route_usage: Dict[Tuple[int, int], int] = {
            key: 0 for key in self.station_routes
        }
        self.hourly_bike_counts: Dict[int, Dict[int, int]] = {}
        self.hourly_failures: Dict[int, int] = {
            h: 0 for h in range(24)
        }  # Track failures by hour

        self._log_initial_station_states()

        status_text.empty()
        progress_bar.empty()

    def _log_initial_station_states(self):
        """Logs the starting bike count of all stations for live animation."""
        for station in self.stations:
            self.station_state_log.append(
                {
                    "time": config.SIMULATION_START_TIME,
                    "station_id": station.id,
                    "bikes": station.bikes,
                }
            )

    def log_station_state(self, time: float, station_id: int, bikes: int):
        """Records a change in a station's bike count."""
        self.station_state_log.append(
            {"time": time, "station_id": station_id, "bikes": bikes}
        )

    def _load_stations(self) -> List[Station]:
        """Loads station data from the GeoJSON file."""
        stations_gdf = gpd.read_file(STATION_GEOJSON_PATH)
        stations = [
            Station(
                id=index,
                x=row.geometry.centroid.x,
                y=row.geometry.centroid.y,
                capacity=20,  # Default capacity
                bikes=10,  # Default starting bikes
                neighbourhood=row.get("name", f"Station_{index}"),
            )
            for index, row in stations_gdf.iterrows()
        ]
        print(f"Loaded {len(stations)} stations.")
        return stations

    def _is_cache_valid(self) -> bool:
        """Checks if the station routes cache is up-to-date."""
        if not all(
            p.exists() for p in [STATION_ROUTES_CACHE_PATH, STATION_ROUTES_META_PATH]
        ):
            return False

        try:
            with open(STATION_ROUTES_META_PATH, "r") as f:
                meta_data = json.load(f)
            current_hash = get_file_md5(STATION_GEOJSON_PATH)
            return meta_data.get("station_file_hash") == current_hash
        except (json.JSONDecodeError, FileNotFoundError):
            return False

    def _precompute_or_load_station_routes(self) -> Dict[Tuple[int, int], Dict]:
        """Loads station-to-station routes from cache or computes them if necessary."""
        if self._is_cache_valid():
            print("Loading station routes from cache...")
            with open(STATION_ROUTES_CACHE_PATH, "rb") as f:
                return pickle.load(f)

        print("Cache invalid or not found. Precomputing station routes...")
        routes = {}
        station_coords = [(s.x, s.y) for s in self.stations]
        ors_matrix = (
            self.ors_client.get_matrix(station_coords)
            if self.ors_client.client
            else None
        )
        if ors_matrix:
            print("Using OpenRouteService for travel times and distances.")
        else:
            print(
                "ORS client not available or failed. Using OSMnx estimates for travel times."
            )

        for i, origin in enumerate(self.stations):
            for j, dest in enumerate(self.stations):
                if origin.id == dest.id:
                    continue
                try:
                    o_node = ox.nearest_nodes(self.graph, origin.x, origin.y)
                    d_node = ox.nearest_nodes(self.graph, dest.x, dest.y)
                    path_nodes = nx.shortest_path(
                        self.graph, o_node, d_node, weight="length"
                    )

                    if not path_nodes:
                        continue

                    route_gdf = ox.routing.route_to_gdf(self.graph, path_nodes)
                    distance_km = route_gdf["length"].sum() / 1000

                    if ors_matrix:
                        distance_km = ors_matrix["distances"][i][j] / 1000
                        duration_min = ors_matrix["durations"][i][j] / 60
                    else:
                        duration_min = (distance_km / CYCLING_SPEED_KMPH) * 60

                    routes[(origin.id, dest.id)] = {
                        "geometry": route_gdf.unary_union,
                        "distance": distance_km,
                        "duration": duration_min,
                    }
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue

        print(f"Saving {len(routes)} computed routes to cache...")
        with open(STATION_ROUTES_CACHE_PATH, "wb") as f:
            pickle.dump(routes, f)
        with open(STATION_ROUTES_META_PATH, "w") as f:
            json.dump({"station_file_hash": get_file_md5(STATION_GEOJSON_PATH)}, f)

        return routes

    def record_bike_counts_process(self, env: simpy.Environment):
        """A simpy process that records bike counts at each station every hour."""
        while True:
            current_hour = int(env.now / 60)
            self.hourly_bike_counts[current_hour] = {
                station.id: station.bikes for station in self.stations
            }
            yield env.timeout(60)  # Wait for one simulation hour

    def generate_user(self, current_sim_time: float) -> Optional[User]:
        """Generates a new user with an origin and destination based on POI weights."""
        hour = int((current_sim_time / 60) % 24)
        origin_type = self.weights.get_poi_type_for_hour(hour)
        dest_type = self.weights.get_poi_type_for_hour(hour)

        try:
            origin_poi = self.poi_db.get_random_poi(origin_type)
            dest_poi = self.poi_db.get_random_poi(dest_type)
        except (IndexError, KeyError):
            # This can happen if a POI type has no entries in the database
            return None

        origin_coords = (
            get_random_point_in_polygon(origin_poi["geometry"])
            if "geometry" in origin_poi
            else (origin_poi["lon"], origin_poi["lat"])
        )
        dest_coords = (
            get_random_point_in_polygon(dest_poi["geometry"])
            if "geometry" in dest_poi
            else (dest_poi["lon"], dest_poi["lat"])
        )

        return User(
            id=random.randint(10000, 99999),
            origin=origin_coords,
            destination=dest_coords,
            origin_type=origin_type,
            destination_type=dest_type,
        )

    def get_walking_info(
        self, start_coords: tuple, end_coords: tuple
    ) -> Tuple[float, float]:
        """Calculates walking distance (km) and time (minutes)."""
        dist_km = haversine_distance(start_coords, end_coords)
        time_min = (dist_km / WALKING_SPEED_KMPH) * 60
        return dist_km, time_min

    def get_cycling_info(
        self, origin_station_id: int, dest_station_id: int
    ) -> Tuple[float, float, Optional[object]]:
        """Retrieves pre-computed cycling distance, time, and route geometry."""
        route = self.station_routes.get((origin_station_id, dest_station_id))
        return (
            (route["distance"], route["duration"], route["geometry"])
            if route
            else (0, 0, None)
        )

    def find_nearest_station_with_bike(self, location: tuple) -> Optional[Station]:
        """Finds the closest station to a location that has at least one bike."""
        available_stations = [s for s in self.stations if s.has_bike()]
        if not available_stations:
            for station in self.stations:
                if not station.has_bike():
                    self.station_failures[station.id] += 1
            return None
        return min(
            available_stations, key=lambda s: haversine_distance(location, (s.x, s.y))
        )

    def find_nearest_station_with_space(self, location: tuple) -> Optional[Station]:
        """Finds the closest station to a location that has at least one empty dock."""
        available_stations = [s for s in self.stations if s.has_space()]
        if not available_stations:
            for station in self.stations:
                if not station.has_space():
                    self.station_failures[station.id] += 1
            return None
        return min(
            available_stations, key=lambda s: haversine_distance(location, (s.x, s.y))
        )

    def get_stations_needing_rebalancing(
        self, min_threshold: float = 0.3, max_threshold: float = 0.7
    ) -> List[Station]:
        """Returns stations that need rebalancing based on fill ratio thresholds."""
        return [
            station
            for station in self.stations
            if (station.bikes / station.capacity) < min_threshold
            or (station.bikes / station.capacity) > max_threshold
        ]

    def generate_rebalancing_route(
        self, min_threshold: float = 0.3, max_threshold: float = 0.7
    ) -> Optional[Dict]:
        """Generates an optimal rebalancing route using OpenRouteService optimization."""
        if not self.ors_client.client:
            return None

        stations_to_visit = self.get_stations_needing_rebalancing(
            min_threshold, max_threshold
        )
        if not stations_to_visit:
            return None

        try:
            import openrouteservice
            from openrouteservice.optimization import Job, Vehicle

            # Create jobs for each station
            jobs = []
            for station in stations_to_visit:
                jobs.append(
                    Job(
                        id=station.id,
                        location=[station.x, station.y],
                        service=300,  # 5 minutes service time per station
                    )
                )

            # Create a single vehicle starting from the first station
            vehicle = Vehicle(
                id=1,
                profile="driving-car",  # Using car for rebalancing
                start=[stations_to_visit[0].x, stations_to_visit[0].y],
                end=[stations_to_visit[0].x, stations_to_visit[0].y],  # Return to start
            )

            # Get the optimization result
            result = self.ors_client.client.optimization(
                jobs=jobs, vehicles=[vehicle], geometry=True
            )

            return {"route": result, "stations": stations_to_visit}

        except Exception as e:
            print(f"Error generating rebalancing route:")
            print(e)
            return None

