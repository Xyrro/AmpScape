# Review round 2, point 1: production Omniscape solve (per-tier radius / block, artefact correction on, CHOLMOD) timed
# with Omniscape's own parallelisation (`parallelize = true`, Julia threads) against the single-thread production
# setting, on the first landscapes of the T4 reference subsets. The production generation ran parallelize = false
# with one core per solve, so the paper's "solver seconds" are single-core numbers.
#   JULIA_NUM_THREADS=<n> julia --project=julia/AmpScapeSolve.jl scripts/review/omniscape_threads.jl <out.json> <n_M> <n_L>
using AmpScapeSolve, HDF5, JSON, Logging, Dates
const E = AmpScapeSolve
out, nM, nL = ARGS[1], parse(Int, ARGS[2]), parse(Int, ARGS[3])
nt = Threads.nthreads()
PROD = Dict("M" => (radius = 32, block = 3), "L" => (radius = 64, block = 5))
res = Any[]
for (tier, n) in (("M", nM), ("L", nL))
    shard = "aux/t4_bs1_reference/$(tier)_bs1/inputs/shard-00000.inputs.h5"
    h = h5open(shard, "r")
    sids = collect(keys(h["samples"]))[1:n]
    for sid in sids
        g = h["samples"][sid]
        R = E.h5_hw(g["inputs"], "resistance"); nd = E.h5_hw(g["inputs"], "nodata_mask") .> 0
        gc = g["configs"]["omniscape"]; gin = haskey(gc, "inputs") ? gc["inputs"] : gc   # aux inputs shards keep the inputs at the config level
        S = E.h5_hw(gin, "source_strength")
        radius = Int(attrs(g)["omni_radius"]); @assert radius == PROD[tier].radius
        block = PROD[tier].block
        workdir = mktempdir()
        project = joinpath(workdir, "omniscape_project")
        Rw = Float64.(R); Rw[nd] .= E.NODATA
        Sw = Float64.(S); Sw[nd] .= E.NODATA
        Rm = E.missingarray(Rw, Float64, E.NODATA); Sm = E.missingarray(Sw, Float64, E.NODATA)
        cfg = Dict{String,String}(
            "radius" => string(radius), "block_size" => string(block), "project_name" => project,
            "source_threshold" => "0.0", "source_from_resistance" => "false", "resistance_is_conductance" => "false",
            "r_cutoff" => "Inf", "buffer" => "0", "calc_flow_potential" => "true", "calc_normalized_current" => "true",
            "correct_artifacts" => "true", "mask_nodata" => "true", "connect_four_neighbors_only" => "false",
            "solver" => "cholmod", "precision" => "double", "parallelize" => nt > 1 ? "true" : "false",
            "parallel_batch_size" => "20", "write_raw_currmap" => "false", "write_as_tif" => "false",
            "suppress_cs_messages" => "true")
        GC.gc()
        t = @elapsed r = with_logger(NullLogger()) do
            E.run_omniscape(cfg, Rm; source_strength = Sm, write_outputs = false)
        end
        rm(project; recursive = true, force = true); rm(workdir; recursive = true, force = true)
        cum = E.clean_map(E.missingarray_to_array(r[1], E.NODATA))
        push!(res, Dict("tier" => tier, "sample_id" => sid, "threads" => nt, "parallelize" => nt > 1,
                        "radius" => radius, "block" => block, "wall_s" => t, "cum_max" => maximum(cum),
                        "cum_sum" => sum(Float64, cum), "host" => gethostname(), "at" => string(now(UTC))))
        println("$tier $sid threads=$nt wall=$(round(t; digits = 1)) s"); flush(stdout)
        open(out, "w") do io; JSON.print(io, res, 1); end
    end
    close(h)
end
println("wrote $out ($(length(res)) solves)")
