import pandas as pd

from water_of_leith.regional import select_comparison_stations


def test_selection_applies_distance_record_and_missingness_rules():
    metadata = pd.DataFrame({
        "station_id": [19006, 1, 2, 3],
        "Start_date": ["01/01/1990"] * 4,
        "End_date": ["31/12/2023"] * 4,
        "Missing_values_%": [0, 0, 2, 0],
        "Catchment_Area": [107, 100, 100, 400],
        "Easting": [322792, 323792, 324792, 323792],
        "Northing": [673202] * 4,
    })
    selected = select_comparison_stations(metadata)
    assert selected["station_id"].tolist() == [1]
