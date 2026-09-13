"""Select and download nearby open UK-Flow15 comparison stations."""

from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

from water_of_leith.regional import select_comparison_stations

ROOT = "https://catalogue.ceh.ac.uk/datastore/eidchub/211710ac-f01b-4b52-807f-373babb1c368"


def main() -> None:
    destination = Path("data/raw/regional")
    destination.mkdir(parents=True, exist_ok=True)
    metadata = pd.read_csv("data/raw/00_station_id_meta.csv")
    selected = select_comparison_stations(metadata)
    selected.to_csv(destination / "selected_stations.csv", index=False)
    for station_id in selected["station_id"]:
        filename = f"{int(station_id):06d}.csv"
        target = destination / filename
        if not target.exists():
            print(f"Downloading {filename}")
            urlretrieve(f"{ROOT}/1_RiverFlowStations/{filename}", target)
    print(selected[["station_id", "River", "Location", "distance_km"]].to_string(index=False))


if __name__ == "__main__":
    main()
