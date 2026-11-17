"""Unit tests for scripts/submit_results.py (docs/submission.md): the leaderboard entry schema, seed aggregation,
entry construction from a harness results.json, the README rendering and the append-only file — on tiny synthetic
entries, without any data access."""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "submit_results", ROOT / "scripts" / "submit_results.py"
)
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)


def metrics(rel_l2=0.2, n=10, **kw):
    m = {
        "rel_l2": rel_l2,
        "mae_log10eps": 0.1,
        "top5_iou": 0.7,
        "pinch_recall": 0.8,
        "spearman": 0.95,
        "corridor_dice": 0.85,
        "ssim": 0.9,
        "speedup_median": 500.0,
        "inference_time_s_median": 0.01,
        "n": n,
    }
    m.update(kw)
    return m


def entry(**kw):
    e = {
        "submission_id": "sub-20261004-abc123",
        "timestamp": "2026-10-04T12:00:00+00:00",
        "submitter": "A. Tester",
        "model": "TinyNet",
        "task": "T1",
        "tier": "S",
        "split": "test_id",
        "metrics": metrics(),
        "metrics_std": None,
        "params_M": 1.5,
        "train_tiers": ["S"],
        "zero_shot": False,
        "seeds": {"n": 1, "values": [1]},
        "notes": "",
    }
    e.update(kw)
    return e


def harness_results(rel_l2=0.3, n=4, task="T1", seed=1, t4_rows=0):
    per_sample = [
        {
            "sample_id": f"s{i}",
            "config": "points",
            "task": task,
            "rel_l2": rel_l2,
            "mae_log10eps": 0.1,
            "top5_iou": 0.6,
            "pinch_recall": 0.5,
            "spearman": 0.9,
            "corridor_dice_q10": 0.7,
            "ssim": 0.8,
            "speedup": 100.0 + i,
            "inference_time_s": 0.01 * (i + 1),
        }
        for i in range(n)
    ]
    agg = {
        k: {"mean": per_sample[0][k], "median": per_sample[0][k], "n": n}
        for k in (
            "rel_l2",
            "mae_log10eps",
            "top5_iou",
            "pinch_recall",
            "spearman",
            "corridor_dice_q10",
            "ssim",
        )
    }
    for r in per_sample[:t4_rows]:
        r["t4_target"] = "block1_reference"
        r["rel_l2"] = 2 * rel_l2
    agg["inference_time_s"] = {"mean": 0.025, "median": 0.02, "n": n}
    agg["speedup"] = {"speedup_median": 101.5, "speedup_geomean": 101.0}
    return {
        "model": "tiny",
        "meta": {"seed": seed},
        "n_rows": n,
        "evaluated_at": "2026-10-04T00:00:00+00:00",
        "per_task": {task: agg},
        "per_sample": per_sample,
    }


META = {
    "model": "TinyNet",
    "task": "T1",
    "tier": "S",
    "split": "test_id",
    "seed": 1,
    "params_M": 1.5,
    "train_data": "S train split only",
    "train_tiers": ["S"],
    "hardware": "1x L40S",
    "inference_batch": 8,
    "code_url": "https://example.org/tinynet",
    "code_commit": "deadbeef",
    "contact": "tester@example.org",
    "notes": "unit test",
}


# ----------------------------------------------------------------------------------------------------- schema
def test_valid_entry_passes():
    assert sr.validate_entry(entry()) == []
    multi = entry(
        seeds={"n": 2, "values": [1, 2]},
        metrics_std={"rel_l2": 0.01, "mae_log10eps": None},
        t4_target=None,
        hardware="L40S",
        inference_batch=4,
    )
    assert sr.validate_entry(multi) == []


@pytest.mark.parametrize(
    "patch, needle",
    [
        ({"tier": "XXXL"}, "tier"),
        ({"split": "val"}, "split"),
        ({"task": "T9"}, "task"),
        ({"bogus": 1}, "unknown fields"),
        ({"zero_shot": True}, "zero_shot"),
        ({"tier": "XL", "zero_shot": False}, "zero_shot"),
        ({"tier": "XL", "zero_shot": True, "inference_batch": 4}, "inference_batch"),
        ({"metrics_std": {"rel_l2": 0.1}}, "metrics_std"),
        ({"seeds": {"n": 2, "values": [1, 2]}}, "metrics_std is required"),
        ({"task": "T4"}, "t4_target"),
        ({"t4_target": "block1_reference"}, "T4 only"),
        ({"train_tiers": []}, "train_tiers"),
        ({"timestamp": "yesterday"}, "ISO-8601"),
        ({"submission_id": "a b"}, "submission_id"),
    ],
)
def test_invalid_entries(patch, needle):
    errs = sr.validate_entry(entry(**patch))
    assert errs and any(needle in e for e in errs), errs


def test_metric_problems():
    e = entry()
    del e["metrics"]["ssim"]
    assert any("ssim" in x for x in sr.validate_entry(e))
    e = entry(metrics=metrics(rel_l2=None))
    assert any("rel_l2" in x for x in sr.validate_entry(e))
    e = entry(metrics=metrics(n=0))
    assert any("metrics.n" in x for x in sr.validate_entry(e))
    e = entry(metrics=metrics(top5_iou=float("nan")))
    assert any("top5_iou" in x for x in sr.validate_entry(e))
    e = entry()
    del e["submitter"]
    assert any("missing field 'submitter'" in x for x in sr.validate_entry(e))


# ----------------------------------------------------------------------------------------------------- aggregation
def test_aggregate_seeds_mean_and_sample_std():
    m, s = sr.aggregate_seeds(
        [metrics(rel_l2=0.1, n=5), metrics(rel_l2=0.3, n=5), metrics(rel_l2=0.2, n=5)]
    )
    assert m["rel_l2"] == pytest.approx(0.2)
    assert s["rel_l2"] == pytest.approx(0.1)  # ddof = 1
    assert m["n"] == 5 and s is not None and "n" not in s and "speedup_median" not in s
    m1, s1 = sr.aggregate_seeds([metrics()])
    assert s1 is None and m1["rel_l2"] == 0.2


def test_harness_metrics_and_block1_subset():
    r = harness_results(rel_l2=0.3, n=4, t4_rows=2)
    m = sr.harness_metrics(r, "T1")
    assert m["rel_l2"] == 0.3 and m["corridor_dice"] == 0.7 and m["n"] == 4
    assert m["inference_time_s_median"] == 0.02 and m["speedup_median"] == 101.5
    b = sr.harness_metrics(r, "T1", "block1_reference")
    assert b["rel_l2"] == pytest.approx(0.6) and b["n"] == 2
    assert b["inference_time_s_median"] == pytest.approx(0.015)
    with pytest.raises(ValueError):
        sr.harness_metrics(harness_results(), "T1", "block1_reference")
    with pytest.raises(ValueError):
        sr.harness_metrics(harness_results(), "T3")


def test_make_entry_single_and_seeds():
    e = sr.make_entry(harness_results(0.3), META, timestamp="2026-10-04T12:00:00+00:00")
    assert sr.validate_entry(e) == []
    assert (
        e["metrics"]["rel_l2"] == 0.3
        and e["metrics_std"] is None
        and e["seeds"] == {"n": 1, "values": [1]}
    )
    assert e["zero_shot"] is False and e["submission_id"].startswith("sub-20261004-")
    e3 = sr.make_entry(
        harness_results(0.3),
        META,
        [harness_results(0.5, seed=2), harness_results(0.4, seed=3)],
        submitter="X",
    )
    assert sr.validate_entry(e3) == []
    assert e3["seeds"] == {"n": 3, "values": [1, 2, 3]} and e3["submitter"] == "X"
    assert e3["metrics"]["rel_l2"] == pytest.approx(0.4) and e3["metrics_std"][
        "rel_l2"
    ] == pytest.approx(0.1)
    zs = sr.make_entry(
        harness_results(), {**META, "tier": "XL", "inference_batch": 1}, submission_id="zs-1"
    )
    assert zs["zero_shot"] is True and zs["submission_id"] == "zs-1"
    with pytest.raises(ValueError):
        sr.make_entry(harness_results(), {k: v for k, v in META.items() if k != "contact"})
    with pytest.raises(ValueError):  # batch 4 at XL is rejected by the schema
        sr.make_entry(harness_results(), {**META, "tier": "XL", "inference_batch": 4})


def test_parse_helpers():
    assert sr.parse_run_name("unet_T1_L_s2") == {
        "model": "unet",
        "task": "T1",
        "tier": "L",
        "seed": 2,
    }
    assert sr.parse_run_name("unet_T1_L_s1_scalenorm") is None
    assert sr.parse_run_name("unet_T1_S_s1_n1000_ep30") is None
    assert sr.parse_tag("hfcache_XL_ood_region") == ("XL", "ood_region")
    assert sr.parse_tag("published_S_test_ood_published") == ("S", "test_ood_published")
    assert sr.parse_tag("hfcache_S_train") is None


# ----------------------------------------------------------------------------------------------------- rendering
def test_render_readme_tables_sorted_by_rel_l2():
    a = entry(submission_id="a", model="Worse", metrics=metrics(rel_l2=0.5))
    b = entry(
        submission_id="b",
        model="Better",
        metrics=metrics(rel_l2=0.1),
        seeds={"n": 3, "values": [1, 2, 3]},
        metrics_std={"rel_l2": 0.02},
    )
    c = entry(
        submission_id="c", model="Other", tier="XL", zero_shot=True, metrics=metrics(rel_l2=0.9)
    )
    d = entry(
        submission_id="d",
        task="T4",
        t4_target="block1_reference",
        tier="M",
        metrics=metrics(rel_l2=0.3),
    )
    md = sr.render_readme([a, b, c, d], generated="2026-10-04")
    assert md.startswith("# AmpScape leaderboard")
    heads = [ln for ln in md.splitlines() if ln.startswith("## ")]
    assert heads == [
        "## T1 · S · test_id",
        "## T1 · XL · test_id",
        "## T4 · M · test_id · target block1_reference",
    ]
    sec = md.split("## T1 · S · test_id")[1].split("## ")[0]
    rows = [ln for ln in sec.splitlines() if ln.startswith("| ") and not ln.startswith("| #")]
    assert (
        rows[0].startswith("| 1 | Better |") and "0.100 ± 0.020" in rows[0] and "| 3 |" in rows[0]
    )
    assert rows[1].startswith("| 2 | Worse |") and "0.500 |" in rows[1]
    xl = md.split("## T1 · XL · test_id")[1].split("## ")[0]
    assert "| yes |" in xl and "`c`" in xl
    assert "4 entries" in md and "2026-10-04" in md


def test_append_entries_is_append_only_and_deduplicated(tmp_path):
    lb = tmp_path / "leaderboard"
    e1, e2 = entry(submission_id="one"), entry(submission_id="two", metrics=metrics(rel_l2=0.05))
    assert sr.append_entries([e1], lb) == (1, 0)
    assert sr.append_entries([e1, e2], lb) == (1, 1)  # 'one' already present
    lines = (lb / "results.jsonl").read_text().splitlines()
    assert [json.loads(ln)["submission_id"] for ln in lines] == ["one", "two"]
    md = (lb / "README.md").read_text()
    assert md.index("| 1 | TinyNet |") < md.index("| 2 | TinyNet |") and "2 entries" in md
    assert sr.load_entries(lb / "results.jsonl") == [e1, e2]
    bad = copy.deepcopy(e2)
    bad["submission_id"] = "three"
    bad["tier"] = "nope"
    with pytest.raises(ValueError):
        sr.append_entries([bad], lb)
    assert (
        len((lb / "results.jsonl").read_text().splitlines()) == 2
    )  # nothing written on a failed batch
