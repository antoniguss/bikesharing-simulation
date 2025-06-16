# visualizations.py

import folium
import folium.plugins
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx
from shapely.geometry import Point, LineString, MultiLineString, mapping
from datetime import datetime, timedelta

from simulation_system import BikeShareSystem
from config import (
    NEIGHBORHOOD_AREAS_GEOJSON_PATH, POI_MAP_PATH, ALL_TRIP_PATHS_MAP_PATH,
    RESULTS_HEATMAP_PATH, HOURLY_STATION_HEATMAP_PATH, HOURLY_TRIP_ANIMATION_PATH
)

BASE_DATE = datetime(2025, 1, 1)

def create_poi_distribution_map(system: BikeShareSystem):
    """Generates a Folium map showing all POI types and neighborhood boundaries."""
    if not system.stations: return
    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")

    colors = {
        'home': 'blue', 'shops': 'red', 'edu': 'green', 'uni': 'purple',
        'hospital': 'darkred', 'restaurant': 'orange', 'park': 'darkgreen',
        'sport': 'cadetblue', 'station': 'black'
    }

    for poi_type, poi_list in sorted(system.poi_db.poi_data.items()):
        if not poi_list: continue
        fg = folium.FeatureGroup(name=poi_type.capitalize(), show=False).add_to(m)
        color = colors.get(poi_type, 'gray')
        
        if 'geometry' in poi_list[0]:
            for poi in poi_list:
                folium.GeoJson(poi['geometry'], style_function=lambda _, c=color: {'fillColor': c, 'color': c}).add_to(fg)
        else:
            for poi in poi_list:
                folium.CircleMarker(location=[poi['lat'], poi['lon']], radius=3, color=color, fill=True).add_to(fg)

    try:
        boundaries_gdf = gpd.read_file(NEIGHBORHOOD_AREAS_GEOJSON_PATH)
        boundary_layer = folium.FeatureGroup(name='Neighborhood Boundaries', show=True).add_to(m)
        folium.GeoJson(
            boundaries_gdf,
            style_function=lambda x: {'color': 'black', 'weight': 1, 'fillOpacity': 0.1},
            tooltip=folium.GeoJsonTooltip(fields=['buurtnaam'])
        ).add_to(boundary_layer)
    except Exception as e:
        print(f"Warning: Could not add neighborhood boundaries to map: {e}")

    folium.LayerControl().add_to(m)
    m.save(str(POI_MAP_PATH))

def create_hourly_trip_animation_map(system: BikeShareSystem):
    """
    Generates a Folium map animating trips, grouped by the hour they started.
    """
    print("Generating hourly trip animation map...")
    if not system.trip_log:
        print("No trips were logged, skipping animation map generation."); return

    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")

    features = []
    walk_feature_group = folium.FeatureGroup(name='Walking Routes', show=True)
    cycle_feature_group = folium.FeatureGroup(name='Cycling Routes', show=True)

    for trip in system.trip_log:
        start_time_minutes = trip['start_time']
        start_hour = int((start_time_minutes / 60) % 24)
        timestamp = BASE_DATE + timedelta(minutes=(start_hour + 1) * 60)
        timestamp_str = timestamp.isoformat()

        # Walk to station
        walk_to_geom = LineString([trip['user_origin'], trip['origin_station']])
        features.append({
            'type': 'Feature',
            'geometry': mapping(walk_to_geom),
            'properties': {
                'times': [timestamp_str] * len(walk_to_geom.coords),
                'style': {'color': 'blue', 'weight': 2, 'opacity': 0.8, 'dashArray': '5, 5'},
                # 'popup': f"Walk to Station (Trip started hour {start_hour})"
            }
        })

        # Cycle route
        cycle_geom = trip.get('route_geometry')
        if cycle_geom and isinstance(cycle_geom, (LineString, MultiLineString)):
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
                        'style': {'color': 'red', 'weight': 5, 'opacity': 0.6},
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
            }
        })

    # Add the TimestampedGeoJson layer to the map
    folium.plugins.TimestampedGeoJson(
        {'type': 'FeatureCollection', 'features': features},
        period='PT1H',
        add_last_point=False,
        auto_play=False,
        loop=False,
        duration='PT1M',
        transition_time=500,
        time_slider_drag_update=True
    ).add_to(m)

    # Add station markers with toggleable feature groups
    station_feature_group = folium.FeatureGroup(name='Stations', show=True)
    for s in system.stations:
        tooltip = folium.Tooltip(text=f"{s.neighbourhood}\n")
        folium.Marker(
            location=[s.y, s.x],
            icon=folium.Icon(color='green', icon='bicycle', prefix='fa'),
            tooltip=tooltip
        ).add_to(station_feature_group)
    station_feature_group.add_to(m)

    folium.LayerControl().add_to(m)
    map_filename = './generated/hourly_trip_animation.html'
    m.save(map_filename)
    print(f"Hourly trip animation map saved to '{map_filename}'")

def create_all_trip_paths_map(system: BikeShareSystem):
    """Generates a Folium map showing the complete path of every successful trip."""
    if not system.trip_log: return
    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")

    for station in system.stations:
        folium.Marker(location=[station.y, station.x], icon=folium.Icon(color='green', icon='bicycle', prefix='fa'), tooltip=f"Station: {station.neighbourhood}").add_to(m)

    walk_paths = folium.FeatureGroup(name="Walking Paths", show=False).add_to(m)
    bike_paths = folium.FeatureGroup(name="Cycling Paths", show=True).add_to(m)

    for trip in system.trip_log:
        walk_to_coords = [(p[1], p[0]) for p in [trip['user_origin'], trip['origin_station']]]
        walk_from_coords = [(p[1], p[0]) for p in [trip['dest_station'], trip['user_destination']]]
        folium.PolyLine(walk_to_coords, color='blue', weight=2.5, opacity=0.8, dash_array='5').add_to(walk_paths)
        folium.PolyLine(walk_from_coords, color='blue', weight=2.5, opacity=0.8, dash_array='5').add_to(walk_paths)
        
        if trip.get('route_geometry'):
            folium.GeoJson(trip['route_geometry'], style_function=lambda x: {'color': 'red', 'weight': 3}).add_to(bike_paths)
            
    folium.LayerControl().add_to(m)
    m.save(str(ALL_TRIP_PATHS_MAP_PATH))

def create_results_heatmap(system: BikeShareSystem):
    """Generates a heatmap image of route and station usage."""
    route_geometries = [
        geom for route, usage in system.route_usage.items()
        if usage > 0 and (geom := system.station_routes.get(route, {}).get('geometry'))
        for _ in range(usage)
    ]
    if not route_geometries: return

    routes_gdf = gpd.GeoDataFrame(geometry=route_geometries, crs="EPSG:4326")
    stations_gdf = gpd.GeoDataFrame(
        data=[(system.station_usage.get(s.id, 0),) for s in system.stations],
        geometry=[Point(s.x, s.y) for s in system.stations],
        columns=['usage'], crs="EPSG:4326"
    )

    fig, ax = plt.subplots(figsize=(12, 12))
    routes_gdf.to_crs(epsg=3857).plot(ax=ax, color='crimson', linewidth=0.5, alpha=0.15)
    markersize = stations_gdf['usage'].apply(lambda x: max(x * 4, 10))
    stations_gdf.to_crs(epsg=3857).plot(ax=ax, marker='o', color='skyblue', edgecolor='black', markersize=markersize, alpha=0.9)

    cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)
    ax.set_axis_off()
    plt.savefig(str(RESULTS_HEATMAP_PATH), dpi=200, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)

def create_hourly_station_heatmap(system: BikeShareSystem):
    """Generates a heatmap image showing station trip activity by hour."""
    if not system.trip_log: return
    
    station_map = {s.id: s.neighbourhood for s in system.stations}
    station_ids = list(station_map.keys())
    hourly_usage = {s_id: [0] * 24 for s_id in station_ids}
    
    for trip in system.trip_log:
        hour = int(trip['start_time'] / 60) % 24
        origin = next((s for s in system.stations if (s.x, s.y) == trip['origin_station']), None)
        dest = next((s for s in system.stations if (s.x, s.y) == trip['dest_station']), None)
        if origin: hourly_usage[origin.id][hour] += 1
        if dest: hourly_usage[dest.id][hour] += 1

    data = np.array([hourly_usage[s_id] for s_id in station_ids])
    if data.sum() == 0: return

    fig, ax = plt.subplots(figsize=(16, max(8, len(station_map) * 0.4)))
    im = ax.imshow(data, cmap='YlOrRd', aspect='auto')

    ax.set_xticks(np.arange(24))
    ax.set_yticks(np.arange(len(station_map)))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(24)])
    ax.set_yticklabels([station_map[s_id] for s_id in station_ids])

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.02, pad=0.04)
    cbar.ax.set_ylabel("Number of Trips", rotation=-90, va="bottom")
    ax.set_title("Station Activity by Hour of Day")

    plt.tight_layout()
    plt.savefig(str(HOURLY_STATION_HEATMAP_PATH), dpi=150, bbox_inches='tight')
    plt.close(fig)