"""Small worker adapter. All physics and coordinate transforms live in magnetic_model."""

from dataclasses import asdict
from time import perf_counter

import numpy as np

from magnetic_model import Grid, OreBody, simulate
from magnetic_model.geomagnetic import NT_TO_T, survey_field_t
from magnetic_model.igrf import geographic_field
from magnetic_model.observables import total_field_anomaly_nt


def _field(inputs):
    start = perf_counter()
    field = geographic_field(inputs["latitude"], inputs["longitude"])
    return field, (perf_counter() - start) * 1000


def _elements(field, inputs):
    return dict(
        intensity_nt=field.total_nt,
        inclination_deg=field.inclination_deg,
        declination_deg=field.declination_deg if field.horizontal_nt else 0,
        azimuth_deg=inputs["azimuth"],
    )


def _field_metadata(field, inputs, igrf_ms):
    return dict(
        field={**asdict(field), "declination_deg": field.declination_deg if field.horizontal_nt else None},
        background=(survey_field_t(**_elements(field, inputs)) / NT_TO_T).tolist(),
        igrf_ms=igrf_ms,
    )


def field_result(inputs):
    field, elapsed = _field(inputs)
    return _field_metadata(field, inputs, elapsed)


def simulation_result(inputs):
    spacing = inputs["spacing"]
    half_count = round(800 / spacing)
    if not 5 <= spacing <= 25 or not np.isclose(half_count * spacing, 800, atol=1e-8, rtol=0):
        raise ValueError("Grid spacing must divide 800 m evenly and be between 5 and 25 m.")
    grid = Grid(spacing, half_count * 2, half_count, half_count)
    body = OreBody(inputs["width"], inputs["thickness"], inputs["depth"], inputs["susceptibility"])
    if min(body.width_m, body.thickness_m) < 3 * spacing:
        raise ValueError("Width and thickness must span at least three cells.")
    field, elapsed = _field(inputs)
    result = simulate(body, **_elements(field, inputs), grid=grid,
                      observation_height_m=inputs["height"])
    metadata = _field_metadata(field, inputs, elapsed)
    metadata.update(diagnostics=asdict(result.diagnostics), shape=list(result.potential_a.shape))
    return metadata, {
        "x": result.x_m,
        "z": result.z_m,
        "profile": result.profile_total_anomaly_nt,
        "vertical": np.ascontiguousarray(result.anomaly_nt[..., 2]).ravel(),
        "total": total_field_anomaly_nt(result.anomaly_nt, result.background_nt).ravel(),
    }
