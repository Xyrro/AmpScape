#!/bin/bash
#SBATCH -A coc
#SBATCH -q coc-ice
#SBATCH -p coc-cpu
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 2
#SBATCH --mem=12G
#SBATCH -t 02:00:00
#SBATCH -o logs/accel/pair1_%A_%a.out
# First-pair voltages for T1 shards (array over shard numbers). TIER and SHARDS (comma list) via --export.
#   sbatch --array=0-N scripts/slurm/accel/pair1_voltage.sbatch   with TIER=S,SHARDS=... exported
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"; source scripts/env.sh
IFS=',' read -r -a arr <<< "$SHARDS"; sh=${arr[$SLURM_ARRAY_TASK_ID]}
out=aux/t1_pair1/$TIER/shard-$(printf %05d $sh).h5
[ -f "$out" ] && { echo "exists $out"; exit 0; }
mkdir -p "$(dirname "$out")" "$TMPDIR/pair1"
src=$(python -c "from huggingface_hub import hf_hub_download;print(hf_hub_download('Xirro/AmpScape','data/$TIER/T1/shard-$(printf %05d $sh).h5',repo_type='dataset',cache_dir='$TMPDIR/pair1'))")
echo "start=$(date -u +%FT%TZ) tier=$TIER shard=$sh src=$src"
julia --project=julia/AmpScapeSolve.jl julia/AmpScapeSolve.jl/scripts/pair1_voltage.jl "$src" "$out"
echo "end=$(date -u +%FT%TZ) rc=$?"
