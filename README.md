# 2D magnetic forward modeling

A numerical PDE course project for exploring how buried magnetic bodies affect surface survey measurements. The planned browser app will use an interactive globe and IGRF to set the inducing field, then compute a 2D anomaly heatmap and a surface total-field anomaly profile in nT.

The standalone NumPy/SciPy solver accepts local IGRF field elements supplied by the caller. Geographic IGRF evaluation, the browser interface, the executed verification notebook, and the Pages workflow are future milestones.

## Run the solver and tests

From the repository root with Python 3.12:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

`requirements.txt` pins the solver dependencies. From the same directory, run a model with:

```python
from magnetic_model import Grid, OreBody, simulate

result = simulate(
    OreBody(width_m=80, thickness_m=40, depth_to_top_m=40, susceptibility=0.1),
    grid=Grid(spacing_m=5, nx=128, nz_air=64, nz_ground=64),
    intensity_nt=50_000,
    inclination_deg=60,
    declination_deg=20,
    azimuth_deg=0,
    observation_height_m=10,
)
print(result.diagnostics)
heatmap_nt = result.anomaly_nt[:, :, 2]
profile_nt = result.profile_total_anomaly_nt
```

The example field elements are illustrative. Enter intensity in nT and angles in degrees, with inclination positive down and declination and survey azimuth clockwise from true north. The grid uses square cells and depth increases downward. Height is measured upward from the surface. Zero height samples the air side at ground level. The exact profile uses the full three-component inducing field.

Potential is in A. Scalar arrays are indexed by depth then distance, and magnetic induction vectors end in survey, strike, and down components. The result also provides cell and face coordinates in m, face-normal anomalies in nT, represented ore-body bounds, and linear and flux-balance residuals. Ore-body geometry is assigned by cell centers, so the represented bounds can differ from the requested dimensions.

## Numerical checks

For the rectangular case above, sampling 21 profile points from −100 to 100 m on a fixed 640 m × 640 m domain gave RMS differences of 1.76 nT and 0.36 nT for 10 m and 5 m spacing, respectively, relative to a 2.5 m grid. At 5 m spacing, doubling the domain dimensions changed that profile by 14.50 nT RMS. Enlarge the domain at fixed spacing until boundary effects are small enough for the survey, then check grid refinement separately.

A 2 m grid reproduced the analytic exterior potential of a 20 m radius cylinder to 6.56% relative L2 error over the annulus from 30 to 60 m in a 320 m × 320 m domain. This comparison includes the effects of the finite zero-potential boundary and the stair-stepped cylinder.


## Repository layout

| Path | Role |
| --- | --- |
| `magnetic_model/` | Shared Python package for geomagnetism, model geometry, the PDE, and survey observables |
| `web/` | Static HTML, CSS, JavaScript, and a dedicated Pyodide worker |
| `web/vendor/` | Staging location for browser runtime assets assembled by the Pages build |
| `notebooks/` | Executed numerical verification notebook importing the shared Python package |
| `tests/` | Native Python tests and browser smoke checks |
| `.github/workflows/` | Future validation and GitHub Pages deployment workflows |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Physics, numerical verification, interface, and delivery milestones |
| [AGENTS.md](AGENTS.md) | Repository conventions for contributors and coding agents |
| [AI_USE.md](AI_USE.md) | AI-use statement |

The model assumes infinite extent along strike, linear isotropic susceptibility, and zero remanent magnetization. The globe sets the local main field. The PDE models a local vertical cross-section with that field held uniform across the domain.
