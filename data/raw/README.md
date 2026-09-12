# Raw data

Raw UK-Flow15 files are intentionally not committed. Download them from the
official catalogue with:

```bash
python scripts/download_ukflow15.py
```

Dataset: Fileni, F. et al. (2025), *Sub-hourly river flow data observations
from 1369 river gauges in the UK, 1948–2023 (UK-Flow15)*, NERC EDS
Environmental Information Data Centre.

DOI: https://doi.org/10.5285/211710ac-f01b-4b52-807f-373babb1c368

Licence: Open Government Licence. Users must review the catalogue record and
cite the dataset. Station `019006` is Water of Leith at Murrayfield.

## Hourly rainfall

Catchment-mean rainfall is extracted on demand from **CEH-GEAR1hr v2** with:

```bash
python scripts/download_ceh_gear1hr.py
```

The script reads the public UKCEH cloud store and the station `19006` catchment
boundary used in UKCEH's FDRI data-access examples. It retains only grid-centre
values inside the Murrayfield catchment and writes the local, gitignored file
`ceh_gear1hr_19006.csv`.

Dataset: Lewis, E. et al. (2022), *Gridded estimates of hourly areal rainfall
for Great Britain 1990–2016 [CEH-GEAR1hr] v2*, NERC EDS Environmental
Information Data Centre. https://doi.org/10.5285/fc9423d6-3d54-467f-bb2b-fc7357a3941f

Licence: Open Government Licence v3. Required acknowledgement: **Contains data
supplied by UK Centre for Ecology & Hydrology.** Source copyright and citation
requirements remain with the dataset.

The catchment polygon is used remotely for spatial selection only and is not
redistributed by this repository. Catchment-boundary rights and conditions
remain with the NRFA/UKCEH source.
