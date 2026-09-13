"""Download open terrain and river data used by the GIS figure."""

from pathlib import Path
import json
import time
from zipfile import ZipFile

import requests

DEM_URL = (
    "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
    "Copernicus_DSM_COG_10_N55_00_W004_00_DEM/"
    "Copernicus_DSM_COG_10_N55_00_W004_00_DEM.tif"
)
RIVERS_URL = (
    "https://api.os.uk/downloads/v1/products/OpenRivers/downloads"
    "?area=GB&format=GeoPackage&redirect"
)
BUILT_UP_URL = (
    "https://api.os.uk/downloads/v1/products/BuiltUpAreas/downloads"
    "?area=GB&format=GeoPackage&redirect"
)
RESERVOIRS = [
    "Harlaw Reservoir, Edinburgh, Scotland",
    "Threipmuir Reservoir, Edinburgh, Scotland",
    "Harperrig Reservoir, Scotland",
]


def main() -> None:
    cache = Path("data/cache/gis")
    cache.mkdir(parents=True, exist_ok=True)
    dem_path = cache / "copernicus_dem_n55w004.tif"
    if not dem_path.exists():
        response = requests.get(DEM_URL, timeout=180)
        response.raise_for_status()
        dem_path.write_bytes(response.content)

    rivers_path = cache / "os_open_rivers.zip"
    if not rivers_path.exists():
        response = requests.get(RIVERS_URL, timeout=180)
        response.raise_for_status()
        rivers_path.write_bytes(response.content)
    extracted = cache / "open_rivers"
    if not extracted.exists():
        with ZipFile(rivers_path) as archive:
            archive.extractall(extracted)

    built_up_path = cache / "os_open_built_up_areas.zip"
    if not built_up_path.exists():
        response = requests.get(BUILT_UP_URL, timeout=180)
        response.raise_for_status()
        built_up_path.write_bytes(response.content)
    built_up_extracted = cache / "built_up_areas"
    if not built_up_extracted.exists():
        with ZipFile(built_up_path) as archive:
            archive.extractall(built_up_extracted)

    reservoir_path = cache / "osm_named_reservoirs.geojson"
    if not reservoir_path.exists():
        features = []
        headers = {"User-Agent": "water-of-leith-flood-hydrology/0.1"}
        for index, name in enumerate(RESERVOIRS):
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": name, "format": "geojson", "polygon_geojson": 1, "limit": 1},
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            results = response.json().get("features", [])
            if not results:
                raise RuntimeError(f"No OpenStreetMap geometry returned for {name}")
            features.append(results[0])
            if index < len(RESERVOIRS) - 1:
                time.sleep(1)
        reservoir_path.write_text(
            json.dumps({"type": "FeatureCollection", "features": features}),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
