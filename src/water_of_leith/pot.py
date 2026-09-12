"""Peaks-over-threshold extraction and Generalised Pareto inference."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class GPDFit:
    threshold: float
    shape: float
    scale: float
    event_rate_per_year: float
    event_count: int
    record_years: float


def ljung_box_rank_test(values: pd.Series | np.ndarray, max_lag: int = 5) -> tuple[float, float]:
    """Test serial dependence in ordered peak magnitudes using rank autocorrelations.

    Ranking limits sensitivity to individual exceptional floods.  The returned
    values are the Ljung--Box Q statistic and its chi-square p-value.
    """
    ranks = stats.rankdata(np.asarray(values, dtype=float))
    n = len(ranks)
    if n <= max_lag + 1:
        raise ValueError("The series is too short for the requested maximum lag")
    centred = ranks - ranks.mean()
    denominator = float(np.dot(centred, centred))
    if denominator == 0:
        raise ValueError("Serial dependence is undefined for a constant series")
    correlations = [
        float(np.dot(centred[lag:], centred[:-lag]) / denominator)
        for lag in range(1, max_lag + 1)
    ]
    statistic = n * (n + 2) * sum(
        correlation**2 / (n - lag)
        for lag, correlation in enumerate(correlations, start=1)
    )
    return float(statistic), float(stats.chi2.sf(statistic, df=max_lag))


def decluster_exceedances(
    data: pd.DataFrame,
    threshold: float,
    run_length: str | pd.Timedelta = "72h",
) -> pd.DataFrame:
    """Retain the largest exceedance in clusters separated by ``run_length``.

    Run declustering is deliberately explicit and is not claimed to reproduce
    the FEH event-independence procedure.
    """
    run_length = pd.Timedelta(run_length)
    exceedances = data.loc[data["value"] > threshold, ["datetime", "value", "flag"]].sort_values("datetime").copy()
    if exceedances.empty:
        return exceedances.assign(excess=pd.Series(dtype=float))
    exceedances["new_cluster"] = exceedances["datetime"].diff().gt(run_length).fillna(True)
    exceedances["cluster"] = exceedances["new_cluster"].cumsum()
    peak_indices = exceedances.groupby("cluster")["value"].idxmax()
    peaks = exceedances.loc[peak_indices, ["datetime", "value", "flag"]].sort_values("datetime").reset_index(drop=True)
    peaks["excess"] = peaks["value"] - threshold
    return peaks


def fit_gpd(data: pd.DataFrame, peaks: pd.DataFrame, threshold: float) -> GPDFit:
    """Fit a two-parameter GPD to independent threshold excesses."""
    if len(peaks) < 20:
        raise ValueError("At least 20 independent exceedances are required")
    shape, _, scale = stats.genpareto.fit(peaks["excess"].to_numpy(), floc=0)
    record_years = (data["datetime"].max() - data["datetime"].min()) / pd.Timedelta(days=365.2425)
    return GPDFit(
        threshold=float(threshold),
        shape=float(shape),
        scale=float(scale),
        event_rate_per_year=float(len(peaks) / record_years),
        event_count=len(peaks),
        record_years=float(record_years),
    )


def gpd_return_level(fit: GPDFit, return_period_years: float) -> float:
    """Return the level exceeded with annual probability 1/T under a Poisson-GPD model."""
    target_rate = -np.log1p(-1 / return_period_years)
    ratio = fit.event_rate_per_year / target_rate
    if abs(fit.shape) < 1e-8:
        return float(fit.threshold + fit.scale * np.log(ratio))
    return float(fit.threshold + fit.scale / fit.shape * (ratio**fit.shape - 1))


def bootstrap_gpd_levels(
    fit: GPDFit,
    peaks: pd.DataFrame,
    periods: list[int],
    repetitions: int = 1000,
    seed: int = 19006,
) -> pd.DataFrame:
    """Bootstrap GPD parameter uncertainty by resampling independent events."""
    rng = np.random.default_rng(seed)
    excesses = peaks["excess"].to_numpy()
    values: list[dict[str, float | int]] = []
    for _ in range(repetitions):
        sample = rng.choice(excesses, size=len(excesses), replace=True)
        try:
            shape, _, scale = stats.genpareto.fit(sample, floc=0)
            candidate = GPDFit(fit.threshold, float(shape), float(scale), fit.event_rate_per_year, fit.event_count, fit.record_years)
            values.extend({"return_period_years": period, "flow_m3s": gpd_return_level(candidate, period)} for period in periods)
        except (ValueError, FloatingPointError):
            continue
    frame = pd.DataFrame(values)
    return (
        frame.groupby("return_period_years")["flow_m3s"]
        .quantile([0.025, 0.5, 0.975])
        .unstack()
        .rename(columns={0.025: "lower_95_m3s", 0.5: "median_m3s", 0.975: "upper_95_m3s"})
        .reset_index()
    )
