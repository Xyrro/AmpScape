# Diagnose why Circuitscape's CHOLMOD path fails on a `regions` (T1R) problem that the CG+AMG fallback solves
# (generation log incident (h), 2026-09-21). Runs the same pairwise call as AmpScapeSolve.solve_pairwise with the
# reference solver only and prints the exception type, message and backtrace instead of swallowing it.
#   julia --project=julia/AmpScapeSolve.jl julia/AmpScapeSolve.jl/scripts/diag_regions_cholmod.jl <inputs.h5> <sample_id> [config]
using AmpScapeSolve, HDF5, Circuitscape, Logging

inputs, sid = ARGS[1], ARGS[2]
cname = length(ARGS) >= 3 ? ARGS[3] : "regions"
R, nodata, focal = h5open(inputs, "r") do f
    g = f["samples"][sid]
    R = AmpScapeSolve.h5_hw(g["inputs"], "resistance")
    nd = AmpScapeSolve.h5_hw(g["inputs"], "nodata_mask") .> 0
    fm = Int32.(AmpScapeSolve.h5_hw(g["configs"][cname], "focal_mask"))
    (R, nd, fm)
end
labels = sort(unique(vec(focal[focal .> 0])))
println("sample $sid config $cname: size $(size(R)) nodata $(round(sum(nodata)/length(nodata); digits=3)) labels $(labels) pixels/label $([sum(focal .== l) for l in labels])")
workdir = mktempdir()
Rw = Float64.(R); Rw[nodata] .= AmpScapeSolve.NODATA
AmpScapeSolve.write_asc(joinpath(workdir, "habitat.asc"), Rw)
AmpScapeSolve.write_asc(joinpath(workdir, "points.asc"), Int.(focal); nodata = 0)
for sol in ("cholmod", "cg+amg")
    cfg = AmpScapeSolve.cs_base_config(; solver = sol, four_neighbors = false)
    cfg["scenario"] = "pairwise"
    cfg["habitat_file"] = joinpath(workdir, "habitat.asc")
    cfg["point_file"] = joinpath(workdir, "points.asc")
    cfg["output_file"] = joinpath(workdir, "out_$(sol).out")
    cfg["write_cur_maps"] = "True"; cfg["write_volt_maps"] = "True"; cfg["write_cum_cur_map_only"] = "False"; cfg["write_max_cur_maps"] = "False"
    GC.gc(); rss0 = Sys.maxrss() / 2^20
    println("== solver $sol: start (maxrss $(round(rss0; digits=0)) MB)")
    t = @elapsed try
        r = Circuitscape.compute(cfg)   # full logging on purpose
        println("== solver $sol: OK, result type $(typeof(r))")
    catch err
        println("== solver $sol: FAILED with $(typeof(err)): ", sprint(showerror, err))
        Base.show_backtrace(stdout, catch_backtrace()); println()
    end
    println("== solver $sol: $(round(t; digits=1)) s, maxrss $(round(Sys.maxrss() / 2^20; digits=0)) MB")
    sol == "cholmod" && length(ARGS) >= 4 && ARGS[4] == "cholmod-only" && break
end
