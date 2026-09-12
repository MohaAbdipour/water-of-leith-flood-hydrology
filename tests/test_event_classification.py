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
    assert duration_class(8.0) == "concentrated (≤12 h)"


def test_peak_counter_separates_two_prominent_bursts():
    values = pd.Series([0, 0, 3, 5, 3, 0, 0, 0, 0, 4, 6, 4, 0, 0], dtype=float)
    assert count_event_peaks(values, smoothing_hours=1, minimum_separation_hours=4) == 2


def test_rainfall_centroid_lag_for_single_pulse():
    index = pd.date_range("2020-01-01", periods=5, freq="h")
    rainfall = pd.Series([0, 0, 2, 0, 0], index=index)
    assert rainfall_centroid_lag(rainfall, index[-1]) == 2.0
