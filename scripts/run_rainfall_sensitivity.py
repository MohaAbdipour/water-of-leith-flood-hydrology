"""Assess rainfall-flow results under alternative CEH-GEAR1hr quality filters."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from water_of_leith.rainfall_sensitivity import sensitivity_table


def main() -> None:
    events = pd.read_csv("outputs/rainfall_linked_flood_events.csv")
    results = sensitivity_table(events)
    results.to_csv("outputs/rainfall_quality_sensitivity.csv", index=False)

    selected = results.loc[results["rainfall_duration_hours"] == 72].copy()
    positions = range(len(selected))
    lower_error = selected["spearman_rho"] - selected["bootstrap_lower_95"]
    upper_error = selected["bootstrap_upper_95"] - selected["spearman_rho"]
    fig, axis = plt.subplots(figsize=(11, 6))
    axis.errorbar(
        positions,
        selected["spearman_rho"],
        yerr=[lower_error, upper_error],
        fmt="o",
        capsize=4,
        color="#0072B2",
    )
    axis.axhline(0, color="0.4", linewidth=1)
    labels = [f"{label}\n(n={count})" for label, count in zip(selected["quality_subset"], selected["events"])]
    axis.set_xticks(list(positions), labels, rotation=20, ha="right")
    axis.set_ylabel("Spearman correlation with 72-hour rainfall")
    axis.set_title("Rainfall–flow association under CEH-GEAR1hr quality filters")
    axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    output = Path("docs/figures/rainfall_quality_sensitivity.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
