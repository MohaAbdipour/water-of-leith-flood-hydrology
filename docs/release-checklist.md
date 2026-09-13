# Public-release checklist

Current status: **local review candidate; not published**.

## Automated checks

- [x] Complete public pipeline reproduced in a clean Python 3.12 environment.
- [x] Regenerated public outputs match the committed versions.
- [x] Unit and integration-oriented tests pass.
- [x] README local links resolve.
- [x] No raw, cached or restricted data are tracked.
- [x] No common credential or private-key patterns are present.
- [x] No tracked file exceeds 5 MB.

## Scientific and licensing checks

- [x] Open-data sources, licences and attributions are documented.
- [x] NRFA row-level Peak Flow data and catchment geometry remain local.
- [x] Terrain-derived geometry is distinguished from the NRFA boundary.
- [x] Regional stations are not described as an FEH pooling group.
- [x] Statistical uncertainty and negative predictive results are reported.
- [x] Results are explicitly excluded from engineering and operational use.

## Required before publication

- [ ] Review the rendered GitHub README and repository file list with the owner.
- [ ] Confirm the intended public repository name and description.
- [ ] Confirm that no additional local files are to be included.
- [ ] Obtain the owner's explicit instruction to publish.

Publication is not authorised by completion of this checklist.
