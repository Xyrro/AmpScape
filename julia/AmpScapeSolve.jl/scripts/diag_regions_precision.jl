# Owner question (2026-09-21, incident (h)): can the `regions` problems on which CHOLMOD raises PosDefException be
# solved to the reference precision (relative residual 1e-9) and at what cost? For every region pair of one sample
# this script builds the same reduced system as `refine_voltage!` (grounded region removed, source region collapsed
# to one node) and tries: (a) plain CHOLMOD, (b) CHOLMOD on the Jacobi-scaled system D A D, (c) CHOLMOD LDLᵀ,
# (d) AMG-preconditioned CG to 1e-6 / 1e-9 / 1e-10 / 1e-12. Prints residual, time and memory per pair and method.
#   julia --project=julia/AmpScapeSolve.jl julia/AmpScapeSolve.jl/scripts/diag_regions_precision.jl <inputs.h5> <sample_id> [config]
using AmpScapeSolve, HDF5, LinearAlgebra, SparseArrays, AlgebraicMultigrid, Printf, Statistics

inputs, sid = ARGS[1], ARGS[2]
cname = length(ARGS) >= 3 ? ARGS[3] : "regions"
R, nodata, focal = h5open(inputs, "r") do f
    g = f["samples"][sid]
    (AmpScapeSolve.h5_hw(g["inputs"], "resistance"),
     AmpScapeSolve.h5_hw(g["inputs"], "nodata_mask") .> 0,
     Int32.(AmpScapeSolve.h5_hw(g["configs"][cname], "focal_mask")))
end
labels = sort(unique(vec(focal[focal .> 0])))
println("sample $sid $cname: $(size(R)) contrast $(maximum(R[.!nodata]) / minimum(R[.!nodata])) labels $labels pixels/label $([count(focal .== l) for l in labels])")
t0 = time(); L, idx = graph_laplacian(R, nodata); println(@sprintf("laplacian: n=%d nnz=%d in %.1f s", size(L, 1), nnz(L), time() - t0))
valid = idx .> 0; n = size(L, 1); ids = vec(idx[valid])

"""reduced system for pair (i grounded, 1 A into region j collapsed to one node); returns Af, bf"""
function reduced(i, j)
    gnd = falses(n); gnd[ids] .= vec((focal .== i)[valid])
    reg = falses(n); reg[ids] .= vec((focal .== j)[valid])
    b = zeros(n); b[findfirst(reg)] = 1.0
    rep = findfirst(reg); col = collect(1:n); col[reg] .= rep
    keep = .!reg; keep[rep] = true
    newid = zeros(Int, n); newid[keep] .= 1:count(keep)
    P = sparse(1:n, newid[col], ones(n), n, count(keep))
    A = P' * L * P; bc = P' * b; gc = falses(count(keep)); gc[newid[keep]] .= gnd[keep]
    free = .!gc
    return A[free, free], bc[free]
end
rss() = round(Sys.maxrss() / 2^20; digits = 0)
resid(Af, x, bf) = norm(bf .- Af * x) / norm(bf)

function try_direct(name, Af, bf, factor, unscale)
    t = @elapsed r = try
        F = factor(Af)
        x = unscale(F, bf)
        (true, resid(Af, x, bf), "")
    catch err
        (false, NaN, first(sprint(showerror, err), 80))
    end
    ok, res, msg = r
    println(@sprintf("    %-22s %s residual %.2e  %.1f s  maxrss %d MB %s", name, ok ? "OK  " : "FAIL", res, t, rss(), msg))
    return ok, res, t
end

summary = Dict{String,Vector{Float64}}()
for a in 1:length(labels), bidx in (a + 1):length(labels)
    i, j = labels[a], labels[bidx]
    Af, bf = reduced(i, j)
    println(@sprintf("pair (%d,%d): free nodes %d", i, j, size(Af, 1)))
    ok, res, t = try_direct("cholmod", Af, bf, cholesky, (F, b) -> F \ b)
    push!(get!(summary, "cholmod", Float64[]), ok ? res : NaN)
    d = 1 ./ sqrt.(diag(Af)); D = Diagonal(d)
    ok, res, t = try_direct("cholmod jacobi-scaled", Af, bf, A -> cholesky(Symmetric(spdiagm(d) * A * spdiagm(d))), (F, b) -> d .* (F \ (d .* b)))
    push!(get!(summary, "jacobi", Float64[]), ok ? res : NaN)
    ok, res, t = try_direct("cholmod ldlt", Af, bf, A -> ldlt(Symmetric(A)), (F, b) -> F \ b)
    push!(get!(summary, "ldlt", Float64[]), ok ? res : NaN)
    # AMG-PCG with several targets from one run
    t = @elapsed begin
        P = aspreconditioner(ruge_stuben(Af))
    end
    println(@sprintf("    amg setup %.1f s  maxrss %d MB", t, rss()))
    targets = [1e-6, 1e-9, 1e-10, 1e-12]; ti = 1; nb = norm(bf)
    x = zeros(length(bf)); r = bf .- Af * x; z = similar(r); ldiv!(z, P, r); p = copy(z); rz = dot(r, z)
    it = 0; t0 = time(); rel = norm(r) / nb; itmax = 100_000
    while ti <= length(targets) && it < itmax
        if rel <= targets[ti]
            println(@sprintf("    pcg to %.0e: %d iters, %.1f s", targets[ti], it, time() - t0))
            push!(get!(summary, @sprintf("pcg_%.0e_iters", targets[ti]), Float64[]), it)
            push!(get!(summary, @sprintf("pcg_%.0e_s", targets[ti]), Float64[]), time() - t0)
            ti += 1; continue
        end
        Ap = Af * p; alpha = rz / dot(p, Ap); x .+= alpha .* p; r .-= alpha .* Ap
        ldiv!(z, P, r); rz2 = dot(r, z); p .= z .+ (rz2 / rz) .* p; rz = rz2; it += 1; rel = norm(r) / nb
        it % 2000 == 0 && println(@sprintf("      it %d rel %.2e", it, rel))
    end
    println(@sprintf("    pcg final: %d iters, residual %.2e (true %.2e), %.1f s, maxrss %d MB", it, rel, resid(Af, x, bf), time() - t0, rss()))
    push!(get!(summary, "pcg_final", Float64[]), resid(Af, x, bf))
    flush(stdout)
end
println("SUMMARY")
for (k, v) in sort(collect(summary))
    println(@sprintf("  %-18s n=%d  median %.3g  max %.3g  nan %d", k, length(v), (isempty(filter(!isnan, v)) ? NaN : median(filter(!isnan, v))), (isempty(filter(!isnan, v)) ? NaN : maximum(filter(!isnan, v))), count(isnan, v)))
end
