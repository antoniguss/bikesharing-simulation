# Simulation overview
We're creating a digital model of a bike-sharing system for specific neighbourhoods in Eindhoven.
Our main goal is to **test and visualize the system's performance before building it in real life** and to serve as a **proof of concept** for a tool that could be used in real-time operations.

The key questions it helps answer are:
- Are the stations placed correctly?
- How often do trips fail due to no available bikes?
- How often do trips fail because a station is full?
- What are the most common travel routes?

## Implementation
### Setup
The simulation is built in Python. To calculate travel routes, we use the **[OSMnx][2]** library to download the bike-friendly street network from **[OpenStreetMap][1]**. This network is saved locally so it loads quickly on future runs. Before the simulation starts, the system calculates the fastest cycling route between every pair of stations using **[NetworkX][3]**. This pre-calculation makes the simulation run much faster.

### User agents
Users in our simulation are managed by **[SimPy][4]**, a library for running event-based simulations. New users are created over time based on realistic patterns, like traveling from home to a shop or from a school back home. These start and end points are real locations taken from our map data.

A user's journey follows these steps:
1.  Walk to the nearest station with an available bike.
2.  Take a bike and cycle to the station nearest their destination.
3.  Return the bike and walk to their final destination.

A trip is marked as failed if there are no bikes, the destination station is full, or if the user has to walk too far (based on a predefined threshold).

### Visualization of results
After the simulation runs, we create two maps to understand the results.

First, we can generate an interactive map using **[Folium][5]** that shows the specific path of every single successful trip. This includes the user's walk to the station, the bike ride, and their final walk to the destination. This helps us see the complete door-to-door journey for our users.

Second, we create a heatmap image using **[Matplotlib][6]** and **[Contextily][7]**. On this map:
-   **Routes** are drawn with transparency, so more frequently used routes appear darker and thicker.
-   **Stations** are shown as circles where the size depends on how busy the station was.

### Statistics
The simulation tracks key data to measure performance. After it finishes, we analyze:
-   The final count of successful vs. failed trips, giving us a system success rate.
-   The usage count for each station, which helps identify "hotspots" (busy stations) and "coldspots" (ignored stations).
-   The usage count for each route, showing the most important travel corridors between stations.


# Resources
[1]: https://www.openstreetmap.org/ "OpenStreetMap Homepage"
[2]: https://osmnx.readthedocs.io/ "OSMnx Documentation"
[3]: https://networkx.org/ "NetworkX Documentation"
[4]: https://simpy.readthedocs.io/ "SimPy Documentation"
[5]: https://python-visualization.github.io/folium/ "Folium Documentation"
[6]: https://matplotlib.org/ "Matplotlib Homepage"
[7]: https://contextily.readthedocs.io/ "Contextily Documentation"
