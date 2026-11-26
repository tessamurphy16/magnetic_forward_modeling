import numpy as np
import pytest

from magnetic_model import Grid, OreBody, simulate
from magnetic_model.geomagnetic import survey_field_t
from magnetic_model.solver import solve_potential


GRID = Grid(spacing_m=5.0, nx=48, nz_air=24, nz_ground=40)
BODY = OreBody(width_m=60, thickness_m=30, depth_to_top_m=20, susceptibility=0.25)


def run(body=BODY, *, inclination=55, declination=20, azimuth=0, height=0):
    return simulate(
        body, grid=GRID, intensity_nt=50_000, inclination_deg=inclination,
        declination_deg=declination, azimuth_deg=azimuth, observation_height_m=height,
    )


@pytest.mark.parametrize("inclination, declination", [(0, 0), (55, 20), (-35, 127)])
def test_zero_susceptibility(inclination, declination):
    result = run(OreBody(60, 30, 20, 0), inclination=inclination, declination=declination)
    for values in (result.potential_a, result.anomaly_nt, result.profile_total_anomaly_nt):
        np.testing.assert_array_equal(values, np.zeros_like(values))
    np.testing.assert_array_equal(
        result.induction_nt, np.broadcast_to(result.background_nt, result.induction_nt.shape),
    )
    assert result.diagnostics.relative_residual_l2 == 0


def test_residual_and_flux_conservation():
    result = run()
    diagnostics = result.diagnostics
    assert diagnostics.residual_l2_am2 < 1e-10
    assert diagnostics.relative_residual_l2 < 1e-11
    assert diagnostics.max_flux_divergence_nt_per_m < 1e-8
    assert diagnostics.body_bounds_m == (-30, 30, 20, 50)
    assert np.max(np.abs(result.profile_total_anomaly_nt)) > 100

    # Check the interface flux directly from the adjacent cell potentials.
    row = np.flatnonzero(result.z_m > 20)[0]
    col = np.flatnonzero(result.x_m > 0)[0]
    mu_above, mu_below = result.relative_permeability[row - 1:row + 1, col]
    assert (mu_above, mu_below) == (1, 1.25)
    mu_face = 2 / (1 / mu_above + 1 / mu_below)
    gradient = np.diff(result.potential_a[row - 1:row + 1, col])[0] / GRID.spacing_m
    expected_nt = (mu_face - 1) * result.background_nt[2] - mu_face * 1.25663706127e3 * gradient
    assert result.anomaly_z_faces_nt[row, col] == pytest.approx(expected_nt)


@pytest.mark.parametrize(
    "inclination, declination, azimuth, expected_t",
    [(0, 0, 0, [5e-5, 0, 0]), (0, 0, 90, [0, -5e-5, 0]),
     (0, 90, 90, [5e-5, 0, 0]), (-30, 90, 0, [0, np.sqrt(3) * 2.5e-5, -2.5e-5]),
     (90, 123, 74, [0, 0, 5e-5])],
)
def test_field_rotation_and_nt_to_t(inclination, declination, azimuth, expected_t):
    np.testing.assert_allclose(
        survey_field_t(50_000, inclination, declination, azimuth), expected_t,
        rtol=0, atol=1e-19,
    )


def test_pure_strike_induction():
    result = run(inclination=0, declination=90)
    np.testing.assert_allclose(result.potential_a, 0, atol=1e-12)
    np.testing.assert_allclose(result.profile_total_anomaly_nt, 0, atol=1e-12)
    body_mask = result.relative_permeability > 1
    np.testing.assert_allclose(result.anomaly_nt[body_mask, 1], 12_500)
    np.testing.assert_array_equal(result.anomaly_nt[~body_mask, 1], 0)


def test_vertical_field_symmetry():
    result = run(inclination=90)
    np.testing.assert_allclose(result.potential_a, result.potential_a[:, ::-1], atol=1e-12)
    profile = result.profile_vector_anomaly_nt
    np.testing.assert_allclose(profile[:, 0], -profile[::-1, 0], atol=1e-9)
    np.testing.assert_allclose(profile[:, 2], profile[::-1, 2], atol=1e-9)
    np.testing.assert_allclose(
        result.profile_total_anomaly_nt, result.profile_total_anomaly_nt[::-1], atol=1e-9,
    )


def test_air_sampling_and_exact_total_field():
    ground = run()
    raised = run(height=12.5)
    row = np.flatnonzero(ground.z_faces_m == 0)[0]
    np.testing.assert_array_equal(
        ground.profile_vector_anomaly_nt[:, 2], ground.anomaly_z_faces_nt[row],
    )
    delta = raised.profile_vector_anomaly_nt
    np.testing.assert_array_equal(delta[:, 1], 0)
    air_center = np.flatnonzero(raised.z_m == -12.5)[0]
    np.testing.assert_allclose(delta[:, 0], raised.anomaly_nt[air_center, :, 0])
    np.testing.assert_allclose(delta[:, 2], raised.anomaly_nt[air_center, :, 2])
    expected = np.linalg.norm(raised.background_nt + delta, axis=1) - 50_000
    np.testing.assert_allclose(raised.profile_total_anomaly_nt, expected, atol=2e-11)
    assert np.max(np.abs(expected)) < np.max(np.abs(ground.profile_total_anomaly_nt))

    # Omitting strike from both norms would change this oblique-field result.
    in_plane = raised.background_nt[[0, 2]]
    projected = np.linalg.norm(in_plane + delta[:, [0, 2]], axis=1) - np.linalg.norm(in_plane)
    assert np.max(np.abs(expected - projected)) > 1


def test_cylinder_exterior_potential():
    spacing = 2.0
    centers = (np.arange(160) + 0.5) * spacing - 160
    x, z = np.meshgrid(centers, centers)
    radius_squared = x**2 + z**2
    permeability = np.where(radius_squared <= 20**2, 1.5, 1)
    potential, *_ = solve_potential(permeability, spacing, (30, 0))
    ring = (radius_squared >= 30**2) & (radius_squared <= 60**2)
    analytic = ((1.5 - 1) / (1.5 + 1)) * 20**2 * 30 * x[ring] / radius_squared[ring]
    relative_l2 = np.linalg.norm(potential[ring] - analytic) / np.linalg.norm(analytic)
    # Finite-box Dirichlet boundaries and stair-stepped geometry both contribute.
    assert relative_l2 < 0.08


def test_invalid_geometry_and_height():
    with pytest.raises(ValueError, match="top of the air grid"):
        run(height=120)
    with pytest.raises(ValueError, match="no cell centers"):
        run(OreBody(1, 1, 1, 0.25))
    with pytest.raises(ValueError, match="positive"):
        OreBody(60, 30, 20, -1)


def test_nonzero_dirichlet_values_reproduce_affine_potential():
    spacing = 2.0
    x = spacing * (np.arange(8) + 0.5)
    z = spacing * (np.arange(5) + 0.5)

    def affine(x_m, z_m):
        return 3 + 2 * x_m - 4 * z_m

    boundary = (affine(0, z), affine(16, z), affine(x, 0), affine(x, 10))
    potential, flux_x, flux_z, _, relative = solve_potential(
        np.ones((z.size, x.size)), spacing, (0, 0), boundary_a=boundary,
    )
    np.testing.assert_allclose(potential, affine(x[None, :], z[:, None]), atol=1e-12)
    np.testing.assert_allclose(flux_x, -2, atol=1e-12)
    np.testing.assert_allclose(flux_z, 4, atol=1e-12)
    assert relative < 1e-12
