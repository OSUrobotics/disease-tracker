# disease-tracker
This package models the two-dimensional spread of bacteria, viruses, or other contaminated particles around a room and calculates an optimal path for a cleaning robot to take based on that model. It consists of two components which can function separately.

The tracking component models the spread of contamination around a room by tracking the movement of people in the room. As people interact with contaminated areas in the environment they pick up some contamination. They then spread it around the room as they move until all contaminated particles are deposited. The current model assumes particles are spread around the room evenly as the person moves around until all picked-up particles are distributed. The amount of contamination transferred from an infected area to a person and vice versa are parameters.

The cleaning component models removal of the contamination with a cleaning robot. It takes in a map of a contaminated room created either through the above process or during initialization in the YAML input file, and tries to find the best path to clean the room based on modeled contamination levels and the estimated power of the cleaning robot. 

See here for additional information: https://secure.engr.oregonstate.edu/wiki/robotics/index.php/Main/DiseaseTracking
