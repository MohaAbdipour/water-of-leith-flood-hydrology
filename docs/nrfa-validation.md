# NRFA validation protocol

The National River Flow Archive Peak Flow Dataset is free to access but is not
redistributable under the terms applying to the downloaded files. The archive,
station AMAX/POT files and row-level comparisons are therefore stored only in
the ignored `data/restricted/` directory.

To repeat the validation:

1. Review and accept the official NRFA licence yourself.
2. Download Peak Flow Dataset v15 from the NRFA website.
3. Extract it under `data/restricted/nrfa-v15/`.
4. Run `python scripts/validate_against_nrfa.py` after the open-data analysis.

The validation script exports only aggregate agreement diagnostics and fitted
statistical estimates. It does not export the NRFA annual-maximum series.

Required acknowledgement: **Data from the UK National River Flow Archive,
Peak Flow Dataset version 15.**

- Dataset page: https://nrfa.ceh.ac.uk/data/peak-flow-dataset
- Licence: https://eidc.ceh.ac.uk/licences/nrfa-data-terms-and-conditions-for-api-access-to-time-series-data-and-metadata/

