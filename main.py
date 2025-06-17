# main.py

import sys
from io import StringIO
import simpy

import config  # Import the module directly
from simulation_system import BikeShareSystem
from simulation_processes import user_generator
import visualizations

def print_simulation_summary(bike_system: BikeShareSystem):
    """Prints a formatted summary of the simulation results to the console."""
    stats = bike_system.stats
    total_trips = stats["successful_trips"] + stats["failed_trips"]
    success_rate = (stats["successful_trips"] / total_trips * 100) if total_trips > 0 else 0

    print("-" * 70)
    print("=== Simulation Results ===")
    print(f"Successful trips: {stats['successful_trips']}")
    print(f"Failed trips: {stats['failed_trips']}")
    print(f"Success rate: {success_rate:.1f}%")

    print("\n=== Station Usage Statistics ===")
    
    sorted_by_usage = sorted(
        bike_system.stations, 
        key=lambda s: bike_system.station_usage.get(s.id, 0), 
        reverse=True
    )
    print("\nTop 5 Most Used Stations:")
    for station in sorted_by_usage[:5]:
        usage = bike_system.station_usage.get(station.id, 0)
        print(f"- {station.neighbourhood}: {usage} trips")

    sorted_by_failures = sorted(
        bike_system.stations, 
        key=lambda s: bike_system.station_failures.get(s.id, 0), 
        reverse=True
    )
    print("\nTop 5 Stations with Most Failures (no bike/no space):")
    for station in sorted_by_failures[:5]:
        failures = bike_system.station_failures.get(station.id, 0)
        print(f"- {station.neighbourhood}: {failures} failures")
    print("-" * 70)

def run_simulation() -> BikeShareSystem:
    """Sets up and runs the bike-sharing simulation, returning the final system state."""
    old_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output

    print("=== Bike-Sharing System Simulation ===")
    
    config.CACHE_DIR.mkdir(exist_ok=True)
    config.GENERATED_DIR.mkdir(exist_ok=True)
    
    # Use config variables via the module object to get the latest values
    env = simpy.Environment(initial_time=config.SIMULATION_START_TIME)
    bike_system = BikeShareSystem()
    
    visualizations.create_poi_distribution_map(bike_system)
    
    print("\nStarting simulation...")
    print(f"Maximum walking distance: {config.MAX_TOTAL_WALK_DISTANCE_KM:.1f} km")
    
    env.process(user_generator(env, bike_system))
    env.process(bike_system.record_bike_counts_process(env))
    env.run(until=config.SIMULATION_START_TIME + config.SIMULATION_DURATION)
    print("Simulation finished.")

    print_simulation_summary(bike_system)
    
    print("Generating visualizations...")
    if bike_system.stats["successful_trips"] > 0:
        visualizations.create_all_trip_paths_map(bike_system)
        visualizations.create_results_heatmap(bike_system)
        visualizations.create_hourly_trip_animation_map(bike_system)
        visualizations.create_hourly_station_heatmap(bike_system)
    else:
        print("No successful trips to visualize, skipping trip-based maps.")
    
    visualizations.create_station_availability_animation_map(bike_system)
    visualizations.create_hourly_failures_plot(bike_system)
    print("Visualizations created successfully.")

    with open(config.CONSOLE_OUTPUT_PATH, 'w') as f:
        f.write(captured_output.getvalue())
    
    sys.stdout = old_stdout
    return bike_system

if __name__ == "__main__":
    run_simulation()