# How to Run the App

1. **(Optional but recommended) Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API keys:**
   - Create a file at `.streamlit/secrets.toml` in the project root.
   - Add your OpenRouteService API key:
     ```toml
     ORS_API_KEY = "your_openrouteservice_api_key_here"
     ```

4. **Run the app locally:**
   ```bash
   streamlit run dashboard.py
   ```

5. **Access the dashboard:**
   - Open your browser and go to [http://localhost:8501](http://localhost:8501)

---

> The app is also hosted online at: [https://bikesharing-simulation.streamlit.app/](https://bikesharing-simulation.streamlit.app/)

# Simulation overview

We're creating a digital model of a bike-sharing system for specific neighbourhoods in Eindhoven.
Our main goal is to **test and visualize the system's performance before building it in real life** and to serve as a **proof of concept** for a tool that could be used in real-time operations.

The simulation helps validate our business plan by answering key operational questions:

- Are the stations placed correctly to serve 15-minute city neighborhoods?
- How often do trips fail due to no available bikes?
- How often do trips fail because a station is full?
- What are the most common travel routes?
- How does bike availability change throughout the day?
- What is the optimal route for rebalancing bikes between stations?

The results provide evidence for:
- Operational feasibility through success/failure rates and station usage patterns
- Financial sustainability via demand patterns and rebalancing costs
- Real-time decision support for bike allocation and routing
- System responsiveness to dynamic demand fluctuations

## Implementation

### Setup

The simulation is built in Python. To calculate travel routes, we use the **[OSMnx][2]** library to download the bike-friendly street network from **[OpenStreetMap][1]**. This network is saved locally so it loads quickly on future runs. Before the simulation starts, the system calculates the fastest cycling route between every pair of stations using **[NetworkX][3]**. This pre-calculation makes the simulation run much faster.

### User agent

Users in our simulation are managed by **[SimPy][4]**, a library for running event-based simulations. New users are created over time based on realistic patterns, like traveling from home to a shop or from a school back home. These start and end points are real locations taken from our map data. Their behaviour is based on the flowchart model from the research paper **"A simulation model for public bike-sharing systems"[9]**.

A user's journey follows these steps:

1. Walk to the nearest station with an available bike.
2. Take a bike and cycle to the station nearest their destination.
3. Return the bike and walk to their final destination.

A trip is marked as failed if there are no bikes, the destination station is full, or if the user has to walk too far (based on a predefined threshold).

### Interactive Dashboard

The simulation includes a **[Streamlit][8]**-based dashboard that provides:

- Interactive parameter configuration (simulation duration, start time)
- POI and time weight adjustments
- Real-time simulation results
- Multiple visualization tabs:
  - Station data and hourly bike availability
  - Trip animations
  - Station availability animations
  - All trip paths
  - Route usage heatmaps
  - POI distribution
  - Console logs
  - Rebalancing route optimization with adjustable thresholds

### Visualization of results

The system generates several types of visualizations:

1. Interactive maps using **[Folium][5]** showing:
   - Complete trip paths (walking + cycling)
   - Hourly trip animations
   - Station availability over time
   - POI distribution
   - Optimized rebalancing routes with numbered stops and visit order

2. Static visualizations using **[Matplotlib][6]** and **[Contextily][7]**:
   - Route usage heatmaps
   - Hourly station activity heatmaps
   - Failed trips by hour

### Statistics and Analysis

The simulation tracks and analyzes:

- Success/failure rates for trips
- Station usage patterns
- Route popularity
- Hourly bike availability per station
- Optimal rebalancing routes based on station fill levels
- Failed trips by hour of day
- Station fill ratios and rebalancing needs

### Route Optimization

The system uses **[OpenRouteService][10]** for:
- Accurate cycling route calculations
- Travel time and distance matrices
- Vehicle routing optimization for bike rebalancing
- Interactive visualization of optimal rebalancing routes

### Libraries Used

The simulation leverages several powerful Python libraries:

- **[OpenRouteService-py][10]**: A Python client for the OpenRouteService API, providing:
  - Route optimization for bike rebalancing
  - Distance and duration matrices
  - Polyline decoding for route visualization
  - Support for multiple transport profiles

- **[Folium][5]**: Interactive map visualization library that:
  - Creates interactive HTML maps with Leaflet.js
  - Supports custom markers, popups, and tooltips
  - Enables time-based animations with TimestampedGeoJson
  - Provides layer controls for toggling different map elements

- **[SimPy][4]**: Discrete event simulation framework for:
  - Managing concurrent user journeys
  - Simulating time-based events
  - Handling resource allocation (bikes and docks)
  - Coordinating complex system interactions

- **[OSMnx][2]**: Street network analysis and visualization:
  - Downloads and processes OpenStreetMap data
  - Calculates optimal cycling routes
  - Provides network analysis capabilities
  - Caches network data for performance

- **[NetworkX][3]**: Graph theory and network analysis:
  - Computes shortest paths between stations
  - Analyzes network connectivity
  - Optimizes route calculations
  - Integrates with OSMnx for route planning

- **[Streamlit][8]**: Web application framework for:
  - Interactive parameter configuration
  - Real-time data visualization
  - Dynamic dashboard updates
  - User-friendly interface

- **[Matplotlib][6]** & **[Contextily][7]**: Static visualization tools for:
  - Creating heatmaps and statistical plots
  - Adding basemaps to visualizations
  - Generating publication-quality figures
  - Analyzing spatial patterns

### Data Sources & Attribution

- Neighborhood boundaries and geographic data: [Eindhoven Open Data](https://data.eindhoven.nl/pages/home/)

- [1] https://www.openstreetmap.org/ "OpenStreetMap Homepage"
- [2] https://osmnx.readthedocs.io/ "OSMnx Documentation"
- [3] https://networkx.org/ "NetworkX Documentation"
- [4] https://simpy.readthedocs.io/ "SimPy Documentation"
- [5] https://python-visualization.github.io/folium/ "Folium Documentation"
- [6] https://matplotlib.org/ "Matplotlib Homepage"
- [7] https://contextily.readthedocs.io/ "Contextily Documentation"
- [8] https://streamlit.io/ "Streamlit Homepage"
- [9] https://www.sciencedirect.com/science/article/pii/S2352146518302412 "Paper on behaviour of user agents in a bikesharing system"
- [10] https://openrouteservice.org/ "OpenRouteService Homepage"
