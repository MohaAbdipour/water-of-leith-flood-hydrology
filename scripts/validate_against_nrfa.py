"""Validate UK-Flow15 AMAX against a locally supplied NRFA v15 file.

The script writes aggregate diagnostics and fitted return levels only. It does
not copy, transform or export the restricted row-level NRFA data.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from water_of_leith.frequency import bootstrap_return_levels, fit_models, read_ukflow15, return_levels
from water_of_leith.diagnostics import model_diagnostics, trend_summary
from water_of_leith.nrfa import (
    comparison_summary,
    pot_comparison_summary,
    read_nrfa_am,
    read_nrfa_pot,
)

NRFA_FILE = Path("data/restricted/nrfa-v15/suitable-for-pooling/019006-water-of-leith-at-murrayfield.am")
NRFA_POT_FILE = NRFA_FILE.with_suffix(".pt")


def main() -> None:
    if not NRFA_FILE.exists():
        raise FileNotFoundError("Place an authorised NRFA v15 extraction under data/restricted; see docs/nrfa-validation.md")
    ukflow = pd.read_csv("outputs/annual_maxima.csv", parse_dates=["peak_datetime"])
    nrfa, rejected = read_nrfa_am(NRFA_FILE)
    accepted = nrfa[nrfa["accepted"]][["peak_flow_m3s"]]

    summary = comparison_summary(ukflow, nrfa)
    summary.update({
        "nrfa_version": "15.0.2",
        "nrfa_rejected_years_listed": len(rejected),
        "nrfa_first_accepted_water_year": int(nrfa.loc[nrfa["accepted"], "water_year"].min()),
        "nrfa_last_accepted_water_year": int(nrfa.loc[nrfa["accepted"], "water_year"].max()),
        "nrfa_at_site_qmed_m3s": float(accepted["peak_flow_m3s"].median()),
    })
    pd.DataFrame([summary]).to_csv("outputs/nrfa_validation_summary.csv", index=False)

    ukflow_series = read_ukflow15("data/raw/019006.csv")
    nrfa_pot = read_nrfa_pot(NRFA_POT_FILE)
    pd.DataFrame([pot_comparison_summary(ukflow_series, nrfa_pot)]).to_csv(
        "outputs/nrfa_pot_validation_summary.csv", index=False
    )

    periods = [2, 5, 10, 20, 50, 100, 200]
    levels = return_levels(fit_models(accepted), periods)
    intervals = bootstrap_return_levels(accepted, periods)
    full_results = levels.merge(intervals, on=["model", "return_period_years"])
    full_results.to_csv("outputs/nrfa_full_record_return_levels.csv", index=False)
    full_for_analysis = nrfa.loc[nrfa["accepted"], ["water_year", "peak_flow_m3s"]]
    model_diagnostics(full_for_analysis, fit_models(full_for_analysis)).to_csv(
        "outputs/nrfa_full_record_model_diagnostics.csv", index=False
    )
    pd.DataFrame([trend_summary(full_for_analysis)]).to_csv(
        "outputs/nrfa_full_record_temporal_stability.csv", index=False
    )

    overlap_results = pd.read_csv("outputs/return_levels.csv")
    overlap_q100 = overlap_results[overlap_results["return_period_years"] == 100].set_index("model")
    full_q100 = full_results[full_results["return_period_years"] == 100].set_index("model")
    names = ["GEV", "Gumbel", "Log-Pearson III"]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for offset, label, table, colour in [
        (-0.12, "UK-Flow15 overlap: 31 years", overlap_q100, "#D55E00"),
        (0.12, "NRFA accepted record: 62 years", full_q100, "#0072B2"),
    ]:
        estimates = table.loc[names, "flow_m3s"].to_numpy()
        lower = estimates - table.loc[names, "lower_95_m3s"].to_numpy()
        upper = table.loc[names, "upper_95_m3s"].to_numpy() - estimates
        ax.errorbar(x + offset, estimates, yerr=[lower, upper], fmt="o", capsize=5, label=label, color=colour)
    ax.set_xticks(x, names)
    ax.set(ylabel="Estimated Q100 (m³/s)", title="Record length and Q100 sampling uncertainty")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig("docs/figures/record_length_q100.png", dpi=180)
    plt.close(fig)
    print("NRFA validation completed; restricted row-level records were not exported.")


if __name__ == "__main__":
    main()
