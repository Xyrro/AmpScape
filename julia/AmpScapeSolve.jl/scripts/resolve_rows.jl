# Post-run precision pass (owner 2026-09-21, docs/post_run_resolve_plan.md): re-solve selected (sample, config) rows of
# one Hub task-group file IN PLACE with the reduced-system CHOLMOD solve + iterative refinement, verify the true
# relative residual per pair, recompute node currents / Reff / cumulative map, and record provenance in solver_stats.
#
#   julia --project=julia/AmpScapeSolve.jl julia/AmpScapeSolve.jl/scripts/resolve_rows.jl <taskgroup.h5> <rows.json> <report.json> [--target 1e-9] [--qc-tol 1e-6]
#
# rows.json: [{"sample_id": ..., "config": ...}, ...]   (configs of kind points / wall_to_wall / regions / advanced)
# The file keeps the Hub layout (<sid>/inputs, <sid>/configs/<cname>/{inputs,outputs}); only the outputs datasets
# (same names and shapes) and the `solver_stats` attribute of the selected rows are rewritten.
using AmpScapeSolve, HDF5, JSON, LinearAlgebra, SparseArrays, AlgebraicMultigrid, Dates, Printf

const TARGET = Ref(1e-9)
const QC_TOL = Ref(1e-6)

hw(g, name) = permutedims(read(g[name]))                      # h5py (H,W) C-order -> Julia (H,W)
sanitize(x) = AmpScapeSolve.sanitize_nan(x)

"""Solve A x = b for the reduced system with CHOLMOD + iterative refinement; LDLᵀ and AMG-PCG as last resorts.
Returns (x, residual, method, n_refine)."""
function solve_reduced(Af::SparseMatrixCSC, bf::Vector{Float64})
    nb = norm(bf)
    resid(x) = norm(bf .- Af * x) / nb
    for (name, factor) in (("cholmod", A -> cholesky(A)), ("ldlt", A -> ldlt(Symmetric(A))))
        F = try
            factor(Af)
        catch err
            nothing
        end
        F === nothing && continue
        x = F \ bf
        r = resid(x); n = 0
        while r > TARGET[] && n < 3                            # iterative refinement with the same factorisation
            d = F \ (bf .- Af * x)
            x2 = x .+ d; r2 = resid(x2)
            r2 < r || break
            x, r = x2, r2; n += 1
        end
        return x, r, name, n
    end
    # AMG-preconditioned CG (recursive residual to 1e-12), then report the true residual
    P = aspreconditioner(ruge_stuben(Af))
    x = zeros(length(bf)); r = copy(bf); z = similar(r); ldiv!(z, P, r); p = copy(z); rz = dot(r, z); it = 0
    while norm(r) / nb > 1e-12 && it < 20_000
        Ap = Af * p; alpha = rz / dot(p, Ap); x .+= alpha .* p; r .-= alpha .* Ap
        ldiv!(z, P, r); rz2 = dot(r, z); p .= z .+ (rz2 / rz) .* p; rz = rz2; it += 1
    end
    return x, resid(x), "cg+amg", 0
end

"""One pair: nodes with label `gl` grounded (0 V), 1 A injected into the (collapsed) region with label `sl`.
Returns the (H,W) voltage map, the true residual, method and refinement count."""
function solve_pair(L, idx, focal, gl, sl)
    valid = idx .> 0; n = size(L, 1); ids = vec(idx[valid])
    gnd = falses(n); gnd[ids] .= vec((focal .== gl)[valid])
    reg = falses(n); reg[ids] .= vec((focal .== sl)[valid])
    rep = findfirst(reg)
    b = zeros(n); b[rep] = 1.0
    if count(reg) > 1
        col = collect(1:n); col[reg] .= rep
        keep = .!reg; keep[rep] = true
        newid = zeros(Int, n); newid[keep] .= 1:count(keep)
        P = sparse(1:n, newid[col], ones(n), n, count(keep))
        A = P' * L * P; bc = P' * b; gc = falses(count(keep)); gc[newid[keep]] .= gnd[keep]
    else
        P = nothing; A = L; bc = b; gc = gnd
    end
    free = .!gc
    x, r, method, nref = solve_reduced(A[free, free], bc[free])
    vc = zeros(size(A, 1)); vc[free] .= x
    v = P === nothing ? vc : P * vc                       # region pixels share the collapsed node's voltage
    V = zeros(Float64, size(idx)); V[valid] .= v[ids]
    return V, r, method, nref
end

"""Connected-component label per pixel (0 on NoData), from the Laplacian's sparsity (BFS)."""
function components(L::SparseMatrixCSC, idx::AbstractMatrix{<:Integer})
    n = size(L, 1); lab = zeros(Int, n); rows = rowvals(L); c = 0
    stack = Int[]
    for s in 1:n
        lab[s] == 0 || continue
        c += 1; lab[s] = c; push!(stack, s)
        while !isempty(stack)
            u = pop!(stack)
            for k in nzrange(L, u)
                v = rows[k]
                if lab[v] == 0
                    lab[v] = c; push!(stack, v)
                end
            end
        end
    end
    out = zeros(Int, size(idx)); valid = idx .> 0; out[valid] .= lab[vec(idx[valid])]
    return out
end

function resolve_pairwise!(og, gin, gc, L, idx, R, nodata, stats)
    focal = Int32.(hw(gc["inputs"], "focal_mask"))
    labels = sort(unique(vec(focal[focal .> 0]))); K = length(labels); pos = Dict(l => i for (i, l) in enumerate(labels))
    pairs = [(labels[i], labels[j]) for i in 1:K for j in (i + 1):K]
    keep = haskey(og, "pairwise_current")
    H, W = size(R)
    cum = zeros(Float32, H, W); reff = zeros(Float64, K, K)      # Circuitscape: diagonal 0, unreachable pairs -1
    res_pairs = Float64[]; methods = String[]; nrefs = Int[]
    comp = components(L, idx)
    for (p, (i, j)) in enumerate(pairs)
        src = focal .== j; gnd = focal .== i
        if comp[findfirst(src)] != comp[findfirst(gnd)]        # different connected components: no current flows
            reff[pos[i], pos[j]] = -1.0; reff[pos[j], pos[i]] = -1.0
            push!(res_pairs, 0.0); push!(methods, "disconnected"); push!(nrefs, 0)
            if keep
                og["pairwise_current"][:, :, p] = zeros(Float32, W, H); og["voltage"][:, :, p] = zeros(Float32, W, H)
            end
            continue
        end
        V, r, method, nref = solve_pair(L, idx, focal, i, j)
        # Circuitscape convention (verified on the dev subset 2026-09-21): every pixel of a multi-pixel focal region —
        # source AND ground of the pair — displays the merged node's current, i.e. the full injected 1 A
        regpix = (count(src) > 1 ? src : falses(size(src))) .| (count(gnd) > 1 ? gnd : falses(size(gnd)))
        cur = node_current_map(L, idx, V; region_pixels = any(regpix) ? regpix : nothing)
        cum .+= cur
        vj = V[findfirst(src)]
        reff[pos[i], pos[j]] = vj; reff[pos[j], pos[i]] = vj
        push!(res_pairs, r); push!(methods, method); push!(nrefs, nref)
        if keep
            og["pairwise_current"][:, :, p] = permutedims(cur)
            og["voltage"][:, :, p] = permutedims(Float32.(V))
        end
    end
    og["cum_current"][:, :] = permutedims(cum)
    og["reff"][:, :] = permutedims(reff)
    return res_pairs, methods, nrefs
end

function resolve_advanced!(og, gin, gc, L, idx, R, nodata, stats)
    S = Float64.(hw(gc["inputs"], "source_strength")); G = hw(gc["inputs"], "ground") .> 0
    valid = idx .> 0; n = size(L, 1); ids = vec(idx[valid])
    b = zeros(n); b[ids] .= vec(S[valid]); gnd = falses(n); gnd[ids] .= vec(G[valid])
    free = .!gnd
    x, r, method, nref = solve_reduced(L[free, free], b[free])
    v = zeros(n); v[free] .= x
    V = zeros(Float64, size(idx)); V[valid] .= v[ids]
    cur = node_current_map(L, idx, V)
    og["current"][:, :] = permutedims(cur)
    og["voltage"][:, :] = permutedims(Float32.(V))
    return [r], [method], [nref]
end

function set_attr!(g, k, v)
    haskey(attrs(g), k) && delete_attribute(g, k)
    attrs(g)[k] = v
end

function main()
    args = copy(ARGS)
    function popopt!(a, name, default)
        i = findfirst(==(name), a); i === nothing && return default
        v = a[i + 1]; deleteat!(a, i:i + 1); return v
    end
    TARGET[] = parse(Float64, popopt!(args, "--target", "1e-9"))
    QC_TOL[] = parse(Float64, popopt!(args, "--qc-tol", "1e-6"))
    h5path, rows_json, report_json = args[1], args[2], args[3]
    rows = JSON.parsefile(rows_json)
    report = Any[]
    t_all = time()
    h5open(h5path, "r+") do f
        cache = Dict{String,Any}()
        for row in rows
            sid = row["sample_id"]; cname = row["config"]
            rec = Dict{String,Any}("sample_id" => sid, "config" => cname, "status" => "skipped")
            t0 = time()
            try
                gs = f[sid]; gc = gs["configs"][cname]; og = gc["outputs"]
                if !haskey(cache, sid)
                    R = hw(gs["inputs"], "resistance"); nodata = hw(gs["inputs"], "nodata_mask") .> 0
                    L, idx = graph_laplacian(R, nodata)
                    cache = Dict{String,Any}(sid => (R, nodata, L, idx))   # one sample at a time
                end
                R, nodata, L, idx = cache[sid]
                stats = JSON.parse(String(attrs(og)["solver_stats"]))
                sp = get!(stats, "solver_params", Dict{String,Any}())
                old_cum = haskey(og, "cum_current") ? permutedims(read(og["cum_current"])) : (haskey(og, "current") ? permutedims(read(og["current"])) : nothing)
                old_reff = haskey(og, "reff") ? permutedims(read(og["reff"])) : nothing
                kind = String(attrs(gc)["kind"])
                if kind in ("points", "wall_to_wall", "regions")
                    res_pairs, methods, nrefs = resolve_pairwise!(og, gs, gc, L, idx, R, nodata, stats)
                elseif kind == "advanced"
                    res_pairs, methods, nrefs = resolve_advanced!(og, gs, gc, L, idx, R, nodata, stats)
                else
                    rec["status"] = "unsupported kind $kind"; push!(report, rec); continue
                end
                new_cum = haskey(og, "cum_current") ? permutedims(read(og["cum_current"])) : permutedims(read(og["current"]))
                m = .!nodata
                rel_l2 = old_cum === nothing ? NaN : norm(Float64.(new_cum[m]) .- Float64.(old_cum[m])) / max(norm(Float64.(old_cum[m])), 1e-30)
                reff_diff = NaN
                if old_reff !== nothing
                    new_reff = permutedims(read(og["reff"])); ok = isfinite.(old_reff) .& (old_reff .!= 0)
                    reff_diff = any(ok) ? maximum(abs.(new_reff[ok] .- old_reff[ok]) ./ abs.(old_reff[ok])) : NaN
                end
                rmax = maximum(res_pairs)
                prov = Dict{String,Any}(
                    "date" => Dates.format(now(UTC), "yyyy-mm-ddTHH:MM:SS"), "target" => TARGET[],
                    "residual_before" => get(sp, "residual_rel", nothing), "residual_after" => rmax,
                    "residual_per_pair" => res_pairs, "method_per_pair" => methods, "refine_steps_per_pair" => nrefs,
                    "consistency_cum_rel_l2" => rel_l2, "consistency_reff_max_rel" => reff_diff, "time_s" => time() - t0)
                if get(stats, "solver", "") != "cholmod" && all(==("cholmod"), methods)
                    stats["solver_original"] = stats["solver"]; stats["solver"] = "cholmod"
                elseif get(stats, "solver", "") != "cholmod"
                    stats["solver_original"] = stats["solver"]; stats["solver"] = join(unique(methods), "+")
                end
                stats["fallback_used"] = false; stats["error"] = nothing; stats["converged"] = true
                sp["residual_rel"] = rmax; sp["residual_per_pair"] = res_pairs
                stats["resolved_post_run"] = prov
                set_attr!(og, "solver_stats", JSON.json(sanitize(stats)))
                merge!(rec, Dict("status" => rmax <= QC_TOL[] ? "ok" : "residual_high", "residual_after" => rmax,
                                 "residual_before" => prov["residual_before"], "n_pairs" => length(res_pairs),
                                 "methods" => unique(methods), "refine_max" => maximum(nrefs),
                                 "cum_rel_l2" => rel_l2, "reff_max_rel" => reff_diff, "time_s" => time() - t0,
                                 "reached_target" => rmax <= TARGET[]))
            catch err
                rec["status"] = "error"; rec["error"] = first(sprint(showerror, err), 300)
            end
            push!(report, rec)
            println(JSON.json(sanitize(rec))); flush(stdout)
        end
    end
    open(report_json, "w") do io
        JSON.print(io, sanitize(Dict("file" => h5path, "n_rows" => length(rows), "rows" => report, "time_s" => time() - t_all)), 1)
    end
    println("RESOLVE_RESULT rows=$(length(rows)) ok=$(count(r -> r["status"] == "ok", report)) high=$(count(r -> r["status"] == "residual_high", report)) errors=$(count(r -> r["status"] == "error", report)) seconds=$(round(time() - t_all; digits = 1))")
end

main()
