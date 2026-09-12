import pandas as pd

from water_of_leith.rainfall_runoff import event_rainfall_metrics


def test_event_rainfall_windows_end_at_peak_hour():
    times = pd.date_range("2020-01-01", periods=73, freq="h")
    rainfall = pd.DataFrame({
        "time": times,
        "rainfall_mm": 1.0,
        "statistical_disaggregation_fraction": 0.0,
        "maximum_gauge_distance_km": 8.0,
    })
    result = event_rainfall_metrics(rainfall, times[-1])
    assert result["rainfall_24h_mm"] == 24.0
    assert result["rainfall_48h_mm"] == 48.0
    assert result["rainfall_72h_mm"] == 72.0
