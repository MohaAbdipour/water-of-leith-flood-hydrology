"""Delineate and map the Water of Leith catchment using open GIS data."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.lines import Line2D
from pyproj import Transformer
from pysheds.grid import Grid
from rasterio.enums import Resampling
from rasterio.features import rasterize, shapes
from rasterio.transform import from_origin
from rasterio.warp import reproject
from shapely.geometry import Point, shape

from water_of_leith.gis import cell_area_km2, hillshade

OUTLET_E = 322_792.0
OUTLET_N = 673_202.0
NRFA_AREA_KM2 = 107.0
CELL_SIZE = 30.0
BOUNDS = (300_000.0, 645_000.0, 340_000.0, 690_000.0)


def prepare_dem(source: Path, target: Path) -> None:
    """Clip and project Copernicus GLO-30 terrain to British National Grid."""
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    width = math.ceil((BOUNDS[2] - BOUNDS[0]) / CELL_SIZE)
    height = math.ceil((BOUNDS[3] - BOUNDS[1]) / CELL_SIZE)
    transform = from_origin(BOUNDS[0], BOUNDS[3], CELL_SIZE, CELL_SIZE)
    destination = np.full((height, width), np.nan, dtype="float32")
    with rasterio.open(source) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs="EPSG:27700",
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:27700",
        "transform": transform,
        "nodata": np.nan,
        "compress": "deflate",
    }
    with rasterio.open(target, "w", **profile) as dst:
        dst.write(destination, 1)


def delineate(dem_path: Path, rivers_path: Path):
    """Hydrologically condition the DEM and delineate the upstream catchment."""
    grid = Grid.from_raster(str(dem_path))
    dem = grid.read_raster(str(dem_path))
    with rasterio.open(dem_path) as src:
        river_lines = gpd.read_file(
            rivers_path, layer="watercourse_link", bbox=tuple(src.bounds)
        )
        river_mask = rasterize(
            ((geometry, 1) for geometry in river_lines.geometry),
            out_shape=src.shape,
            transform=src.transform,
            fill=0,
            dtype="uint8",
        ).astype(bool)
    # A shallow stream burn reconnects channels interrupted by bridges and other
    # urban surface features in the DSM. OS geometry is used only for conditioning.
    burned_dem = dem.copy()
    burned_dem[river_mask] -= 10.0
    conditioned = grid.resolve_flats(grid.fill_depressions(grid.fill_pits(burned_dem)))
    fdir = grid.flowdir(conditioned)
    accumulation = grid.accumulation(fdir)

    # Restrict snapping to cells draining at least 0.9 km². This removes local
    # hillslope cells while retaining tributaries represented at GLO-30 scale.
    snap_threshold_cells = int(0.9 * 1_000_000 / CELL_SIZE**2)
    snapped_e, snapped_n = grid.snap_to_mask(
        accumulation > snap_threshold_cells, (OUTLET_E, OUTLET_N)
    )
    catchment = grid.catchment(
        x=snapped_e, y=snapped_n, fdir=fdir, xytype="coordinate"
    ).astype(bool)
    return grid, np.asarray(dem), catchment, float(snapped_e), float(snapped_n)


def polygonise(mask: np.ndarray, transform):
    polygons = [
        shape(geometry)
        for geometry, value in shapes(mask.astype("uint8"), mask=mask, transform=transform)
        if value == 1
    ]
    return max(polygons, key=lambda polygon: polygon.area)


def main() -> None:
    cache = Path("data/cache/gis")
    outputs = Path("outputs")
    figures = Path("docs/figures")
    outputs.mkdir(exist_ok=True)
    figures.mkdir(exist_ok=True)
    projected_dem = cache / "copernicus_dem_bng_30m.tif"
    prepare_dem(cache / "copernicus_dem_n55w004.tif", projected_dem)
    rivers_path = cache / "open_rivers/Data/oprvrs_gb.gpkg"
    grid, dem, catchment, snapped_e, snapped_n = delineate(projected_dem, rivers_path)

    with rasterio.open(projected_dem) as src:
        transform = src.transform
        bounds = src.bounds
    basin = polygonise(catchment, transform)
    basin_gdf = gpd.GeoDataFrame(geometry=[basin], crs="EPSG:27700")
    rivers = gpd.read_file(
        rivers_path,
        layer="watercourse_link",
        bbox=basin.bounds,
    )
    rivers = gpd.clip(rivers, basin_gdf)
    built_up = gpd.read_file(
        cache / "built_up_areas/os_open_built_up_areas.gpkg",
        layer="os_open_built_up_areas",
        bbox=basin.bounds,
    )
    built_up = gpd.clip(built_up, basin_gdf)
    reservoirs = gpd.read_file(cache / "osm_named_reservoirs.geojson").to_crs("EPSG:27700")
    reservoirs = gpd.clip(reservoirs, basin_gdf)

    valid_elevation = dem[catchment & np.isfinite(dem)]
    derived_area = cell_area_km2(catchment, CELL_SIZE)
    snap_distance = math.hypot(snapped_e - OUTLET_E, snapped_n - OUTLET_N)
    built_up_area = float(built_up.geometry.area.sum() / 1_000_000)
    reservoir_areas = {
        row["name"]: float(row.geometry.area / 1_000_000)
        for _, row in reservoirs.iterrows()
    }
    summary = {
        "station": "Water of Leith at Murrayfield (NRFA 19006)",
        "outlet_easting_m": f"{OUTLET_E:.1f}",
        "outlet_northing_m": f"{OUTLET_N:.1f}",
        "snapped_easting_m": f"{snapped_e:.1f}",
        "snapped_northing_m": f"{snapped_n:.1f}",
        "snap_distance_m": f"{snap_distance:.1f}",
        "dem_derived_area_km2": f"{derived_area:.2f}",
        "nrfa_published_area_km2": f"{NRFA_AREA_KM2:.2f}",
        "area_difference_percent": f"{100 * (derived_area - NRFA_AREA_KM2) / NRFA_AREA_KM2:.2f}",
        "minimum_elevation_m": f"{np.min(valid_elevation):.1f}",
        "median_elevation_m": f"{np.median(valid_elevation):.1f}",
        "maximum_elevation_m": f"{np.max(valid_elevation):.1f}",
        "mapped_river_segments": str(len(rivers)),
        "built_up_area_km2": f"{built_up_area:.2f}",
        "built_up_fraction_percent": f"{100 * built_up_area / derived_area:.2f}",
        "mapped_named_reservoirs": str(len(reservoirs)),
    }
    for name, area in reservoir_areas.items():
        summary[f"{name.lower().replace(' ', '_')}_area_km2"] = f"{area:.3f}"
    with (outputs / "gis_catchment_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        writer.writerows(summary.items())

    shade = hillshade(dem, CELL_SIZE)
    masked_dem = np.ma.masked_where(~catchment, dem)
    fig, ax = plt.subplots(figsize=(9, 8.2), constrained_layout=True)
    extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)
    ax.imshow(shade, extent=extent, origin="upper", cmap="gray", alpha=0.42)
    terrain = ax.imshow(masked_dem, extent=extent, origin="upper", cmap="terrain", alpha=0.78)
    built_up.plot(
        ax=ax, facecolor="#6f6f6f", edgecolor="none", alpha=0.28, hatch="////"
    )
    basin_gdf.boundary.plot(ax=ax, color="#6b3f1d", linewidth=1.7)
    rivers.plot(ax=ax, color="#207bb5", linewidth=0.8, alpha=0.9)
    reservoirs.plot(
        ax=ax, facecolor="#36b9d6", edgecolor="#075985", linewidth=0.8, zorder=5
    )
    label_offsets = {
        "Harperrig Reservoir": (0, 11),
        "Harlaw Reservoir": (18, 10),
        "Threipmuir Reservoir": (18, -13),
    }
    for _, reservoir in reservoirs.iterrows():
        point = reservoir.geometry.representative_point()
        x_offset, y_offset = label_offsets[reservoir["name"]]
        ax.annotate(
            reservoir["name"].replace(" Reservoir", ""),
            (point.x, point.y),
            xytext=(x_offset, y_offset),
            textcoords="offset points",
            fontsize=7.5,
            color="#064e62",
            fontweight="bold",
            ha="center",
            zorder=7,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 1},
        )
    ax.scatter(OUTLET_E, OUTLET_N, marker="^", s=75, color="#b2182b", edgecolor="white", zorder=6)
    ax.annotate("Murrayfield gauge", (OUTLET_E, OUTLET_N), xytext=(7, 6), textcoords="offset points", fontsize=8.5)
    minx, miny, maxx, maxy = basin.bounds
    pad_x, pad_y = (maxx - minx) * 0.05, (maxy - miny) * 0.05
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)
    ax.set_aspect("equal")
    ax.set_xlabel("British National Grid easting (m)")
    ax.set_ylabel("British National Grid northing (m)")
    ax.set_title(
        "Terrain-derived Water of Leith catchment and drainage network",
        loc="left",
        fontweight="bold",
        fontsize=15,
        pad=28,
    )
    ax.text(
        0,
        1.012,
        f"GLO-30 delineation: {derived_area:.1f} km² | NRFA published area: 107 km² | outlet snap: {snap_distance:.0f} m",
        transform=ax.transAxes,
        fontsize=8.5,
    )
    ax.legend(
        handles=[
            Line2D([0], [0], color="#6b3f1d", lw=1.7, label="DEM-derived divide"),
            Line2D([0], [0], color="#207bb5", lw=1.2, label="OS Open Rivers"),
            Line2D([0], [0], color="#6f6f6f", lw=5, alpha=0.4, label="OS built-up area"),
            Line2D([0], [0], color="#075985", lw=5, label="Named reservoir (OSM)"),
            Line2D([0], [0], marker="^", color="none", markerfacecolor="#b2182b", markeredgecolor="white", markersize=8, label="NRFA gauge"),
        ],
        loc="lower left",
        frameon=True,
        fontsize=8,
    )
    colorbar = fig.colorbar(terrain, ax=ax, shrink=0.65, pad=0.02)
    colorbar.set_label("Elevation (m)")
    fig.text(
        0.5,
        0.003,
        "Terrain and built-up areas: Copernicus GLO-30 and OS OpenData. Reservoirs: OpenStreetMap contributors (ODbL). Divide is not the NRFA polygon.",
        ha="center",
        fontsize=7.5,
    )
    fig.savefig(figures / "catchment_gis_context.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(summary)


if __name__ == "__main__":
    main()
