"""Transparent selection and summary methods for regional flow comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd

TARGET_STATION = 19006
TARGET_EASTING = 322_792
TARGET_NORTHING = 673_202


def select_comparison_stations(metadata: pd.DataFrame, count: int = 6) -> pd.DataFrame:
    """Return the nearest stations satisfying predeclared comparability rules."""
    stations = metadata.copy()
    stations["start"] = pd.to_datetime(stations["Start_date"], dayfirst=True)
    stations["end"] = pd.to_datetime(stations["End_date"], dayfirst=True)
    stations["distance_km"] = np.hypot(
        stations["Easting"] - TARGET_EASTING,
        stations["Northing"] - TARGET_NORTHING,
    ) / 1000
    eligible = stations[
        (stations["station_id"] != TARGET_STATION)
        & (stations["distance_km"] <= 30)
        & stations["Catchment_Area"].between(30, 300)
        & (stations["start"].dt.year <= 2000)
        & (stations["end"].dt.year >= 2023)
        & (stations["Missing_values_%"] <= 1)
    ]
    return eligible.sort_values(["distance_km", "station_id"]).head(count)


def coefficient_of_variation(values: pd.Series | np.ndarray) -> float:
    """Sample coefficient of variation for positive annual maxima."""
    array = np.asarray(values, dtype=float)
    return float(np.std(array, ddof=1) / np.mean(array))
