"""Quality-controlled extraction and flood-frequency estimation.

The fitted distributions are independent statistical estimates. They are not
formal FEH estimates and do not reproduce licensed FEH software.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class FittedModel:
    name: str
    distribution: object
    parameters: tuple[float, ...]


def read_ukflow15(path: str) -> pd.DataFrame:
    """Read a UK-Flow15 station file while retaining three-digit QC flags."""
    data = pd.read_csv(path, dtype={"flag": "string"}, parse_dates=["datetime"])
    data["flag"] = data["flag"].str.zfill(3)
    return data


def validate_series(data: pd.DataFrame) -> dict[str, int | float | str]:
    """Return core integrity diagnostics and raise on structural failures."""
    required = {"datetime", "value", "resolution", "flag"}
    if not required.issubset(data.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(data.columns))}")
    ordered = data.sort_values("datetime")
    duplicate_count = int(ordered["datetime"].duplicated().sum())
    irregular_steps = int((ordered["datetime"].diff().dropna() != pd.Timedelta(minutes=15)).sum())
    missing_flows = int(ordered["value"].isna().sum())
    negative_flows = int((ordered["value"] < 0).sum())
    if duplicate_count or irregular_steps or missing_flows or negative_flows:
        raise ValueError("Flow series failed structural QA; inspect diagnostics before analysis")
    return {
        "start": str(ordered["datetime"].min()),
        "end": str(ordered["datetime"].max()),
        "observations": len(ordered),
        "duplicate_timestamps": duplicate_count,
        "irregular_steps": irregular_steps,
        "missing_flows": missing_flows,
        "negative_flows": negative_flows,
        "flagged_observations": int((ordered["flag"] != "000").sum()),
    }


def annual_maxima(data: pd.DataFrame, minimum_completeness: float = 0.95) -> pd.DataFrame:
    """Extract maxima for complete October–September water years.

    Water year 2020 denotes 1 October 2019 through 30 September 2020. Partial
    boundary years and years below ``minimum_completeness`` are excluded.
    """
    frame = data.copy().sort_values("datetime")
    frame["water_year"] = frame["datetime"].dt.year + (frame["datetime"].dt.month >= 10)
    records: list[dict[str, object]] = []
    for water_year, group in frame.groupby("water_year"):
        start = pd.Timestamp(int(water_year) - 1, 10, 1)
        end = pd.Timestamp(int(water_year), 10, 1)
        expected = int((end - start) / pd.Timedelta(minutes=15))
        completeness = len(group) / expected
        covers_boundaries = group["datetime"].min() == start and group["datetime"].max() == end - pd.Timedelta(minutes=15)
        if completeness >= minimum_completeness and covers_boundaries:
            peak_index = group["value"].idxmax()
            records.append({
                "water_year": int(water_year),
                "peak_datetime": group.loc[peak_index, "datetime"],
                "peak_flow_m3s": float(group.loc[peak_index, "value"]),
                "quality_flag": str(group.loc[peak_index, "flag"]),
                "completeness": completeness,
            })
    return pd.DataFrame.from_records(records)


def empirical_return_periods(maxima: pd.DataFrame) -> pd.DataFrame:
    """Calculate Gringorten plotting positions for ranked annual maxima."""
    ranked = maxima.sort_values("peak_flow_m3s", ascending=False).reset_index(drop=True).copy()
    rank = np.arange(1, len(ranked) + 1)
    exceedance_probability = (rank - 0.44) / (len(ranked) + 0.12)
    ranked["rank"] = rank
    ranked["return_period_years"] = 1 / exceedance_probability
    return ranked


def fit_models(maxima: pd.DataFrame) -> dict[str, FittedModel]:
    """Fit GEV, Gumbel and log-Pearson III models by maximum likelihood."""
    flows = maxima["peak_flow_m3s"].to_numpy(dtype=float)
    if len(flows) < 10 or np.any(flows <= 0):
        raise ValueError("At least ten positive annual maxima are required")
    gev = stats.genextreme.fit(flows)
    gumbel = stats.gumbel_r.fit(flows)
    log_flows = np.log10(flows)
    lp3 = stats.pearson3.fit(log_flows)
    return {
        "GEV": FittedModel("GEV", stats.genextreme, tuple(gev)),
        "Gumbel": FittedModel("Gumbel", stats.gumbel_r, tuple(gumbel)),
        "Log-Pearson III": FittedModel("Log-Pearson III", stats.pearson3, tuple(lp3)),
    }


def return_levels(models: dict[str, FittedModel], periods: list[int]) -> pd.DataFrame:
    """Evaluate fitted return levels for annual exceedance probabilities 1/T."""
    rows = []
    for name, model in models.items():
        values = model.distribution.ppf(1 - 1 / np.asarray(periods), *model.parameters)
        if name == "Log-Pearson III":
            values = 10**values
        rows.extend({"model": name, "return_period_years": t, "flow_m3s": float(q)} for t, q in zip(periods, values))
    return pd.DataFrame(rows)


def bootstrap_return_levels(maxima: pd.DataFrame, periods: list[int], repetitions: int = 500, seed: int = 19006) -> pd.DataFrame:
    """Non-parametric bootstrap 95% intervals, including refitting uncertainty."""
    rng = np.random.default_rng(seed)
    flows = maxima["peak_flow_m3s"].to_numpy()
    samples = []
    for iteration in range(repetitions):
        resampled = pd.DataFrame({"peak_flow_m3s": rng.choice(flows, len(flows), replace=True)})
        try:
            levels = return_levels(fit_models(resampled), periods)
            levels["iteration"] = iteration
            samples.append(levels)
        except (ValueError, FloatingPointError):
            continue
    boot = pd.concat(samples, ignore_index=True)
    return (
        boot.groupby(["model", "return_period_years"])["flow_m3s"]
        .quantile([0.025, 0.5, 0.975])
        .unstack()
        .rename(columns={0.025: "lower_95_m3s", 0.5: "median_m3s", 0.975: "upper_95_m3s"})
        .reset_index()
    )

