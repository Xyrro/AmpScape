# Review round 3, point 2a: truncated AMG-PCG on the full T1 target. For every pair (i, j) of a T1 landscape (node i
# grounded, 1 A injected at node j: Circuitscape's convention) PCG runs from zero; after k iterations the pair's node
# current map is taken from the truncated voltage and the K(K-1)/2 maps are summed into a cumulative map, which is
# scored against the stored `cum_current` target (the quantity the learned T1 models predict). The AMG setup is built
# once per grounded node and shared by its pairs, as a pairwise solver would. Cost = setups + all iterations.
#   julia --project=julia/AmpScapeSolve.jl scripts/review/pcg_truncated_allpairs.jl <manifest.json> <out.json>
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

"""PCG from zero with a given preconditioner; snapshots after each k in KS and the iterate at rtol (1e-6)."""
function pcg_snapshots(Lf, P, b; rtol = 1e-6, itmax = 20_000)
    nb = norm(b)
    x = zeros(length(b)); r = copy(b); z = similar(r); ldiv!(z, P, r); pvec = copy(z); rz = dot(r, z)
    snaps = Dict{Int,Tuple{Vector{Float64},Float64}}()
    it = 0; t1 = time(); rel = norm(r) / nb; conv = nothing
    while it < itmax
        if rel <= rtol && conv === nothing
            conv = (copy(x), time() - t1, it)
        end
        (it >= maximum(KS) && conv !== nothing) && break
        Ap = Lf * pvec; alpha = rz / dot(pvec, Ap)
        x .+= alpha .* pvec; r .-= alpha .* Ap
        ldiv!(z, P, r); rz2 = dot(r, z); pvec .= z .+ (rz2 / rz) .* pvec; rz = rz2
        it += 1; rel = norm(r) / nb
        it in KS && (snaps[it] = (copy(x), time() - t1))
    end
    conv === nothing && (conv = (copy(x), time() - t1, it))
    return snaps, conv
end

res = Any[]
for m in man
    m["task"] == "T1V" || continue           # the T1 entries of the round-2 subset (config `points`)
    h = h5open(m["shard"], "r")
    for sid in m["sids"]
        haskey(h, sid) || continue
        g = h[sid]
        R = E.h5_hw(g["inputs"], "resistance"); nd = E.h5_hw(g["inputs"], "nodata_mask") .> 0
        L, idx = E.graph_laplacian(R, nd)
        gc = g["configs"]["points"]
        focal = Int32.(E.h5_hw(gc["inputs"], "focal_mask"))
        target = E.h5_hw(gc["outputs"], "cum_current")
        labels = sort(unique(focal[focal .> 0]))
        K = length(labels)
        (K >= 2 && all(count(focal .== l) == 1 for l in labels)) || continue
        valid = idx .> 0
        order = sortperm(vec(idx[valid]))
        mask = valid
        cum = Dict(k => zeros(Float64, size(R)) for k in KS)
        cum_conv = zeros(Float64, size(R))
        t_setup = 0.0; t_it = Dict(k => 0.0 for k in KS); t_conv = 0.0; its_conv = Int[]
        for (a, li) in enumerate(labels)
            gnd = focal .== li
            free = .!(vec(gnd[valid])[order])
            Lf = L[free, free]
            t0 = time(); P = aspreconditioner(ruge_stuben(Lf)); t_setup += time() - t0
            tovmap(xv) = (v = zeros(Float64, size(idx)); vv = zeros(length(order)); vv[free] .= xv; vv2 = similar(vv); vv2[order] .= vv; v[valid] .= vv2; v)
            for lj in labels[(a + 1):end]
                inj = zeros(size(R)); inj[focal .== lj] .= 1.0
                b = Float64.(vec(inj[valid]))[order][free]
                snaps, conv = pcg_snapshots(Lf, P, b)
                for k in KS
                    xk, tk = snaps[k]
                    cum[k] .+= E.node_current_map(L, idx, tovmap(xk))
                    t_it[k] += tk
                end
                cum_conv .+= E.node_current_map(L, idx, tovmap(conv[1]))
                t_conv += conv[2]; push!(its_conv, conv[3])
            end
        end
        rec = Dict("tier" => m["tier"], "task" => "T1", "sample_id" => sid, "K" => K, "n_pairs" => K * (K - 1) ÷ 2,
                   "t_setup_s" => t_setup, "k" => Any[])
        for k in KS
            rel, mae = metrics(cum[k], target, mask)
            push!(rec["k"], Dict("k" => k, "t_solve_s" => t_it[k], "rel_l2" => rel, "mae_log" => mae))
        end
        rel, mae = metrics(cum_conv, target, mask)
        rec["converged_1e-6"] = Dict("iters_mean" => mean(its_conv), "t_solve_s" => t_conv, "rel_l2" => rel, "mae_log" => mae)
        push!(res, rec)
        k2 = rec["k"][findfirst(d -> d["k"] == 2, rec["k"])]
        println(m["tier"], " ", sid, " K=", K, " rel@2=", @sprintf("%.3f", k2["rel_l2"]), " rel@conv=", @sprintf("%.2e", rel),
                " t(2)=", @sprintf("%.3f", t_setup + k2["t_solve_s"])); flush(stdout)
    end
    close(h)
    open(out, "w") do io; JSON.print(io, E.sanitize_nan(res), 1); end
end
println("wrote $out ($(length(res)) landscapes)")
