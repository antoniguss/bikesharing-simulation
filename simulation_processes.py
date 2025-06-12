# simulation_processes.py
# Description: SimPy processes that define the simulation's dynamic events.

import random
from data_models import User
from simulation_system import BikeShareSystem

def user_journey(env, system: BikeShareSystem, user: User):
    # Find nearest stations
    origin_station = system.find_nearest_station_with_bike(user.origin)
    dest_station = system.find_nearest_station_with_space(user.destination)
    
    if not origin_station or not dest_station or origin_station.id == dest_station.id:
        system.stats["failed_trips"] += 1
        return
        
    # Get journey info
    walk_to_dist, walk_to_time = system.get_walking_info(user.origin, (origin_station.x, origin_station.y))
    walk_from_dist, walk_from_time = system.get_walking_info((dest_station.x, dest_station.y), user.destination)
    cycle_dist, cycle_time, _ = system.get_cycling_info(origin_station.id, dest_station.id)
    
    # User gives up if walking is too far
    walking_threshold = 2.0 # km
    if (walk_to_dist + walk_from_dist) > walking_threshold:
        system.stats["failed_trips"] += 1
        return

    # --- Simulate Journey ---
    yield env.timeout(walk_to_time)
    if not origin_station.has_bike():
        system.stats["failed_trips"] += 1
        return
    origin_station.take_bike()

    yield env.timeout(cycle_time)
    if not dest_station.has_space():
        system.stats["failed_trips"] += 1
        origin_station.return_bike() # Failed, so bike goes back to origin
        return
    dest_station.return_bike()

    yield env.timeout(walk_from_time)
    
    # --- Update Stats and Usage Counters on Success ---
    system.stats["successful_trips"] += 1
    system.stats["total_walking_distance"] += (walk_to_dist + walk_from_dist)
    system.stats["total_cycling_distance"] += cycle_dist
    total_time = walk_to_time + cycle_time + walk_from_time
    system.stats["total_trip_time"] += total_time
    
    # New: Increment usage counters for visualization
    system.station_usage[origin_station.id] += 1
    system.station_usage[dest_station.id] += 1
    system.route_usage[(origin_station.id, dest_station.id)] += 1
    
    print(f"User {user.id}: Journey completed in {total_time:.1f} min.")

def user_generator(env, system: BikeShareSystem, arrival_rate: float):
    while True:
        yield env.timeout(random.expovariate(arrival_rate))
        user = system.generate_user()
        env.process(user_journey(env, system, user))