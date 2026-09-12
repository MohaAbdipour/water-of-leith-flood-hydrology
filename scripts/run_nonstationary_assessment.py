"""Compare stationary and time-varying GEV models for open annual maxima."""

import pandas as pd

from water_of_leith.nonstationary import compare_gev_trends


def main() -> None:
    maxima = pd.read_csv("outputs/annual_maxima.csv")
    results = compare_gev_trends(maxima["peak_flow_m3s"], maxima["water_year"])
    results.to_csv("outputs/nonstationary_model_comparison.csv", index=False)


if __name__ == "__main__":
    main()
