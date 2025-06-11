# simulation_runner.py

import simpy
import threading
import time
import pandas as pd

from config import ORS_API_KEY, SIMULATION_TIME, USER_ARRIVAL_RATE
from simulation_system import BikeShareSystem
from simulation_processes import user_generator

class SimulationRunner:
    """
    This class runs the SimPy simulation in a background thread
    and provides the latest data to the Streamlit UI thread-safely.
    """
    def __init__(self):
        self.system = BikeShareSystem(ors_api_key=ORS_API_KEY)
        self.env = simpy.Environment()
        self.env.process(user_generator(self.env, self.system, USER_ARRIVAL_RATE))
        
        self.lock = threading.Lock()
        self.latest_data = {
            "time": 0,
            "users_df": pd.DataFrame(),
            "stations_df": pd.DataFrame(),
            "stats": self.system.stats
        }
        self.is_running = False
        self.simulation_thread = None

    def _get_live_user_positions(self, current_time):
        """Calculates the current lon/lat of all active users."""
        user_data = []
        for user_id, data in self.system.active_users.items():
            duration = data['end_time'] - data['start_time']
            time_elapsed = current_time - data['start_time']
            progress = min(max(time_elapsed / duration, 0.0), 1.0) if duration > 0 else 1.0
            
            start_lon, start_lat = data['start_coord']
            end_lon, end_lat = data['end_coord']
            
            current_lon = start_lon + progress * (end_lon - start_lon)
            current_lat = start_lat + progress * (end_lat - start_lat)
            
            user_data.append({
                "lon": current_lon, "lat": current_lat, "mode": data['mode'],
                "size": 25 if data['mode'] == 'cycling' else 15,
                "color": [255, 0, 0, 200] if data['mode'] == 'cycling' else [0, 0, 255, 200]
            })
        return pd.DataFrame(user_data) if user_data else pd.DataFrame()

    def _simulation_loop(self, speed_config):
        """The main loop for the background simulation thread."""
        while self.env.now < SIMULATION_TIME and self.is_running:
            # Run simulation for a step
            self.env.run(until=self.env.now + speed_config["step"])
            
            # Prepare data for the UI
            users_df = self._get_live_user_positions(self.env.now)
            stations_df = pd.DataFrame([{
                "lon": s.x, "lat": s.y, "id": s.id, 
                "bikes": s.bikes, "capacity": s.capacity
            } for s in self.system.stations])
            
            # Use a lock to update shared data safely
            with self.lock:
                self.latest_data["time"] = self.env.now
                self.latest_data["users_df"] = users_df
                self.latest_data["stations_df"] = stations_df
                self.latest_data["stats"] = self.system.stats.copy()
            
            time.sleep(speed_config["sleep"])
        
        self.is_running = False
        print("--- SIMULATION THREAD FINISHED ---")

    def start(self, speed_config):
        """Starts the simulation thread."""
        if not self.is_running:
            self.is_running = True
            # Create and start the thread
            self.simulation_thread = threading.Thread(
                target=self._simulation_loop, 
                args=(speed_config,)
            )
            self.simulation_thread.start()

    def stop(self):
        """Stops the simulation thread."""
        self.is_running = False
        # Optional: Wait for the thread to finish
        if self.simulation_thread:
            self.simulation_thread.join()

    def get_latest_data(self):
        """Returns the latest data snapshot for the UI in a thread-safe way."""
        with self.lock:
            return self.latest_data.copy()