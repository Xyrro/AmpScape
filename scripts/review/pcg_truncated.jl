# Review round 2, point 4: cheap numerical baselines for T3 (and the first pair of T1, "T1V") — AMG-preconditioned CG
# from zero stopped after k iterations, the current map taken from the truncated voltage (Circuitscape's node
# current), scored like the learned models (rel-L2 on raw currents, MAE in log10-ε space, NoData masked).
#   julia --project=julia/AmpScapeSolve.jl scripts/review/pcg_truncated.jl <manifest.json> <out.json>
using AmpScapeSolve, HDF5, JSON, LinearAlgebra, SparseArrays, Statistics, Printf
using AlgebraicMultigrid
const E = AmpScapeSolve
const KS = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64]
const EPS = 1e-6
man = JSON.parsefile(ARGS[1]); out = ARGS[2]

function metrics(pred::AbstractMatrix, target::AbstractMatrix, mask::AbstractMatrix{Bool})
    p = Float64.(pred[mask]); t = Float64.(target[mask])
    nt = norm(t); rel = nt > 0 ? norm(p .- t) / nt : NaN
    cmax = maximum(t)
    mae = cmax > 0 ? mean(abs.(log10.(max.(p, 0.0) .+ EPS * cmax) .- log10.(max.(t, 0.0) .+ EPS * cmax))) : 0.0
    return rel, mae
end

"""PCG on the reduced system, recording the iterate after each k in KS and at rtol 1e-6; returns the snapshots."""
function pcg_snapshots(L, idx, inj, gnd; rtol = 1e-6, itmax = 20_000)
    valid = idx .> 0
    order = sortperm(vec(idx[valid]))
    free = .!(vec(gnd[valid])[order])
    b = Float64.(vec(inj[valid]))[order][free]
    Lf = L[free, free]
    nb = norm(b)
    t0 = time(); P = aspreconditioner(ruge_stuben(Lf)); t_setup = time() - t0
    x = zeros(length(b)); r = copy(b); z = similar(r); ldiv!(z, P, r); pvec = copy(z); rz = dot(r, z)
    snaps = Dict{Int,Tuple{Vector{Float64},Float64,Float64}}()   # k -> (x, cumulative solve time, residual)
    it = 0; t1 = time(); rel = norm(r) / nb; conv = nothing
    while it < itmax
        if rel <= rtol && conv === nothing
            conv = (copy(x), time() - t1, rel, it)
        end
        (it >= maximum(KS) && conv !== nothing) && break
        Ap = Lf * pvec; alpha = rz / dot(pvec, Ap)
        x .+= alpha .* pvec; r .-= alpha .* Ap
        ldiv!(z, P, r); rz2 = dot(r, z); pvec .= z .+ (rz2 / rz) .* pvec; rz = rz2
        it += 1; rel = norm(r) / nb
        it in KS && (snaps[it] = (copy(x), time() - t1, rel))
    end
    conv === nothing && (conv = (copy(x), time() - t1, rel, it))
    tovmap(xv) = (v = zeros(Float64, size(idx)); vv = zeros(length(order)); vv[free] .= xv; vv2 = similar(vv); vv2[order] .= vv; v[valid] .= vv2; v)
    return snaps, conv, t_setup, tovmap, length(b)
end

res = Any[]
for m in man
    h = h5open(m["shard"], "r")
    for sid in m["sids"]
        haskey(h, sid) || continue
        g = h[sid]
        R = E.h5_hw(g["inputs"], "resistance"); nd = E.h5_hw(g["inputs"], "nodata_mask") .> 0
        L, idx = E.graph_laplacian(R, nd)
        gc = g["configs"][m["config"]]
        if m["config"] == "advanced"
            inj = Float64.(E.h5_hw(gc["inputs"], "source_strength")); gnd = E.h5_hw(gc["inputs"], "ground") .> 0
            target = E.h5_hw(gc["outputs"], "current")
        else
            focal = Int32.(E.h5_hw(gc["inputs"], "focal_mask"))
            labels = sort(unique(focal[focal .> 0])); length(labels) >= 2 || continue
            i, j = labels[1], labels[2]
            count(focal .== j) == 1 || continue
            inj = zeros(size(R)); inj[focal .== j] .= 1.0; gnd = focal .== i
            target = nothing
        end
        snaps, conv, t_setup, tovmap, nfree = pcg_snapshots(L, idx, inj, gnd)
        mask = (idx .> 0)
        if target === nothing   # T1V: exact reference = PCG to 1e-12 on the same system
            _, ex, _, _, _ = pcg_snapshots(L, idx, inj, gnd; rtol = 1e-12, itmax = 50_000)
            target = E.node_current_map(L, idx, tovmap(ex[1]))
        end
        rec = Dict("tier" => m["tier"], "task" => m["task"], "sample_id" => sid, "n_free" => nfree,
                   "t_setup_s" => t_setup, "k" => Any[])
        for k in sort(collect(keys(snaps)))
            xk, tk, rk = snaps[k]
            C = E.node_current_map(L, idx, tovmap(xk))
            rel, mae = metrics(C, target, mask)
            push!(rec["k"], Dict("k" => k, "t_solve_s" => tk, "residual" => rk, "rel_l2" => rel, "mae_log" => mae))
        end
        C = E.node_current_map(L, idx, tovmap(conv[1]))
        rel, mae = metrics(C, target, mask)
        rec["converged_1e-6"] = Dict("iters" => conv[4], "t_solve_s" => conv[2], "residual" => conv[3], "rel_l2" => rel, "mae_log" => mae)
        push!(res, rec)
        println(m["tier"], " ", m["task"], " ", sid, " n=", nfree, " it(1e-6)=", conv[4], " rel@8=", @sprintf("%.3f", rec["k"][findfirst(d -> d["k"] == 8, rec["k"])]["rel_l2"])); flush(stdout)
    end
    close(h)
    open(out, "w") do io; JSON.print(io, E.sanitize_nan(res), 1); end
end
println("wrote $out ($(length(res)) systems)")
