"""Extract catchment-mean CEH-GEAR1hr rainfall for NRFA station 19006."""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import s3fs
import shapely
import xarray as xr

ENDPOINT = "https://fdri-o.s3-ext.jc.rl.ac.uk/"
ZARR_STORE = "s3://gearhrly-spacechunk/gearhrly_10km_chunks_all.zarr"
CATCHMENTS = "example-data/gb_catchments.zip"


def main() -> None:
    filesystem = s3fs.S3FileSystem(anon=True, endpoint_url=ENDPOINT)
    catchments = gpd.read_file(filesystem.open(CATCHMENTS)).set_crs(27700, allow_override=True)
    selected = catchments.loc[catchments["ID_STRING"].astype(str) == "19006"]
    if len(selected) != 1:
        raise ValueError("Expected exactly one catchment boundary for station 19006")
    geometry = selected.geometry.iloc[0]
    min_x, min_y, max_x, max_y = geometry.bounds

    dataset = xr.open_zarr(
        ZARR_STORE,
        storage_options={"anon": True, "endpoint_url": ENDPOINT},
        consolidated=True,
    )
    subset = dataset[["rainfall_amount", "min_dist", "stat_disag"]].sel(
        time=slice("1992-06-01", "2016-12-31 23:00"),
        x=slice(np.floor(min_x / 1000) * 1000, np.ceil(max_x / 1000) * 1000),
        y=slice(np.ceil(max_y / 1000) * 1000, np.floor(min_y / 1000) * 1000),
    )
    grid_x, grid_y = np.meshgrid(subset.x.values, subset.y.values)
    inside = shapely.contains_xy(geometry, grid_x, grid_y)
    if inside.sum() < 50:
        raise ValueError("Catchment mask contains unexpectedly few grid cells")
    mask = xr.DataArray(inside, coords={"y": subset.y, "x": subset.x}, dims=("y", "x"))

    extracted = xr.Dataset({
        "rainfall_mm": subset["rainfall_amount"].where(mask).mean(("y", "x")),
        "statistical_disaggregation_fraction": subset["stat_disag"].where(mask).mean(("y", "x")),
        "maximum_gauge_distance_km": subset["min_dist"].where(mask).max(("y", "x")) / 1000,
    }).compute()
    frame = extracted.to_dataframe().reset_index()
    frame = frame.drop(columns=["crs"], errors="ignore")
    output = Path("data/raw/ceh_gear1hr_19006.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)

    pd.DataFrame([{
        "dataset": "CEH-GEAR1hr v2",
        "station": "19006",
        "start": frame["time"].min(),
        "end": frame["time"].max(),
        "hourly_observations": len(frame),
        "catchment_grid_centres": int(inside.sum()),
        "boundary_area_km2": geometry.area / 1e6,
        "rainfall_missing_hours": int(frame["rainfall_mm"].isna().sum()),
        "hours_using_any_statistical_disaggregation": int((frame["statistical_disaggregation_fraction"] > 0).sum()),
        "maximum_source_gauge_distance_km": frame["maximum_gauge_distance_km"].max(),
    }]).to_csv("outputs/rainfall_data_summary.csv", index=False)


if __name__ == "__main__":
    main()
