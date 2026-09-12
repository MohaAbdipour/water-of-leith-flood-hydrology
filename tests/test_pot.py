import pandas as pd
from pathlib import Path

from water_of_leith.pot import GPDFit, decluster_exceedances, gpd_return_level
from water_of_leith.nrfa import read_nrfa_pot


def test_decluster_retains_largest_peak_within_run():
    data = pd.DataFrame({
        "datetime": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-10"]),
        "value": [11.0, 15.0, 12.0],
        "flag": ["000", "000", "000"],
    })
    peaks = decluster_exceedances(data, threshold=10.0, run_length="72h")
    assert peaks["value"].tolist() == [15.0, 12.0]


def test_return_level_increases_with_period():
    fit = GPDFit(threshold=10.0, shape=0.1, scale=3.0, event_rate_per_year=3.0, event_count=60, record_years=20.0)
    assert gpd_return_level(fit, 100) > gpd_return_level(fit, 10)


def test_nrfa_pot_parser(tmp_path: Path):
    source = tmp_path / "station.pt"
    source.write_text(
        "[POT Values]\n2020-01-02 03:15:00Z,10.500,1.200\n[END]\n"
    )
    values = read_nrfa_pot(source)
    assert values.loc[0, "peak_datetime"] == pd.Timestamp("2020-01-02 03:15")
    assert values.loc[0, "peak_flow_m3s"] == 10.5
