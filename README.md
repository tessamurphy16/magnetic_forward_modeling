# 2D magnetic forward modeling

A numerical PDE course project for exploring how buried magnetic bodies affect surface survey measurements. The planned browser app will use an interactive globe and IGRF to set the inducing field, then compute a 2D anomaly heatmap and a surface total-field anomaly profile in nT.

The standalone NumPy/SciPy solver accepts either caller-supplied field elements or a geographic location evaluated offline with IGRF-14. The browser interface and Pages workflow are future milestones.

## Run the solver and tests

From the repository root with Python 3.12:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

`requirements.txt` pins the solver and notebook dependencies. From the same directory, run a model with:

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

## Evaluate the geographic main field

```python
from magnetic_model.igrf import geographic_field

field = geographic_field(latitude_deg=39.7, longitude_deg=-105.0)
print(field)
```

To run a model from coordinates, call `simulate_at_location` with the ore body, latitude, longitude, survey azimuth, and the usual optional grid and observation height. IGRF-14 is fixed at decimal year 2026.0 and WGS84 ellipsoid height 0 km. See the [IGRF-14 notes](docs/igrf-14.md) for coefficient licensing, conventions, independent reference comparisons, and Pyodide results.

Open the executed [geomagnetic demonstration](notebooks/geomagnetic_field_demo.ipynb) for location and azimuth comparisons. To rerun it in the same environment as the verification notebook, use `python -m notebook notebooks/geomagnetic_field_demo.ipynb`.

## Run the verification notebook

The [executed notebook](notebooks/verification.ipynb) includes the derivation, plots, error tables, and the domain sensitivity study. It imports the shared solver directly from the checkout.

With the Python 3.12 virtual environment active, run from the repository root:

```sh
python -m pip install -r requirements.txt
python -m notebook notebooks/verification.ipynb
```

In Jupyter, select the Python 3 kernel for this environment and use **Kernel → Restart Kernel and Run All Cells**. To execute and save every output from the terminal:

```sh
python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=180 notebooks/verification.ipynb
```

The largest sensitivity case solves for 262,144 cells. For the rectangular example, the notebook reproduces the 0.36 nT RMS grid-refinement difference and the 14.50 nT RMS domain-doubling difference. Domain size and grid resolution should be checked separately for new geometries.

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
