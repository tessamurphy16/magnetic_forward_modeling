"""Cell-centered grid and rectangular permeability model."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Grid:
    """Square cells with a face at z=0, x centered on zero, and z positive down."""

    spacing_m: float = 10.0
    nx: int = 120
    nz_air: int = 40
    nz_ground: int = 80

    def __post_init__(self):
        if not np.isfinite(self.spacing_m) or self.spacing_m <= 0:
            raise ValueError("Grid spacing must be finite and positive.")
        for count in (self.nx, self.nz_air, self.nz_ground):
            if isinstance(count, bool) or not isinstance(count, (int, np.integer)) or count < 2:
                raise ValueError("Each grid cell count must be an integer of at least two.")

    @property
    def x_faces_m(self):
        return (np.arange(self.nx + 1) - self.nx / 2) * self.spacing_m

    @property
    def z_faces_m(self):
        return (np.arange(self.nz_air + self.nz_ground + 1) - self.nz_air) * self.spacing_m


@dataclass(frozen=True)
class OreBody:
    """A rectangle centered on x=0 with dimensionless SI susceptibility contrast."""

    width_m: float
    thickness_m: float
    depth_to_top_m: float
    susceptibility: float

    def __post_init__(self):
        values = (self.width_m, self.thickness_m, self.depth_to_top_m, self.susceptibility)
        if not all(np.isfinite(values)):
            raise ValueError("Ore-body inputs must be finite.")
        if self.width_m <= 0 or self.thickness_m <= 0 or self.depth_to_top_m < 0:
            raise ValueError("Width and thickness must be positive and depth nonnegative.")
        if self.susceptibility <= -1:
            raise ValueError("Relative permeability must be positive.")


def cell_centers(faces):
    return (faces[:-1] + faces[1:]) / 2


def rectangular_model(grid, body):
    """Return cell permeability and the represented (left, right, top, bottom) bounds."""
    x_faces, z_faces = grid.x_faces_m, grid.z_faces_m
    x, z = cell_centers(x_faces), cell_centers(z_faces)
    half_width = body.width_m / 2
    bottom = body.depth_to_top_m + body.thickness_m
    if half_width >= x_faces[-1] or bottom >= z_faces[-1]:
        raise ValueError("The ore body must fit inside the domain with lateral and bottom padding.")

    columns = np.flatnonzero(np.abs(x) <= half_width)
    rows = np.flatnonzero((z >= body.depth_to_top_m) & (z < bottom))
    if columns.size == 0 or rows.size == 0:
        raise ValueError("The ore body contains no cell centers. Use a finer grid.")
    if columns[0] == 0 or columns[-1] == x.size - 1 or rows[-1] == z.size - 1:
        raise ValueError("Leave at least one host cell between the ore body and outer boundaries.")

    permeability = np.ones((z.size, x.size))
    permeability[np.ix_(rows, columns)] = 1 + body.susceptibility
    bounds = (
        float(x_faces[columns[0]]), float(x_faces[columns[-1] + 1]),
        float(z_faces[rows[0]]), float(z_faces[rows[-1] + 1]),
    )
    return permeability, bounds
