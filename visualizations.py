# visualizations.py

import folium
import folium.plugins
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx
from shapely.geometry import Point, LineString, MultiLineString, mapping
from datetime import datetime, timedelta
from typing import Dict, List
from data_models import Station

import config
from simulation_system import BikeShareSystem

BASE_DATE = datetime(2025, 1, 1)

def get_station_color(bikes: int, capacity: int) -> str:
    """Determines a hex color for a station marker based on bike availability percentage."""
    if capacity == 0: return '#808080'  # Gray for no/unknown capacity
    
    fill_ratio = bikes / capacity
    if bikes == 0:
        return '#d9534f'  # Red: Empty
    elif bikes == capacity:
        return '#0275d8'  # Dark Blue: Full
    elif fill_ratio <= 0.3:
        return '#f0ad4e'  # Orange: Almost Empty
    elif fill_ratio >= 0.8:
        return '#5bc0de'  # Light Blue: Almost Full
    else:
        return '#5cb85c'  # Green: Normal

# Common legend for station status maps
STATION_LEGEND_HTML = '''
<div style="position: fixed; bottom: 50px; left: 50px; width: 220px; height: 140px; 
 border:2px solid grey; z-index:9999; font-size:14px; background-color: white; padding: 5px;">
 <b>Station Status</b><br>
 <i class="fa fa-circle" style="color:#5cb85c"></i> Normal (>30% - <80%)<br>
 <i class="fa fa-circle" style="color:#f0ad4e"></i> Almost Empty (≤30%)<br>
 <i class="fa fa-circle" style="color:#d9534f"></i> Empty (0)<br>
 <i class="fa fa-circle" style="color:#5bc0de"></i> Almost Full (≥80%)<br>
 <i class="fa fa-circle" style="color:#0275d8"></i> Full (100%)<br>
</div>
'''

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
        boundaries_gdf = gpd.read_file(config.NEIGHBORHOOD_AREAS_GEOJSON_PATH)
        boundary_layer = folium.FeatureGroup(name='Neighborhood Boundaries', show=True).add_to(m)
        folium.GeoJson(
            boundaries_gdf,
            style_function=lambda x: {'color': 'black', 'weight': 1, 'fillOpacity': 0.1},
            tooltip=folium.GeoJsonTooltip(fields=['buurtnaam'])
        ).add_to(boundary_layer)
    except Exception as e:
        print(f"Warning: Could not add neighborhood boundaries to map: {e}")

    folium.LayerControl().add_to(m)
    m.save(str(config.POI_MAP_PATH))

def create_hourly_trip_animation_map(system: BikeShareSystem):
    """Generates a Folium map animating trips, grouped by the hour they started."""
    if not system.trip_log: return
    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")

    features = []
    for trip in system.trip_log:
        start_time_minutes = trip['start_time']
        start_hour = int((start_time_minutes / 60) % 24)
        timestamp = BASE_DATE + timedelta(minutes=(start_hour + 1) * 60)
        timestamp_str = timestamp.isoformat()
        
        # --- FIX STARTS HERE ---
        # Add walking paths
        features.append({'type': 'Feature','geometry': mapping(LineString([trip['user_origin'], trip['origin_station']])), 'properties': {'times': [timestamp_str] * 2, 'style': {'color': 'blue', 'weight': 2, 'opacity': 0.8, 'dashArray': '5, 5'}}})
        features.append({'type': 'Feature','geometry': mapping(LineString([trip['dest_station'], trip['user_destination']])), 'properties': {'times': [timestamp_str] * 2, 'style': {'color': 'blue', 'weight': 2, 'opacity': 0.8, 'dashArray': '5, 5'}}})
        
        # Add cycling path, correctly handling both LineString and MultiLineString
        cycle_geom = trip.get('route_geometry')
        if cycle_geom and isinstance(cycle_geom, (LineString, MultiLineString)):
            all_coords = []
            if isinstance(cycle_geom, LineString):
                all_coords.extend(list(cycle_geom.coords))
            elif isinstance(cycle_geom, MultiLineString):
                for line in cycle_geom.geoms:
                    all_coords.extend(list(line.coords))
            
            if all_coords:
                features.append({
                    'type': 'Feature',
                    'geometry': mapping(cycle_geom),
                    'properties': {
                        'times': [timestamp_str] * len(all_coords),
                        'style': {'color': 'red', 'weight': 4, 'opacity': 0.7}
                    }
                })
        # --- FIX ENDS HERE ---

    folium.plugins.TimestampedGeoJson(
        {'type': 'FeatureCollection', 'features': features}, period='PT1H', add_last_point=False,
        auto_play=False, loop=False, duration='PT1M', transition_time=500, time_slider_drag_update=True
    ).add_to(m)

    # Add static station markers for context
    station_fg = folium.FeatureGroup(name="Stations (Static)", show=True).add_to(m)
    for s in system.stations:
        folium.Marker(location=[s.y, s.x], icon=folium.Icon(color='darkgreen', icon='bicycle', prefix='fa'), tooltip=s.neighbourhood).add_to(station_fg)
    folium.LayerControl().add_to(m)
    m.save(str(config.HOURLY_TRIP_ANIMATION_PATH))


def create_station_availability_animation_map(system: BikeShareSystem):
    """Generates a TimestampedGeoJson map showing bike availability at each station per hour."""
    if not system.hourly_bike_counts: return
    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")
    
    features, station_dict = [], {s.id: s for s in system.stations}
    for hour in sorted(system.hourly_bike_counts.keys()):
        timestamp = BASE_DATE + timedelta(hours=hour)
        for station_id, bike_count in system.hourly_bike_counts[hour].items():
            station = station_dict.get(station_id)
            if not station: continue
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [station.x, station.y]},
                'properties': {
                    'time': timestamp.isoformat(), 'icon': 'circle',
                    'iconstyle': {
                        'fillColor': get_station_color(bike_count, station.capacity),
                        'fillOpacity': 0.9, 'stroke': 'true', 'radius': 8, 'color': 'black', 'weight': 1
                    },
                    'popup': (f"<b>{station.neighbourhood}</b><br>"
                              f"Time: {timestamp.strftime('%H:%M')}<br>"
                              f"Bikes: {bike_count} / {station.capacity}")
                }
            })
    if not features: return

    folium.plugins.TimestampedGeoJson(
        {'type': 'FeatureCollection', 'features': features}, period='PT1H', add_last_point=True,
        auto_play=False, loop=False, max_speed=1.5, loop_button=True, time_slider_drag_update=True, duration='PT1H'
    ).add_to(m)
    
    m.get_root().html.add_child(folium.Element(STATION_LEGEND_HTML))
    m.save(str(config.STATION_AVAILABILITY_ANIMATION_PATH))

def create_all_trip_paths_map(system: BikeShareSystem):
    """Generates a map showing all trip paths and the FINAL state of each station."""
    if not system.trip_log and not system.stations: return
    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")

    # Add station markers showing final availability state
    station_fg = folium.FeatureGroup(name="Stations (Final State)", show=True).add_to(m)
    for station in system.stations:
        color = get_station_color(station.bikes, station.capacity)
        tooltip = f"<b>{station.neighbourhood}</b><br>Final State: {station.bikes}/{station.capacity} bikes"
        folium.CircleMarker(
            location=[station.y, station.x],
            radius=8,
            color='black',
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            tooltip=tooltip
        ).add_to(station_fg)

    # Add paths if any trips occurred
    if system.trip_log:
        walk_paths = folium.FeatureGroup(name="Walking Paths", show=False).add_to(m)
        bike_paths = folium.FeatureGroup(name="Cycling Paths", show=True).add_to(m)
        for trip in system.trip_log:
            folium.PolyLine([(p[1], p[0]) for p in [trip['user_origin'], trip['origin_station']]], color='blue', weight=2.5, opacity=0.8, dash_array='5').add_to(walk_paths)
            folium.PolyLine([(p[1], p[0]) for p in [trip['dest_station'], trip['user_destination']]], color='blue', weight=2.5, opacity=0.8, dash_array='5').add_to(walk_paths)
            if trip.get('route_geometry'):
                folium.GeoJson(trip['route_geometry'], style_function=lambda x: {'color': 'red', 'weight': 3}).add_to(bike_paths)
            
    m.get_root().html.add_child(folium.Element(STATION_LEGEND_HTML))
    folium.LayerControl().add_to(m)
    m.save(str(config.ALL_TRIP_PATHS_MAP_PATH))


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
    plt.savefig(str(config.RESULTS_HEATMAP_PATH), dpi=200, bbox_inches='tight', pad_inches=0.1)
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
    plt.savefig(str(config.HOURLY_STATION_HEATMAP_PATH), dpi=150, bbox_inches='tight')
    plt.close(fig)

def create_rebalancing_route_map(system: BikeShareSystem, route_data: Dict, stations_to_visit: List[Station]) -> None:
    """Creates a map visualization of the optimized rebalancing route."""
    if not route_data or not stations_to_visit: return
    
    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")

    # Add the optimized route
    folium.GeoJson(
        route_data,
        style_function=lambda x: {'color': 'red', 'weight': 4, 'opacity': 0.7}
    ).add_to(m)

    # Add station markers
    for i, station in enumerate(stations_to_visit, 1):
        fill_ratio = station.bikes / station.capacity
        color = '#d9534f' if fill_ratio < 0.3 else '#0275d8'  # Red for low, Blue for high
        reason = "Low bikes" if fill_ratio < 0.3 else "High bikes"
        
        folium.CircleMarker(
            location=[station.y, station.x],
            radius=8,
            color='black',
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=f"#{i}: {station.neighbourhood}<br>Bikes: {station.bikes}/{station.capacity}<br>Reason: {reason}"
        ).add_to(m)

    m.save(str(config.REBALANCING_ROUTE_MAP_PATH))