"""Local validation against restricted NRFA peak-flow files.

NRFA source records must not be committed or redistributed. These functions
read a user-supplied `.am` file and return aggregate scientific diagnostics.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _section(lines: list[str], heading: str) -> list[str]:
    start = lines.index(heading) + 1
    end = lines.index("[END]", start)
    return lines[start:end]


def read_nrfa_am(path: str | Path) -> tuple[pd.DataFrame, set[int]]:
    """Parse AM values and rejected water years from a WINFAP-format file."""
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    rejected = {int(line.split(",")[0]) for line in _section(lines, "[AM Rejected]") if line.strip()}
    records = []
    for line in _section(lines, "[AM Values]"):
        date_text, flow_text, stage_text = (part.strip() for part in line.split(","))
        date = pd.to_datetime(date_text).tz_localize(None)
        water_year = int(date.year + (date.month >= 10))
        records.append({
            "water_year": water_year,
            "peak_date": date.normalize(),
            "peak_flow_m3s": float(flow_text),
            "peak_stage_m": float(stage_text),
            "accepted": water_year not in rejected,
        })
    return pd.DataFrame(records), rejected


def comparison_summary(ukflow_maxima: pd.DataFrame, nrfa_maxima: pd.DataFrame) -> dict[str, int | float]:
    """Summarise overlap without reproducing the licensed annual-maximum series."""
    accepted = nrfa_maxima[nrfa_maxima["accepted"]]
    joined = ukflow_maxima.merge(accepted, on="water_year", suffixes=("_ukflow", "_nrfa"))
    differences = joined["peak_flow_m3s_ukflow"] - joined["peak_flow_m3s_nrfa"]
    date_matches = joined["peak_datetime"].dt.normalize() == joined["peak_date"]
    return {
        "overlap_years": len(joined),
        "flow_matches_at_0_001_m3s": int(np.isclose(differences, 0, atol=0.001).sum()),
        "peak_date_matches": int(date_matches.sum()),
        "mean_bias_m3s": float(differences.mean()),
        "mae_m3s": float(differences.abs().mean()),
        "rmse_m3s": float(np.sqrt(np.mean(differences**2))),
        "maximum_absolute_difference_m3s": float(differences.abs().max()),
        "pearson_correlation": float(joined[["peak_flow_m3s_ukflow", "peak_flow_m3s_nrfa"]].corr().iloc[0, 1]),
        "nrfa_values": len(nrfa_maxima),
        "nrfa_rejected_values_present": int((~nrfa_maxima["accepted"]).sum()),
        "nrfa_accepted_years": int(nrfa_maxima["accepted"].sum()),
    }
