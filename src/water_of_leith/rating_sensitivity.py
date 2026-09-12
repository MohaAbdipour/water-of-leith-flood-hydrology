"""Sensitivity diagnostics around the 2016–2017 Murrayfield rating transition."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def split_rating_eras(maxima: pd.DataFrame) -> pd.DataFrame:
    """Label pre-works, transition and post-works water years."""
    frame = maxima.copy()
    frame["rating_era"] = np.select(
        [frame["water_year"] <= 2016, frame["water_year"] == 2017, frame["water_year"] >= 2018],
        ["pre-works", "transition", "post-works"],
        default="unclassified",
    )
    return frame


def era_comparison(maxima: pd.DataFrame, repetitions: int = 10000, seed: int = 19006) -> dict[str, float | int]:
    """Compare pre/post medians with a rank test and bootstrap interval.

    The tests diagnose a distributional difference; they cannot attribute any
    difference specifically to rating changes rather than hydrological variation.
    """
    frame = split_rating_eras(maxima)
    pre = frame.loc[frame["rating_era"] == "pre-works", "peak_flow_m3s"].to_numpy()
    post = frame.loc[frame["rating_era"] == "post-works", "peak_flow_m3s"].to_numpy()
    test = stats.mannwhitneyu(pre, post, alternative="two-sided")
    rng = np.random.default_rng(seed)
    differences = np.empty(repetitions)
    for index in range(repetitions):
        differences[index] = np.median(rng.choice(post, len(post), replace=True)) - np.median(rng.choice(pre, len(pre), replace=True))
    lower, upper = np.quantile(differences, [0.025, 0.975])
    return {
        "pre_years": len(pre),
        "post_years": len(post),
        "pre_median_m3s": float(np.median(pre)),
        "post_median_m3s": float(np.median(post)),
        "post_minus_pre_median_m3s": float(np.median(post) - np.median(pre)),
        "bootstrap_difference_lower_95_m3s": float(lower),
        "bootstrap_difference_upper_95_m3s": float(upper),
        "mann_whitney_u": float(test.statistic),
        "mann_whitney_p_value": float(test.pvalue),
    }

