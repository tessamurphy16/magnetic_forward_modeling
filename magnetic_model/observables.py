"""Reconstruct magnetic induction and sample an observation line in air."""

import numpy as np


def _sample_rows(values, coordinates, target):
    # At the top and bottom half-cell of the air region, use the nearest
    # two air centers for a one-sided linear reconstruction.
    upper = np.clip(np.searchsorted(coordinates, target), 1, coordinates.size - 1)
    lower = upper - 1
    weight = (target - coordinates[lower]) / (coordinates[upper] - coordinates[lower])
    return (1 - weight) * values[lower] + weight * values[upper]


def air_profile(delta_bx_nt, delta_bz_faces_nt, background_nt, z_m, z_faces_m, height_m):
    """Return vector and exact total-field anomalies (nT) at z = -height."""
    air = z_m < 0
    bx = _sample_rows(delta_bx_nt[air], z_m[air], -height_m)
    bz = _sample_rows(delta_bz_faces_nt[z_faces_m <= 0], z_faces_m[z_faces_m <= 0], -height_m)
    delta = np.stack((bx, np.zeros_like(bx), bz), axis=-1)
    return delta, total_field_anomaly_nt(delta, background_nt)


def total_field_anomaly_nt(delta, background_nt):
    """Return the exact magnitude difference for vectors on the last axis, in nT."""
    # Rationalize |B0 + dB| - |B0| to preserve precision for small anomalies.
    total = np.sum(delta * (2 * background_nt + delta), axis=-1)
    total /= np.linalg.norm(background_nt + delta, axis=-1) + np.linalg.norm(background_nt)
    return total
