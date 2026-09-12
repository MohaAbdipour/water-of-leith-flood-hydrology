"""Assess sensitivity to the 2016–2017 rating and flood-defence transition."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from water_of_leith.frequency import fit_models, return_levels
from water_of_leith.rating_sensitivity import era_comparison, split_rating_eras


def main() -> None:
    maxima = pd.read_csv("outputs/annual_maxima.csv")
    eras = split_rating_eras(maxima)
    comparison = era_comparison(maxima)
    pd.DataFrame([comparison]).to_csv("outputs/rating_era_comparison.csv", index=False)

    full_q100 = return_levels(fit_models(maxima), [100]).rename(columns={"flow_m3s": "q100_all_years_m3s"})
    without_transition = return_levels(fit_models(maxima[maxima["water_year"] != 2017]), [100]).rename(
        columns={"flow_m3s": "q100_excluding_2017_m3s"}
    )
    sensitivity = full_q100.merge(without_transition, on=["model", "return_period_years"])
    sensitivity["absolute_change_m3s"] = sensitivity["q100_excluding_2017_m3s"] - sensitivity["q100_all_years_m3s"]
    sensitivity["relative_change_percent"] = 100 * sensitivity["absolute_change_m3s"] / sensitivity["q100_all_years_m3s"]
    sensitivity.to_csv("outputs/rating_transition_q100_sensitivity.csv", index=False)

    groups = [
        eras.loc[eras["rating_era"] == era, "peak_flow_m3s"].to_numpy()
        for era in ["pre-works", "transition", "post-works"]
    ]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].boxplot(groups, tick_labels=["Pre-works\n≤2016", "Transition\n2017", "Post-works\n≥2018"], showmeans=True)
    rng = np.random.default_rng(19006)
    for position, values in enumerate(groups, start=1):
        axes[0].scatter(position + rng.normal(0, 0.035, len(values)), values, alpha=0.75, s=25)
    axes[0].set(ylabel="Annual maximum flow (m³/s)", title="Observed rating-era groups")
    x = np.arange(len(sensitivity))
    width = 0.36
    axes[1].bar(x - width / 2, sensitivity["q100_all_years_m3s"], width, label="All complete years")
    axes[1].bar(x + width / 2, sensitivity["q100_excluding_2017_m3s"], width, label="Transition year excluded")
    axes[1].set_xticks(x, sensitivity["model"])
    axes[1].set(ylabel="Estimated Q100 (m³/s)", title="Transition-year sensitivity")
    axes[1].legend()
    for ax in axes:
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("Sensitivity to the 2016–2017 Murrayfield rating transition")
    fig.tight_layout()
    fig.savefig("docs/figures/rating_transition_sensitivity.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()

