# simulation_processes.py

import random
import config
from data_models import User
from simulation_system import BikeShareSystem

def handle_user_trip(env, system, user):
    # Find nearest station with bike
    origin_station = system.find_nearest_station_with_bike(user.origin)
    if not origin_station:
        system.stats["failed_trips"] += 1
        return

    # Find nearest station with space
    dest_station = system.find_nearest_station_with_space(user.destination)
    if not dest_station:
        system.stats["failed_trips"] += 1
        return

    # Calculate walking times
    walk_to_dist, walk_to_time = system.get_walking_info(user.origin, (origin_station.x, origin_station.y))
    walk_from_dist, walk_from_time = system.get_walking_info((dest_station.x, dest_station.y), user.destination)

    # Get cycling info
    cycle_dist, cycle_time, route_geometry = system.get_cycling_info(origin_station.id, dest_station.id)

    # Check if total walking distance is acceptable
    if walk_to_dist + walk_from_dist > config.MAX_TOTAL_WALK_DISTANCE_KM:
        system.stats["failed_trips"] += 1
        return

    # Take bike from origin station
    origin_station.bikes -= 1

    # Walk to station
    yield env.timeout(walk_to_time)

    # Cycle to destination station
    yield env.timeout(cycle_time)

    # Return bike to destination station
    dest_station.bikes += 1

    # Walk to final destination
    yield env.timeout(walk_from_time)

    # Update statistics
    system.stats["successful_trips"] += 1
    system.stats["total_walking_distance"] += walk_to_dist + walk_from_dist
    system.stats["total_cycling_distance"] += cycle_dist
    system.station_usage[origin_station.id] += 1
    system.station_usage[dest_station.id] += 1

    # Log the trip
    system.trip_log.append({
        'user_origin': user.origin,
        'user_destination': user.destination,
        'origin_station': (origin_station.x, origin_station.y),
        'dest_station': (dest_station.x, dest_station.y),
        'start_time': env.now,
        'route_geometry': route_geometry
    })

def user_generator(env, system: BikeShareSystem):
    """Generates users with a variable arrival rate based on the time of day."""
    # print("[DEBUG: user_generator started]")
    loop_count = 0
    while True:
        loop_count += 1
        current_hour = int((env.now / 60) % 24)
        arrival_rate = system.weights.get_arrival_rate_for_hour(current_hour)
        
        # --- DEBUG LOG ---
        # print(f"[: Loop {loop_count}, Sim Time: {env.now:.2f} min, Hour: {current_hour}, Arrival Rate: {arrival_rate:.4f} users/min]")
        
        if arrival_rate > 0:
            time_to_next_user = random.expovariate(arrival_rate)
            # --- DEBUG LOG ---
            # print(f"  -> Next user in {time_to_next_user:.2f} minutes.")
            
            yield env.timeout(time_to_next_user)
            
            # print(f"[DEBUG: Time is now {env.now:.2f}. Attempting to generate user.]")
            user = system.generate_user(env.now)
            if user:
                # print(f"  -> SUCCESS: User {user.id} created. Starting journey.")
                env.process(handle_user_trip(env, system, user))
            else:
                pass
                # print("  -> FAILED: system.generate_user() returned None.")
        else:
            wait_time = 60 - (env.now % 60)
            # --- DEBUG LOG ---
            print(f"  -> Zero arrival rate. Waiting {wait_time:.2f} minutes until the next hour.")
            yield env.timeout(wait_time)
        
        # Safety break to prevent infinite loops during debugging if time doesn't advance
        if loop_count > 5000:
            # print("[DEBUG: Safety break triggered. Too many loops.]")
            break
