from dataclasses import astuple

import numpy as np
import pytest

from magnetic_model import Grid, OreBody, simulate_at_location
from magnetic_model.geomagnetic import NT_TO_T, survey_field_t
from magnetic_model.igrf import geographic_field


# NOAA/CIRES geomaglib references at 2026.0 and 0 km. See docs/igrf-14.md.
@pytest.mark.parametrize("lat, lon, reference", [
    (39.7, -105.0, (20715.692176, 2747.165628, 46589.419363, 65.842026778,
                   7.554076280, 51061.343675, 20897.052934)),
    (59.45, -135.31, (13790.549447, 4434.456195, 53672.512652, 74.895993951,
                     17.825589983, 55593.005587, 14485.981354)),
    (1.35, 103.82, (41037.780206, 156.787207, -9348.797200, -12.833417711,
                   0.218900766, 42089.476067, 41038.079713)),
    (-31.95, 115.86, (23929.707853, -637.355313, -53333.494807, -65.827559855,
                     -1.525682563, 58459.377417, 23938.194162)),
])
def test_noaa_reference(lat, lon, reference):
    actual = np.asarray(astuple(geographic_field(lat, lon)))
    reference = np.asarray(reference)
    fields = [0, 1, 2, 5, 6]
    np.testing.assert_allclose(actual[fields], reference[fields], rtol=0, atol=5e-4)
    np.testing.assert_allclose(actual[3:5], reference[3:5], rtol=0, atol=1e-6)


def test_field_elements_and_rotation():
    field = geographic_field(-31.95, 115.86)
    north, east, down = field.north_nt, field.east_nt, field.down_nt
    assert field.horizontal_nt == pytest.approx(np.linalg.norm([north, east]))
    assert field.total_nt == pytest.approx(np.linalg.norm([north, east, down]))
    assert field.inclination_deg == pytest.approx(np.rad2deg(np.arctan2(down, field.horizontal_nt)))
    assert field.declination_deg == pytest.approx(np.rad2deg(np.arctan2(east, north)))
    for azimuth, expected in [(0, [north, east, down]), (90, [east, -north, down]),
                              (360, [north, east, down])]:
        rotated = survey_field_t(field.total_nt, field.inclination_deg,
                                 field.declination_deg, azimuth)
        np.testing.assert_allclose(rotated / NT_TO_T, expected, rtol=0, atol=1e-10)


def test_longitude_wrap():
    assert geographic_field(20, -180) == geographic_field(20, 180)
    assert geographic_field(20, -105) == geographic_field(20, 255)


@pytest.mark.parametrize("sign", [-1, 1])
def test_pole_limits(sign):
    pole = geographic_field(sign * 90, 45)
    near = geographic_field(sign * 89.99999, 45)
    shifted = geographic_field(sign * 90, 135)
    assert np.isfinite(astuple(pole)).all()
    assert sign * pole.down_nt > 0
    np.testing.assert_allclose(astuple(pole), astuple(near), rtol=0, atol=0.02)
    assert shifted.total_nt == pytest.approx(pole.total_nt, abs=0.002)
    assert shifted.north_nt == pytest.approx(-sign * pole.east_nt, abs=0.002)
    assert shifted.east_nt == pytest.approx(sign * pole.north_nt, abs=0.002)


@pytest.mark.parametrize("latitude, longitude", [(90.1, 0), (float("nan"), 0), (0, float("inf"))])
def test_invalid_coordinates(latitude, longitude):
    with pytest.raises(ValueError):
        geographic_field(latitude, longitude)


def test_geographic_simulation_retains_strike_component():
    field = geographic_field(39.7, -105)
    model = simulate_at_location(
        OreBody(80, 40, 40, 0.1), latitude_deg=39.7, longitude_deg=-105,
        azimuth_deg=80, grid=Grid(10, 64, 32, 32), observation_height_m=10,
    )
    assert abs(model.background_nt[1]) > 1000
    vectors = model.background_nt + model.profile_vector_anomaly_nt
    np.testing.assert_allclose(
        model.profile_total_anomaly_nt, np.linalg.norm(vectors, axis=1) - field.total_nt,
        rtol=0, atol=2e-11,
    )
