# Repository instructions

- Read [the implementation plan](docs/implementation-plan.md) before changing the physics, numerical solver, browser code, notebook, or deployment.
- Keep the simulation in importable Python modules under `magnetic_model/`. The verification notebook, tests, and Pyodide worker must import those same source files. Build the browser bundle from the repository package.
- Keep solver inputs and outputs independent of Pyodide, browser globals, UI state, and network access. Document units, signs, coordinate frames, and array layout at module boundaries.
- Treat the section as a horizontal survey axis and a downward-positive depth axis, with invariant perpendicular strike. Use SI in the solver, convert magnetic fields to nT at the output boundary, and retain the full IGRF field when projecting the total-field anomaly.
- Verify numerical changes using analytic or independent references, interface checks, and refinement studies. Record error norms and grid sizes. A plausible plot alone is insufficient.
- Keep the app static and mount-path independent. Test it under a GitHub Pages project path with a clean browser session. Keep Pyodide execution in a dedicated worker.
- Record dependency versions, IGRF coefficient provenance, and material AI assistance. Run the relevant native checks, notebook, and browser smoke test when their corresponding implementation exists.
