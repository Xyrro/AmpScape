# Phase 8 report — licensing and provenance

Date: 2026-09-07. Status: **complete, awaiting owner confirmation** before Phase 9 (metrics and evaluation harness).

## What was done

- `docs/licenses.md` reconciled with every entry of `data/sources/manifest.json` (21 files, 5.45 GB): the
  seven core layers, GRIP4 regions 1–7, HydroRIVERS regions ×9, and the three published resistance rasters
  (Eurac Alps CC BY 4.0, raccoon Europe CC BY 4.0, Hawaiian gallinule CC0, the last registered from the
  owner's manual download with `download_sources.py --register`). A manifest reconciliation table (licence,
  sha256, date) and a verification-status table were added.
- `CITATION.cff` completed (dataset metadata + references for both solvers and every upstream source).
- Dataset card: "Redistribution terms and attributions" section with the mandatory Copernicus notices, the
  CC BY attributions, the CC0 items, and the not-used sources (WDPA, OSM); the refinement sentence was added
  to the card and the task spec as requested.
- `tests/test_licenses.py`: every manifest entry must carry a licence from the permitted set, a sha256 and
  a row in `docs/licenses.md` (the test skips on machines without the manifest).

## Licence status

| Verified from the licence document or repository API | Verified from site text via search (manual check recommended) | Unverifiable |
|---|---|---|
| Copernicus DEM (PDF read), gHM (figshare API), Eurac Alps (Zenodo API), raccoon Europe (figshare API), Hawaiian gallinule (Dryad API) | ESA WorldCover (CC BY 4.0), HydroRIVERS (CC BY 4.0), RESOLVE 2017 (CC BY 4.0) | **GRIP4**: globio.info says CC0, FAO/UNDP catalogues say CC BY 4.0, one catalogue says ODbL — cannot be resolved without asking PBL; attributed as CC BY 4.0, only distance/class rasters stored |

Combined data licence: CC BY 4.0 with the attribution block; nothing in the manifest has an unknown
licence; WDPA remains excluded.

## Next step (Phase 9, on confirmation)

Metrics (`ampscape/metrics`): pixel-level in log10-ε space, domain-level (top-q % IoU, pinch-point
recall, Spearman, corridor Dice), Reff metrics, physics residuals, efficiency, the solver-acceleration
track (warm-start PCG from predicted voltages), `scripts/evaluate.py` + leaderboard export, and the
`test_ood_published` set from the three downloaded rasters.
