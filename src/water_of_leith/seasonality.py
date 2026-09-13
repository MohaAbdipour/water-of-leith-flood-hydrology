"""Seasonality and leakage-safe event-model utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import rankdata


def hydrological_year_angle(times: pd.Series | pd.DatetimeIndex) -> np.ndarray:
    """Map dates to radians from 1 October, accounting for water-year length."""
    dates = pd.DatetimeIndex(times)
    starts = pd.to_datetime(
        np.where(dates.month >= 10, dates.year, dates.year - 1).astype(str) + "-10-01"
    )
    ends = starts + pd.offsets.DateOffset(years=1)
    fraction = (dates - starts) / (ends - starts)
    return 2 * np.pi * np.asarray(fraction, dtype=float)


def circular_summary(angles: np.ndarray) -> tuple[float, float, float]:
    """Return mean angle, resultant length and approximate Rayleigh p-value."""
    values = np.asarray(angles, dtype=float)
    resultant = np.mean(np.exp(1j * values))
    mean_angle = float(np.angle(resultant) % (2 * np.pi))
    r_bar = float(abs(resultant))
    n = len(values)
    z = n * r_bar**2
    p_value = np.exp(-z) * (
        1
        + (2 * z - z**2) / (4 * n)
        - (24 * z - 132 * z**2 + 76 * z**3 - 9 * z**4) / (288 * n**2)
    )
    return mean_angle, r_bar, float(np.clip(p_value, 0, 1))


def partial_spearman(x: np.ndarray, y: np.ndarray, control: np.ndarray) -> float:
    """Spearman correlation after linearly residualising ranks on one control."""
    ranked_x, ranked_y, ranked_control = map(rankdata, (x, y, control))
    design = np.column_stack([np.ones(len(ranked_control)), ranked_control])
    residual_x = ranked_x - design @ np.linalg.lstsq(design, ranked_x, rcond=None)[0]
    residual_y = ranked_y - design @ np.linalg.lstsq(design, ranked_y, rcond=None)[0]
    return float(np.corrcoef(residual_x, residual_y)[0, 1])


def expanding_splits(n: int, initial: int, test_size: int):
    """Yield expanding training indices and subsequent non-overlapping tests."""
    if initial <= 0 or test_size <= 0 or initial >= n:
        raise ValueError("Invalid expanding-window dimensions")
    start = initial
    while start < n:
        stop = min(start + test_size, n)
        yield np.arange(start), np.arange(start, stop)
        start = stop


def fit_predict_log_linear(
    train_x: np.ndarray,
    train_y: np.ndarray,
    test_x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit OLS to log flow and return coefficients and back-transformed flows."""
    coefficients = np.linalg.lstsq(train_x, np.log(train_y), rcond=None)[0]
    prediction = np.exp(test_x @ coefficients)
    return coefficients, prediction
