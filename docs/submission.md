# Submitting results to the AmpScape leaderboard

Status (2026-10-05): the submission path is implemented (`scripts/submit_results.py`) and the leaderboard has been
seeded locally with the official Phase 10-full baselines. **The seeded `aux/leaderboard/` files have not been pushed to
the Hub yet; the maintainer pushes them after the tuning pass** (`scripts/submit_results.py append --push`, login node
only). Until then the leaderboard location below is reserved, not live.

Evaluation harness and metric definitions: `docs/evaluation.md`; predictions layout: the module docstring of
`ampscape/eval/harness.py`; data splits and tiers: `docs/dataset_card.md`.

## 1. What a submission contains

One directory per evaluated (task, tier, split) with exactly two files — the existing harness format, nothing new:

```
<submission>/<anything>/predictions.h5     /<sample_id>/<config>/<dataset>  (+ attr inference_time_s per config group)
<submission>/<anything>/meta.json
```

The directory name is free (the `<root>_<tier>_<split>` naming used by `scripts/train.py` is not required); tier and
split are declared in `meta.json` and checked by the validator.

### predictions.h5

One group per `sample_id`, one subgroup per configuration (`points`, `wall_to_wall_NS`/`_EW`, `regions`, `advanced`,
`omniscape`), holding (see `ampscape/eval/harness.py`):

| task | required dataset | dtype, shape | optional datasets |
|---|---|---|---|
| T1 (pairwise, `points`) | `cum_current` | float32 (H, W) | `voltage` (H, W) or (P, H, W), `pairwise_current` (P, H, W) |
| T1W (`wall_to_wall_*`), T1R (`regions`) | `cum_current` | float32 (H, W) | `voltage` |
| T2 (`points`) | `reff` | float64 (K, K) | — |
| T3 (`advanced`) | `current` | float32 (H, W) | `voltage` (H, W) |
| T4 (`omniscape`) | `cum_current` | float32 (H, W) | `flow_potential`, `normalized` (H, W) |

`H`, `W` and `K` are the index values of the row (tier raster sizes: S 128², M 256², L 512², XL 1024², XXL 2048²).
Every configuration group carries the attribute `inference_time_s` (float, wall clock per configuration **including
any preprocessing**, > 0); the speed-up column is the recorded solver time divided by it.

Coverage: **every `qc_pass` sample of the declared split whose configuration kind matches the task must be present,
and nothing else** (no samples of other splits, kinds or tiers in the file). The harness itself skips absent samples,
which is convenient for development but not accepted for a leaderboard entry.

NaN policy: predictions must be finite everywhere (no NaN/Inf), including under NoData pixels — those are masked out
of the metrics but a NaN anywhere fails validation. Negative currents are allowed (they are measured by
`phys_neg_fraction`), as is any value range; the metrics are defined in `docs/evaluation.md`.

### meta.json (required fields)

```json
{
 "model": "MyNet-base",
 "task": "T1",
 "tier": "M",
 "split": "test_id",
 "seed": 1,
 "params_M": 7.77,
 "train_data": "AmpScape v1.0 tiers S+M, train split only (qc_trainval), no external data",
 "train_tiers": ["S", "M"],
 "hardware": "1x NVIDIA L40S 48 GB",
 "inference_batch": 8,
 "code_url": "https://github.com/<org>/<repo>",
 "code_commit": "0123abcd",
 "contact": "name <mail@example.org>",
 "notes": "free text (optional)",
 "submitter": "display name for the leaderboard (optional; defaults to contact)"
}
```

`train_data` is the training-data statement: which subset(s), tiers and splits were used and whether anything outside
the `train`/`val` splits or outside AmpScape was used. `train_tiers` drives the zero-shot flag (below).

### Rules

- **Zero-shot at XL and XXL.** XL and XXL are the held-out-scale tiers for models trained at ≤ L (`docs/dataset_card.md`,
  "Splits and leakage"). An entry at XL/XXL is zero-shot unless `train_tiers` includes that tier (XL has a 25 % train/val
  share since v1.0.2; XXL is test-only). The validator and the entry schema set `zero_shot = tier not in train_tiers`;
  declare XL training explicitly, it is reported in its own column.
- **Batch 1 at XL and XXL.** Inference at XL/XXL runs one landscape at a time (`inference_batch` must be 1, as for the
  official transfer rows), so inference times and speed-ups are comparable across submissions. At S/M/L the batch is free
  and is recorded.
- **Reported splits.** `test_id`, `test_ood`, `ood_region` at every tier; the published-resistance tiles
  (`test_ood_published`, `aux/test_ood_published`) at S. Entries are per split; submit all three for a tier when you
  can — the README shows each split's table separately. Per-OOD-flag breakdowns (`test_ood_*`) are kept in the harness
  output but are not leaderboard columns.
- **T4 at M and L** is reported against the block-centred production target (`t4_target = "production"`, every sample
  of the split) **and** against the exact block-1 reference map on the reference subset (`t4_target =
  "block1_reference"`, 1 000 samples at M, 60 at L; `docs/t4_fidelity.md`, owner decision 2026-09-18). The second row
  needs the validator run with `--t4-reference aux/t4_bs1_reference/<tier>_bs1` and `make-entry --t4-target
  block1_reference`, which averages the per-sample harness rows the harness scored against the reference. The two
  targets are shown in separate tables and are not comparable with each other.
- **Seeds.** One entry per model × task × tier × split. Several seeds are aggregated into one entry (mean ± sample
  std, `seeds.n` and the seed list); single-seed entries are allowed and show `seeds.n = 1`.
- **Nothing is recomputed.** Every leaderboard number comes from a harness `results.json`; the only arithmetic on
  top is the mean / std over seeds.

## 2. Leaderboard entry schema (JSON)

One JSON object per line of `aux/leaderboard/results.jsonl`:

```json
{
 "submission_id": "sub-20261005-3f9a1c2b7e",
 "timestamp": "2026-10-05T10:00:00+00:00",
 "submitter": "display name",
 "model": "MyNet-base",
 "task": "T1",
 "tier": "M",
 "split": "test_id",
 "metrics": {
  "rel_l2": 0.212, "mae_log10eps": 0.103, "top5_iou": 0.708, "pinch_recall": 0.722, "spearman": 0.964,
  "corridor_dice": 0.861, "ssim": 0.957, "speedup_median": 773.0, "inference_time_s_median": 0.0041, "n": 4830
 },
 "metrics_std": {"rel_l2": 0.023, "mae_log10eps": 0.014, "top5_iou": 0.041, "pinch_recall": 0.071,
                 "spearman": 0.009, "corridor_dice": 0.012, "ssim": 0.004},
 "params_M": 7.77,
 "train_tiers": ["M"],
 "zero_shot": false,
 "seeds": {"n": 3, "values": [1, 2, 3]},
 "notes": "free text",
 "t4_target": null,
 "hardware": "1x NVIDIA L40S",
 "inference_batch": 8,
 "code_url": "https://github.com/<org>/<repo>",
 "code_commit": "0123abcd",
 "source": {"kind": "submission", "train_data": "...", "contact": "...", "evaluated_at": ["..."]}
}
```

Field rules (enforced by `validate_entry` in `scripts/submit_results.py`):

| field | type / values |
|---|---|
| `submission_id` | 3–128 chars of `[A-Za-z0-9._@+-]`, unique in the file (`sub-<YYYYMMDD>-<hash>` for submissions, `baseline-…` for the official rows) |
| `timestamp` | ISO-8601 |
| `submitter`, `model` | non-empty strings; `notes` any string |
| `task` | `T1`, `T1W`, `T1R`, `T2`, `T3`, `T4` |
| `tier` | `S`, `M`, `L`, `XL`, `XXL` |
| `split` | `test_id`, `test_ood`, `ood_region`, `test_ood_published` |
| `metrics` | exactly the ten keys above; floats or `null` (metric not applicable), `rel_l2` required (sort key), `n` positive integer = evaluated (sample, config) rows; `corridor_dice` is the harness `corridor_dice_q10`; `speedup_median` and `inference_time_s_median` are medians over the rows |
| `metrics_std` | `null` when `seeds.n == 1`; otherwise an object over the seven averaged metrics (sample std, ddof 1; `null` where unavailable) |
| `params_M` | non-negative float or `null` (non-learned methods) |
| `train_tiers` | non-empty list of tiers |
| `zero_shot` | boolean, must equal `tier not in train_tiers` |
| `seeds` | `{"n": k, "values": [k integers]}` |
| `t4_target` | required for T4: `production` or `block1_reference`; must be absent/`null` for other tasks |
| `hardware`, `inference_batch`, `code_url`, `code_commit`, `source` | optional; `inference_batch` must be 1 at XL/XXL |

Unknown fields are rejected so the file stays machine-readable.

## 3. Running the validator

```
python scripts/submit_results.py validate --predictions <dir> --root <data root> --tier M --split test_id \
    --workers 8 [--t4-reference aux/t4_bs1_reference/M_bs1] [--no-eval]
```

`--root` is the data root the harness reads: an HF-layout download (`index/<tier>.parquet` + `data/<tier>/…`) or a
build directory (`index.parquet` + `shards/`). The validator checks, in this order, and stops at the first failing stage:

1. `meta.json`: all required fields with the right types; `tier`/`split` equal the command-line values; `train_tiers`
   valid; `inference_batch == 1` at XL/XXL.
2. `predictions.h5` against the index: the set of `qc_pass` samples of the split with the task's configuration kind must
   be exactly the set of groups in the file (missing and extra samples are listed); every expected configuration group
   is present; required datasets exist; dtypes (`float32`, `reff` `float64`) and shapes (`(H, W)` of the index row,
   `(K, K)` for `reff`, `(P, H, W)` allowed for `voltage`/`pairwise_current`); no NaN/Inf; `inference_time_s` present,
   finite and > 0; no datasets outside the documented set.
3. The harness `evaluate()` with `--workers` processes (`--t4-reference` forwarded), writing `results.json` and
   `results.md` **next to the predictions** (inside `--predictions`), and printing the primary metrics
   (mean / median / n) per task plus the median speed-up. `--no-eval` runs stages 1–2 only.

Exit status 0 means the directory is accepted. Then build the entry:

```
python scripts/submit_results.py make-entry --results <dir>/results.json --meta <dir>/meta.json \
    [--seeds <dir_seed2>/results.json <dir_seed3>/results.json] [--submitter NAME] [--t4-target block1_reference] \
    --out entry.json
```

`make-entry` reads the per-task aggregate of the harness file(s) (means, the median inference time, the median
speed-up, `n`), averages seeds, and writes a schema-valid entry. The harness results of the extra seeds must come from
the same task/tier/split; their seed numbers are taken from the `meta` block the harness stored in each file.

## 4. Where the leaderboard lives and how entries get in

- Hub (`Xirro/AmpScape`): `aux/leaderboard/results.jsonl` — the append-only record, one entry per line — and
  `aux/leaderboard/README.md` — the rendered tables, one per task × tier × split (× T4 target), sorted by `rel_l2`
  ascending, with `± std` over seeds, params, seeds, speed-up, inference time, `n`, date and the submission id.
- Local source: `aux/leaderboard/` in the scratch checkout (`aux/` is git-ignored; the Hub copy is the record).
- Policy: **entries are appended by a maintainer only**, with `scripts/submit_results.py append --entry entry.json
  [--push]`, after re-running the validator on the submitted predictions. `append` validates the schema, refuses
  duplicate ids, appends to `results.jsonl`, re-renders `README.md`, and with `--push` uploads both files through
  `scripts/push_aux.py` (sha256-verified, nothing deleted; login node only — compute nodes have no Hub access for
  pushes by project convention). Entries are never edited or removed; a correction is a new entry whose `notes`
  names the superseded id.
- Submitters open an issue in the code repository (`https://github.com/xyrro/EcoFlowBench`) titled
  `Leaderboard: <model> <task> <tier> <split>` with (i) the `entry.json` produced by `make-entry`, (ii) a link to the
  predictions — a Hub dataset/model repo or any download the maintainer can fetch; the `predictions.h5` + `meta.json`
  per split, not the checkpoints — and (iii) the validator output. The maintainer re-validates, appends and pushes;
  the issue is closed with the submission id.
- Official baselines: `scripts/submit_results.py seed-baselines --runs runs/full [--push]` builds the entries of every
  official run group `<model>_<task>_<tier>_s<seed>` (suffixed variants such as `_scalenorm`, `_n1000_ep30`,
  `_voltage` are skipped) from `results.json` (in-tier rows, `zero_shot = false`, three seeds), the scale-transfer rows
  from `results_transfer.json` (XL/XXL, `zero_shot = true`, model `"<model> (trained at L)"`), and — once the files
  contain rows scored against the reference — the T4 block-1 rows from `eval_t4_reference/results.json`. Baseline ids
  are deterministic (`baseline-<model>_<task>_<tier>-<split>`, `…-xfer-<tier>-<split>`, `…-block1`) so re-running the
  command is idempotent.

Known gap (2026-10-05): the official `eval_t4_reference/results.json` files carry no per-sample `t4_target`, i.e. the
block-1 reference was not applied when they were produced (`ampscape/eval/harness.py` only reaches the reference
branch for pairwise kinds); `seed-baselines` therefore warns and seeds no `block1_reference` rows until those
evaluations are redone with a fixed harness.
