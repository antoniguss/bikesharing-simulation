# main.py
# Description: Main entry point to run the bike-sharing simulation and visualization.

import simpy
import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as cx
from shapely.geometry import Point
from config import SIMULATION_TIME, USER_ARRIVAL_RATE
from simulation_system import BikeShareSystem
from simulation_processes import user_generator

def create_poi_distribution_map(system: BikeShareSystem):
    """
    Generates a single Folium map with toggleable layers to show the
    distribution of each type of POI (houses, shops, education).
    """
    print("Generating POI distribution map...")

    # Find a central point for the map
    poi_data = system.poi_db.poi_data
    all_lats = [poi['lat'] for poi_type in poi_data.values() for poi in poi_type]
    all_lons = [poi['lon'] for poi_type in poi_data.values() for poi in poi_type]
    
    if not all_lats:
        print("No POI data to visualize.")
        return

    map_center = [sum(all_lats) / len(all_lats), sum(all_lons) / len(all_lons)]
    m = folium.Map(location=map_center, zoom_start=13)

    # Define colors for each POI type
    colors = {
        'houses': 'blue',
        'shops': 'red',
        'education': 'green'
    }

    # Create a feature group for each POI type
    for poi_type, poi_list in poi_data.items():
        feature_group = folium.FeatureGroup(name=poi_type.capitalize())
        
        for poi in poi_list:
            folium.CircleMarker(
                location=[poi['lat'], poi['lon']],
                radius=3,
                color=colors.get(poi_type, 'gray'),
                fill=True,
                fill_color=colors.get(poi_type, 'gray'),
                fill_opacity=0.7
            ).add_to(feature_group)
        
        feature_group.add_to(m)

    # Add the layer control to toggle layers on and off
    folium.LayerControl().add_to(m)
    
    map_filename = './generated/poi_distribution_map.html'
    m.save(map_filename)
    print(f"POI distribution map saved to '{map_filename}'")


def create_results_visualization(system: BikeShareSystem):
    """
    Generates and saves a heatmap-style visualization of simulation results.
    """
    print("Generating results visualization...")
    
    trip_geometries = []
    for route, usage in system.route_usage.items():
        if usage > 0:
            geom = system.station_routes[route]['geometry']
            if geom:
                for _ in range(usage):
                    trip_geometries.append(geom)

    if not trip_geometries:
        print("No routes were used, skipping trip visualization.")
        return

    routes_gdf = gpd.GeoDataFrame(geometry=trip_geometries, crs="EPSG:4326")
    station_geometries = [Point(s.x, s.y) for s in system.stations]
    station_weights = [system.station_usage[s.id] for s in system.stations]
    stations_gdf = gpd.GeoDataFrame(geometry=station_geometries, crs="EPSG:4326")
    stations_gdf['usage'] = station_weights

    fig, ax = plt.subplots(1, 1, figsize=(15, 15))
    routes_gdf_web_mercator = routes_gdf.to_crs(epsg=3857)
    stations_gdf_web_mercator = stations_gdf.to_crs(epsg=3857)
    
    routes_gdf_web_mercator.plot(
        ax=ax, color='crimson', linewidth=0.5, alpha=0.1, zorder=2
    )
    stations_gdf_web_mercator.plot(
        ax=ax, marker='o', color='skyblue', edgecolor='black',
        markersize=stations_gdf_web_mercator['usage'] * 20, alpha=1.0, zorder=3
    )

    cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)
    ax.set_axis_off()
    plt.savefig('./generated/simulation_results_heatmap.png', dpi=300, bbox_inches='tight')
    print("Results heatmap visualization saved to './generated/simulation_results_heatmap.png'")


def run_simulation():
    print("=== Bike-Sharing System Simulation ===")
    
    env = simpy.Environment()
    bike_system = BikeShareSystem()
    
    print(f"System initialized with {len(bike_system.stations)} stations.")
    
    # --- New visualization call for POI distribution ---
    create_poi_distribution_map(bike_system)
    
    print("-" * 70)
    
    env.process(user_generator(env, bike_system, USER_ARRIVAL_RATE))
    env.run(until=SIMULATION_TIME)

    print("-" * 70)
    print("=== Simulation Results ===")
    stats = bike_system.stats
    total_trips = stats["successful_trips"] + stats["failed_trips"]
    success_rate = (stats["successful_trips"] / total_trips * 100 if total_trips > 0 else 0)

    print(f"Successful trips: {stats['successful_trips']}")
    print(f"Failed trips: {stats['failed_trips']} (Success rate: {success_rate:.1f}%)")

    if stats["successful_trips"] > 0:
        create_results_visualization(bike_system)
    else:
        print("No successful trips to visualize.")

if __name__ == "__main__":
    run_simulation()