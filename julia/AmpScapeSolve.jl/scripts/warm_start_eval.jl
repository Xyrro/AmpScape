# Solver-acceleration metric: AMG-PCG iterations / wall time to a target residual from a predicted voltage map
using Printf
# versus from zero, on the exact graph of each sample (T1 first pair, T3).
# julia --project=. scripts/warm_start_eval.jl <inputs_or_final.h5> <predictions.h5> <out.json> [rtol=1e-6]
# predictions.h5: /<sample_id>/<config>/voltage  (H,W) or (P,H,W) float; only the first pair is used.
using AmpScapeSolve, HDF5, JSON
const E = AmpScapeSolve
src, preds, outjson = ARGS[1], ARGS[2], ARGS[3]
rtol = length(ARGS) >= 4 ? parse(Float64, ARGS[4]) : 1e-6
fs = h5open(src, "r"); fp = h5open(preds, "r")
root = haskey(fs, "samples") ? fs["samples"] : fs          # inputs shard or final shard
res = Any[]
for sid in keys(fp)
    haskey(root, sid) || continue
    g = root[sid]
    R = E.h5_hw(g["inputs"], "resistance"); nd = E.h5_hw(g["inputs"], "nodata_mask") .> 0
    L, idx = E.graph_laplacian(R, nd)
    for cname in keys(fp[sid])
        haskey(fp[sid][cname], "voltage") || continue
        gc = g["configs"][cname]
        gin = haskey(gc, "inputs") ? gc["inputs"] : gc
        v = read(fp[sid][cname]["voltage"])
        vmap = ndims(v) == 3 ? permutedims(v[:, :, 1]) : permutedims(v)      # h5py (P,H,W)/(H,W) -> Julia (H,W)
        if haskey(gin, "focal_mask")
            focal = Int32.(E.h5_hw(gin, "focal_mask"))
            labels = sort(unique(focal[focal .> 0])); length(labels) >= 2 || continue
            i, j = labels[1], labels[2]
            src_m = focal .== j; gnd = focal .== i
            inj = zeros(size(R)); inj[src_m] .= 1.0 / count(src_m)
            count(src_m) == 1 || continue          # point sources only (regions need the collapsed system)
        else
            inj = Float64.(E.h5_hw(gin, "source_strength")); gnd = E.h5_hw(gin, "ground") .> 0
        end
        zero = E.cg_baseline(L, idx, inj, gnd; rtol_targets = (rtol,))
        warm = E.cg_baseline(L, idx, inj, gnd; rtol_targets = (rtol,), x0 = Float64.(vmap))
        key = @sprintf("%.0e", rtol)
        push!(res, Dict("sample_id" => sid, "config" => cname, "rtol" => rtol,
                        "iters_zero" => zero["iters_to_$key"], "iters_warm" => warm["iters_to_$key"],
                        "time_zero_s" => zero["time_to_$key"], "time_warm_s" => warm["time_to_$key"],
                        "residual_start_warm" => warm["residual_start"], "converged_warm" => warm["converged_$key"],
                        "converged_zero" => zero["converged_$key"], "n_free" => zero["n_free"]))
    end
end
close(fs); close(fp)
open(outjson, "w") do io; JSON.print(io, E.sanitize_nan(res), 1); end
println("wrote ", outjson, " (", length(res), " systems)")
