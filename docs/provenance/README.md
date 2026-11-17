# Provenance copies (2026-11-16)

Byte-identical copies of small scratch files that a paper figure, table or claim depends on and that were neither in
git nor on the Hub (offsite audit, `scripts/maintenance/audit_offsite.py`; record in
`docs/offsite_audit_2026-11-16.md`). Scratch may be purged; these copies keep the paper regenerable without it.

| File | Scratch original | Used by |
|---|---|---|
| `sources_manifest.json` | `data/sources/manifest.json` | the 21 source downloads: URL, licence, size, full sha256, download date (`docs/licenses.md` lists only the first 16 hex digits); a re-download from the recorded URLs can be checked against it |
| `tiles_v1.0.parquet` | `data/tiles/v1.0/tiles.parquet` | the 14,081 v1.0 tiles: location, QC fractions, biome, realm, ecoregion, gHM tercile; input of the dataset-statistics figures (biome/realm table, NoData histogram), whose columns the Hub index does not carry. To regenerate the figures without scratch, copy it to `data/tiles/v1.0/tiles.parquet` |
| `repro_S_compare.json`, `repro_M_compare.json` | `data/repro/{S,M}_compare.json` | evidence for "regeneration is bitwise reproducible on one CPU model" (paper, Section "The dataset"; `docs/dataset_card.md`): per-shard dataset diffs of a rebuild from `v1.0-pipeline` |

Also tracked since this audit (previously excluded by the `*.parquet` rule in `.gitignore`):
`docs/tables/nodata_sample.parquet` (NoData figure, synthetic side) and `docs/tables/review_round3_raw/*.parquet`
(T4 Pareto heuristic, source-OOD model scores and selections, L reference subsets; `heuristic`, `models_{S,M}` and
`reference_L` are byte-identical to their `aux/review_round3/` originals, the other three exist only here).
