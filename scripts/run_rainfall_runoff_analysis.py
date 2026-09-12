"""Link open-data POT events to catchment-mean CEH-GEAR1hr rainfall."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

from water_of_leith.frequency import read_ukflow15
from water_of_leith.pot import decluster_exceedances
from water_of_leith.rainfall_runoff import event_rainfall_metrics


def main() -> None:
    flow = read_ukflow15("data/raw/019006.csv")
    rain = pd.read_csv("data/raw/ceh_gear1hr_19006.csv", parse_dates=["time"])
    threshold = float(flow["value"].quantile(0.997))
    peaks = decluster_exceedances(flow, threshold, "72h")
    peaks = peaks.loc[
        (peaks["datetime"] >= rain["time"].min() + pd.Timedelta(hours=72))
        & (peaks["datetime"] <= rain["time"].max())
    ].copy()

    metrics = []
    for row in peaks.itertuples(index=False):
        metrics.append({
            "flow_peak_datetime": row.datetime,
            "peak_flow_m3s": row.value,
            **event_rainfall_metrics(rain, row.datetime),
        })
    events = pd.DataFrame(metrics).sort_values("flow_peak_datetime")
    events.to_csv("outputs/rainfall_linked_flood_events.csv", index=False)

    summary = []
    for duration in [24, 48, 72]:
        coefficient, p_value = stats.spearmanr(events["peak_flow_m3s"], events[f"rainfall_{duration}h_mm"])
        summary.append({
            "rainfall_duration_hours": duration,
            "events": len(events),
            "spearman_rho": coefficient,
            "spearman_p": p_value,
        })
    pd.DataFrame(summary).to_csv("outputs/rainfall_runoff_association.csv", index=False)

    largest = events.nlargest(4, "peak_flow_m3s")
    figure_dir = Path("docs/figures")
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(4, 1, figsize=(12, 13), sharex=False)
    for axis, event in zip(axes, largest.itertuples(index=False)):
        start = event.flow_peak_datetime - pd.Timedelta(hours=72)
        end = event.flow_peak_datetime + pd.Timedelta(hours=24)
        event_flow = flow.loc[flow["datetime"].between(start, end)]
        event_rain = rain.loc[rain["time"].between(start.floor("h"), end.floor("h"))]
        axis.plot(event_flow["datetime"], event_flow["value"], color="#0072B2", linewidth=1.5)
        axis.axvline(event.flow_peak_datetime, color="0.35", linestyle="--", linewidth=0.8)
        axis.set_ylabel("Flow (m³/s)", color="#0072B2")
        rain_axis = axis.twinx()
        rain_axis.bar(event_rain["time"], event_rain["rainfall_mm"], width=0.035, color="#56B4E9", alpha=0.45)
        rain_axis.invert_yaxis()
        rain_axis.set_ylabel("Rain (mm/h)", color="#4477AA")
        axis.set_title(f"Peak {event.peak_flow_m3s:.2f} m³/s on {event.flow_peak_datetime:%d %b %Y %H:%M}")
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H:%M"))
        axis.grid(alpha=0.2)
    fig.suptitle("Largest Murrayfield floods with CEH-GEAR1hr catchment rainfall, 1992–2016")
    fig.tight_layout()
    fig.savefig(figure_dir / "rainfall_linked_hydrographs.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
