# First-pair voltage for T1 `points` landscapes (solver-acceleration track, 2026-10-05).
# For each landscape: ground = lowest focal label, source = second label (one pixel, unit current) — the same pair
# scripts/warm_start_eval.jl uses — solved in Circuitscape advanced mode with CHOLMOD. Output: /<sid>/points/voltage
# (H,W) float32 (h5py layout) + attrs src_label, gnd_label, solver, error. Landscapes whose second label is not a
# single pixel are skipped (the warm-start metric needs point sources).
# julia --project=. scripts/pair1_voltage.jl <shard.h5> <out.h5>
using HDF5, JSON
using AmpScapeSolve
const E = AmpScapeSolve
src, out = ARGS[1], ARGS[2]
fs = h5open(src, "r")
root = haskey(fs, "samples") ? fs["samples"] : fs
tmp = out * ".part"
fo = h5open(tmp, "w")
n = 0; skipped = 0
for sid in keys(root)
    g = root[sid]
    haskey(g, "configs") && haskey(g["configs"], "points") || continue
    R = E.h5_hw(g["inputs"], "resistance"); nd = E.h5_hw(g["inputs"], "nodata_mask") .> 0
    focal = Int32.(E.h5_hw(g["configs"]["points"]["inputs"], "focal_mask"))
    labels = sort(unique(focal[focal .> 0]))
    if length(labels) < 2; global skipped += 1; continue; end
    i, j = labels[1], labels[2]
    src_m = focal .== j; gnd = focal .== i
    if count(src_m) != 1; global skipped += 1; continue; end
    S = zeros(Float64, size(R)); S[src_m] .= 1.0
    wd = mktempdir()
    res = E.solve_advanced(R, nd, S, gnd; solver = "cholmod", workdir = wd)
    rm(wd; force = true, recursive = true)
    v = getfield(res, 2); st = getfield(res, 3)
    go = create_group(fo, sid); gp = create_group(go, "points")
    gp["voltage", chunk = size(v), compress = 4] = permutedims(Float32.(v))
    attrs(gp)["src_label"] = Int(j); attrs(gp)["gnd_label"] = Int(i)
    attrs(gp)["solver"] = string(st.solver); attrs(gp)["error"] = string(st.error)
    global n += 1
end
close(fo); close(fs)
mv(tmp, out; force = true)
println(JSON.json(Dict("out" => out, "solved" => n, "skipped" => skipped)))
