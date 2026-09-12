import numpy as np
import pandas as pd

from water_of_leith.rainfall_sensitivity import bootstrap_spearman_interval, quality_subsets


def test_quality_subsets_are_not_larger_than_full_sample():
    events = pd.DataFrame({
        "mean_disaggregation_fraction": [0.0, 0.2, 0.5],
        "maximum_disaggregation_fraction": [0.0, 1.0, 1.0],
        "maximum_gauge_distance_km": [8.0, 9.0, 15.0],
    })
    subsets = quality_subsets(events)
    assert subsets["All events"].sum() == 3
    assert all(mask.sum() <= 3 for mask in subsets.values())


def test_bootstrap_interval_contains_strong_monotonic_association():
    x = np.arange(20, dtype=float)
    lower, upper = bootstrap_spearman_interval(x, x, repetitions=100, seed=1)
    assert lower > 0.99
    assert upper <= 1.0
