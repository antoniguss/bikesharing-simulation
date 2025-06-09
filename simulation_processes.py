# simulation_processes.py
# Description: SimPy processes that define the simulation's dynamic events.

import random
from data_models import User
from simulation_system import BikeShareSystem

def user_journey(env, system: BikeShareSystem, user: User):
    origin_station = system.find_nearest_station_with_bike(user.origin)
    dest_station = system.find_nearest_station_with_space(user.destination)
    
    if not origin_station or not dest_station:
        system.stats["failed_trips"] += 1
        return

    walk_to_dist, walk_to_time = system.get_walking_info(user.origin, (origin_station.x, origin_station.y))
    walk_from_dist, walk_from_time = system.get_walking_info((dest_station.x, dest_station.y), user.destination)
    cycle_dist, cycle_time = system.get_cycling_info(origin_station.id, dest_station.id)
    
    if (walk_to_dist + walk_from_dist) > 10.0:
        system.stats["failed_trips"] += 1
        return

    yield env.timeout(walk_to_time)
    if not origin_station.has_bike():
        system.stats["failed_trips"] += 1
        return
    origin_station.take_bike()

    yield env.timeout(cycle_time)
    if not dest_station.has_space():
        system.stats["failed_trips"] += 1
        origin_station.return_bike()
        return
    dest_station.return_bike()

    yield env.timeout(walk_from_time)
    
    total_time = walk_to_time + cycle_time + walk_from_time
    system.stats["successful_trips"] += 1
    system.stats["total_walking_distance"] += (walk_to_dist + walk_from_dist)
    system.stats["total_cycling_distance"] += cycle_dist
    system.stats["total_trip_time"] += total_time

    system.trip_log.append({
        "user_origin": (user.origin[1], user.origin[0]), # (lat, lon) for folium
        "origin_station": (origin_station.y, origin_station.x),
        "dest_station": (dest_station.y, dest_station.x),
        "user_destination": (user.destination[1], user.destination[0]),
    })

    print(f"User {user.id}: Journey completed in {total_time:.1f} min ({user.origin_neighbourhood} -> {user.destination_neighbourhood}).")


def user_generator(env, system: BikeShareSystem, arrival_rate: float):
    while True:
        yield env.timeout(random.expovariate(arrival_rate))
        user = system.generate_user()
        env.process(user_journey(env, system, user))