# live_folium_app.py

import simpy
import folium
import json
import threading
import time
from flask import Flask, jsonify

from config import ORS_API_KEY, SIMULATION_TIME, USER_ARRIVAL_RATE
from simulation_system import BikeShareSystem
from simulation_processes import user_generator
from folium.plugins import Realtime

# --- Global objects ---
# We initialize the system here so it's accessible to all parts of the app
system = BikeShareSystem(ors_api_key=ORS_API_KEY)
env = simpy.Environment()

# --- Simulation Runner Function (CHANGED) ---
def run_simulation():
    """
    This function runs in a background thread, advancing the simulation
    in small steps and sleeping in between.
    """
    print("--- Simulation Thread Started ---")
    # This process starts the user generator
    env.process(user_generator(env, system, USER_ARRIVAL_RATE))
    
    # The new simulation loop
    while env.now < SIMULATION_TIME:
        # Advance the simulation by 1 minute of simulation time
        env.run(until=env.now + 1)
        # Wait for 0.5 seconds of real time to control the "speed"
        time.sleep(0.5)
        
    print("--- Simulation Thread Finished ---")

def get_live_data_as_geojson(current_sim_time):
    """
    Calculates current positions and formats them as GeoJSON,
    which is what the folium.plugins.Realtime plugin expects.
    """
    features = []
    
    # We acquire the system's lock to safely get a copy of the active users
    with system.lock:
        active_users_copy = list(system.active_users.items())

    for user_id, data in active_users_copy:
        duration = data['end_time'] - data['start_time']
        time_elapsed = current_sim_time - data['start_time']
        progress = min(max(time_elapsed / duration, 0.0), 1.0) if duration > 0 else 1.0
        
        start_lon, start_lat = data['start_coord']
        end_lon, end_lat = data['end_coord']
        
        current_lon = start_lon + progress * (end_lon - start_lon)
        current_lat = start_lat + progress * (end_lat - start_lat)
        
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [current_lon, current_lat]},
            'properties': {
                'id': user_id, 'time': current_sim_time,
                'icon': 'circle',
                'color': 'red' if data['mode'] == 'cycling' else 'blue',
                'popup': f"User {user_id}<br>Mode: {data['mode']}"
            }
        })
        
    return {"type": "FeatureCollection", "features": features}

# --- Flask Web Application ---
app = Flask(__name__)

@app.route('/')
def index():
    """Serves the initial Folium map."""
    avg_lat = sum(s.y for s in system.stations) / len(system.stations)
    avg_lon = sum(s.x for s in system.stations) / len(system.stations)
    
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)

    for s in system.stations:
        folium.Marker(
            location=[s.y, s.x],
            popup=f"Station {s.id}: {s.neighbourhood}",
            icon=folium.Icon(color='green', icon='bicycle', prefix='fa')
        ).add_to(m)
        
    realtime_plugin = Realtime(
        source='/data',
        callback="""
            function(data) {
                this.layer.clearLayers();
                L.geoJson(data, {
                    pointToLayer: function(feature, latlng) {
                        return L.circleMarker(latlng, {
                            radius: 8, fillColor: feature.properties.color,
                            color: "#000", weight: 1, opacity: 1, fillOpacity: 0.8
                        }).bindPopup(feature.properties.popup);
                    }
                }).addTo(this.layer);
            }
        """,
        interval=1000
    )
    m.add_child(realtime_plugin)
    
    return m.get_root().render()

@app.route('/data')
def data():
    """Provides the live data feed."""
    return jsonify(get_live_data_as_geojson(env.now))

if __name__ == '__main__':
    sim_thread = threading.Thread(target=run_simulation)
    sim_thread.daemon = True
    sim_thread.start()
    
    app.run(debug=True, use_reloader=False)