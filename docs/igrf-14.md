# Offline IGRF-14 main field

`magnetic_model.igrf.geographic_field(latitude_deg, longitude_deg)` returns a `GeomagneticField` record. The three geodetic components point north, east, and down and are in nT. Horizontal intensity is `hypot(N, E)`, total intensity is `hypot(H, Down)`, inclination is `atan2(Down, H)`, and east-positive declination is `atan2(E, N)`, with both angles converted to degrees.

Latitude must be in [−90°, 90°]. Input longitude is east-positive and wraps to [−180°, 180°), so equivalent meridians give the same results. At a geographic pole the local horizontal axes depend on the supplied meridian. The evaluator uses the limit approximated at 0.0000001° inside each pole to avoid the spherical-coordinate singularity in ppigrf. Declination is undefined if horizontal intensity is zero.

Survey azimuth is clockwise from true north, with 0° and 360° equivalent. `simulate_at_location` uses the existing rotation to produce survey, strike (azimuth + 90°), and downward components. The PDE uses survey and downward forcing. The exact total-field magnitude difference uses all three background components.

## Model and data provenance

The epoch is fixed to decimal year 2026.0 and the height is fixed to 0 km above the WGS84 ellipsoid. Observation height in the PDE still sets the profile sampling elevation. It does not change the IGRF evaluation height. The reference field represents the large-scale internal main field. It omits local crustal anomalies and short-term external disturbances, and the forward model treats it as uniform over the survey.

The bundled [IGRF14.shc](../magnetic_model/data/IGRF14.shc) is a byte-for-byte copy from the ppigrf 2.1.0 distribution, which is MIT-licensed. The [distribution's license notice](../magnetic_model/data/LICENSE-ppigrf.txt) accompanies the copy. The file identifies the IAGA model release. Its 2030.0 column includes five years of predictive secular variation from 2025.0. The wrapper asks ppigrf to interpolate at exactly one fifth of the timestamp interval between those columns, so each coefficient advances by one year of secular variation. The SHC SHA-256 is `717f6dce821a8f2bfcc6a77f79cc227ba91f61aeb458d5433e8c72450d48f8e0`. [IAGA model release](https://doi.org/10.5281/zenodo.14012302) · [ppigrf 2.1.0 distribution](https://pypi.org/project/ppigrf/2.1.0/)

## Independent verification

For the reference, run NOAA/CIRES geomaglib 1.2.4 at commit `b488b46f4590b5edfc9980b3397dc65bd336d603` with its bundled `IGRF14_sv.COF`. Load the 2025 epoch with `sh_loader.load_coef` (`skip_two_columns=True, load_sv=True, load_year=2025`) and apply `timely_modify_magnetic_model` at 2026.0. Use `util.geod_to_geoc_lat` with altitude 0 km, degree-13 harmonics via `sh_vars.comp_sh_vars`, `legendre.Flattened_Chaos_Legendre1`, and `magmath.mag_SPH_summation`. Rotate back to local geodetic components with `magmath.rotate_magvec` using the library's north/east/down test convention. The angles and intensities in the reference rows are derived from those independent components. [NOAA/CIRES geomaglib source](https://github.com/CIRES-Geomagnetism/geomaglib/tree/b488b46f4590b5edfc9980b3397dc65bd336d603)

Differences are calculated minus reference and rounded after subtraction.

| Site (latitude, longitude) | Values | N (nT) | E (nT) | Down (nT) | I (°) | D (°) | F (nT) | H (nT) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Golden (39.7, −105.0) | Reference | 20715.692176 | 2747.165628 | 46589.419363 | 65.842026778 | 7.554076280 | 51061.343675 | 20897.052934 |
| | Calculated | 20715.691897 | 2747.165628 | 46589.419487 | 65.842027118 | 7.554076381 | 51061.343675 | 20897.052658 |
| | Difference | −0.000279 | 0.000000 | +0.000124 | +0.000000340 | +0.000000100 | 0.000000 | −0.000276 |
| Skagway (59.45, −135.31) | Reference | 13790.549447 | 4434.456195 | 53672.512652 | 74.895993951 | 17.825589983 | 55593.005587 | 14485.981354 |
| | Calculated | 13790.549218 | 4434.456195 | 53672.512711 | 74.895994183 | 17.825590259 | 55593.005587 | 14485.981137 |
| | Difference | −0.000228 | 0.000000 | +0.000059 | +0.000000232 | +0.000000277 | 0.000000 | −0.000218 |
| Singapore (1.35, 103.82) | Reference | 41037.780206 | 156.787207 | −9348.797200 | −12.833417711 | 0.218900766 | 42089.476067 | 41038.079713 |
| | Calculated | 41037.780206 | 156.787207 | −9348.797200 | −12.833417711 | 0.218900766 | 42089.476067 | 41038.079713 |
| | Difference | 0.000000 | 0.000000 | 0.000000 | 0.000000000 | 0.000000000 | 0.000000 | 0.000000 |
| Perth (−31.95, 115.86) | Reference | 23929.707853 | −637.355313 | −53333.494807 | −65.827559855 | −1.525682563 | 58459.377417 | 23938.194162 |
| | Calculated | 23929.707610 | −637.355313 | −53333.494916 | −65.827560116 | −1.525682578 | 58459.377417 | 23938.193919 |
| | Difference | −0.000243 | 0.000000 | −0.000109 | −0.000000261 | −0.000000015 | 0.000000 | −0.000243 |

The maximum component discrepancy was 0.000279 nT and the maximum angular discrepancy was 0.000000340°. These measure implementation agreement and do not represent field prediction accuracy.

## Pyodide compatibility

A headless Chromium 156 Web Worker ran Pyodide 0.27.7 with its NumPy 2.0.2, SciPy 1.14.1, and pandas 2.2.3 builds, plus the pure-Python ppigrf 2.1.0 wheel. Native tests used NumPy 2.2.6, SciPy 1.15.3, pandas 2.2.3, and ppigrf 2.1.0. The smoke test served local assets over loopback and sent Golden's latitude, longitude, and an 80° survey azimuth as JavaScript numbers. The worker loaded the repository files and coefficients into Pyodide's virtual filesystem, evaluated the field, and ran a 64 × 64 solve with 10 m cells and a 10 m observation height. The maximum difference from native Python was 2.91 × 10⁻¹¹ nT for field outputs and 7.96 × 10⁻¹³ nT over the full profile.

For future static deployment, include the ppigrf wheel, Pyodide dependencies, and the complete `magnetic_model/` package tree so `igrf.py` can resolve `data/IGRF14.shc` beside it. The worker can pass the globe's numeric latitude and longitude directly to `geographic_field` or `simulate_at_location`. The calculation needs no network service after the assets are loaded.
