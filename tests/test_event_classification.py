import numpy as np
import pandas as pd

from water_of_leith.event_classification import (
    count_event_peaks,
    cumulative_rainfall_duration,
    duration_class,
    rainfall_centroid_lag,
)


def test_cumulative_duration_and_class_are_explicit():
    rainfall = pd.Series(np.ones(10), index=pd.date_range("2020-01-01", periods=10, freq="h"))
    assert cumulative_rainfall_duration(rainfall) == 8.0
    assert duration_class(8.0) == "concentrated"


def test_duration_boundaries_are_configurable_and_ordered():
    assert duration_class(14, concentrated_limit=15, prolonged_limit=42) == "concentrated"
    assert duration_class(40, concentrated_limit=15, prolonged_limit=42) == "intermediate"
    with np.testing.assert_raises(ValueError):
        duration_class(20, concentrated_limit=36, prolonged_limit=12)


def test_peak_counter_separates_two_prominent_bursts():
    values = pd.Series([0, 0, 3, 5, 3, 0, 0, 0, 0, 4, 6, 4, 0, 0], dtype=float)
    assert count_event_peaks(values, smoothing_hours=1, minimum_separation_hours=4) == 2


def test_peak_prominence_is_configurable():
    values = pd.Series([0, 4, 0, 1, 0], dtype=float)
    assert count_event_peaks(
        values, smoothing_hours=1, minimum_separation_hours=1,
        prominence_range_fraction=0.1,
    ) == 2
    assert count_event_peaks(
        values, smoothing_hours=1, minimum_separation_hours=1,
        prominence_range_fraction=0.3,
    ) == 1


def test_rainfall_centroid_lag_for_single_pulse():
    index = pd.date_range("2020-01-01", periods=5, freq="h")
    rainfall = pd.Series([0, 0, 2, 0, 0], index=index)
    assert rainfall_centroid_lag(rainfall, index[-1]) == 2.0
