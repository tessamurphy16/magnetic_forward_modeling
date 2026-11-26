# 2D magnetic forward modeling

A numerical PDE course project for exploring how buried magnetic bodies affect surface survey measurements. The planned browser app will use an interactive globe and IGRF to set the inducing field, then compute a 2D anomaly heatmap and a surface total-field anomaly profile in nT.

This repository currently contains the architecture and implementation plan. The solver, interface, executed notebook, and Pages workflow are future milestones. There are no application dependencies or run commands in this phase.

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
