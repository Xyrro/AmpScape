"""offload_runs.reference_stale: a recomputed eval_t4_reference/ of an offloaded run must be pushed again."""

import hashlib
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("offload_runs", ROOT / "scripts/slurm/gpu/offload_runs.py")
offload_runs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offload_runs)


def _run(tmp_path, pushed_sha, offloaded=True, with_ref=True):
    run = tmp_path / "fno_T4_L_s1"
    (run / "eval_t4_reference").mkdir(parents=True)
    if with_ref:
        (run / "eval_t4_reference/results.json").write_text('{"a": 1}')
    if offloaded:
        (run / ".offloaded").write_text("{}")
    rec = {} if pushed_sha is None else {"eval_t4_reference/results.json": {"sha256": pushed_sha}}
    (run / ".hub_pushed.json").write_text(json.dumps(rec))
    return run


def test_matching_hash_is_not_stale(tmp_path):
    sha = hashlib.sha256(b'{"a": 1}').hexdigest()
    assert offload_runs.reference_stale(_run(tmp_path, sha)) is False


def test_changed_or_unpushed_reference_is_stale(tmp_path):
    assert offload_runs.reference_stale(_run(tmp_path, "0" * 64)) is True
    assert offload_runs.reference_stale(_run(tmp_path / "b", None)) is True


def test_not_offloaded_or_missing_reference_is_left_to_the_offload(tmp_path):
    assert offload_runs.reference_stale(_run(tmp_path, "0" * 64, offloaded=False)) is False
    assert offload_runs.reference_stale(_run(tmp_path / "b", "0" * 64, with_ref=False)) is False
