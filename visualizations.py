# visualizations.py

import folium
import folium.plugins
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx
from shapely.geometry import Point, LineString, MultiLineString, mapping
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from data_models import Station
from openrouteservice import convert
import pandas as pd

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

# Legend for trip path types
TRIP_LEGEND_HTML = '''
<div style="position: fixed; bottom: 200px; left: 50px; width: 160px; height: 80px; 
 border:2px solid grey; z-index:9999; font-size:14px; background-color: white; padding: 5px;">
 <b>Trip Path Type</b><br>
 <svg width="20" height="10"><line x1="0" y1="5" x2="20" y2="5" style="stroke:red;stroke-width:3" /></svg> Cycling<br>
 <svg width="20" height="10"><line x1="0" y1="5" x2="20" y2="5" style="stroke:blue;stroke-width:3;stroke-dasharray: 3 3" /></svg> Walking<br>
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

    # Add POIs
    for poi_type, poi_list in sorted(system.poi_db.poi_data.items()):
        if not poi_list: continue
        fg = folium.FeatureGroup(name=poi_type.capitalize(), show=True).add_to(m)
        color = colors.get(poi_type, 'gray')
        
        for poi in poi_list:
            if 'geometry' in poi:
                # For area POIs (like neighborhoods, campuses)
                folium.GeoJson(
                    poi['geometry'],
                    style_function=lambda _, c=color: {
                        'fillColor': c,
                        'color': c,
                        'fillOpacity': 0.3,
                        'weight': 2
                    },
                    tooltip=poi.get('name', poi_type)
                ).add_to(fg)
            else:
                # For point POIs
                folium.CircleMarker(
                    location=[poi['lat'], poi['lon']],
                    radius=3,
                    color=color,
                    fill=True,
                    fill_opacity=0.7,
                    tooltip=poi_type
                ).add_to(fg)

    # Add neighborhood boundaries
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

    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 300px; 
    border:2px solid grey; z-index:9999; font-size:14px; background-color: white; padding: 10px;">
    <b>POI Types</b><br>
    '''
    for poi_type, color in colors.items():
        legend_html += f'<i class="fa fa-circle" style="color:{color}"></i> {poi_type.capitalize()}<br>'
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))

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
        
        # Add walking paths
        features.append({
            'type': 'Feature',
            'geometry': mapping(LineString([trip['user_origin'], trip['origin_station']])),
            'properties': {
                'times': [timestamp_str] * 2,
                'style': {'color': 'blue', 'weight': 2, 'opacity': 0.8, 'dashArray': '5, 5'}
            }
        })
        features.append({
            'type': 'Feature',
            'geometry': mapping(LineString([trip['dest_station'], trip['user_destination']])),
            'properties': {
                'times': [timestamp_str] * 2,
                'style': {'color': 'blue', 'weight': 2, 'opacity': 0.8, 'dashArray': '5, 5'}
            }
        })
        
        # Add cycling path
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

    # Add station markers for each hour
    for hour in sorted(system.hourly_bike_counts.keys()):
        timestamp = BASE_DATE + timedelta(hours=hour)
        timestamp_str = timestamp.isoformat()
        
        for station_id, bike_count in system.hourly_bike_counts[hour].items():
            station = next((s for s in system.stations if s.id == station_id), None)
            if not station: continue
            
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [station.x, station.y]},
                'properties': {
                    'times': [timestamp_str],
                    'icon': 'circle',
                    'iconstyle': {
                        'fillColor': get_station_color(bike_count, station.capacity),
                        'fillOpacity': 0.9,
                        'stroke': 'true',
                        'radius': 8,
                        'color': 'black',
                        'weight': 1
                    },
                    'popup': (f"<b>{station.neighbourhood}</b><br>"
                             f"Time: {timestamp.strftime('%H:%M')}<br>"
                             f"Bikes: {bike_count} / {station.capacity}")
                }
            })

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

    # Add station status legend
    m.get_root().html.add_child(folium.Element(STATION_LEGEND_HTML))
    m.save(str(config.HOURLY_TRIP_ANIMATION_PATH))

def create_realtime_trip_animation_map(system: BikeShareSystem):
    """Generates a Folium map with a real-time animation of each trip."""
    if not system.trip_log: return
    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")

    features = []
    for trip in system.trip_log:
        try:
            # Convert simulation minutes to datetime objects
            walk_to_start = BASE_DATE + timedelta(minutes=trip['walk_to_start_time'])
            cycle_start = BASE_DATE + timedelta(minutes=trip['cycle_start_time'])
            walk_from_start = BASE_DATE + timedelta(minutes=trip['walk_from_start_time'])
            trip_end = BASE_DATE + timedelta(minutes=trip['trip_end_time'])
        except KeyError:
            # Skip if a trip log entry is missing the new timing keys
            continue

        # 1. First walk leg (User Origin -> Origin Station)
        features.append({
            'type': 'Feature',
            'geometry': mapping(LineString([trip['user_origin'], trip['origin_station']])),
            'properties': {
                'times': [walk_to_start.isoformat(), cycle_start.isoformat()],
                'style': {'color': 'blue', 'weight': 3, 'dashArray': '5, 5', 'opacity': 0.8},
                'popup': 'Walking to station'
            }
        })

        # 2. Cycling leg (Origin Station -> Destination Station)
        cycle_geom = trip.get('route_geometry')
        if cycle_geom and isinstance(cycle_geom, (LineString, MultiLineString)):
            all_coords = []
            if isinstance(cycle_geom, LineString):
                all_coords.extend(list(cycle_geom.coords))
            elif isinstance(cycle_geom, MultiLineString):
                for line in cycle_geom.geoms:
                    all_coords.extend(list(line.coords))
            
            if all_coords:
                num_points = len(all_coords)
                cycle_duration_seconds = (walk_from_start - cycle_start).total_seconds()
                
                timestamps = []
                if num_points > 1 and cycle_duration_seconds > 0:
                    time_per_segment = cycle_duration_seconds / (num_points - 1)
                    timestamps = [(cycle_start + timedelta(seconds=i * time_per_segment)).isoformat() for i in range(num_points)]
                elif num_points > 0:
                    timestamps = [cycle_start.isoformat()] * num_points
                
                if timestamps:
                    features.append({
                        'type': 'Feature',
                        'geometry': mapping(cycle_geom),
                        'properties': {
                            'times': timestamps,
                            'style': {'color': 'red', 'weight': 4, 'opacity': 0.7},
                            'popup': 'Cycling'
                        }
                    })

        # 3. Second walk leg (Destination Station -> User Destination)
        features.append({
            'type': 'Feature',
            'geometry': mapping(LineString([trip['dest_station'], trip['user_destination']])),
            'properties': {
                'times': [walk_from_start.isoformat(), trip_end.isoformat()],
                'style': {'color': 'blue', 'weight': 3, 'dashArray': '5, 5', 'opacity': 0.8},
                'popup': 'Walking to destination'
            }
        })
    
    # Add station markers (static, showing final state) for context
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
        ).add_to(m)

    folium.plugins.TimestampedGeoJson(
        {'type': 'FeatureCollection', 'features': features},
        period='PT1M', # Update every minute
        add_last_point=False,
        auto_play=False,
        loop=False,
        max_speed=60, # 60x real time, so 1 minute of sim time takes 1 second
        loop_button=True,
        duration='PT1M', # Each segment lasts 1 minute in the animation
        transition_time=100, # ms
        time_slider_drag_update=True
    ).add_to(m)

    m.get_root().html.add_child(folium.Element(STATION_LEGEND_HTML))
    m.get_root().html.add_child(folium.Element(TRIP_LEGEND_HTML))
    m.save(str(config.REALTIME_TRIP_ANIMATION_PATH))


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
            folium.PolyLine([(p[1], p[0]) for p in [trip['user_origin'], trip['origin_station']]], 
                          color='blue', weight=1.5, opacity=0.3, dash_array='5').add_to(walk_paths)
            folium.PolyLine([(p[1], p[0]) for p in [trip['dest_station'], trip['user_destination']]], 
                          color='blue', weight=1.5, opacity=0.3, dash_array='5').add_to(walk_paths)
            if trip.get('route_geometry'):
                folium.GeoJson(trip['route_geometry'], 
                             style_function=lambda x: {'color': 'red', 'weight': 2, 'opacity': 0.2}).add_to(bike_paths)
            
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

def create_hourly_failures_plot(system: BikeShareSystem):
    """Creates a plot showing the number of failed trips by hour."""
    if not system.hourly_failures: return
    
    hours = list(range(24))
    failures = [system.hourly_failures[h] for h in hours]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(hours, failures, color='#d9534f')
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Number of Failed Trips')
    ax.set_title('Failed Trips by Hour')
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}:00" for h in hours], rotation=45)
    
    plt.tight_layout()
    plt.savefig(str(config.HOURLY_FAILURES_PATH), dpi=150, bbox_inches='tight')
    plt.close(fig)

def create_rebalancing_route_map(system: BikeShareSystem, min_threshold: float = 0.3, max_threshold: float = 0.7) -> Optional[tuple[str, list]]:
    """Generates a map showing the optimal rebalancing route.
    Returns a tuple of (map_path, visit_order_data) if successful."""
    rebalancing_data = system.generate_rebalancing_route(min_threshold, max_threshold)
    if not rebalancing_data:
        return None

    map_center = [system.stations[0].y, system.stations[0].x]
    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron")

    # Get stations that need rebalancing
    stations_to_visit = {s.id: s for s in rebalancing_data['stations']}

    # Add all stations (non-rebalancing stations in gray)
    for station in system.stations:
        if station.id in stations_to_visit:
            continue  # Skip stations that need rebalancing, we'll add them with numbered markers
        tooltip = f"<b>{station.neighbourhood}</b><br>Bikes: {station.bikes}/{station.capacity}"
        folium.CircleMarker(
            location=[station.y, station.x],
            radius=8,
            color='black',
            weight=1,
            fill=True,
            fill_color='gray',
            fill_opacity=0.5,
            tooltip=tooltip
        ).add_to(m)

    # Add rebalancing route
    route = rebalancing_data['route']
    visit_order = []
    if 'routes' in route and route['routes']:
        route_geometry = route['routes'][0]['geometry']
        decoded_route = convert.decode_polyline(route_geometry)
        
        # Create route line
        folium.PolyLine(
            locations=[[coord[1], coord[0]] for coord in decoded_route['coordinates']],
            color='red',
            weight=4,
            opacity=0.8,
            tooltip="Rebalancing Route"
        ).add_to(m)

        # Create a table of stations to visit
        count = 0
        for step in route['routes'][0]['steps']:
            if step['type'] == 'job':
                count += 1
                station = next((s for s in rebalancing_data['stations'] if s.id == step['id']), None)
                if station:
                    visit_order.append({
                        'Order': count,
                        'Station': station.neighbourhood,
                        'Current Bikes': station.bikes,
                        'Capacity': station.capacity,
                        'Fill Ratio': f"{(station.bikes / station.capacity) * 100:.1f}%",
                        'Distance': f"{step['distance'] / 1000:.2f}km"
                    })
                    
                    # Add numbered marker for this station
                    folium.CircleMarker(
                        location=[station.y, station.x],
                        radius=12,
                        color='blue',
                        weight=2,
                        fill=True,
                        fill_opacity=0.9,
                        tooltip=(
                            f"Stop {count}: {station.neighbourhood}<br>"
                            f"Distance: {step['distance'] / 1000:.2f}km"
                        )
                    ).add_to(m)
                    
                    # Add number label
                    folium.Marker(
                        location=[station.y, station.x],
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 12pt; color: white; font-weight: bold;">{count}</div>',
                            icon_size=(20, 20),
                            icon_anchor=(10, 10)
                        )
                    ).add_to(m)

    # Add legend
    m.get_root().html.add_child(folium.Element(STATION_LEGEND_HTML))
    
    # Save to a temporary file
    output_path = config.GENERATED_DIR / 'rebalancing_route.html'
    m.save(str(output_path))
    return str(output_path), visit_order