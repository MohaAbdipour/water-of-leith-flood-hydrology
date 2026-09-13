"""Regenerate every public-data result in dependency order."""

from __future__ import annotations

import argparse
import subprocess
import sys

DOWNLOAD_SCRIPTS = [
    "scripts/download_ukflow15.py",
    "scripts/download_ceh_gear1hr.py",
    "scripts/download_gis_data.py",
    "scripts/download_regional_ukflow15.py",
]

ANALYSIS_SCRIPTS = [
    "scripts/run_analysis.py",
    "scripts/run_pot_analysis.py",
    "scripts/run_independence_sensitivity.py",
    "scripts/run_diagnostics.py",
    "scripts/run_nonstationary_assessment.py",
    "scripts/run_rating_sensitivity.py",
    "scripts/run_rainfall_runoff_analysis.py",
    "scripts/run_rainfall_sensitivity.py",
    "scripts/run_event_classification.py",
    "scripts/run_event_classification_sensitivity.py",
    "scripts/run_seasonality_wetness.py",
    "scripts/run_gis_analysis.py",
    "scripts/run_regional_comparison.py",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-downloads",
        action="store_true",
        help="Use already downloaded open inputs from data/raw and data/cache.",
    )
    args = parser.parse_args()
    scripts = ANALYSIS_SCRIPTS if args.skip_downloads else DOWNLOAD_SCRIPTS + ANALYSIS_SCRIPTS
    for script in scripts:
        print(f"\n>>> {script}", flush=True)
        subprocess.run([sys.executable, script], check=True)
    subprocess.run([sys.executable, "-m", "pytest", "-q"], check=True)
    print("\nPublic workflow completed. Restricted NRFA validation was not run.")


if __name__ == "__main__":
    main()
