# Browser validation

The static build contains Globe.gl 2.44.0 (MIT), Plotly.js 2.35.2 (MIT), the NASA Blue Marble Earth texture distributed in the three-globe 2.44.0 examples, and Pyodide 0.27.7 (MPL-2.0). The runtime supplies NumPy 2.0.2, SciPy 1.14.1, and pandas 2.2.3. The browser loads the ppigrf 2.1.0 wheel and the shared Python package with its local IGRF-14 coefficients. The build verifies asset hashes and stages available license notices. [NASA Blue Marble](https://science.nasa.gov/earth/earth-observatory/blue-marble/) · [Globe.gl](https://github.com/vasturiano/globe.gl) · [Plotly.js](https://github.com/plotly/plotly.js) · [Pyodide](https://pyodide.org/en/0.27.7/)

## Model controls and limits

The default uses a 1,600 × 1,600 m centered domain with 5 m cells. This is the default-grid configuration chosen from the rectangular reference study. In that study, it differed by 1.91 nT RMS and 1.92 nT maximum from the 2,560 m domain at the same spacing. The 10 m preview on the 1,600 m domain missed the 2 nT RMS and 4 nT maximum targets. Coarser spacings are explicit choices. The uncertainty changes with the ore body, field, observation height, and padding. [Analytical verification notebook](../notebooks/verification.ipynb)

The site accepts spacings from 5 through 25 m that divide the 800 m half-domain. Width and thickness each span at least three cells, and the outline uses the represented grid-aligned body. The heatmap opens near the ore body and can be zoomed. Its zero-centered scale uses the largest absolute anomaly in the entire computed section for the active quantity. The profile reports the exact field magnitude difference at the chosen height. The geographic panel reports the main field before the ore-body perturbation.

## Chromium benchmark

Measured with headless Chromium 156.0.8078.79 on a cloud AMD EPYC 9V74 machine. The site was served over loopback at the GitHub Pages-style path `/magnetic_forward_modeling/` with a clean browser context. The case used Golden, azimuth 0°, susceptibility 0.1 SI, an 80 m × 40 m body with 40 m top depth, and a 10 m observation height. The 5 m grid contained 102,400 cells.

| Stage | First solve | Repeat 1 | Repeat 2 |
| --- | ---: | ---: | ---: |
| Worker initialization | 9,803.0 ms | — | — |
| IGRF calculation | 59.9 ms | 144.0 ms | 55.2 ms |
| PDE solution | 1,739.1 ms | 1,553.2 ms | 1,240.8 ms |
| Total simulation | 1,825.6 ms | 1,719.5 ms | 1,333.0 ms |

Initialization starts when the worker script executes and includes WASM setup, package loading, and Python imports. PDE solution includes sparse assembly and reconstruction of the solver's face fluxes. Total simulation measures the worker request through assembly of the transferable result. It excludes Plotly rendering and initialization. These timings apply to the tested environment. First-load download time and memory usage can differ on other devices and hosts. The staged site occupies about 49 MiB, including runtime packages.

For identical native Python inputs, the maximum absolute browser differences were 4.42 × 10⁻¹² nT for the profile, 6.82 × 10⁻¹² nT for the vertical heatmap, and 6.76 × 10⁻¹² nT for the exact total-field heatmap. The default solve had a relative L² residual of 1.29 × 10⁻¹⁴ and a maximum flux divergence of 9.82 × 10⁻¹² nT/m.

The smoke test checks globe selection, presets, manual coordinates, azimuth, grid validation, dimension changes, a zero-susceptibility profile, reset, narrow-width layout, and runtime recovery. Singapore's peak profile magnitude changed from 321.10 nT at 0° to 16.07 nT at 90°. Only same-origin assets were requested in the successful run. Both Jupyter notebooks reran, and all 27 native tests passed.

## Rerun the Chromium test

Stage and serve the site as shown in the README. Maintainers need Chromium and Node.js to run the optional browser automation. From the repository root, with the native Python dependencies installed:

```sh
npm install --prefix /tmp/magnetic-browser-test playwright-core@1.65.1
NODE_PATH=/tmp/magnetic-browser-test/node_modules PYTHON="$PWD/.venv/bin/python" \
  node tests/browser_smoke.cjs
```

The default Chromium executable is `/usr/bin/chromium`. Override it with `CHROMIUM` and override the served path with `SITE_URL` if needed. Set `SCREENSHOT` to capture the completed default dashboard. The test waits for the worker and checks the values displayed by Plotly against a native solve.
