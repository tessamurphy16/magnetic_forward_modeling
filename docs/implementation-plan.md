# Implementation plan

## 1. Coordinate and field conventions

Use a vertical cross-section with horizontal coordinate `x` positive along the survey azimuth `A`, measured clockwise from true north, and depth `z` positive down. Use `s` positive toward azimuth `A+90°` for the invariant strike axis. The survey is perpendicular to strike by construction. The selected globe point represents the center of the survey and supplies geodetic latitude and longitude. Use decimal year and altitude above the WGS84 ellipsoid for IGRF. Document the input and output units of the chosen IGRF evaluator and convert its altitude units as needed. The selected altitude is the datum for the model surface, `z=0`.

Use the IGRF north, east, and down components `B_N,B_E,B_D`. Convert nT to T before computing the inducing field `H0 = B0 / μ0`. Rotate the vector into section coordinates:

```text
Bx = BN cos(A) + BE sin(A)
Bs = -BN sin(A) + BE cos(A)
Bz = BD
F0 = sqrt(Bx² + Bs² + Bz²)
```

Display declination, inclination, and total intensity together with the epoch. Use `atan2(BE, BN)` for declination and `atan2(BD, hypot(BN, BE))` for inclination. Treat declination as undefined when the horizontal component vanishes. Validate the IGRF implementation against published reference values at several locations, including the Southern Hemisphere. Document the coefficient generation, supported years, altitude convention, and licensing. Reject unsupported inputs rather than extrapolating silently.

## 2. Model and observable definitions

Use a uniform nonmagnetic host and air in the initial release. Define the rectangular body by width along the section, vertical thickness, depth to top below `z=0`, and dimensionless SI volume susceptibility `χ`. Center it at `x=0`. Set `μr = 1 + χ` inside and `μr = 1` outside. Enforce positive permeability and start with a nonnegative susceptibility range appropriate to the course examples. There are no free currents or remanent magnetization.

Represent the anomalous magnetic scalar potential by `u`, with units A. Use the in-plane gradient with respect to `x,z`, treating the strike derivative of `u` as zero:

```text
H = H0 - grad(u)
B = μ0 μr H
div(μr grad(u)) = div(μr H0)
div(μr (H0 - grad(u))) = 0
```

Set `u=0` on the outer numerical boundary as a finite-domain approximation to a decaying perturbation. Include air above the surface and padding laterally and below the body. Check padding sensitivity independently of grid refinement. Enforce continuity of normal `B` across material interfaces through the discrete flux balance. Tangential `H` is continuous in the underlying scalar-potential formulation.

Use the same definition of `ΔB = B - B0` throughout the model. The strike contribution is `ΔBs = (μr - 1) Bs` in T and is zero in the air. Display:

- **Heatmap** of `ΔBz` in nT across the section, with a diverging color scale centered at zero, a downward-positive depth axis, and outlines for the surface and ore body.
- **Surface profile** of the total-field anomaly in nT using `|B0 + ΔB| - |B0|` evaluated on the air side of `z=0`. Retain the full inducing vector in both norms. Use the equivalent difference-of-squares expression if needed for numerical precision. Compare against the small-anomaly projection `(B0 · ΔB)/|B0|` in verification.

## 3. Python package and numerical method

| Planned file | Responsibility |
| --- | --- |
| `magnetic_model/geomagnetic.py` | IGRF evaluation, input validation, coordinate rotation, and field metadata |
| `magnetic_model/geometry.py` | Grid, ore-body placement, domain padding, and cell permeability |
| `magnetic_model/solver.py` | Conservative face fluxes, sparse system assembly, boundary treatment, and potential solve |
| `magnetic_model/observables.py` | Field reconstruction, surface sampling, and nT conversion |
| `magnetic_model/simulation.py` | Validated inputs and orchestration for notebook, tests, and browser |

Define a cell-centered rectangular grid with arrays ordered `[depth, distance]`. Put the ground surface on a grid face. Use a conservative finite difference in flux form, equivalent here to a cell-centered finite-volume discretization. Start with grid-aligned body interfaces for verification. For free slider positions, use a deterministic cell assignment and show the represented geometry. Refine the grid or restrict control ranges so thin bodies occupy multiple cells.

For an interior face oriented from cell `i` toward cell `j`, use the harmonic mean for equal cell widths and a shared permeability for both the inducing and potential flux terms:

```text
μface = 2 μi μj / (μi + μj)
Bn / μ0 = μface (H0n - (uj - ui) / center_distance)
```

This follows from eliminating the interface potential with continuity of normal flux. Apply the prescribed outer potential at half-cell distance and sum outward face fluxes to zero. Assemble the positive system corresponding to `-div(μr grad(u))`. Use a SciPy sparse direct solver as a baseline on modest grids. Report linear residuals and investigate iterative methods only if browser measurements warrant them. Reconstruct field components with a documented stencil. For the surface profile use the normal face flux and reconstruct tangential components from the air side. Avoid any field interpolation across the ore-body permeability jump.

Return coordinates in meters, arrays in nT for plotting, and diagnostic metadata such as effective geometry, grid spacing, solver residual, and inducing-field components. Keep the boundary between browser and Python limited to validated data and explicit arrays.

## 4. Numerical verification

Build `notebooks/verification.ipynb` as an executed record. Install or import the repository package in the notebook kernel and report its source path and dependency versions. Put reusable assertions in `tests/` and keep figures, derivations, and convergence tables in the notebook.

| Check | Evidence |
| --- | --- |
| Uniform permeability of one | Zero potential and zero anomaly within a scale-aware roundoff tolerance on several grids and field orientations |
| Pure strike inducing field | Zero in-plane perturbation and zero surface profile. Inside the body, check the local strike induction change analytically. |
| Smooth manufactured solution | Known potential with positive smooth permeability and a manufactured source. Measure relative L2 and max errors on at least three grids with a fixed domain. Expect approximately second-order potential convergence for the smooth, centered scheme. |
| Circular cylinder in a uniform transverse field | Compare against the analytic exterior potential and air field of an infinite permeable cylinder. Use its analytic outer potential in the verification case to isolate discretization error. Measure errors at points away from the interface and report the effect of stair-step geometry. |
| Rectangular ore-body case | Check flux balance, symmetry under an appropriate inducing field, and convergence of the surface profile. Refine the grid at fixed domain size, then enlarge the domain at fixed spacing. Report profile RMS and peak differences. |
| Geomagnetic and observable conventions | Check azimuths of 0° and 90°, inclination signs, reference IGRF values, units, and convergence of the linearized projection toward the exact anomaly for a weak perturbation. |

For a cylinder of radius (a) centered at the origin within a unit-permeability host, use `u = ((μr - 1)/(μr + 1)) a² (H0x x + H0z z) / (x² + z²)` outside. Verify its sign using `H = H0 - grad(u)`. Quantify error separately for potential and field. Avoid imposing the smooth-case convergence rate on stair-stepped geometry or fields near rectangle corners. Set test tolerances from reference precision and observed refinement behavior. Execute the notebook in CI from a clean kernel and retain the executed notebook with figures and error tables for submission.

## 5. Browser and deployment

1. Create `web/index.html`, `web/styles.css`, `web/app.js`, and `web/solver-worker.js`. Build a globe with a selectable marker and accessible latitude/longitude inputs. Use a bundled, attributed coastline dataset to avoid remote tile or API dependencies. Add decimal year and altitude inputs, survey azimuth, ore-body width, thickness, depth to top, and susceptibility controls with units and validation.
2. Initialize a pinned Pyodide runtime once in the dedicated worker. Load its matched NumPy and SciPy builds and the built artifact from `magnetic_model/`. Bundle IGRF coefficients with the Python artifact or a versioned data asset and evaluate locally. Keep runtime loading, solver readiness, errors, and results explicit in the worker message protocol.
3. Send input snapshots with request IDs. Coalesce rapid edits and ignore stale responses. Transfer typed-array buffers for plots and clean up Python proxies. Set grid limits after measuring solve time and peak memory on representative browsers. Keep globe interaction and rendering on the main thread while the solver runs.
4. Use HTML/CSS/JS to render the heatmap and profile with physical units, axes, and captions. Test keyboard input, layout at narrow widths, worker initialization failure, and repeat runs. Check quantitative agreement for a fixed case through both native Python and the browser worker.
5. Add a dependency manifest and reproducible environment for Python, NumPy, SciPy, pytest, and Jupyter execution. Pin the Pyodide release first and match native NumPy/SciPy versions to the compatible browser build where available. Record exact versions of the IGRF evaluator and coefficients, globe and plotting libraries or datasets, and CI actions. Verify the selected wheels and libraries in Pyodide before committing pins. The native solver and test versions are pinned in the requirements files. Confirm browser compatibility when selecting the Pyodide release.
6. Add a GitHub Actions workflow to run native tests, execute the verification notebook, build the site into a staging directory, and run the browser smoke test against that artifact. Use relative URLs and test under a project subpath such as `/magnetic_forward_modeling/`. Serve the pinned runtime and application assets as part of the static site. Check browser loading of WASM and worker assets. Parallel WASM threads and cross-origin isolation are outside the baseline.
7. Deploy the verified artifact from `main` with the official GitHub Pages Actions. Configure Pages to use GitHub Actions and grant the deployment job the required Pages and OIDC permissions. Verify worker initialization and a complete simulation at the published project URL.

## 6. Delivery milestones

1. **Native solver** — Submit equations, conventions, reproducible dependencies, and native tests for geometry, flux assembly, and sampling.
2. **Verification** — Run the manufactured and analytic cases, refine the rectangular model, and commit the executed notebook with interpretation of the errors and model limitations.
3. **Browser integration** — Run the same Python artifact in Pyodide, add interactive controls and plots, and verify parity with the native reference case.
4. **Deployment and documentation** — Publish the static artifact after CI passes. Add usage instructions, sample parameters, runtime and model limitations, references, and implementation-phase AI disclosure.

## References

- NOAA National Centers for Environmental Information. [International Geomagnetic Reference Field](https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field)
- Blakely, R. J. (1995). *Potential Theory in Gravity and Magnetic Applications*. [Cambridge University Press](https://doi.org/10.1017/CBO9780511549816)
- LeVeque, R. J. (2007). *Finite Difference Methods for Ordinary and Partial Differential Equations*. [SIAM](https://doi.org/10.1137/1.9780898717839)
- Pyodide documentation. [Using Pyodide in a web worker](https://pyodide.org/en/stable/usage/webworker.html)
- GitHub documentation. [Using custom workflows with GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
