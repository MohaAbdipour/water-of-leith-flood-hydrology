"""Assess how the POT model responds to alternative event-separation rules."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from water_of_leith.frequency import read_ukflow15
from water_of_leith.pot import (
    decluster_exceedances,
    fit_gpd,
    gpd_return_level,
    ljung_box_rank_test,
)


def main() -> None:
    data = read_ukflow15("data/raw/019006.csv")
    threshold = float(data["value"].quantile(0.997))
    rows = []
    for hours in [24, 48, 72, 96, 120, 168]:
        peaks = decluster_exceedances(data, threshold, f"{hours}h")
        fit = fit_gpd(data, peaks, threshold)
        q_statistic, p_value = ljung_box_rank_test(peaks["value"], max_lag=5)
        rows.append({
            "run_length_hours": hours,
            "threshold_m3s": threshold,
            "independent_events": fit.event_count,
            "events_per_year": fit.event_rate_per_year,
            "gpd_shape": fit.shape,
            "gpd_scale_m3s": fit.scale,
            "q100_m3s": gpd_return_level(fit, 100),
            "rank_ljung_box_lags": 5,
            "rank_ljung_box_q": q_statistic,
            "rank_ljung_box_p": p_value,
        })

    results = pd.DataFrame(rows)
    results.to_csv("outputs/pot_independence_sensitivity.csv", index=False)

    figure_dir = Path("docs/figures")
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(results["run_length_hours"], results["independent_events"], marker="o")
    axes[0].set(xlabel="Minimum below-threshold run (hours)", ylabel="Retained events", title="Event count")
    axes[1].plot(results["run_length_hours"], results["q100_m3s"], marker="o", color="#D55E00")
    axes[1].set(xlabel="Minimum below-threshold run (hours)", ylabel="Estimated Q100 (m³/s)", title="Return-level sensitivity")
    for ax in axes:
        ax.grid(alpha=0.25)
    fig.suptitle("POT sensitivity to event-separation rule")
    fig.tight_layout()
    fig.savefig(figure_dir / "pot_independence_sensitivity.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
