"""Download the openly licensed UK-Flow15 Murrayfield record and metadata."""

from pathlib import Path
from urllib.request import urlretrieve

DOI = "https://doi.org/10.5285/211710ac-f01b-4b52-807f-373babb1c368"
ROOT = "https://catalogue.ceh.ac.uk/datastore/eidchub/211710ac-f01b-4b52-807f-373babb1c368"
FILES = {
    "019006.csv": f"{ROOT}/1_RiverFlowStations/019006.csv",
    "00_station_id_meta.csv": f"{ROOT}/2_metadata/2_1_station_identification_metadata/00_station_id_meta.csv",
    "01_common_sense_anomalies_meta.csv": f"{ROOT}/2_metadata/2_2_quality_control_metadata/01_common_sense_anomalies_meta.csv",
    "02_uk_products_meta.csv": f"{ROOT}/2_metadata/2_2_quality_control_metadata/02_uk_products_meta.csv",
    "03_traditional_qc_meta.csv": f"{ROOT}/2_metadata/2_2_quality_control_metadata/03_traditional_qc_meta.csv",
    "04_high_flows_qc_meta.csv": f"{ROOT}/2_metadata/2_2_quality_control_metadata/04_high_flows_qc_meta.csv",
}


def main() -> None:
    destination = Path("data/raw")
    destination.mkdir(parents=True, exist_ok=True)
    for filename, url in FILES.items():
        target = destination / filename
        if not target.exists():
            print(f"Downloading {filename}")
            urlretrieve(url, target)
    print(f"Source and citation: {DOI}")


if __name__ == "__main__":
    main()

