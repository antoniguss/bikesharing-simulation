# main.py
# Description: Main entry point to run the bike-sharing simulation.

import simpy
import folium
from config import ORS_API_KEY, SIMULATION_TIME, USER_ARRIVAL_RATE
from simulation_system import BikeShareSystem
from simulation_processes import user_generator

def create_trip_map(stations, trip_log):
    """Generates a folium map visualizing all trips."""
    
    # Calculate map center
    avg_lat = sum(s.y for s in stations) / len(stations)
    avg_lon = sum(s.x for s in stations) / len(stations)
    
    # Create base map
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=14)

    # 1. Add station markers
    for s in stations:
        folium.Marker(
            location=[s.y, s.x],
            popup=f"Station {s.id}<br>Hood: {s.neighbourhood}<br>Capacity: {s.capacity}",
            icon=folium.Icon(color='darkblue', icon='bicycle', prefix='fa')
        ).add_to(m)

    # 2. Add trip lines
    for trip in trip_log:
        # Walking to station (dashed blue line)
        folium.PolyLine(
            locations=[trip['user_origin'], trip['origin_station']],
            color='blue', weight=2.5, opacity=0.8, dash_array='5, 5'
        ).add_to(m)
        
        # Cycling between stations (solid red line)
        folium.PolyLine(
            locations=[trip['origin_station'], trip['dest_station']],
            color='red', weight=4, opacity=0.7
        ).add_to(m)

        # Walking from station (dashed blue line)
        folium.PolyLine(
            locations=[trip['dest_station'], trip['user_destination']],
            color='blue', weight=2.5, opacity=0.8, dash_array='5, 5'
        ).add_to(m)
        
        # Mark user's actual start and end points
        folium.CircleMarker(location=trip['user_origin'], radius=4, color='green', fill=True, fill_color='green').add_to(m)
        folium.CircleMarker(location=trip['user_destination'], radius=4, color='purple', fill=True, fill_color='purple').add_to(m)

    return m


def run_simulation():
    print("=== Bike-Sharing System Simulation ===")
    
    env = simpy.Environment()
    bike_system = BikeShareSystem(ors_api_key=ORS_API_KEY)
    
    total_bikes = sum(s.bikes for s in bike_system.stations)
    total_capacity = sum(s.capacity for s in bike_system.stations)
    print(f"System initialized: {len(bike_system.stations)} stations, {total_bikes}/{total_capacity} bikes")
    print("-" * 70)
    
    env.process(user_generator(env, bike_system, USER_ARRIVAL_RATE))
    env.run(until=SIMULATION_TIME)

    print("-" * 70)
    print("=== Simulation Results ===")
    stats = bike_system.stats
    total_trips = stats["successful_trips"] + stats["failed_trips"]
    success_rate = (stats["successful_trips"] / total_trips * 100 if total_trips > 0 else 0)

    print(f"Total trip attempts: {total_trips}")
    print(f"Successful trips: {stats['successful_trips']}")
    print(f"Failed trips: {stats['failed_trips']}")
    print(f"Success rate: {success_rate:.1f}%")

    if stats["successful_trips"] > 0:
        avg_walk = stats["total_walking_distance"] / stats["successful_trips"]
        avg_cycle = stats["total_cycling_distance"] / stats["successful_trips"]
        avg_time = stats["total_trip_time"] / stats["successful_trips"]
        print(f"Average walking distance per trip: {avg_walk:.2f} km")
        print(f"Average cycling distance per trip: {avg_cycle:.2f} km")
        print(f"Average total trip time: {avg_time:.1f} minutes")

    print("\n=== Final Station States ===")
    for station in bike_system.stations:
        print(f"Station {station.id} ({station.neighbourhood}): {station.bikes}/{station.capacity} bikes")

    if bike_system.trip_log:
        print("\nGenerating trip visualization map...")
        trip_map = create_trip_map(bike_system.stations, bike_system.trip_log)
        map_file = "trip_map.html"
        trip_map.save(map_file)
        print(f"Map saved to '{map_file}'. Open this file in your browser to view the trips.")
    else:
        print("\nNo successful trips were logged to generate a map.")

if __name__ == "__main__":
    run_simulation()