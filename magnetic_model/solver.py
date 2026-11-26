"""Conservative finite differences for anomalous magnetostatic potential."""

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve


def _face_permeability(permeability):
    def harmonic(left, right):
        lower = np.minimum(left, right)
        upper = np.maximum(left, right)
        return lower / (0.5 + 0.5 * lower / upper)

    nz, nx = permeability.shape
    mu_x = np.empty((nz, nx + 1))
    mu_z = np.empty((nz + 1, nx))
    mu_x[:, 1:-1] = harmonic(permeability[:, :-1], permeability[:, 1:])
    mu_z[1:-1] = harmonic(permeability[:-1], permeability[1:])
    mu_x[:, 0], mu_x[:, -1] = permeability[:, 0], permeability[:, -1]
    mu_z[0], mu_z[-1] = permeability[0], permeability[-1]
    return mu_x, mu_z


def solve_potential(permeability, spacing_m, h0_xz_am, *, boundary_a=None):
    """Return phi_a in A, anomalous B/mu_0 on x and z faces, and residuals.

    Inputs are cell permeability indexed [z, x], square cell spacing in m,
    and the uniform in-plane inducing field (Hx, Hz) in A/m. Optional
    Dirichlet values (A) are supplied as (left, right, top, bottom) at
    boundary face centers, with each edge a scalar or a one-dimensional
    array in increasing coordinate order. The default is zero on all edges.
    """
    permeability = np.asarray(permeability, dtype=float)
    if permeability.ndim != 2 or not permeability.size:
        raise ValueError("Permeability must be a nonempty 2D array.")
    if not np.isfinite(permeability).all() or np.any(permeability <= 0):
        raise ValueError("Permeability must be finite and positive.")
    if not np.isfinite(spacing_m) or spacing_m <= 0:
        raise ValueError("Spacing must be finite and positive.")
    field = np.asarray(h0_xz_am, dtype=float)
    if field.shape != (2,) or not np.isfinite(field).all():
        raise ValueError("The inducing field must contain two finite components.")

    nz, nx = permeability.shape
    if boundary_a is None:
        boundary_a = (0, 0, 0, 0)
    try:
        wall_left, wall_right, wall_top, wall_bottom = (
            np.broadcast_to(np.asarray(wall, dtype=float), (length,))
            for wall, length in zip(boundary_a, (nz, nz, nx, nx), strict=True)
        )
    except (ValueError, TypeError) as exc:
        raise ValueError("Supply Dirichlet values for left, right, top, and bottom edges.") from exc
    if not all(np.isfinite(wall).all() for wall in (wall_left, wall_right, wall_top, wall_bottom)):
        raise ValueError("Dirichlet values must be finite.")

    mu_x, mu_z = _face_permeability(permeability)
    inv_spacing = 1 / spacing_m
    wx, wz = mu_x * inv_spacing**2, mu_z * inv_spacing**2

    # Assemble -div(mu_r grad(phi_a)). Each shared face couples two cells
    # with equal negative off-diagonals and adds its weight to both diagonals.
    # Each wall is half a cell away, doubling its diagonal weight.
    diagonal = wx[:, :-1] + wx[:, 1:] + wz[:-1] + wz[1:]
    diagonal[:, 0] += wx[:, 0]
    diagonal[:, -1] += wx[:, -1]
    diagonal[0] += wz[0]
    diagonal[-1] += wz[-1]
    indices = np.arange(permeability.size).reshape(permeability.shape)
    left, right = indices[:, :-1].ravel(), indices[:, 1:].ravel()
    upper, lower = indices[:-1].ravel(), indices[1:].ravel()
    matrix = coo_matrix((
        np.concatenate((diagonal.ravel(), -wx[:, 1:-1].ravel(), -wx[:, 1:-1].ravel(),
                        -wz[1:-1].ravel(), -wz[1:-1].ravel())),
        (np.concatenate((indices.ravel(), left, right, upper, lower)),
         np.concatenate((indices.ravel(), right, left, lower, upper))),
    ), shape=(indices.size, indices.size)).tocsr()

    # grad(phi_0) = -H0, so the right side of the positive system is
    # -div(mu_r H0). Subtracting the uniform background from face fluxes
    # leaves their divergence unchanged and gives exact zeros for mu_r = 1.
    hx, hz = field
    flux_x = (mu_x - 1) * hx
    flux_z = (mu_z - 1) * hz
    rhs = -(np.diff(flux_x, axis=1) + np.diff(flux_z, axis=0)) * inv_spacing
    # Move the known wall contribution to the right side.
    rhs[:, 0] += 2 * wx[:, 0] * wall_left
    rhs[:, -1] += 2 * wx[:, -1] * wall_right
    rhs[0] += 2 * wz[0] * wall_top
    rhs[-1] += 2 * wz[-1] * wall_bottom
    rhs = rhs.ravel()
    values = spsolve(matrix, rhs)
    if not np.isfinite(values).all():
        raise RuntimeError("The sparse solve returned nonfinite potential values.")
    residual = np.linalg.norm(matrix @ values - rhs)
    rhs_norm = np.linalg.norm(rhs)
    potential = values.reshape(permeability.shape)

    # Reuse the assembly's harmonic face coefficients and half-cell wall
    # gradients so the reconstructed normal induction obeys the same balance.
    flux_x[:, 1:-1] -= mu_x[:, 1:-1] * np.diff(potential, axis=1) * inv_spacing
    flux_x[:, 0] -= mu_x[:, 0] * (potential[:, 0] - wall_left) * (2 * inv_spacing)
    flux_x[:, -1] += mu_x[:, -1] * (potential[:, -1] - wall_right) * (2 * inv_spacing)
    flux_z[1:-1] -= mu_z[1:-1] * np.diff(potential, axis=0) * inv_spacing
    flux_z[0] -= mu_z[0] * (potential[0] - wall_top) * (2 * inv_spacing)
    flux_z[-1] += mu_z[-1] * (potential[-1] - wall_bottom) * (2 * inv_spacing)
    return potential, flux_x, flux_z, float(residual), float(residual / rhs_norm if rhs_norm else 0)
