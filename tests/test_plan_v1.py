"""v1.0 planner: prefix property and determinism (ampscape.solve.plan_v1)."""
import json

from ampscape.solve.plan_v1 import TIER_SEED_BASE, plan_v1_synthetic, split_counts, stable_seed


def test_split_counts_exact_for_dev_sizes():
    assert split_counts(3000) == (1800, 240)
    assert split_counts(500) == (300, 40)
    n_syn, n_tiles = split_counts(100000)
    assert n_syn + 5 * n_tiles == 100000


def test_synthetic_stream_is_a_prefix_and_deterministic():
    a = plan_v1_synthetic("S", 12, shard_size=5)
    b = plan_v1_synthetic("S", 30, shard_size=5)
    assert [s.sample_id for s in a] == [s.sample_id for s in b[:12]]
    assert [s.seed for s in a] == [TIER_SEED_BASE["S"] + i for i in range(12)]
    assert all(json.loads(s.extra)["design"] == "v1" for s in a)
    assert [s.sample_id for s in plan_v1_synthetic("M", 5, 5)] != [s.sample_id for s in plan_v1_synthetic("S", 5, 5)]


def test_stable_seed_is_process_independent():
    assert stable_seed("S_x|generic_hm") == 205588262
    assert stable_seed("a|b") == stable_seed("a|b") and stable_seed("a|b") != stable_seed("a|c")
