"""Standalone user-facing magnetic forward model."""

from dataclasses import dataclass

import numpy as np

from .geomagnetic import MU_0, NT_TO_T, survey_field_t
from .geometry import Grid, OreBody, cell_centers, rectangular_model
from .observables import air_profile
from .solver import solve_potential


@dataclass(frozen=True)
class SolverDiagnostics:
    residual_l2_am2: float
    relative_residual_l2: float
    max_flux_divergence_nt_per_m: float
    body_bounds_m: tuple[float, float, float, float]
    spacing_m: float


@dataclass(frozen=True)
class SimulationResult:
    """Scalar grids use [z, x]. Magnetic induction vectors end in (x, strike, z)."""

    x_m: np.ndarray
    z_m: np.ndarray
    x_faces_m: np.ndarray
    z_faces_m: np.ndarray
    observation_height_m: float
    relative_permeability: np.ndarray
    potential_a: np.ndarray
    background_nt: np.ndarray
    induction_nt: np.ndarray
    anomaly_nt: np.ndarray
    anomaly_x_faces_nt: np.ndarray
    anomaly_z_faces_nt: np.ndarray
    profile_vector_anomaly_nt: np.ndarray
    profile_total_anomaly_nt: np.ndarray
    diagnostics: SolverDiagnostics


def simulate(
    body: OreBody,
    *,
    intensity_nt: float,
    inclination_deg: float,
    declination_deg: float,
    azimuth_deg: float,
    observation_height_m: float = 0.0,
    grid: Grid = Grid(),
) -> SimulationResult:
    """Solve using supplied IGRF elements and sample at the given height above ground."""
    x_faces, z_faces = grid.x_faces_m, grid.z_faces_m
    if not np.isfinite(observation_height_m) or not 0 <= observation_height_m < -z_faces[0]:
        raise ValueError("Observation height must be nonnegative and below the top of the air grid.")
    x, z = cell_centers(x_faces), cell_centers(z_faces)
    permeability, bounds = rectangular_model(grid, body)
    background_t = survey_field_t(intensity_nt, inclination_deg, declination_deg, azimuth_deg)
    potential, flux_x, flux_z, residual, relative = solve_potential(
        permeability, grid.spacing_m, background_t[[0, 2]] / MU_0,
    )

    background = background_t / NT_TO_T
    bx_faces = flux_x * (MU_0 / NT_TO_T)
    bz_faces = flux_z * (MU_0 / NT_TO_T)
    bx = (bx_faces[:, :-1] + bx_faces[:, 1:]) / 2
    bz = (bz_faces[:-1] + bz_faces[1:]) / 2
    bs = (permeability - 1) * background[1]
    anomaly = np.stack((bx, bs, bz), axis=-1)
    profile_vector, profile_total = air_profile(
        bx, bz_faces, background, z, z_faces, observation_height_m,
    )
    divergence = (np.diff(bx_faces, axis=1) + np.diff(bz_faces, axis=0)) / grid.spacing_m
    diagnostics = SolverDiagnostics(
        residual, relative, float(np.max(np.abs(divergence))), bounds, grid.spacing_m,
    )
    return SimulationResult(
        x, z, x_faces, z_faces, observation_height_m, permeability, potential,
        background, background + anomaly, anomaly, bx_faces, bz_faces,
        profile_vector, profile_total, diagnostics,
    )
