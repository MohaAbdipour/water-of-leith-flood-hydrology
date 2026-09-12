"""Sensitivity of event associations to CEH-GEAR1hr quality indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def quality_subsets(events: pd.DataFrame) -> dict[str, pd.Series]:
    """Return explicit, progressively selective rainfall-quality masks."""
    return {
        "All events": pd.Series(True, index=events.index),
        "Mean disaggregation ≤ 0.25": events["mean_disaggregation_fraction"] <= 0.25,
        "Mean disaggregation ≤ 0.10": events["mean_disaggregation_fraction"] <= 0.10,
        "No statistical disaggregation": events["maximum_disaggregation_fraction"] == 0,
        "Gauge distance ≤ 10 km": events["maximum_gauge_distance_km"] <= 10,
        "Disaggregation ≤ 0.10 and distance ≤ 10 km": (
            (events["mean_disaggregation_fraction"] <= 0.10)
            & (events["maximum_gauge_distance_km"] <= 10)
        ),
    }


def bootstrap_spearman_interval(
    x: pd.Series | np.ndarray,
    y: pd.Series | np.ndarray,
    repetitions: int = 2000,
    seed: int = 19006,
) -> tuple[float, float]:
    """Return a paired non-parametric 95% interval for Spearman correlation."""
    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    if len(x_values) < 10 or len(x_values) != len(y_values):
        raise ValueError("At least ten paired observations are required")
    rng = np.random.default_rng(seed)
    correlations = []
    for _ in range(repetitions):
        indices = rng.integers(0, len(x_values), len(x_values))
        coefficient = stats.spearmanr(x_values[indices], y_values[indices]).statistic
        if np.isfinite(coefficient):
            correlations.append(coefficient)
    return tuple(float(value) for value in np.quantile(correlations, [0.025, 0.975]))


def sensitivity_table(events: pd.DataFrame, repetitions: int = 2000) -> pd.DataFrame:
    """Calculate rainfall-flow associations for each quality subset and duration."""
    rows = []
    for subset_number, (label, mask) in enumerate(quality_subsets(events).items()):
        selected = events.loc[mask]
        for duration in [24, 48, 72]:
            rainfall = selected[f"rainfall_{duration}h_mm"]
            result = stats.spearmanr(selected["peak_flow_m3s"], rainfall)
            lower, upper = bootstrap_spearman_interval(
                selected["peak_flow_m3s"], rainfall, repetitions, seed=19006 + subset_number + duration
            )
            rows.append({
                "quality_subset": label,
                "rainfall_duration_hours": duration,
                "events": len(selected),
                "spearman_rho": result.statistic,
                "spearman_p": result.pvalue,
                "bootstrap_lower_95": lower,
                "bootstrap_upper_95": upper,
                "median_lag_hours": selected["hours_from_rainfall_maximum_to_flow_peak"].median(),
            })
    return pd.DataFrame(rows)
