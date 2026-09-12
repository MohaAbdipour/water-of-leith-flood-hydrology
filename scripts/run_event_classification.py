"""Describe rainfall structure and hydrograph response for linked flood events."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from water_of_leith.event_classification import (
    count_event_peaks,
    cumulative_rainfall_duration,
    duration_class,
    rainfall_centroid_lag,
    recession_half_time,
    rising_limb_duration,
)
from water_of_leith.frequency import read_ukflow15


def main() -> None:
    flow = read_ukflow15("data/raw/019006.csv").set_index("datetime")["value"]
    rain = pd.read_csv("data/raw/ceh_gear1hr_19006.csv", parse_dates=["time"]).set_index("time")["rainfall_mm"]
    events = pd.read_csv("outputs/rainfall_linked_flood_events.csv", parse_dates=["flow_peak_datetime"])
    rows = []
    for event in events.itertuples(index=False):
        peak = event.flow_peak_datetime
        rain_window = rain.loc[peak.floor("h") - pd.Timedelta(hours=71):peak.floor("h")]
        flow_window = flow.loc[peak - pd.Timedelta(hours=72):peak + pd.Timedelta(hours=48)]
        hourly_flow = flow_window.resample("h").max()
        duration = cumulative_rainfall_duration(rain_window)
        rainfall_peaks = count_event_peaks(rain_window, 3, 6)
        hydrograph_peaks = count_event_peaks(hourly_flow, 3, 6)
        rows.append({
            "flow_peak_datetime": peak,
            "peak_flow_m3s": event.peak_flow_m3s,
            "rainfall_duration_10_90_hours": duration,
            "rainfall_duration_class": duration_class(duration),
            "rainfall_peak_count": rainfall_peaks,
            "rainfall_structure": "single-burst" if rainfall_peaks <= 1 else "multi-burst",
            "hydrograph_peak_count": hydrograph_peaks,
            "hydrograph_structure": "single-peak" if hydrograph_peaks <= 1 else "multi-peak",
            "rainfall_centroid_to_flow_peak_hours": rainfall_centroid_lag(rain_window, peak),
            "rising_limb_10_percent_hours": rising_limb_duration(flow_window, peak),
            "recession_half_time_hours": recession_half_time(flow_window, peak),
        })
    classified = pd.DataFrame(rows)
    classified.to_csv("outputs/flood_event_classification.csv", index=False)

    summary = (
        classified.groupby(["rainfall_duration_class", "rainfall_structure", "hydrograph_structure"], dropna=False)
        .agg(
            events=("peak_flow_m3s", "size"),
            median_peak_flow_m3s=("peak_flow_m3s", "median"),
            median_centroid_lag_hours=("rainfall_centroid_to_flow_peak_hours", "median"),
            median_rising_limb_hours=("rising_limb_10_percent_hours", "median"),
            median_recession_half_time_hours=("recession_half_time_hours", "median"),
        )
        .reset_index()
    )
    summary.to_csv("outputs/flood_event_class_summary.csv", index=False)

    colours = {"single-peak": "#0072B2", "multi-peak": "#D55E00"}
    fig, axis = plt.subplots(figsize=(10, 6))
    for structure, group in classified.groupby("hydrograph_structure"):
        axis.scatter(
            group["rainfall_duration_10_90_hours"], group["peak_flow_m3s"],
            label=f"{structure} (n={len(group)})", alpha=0.8, color=colours[structure],
        )
    axis.axvline(12, color="0.5", linestyle="--", linewidth=1)
    axis.axvline(36, color="0.5", linestyle="--", linewidth=1)
    axis.set(
        xlabel="Rainfall D10–90 duration (hours)",
        ylabel="Peak flow (m³/s)",
        title="Storm duration and observed flood-hydrograph structure",
    )
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    output = Path("docs/figures/flood_event_classification.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
