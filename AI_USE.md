# AI use

OpenAI Codex drafted the repository structure and implementation plan from the project requirements. This phase produced no solver code or simulation results. Record material AI assistance as the implementation progresses, including the affected files or methods and the checks used to verify the work. Follow the course's disclosure requirements when preparing the final submission.

OpenAI Codex also assisted with the Python solver, field and profile reconstruction, and native tests. Verification includes orientation and unit checks, residual and interface-flux checks, a cylinder benchmark, and separate rectangular-body grid and domain comparisons.

OpenAI Codex assisted with the verification notebook, analytical boundary support, and the affine boundary regression test. The notebook was executed against the shared solver. It records numerical residuals, analytic comparisons, refinement, and domain-sensitivity results.

OpenAI Codex assisted with the IGRF-14 wrapper, geographic solver integration, tests, reference comparisons, and Jupyter demonstration. Geographic fields were checked against independently computed NOAA/CIRES geomaglib results and run with the shared solver in a Chromium Pyodide worker.

OpenAI Codex assisted with the static dashboard, Web Worker adapter, build script, and Chromium smoke test. Browser results were compared against the native Python model, and both existing notebooks were rerun.

OpenAI Codex assisted with the GitHub Pages workflow and its launch documentation. The staged site was tested under the repository URL prefix in Chromium.
