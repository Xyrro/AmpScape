#!/bin/bash
# Verification (owner, 2026-10-15, item 1): a reviewer's path on a compute node — fresh clone of the GitHub repository
# at a tag, fresh Python environment from uv.lock, the test suite, the documented loader on the `lite` subset, and
# scripts/evaluate.py on one published baseline's predictions from the Hub, compared with docs/tables/baselines_full.md
# of origin/main at the printed precision. Nothing is read from the working tree except the HF token.
#
#   sbatch -A coc -q coc-ice -p coc-cpu -c8 --mem=48G -t 04:00:00 --export=ALL,TAG=v1.0.2 \
#       -o work/verify/fresh_clone_%j.out scripts/verify/fresh_clone_verify.sbatch
set -uo pipefail
TAG=${TAG:-v1.0.2}
BASELINE=${BASELINE:-unet_T1_S_s1}
PRED_TAG=${PRED_TAG:-hfcache_S_test_id}
TIER=${TIER:-S}
SPLIT=${SPLIT:-test_id}
W=/tmp/ampscape_verify_${SLURM_JOB_ID}
TOKEN_SRC=${TOKEN_SRC:-/storage/ice1/1/8/yxiao413/EcoFlowBench/.hf_cache/token}
mkdir -p "$W"
trap 'echo "cleanup $W"; rm -rf "$W"' EXIT
step() { echo; echo "=== $(date -u +%FT%TZ) $*"; }
step "host=$(hostname) tag=$TAG baseline=$BASELINE"; df -h /tmp | tail -n 1; nproc; free -g | head -n 2
cd "$W"

step "bootstrap uv (UNDOCUMENTED: the README assumes uv is installed; here: system python3 venv + pip install uv)"
python3 --version
python3 -m venv "$W/boot" && "$W/boot/bin/pip" -q install uv 2>&1 | tail -n 2
export PATH="$W/boot/bin:$PATH" UV_CACHE_DIR="$W/uv_cache" UV_PYTHON_INSTALL_DIR="$W/uv_python" HF_HOME="$W/hf"
mkdir -p "$HF_HOME" && cp "$TOKEN_SRC" "$HF_HOME/token" && chmod 600 "$HF_HOME/token"
echo "token copied (the dataset is private: a reviewer needs a read token)"
uv --version

step "clone (ssh; the README shows the https URL, which needs the repository to be public)"
/usr/bin/time -f "clone %e s" git clone -q git@github.com:Xyrro/AmpScape.git repo || { echo "FAIL clone"; exit 1; }
cd repo && git checkout -q "$TAG" && echo "checked out $(git log -1 --format='%H %cs %s' | cut -c1-120)"
git show origin/main:docs/tables/baselines_full.md > "$W/baselines_full_main.md"

step "uv python install 3.11 && uv sync --extra dev (documented)"
/usr/bin/time -f "uv python install %e s" uv python install 3.11 2>&1 | tail -n 2
/usr/bin/time -f "uv sync %e s" uv sync --extra dev 2>&1 | tail -n 3
uv run python -c "import ampscape, torch, h5py, pandas; print('import ok; torch', torch.__version__, 'cuda', torch.cuda.is_available())" || echo "FAIL import"
du -sh .venv "$UV_CACHE_DIR" 2>/dev/null

step "test suite (uv run pytest -q tests)"
/usr/bin/time -f "pytest %e s" uv run pytest -q tests -p no:cacheprovider 2>&1 | tail -n 25

step "documented loader on the lite subset: load_from_hub('T1','S', split='train', subset='lite')"
export W
/usr/bin/time -f "loader %e s" uv run python - <<'PY'
import os, time
from ampscape.data import load_from_hub
t = time.time()
ds = load_from_hub("T1", "S", split="train", subset="lite", cache_dir=os.environ["W"] + "/hf_cache")
x = ds[0]
print("lite T1 S train:", len(ds), "samples;", {k: getattr(v, "shape", type(v).__name__) for k, v in x.items() if k != "meta"}, "in", round(time.time() - t), "s")
PY
echo "downloaded by the loader: $(du -sh "$W/hf_cache" | cut -f1) (card: lite ≈ 26 GB for S+M+L, all tasks; this call asked for S/T1 only)"
find "$W/hf_cache" -name "*.h5" | wc -l
if [ "${LITE_FULL:-0}" = "1" ]; then
  step "whole lite subset through the loader (S, M, L × T1, T1W, T1R, T3, T4)"
  /usr/bin/time -f "lite loader %e s" uv run python - <<'PY'
import os, time
from ampscape.data import load_from_hub
for tier in ("S", "M", "L"):
    for task in ("T1", "T1W", "T1R", "T3", "T4"):
        t = time.time()
        ds = load_from_hub(task, tier, split="train", subset="lite", cache_dir=os.environ["W"] + "/hf_cache")
        print(f"lite {task} {tier} train: {len(ds)} samples in {time.time() - t:.0f} s", flush=True)
PY
  echo "whole lite subset on disk: $(du -sh "$W/hf_cache" | cut -f1); shards: $(find "$W/hf_cache" -name '*.h5' | wc -l)"
fi

step "published baseline predictions from the Hub: aux/results/runs_full/$BASELINE/predictions/$PRED_TAG"
uv run python - <<PY
import os
from huggingface_hub import snapshot_download
p = snapshot_download("Xirro/AmpScape", repo_type="dataset", local_dir=os.environ["W"] + "/pred",
                      allow_patterns=[f"aux/results/runs_full/$BASELINE/predictions/$PRED_TAG/predictions.h5",
                                      f"aux/results/runs_full/$BASELINE/predictions/$PRED_TAG/meta.json"])
root = snapshot_download("Xirro/AmpScape", repo_type="dataset", cache_dir=os.environ["W"] + "/hf_cache",
                         allow_patterns=["data/$TIER/T1/*", "index/$TIER.parquet", "splits/*", "stats/*"])
open(os.environ["W"] + "/root.txt", "w").write(root)
print("predictions at", p, "; data root", root)
PY
ROOT=$(cat "$W/root.txt")
du -sh "$W/pred" "$ROOT/data/$TIER/T1" 2>/dev/null

step "scripts/evaluate.py at $TAG"
/usr/bin/time -f "evaluate %e s" uv run python scripts/evaluate.py --predictions "$W/pred/aux/results/runs_full/$BASELINE/predictions/$PRED_TAG" \
    --split "$SPLIT" --root "$ROOT" --tier "$TIER" --out "$W/eval" --workers 8 2>&1 | tail -n 8

step "compare with docs/tables/baselines_full.md (origin/main) at the printed precision"
uv run python - <<PY
import json, re
r = json.load(open("$W/eval/results.json"))
agg = r["per_task"]["T1"]
row = [l for l in open("$W/baselines_full_main.md") if "| $BASELINE |" in l and "| $SPLIT |" in l]
if not row:
    print("FAIL: no row for $BASELINE $SPLIT in baselines_full.md"); raise SystemExit(1)
cells = [c.strip() for c in row[0].strip().strip("|").split("|")]
hdr = [l for l in open("$W/baselines_full_main.md") if l.startswith("| task |")][0]
cols = [c.strip() for c in hdr.strip().strip("|").split("|")]
tab = dict(zip(cols, cells))
m = {"mae_log10eps": "mae_log10eps", "rel_l2": "rel_l2", "top5_iou": "top5_iou", "pinch_recall": "pinch_recall",
     "spearman": "spearman", "corridor_dice": "corridor_dice_q10", "ssim": "ssim"}
bad = 0
print(f"n rows: harness {r['n_rows']} vs table {tab['n']}")
bad += r["n_rows"] != int(tab["n"])
for col, key in m.items():
    v = agg[key]["mean"] if isinstance(agg.get(key), dict) else agg.get(key)
    s = f"{v:.3f}" if v is not None else "–"
    ok = s == tab[col]
    bad += not ok
    print(f"  {col:14s} harness {s}  table {tab[col]}  {'ok' if ok else 'MISMATCH'}")
sp = agg.get("speedup", {}).get("speedup_median") if isinstance(agg.get("speedup"), dict) else None
if sp is not None:
    ok = f"{sp:.3f}" == tab["speed-up (median)"]
    bad += not ok
    print(f"  speed-up med.  harness {sp:.3f}  table {tab['speed-up (median)']}  {'ok' if ok else 'MISMATCH (hardware-dependent: inference time is recorded in the predictions, so it should match)'}")
print("RESULT:", "PASS" if not bad else f"FAIL ({bad} mismatches)")
PY
step "done"
