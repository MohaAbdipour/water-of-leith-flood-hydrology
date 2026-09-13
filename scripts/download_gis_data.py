"""Download open terrain and river data used by the GIS figure."""

from pathlib import Path
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


if __name__ == "__main__":
    main()
