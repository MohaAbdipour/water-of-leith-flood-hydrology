import pandas as pd
from pathlib import Path

from water_of_leith.frequency import annual_maxima, empirical_return_periods, validate_series
from water_of_leith.nrfa import read_nrfa_am


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


def test_nrfa_parser_marks_rejected_year(tmp_path: Path):
    source = tmp_path / "station.am"
    source.write_text(
        "[AM Rejected]\n2020,2020\n[END]\n[AM Values]\n"
        "2020-01-02 00:00:00Z,10.500,1.200\n"
        "2020-11-03 00:00:00Z,12.000,1.300\n[END]\n"
    )
    values, rejected = read_nrfa_am(source)
    assert rejected == {2020}
    assert values["water_year"].tolist() == [2020, 2021]
    assert values["accepted"].tolist() == [False, True]
