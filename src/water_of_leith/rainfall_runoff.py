"""Rainfall metrics aligned to observed flood peaks."""

from __future__ import annotations

import pandas as pd


def event_rainfall_metrics(rainfall: pd.DataFrame, peak_time: pd.Timestamp) -> dict[str, object]:
    """Summarise catchment rainfall ending at one observed flow peak."""
    data = rainfall.sort_values("time").set_index("time")
    peak_time = pd.Timestamp(peak_time).floor("h")
    antecedent = data.loc[peak_time - pd.Timedelta(hours=72):peak_time]
    if len(antecedent) < 70:
        raise ValueError("Insufficient hourly rainfall coverage around flow peak")
    wettest_time = antecedent["rainfall_mm"].idxmax()
    return {
        "peak_hour": peak_time,
        "rainfall_24h_mm": float(antecedent.loc[peak_time - pd.Timedelta(hours=23):, "rainfall_mm"].sum()),
        "rainfall_48h_mm": float(antecedent.loc[peak_time - pd.Timedelta(hours=47):, "rainfall_mm"].sum()),
        "rainfall_72h_mm": float(antecedent.loc[peak_time - pd.Timedelta(hours=71):, "rainfall_mm"].sum()),
        "maximum_hourly_rainfall_mm": float(antecedent["rainfall_mm"].max()),
        "hours_from_rainfall_maximum_to_flow_peak": float((peak_time - wettest_time) / pd.Timedelta(hours=1)),
        "mean_disaggregation_fraction": float(antecedent["statistical_disaggregation_fraction"].mean()),
        "maximum_disaggregation_fraction": float(antecedent["statistical_disaggregation_fraction"].max()),
        "maximum_gauge_distance_km": float(antecedent["maximum_gauge_distance_km"].max()),
    }
