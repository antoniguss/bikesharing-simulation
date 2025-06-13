# visualizations.py

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as cx
from shapely.geometry import LineString
from simulation_system import BikeShareSystem

def create_trip_path_map(system: BikeShareSystem):
    """
    Generates a Folium map showing the complete path of every successful trip.
    """
    print("Generating detailed trip path map...")
    if not system.trip_log:
        print("No trips were logged, skipping map generation.")
        return

    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13)

    # Add station markers
    for s in system.stations:
        folium.Marker(
            location=[s.y, s.x],
            icon=folium.Icon(color='green', icon='bicycle', prefix='fa')
        ).add_to(m)

    # Add trip lines
    for trip in system.trip_log:
        # Walking lines (dashed)
        folium.PolyLine(
            locations=[(trip['user_origin'][1], trip['user_origin'][0]), 
                       (trip['origin_station'][1], trip['origin_station'][0])],
            color='blue', weight=2, opacity=0.8, dash_array='5, 5'
        ).add_to(m)
        folium.PolyLine(
            locations=[(trip['dest_station'][1], trip['dest_station'][0]), 
                       (trip['user_destination'][1], trip['user_destination'][0])],
            color='blue', weight=2, opacity=0.8, dash_array='5, 5'
        ).add_to(m)

        # Cycling route (solid)
        if trip.get('route_geometry'):
            gpd.GeoSeries([trip['route_geometry']]).explore(
                m=m, color="red", style_kwds={"weight": 3}
            )

    map_filename = './generated/all_trip_paths.html'
    m.save(map_filename)
    print(f"Detailed trip path map saved to '{map_filename}'")

def create_results_heatmap(system: BikeShareSystem):
    """
    Generates a heatmap of route and station usage.
    """
    print("Generating results heatmap...")
    
    route_geometries = [
        system.station_routes[route]['geometry']
        for route, usage in system.route_usage.items()
        if usage > 0 and system.station_routes.get(route)
        for _ in range(usage)
    ]

    if not route_geometries:
        print("No routes were used, skipping heatmap visualization.")
        return

    routes_gdf = gpd.GeoDataFrame(geometry=route_geometries, crs="EPSG:4326")
    stations_gdf = gpd.GeoDataFrame(
        geometry=[Point(s.x, s.y) for s in system.stations],
        crs="EPSG:4326"
    )
    stations_gdf['usage'] = [system.station_usage.get(s.id, 0) for s in system.stations]

    fig, ax = plt.subplots(figsize=(15, 15))
    routes_gdf.to_crs(epsg=3857).plot(ax=ax, color='crimson', linewidth=0.5, alpha=0.1)
    stations_gdf.to_crs(epsg=3857).plot(
        ax=ax, marker='o', color='skyblue', edgecolor='black',
        markersize=stations_gdf['usage'], alpha=0.9
    )

    cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)
    ax.set_axis_off()
    plt.savefig('./generated/simulation_results_heatmap.png', dpi=300)
    print("Results heatmap saved to './generated/simulation_results_heatmap.png'")