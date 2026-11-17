#!/usr/bin/env bash
# AmpScape environment bootstrap for the Slurm cluster.
#
# Usage:   source scripts/env.sh
#
# What it does:
#   * Deactivates any conda env the login shell auto-activates and strips it (and the
#     anaconda3 module) from PATH, so this project is fully isolated from it (site-specific
#     patterns: AMPSCAPE_STRIP_PATH_RE, AMPSCAPE_UNSET_VARS in scripts/env.local.sh).
#   * Points every cache / depot / environment at scratch (home quota is 30 GB).
#   * Loads the Julia module and exposes `uv` and the project virtualenv.
#   * Sources the untracked scripts/env.local.sh (site settings: Slurm account, QoS, partitions, quota command;
#     template scripts/env.local.sh.example) and defines `ampscape_sbatch` (sbatch with those settings).
#
# Nothing here is heavy; safe to source on login nodes and inside sbatch jobs.

# ---------------------------------------------------------------------------
# Locations (all under scratch)
# ---------------------------------------------------------------------------
# the working copy (this file's parent directory) unless set; site values never live in tracked files
export AMPSCAPE_SCRATCH="${AMPSCAPE_SCRATCH:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
if [ -f "$AMPSCAPE_SCRATCH/scripts/env.local.sh" ]; then
  . "$AMPSCAPE_SCRATCH/scripts/env.local.sh"
fi
export AMPSCAPE_ROOT="$AMPSCAPE_SCRATCH"                 # git repo root == scratch dir
export AMPSCAPE_DATA="$AMPSCAPE_SCRATCH/data"            # generated shards, tiles, caches
export AMPSCAPE_TOOLS="$AMPSCAPE_SCRATCH/tools"          # uv binary, misc. tools
export AMPSCAPE_JULIA_VERSION="${AMPSCAPE_JULIA_VERSION:-1.11.3}"
# AMPSCAPE_MODULES (colon-separated) overrides the default module list; set by the cluster profile via generate.py.
export AMPSCAPE_MODULES="${AMPSCAPE_MODULES-julia/$AMPSCAPE_JULIA_VERSION}"

# ---------------------------------------------------------------------------
# Isolate from other conda envs / the anaconda3 module
# ---------------------------------------------------------------------------
if command -v conda >/dev/null 2>&1; then
  # deactivate as many nested envs as exist
  while [ -n "$CONDA_DEFAULT_ENV" ] && [ "$CONDA_SHLVL" != "0" ]; do
    conda deactivate 2>/dev/null || break
  done
fi
unset CONDA_DEFAULT_ENV CONDA_PREFIX ${AMPSCAPE_UNSET_VARS:-}
if command -v module >/dev/null 2>&1; then
  module unload anaconda3 2>/dev/null || true
fi
# Strip leftover conda-env / anaconda3 entries from PATH.
PATH="$(printf '%s' "$PATH" | tr ':' '\n' \
      | grep -v -E "${AMPSCAPE_STRIP_PATH_RE:-/anaconda3/}" | paste -sd ':' -)"
export PATH

# ---------------------------------------------------------------------------
# Python (uv) — venv and caches on scratch
# ---------------------------------------------------------------------------
export UV_CACHE_DIR="$AMPSCAPE_SCRATCH/.uv_cache"
export UV_PYTHON_INSTALL_DIR="$AMPSCAPE_TOOLS/python"
export UV_PROJECT_ENVIRONMENT="$AMPSCAPE_SCRATCH/.venv"
export PIP_CACHE_DIR="$AMPSCAPE_SCRATCH/.pip_cache"
export PATH="$AMPSCAPE_TOOLS/uv/bin:$PATH"
if [ -d "$AMPSCAPE_SCRATCH/.venv/bin" ]; then
  export VIRTUAL_ENV="$AMPSCAPE_SCRATCH/.venv"
  export PATH="$VIRTUAL_ENV/bin:$PATH"
fi

# ---------------------------------------------------------------------------
# Julia — depot on scratch, module-provided binary
# ---------------------------------------------------------------------------
export JULIA_DEPOT_PATH="$AMPSCAPE_SCRATCH/julia_depot"
# Portable multi-target pkgimages: the login node (Xeon Gold 6538Y+), the standard CPU nodes (Gold 6226)
# and the large node (Xeon 6972P) otherwise each rebuild the shared compiled cache and race on its
# pidfiles (observed hang, 2026-09-05). Same string Julia's own binaries are built with.
export JULIA_CPU_TARGET="generic;sandybridge,-xsaveopt,clone_all;haswell,-rdrnd,base(1)"
export JULIA_PKG_PRECOMPILE_AUTO=0   # jobs never precompile; scripts/generate.py submit does it on the login node
export JULIA_PROJECT="$AMPSCAPE_SCRATCH/julia/AmpScapeSolve.jl"
export JULIA_PKG_USE_CLI_GIT=true
if command -v module >/dev/null 2>&1 && [ -n "$AMPSCAPE_MODULES" ]; then
  for m in ${AMPSCAPE_MODULES//:/ }; do module load "$m" 2>/dev/null || true; done
fi

# ---------------------------------------------------------------------------
# Hugging Face / misc caches on scratch
# ---------------------------------------------------------------------------
export HF_HOME="$AMPSCAPE_SCRATCH/.hf_cache"
export XDG_CACHE_HOME="$AMPSCAPE_SCRATCH/.cache"
export MPLCONFIGDIR="$AMPSCAPE_SCRATCH/.cache/matplotlib"
export NUMBA_CACHE_DIR="$AMPSCAPE_SCRATCH/.cache/numba"
export TMPDIR="${TMPDIR:-/tmp}"

# GDAL CLI conda env (optional; created by scripts/setup_gdal_env.sh)
if [ -d "$AMPSCAPE_SCRATCH/envs/gdal/bin" ]; then
  # Appended (not prepended) so the venv's rasterio/pyproj keep their own bundled GDAL/PROJ.
  # Do NOT export GDAL_DATA / PROJ_LIB here: they would shadow rasterio's PROJ database
  # (different DATABASE.LAYOUT version) and break CRS lookups in Python.
  export PATH="$PATH:$AMPSCAPE_SCRATCH/envs/gdal/bin"
fi

mkdir -p "$AMPSCAPE_DATA" "$AMPSCAPE_TOOLS" "$UV_CACHE_DIR" "$JULIA_DEPOT_PATH" "$HF_HOME" "$XDG_CACHE_HOME" 2>/dev/null

# sbatch with the site's account, QoS and CPU partition (scripts/env.local.sh); options on the command line win,
# e.g. `ampscape_sbatch -p "$AMPSCAPE_GPU_PARTITION" --gres=gpu:1 job.sbatch`. The SBATCH_* variables are set for this
# one call only, so other projects' submissions from the same shell are not affected.
ampscape_sbatch() {
  SBATCH_ACCOUNT="${AMPSCAPE_ACCOUNT:-}" SBATCH_QOS="${AMPSCAPE_QOS:-}" SBATCH_PARTITION="${AMPSCAPE_CPU_PARTITION:-}" \
    sbatch "$@"
}
