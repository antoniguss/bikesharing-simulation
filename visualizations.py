# visualizations.py

import folium
import folium.plugins
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as cx
from shapely.geometry import Point, LineString, MultiLineString, mapping
from simulation_system import BikeShareSystem
from config import NEIGHBORHOOD_AREAS_GEOJSON_PATH
from datetime import datetime, timedelta


BASE_DATE = datetime(2025, 1, 1)

def create_hourly_trip_animation_map(system: BikeShareSystem):
    """
    Generates a Folium map animating trips, grouped by the hour they started.
    """
    print("Generating hourly trip animation map...")
    if not system.trip_log:
        print("No trips were logged, skipping animation map generation."); return

    # Use the first station as a fallback center point
    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")

    features = []

    for trip in system.trip_log:
        start_time_minutes = trip['start_time']
        # Group trips by the hour they started. The timestamp will be the end of that hour.
        start_hour = int((start_time_minutes / 60) % 24)
        # Use the end of the hour as the timestamp for the feature
        timestamp = BASE_DATE + timedelta(minutes=(start_hour + 1) * 60)
        timestamp_str = timestamp.isoformat()

        # Create GeoJSON features for each segment of the trip
        # Walk to station
        walk_to_geom = LineString([trip['user_origin'], trip['origin_station']])
        features.append({
            'type': 'Feature',
            'geometry': mapping(walk_to_geom),
            'properties': {
                'times': [timestamp_str] * len(walk_to_geom.coords),
                'style': {'color': 'blue', 'weight': 2, 'opacity': 0.8, 'dashArray': '5, 5'},
                'popup': f"Walk to Station (Trip started hour {start_hour})"
            }
        })

        # Cycle route
        cycle_geom = trip.get('route_geometry')
        if cycle_geom:
            # Ensure cycle_geom is a Shapely geometry object
            if isinstance(cycle_geom, (LineString, MultiLineString)):
                 # Flatten coordinates for MultiLineString
                coords = []
                if isinstance(cycle_geom, LineString):
                    coords = list(cycle_geom.coords)
                elif isinstance(cycle_geom, MultiLineString):
                    for line in cycle_geom.geoms:
                        coords.extend(list(line.coords))

                if coords:
                    features.append({
                        'type': 'Feature',
                        'geometry': mapping(cycle_geom),
                        'properties': {
                            'times': [timestamp_str] * len(coords),
                            'style': {'color': 'red', 'weight': 3, 'opacity': 0.8},
                            'popup': f"Cycle Route (Trip started hour {start_hour})"
                        }
                    })


        # Walk from station
        walk_from_geom = LineString([trip['dest_station'], trip['user_destination']])
        features.append({
            'type': 'Feature',
            'geometry': mapping(walk_from_geom),
            'properties': {
                'times': [timestamp_str] * len(walk_from_geom.coords),
                'style': {'color': 'blue', 'weight': 2, 'opacity': 0.8, 'dashArray': '5, 5'},
                'popup': f"Walk from Station (Trip started hour {start_hour})"
            }
        })

    # Add the TimestampedGeoJson layer to the map
    folium.plugins.TimestampedGeoJson(
        {'type': 'FeatureCollection', 'features': features},
        period='PT1H',  # Animation steps every hour
        add_last_point=True,
        auto_play=False,
        loop=False,
        duration='PT1M', # How long each step lasts
        transition_time=500, # Time between steps
        time_slider_drag_update=True
    ).add_to(m)

    # Add station markers (static, as animating capacity is complex here)
    for s in system.stations:
        tooltip = folium.Tooltip(text=f"Station {s.id}\nBikes: {s.bikes}\nCapacity: {s.capacity}")
        folium.Marker(location=[s.y, s.x], icon=folium.Icon(color='green', icon='bicycle', prefix='fa'), tooltip=tooltip).add_to(m)


    folium.LayerControl().add_to(m)
    map_filename = './generated/hourly_trip_animation.html'
    m.save(map_filename)
    print(f"Hourly trip animation map saved to '{map_filename}'")
def create_poi_distribution_map(system: BikeShareSystem):
    """
    Generates a Folium map showing the distribution of all POI types
    and the boundaries of the neighborhoods they were generated from.
    """
    print("Generating POI distribution map with neighborhood boundaries...")
    
    # Use the first station as a fallback center point
    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")

    # Define colors for each POI type for consistency
    colors = {
        'home': 'blue', 'shops': 'red', 'edu': 'green', 'uni': 'purple',
        'hospital': 'darkred', 'restaurant': 'orange', 'park': 'darkgreen',
        'sport': 'cadetblue', 'station': 'black'
    }

    # Add POI layers
    for poi_type, poi_list in sorted(system.poi_db.poi_data.items()):
        if not poi_list: continue
        
        feature_group = folium.FeatureGroup(name=poi_type.capitalize(), show=False)
        
        # Handle polygons (like 'uni') and points differently
        if 'geometry' in poi_list[0]:
            for poi in poi_list:
                folium.GeoJson(
                    poi['geometry'],
                    style_function=lambda x, color=colors.get(poi_type, 'gray'): {
                        'fillColor': color, 'color': color, 'weight': 2
                    }
                ).add_to(feature_group)
        else:
            for poi in poi_list:
                folium.CircleMarker(
                    location=[poi['lat'], poi['lon']], radius=3,
                    color=colors.get(poi_type, 'gray'), fill=True, fill_opacity=0.7
                ).add_to(feature_group)
        
        feature_group.add_to(m)

    # Add neighborhood boundaries layer
    try:
        boundaries_gdf = gpd.read_file(NEIGHBORHOOD_AREAS_GEOJSON_PATH)
        boundary_layer = folium.FeatureGroup(name='Neighborhood Boundaries', show=True)
        folium.GeoJson(
            boundaries_gdf,
            style_function=lambda x: {'color': 'black', 'weight': 1, 'fillOpacity': 0.1},
            tooltip=folium.GeoJsonTooltip(fields=['buurtnaam'])
        ).add_to(boundary_layer)
        boundary_layer.add_to(m)
    except Exception as e:
        print(f"Could not add neighborhood boundaries: {e}")

    folium.LayerControl().add_to(m)
    map_filename =  './generated/poi_and_boundaries_map.html'
    m.save(map_filename)
    print(f"POI distribution map saved to '{map_filename}'")


def create_trip_path_map(system: BikeShareSystem):
    """
    Generates a Folium map showing the complete path of every successful trip.
    """
    print("Generating detailed trip path map...")
    if not system.trip_log:
        print("No trips were logged, skipping map generation."); return

    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13,  tiles="CartoDB positron")

    for s in system.stations:
        tooltip = folium.Tooltip(text=f"Station {s.id}\n{s.bikes}/{s.capacity} available")
        folium.Marker(location=[s.y, s.x], icon=folium.Icon(color='green', icon='bicycle', prefix='fa'), tooltip=tooltip).add_to(m)

    for trip in system.trip_log:
        folium.PolyLine(locations=[(trip['user_origin'][1], trip['user_origin'][0]), (trip['origin_station'][1], trip['origin_station'][0])], color='blue', weight=2, opacity=0.8, dash_array='5, 5').add_to(m)
        folium.PolyLine(locations=[(trip['dest_station'][1], trip['dest_station'][0]), (trip['user_destination'][1], trip['user_destination'][0])], color='blue', weight=2, opacity=0.8, dash_array='5, 5').add_to(m)
        if trip.get('route_geometry'):
            folium.GeoJson(trip['route_geometry'], style_function=lambda x: {'color': 'red', 'weight': 3}).add_to(m)
            
    map_filename = './generated/all_trip_paths.html'
    m.save(map_filename)
    print(f"Detailed trip path map saved to '{map_filename}'")

def create_results_heatmap(system: BikeShareSystem):
    """
    Generates a heatmap of route and station usage.
    """
    print("Generating results heatmap...")
    route_geometries = [system.station_routes[route]['geometry'] for route, usage in system.route_usage.items() if usage > 0 and system.station_routes.get(route) and system.station_routes[route].get('geometry') for _ in range(usage)]
    if not route_geometries:
        print("No routes were used, skipping heatmap visualization."); return

    routes_gdf = gpd.GeoDataFrame(geometry=route_geometries, crs="EPSG:4326")
    stations_gdf = gpd.GeoDataFrame(geometry=[Point(s.x, s.y) for s in system.stations], crs="EPSG:4326")
    stations_gdf['usage'] = [system.station_usage.get(s.id, 0) for s in system.stations]

    fig, ax = plt.subplots(figsize=(15, 15))
    routes_gdf.to_crs(epsg=3857).plot(ax=ax, color='crimson', linewidth=0.5, alpha=0.1)
    markersize = stations_gdf['usage'].apply(lambda x: x * 5 + 10)
    stations_gdf.to_crs(epsg=3857).plot(ax=ax, marker='o', color='skyblue', edgecolor='black', markersize=markersize, alpha=0.9)

    cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)
    ax.set_axis_off()
    heatmap_path = './generated/simulation_results_heatmap.png'
    plt.savefig(heatmap_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
    print(f"Results heatmap saved to '{heatmap_path}'")