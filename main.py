# main.py

import simpy
from pathlib import Path
from config import SIMULATION_TIME
from simulation_system import BikeShareSystem
from simulation_processes import user_generator
from visualizations import create_trip_path_map, create_results_heatmap

def run_simulation():
    print("=== Bike-Sharing System Simulation ===")
    
    # Ensure the output directory exists
    Path('./generated').mkdir(exist_ok=True)
    
    env = simpy.Environment()
    bike_system = BikeShareSystem()
    
    print(f"System initialized with {len(bike_system.stations)} stations.")
    print("-" * 70)
    
    env.process(user_generator(env, bike_system))
    env.run(until=SIMULATION_TIME)

    print("-" * 70)
    print("=== Simulation Results ===")
    stats = bike_system.stats
    total_trips = stats["successful_trips"] + stats["failed_trips"]
    success_rate = (stats["successful_trips"] / total_trips * 100 if total_trips > 0 else 0)

    print(f"Successful trips: {stats['successful_trips']}")
    print(f"Failed trips: {stats['failed_trips']} (Success rate: {success_rate:.1f}%)")

    if stats["successful_trips"] > 0:
        create_trip_path_map(bike_system)
        create_results_heatmap(bike_system)
    else:
        print("No successful trips to visualize.")

if __name__ == "__main__":
    run_simulation()