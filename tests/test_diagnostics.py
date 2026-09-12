import numpy as np
import pandas as pd

from water_of_leith.diagnostics import pettitt_test, trend_summary


def test_pettitt_identifies_clear_step():
    result = pettitt_test(np.r_[np.ones(20), np.ones(20) * 10])
    assert result["change_index"] in {19, 20}
    assert result["p_value"] < 0.01


def test_trend_summary_detects_increasing_series():
    maxima = pd.DataFrame({"water_year": range(2000, 2020), "peak_flow_m3s": range(20)})
    result = trend_summary(maxima)
    assert result["kendall_tau"] == 1.0
    assert result["theil_sen_slope_m3s_per_year"] == 1.0

