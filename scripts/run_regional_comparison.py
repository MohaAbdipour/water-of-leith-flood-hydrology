"""Compare Murrayfield with transparently selected nearby UK-Flow15 stations."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from water_of_leith.frequency import annual_maxima, read_ukflow15
from water_of_leith.pot import decluster_exceedances
from water_of_leith.regional import coefficient_of_variation, select_comparison_stations
from water_of_leith.seasonality import circular_summary, hydrological_year_angle

TARGET = 19006


def station_path(station_id: int) -> Path:
    if station_id == TARGET:
        return Path("data/raw/019006.csv")
    return Path(f"data/raw/regional/{station_id:06d}.csv")


def main() -> None:
    metadata = pd.read_csv("data/raw/00_station_id_meta.csv")
    selected = select_comparison_stations(metadata)
    station_ids = [TARGET, *selected["station_id"].astype(int).tolist()]
    station_meta = metadata[metadata["station_id"].isin(station_ids)].copy()
    station_meta["distance_km"] = np.hypot(
        station_meta["Easting"] - 322_792, station_meta["Northing"] - 673_202
    ) / 1000

    maxima_by_station: dict[int, pd.DataFrame] = {}
    pot_by_station: dict[int, pd.DataFrame] = {}
    series_by_station: dict[int, pd.DataFrame] = {}
    for station_id in station_ids:
        flow = read_ukflow15(str(station_path(station_id))).sort_values("datetime")
        series_by_station[station_id] = flow
        maxima_by_station[station_id] = annual_maxima(flow)
        threshold = float(flow["value"].quantile(0.997))
        pot_by_station[station_id] = decluster_exceedances(flow, threshold, "72h")

    common_years = sorted(
        set.intersection(*[set(frame["water_year"]) for frame in maxima_by_station.values()])
    )
    if len(common_years) < 20:
        raise ValueError("Insufficient common complete water years for regional comparison")

    summaries, maxima_rows = [], []
    for station_id in station_ids:
        meta = station_meta.loc[station_meta["station_id"] == station_id].iloc[0]
        maxima = maxima_by_station[station_id]
        maxima = maxima[maxima["water_year"].isin(common_years)].copy()
        maxima["station_id"] = station_id
        maxima["station_name"] = f"{meta['River']} at {meta['Location']}"
        maxima_rows.append(maxima)
        peaks = pot_by_station[station_id]
        angles = hydrological_year_angle(peaks["datetime"])
        mean_angle, concentration, p_value = circular_summary(angles)
        mean_date = pd.Timestamp("2001-10-01") + pd.to_timedelta(
            mean_angle / (2 * np.pi) * 365.25, unit="D"
        )
        duration_years = (
            series_by_station[station_id]["datetime"].max()
            - series_by_station[station_id]["datetime"].min()
        ) / pd.Timedelta(days=365.2425)
        qmed = float(maxima["peak_flow_m3s"].median())
        summaries.append({
            "station_id": station_id,
            "river": meta["River"],
            "location": meta["Location"],
            "distance_from_murrayfield_km": meta["distance_km"],
            "catchment_area_km2": meta["Catchment_Area"],
            "catalogue_missing_values_percent": meta["Missing_values_%"],
            "nrfa_quality_status_v14": meta["nrfa_quality_status_v14"],
            "common_water_year_start": min(common_years),
            "common_water_year_end": max(common_years),
            "common_annual_maxima": len(maxima),
            "qmed_common_period_m3s": qmed,
            "specific_qmed_l_s_km2": 1000 * qmed / meta["Catchment_Area"],
            "annual_maximum_cv": coefficient_of_variation(maxima["peak_flow_m3s"]),
            "pot_threshold_99_7_m3s": float(series_by_station[station_id]["value"].quantile(0.997)),
            "pot_events": len(peaks),
            "pot_events_per_year": len(peaks) / duration_years,
            "pot_circular_mean_date": mean_date.strftime("%d %B"),
            "pot_mean_resultant_length": concentration,
            "pot_rayleigh_p_value": p_value,
        })

    summary = pd.DataFrame(summaries)
    maxima_long = pd.concat(maxima_rows, ignore_index=True)
    Path("outputs").mkdir(exist_ok=True)
    summary.to_csv("outputs/regional_station_comparison.csv", index=False)
    maxima_long.to_csv("outputs/regional_common_annual_maxima.csv", index=False)

    names = [
        f"{row.river}\n{row.location}" for row in summary.itertuples(index=False)
    ]
    colours = ["#a51c30" if station == TARGET else "#3977a8" for station in summary["station_id"]]
    fig = plt.figure(figsize=(14, 10), constrained_layout=True)
    grid = fig.add_gridspec(2, 2)
    map_axis = fig.add_subplot(grid[0, 0])
    bar_axis = fig.add_subplot(grid[0, 1])
    series_axis = fig.add_subplot(grid[1, 0])
    polar_axis = fig.add_subplot(grid[1, 1], projection="polar")

    map_offsets = {
        19006: (7, 8), 19012: (7, 5), 19017: (-8, 8), 19004: (7, 5),
        19021: (7, 5), 19005: (7, 5), 20003: (7, 5),
    }
    for row, colour in zip(summary.itertuples(index=False), colours):
        meta = station_meta.loc[station_meta["station_id"] == row.station_id].iloc[0]
        size = 35 + 0.45 * meta["Catchment_Area"]
        map_axis.scatter(meta["Easting"], meta["Northing"], s=size, color=colour, edgecolor="white", zorder=3)
        map_axis.annotate(
            f"{row.river}\n{row.location}", (meta["Easting"], meta["Northing"]),
            xytext=map_offsets[row.station_id], textcoords="offset points", fontsize=7.5,
            ha="right" if row.station_id == 19017 else "left",
        )
    map_axis.set(
        xlabel="British National Grid easting (m)",
        ylabel="British National Grid northing (m)",
        title="Transparent geographic comparison set",
    )
    map_axis.set_aspect("equal")
    map_axis.margins(x=0.09, y=0.24)
    map_axis.grid(alpha=0.22)

    order = np.arange(len(summary))
    bar_axis.barh(order, summary["specific_qmed_l_s_km2"], color=colours)
    bar_axis.set(
        yticks=order, yticklabels=names,
        xlabel="Common-period QMED / area (L s⁻¹ km⁻²)",
        title="Specific median annual maximum",
    )
    bar_axis.invert_yaxis()
    bar_axis.grid(axis="x", alpha=0.22)

    for station_id, colour, name in zip(summary["station_id"], colours, names):
        station_maxima = maxima_long[maxima_long["station_id"] == station_id]
        median = station_maxima["peak_flow_m3s"].median()
        series_axis.plot(
            station_maxima["water_year"], station_maxima["peak_flow_m3s"] / median,
            color=colour, alpha=0.72, linewidth=1.2,
            label=name.replace("\n", " at ") if station_id == TARGET else None,
        )
    series_axis.axhline(1, color="0.35", linestyle="--", linewidth=1)
    series_axis.set(
        xlabel="Water year", ylabel="Annual maximum / station QMED",
        title="Common-period flood variability",
    )
    series_axis.grid(alpha=0.22)
    series_axis.legend(fontsize=8)

    angles = []
    radii = []
    for row in summary.itertuples(index=False):
        parsed = pd.Timestamp(f"2001 {row.pot_circular_mean_date}")
        angle = float(hydrological_year_angle(pd.DatetimeIndex([parsed]))[0])
        angles.append(angle)
        radii.append(row.pot_mean_resultant_length)
    polar_axis.set_theta_zero_location("N")
    polar_axis.set_theta_direction(-1)
    polar_axis.scatter(angles, radii, s=85, c=colours, edgecolor="white")
    polar_offsets = {
        19006: (-29, -7), 19012: (-29, 8), 19017: (-19, 12),
        19004: (7, -10), 19021: (8, -2), 19005: (8, 11), 20003: (-30, -2),
    }
    for angle, radius, row in zip(angles, radii, summary.itertuples(index=False)):
        polar_axis.annotate(
            str(row.station_id), (angle, radius), xytext=polar_offsets[row.station_id],
            textcoords="offset points", fontsize=6.5,
            color="#8f1028" if row.station_id == TARGET else "#194f78",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.5},
        )
    polar_axis.set_xticks(np.arange(12) * 2 * np.pi / 12, ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"])
    polar_axis.set_ylim(0, max(radii) + 0.12)
    polar_axis.set_title("Mean POT timing and seasonal concentration", pad=24)
    fig.suptitle(
        f"Regional high-flow comparison, {min(common_years)}–{max(common_years)} water years",
        fontsize=16, fontweight="bold",
    )
    Path("docs/figures").mkdir(parents=True, exist_ok=True)
    fig.savefig("docs/figures/regional_flow_comparison.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
