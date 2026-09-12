"""Distribution diagnostics and temporal-stability tests for annual maxima."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .frequency import FittedModel


def fitted_cdf(model: FittedModel, flows: np.ndarray) -> np.ndarray:
    """Evaluate a fitted model CDF on the original flow scale."""
    values = np.asarray(flows, dtype=float)
    if model.name == "Log-Pearson III":
        return model.distribution.cdf(np.log10(values), *model.parameters)
    return model.distribution.cdf(values, *model.parameters)


def fitted_quantiles(model: FittedModel, probabilities: np.ndarray) -> np.ndarray:
    """Evaluate fitted quantiles on the original flow scale."""
    values = model.distribution.ppf(probabilities, *model.parameters)
    return 10**values if model.name == "Log-Pearson III" else values


def model_diagnostics(maxima: pd.DataFrame, models: dict[str, FittedModel]) -> pd.DataFrame:
    """Calculate comparable likelihood criteria and descriptive fit statistics."""
    flows = maxima["peak_flow_m3s"].to_numpy(dtype=float)
    n = len(flows)
    rows = []
    for name, model in models.items():
        if name == "Log-Pearson III":
            transformed = np.log10(flows)
            log_likelihood = float(np.sum(model.distribution.logpdf(transformed, *model.parameters) - np.log(flows * np.log(10))))
        else:
            log_likelihood = float(np.sum(model.distribution.logpdf(flows, *model.parameters)))
        k = len(model.parameters)
        aic = 2 * k - 2 * log_likelihood
        aicc = aic + (2 * k * (k + 1)) / (n - k - 1)
        sorted_flows = np.sort(flows)
        empirical = (np.arange(1, n + 1) - 0.44) / (n + 0.12)
        fitted = fitted_cdf(model, sorted_flows)
        ks = float(np.max(np.abs(empirical - fitted)))
        correlation = float(np.corrcoef(sorted_flows, fitted_quantiles(model, empirical))[0, 1])
        rows.append({
            "model": name,
            "parameters": k,
            "log_likelihood": log_likelihood,
            "aic": aic,
            "aicc": aicc,
            "descriptive_ks_distance": ks,
            "probability_plot_correlation": correlation,
        })
    result = pd.DataFrame(rows).sort_values("aicc").reset_index(drop=True)
    result["delta_aicc"] = result["aicc"] - result["aicc"].min()
    weights = np.exp(-0.5 * result["delta_aicc"])
    result["akaike_weight"] = weights / weights.sum()
    return result


def pettitt_test(values: np.ndarray) -> dict[str, float | int]:
    """Exploratory Pettitt single-change-point test using its asymptotic p-value."""
    values = np.asarray(values, dtype=float)
    ranks = stats.rankdata(values)
    statistic_by_split = 2 * np.cumsum(ranks) - np.arange(1, len(values) + 1) * (len(values) + 1)
    index = int(np.argmax(np.abs(statistic_by_split)))
    statistic = float(abs(statistic_by_split[index]))
    p_value = float(min(1.0, 2 * np.exp((-6 * statistic**2) / (len(values) ** 3 + len(values) ** 2))))
    return {"change_index": index, "statistic": statistic, "p_value": p_value}


def trend_summary(maxima: pd.DataFrame) -> dict[str, float | int]:
    """Summarise monotonic trend and one exploratory change point."""
    ordered = maxima.sort_values("water_year")
    years = ordered["water_year"].to_numpy(dtype=float)
    flows = ordered["peak_flow_m3s"].to_numpy(dtype=float)
    tau = stats.kendalltau(years, flows)
    slope, intercept, lower, upper = stats.theilslopes(flows, years, alpha=0.95)
    change = pettitt_test(flows)
    change_index = int(change["change_index"])
    return {
        "years": len(flows),
        "kendall_tau": float(tau.statistic),
        "kendall_p_value": float(tau.pvalue),
        "theil_sen_slope_m3s_per_year": float(slope),
        "theil_sen_lower_95": float(lower),
        "theil_sen_upper_95": float(upper),
        "pettitt_change_after_water_year": int(years[change_index]),
        "pettitt_statistic": float(change["statistic"]),
        "pettitt_p_value": float(change["p_value"]),
    }

