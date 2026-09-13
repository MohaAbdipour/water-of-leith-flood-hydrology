"""Small, testable utilities for terrain-based catchment mapping."""

from __future__ import annotations

import numpy as np


def hillshade(
    elevation: np.ndarray,
    cell_size: float,
    azimuth: float = 315.0,
    altitude: float = 40.0,
) -> np.ndarray:
    """Return a 0--1 analytical hillshade for a regularly spaced DEM."""
    values = np.asarray(elevation, dtype=float)
    dy, dx = np.gradient(values, cell_size, cell_size)
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    azimuth_rad = np.deg2rad(azimuth)
    altitude_rad = np.deg2rad(altitude)
    shaded = (
        np.sin(altitude_rad) * np.cos(slope)
        + np.cos(altitude_rad) * np.sin(slope) * np.cos(azimuth_rad - aspect)
    )
    return np.clip((shaded + 1.0) / 2.0, 0.0, 1.0)


def cell_area_km2(mask: np.ndarray, cell_size: float) -> float:
    """Calculate the planimetric area represented by true raster cells."""
    return float(np.count_nonzero(mask) * cell_size**2 / 1_000_000)
