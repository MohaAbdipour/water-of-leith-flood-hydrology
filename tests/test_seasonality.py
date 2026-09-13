import numpy as np
import pandas as pd

from water_of_leith.seasonality import (
    circular_summary,
    expanding_splits,
    hydrological_year_angle,
    partial_spearman,
)


def test_hydrological_angle_starts_on_first_october():
    angles = hydrological_year_angle(pd.to_datetime(["2023-10-01", "2024-04-01"]))
    assert angles[0] == 0
    assert np.isclose(angles[1], np.pi, atol=0.03)


def test_circular_summary_detects_concentration():
    mean, resultant, p_value = circular_summary(np.array([0.0, 0.1, 2 * np.pi - 0.1]))
    assert np.isclose(mean, 0)
    assert resultant > 0.99
    assert p_value < 0.1


def test_partial_spearman_removes_shared_monotonic_control():
    rng = np.random.default_rng(42)
    control = rng.normal(size=500)
    x = 2 * control + rng.normal(size=500)
    y = -3 * control + rng.normal(size=500)
    assert abs(partial_spearman(x, y, control)) < 0.15


def test_expanding_splits_never_train_on_future_observations():
    splits = list(expanding_splits(10, initial=4, test_size=3))
    assert [pair[1].tolist() for pair in splits] == [[4, 5, 6], [7, 8, 9]]
    assert all(train.max() < test.min() for train, test in splits)
