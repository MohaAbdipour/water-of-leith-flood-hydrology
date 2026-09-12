"""Run the observed annual-maximum flood-frequency analysis."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from water_of_leith.frequency import (
    annual_maxima,
    bootstrap_return_levels,
    empirical_return_periods,
    fit_models,
    read_ukflow15,
    return_levels,
    validate_series,
)


def main() -> None:
    raw = Path("data/raw/019006.csv")
    if not raw.exists():
        raise FileNotFoundError("Run python scripts/download_ukflow15.py first")
    outputs = Path("outputs")
    figures = Path("docs/figures")
    outputs.mkdir(exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    data = read_ukflow15(str(raw))
    diagnostics = validate_series(data)
    maxima = annual_maxima(data)
    empirical = empirical_return_periods(maxima)
    models = fit_models(maxima)
    periods = [2, 5, 10, 20, 50, 100, 200]
    levels = return_levels(models, periods)
    intervals = bootstrap_return_levels(maxima, periods)

    pd.DataFrame([diagnostics]).to_csv(outputs / "series_diagnostics.csv", index=False)
    maxima.to_csv(outputs / "annual_maxima.csv", index=False)
    levels.merge(intervals, on=["model", "return_period_years"]).to_csv(outputs / "return_levels.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(maxima["water_year"], maxima["peak_flow_m3s"], marker="o", linewidth=1.2)
    ax.axhline(maxima["peak_flow_m3s"].median(), color="0.35", linestyle="--", label=f"QMED = {maxima['peak_flow_m3s'].median():.1f} m³/s")
    ax.set(xlabel="Water year", ylabel="Annual maximum flow (m³/s)", title="Water of Leith at Murrayfield: annual maximum series")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures / "annual_maxima.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.scatter(empirical["return_period_years"], empirical["peak_flow_m3s"], color="black", label="Observed AMAX (Gringorten)", zorder=4)
    curve_periods = np.geomspace(1.01, 250, 300)
    for name, model in models.items():
        curve = return_levels({name: model}, curve_periods.tolist())
        ax.plot(curve["return_period_years"], curve["flow_m3s"], label=name)
    ax.set_xscale("log")
    ax.set(xlabel="Return period (years, log scale)", ylabel="Peak flow (m³/s)", title="Independent statistical flood-frequency estimates")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures / "frequency_curves.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
