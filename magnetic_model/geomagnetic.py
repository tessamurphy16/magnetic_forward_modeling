"""Convert supplied IGRF field elements into the survey coordinate frame."""

import numpy as np


NT_TO_T = 1e-9
MU_0 = 1.25663706127e-6  # H/m, 2022 CODATA


def survey_field_t(intensity_nt, inclination_deg, declination_deg, azimuth_deg):
    """Return B0 in tesla ordered (survey x, strike s, depth z).

    Inclination is positive down. Declination and azimuth increase clockwise
    from true north. Azimuth and declination may wrap through 360 degrees.
    """
    values = (intensity_nt, inclination_deg, declination_deg, azimuth_deg)
    if not all(np.isfinite(values)):
        raise ValueError("Field intensity and angles must be finite.")
    if intensity_nt <= 0 or not -90 <= inclination_deg <= 90:
        raise ValueError("Intensity must be positive and inclination within [-90, 90] degrees.")

    inclination = np.deg2rad(inclination_deg)
    relative_heading = np.deg2rad(declination_deg % 360 - azimuth_deg % 360)
    horizontal = 0.0 if abs(inclination_deg) == 90 else np.cos(inclination)
    return intensity_nt * NT_TO_T * np.array([
        horizontal * np.cos(relative_heading),
        horizontal * np.sin(relative_heading),
        np.sin(inclination),
    ])
