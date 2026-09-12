"""Run open-data POT/GPD analysis and threshold-sensitivity diagnostics."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from water_of_leith.frequency import read_ukflow15
from water_of_leith.pot import bootstrap_gpd_levels, decluster_exceedances, fit_gpd, gpd_return_level


def main() -> None:
    data = read_ukflow15("data/raw/019006.csv")
    periods = [2, 5, 10, 20, 50, 100, 200]
    quantiles = [0.995, 0.996, 0.997, 0.998, 0.999]
    sensitivity = []
    selected = None

    for quantile in quantiles:
        threshold = float(data["value"].quantile(quantile))
        peaks = decluster_exceedances(data, threshold, "72h")
        fit = fit_gpd(data, peaks, threshold)
        sensitivity.append({
            "threshold_quantile": quantile,
            "threshold_m3s": threshold,
            "independent_events": fit.event_count,
            "events_per_year": fit.event_rate_per_year,
            "gpd_shape": fit.shape,
            "gpd_scale_m3s": fit.scale,
            "q100_m3s": gpd_return_level(fit, 100),
        })
        if quantile == 0.997:
            selected = (peaks, fit)

    assert selected is not None
    peaks, fit = selected
    levels = pd.DataFrame({
        "return_period_years": periods,
        "flow_m3s": [gpd_return_level(fit, period) for period in periods],
    })
    intervals = bootstrap_gpd_levels(fit, peaks, periods)
    levels = levels.merge(intervals, on="return_period_years")
    levels.insert(0, "model", "POT-GPD")
    levels.to_csv("outputs/pot_return_levels.csv", index=False)
    pd.DataFrame(sensitivity).to_csv("outputs/pot_threshold_sensitivity.csv", index=False)
    pd.DataFrame([{
        "threshold_quantile": 0.997,
        "threshold_m3s": fit.threshold,
        "run_length_hours": 72,
        "independent_events": fit.event_count,
        "events_per_year": fit.event_rate_per_year,
        "gpd_shape": fit.shape,
        "gpd_scale_m3s": fit.scale,
    }]).to_csv("outputs/pot_model_summary.csv", index=False)

    figure_dir = Path("docs/figures")
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    table = pd.DataFrame(sensitivity)
    axes[0].plot(table["threshold_quantile"] * 100, table["gpd_shape"], marker="o")
    axes[0].axhline(0, color="0.4", linewidth=1, linestyle="--")
    axes[0].set(xlabel="Threshold percentile", ylabel="GPD shape parameter", title="Parameter stability")
    axes[1].plot(table["threshold_quantile"] * 100, table["q100_m3s"], marker="o", color="#D55E00")
    axes[1].set(xlabel="Threshold percentile", ylabel="Estimated Q100 (m³/s)", title="Return-level sensitivity")
    for ax in axes:
        ax.grid(alpha=0.25)
    fig.suptitle("POT threshold sensitivity: 72-hour run declustering")
    fig.tight_layout()
    fig.savefig(figure_dir / "pot_threshold_sensitivity.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()

