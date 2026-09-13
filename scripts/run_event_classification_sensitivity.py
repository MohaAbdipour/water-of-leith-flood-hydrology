"""Test storm-duration and peak-morphology classifications for robustness."""

from __future__ import annotations

from itertools import product
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from water_of_leith.event_classification import (
    classification_agreement,
    count_event_peaks,
    duration_class,
)
from water_of_leith.frequency import read_ukflow15


def main() -> None:
    flow = read_ukflow15("data/raw/019006.csv").set_index("datetime")["value"]
    rain = pd.read_csv(
        "data/raw/ceh_gear1hr_19006.csv", parse_dates=["time"]
    ).set_index("time")["rainfall_mm"]
    events = pd.read_csv(
        "outputs/flood_event_classification.csv", parse_dates=["flow_peak_datetime"]
    )

    duration_settings = list(product([9, 12, 15], [30, 36, 42]))
    peak_settings = list(product([1, 3, 5], [4, 6, 9, 12], [0.075, 0.10, 0.15]))
    scenario_rows: list[dict] = []
    event_labels: dict[pd.Timestamp, dict[str, list[str]]] = {
        peak: {"duration": [], "rain": [], "flow": []}
        for peak in events["flow_peak_datetime"]
    }

    baseline_duration = events["rainfall_duration_class"]
    for lower, upper in duration_settings:
        labels = events["rainfall_duration_10_90_hours"].map(
            lambda value: duration_class(value, lower, upper)
        )
        for peak, label in zip(events["flow_peak_datetime"], labels):
            event_labels[peak]["duration"].append(label)
        counts = labels.value_counts()
        scenario_rows.append({
            "scenario_family": "duration",
            "smoothing_hours": np.nan,
            "minimum_separation_hours": np.nan,
            "prominence_range_fraction": np.nan,
            "concentrated_limit_hours": lower,
            "prolonged_limit_hours": upper,
            "agreement_with_baseline": classification_agreement(baseline_duration, labels),
            "concentrated_events": int(counts.get("concentrated", 0)),
            "intermediate_events": int(counts.get("intermediate", 0)),
            "prolonged_events": int(counts.get("prolonged", 0)),
            "single_rainfall_events": np.nan,
            "single_hydrograph_events": np.nan,
        })

    baseline_rain = events["rainfall_structure"]
    baseline_flow = events["hydrograph_structure"]
    for smoothing, separation, prominence in peak_settings:
        rain_labels, flow_labels = [], []
        for event in events.itertuples(index=False):
            peak = event.flow_peak_datetime
            rain_window = rain.loc[
                peak.floor("h") - pd.Timedelta(hours=71):peak.floor("h")
            ]
            flow_window = flow.loc[
                peak - pd.Timedelta(hours=72):peak + pd.Timedelta(hours=48)
            ].resample("h").max()
            kwargs = {
                "smoothing_hours": smoothing,
                "minimum_separation_hours": separation,
                "prominence_range_fraction": prominence,
            }
            rain_label = (
                "single-burst" if count_event_peaks(rain_window, **kwargs) <= 1
                else "multi-burst"
            )
            flow_label = (
                "single-peak" if count_event_peaks(flow_window, **kwargs) <= 1
                else "multi-peak"
            )
            rain_labels.append(rain_label)
            flow_labels.append(flow_label)
            event_labels[peak]["rain"].append(rain_label)
            event_labels[peak]["flow"].append(flow_label)
        rain_series = pd.Series(rain_labels)
        flow_series = pd.Series(flow_labels)
        scenario_rows.append({
            "scenario_family": "peak morphology",
            "smoothing_hours": smoothing,
            "minimum_separation_hours": separation,
            "prominence_range_fraction": prominence,
            "concentrated_limit_hours": np.nan,
            "prolonged_limit_hours": np.nan,
            "agreement_with_baseline": np.nan,
            "rainfall_agreement_with_baseline": classification_agreement(baseline_rain, rain_series),
            "hydrograph_agreement_with_baseline": classification_agreement(baseline_flow, flow_series),
            "concentrated_events": np.nan,
            "intermediate_events": np.nan,
            "prolonged_events": np.nan,
            "single_rainfall_events": int((rain_series == "single-burst").sum()),
            "single_hydrograph_events": int((flow_series == "single-peak").sum()),
        })

    scenarios = pd.DataFrame(scenario_rows)
    scenarios.to_csv("outputs/event_classification_sensitivity.csv", index=False)

    stability_rows = []
    for event in events.itertuples(index=False):
        labels = event_labels[event.flow_peak_datetime]
        stability_rows.append({
            "flow_peak_datetime": event.flow_peak_datetime,
            "peak_flow_m3s": event.peak_flow_m3s,
            "baseline_duration_class": event.rainfall_duration_class,
            "duration_class_stability": labels["duration"].count(event.rainfall_duration_class) / len(labels["duration"]),
            "baseline_rainfall_structure": event.rainfall_structure,
            "rainfall_structure_stability": labels["rain"].count(event.rainfall_structure) / len(labels["rain"]),
            "baseline_hydrograph_structure": event.hydrograph_structure,
            "hydrograph_structure_stability": labels["flow"].count(event.hydrograph_structure) / len(labels["flow"]),
        })
    stability = pd.DataFrame(stability_rows)
    stability.to_csv("outputs/event_classification_event_stability.csv", index=False)

    duration_rows = scenarios[scenarios["scenario_family"] == "duration"]
    morphology_rows = scenarios[scenarios["scenario_family"] == "peak morphology"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), constrained_layout=True)
    axes[0].boxplot(
        [
            stability["duration_class_stability"],
            stability["rainfall_structure_stability"],
            stability["hydrograph_structure_stability"],
        ],
        tick_labels=["Duration\nclass", "Rainfall\nstructure", "Hydrograph\nstructure"],
    )
    axes[0].set_ylabel("Fraction of scenarios retaining baseline label")
    axes[0].set_ylim(-0.02, 1.02)
    axes[0].set_title("Event-level classification stability", loc="left")
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].plot(duration_rows["concentrated_limit_hours"], duration_rows["concentrated_events"], "o", label="Concentrated")
    axes[1].plot(duration_rows["prolonged_limit_hours"], duration_rows["prolonged_events"], "s", label="Prolonged")
    axes[1].set(xlabel="Applied duration boundary (h)", ylabel="Number of events", title="Duration-class sensitivity")
    axes[1].legend()
    axes[1].grid(alpha=0.25)

    axes[2].scatter(
        morphology_rows["rainfall_agreement_with_baseline"],
        morphology_rows["hydrograph_agreement_with_baseline"],
        c=morphology_rows["prominence_range_fraction"],
        cmap="viridis",
        edgecolor="white",
    )
    axes[2].set(
        xlabel="Rainfall-structure agreement",
        ylabel="Hydrograph-structure agreement",
        title="Sensitivity to peak-detection settings",
        xlim=(0, 1.02),
        ylim=(0, 1.02),
    )
    axes[2].grid(alpha=0.25)
    fig.savefig("docs/figures/event_classification_sensitivity.png", dpi=200)
    plt.close(fig)

    print("Duration agreement range:", duration_rows["agreement_with_baseline"].min(), duration_rows["agreement_with_baseline"].max())
    print("Rainfall agreement range:", morphology_rows["rainfall_agreement_with_baseline"].min(), morphology_rows["rainfall_agreement_with_baseline"].max())
    print("Hydrograph agreement range:", morphology_rows["hydrograph_agreement_with_baseline"].min(), morphology_rows["hydrograph_agreement_with_baseline"].max())
    print("Median event stability:", stability[["duration_class_stability", "rainfall_structure_stability", "hydrograph_structure_stability"]].median().to_dict())


if __name__ == "__main__":
    main()
