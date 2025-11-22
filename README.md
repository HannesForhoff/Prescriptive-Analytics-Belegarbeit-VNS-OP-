# Variable Neighborhood Search (VNS) for Orienteering Problem

This project implements a Variable Neighborhood Search (VNS) metaheuristic to solve a variant of the Orienteering Problem (OP).
The goal is to construct a tour that maximizes collected score while respecting a global time limit.

# Core Features
Multiple constructive heuristics for generating diverse start solutions
(e.g., greedy, best insertion) 

Adaptive shaking operators and local search strategies
to escape local optima and intensify promising regions of the solution space 

A solution pool that maintains diverse and high-quality candidates
to support effective restarts 

Automatic validity checks and scoring for every constructed tour
via the TourSolution class 




# Project Structure

InputData.py	              Loads JSON instances, creates nodes, computes distance matrix. 

ConstructiveHeuristic.py	  Framework + multiple heuristics for building start tours. 

Neighborhood.py	            Shaking + local search operators used in VNS. 

OutputData.py	              Representation and evaluation of solutions. 

StartSolutionSelector.py	  Chooses the best initial solution from several heuristics. 

VNS.py	                    Full implementation of the Variable Neighborhood Search including solution pool and restarts. 

# How does it work ?
Load instance via InputData.
Generate start solution using one or multiple heuristics.
Run VNS:
  Shake the current solution (diversification)
  Apply local search (intensification)
  Update the global best and solution pool
  Restart intelligently when stagnating
Return best found tour under the time limit.

# Use Case
This project was developed as part of a university assignment to compare constructive heuristics and design an effective VNS framework for NP-hard routing problems.


