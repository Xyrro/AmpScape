# Upstream data sources: availability, licences, redistribution

Verified 2026-09-05 from the primary download pages / bucket manifests (Phase 2 pilot scope).
"Derived rasters" = per-tile covariate channels AmpScape stores (class codes, elevation,
slope, distance-to-road, distance-to-river, gHM) — never the original source tiles.

| Layer | Version / year | Access (verified) | Licence (verified) | Redistribute derived rasters? | Notes |
|---|---|---|---|---|---|
| **ESA WorldCover** land cover, 10 m | 2021 v200 | public S3 `s3://esa-worldcover/v200/2021/map/ESA_WorldCover_10m_2021_v200_{N|S}yy{E|W}xxx_Map.tif` (3°×3° COGs, EPSG:4326; e.g. N00E006 = 2.5 MB, N00E009 = 10 MB; grid: `esa_worldcover_grid.geojson` in the same bucket; region eu-central-1, `--no-sign-request`) | **CC BY 4.0** (ESA WorldCover data-access page) | **Yes** | attribution: "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium" |
| **Copernicus DEM GLO-30** | 2021 release (WorldDEM-30 based, © DLR 2010-2014, © Airbus 2014-2018) | public S3 `s3://copernicus-dem-30m/Copernicus_DSM_COG_10_{N|S}yy_00_{E|W}xxx_00_DEM/…_DEM.tif` (1°×1° COGs, ~45 MB each, `tileList.txt` lists 26 450 tiles) | **Copernicus WorldDEM-30 licence** (COP-DEM-GLO-30-F): Art. 4 grants reproduction, distribution, communication to the public, adaptation/modification; Art. 6 requires notices | **Yes, with notices** | required notice on modified data: "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved" + liability sentence "The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30". A few tiles (some countries) are withheld from GLO-30 Public; fall back to GLO-90 (`s3://copernicus-dem-90m`) for those |
| **GRIP4** global roads | v4, 2018 (Meijer et al. 2018, ERL 13:064006) | `https://dataportaal.pbl.nl/downloads/GRIP4/GRIP4_Region{1..7}_vector_shp.zip` (regional shapefiles; global FGDB > 2 GB); 5-arcmin density rasters also available | globio.info states verbatim: "GRIP4 is provided under a Creative Commons License (CC-0) and is free to use." Secondary catalogues (FAO, UNDP GeoHub) label it CC BY 4.0. **We attribute as CC BY 4.0 (the stricter reading).** | **Yes** (as distance / nearest-class rasters) | GRIP4 is PBL's independently harmonised global roads database (UNSDI-Transportation data model), released under PBL's own terms; it is **not an OSM extract and not ODbL**. PBL lists many national/global inputs (OSM among them) and states it verified their public availability. We store only non-reversible derived rasters |
| **HydroRIVERS** | v1.0 (HydroSHEDS) | `https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_shp.zip` (544 MB global) or per-region (e.g. `HydroRIVERS_v10_na_shp.zip`) | HydroSHEDS licence = **CC BY 4.0** (hydrosheds.org/pages/license), "freely available for scientific, educational and commercial use" | **Yes** (distance-to-river raster) | citation Lehner & Grill 2013, Hydrol. Process. 27:2171 |
| **gHM** global Human Modification | v1, 2016 median year, 1 km (Kennedy et al. 2019, GCB) | figshare `https://ndownloader.figshare.com/files/13448294` (`gHM.zip`, 415 MB), DOI 10.6084/m9.figshare.7283087.v1 | **CC BY 4.0** (figshare record) | **Yes** | 300 m temporal version (Theobald et al. 2020, ESSD; Zenodo 3901815) is an option for tiers S/M later |
| **RESOLVE Ecoregions 2017** | 2017 (Dinerstein et al. 2017, BioScience 67:534) | `https://storage.googleapis.com/teow2016/Ecoregions2017.zip` (150 MB shapefile) | **CC BY 4.0** (ecoregions.appspot.com) | used only for stratification (biome / realm labels in the manifest) | |
| **WDPA** protected areas | monthly | protectedplanet.net, registration + terms acceptance | **Restrictive**: no redistribution of WDPA data, non-commercial only without written permission (protectedplanet.net/en/legal) | **No polygons.** Only derived focal-node masks (rasterised, unlabelled) may be stored, and the datasheet must say so | Phase 4 item; not downloaded in the Phase 2 pilot |
| OpenStreetMap | — | — | ODbL (share-alike) | **not used** (owner decision 2026-09-05) | replaced by GRIP4, PBL's own database |

## Manifest reconciliation (Phase 8, 2026-09-07)

Every file in `data/sources/manifest.json` (21 entries, 5.45 GB) with its recorded licence and checksum:

| manifest key | size | licence recorded | sha256 | downloaded |
|---|---|---|---|---|
| `ghm_v1_1km` | 415 MB | CC BY 4.0 | `b20f0f76a6a235be…` | 2026-09-05 |
| `grip4_region1` | 909 MB | CC0 / CC BY 4.0 (see docs/licenses.md) | `fa3958e36a8a9bd8…` | 2026-09-05 |
| `grip4_region2` | 447 MB | CC0 / CC BY 4.0 (see docs/licenses.md) | `3d9abcb589e636a0…` | 2026-09-05 |
| `grip4_region3` | 242 MB | CC0 / CC BY 4.0 (see docs/licenses.md) | `a774a67acaf15820…` | 2026-09-05 |
| `grip4_region4` | 1233 MB | CC0 / CC BY 4.0 (see docs/licenses.md) | `550a848f032f0d04…` | 2026-09-05 |
| `grip4_region5` | 151 MB | CC0 / CC BY 4.0 (see docs/licenses.md) | `4ef0be517b962b67…` | 2026-09-05 |
| `grip4_region6` | 711 MB | CC0 / CC BY 4.0 (see docs/licenses.md) | `3285978f1ce05edc…` | 2026-09-05 |
| `grip4_region7` | 59 MB | CC0 / CC BY 4.0 (see docs/licenses.md) | `609d9f8d868aab55…` | 2026-09-05 |
| `hydrorivers_v10_af` | 108 MB | CC BY 4.0 | `63cc615134d8812b…` | 2026-09-05 |
| `hydrorivers_v10_ar` | 22 MB | CC BY 4.0 | `fd679ed159594406…` | 2026-09-05 |
| `hydrorivers_v10_as` | 91 MB | CC BY 4.0 | `29780b0a75f90024…` | 2026-09-05 |
| `hydrorivers_v10_au` | 49 MB | CC BY 4.0 | `538c87868636c63c…` | 2026-09-05 |
| `hydrorivers_v10_eu` | 68 MB | CC BY 4.0 | `500da7d36ceee0aa…` | 2026-09-05 |
| `hydrorivers_v10_gr` | 9 MB | CC BY 4.0 | `436bd112718f14ad…` | 2026-09-05 |
| `hydrorivers_v10_na` | 66 MB | CC BY 4.0 | `47c2e30041b1a6e0…` | 2026-09-05 |
| `hydrorivers_v10_sa` | 95 MB | CC BY 4.0 | `38bfdcdfcc0698b1…` | 2026-09-05 |
| `hydrorivers_v10_si` | 47 MB | CC BY 4.0 | `ea7432be3b350f3e…` | 2026-09-05 |
| `published_eurac_alps_permeability` | 159 MB | CC BY 4.0 (Zenodo 10.5281/zenodo.6602481) | `333296bf2fdd23b3…` | 2026-09-07 |
| `published_hawaiian_gallinule_resistance` | 299 MB | CC0 1.0 (Dryad 10.5061/dryad.p90b87p) | `7cb2c8e684a27dbf…` | 2026-09-07 (manual) |
| `published_raccoon_europe_maps` | 121 MB | CC BY 4.0 (figshare 10.6084/m9.figshare.27311484.v1) | `c7d349831ced3e3f…` | 2026-09-07 |
| `resolve_ecoregions_2017` | 149 MB | CC BY 4.0 | `be36d6209e443038…` | 2026-09-05 |

Consistency is enforced by `tests/test_licenses.py` (every manifest entry has a licence in the
permitted set, a sha256, and a row in this file).

## Verification status and unverifiable items

| Source | How the licence was verified | Status |
|---|---|---|
| ESA WorldCover 2021 v200 | ESA WorldCover data-access statement (CC BY 4.0) as quoted in search results; bucket is public | verified indirectly — **recommend one manual check of the ESA terms page before publication** |
| Copernicus DEM GLO-30 | licence PDF (COP-DEM-GLO-30-F) downloaded and read: Art. 4 rights of use, Art. 6 notices | **verified** (text quoted above) |
| GRIP4 | globio.info page read: "provided under a Creative Commons License (CC-0)"; FAO / UNDP catalogues list CC BY 4.0; one catalogue lists ODbL | **ambiguous** — three different statements exist; we attribute as CC BY 4.0 and store only distance/class rasters. **Cannot be resolved without asking PBL**; flagged for the owner |
| HydroRIVERS v1.0 | hydrosheds.org licence page (CC BY 4.0) | verified via the site text as returned by search; **recommend one manual read of the PDF licence** |
| gHM v1 | figshare API: licence CC BY 4.0 | **verified** |
| RESOLVE Ecoregions 2017 | ecoregions.appspot.com statement (CC BY 4.0) via search snippet | verified indirectly — **recommend one manual check** |
| Eurac Alps permeability | Zenodo API: `cc-by-4.0` | **verified** |
| Raccoon Europe maps | figshare API: CC BY 4.0 | **verified** |
| Hawaiian gallinule layers | Dryad API: CC0 1.0 | **verified** |
| WDPA | protectedplanet.net legal page | **not redistributable**; not downloaded, not used |

Nothing in the manifest has an unknown licence. The only genuinely unverifiable item is the exact
GRIP4 licence (CC0 vs CC BY 4.0 vs ODbL statements from different catalogues); treating it as CC BY
4.0 with attribution is the conservative reading among the two Creative Commons statements, and
storing only non-reversible derived rasters limits exposure under any of them.

## Combined data licence

All stored covariates derive from CC BY 4.0 sources or the Copernicus WorldDEM-30 licence
(which permits redistribution with notices). The dataset can therefore be released under
**CC BY 4.0** with an attribution block listing every upstream source above, plus the
Copernicus notices verbatim. WDPA-derived masks (if any) are stored without identifiers.

## Source download ledger (Phase 2–3)

| Item | Size |
|---|---|
| RESOLVE Ecoregions 2017 | 150 MB |
| gHM v1 1 km | 415 MB |
| HydroRIVERS regional shapefiles for continents with pilot tiles (≤ 6) | ≤ 480 MB |
| GRIP4 regional shapefiles, all 7 regions (approved 2026-09-05) | 3.5 GB |
| HydroRIVERS, all 9 regions | 0.5 GB |
| WorldCover / Copernicus DEM | windowed reads from COGs via `/vsicurl/`, only the pixels needed (≈ 1 MB per tier-S tile) |
| **Cumulative archives on scratch** | **4.87 GB** (18 files, sha256 in `data/sources/manifest.json`; 18 GB unzipped) |

Gate (refined 2026-09-05): ask before any single download > 5 GB or cumulative > 20 GB. Full-scale set (all GRIP4 + HydroRIVERS regions) ≈ 5.1 GB cumulative, approved 2026-09-05.
