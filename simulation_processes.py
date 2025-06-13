# simulation_processes.py

import random
from data_models import User
from simulation_system import BikeShareSystem

def user_journey(env, system: BikeShareSystem, user: User):
    origin_station = system.find_nearest_station_with_bike(user.origin)
    dest_station = system.find_nearest_station_with_space(user.destination)
    
    if not origin_station or not dest_station or origin_station.id == dest_station.id:
        system.stats["failed_trips"] += 1
        return
        
    walk_to_dist, walk_to_time = system.get_walking_info(user.origin, (origin_station.x, origin_station.y))
    walk_from_dist, walk_from_time = system.get_walking_info((dest_station.x, dest_station.y), user.destination)
    cycle_dist, cycle_time, route_geom = system.get_cycling_info(origin_station.id, dest_station.id)
    
    if (walk_to_dist + walk_from_dist) > 2.0:
        system.stats["failed_trips"] += 1
        return

    yield env.timeout(walk_to_time)
    if not origin_station.take_bike():
        system.stats["failed_trips"] += 1
        return

    yield env.timeout(cycle_time)
    if not dest_station.return_bike():
        system.stats["failed_trips"] += 1
        origin_station.return_bike()
        return

    yield env.timeout(walk_from_time)
    
    system.stats["successful_trips"] += 1
    system.stats["total_walking_distance"] += (walk_to_dist + walk_from_dist)
    system.stats["total_cycling_distance"] += cycle_dist
    
    system.station_usage[origin_station.id] += 1
    system.station_usage[dest_station.id] += 1
    system.route_usage[(origin_station.id, dest_station.id)] += 1

    # Log trip details for detailed visualization
    system.trip_log.append({
        'user_origin': user.origin, 'origin_station': (origin_station.x, origin_station.y),
        'dest_station': (dest_station.x, dest_station.y), 'user_destination': user.destination,
        'route_geometry': route_geom
    })

def user_generator(env, system: BikeShareSystem):
    """Generates users with a variable arrival rate based on the time of day."""
    while True:
        current_hour = int((env.now / 60) % 24)
        arrival_rate = system.weights.get_arrival_rate_for_hour(current_hour)
        
        if arrival_rate > 0:
            # The time until the next user arrives is determined by an exponential distribution
            # with the mean arrival rate for the current hour.
            time_to_next_user = random.expovariate(arrival_rate)
            yield env.timeout(time_to_next_user)
            
            user = system.generate_user(env.now)
            if user:
                env.process(user_journey(env, system, user))
        else:
            # If rate is zero, wait until the next hour starts
            yield env.timeout(60 - (env.now % 60))