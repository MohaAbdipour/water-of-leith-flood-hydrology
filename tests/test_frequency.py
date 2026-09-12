import pandas as pd

from water_of_leith.frequency import annual_maxima, empirical_return_periods, validate_series


def test_complete_water_year_and_peak_are_extracted():
    time = pd.date_range("2019-10-01", "2020-09-30 23:45", freq="15min")
    data = pd.DataFrame({"datetime": time, "value": 1.0, "resolution": 15, "flag": "000"})
    data.loc[100, "value"] = 12.5
    maxima = annual_maxima(data)
    assert maxima.loc[0, "water_year"] == 2020
    assert maxima.loc[0, "peak_flow_m3s"] == 12.5


def test_partial_water_year_is_excluded():
    time = pd.date_range("2020-01-01", "2020-09-30 23:45", freq="15min")
    data = pd.DataFrame({"datetime": time, "value": 1.0, "resolution": 15, "flag": "000"})
    assert annual_maxima(data).empty


def test_gringorten_return_periods_decrease_with_rank():
    maxima = pd.DataFrame({"peak_flow_m3s": [10.0, 30.0, 20.0]})
    ranked = empirical_return_periods(maxima)
    assert ranked["peak_flow_m3s"].tolist() == [30.0, 20.0, 10.0]
    assert ranked["return_period_years"].is_monotonic_decreasing


def test_validation_rejects_duplicate_timestamps():
    data = pd.DataFrame({
        "datetime": pd.to_datetime(["2020-01-01", "2020-01-01"]),
        "value": [1.0, 1.1], "resolution": [15, 15], "flag": ["000", "000"]
    })
    try:
        validate_series(data)
    except ValueError:
        return
    raise AssertionError("duplicate timestamps should fail validation")

