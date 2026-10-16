"""The whole-run offload must not ship transfer-leg predictions (XL/XXL tags) of an L run: those files may still be
growing while the leg runs (2026-10-16 verification finding: partial predictions.h5 on the Hub)."""

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("offload_runs", ROOT / "scripts" / "slurm" / "gpu" / "offload_runs.py")
offload_runs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offload_runs)


def test_run_includes_only_in_tier_predictions(tmp_path):
    run = tmp_path / "gnn_T1_L_s3_t2"
    for tag in ("hfcache_L_test_id", "hfcache_L_test_ood", "hfcache_XL_test_id", "hfcache_XXL_test_id"):
        (run / "predictions" / tag).mkdir(parents=True)
    inc = offload_runs.run_includes(run, "L")
    assert "predictions" not in inc
    assert "predictions/hfcache_L_test_id" in inc and "predictions/hfcache_L_test_ood" in inc
    assert not any("XL" in x for x in inc)
    for name in ("results.json", "config.json", "best.pt", "eval_t4_reference", "eval_accel_test_id"):
        assert name in inc


def test_run_includes_without_predictions_dir(tmp_path):
    run = tmp_path / "unet_T4_S_s1"
    run.mkdir()
    inc = offload_runs.run_includes(run, "S")
    assert "predictions" not in inc and "results.json" in inc
