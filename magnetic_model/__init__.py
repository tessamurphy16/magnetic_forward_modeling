"""Standalone 2D magnetostatic forward modeling."""

from .geometry import Grid, OreBody
from .simulation import SimulationResult, SolverDiagnostics, simulate

__all__ = ["Grid", "OreBody", "SimulationResult", "SolverDiagnostics", "simulate"]
