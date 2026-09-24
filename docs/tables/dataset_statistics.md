# v1.0 dataset statistics

## Contrast

| tier | family | n | log10 contrast p10 / p50 / p90 | max |
|---|---|---|---|---|
| S | synthetic | 60,000 | 1.00 / 3.00 / 4.00 | 1e+06 |
| S | real | 40,000 | 0.76 / 1.79 / 2.79 | 1e+03 |
| M | synthetic | 30,000 | 1.00 / 3.00 / 4.00 | 1e+06 |
| M | real | 20,000 | 1.30 / 1.98 / 2.98 | 1e+03 |
| L | synthetic | 12,000 | 1.00 / 3.00 / 4.00 | 1e+06 |
| L | real | 8,000 | 1.78 / 2.53 / 3.00 | 1e+03 |
| XL | synthetic | 2,400 | 1.00 / 3.00 / 4.00 | 1e+06 |
| XL | real | 1,600 | 1.90 / 2.96 / 3.00 | 1e+03 |
| XXL | synthetic | 210 | 1.00 / 3.00 / 4.00 | 1e+06 |
| XXL | real | 190 | 2.00 / 3.00 / 3.00 | 1e+03 |

## Biome / realm coverage (real landscapes, all tiers)

| biome | landscapes | tiles |
|---|---|---|
| Boreal Forests/Taiga | 3,845 | 769 |
| Deserts & Xeric Shrublands | 9,070 | 1,814 |
| Flooded Grasslands & Savannas | 3,715 | 743 |
| Mangroves | 1,260 | 252 |
| Mediterranean Forests, Woodlands & Scrub | 5,080 | 1,016 |
| Montane Grasslands & Shrublands | 5,320 | 1,064 |
| N/A | 285 | 57 |
| Temperate Broadleaf & Mixed Forests | 7,825 | 1,565 |
| Temperate Conifer Forests | 4,225 | 845 |
| Temperate Grasslands, Savannas & Shrublands | 6,915 | 1,383 |
| Tropical & Subtropical Coniferous Forests | 2,170 | 434 |
| Tropical & Subtropical Dry Broadleaf Forests | 3,745 | 749 |
| Tropical & Subtropical Grasslands, Savannas & Shrublands | 6,010 | 1,202 |
| Tropical & Subtropical Moist Broadleaf Forests | 7,880 | 1,576 |
| Tundra | 2,445 | 489 |

| realm | landscapes | tiles |
|---|---|---|
| Afrotropic | 9,735 | 1,947 |
| Australasia | 10,470 | 2,094 |
| Indomalayan | 4,985 | 997 |
| N/A | 285 | 57 |
| Nearctic | 12,005 | 2,401 |
| Neotropic | 15,405 | 3,081 |
| Oceania | 145 | 29 |
| Palearctic | 16,760 | 3,352 |

## NoData fraction

| population | n | p10 / p50 / p90 | max |
|---|---|---|---|
| real tiles (manifest, all tiers) | 69,790 | 0.000 / 0.002 / 0.159 | 0.896 |
| synthetic (sampled shards) | 526 | 0.000 / 0.000 / 0.206 | 0.639 |

## Solve time per configuration (seconds; median / p90 / max)

| tier | points | wall_to_wall_NS | wall_to_wall_EW | regions | advanced | omniscape | per landscape (median) |
|---|---|---|---|---|---|---|---|
| S | 0 / 0 / 5 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 1 / 6 | 0 / 0 / 2 | 52 / 84 / 531 | 52 |
| M | 1 / 1 / 4 | 0 / 0 / 1 | 0 / 0 / 2 | 1 / 3 / 14 | 0 / 0 / 1 | 107 / 161 / 253 | 110 |
| L | 4 / 6 / 13 | 2 / 2 / 5 | 2 / 2 / 4 | 5 / 14 / 167 | 2 / 3 / 4 | 702 / 1020 / 1262 | 714 |
| XL | 17 / 30 / 39 | 11 / 13 / 14 | 8 / 10 / 12 | 22 / 65 / 3421 | 13 / 27 / 36 | 3087 / 4320 / 5486 | 3155 |
| XXL | 63 / 108 / 153 | 43 / 65 / 75 | 35 / 39 / 47 | 84 / 210 / 717 | 96 / 339 / 441 | 9821 / 14846 / 18455 | 10212 |

## Storage on the Hub (GB)

| tier | T1 | T1W | T1R | T3 | T4 | total | landscapes | GB per landscape |
|---|---|---|---|---|---|---|---|---|
| S | 31.9 | 43.9 | 12.3 | 24.6 | 29.7 | 142.4 | 100,000 | 1.4 MB |
| M | 56.7 | 75.5 | 22.7 | 42.9 | 53.9 | 251.7 | 50,000 | 5.0 MB |
| L | 84.3 | 113.5 | 37.3 | 64.0 | 81.8 | 380.9 | 20,000 | 19.0 MB |
| XL | 61.4 | 81.9 | 30.2 | 47.3 | 60.9 | 281.7 | 4,000 | 70.4 MB |
| XXL | 21.4 | 26.6 | 13.1 | 17.4 | 22.2 | 100.7 | 400 | 251.7 MB |
| **total** | 255.7 | 341.4 | 115.6 | 196.2 | 248.5 | **1157.4** | 174,400 | |

Subsets: mini 0.61 GB, core 115.49 GB (3,705 files), full 1157.4 GB; `aux/` 20.5 GB.

Figures: `docs/figures/dataset_stats_{contrast,biome_realm,nodata,solve_times,storage}.png`.
