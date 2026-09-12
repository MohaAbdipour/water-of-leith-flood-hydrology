import numpy as np

from water_of_leith.nonstationary import compare_gev_trends


def test_model_comparison_contains_nested_candidates():
    rng = np.random.default_rng(19006)
    years = np.arange(1980, 2020)
    values = rng.gumbel(30, 7, size=len(years))
    comparison = compare_gev_trends(values, years)
    assert comparison["model"].tolist() == ["stationary", "location", "scale", "location_scale"]
    assert comparison["converged"].all()
    assert comparison.loc[comparison["model"] == "stationary", "likelihood_ratio_p"].isna().all()
