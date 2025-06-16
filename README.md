# Simulation overview

We're creating a digital model of a bike-sharing system for specific neighbourhoods in Eindhoven.
Our main goal is to **test and visualize the system's performance before building it in real life** and to serve as a **proof of concept** for a tool that could be used in real-time operations.

The key questions it helps answer are:

- Are the stations placed correctly?
- How often do trips fail due to no available bikes?
- How often do trips fail because a station is full?
- What are the most common travel routes?
- How does bike availability change throughout the day?
- What is the optimal route for rebalancing bikes between stations?

## Implementation

### Setup

The simulation is built in Python. To calculate travel routes, we use the **[OSMnx][2]** library to download the bike-friendly street network from **[OpenStreetMap][1]**. This network is saved locally so it loads quickly on future runs. Before the simulation starts, the system calculates the fastest cycling route between every pair of stations using **[NetworkX][3]**. This pre-calculation makes the simulation run much faster.

### User agents

Users in our simulation are managed by **[SimPy][4]**, a library for running event-based simulations. New users are created over time based on realistic patterns, like traveling from home to a shop or from a school back home. These start and end points are real locations taken from our map data.

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
  - Rebalancing route optimization

### Visualization of results

The system generates several types of visualizations:

1. Interactive maps using **[Folium][5]** showing:
   - Complete trip paths (walking + cycling)
   - Hourly trip animations
   - Station availability over time
   - POI distribution
   - Optimized rebalancing routes

2. Static visualizations using **[Matplotlib][6]** and **[Contextily][7]**:
   - Route usage heatmaps
   - Hourly station activity heatmaps

### Statistics and Analysis

The simulation tracks and analyzes:

- Success/failure rates for trips
- Station usage patterns
- Route popularity
- Hourly bike availability per station
- Optimal rebalancing routes based on station fill levels

[1]: https://www.openstreetmap.org/ "OpenStreetMap Homepage"
[2]: https://osmnx.readthedocs.io/ "OSMnx Documentation"
[3]: https://networkx.org/ "NetworkX Documentation"
[4]: https://simpy.readthedocs.io/ "SimPy Documentation"
[5]: https://python-visualization.github.io/folium/ "Folium Documentation"
[6]: https://matplotlib.org/ "Matplotlib Homepage"
[7]: https://contextily.readthedocs.io/ "Contextily Documentation"
[8]: https://streamlit.io/ "Streamlit Homepage"
