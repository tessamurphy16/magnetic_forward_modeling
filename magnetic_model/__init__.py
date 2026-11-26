"""Standalone 2D magnetostatic forward modeling."""

from .geometry import Grid, OreBody
from .simulation import SimulationResult, SolverDiagnostics, simulate, simulate_at_location

__all__ = ["Grid", "OreBody", "SimulationResult", "SolverDiagnostics", "simulate", "simulate_at_location"]
