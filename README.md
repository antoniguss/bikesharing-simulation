# Simulation overview
We're creating a digital model of a bike-sharing system for specific neighbourhoods in Eindhoven
Our main goal is to **test and visualize the system's performance before buliding it in real life** as well as serve as a **proof of concept** of a resource that our startup could use for their real time operations.

The key questions it helps to answer are:
- Are the stations placed in the right locations?
- How often do trips fail because there are no bikes available?
- How often do trips fail because a station is full?
- What are the common travle patters of users?

## Implementation
### Setup
We use Python as a language alongside a number of libraries and resources that will be described in this section.
The simulation starts by using a real map of Eindhoven, obtained from OpenStreeMap [1] by using the OSMNX Python library

