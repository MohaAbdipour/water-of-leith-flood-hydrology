"""Likelihood-based comparison of stationary and time-varying GEV models."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import optimize, stats


@dataclass(frozen=True)
class GEVTrendFit:
    model: str
    parameters: np.ndarray
    log_likelihood: float
    aicc: float
    converged: bool


def _aicc(log_likelihood: float, parameters: int, observations: int) -> float:
    aic = 2 * parameters - 2 * log_likelihood
    return float(aic + 2 * parameters * (parameters + 1) / (observations - parameters - 1))


def fit_gev_trend(values: pd.Series | np.ndarray, years: pd.Series | np.ndarray, model: str) -> GEVTrendFit:
    """Fit a GEV with stationary, linear-location, linear-scale, or joint trends.

    Time is centred and scaled by one standard deviation. Scale is modelled on
    the log scale, which ensures positive values throughout optimisation.
    """
    if model not in {"stationary", "location", "scale", "location_scale"}:
        raise ValueError(f"Unknown model: {model}")
    y = np.asarray(values, dtype=float)
    year = np.asarray(years, dtype=float)
    x = (year - year.mean()) / year.std(ddof=0)
    shape, location, scale = stats.genextreme.fit(y)
    initial = [shape, location, np.log(scale)]
    if model in {"location", "location_scale"}:
        initial.append(0.0)
    if model in {"scale", "location_scale"}:
        initial.append(0.0)

    def objective(parameters: np.ndarray) -> float:
        c, mu0, log_sigma0 = parameters[:3]
        position = 3
        mu = np.full_like(x, mu0)
        log_sigma = np.full_like(x, log_sigma0)
        if model in {"location", "location_scale"}:
            mu = mu + parameters[position] * x
            position += 1
        if model in {"scale", "location_scale"}:
            log_sigma = log_sigma + parameters[position] * x
        likelihood = stats.genextreme.logpdf(y, c, loc=mu, scale=np.exp(log_sigma))
        if not np.all(np.isfinite(likelihood)):
            return 1e100
        return float(-likelihood.sum())

    result = optimize.minimize(objective, np.asarray(initial), method="Nelder-Mead", options={"maxiter": 50000})
    log_likelihood = -float(result.fun)
    return GEVTrendFit(
        model=model,
        parameters=result.x,
        log_likelihood=log_likelihood,
        aicc=_aicc(log_likelihood, len(result.x), len(y)),
        converged=bool(result.success),
    )


def compare_gev_trends(values: pd.Series | np.ndarray, years: pd.Series | np.ndarray) -> pd.DataFrame:
    """Fit candidate models and compare each trend model with the stationary fit."""
    fits = [fit_gev_trend(values, years, model) for model in ["stationary", "location", "scale", "location_scale"]]
    baseline = fits[0]
    rows = []
    for fit in fits:
        added = len(fit.parameters) - len(baseline.parameters)
        lr = max(0.0, 2 * (fit.log_likelihood - baseline.log_likelihood))
        rows.append({
            "model": fit.model,
            "parameters": len(fit.parameters),
            "log_likelihood": fit.log_likelihood,
            "aicc": fit.aicc,
            "delta_aicc": fit.aicc - min(item.aicc for item in fits),
            "likelihood_ratio_vs_stationary": lr if added else np.nan,
            "likelihood_ratio_df": added if added else np.nan,
            "likelihood_ratio_p": stats.chi2.sf(lr, added) if added else np.nan,
            "converged": fit.converged,
        })
    return pd.DataFrame(rows)
