"""Transparent descriptors for rainfall and flood-hydrograph structure."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import find_peaks


def classification_agreement(reference: pd.Series, candidate: pd.Series) -> float:
    """Return the fraction of paired categorical labels that agree exactly."""
    if len(reference) != len(candidate):
        raise ValueError("Classification series must have equal lengths")
    return float((reference.to_numpy() == candidate.to_numpy()).mean())


def cumulative_rainfall_duration(rainfall: pd.Series, lower: float = 0.1, upper: float = 0.9) -> float:
    """Hours between the lower and upper cumulative-rainfall fractions."""
    values = rainfall.fillna(0).clip(lower=0).to_numpy(dtype=float)
    if values.sum() <= 0:
        return float("nan")
    cumulative = np.cumsum(values) / values.sum()
    lower_index = int(np.searchsorted(cumulative, lower))
    upper_index = int(np.searchsorted(cumulative, upper))
    return float(upper_index - lower_index)


def count_event_peaks(
    series: pd.Series,
    smoothing_hours: int = 3,
    minimum_separation_hours: int = 6,
    prominence_range_fraction: float = 0.1,
    prominence_maximum_fraction: float = 0.05,
) -> int:
    """Count prominent peaks after hourly smoothing.

    Prominence is the larger of 10% of the smoothed range or 5% of its maximum,
    preventing negligible numerical fluctuations from defining extra peaks.
    """
    values = series.astype(float).interpolate(limit_direction="both")
    smoothed = values.rolling(smoothing_hours, center=True, min_periods=1).mean().to_numpy()
    prominence = max(
        prominence_range_fraction * np.ptp(smoothed),
        prominence_maximum_fraction * np.max(smoothed),
        1e-9,
    )
    peaks, _ = find_peaks(smoothed, prominence=prominence, distance=minimum_separation_hours)
    return int(len(peaks))


def rainfall_centroid_lag(rainfall: pd.Series, flow_peak_time: pd.Timestamp) -> float:
    """Hours from the rainfall mass centroid to the observed flow peak."""
    values = rainfall.fillna(0).clip(lower=0).to_numpy(dtype=float)
    if values.sum() <= 0:
        return float("nan")
    times = pd.DatetimeIndex(rainfall.index)
    relative_hours = (times - times[0]) / pd.Timedelta(hours=1)
    centroid_hours = float(np.average(relative_hours, weights=values))
    peak_hours = float((pd.Timestamp(flow_peak_time) - times[0]) / pd.Timedelta(hours=1))
    return peak_hours - centroid_hours


def rising_limb_duration(flow: pd.Series, peak_time: pd.Timestamp) -> float:
    """Hours from the last 10%-amplitude crossing to the observed peak."""
    before = flow.loc[:peak_time]
    baseline = float(before.min())
    peak = float(before.loc[peak_time])
    threshold = baseline + 0.1 * (peak - baseline)
    candidates = before.index[before <= threshold]
    if len(candidates) == 0:
        return float("nan")
    return float((pd.Timestamp(peak_time) - candidates[-1]) / pd.Timedelta(hours=1))


def recession_half_time(flow: pd.Series, peak_time: pd.Timestamp) -> float:
    """Hours after the peak until flow first falls to half its event amplitude."""
    before = flow.loc[:peak_time]
    after = flow.loc[peak_time:]
    baseline = float(before.min())
    peak = float(flow.loc[peak_time])
    threshold = baseline + 0.5 * (peak - baseline)
    candidates = after.index[after <= threshold]
    if len(candidates) == 0:
        return float("nan")
    return float((candidates[0] - pd.Timestamp(peak_time)) / pd.Timedelta(hours=1))


def duration_class(
    duration_10_90_hours: float,
    concentrated_limit: float = 12,
    prolonged_limit: float = 36,
) -> str:
    """Classify rainfall concentration using explicit D10–90 boundaries."""
    if concentrated_limit >= prolonged_limit:
        raise ValueError("The concentrated limit must be below the prolonged limit")
    if duration_10_90_hours <= concentrated_limit:
        return "concentrated"
    if duration_10_90_hours <= prolonged_limit:
        return "intermediate"
    return "prolonged"
