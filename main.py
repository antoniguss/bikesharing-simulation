# main.py

import simpy
from pathlib import Path
from config import SIMULATION_DURATION, SIMULATION_START_TIME
from simulation_system import BikeShareSystem
from simulation_processes import user_generator
import visualizations

def run_simulation():
    print("=== Bike-Sharing System Simulation ===")
    
    Path('./cache').mkdir(exist_ok=True)
    Path('./generated').mkdir(exist_ok=True)
    
    env = simpy.Environment(initial_time=SIMULATION_START_TIME)
    bike_system = BikeShareSystem()
    
    print(f"System initialized with {len(bike_system.stations)} stations.")
    
    # --- Create the new POI map before the simulation runs ---
    visualizations.create_poi_distribution_map(bike_system)
    
    print("-" * 70)
    print("Starting simulation...")
    
    env.process(user_generator(env, bike_system))
    env.run(until=SIMULATION_START_TIME + SIMULATION_DURATION)

    print("-" * 70)
    print("=== Simulation Results ===")
    stats = bike_system.stats
    total_trips = stats["successful_trips"] + stats["failed_trips"]
    success_rate = (stats["successful_trips"] / total_trips * 100 if total_trips > 0 else 0)

    print(f"Successful trips: {stats['successful_trips']}")
    print(f"Failed trips: {stats['failed_trips']} (Success rate: {success_rate:.1f}%)")

    # Print station usage statistics
    print("\n=== Station Usage Statistics ===")
    sorted_stations = sorted(bike_system.stations, key=lambda s: bike_system.station_usage[s.id], reverse=True)
    print("\nMost Used Stations:")
    for s in sorted_stations[:5]:
        print(f"Station {s.neighbourhood}: {bike_system.station_usage[s.id]} trips")
    
    print("\nStations with Most Failures:")
    sorted_failures = sorted(bike_system.stations, key=lambda s: bike_system.station_failures[s.id], reverse=True)
    for s in sorted_failures[:5]:
        print(f"Station {s.neighbourhood}: {bike_system.station_failures[s.id]} failures")

    if stats["successful_trips"] > 0:
        visualizations.create_trip_path_map(bike_system)
        visualizations.create_results_heatmap(bike_system)
        visualizations.create_hourly_trip_animation_map(bike_system)
        visualizations.create_hourly_station_heatmap(bike_system)
    else:
        print("No successful trips to visualize.")

if __name__ == "__main__":
    run_simulation()