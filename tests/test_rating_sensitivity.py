import pandas as pd

from water_of_leith.rating_sensitivity import era_comparison, split_rating_eras


def test_rating_era_labels():
    maxima = pd.DataFrame({"water_year": [2016, 2017, 2018], "peak_flow_m3s": [1.0, 2.0, 3.0]})
    assert split_rating_eras(maxima)["rating_era"].tolist() == ["pre-works", "transition", "post-works"]


def test_era_comparison_reports_sample_sizes():
    maxima = pd.DataFrame({
        "water_year": list(range(2000, 2017)) + list(range(2018, 2024)),
        "peak_flow_m3s": list(range(17)) + list(range(20, 26)),
    })
    result = era_comparison(maxima, repetitions=100)
    assert result["pre_years"] == 17
    assert result["post_years"] == 6

