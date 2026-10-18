#!/bin/bash
# GPU-hours consumed by the review round 2 jobs (names r2-*, GPU allocations only), running + completed.
sacct -u $USER -S 2026-10-17T20:00 -E now -X -P -o JobID,JobName,ElapsedRaw,AllocTRES,State | awk -F'|' '$2 ~ /^r2-/ && $4 ~ /gres\/gpu=/ {split($4,a,"gres/gpu="); split(a[2],b,","); h+=$3*b[1]/3600; n++} END {printf "r2 GPU jobs: %d, GPU-h: %.2f\n", n, h}'
