# simulation_processes.py
import random
from simpy import Environment

import config
from data_models import User
from simulation_system import BikeShareSystem

def handle_user_trip(env: Environment, bike_system: BikeShareSystem, user: User):
    """Simulates a single user's journey from origin to destination."""
    
    # 1. Find nearest available stations
    origin_station = bike_system.find_nearest_station_with_bike(user.origin)
    if not origin_station:
        bike_system.stats["failed_trips"] += 1
        bike_system.hourly_failures[int(env.now / 60) % 24] += 1
        return

    dest_station = bike_system.find_nearest_station_with_space(user.destination)
    if not dest_station:
        bike_system.stats["failed_trips"] += 1
        bike_system.hourly_failures[int(env.now / 60) % 24] += 1
        return

    # 2. Calculate trip segments and check constraints
    walk_to_dist, walk_to_time = bike_system.get_walking_info(user.origin, (origin_station.x, origin_station.y))
    walk_from_dist, walk_from_time = bike_system.get_walking_info((dest_station.x, dest_station.y), user.destination)
    
    if (walk_to_dist + walk_from_dist) > config.MAX_TOTAL_WALK_DISTANCE_KM:
        bike_system.stats["failed_trips"] += 1
        bike_system.hourly_failures[int(env.now / 60) % 24] += 1
        return
        
    cycle_dist, cycle_time, route_geometry = bike_system.get_cycling_info(origin_station.id, dest_station.id)

    # 3. Simulate the journey process
    # The `take_bike` and `return_bike` methods should succeed here because the `find_nearest...`
    # functions already filtered for availability. This is for correctness and future-proofing.
    if not origin_station.take_bike():
        bike_system.stats["failed_trips"] += 1
        bike_system.station_failures[origin_station.id] += 1
        return

    yield env.timeout(walk_to_time)
    yield env.timeout(cycle_time)
    
    if not dest_station.return_bike():
        # This case implies the station filled up. The trip fails at the last step.
        # We roll back the bike take to maintain bike count integrity in the simulation.
        origin_station.return_bike()
        bike_system.stats["failed_trips"] += 1
        bike_system.station_failures[dest_station.id] += 1
        return

    yield env.timeout(walk_from_time)

    # 4. Log the successful trip
    bike_system.stats["successful_trips"] += 1
    bike_system.stats["total_walking_distance"] += walk_to_dist + walk_from_dist
    bike_system.stats["total_cycling_distance"] += cycle_dist
    bike_system.station_usage[origin_station.id] += 1
    bike_system.station_usage[dest_station.id] += 1
    if (origin_station.id, dest_station.id) in bike_system.route_usage:
        bike_system.route_usage[(origin_station.id, dest_station.id)] += 1

    bike_system.trip_log.append({
        'user_origin': user.origin,
        'user_destination': user.destination,
        'origin_station': (origin_station.x, origin_station.y),
        'dest_station': (dest_station.x, dest_station.y),
        'start_time': env.now, # Used for hourly grouping of animation
        'route_geometry': route_geometry
    })

def user_generator(env: Environment, bike_system: BikeShareSystem):
    """Generates users based on a variable arrival rate throughout the simulation."""
    while True:
        current_hour = int((env.now / 60) % 24)
        arrival_rate_per_min = bike_system.weights.get_arrival_rate_for_hour(current_hour)

        if arrival_rate_per_min > 0:
            time_to_next_user = random.expovariate(arrival_rate_per_min)
            yield env.timeout(time_to_next_user)
            
            user = bike_system.generate_user(env.now)
            if user:
                env.process(handle_user_trip(env, bike_system, user))
        else:
            # If no users are expected this hour, wait until the next one begins.
            time_to_next_hour = 60 - (env.now % 60)
            yield env.timeout(time_to_next_hour or 60)