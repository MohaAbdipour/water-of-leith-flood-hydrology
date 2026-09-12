"""Generate annual-maximum fit and temporal-stability diagnostics."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from water_of_leith.diagnostics import fitted_quantiles, model_diagnostics, trend_summary
from water_of_leith.frequency import fit_models


def main() -> None:
    maxima = pd.read_csv("outputs/annual_maxima.csv", parse_dates=["peak_datetime"])
    models = fit_models(maxima)
    diagnostics = model_diagnostics(maxima, models)
    trend = trend_summary(maxima)
    diagnostics.to_csv("outputs/model_diagnostics.csv", index=False)
    pd.DataFrame([trend]).to_csv("outputs/temporal_stability.csv", index=False)

    ordered = np.sort(maxima["peak_flow_m3s"].to_numpy())
    probabilities = (np.arange(1, len(ordered) + 1) - 0.44) / (len(ordered) + 0.12)
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.5), sharex=True, sharey=True)
    for ax, (name, model) in zip(axes, models.items()):
        theoretical = fitted_quantiles(model, probabilities)
        low = min(ordered.min(), theoretical.min())
        high = max(ordered.max(), theoretical.max())
        ax.scatter(theoretical, ordered, color="#0072B2", s=28)
        ax.plot([low, high], [low, high], color="0.35", linestyle="--")
        ax.set(title=name, xlabel="Fitted quantile (m³/s)")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Observed annual maximum (m³/s)")
    fig.suptitle("Annual-maximum probability plots")
    fig.tight_layout()
    Path("docs/figures").mkdir(parents=True, exist_ok=True)
    fig.savefig("docs/figures/probability_plots.png", dpi=180)
    plt.close(fig)

    years = maxima["water_year"].to_numpy()
    slope = trend["theil_sen_slope_m3s_per_year"]
    intercept = np.median(maxima["peak_flow_m3s"] - slope * years)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(years, maxima["peak_flow_m3s"], label="Annual maxima")
    ax.plot(years, intercept + slope * years, color="#D55E00", label=f"Theil–Sen slope = {slope:.2f} m³/s/year")
    ax.axvline(trend["pettitt_change_after_water_year"], color="0.35", linestyle="--", label="Exploratory Pettitt split")
    ax.set(xlabel="Water year", ylabel="Annual maximum flow (m³/s)", title="Temporal-stability diagnostics")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig("docs/figures/temporal_stability.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()

