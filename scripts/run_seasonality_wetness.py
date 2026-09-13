"""Analyse flood seasonality and pre-storm catchment wetness."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from water_of_leith.seasonality import (
    circular_summary,
    expanding_splits,
    fit_predict_log_linear,
    hydrological_year_angle,
    partial_spearman,
)

WETNESS_WINDOWS = (7, 14, 30)


def antecedent_total(rain: pd.Series, peak: pd.Timestamp, days: int) -> float:
    """Rainfall before, and excluding, the 72-hour event-rainfall window."""
    end = peak.floor("h") - pd.Timedelta(hours=72)
    start = end - pd.Timedelta(hours=24 * days - 1)
    window = rain.loc[start:end]
    if len(window) != 24 * days:
        return float("nan")
    return float(window.sum())


def design_matrix(events: pd.DataFrame, wetness_days: int, seasonal: bool) -> np.ndarray:
    columns = [
        np.ones(len(events)),
        np.log1p(events["rainfall_72h_mm"].to_numpy()),
    ]
    if wetness_days:
        columns.append(np.log1p(events[f"antecedent_{wetness_days}d_mm"].to_numpy()))
    if seasonal:
        columns.extend([
            np.sin(events["water_year_angle"].to_numpy()),
            np.cos(events["water_year_angle"].to_numpy()),
        ])
    return np.column_stack(columns)


def validation_metrics(events: pd.DataFrame, wetness_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare three models using expanding-window chronological predictions."""
    models = {
        "climatological mean": None,
        "72-hour rainfall": (0, False),
        f"rainfall + {wetness_days}-day wetness + season": (wetness_days, True),
    }
    predictions, folds = [], []
    for fold, (train_idx, test_idx) in enumerate(
        expanding_splits(len(events), initial=29, test_size=10), start=1
    ):
        train, test = events.iloc[train_idx], events.iloc[test_idx]
        for model, specification in models.items():
            if specification is None:
                predicted = np.repeat(train["peak_flow_m3s"].mean(), len(test))
            else:
                window, seasonal = specification
                _, predicted = fit_predict_log_linear(
                    design_matrix(train, window, seasonal),
                    train["peak_flow_m3s"].to_numpy(),
                    design_matrix(test, window, seasonal),
                )
            for event_time, observed, estimate in zip(
                test["flow_peak_datetime"], test["peak_flow_m3s"], predicted
            ):
                predictions.append({
                    "fold": fold,
                    "model": model,
                    "flow_peak_datetime": event_time,
                    "observed_peak_flow_m3s": observed,
                    "predicted_peak_flow_m3s": estimate,
                })
    predictions_frame = pd.DataFrame(predictions)
    for model, group in predictions_frame.groupby("model", sort=False):
        residual = group["predicted_peak_flow_m3s"] - group["observed_peak_flow_m3s"]
        denominator = np.sum(
            (group["observed_peak_flow_m3s"] - group["observed_peak_flow_m3s"].mean()) ** 2
        )
        folds.append({
            "model": model,
            "test_events": len(group),
            "mae_m3s": float(np.abs(residual).mean()),
            "rmse_m3s": float(np.sqrt(np.mean(residual**2))),
            "r_squared": float(1 - np.sum(residual**2) / denominator),
        })
    return pd.DataFrame(folds), predictions_frame


def bootstrap_coefficients(events: pd.DataFrame, repetitions: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(19006)
    names = ["intercept", "log_rainfall_72h", "log_antecedent_14d", "season_sine", "season_cosine"]
    estimates = []
    matrix = design_matrix(events, 14, True)
    response = events["peak_flow_m3s"].to_numpy()
    for _ in range(repetitions):
        sample = rng.integers(0, len(events), len(events))
        coefficients, _ = fit_predict_log_linear(matrix[sample], response[sample], matrix[:1])
        estimates.append(coefficients)
    values = np.asarray(estimates)
    fitted, _ = fit_predict_log_linear(matrix, response, matrix[:1])
    return pd.DataFrame({
        "term": names,
        "estimate": fitted,
        "bootstrap_lower_95": np.quantile(values, 0.025, axis=0),
        "bootstrap_upper_95": np.quantile(values, 0.975, axis=0),
    })


def bootstrap_association(
    wetness: np.ndarray,
    peak_flow: np.ndarray,
    event_rainfall: np.ndarray,
    repetitions: int = 2000,
) -> tuple[float, float, float, float]:
    """Bootstrap intervals for marginal and rainfall-adjusted rank association."""
    rng = np.random.default_rng(19006 + len(wetness))
    marginal, adjusted = [], []
    for _ in range(repetitions):
        sample = rng.integers(0, len(wetness), len(wetness))
        marginal.append(spearmanr(wetness[sample], peak_flow[sample]).statistic)
        adjusted.append(
            partial_spearman(
                wetness[sample], peak_flow[sample], event_rainfall[sample]
            )
        )
    return (
        float(np.nanquantile(marginal, 0.025)),
        float(np.nanquantile(marginal, 0.975)),
        float(np.nanquantile(adjusted, 0.025)),
        float(np.nanquantile(adjusted, 0.975)),
    )


def main() -> None:
    outputs = Path("outputs")
    figures = Path("docs/figures")
    figures.mkdir(parents=True, exist_ok=True)
    rain = pd.read_csv(
        "data/raw/ceh_gear1hr_19006.csv", parse_dates=["time"]
    ).set_index("time")["rainfall_mm"].sort_index()
    events = pd.read_csv(
        outputs / "rainfall_linked_flood_events.csv", parse_dates=["flow_peak_datetime"]
    ).sort_values("flow_peak_datetime").reset_index(drop=True)
    events["month"] = events["flow_peak_datetime"].dt.month
    events["season"] = events["flow_peak_datetime"].dt.month.map({
        12: "winter", 1: "winter", 2: "winter",
        3: "spring", 4: "spring", 5: "spring",
        6: "summer", 7: "summer", 8: "summer",
        9: "autumn", 10: "autumn", 11: "autumn",
    })
    events["water_year_angle"] = hydrological_year_angle(events["flow_peak_datetime"])
    for days in WETNESS_WINDOWS:
        events[f"antecedent_{days}d_mm"] = [
            antecedent_total(rain, peak, days) for peak in events["flow_peak_datetime"]
        ]
    monthly_daily_climatology = rain.groupby(rain.index.month).mean() * 24
    events["antecedent_30d_anomaly_mm_per_day"] = (
        events["antecedent_30d_mm"] / 30
        - events["month"].map(monthly_daily_climatology)
    )
    if events[[f"antecedent_{days}d_mm" for days in WETNESS_WINDOWS]].isna().any().any():
        raise ValueError("Incomplete antecedent rainfall windows")
    events.to_csv(outputs / "seasonality_wetness_events.csv", index=False)
    seasonal_summary = (
        events.groupby("season")
        .agg(
            events=("peak_flow_m3s", "size"),
            median_peak_flow_m3s=("peak_flow_m3s", "median"),
            lower_quartile_peak_flow_m3s=("peak_flow_m3s", lambda values: values.quantile(0.25)),
            upper_quartile_peak_flow_m3s=("peak_flow_m3s", lambda values: values.quantile(0.75)),
            median_rainfall_72h_mm=("rainfall_72h_mm", "median"),
            median_antecedent_14d_mm=("antecedent_14d_mm", "median"),
        )
        .reindex(["autumn", "winter", "spring", "summer"])
        .reset_index()
    )
    seasonal_summary.to_csv(outputs / "seasonal_flood_summary.csv", index=False)

    mean_angle, concentration, rayleigh_p = circular_summary(events["water_year_angle"])
    mean_date = pd.Timestamp("2001-10-01") + pd.to_timedelta(
        mean_angle / (2 * np.pi) * 365.25, unit="D"
    )
    summary_rows = [
        ("events", len(events)),
        ("circular_mean_timing", mean_date.strftime("%d %B")),
        ("mean_resultant_length", f"{concentration:.3f}"),
        ("rayleigh_p_value", f"{rayleigh_p:.6g}"),
    ]
    sensitivity = []
    for days in WETNESS_WINDOWS:
        wetness = events[f"antecedent_{days}d_mm"]
        rho, p_value = spearmanr(wetness, events["peak_flow_m3s"])
        partial = partial_spearman(
            wetness.to_numpy(),
            events["peak_flow_m3s"].to_numpy(),
            events["rainfall_72h_mm"].to_numpy(),
        )
        marginal_lower, marginal_upper, partial_lower, partial_upper = bootstrap_association(
            wetness.to_numpy(),
            events["peak_flow_m3s"].to_numpy(),
            events["rainfall_72h_mm"].to_numpy(),
        )
        model_metrics, _ = validation_metrics(events, days)
        full_model = model_metrics.iloc[-1]
        sensitivity.append({
            "antecedent_window_days": days,
            "spearman_rho_peak_flow": rho,
            "spearman_p_value": p_value,
            "spearman_bootstrap_lower_95": marginal_lower,
            "spearman_bootstrap_upper_95": marginal_upper,
            "partial_spearman_controlling_72h_rainfall": partial,
            "partial_spearman_bootstrap_lower_95": partial_lower,
            "partial_spearman_bootstrap_upper_95": partial_upper,
            "chronological_validation_mae_m3s": full_model["mae_m3s"],
            "chronological_validation_rmse_m3s": full_model["rmse_m3s"],
            "chronological_validation_r_squared": full_model["r_squared"],
        })
    sensitivity_frame = pd.DataFrame(sensitivity)
    sensitivity_frame.to_csv(outputs / "wetness_window_sensitivity.csv", index=False)

    metrics, predictions = validation_metrics(events, 14)
    metrics.to_csv(outputs / "seasonality_model_validation.csv", index=False)
    predictions.to_csv(outputs / "seasonality_model_predictions.csv", index=False)
    coefficients = bootstrap_coefficients(events)
    coefficients.to_csv(outputs / "seasonality_model_coefficients.csv", index=False)
    with (outputs / "seasonality_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        writer.writerows(summary_rows)

    month_counts = events["month"].value_counts().reindex(range(1, 13), fill_value=0)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    axes[0].bar(range(1, 13), month_counts, color="#2878b5")
    axes[0].set(xticks=range(1, 13), xlabel="Month", ylabel="Independent flood events", title="Seasonal occurrence of observed floods")
    axes[0].grid(axis="y", alpha=0.25)
    scatter = axes[1].scatter(
        events["antecedent_14d_mm"], events["peak_flow_m3s"],
        c=events["rainfall_72h_mm"], cmap="viridis", edgecolor="white", alpha=0.9,
    )
    axes[1].set(xlabel="Pre-storm 14-day rainfall (mm)", ylabel="Peak flow (m³/s)", title="Antecedent wetness and flood magnitude")
    axes[1].grid(alpha=0.25)
    colorbar = fig.colorbar(scatter, ax=axes[1])
    colorbar.set_label("Event rainfall over 72 hours (mm)")
    fig.savefig(figures / "seasonality_antecedent_wetness.png", dpi=200)
    plt.close(fig)

    # Circular timing and seasonal magnitude are separated from the wetness
    # diagnostics so that timing concentration is not implied by a linear axis.
    season_colours = {
        "autumn": "#c76d1d",
        "winter": "#3977a8",
        "spring": "#4d9b64",
        "summer": "#d8aa24",
    }
    figure = plt.figure(figsize=(12, 5.4), constrained_layout=True)
    polar_axis = figure.add_subplot(1, 2, 1, projection="polar")
    box_axis = figure.add_subplot(1, 2, 2)
    month_order = [10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    month_labels = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
    theta = np.arange(12) * 2 * np.pi / 12
    ordered_counts = month_counts.reindex(month_order).to_numpy()
    bar_colours = (
        [season_colours["autumn"]] * 2
        + [season_colours["winter"]] * 3
        + [season_colours["spring"]] * 3
        + [season_colours["summer"]] * 3
        + [season_colours["autumn"]]
    )
    polar_axis.bar(
        theta, ordered_counts, width=2 * np.pi / 12 * 0.88,
        color=bar_colours, edgecolor="white", alpha=0.9,
    )
    polar_axis.set_theta_zero_location("N")
    polar_axis.set_theta_direction(-1)
    polar_axis.set_xticks(theta, month_labels)
    polar_axis.set_title("Flood occurrence through the water year", pad=24, fontweight="bold")
    polar_axis.annotate(
        "",
        xy=(mean_angle, max(ordered_counts) * concentration),
        xytext=(mean_angle, 0),
        arrowprops={"arrowstyle": "-|>", "color": "#8b1e3f", "lw": 2.3},
    )
    polar_axis.text(
        0.03, -0.10,
        f"Mean: {mean_date.strftime('%d %b')}  |  R̄ = {concentration:.3f}  |  Rayleigh p = {rayleigh_p:.2g}",
        transform=polar_axis.transAxes, fontsize=9,
    )

    season_order = ["autumn", "winter", "spring", "summer"]
    distributions = [
        events.loc[events["season"] == season, "peak_flow_m3s"].to_numpy()
        for season in season_order
    ]
    boxes = box_axis.boxplot(distributions, patch_artist=True, widths=0.55, showfliers=False)
    for patch_box, season in zip(boxes["boxes"], season_order):
        patch_box.set(facecolor=season_colours[season], alpha=0.45)
    rng = np.random.default_rng(19006)
    for position, (season, values) in enumerate(zip(season_order, distributions), start=1):
        jitter = rng.normal(0, 0.045, len(values))
        box_axis.scatter(
            position + jitter, values, s=27, color=season_colours[season],
            edgecolor="white", linewidth=0.4, alpha=0.85,
        )
    box_axis.set(
        xticks=range(1, 5),
        xticklabels=[season.title() for season in season_order],
        ylabel="Peak flow (m³/s)",
        ylim=(15, 98),
    )
    for position, values in enumerate(distributions, start=1):
        box_axis.text(position, 94, f"n={len(values)}", ha="center", fontsize=9)
    box_axis.set_title(
        "Flood magnitude by meteorological season", loc="left", fontweight="bold", pad=14
    )
    box_axis.grid(axis="y", alpha=0.25)
    figure.savefig(figures / "flood_seasonality_diagnostics.png", dpi=220, bbox_inches="tight")
    plt.close(figure)

    # Association intervals and out-of-time predictions make the absence of
    # predictive improvement visible, rather than reporting only fit statistics.
    figure, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
    windows = sensitivity_frame["antecedent_window_days"].to_numpy()
    for offset, estimate_column, lower_column, upper_column, label, colour in [
        (-0.45, "spearman_rho_peak_flow", "spearman_bootstrap_lower_95", "spearman_bootstrap_upper_95", "Marginal", "#2878b5"),
        (0.45, "partial_spearman_controlling_72h_rainfall", "partial_spearman_bootstrap_lower_95", "partial_spearman_bootstrap_upper_95", "Adjusted for 72 h rain", "#c54e3f"),
    ]:
        estimates = sensitivity_frame[estimate_column].to_numpy()
        lower = sensitivity_frame[lower_column].to_numpy()
        upper = sensitivity_frame[upper_column].to_numpy()
        axes[0].errorbar(
            windows + offset, estimates,
            yerr=np.vstack([estimates - lower, upper - estimates]),
            fmt="o", capsize=4, color=colour, label=label,
        )
    axes[0].axhline(0, color="0.35", linewidth=1, linestyle="--")
    axes[0].set(
        xticks=windows,
        xlabel="Pre-storm wetness window (days)",
        ylabel="Spearman correlation with peak flow",
        title="Wetness-effect uncertainty",
        ylim=(-0.35, 0.5),
    )
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.22)

    model_colours = {
        "climatological mean": "#6b7280",
        "72-hour rainfall": "#2878b5",
        "rainfall + 14-day wetness + season": "#c54e3f",
    }
    short_labels = {
        "climatological mean": "Training mean",
        "72-hour rainfall": "72 h rainfall",
        "rainfall + 14-day wetness + season": "Rain + wetness + season",
    }
    limits = [
        min(predictions["observed_peak_flow_m3s"].min(), predictions["predicted_peak_flow_m3s"].min()) - 2,
        max(predictions["observed_peak_flow_m3s"].max(), predictions["predicted_peak_flow_m3s"].max()) + 2,
    ]
    for model, group in predictions.groupby("model", sort=False):
        axes[1].scatter(
            group["observed_peak_flow_m3s"], group["predicted_peak_flow_m3s"],
            s=24, alpha=0.62, color=model_colours[model], label=short_labels[model],
        )
    axes[1].plot(limits, limits, color="black", linestyle="--", linewidth=1, label="1:1")
    axes[1].set(
        xlim=limits, ylim=limits,
        xlabel="Observed peak flow (m³/s)",
        ylabel="Out-of-time prediction (m³/s)",
        title="Chronological validation",
    )
    axes[1].legend(fontsize=7.5)
    axes[1].grid(alpha=0.22)

    x_positions = np.arange(len(metrics))
    width = 0.36
    axes[2].bar(x_positions - width / 2, metrics["mae_m3s"], width, label="MAE", color="#4c78a8")
    axes[2].bar(x_positions + width / 2, metrics["rmse_m3s"], width, label="RMSE", color="#f28e2b")
    axes[2].set(
        xticks=x_positions,
        xticklabels=[short_labels[model] for model in metrics["model"]],
        ylabel="Validation error (m³/s)",
        title="Out-of-time error",
    )
    axes[2].tick_params(axis="x", rotation=18)
    axes[2].legend()
    axes[2].grid(axis="y", alpha=0.22)
    figure.savefig(figures / "wetness_model_diagnostics.png", dpi=220, bbox_inches="tight")
    plt.close(figure)

    print(summary_rows)
    print(sensitivity_frame.to_string(index=False))
    print(metrics.to_string(index=False))
    print(coefficients.to_string(index=False))


if __name__ == "__main__":
    main()
