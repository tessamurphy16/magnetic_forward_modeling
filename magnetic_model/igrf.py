"""Offline IGRF-14 main field at decimal year 2026.0 and WGS84 height 0 km."""

from dataclasses import dataclass
from datetime import datetime
from math import atan2, degrees, hypot, isfinite
from pathlib import Path

import ppigrf


EPOCH = 2026.0
ALTITUDE_KM = 0.0
_COEFFICIENTS = Path(__file__).with_name("data") / "IGRF14.shc"

# ppigrf interpolates by elapsed time. Select exactly 1/5 of the interval
# so the coefficients advance by one decimal year of 2025–2030 SV.
_START = datetime(2025, 1, 1)
_DATE = _START + (datetime(2030, 1, 1) - _START) * ((EPOCH - 2025) / 5)
_POLE_LIMIT_DEG = 90 - 1e-7


@dataclass(frozen=True)
class GeomagneticField:
    """Local geodetic north, east, down field and IGRF magnetic elements."""

    north_nt: float
    east_nt: float
    down_nt: float
    inclination_deg: float
    declination_deg: float
    total_nt: float
    horizontal_nt: float


def geographic_field(latitude_deg: float, longitude_deg: float) -> GeomagneticField:
    """Evaluate one WGS84 location, with longitude positive east and periodic.

    Longitude is normalized to [-180, 180). At a geographic pole, return
    the meridian-dependent limit approached along the supplied longitude.
    Declination is NaN if the horizontal intensity is exactly zero.
    """
    if not isfinite(latitude_deg) or not -90 <= latitude_deg <= 90:
        raise ValueError("Geodetic latitude must be finite and within [-90, 90] degrees.")
    if not isfinite(longitude_deg):
        raise ValueError("Longitude must be finite.")

    longitude = longitude_deg % 360
    if longitude >= 180:
        longitude -= 360
    # Avoid the spherical-coordinate 1/sin(colatitude) singularity in ppigrf.
    latitude = min(max(latitude_deg, -_POLE_LIMIT_DEG), _POLE_LIMIT_DEG)
    east, north, up = (
        component.item() for component in ppigrf.igrf(
            longitude, latitude, ALTITUDE_KM, _DATE, coeff_fn=_COEFFICIENTS,
        )
    )

    down = -up
    horizontal = hypot(north, east)
    return GeomagneticField(
        north, east, down, degrees(atan2(down, horizontal)),
        degrees(atan2(east, north)) if horizontal else float("nan"),
        hypot(horizontal, down), horizontal,
    )
