"""Source generation: every configuration is connected on the largest component (brief §6 / Phase 11 test list)."""
import numpy as np

from ampscape.landscapes.synthetic import sample_landscape_v1
from ampscape.sources import SourceConfig
from ampscape.sources.generators import generate_all


def test_generate_all_connected_and_deterministic():
    cfg = SourceConfig.from_yaml("configs/tasks/sources_default.yaml").for_tier("S")
    for seed in (100_000_000, 100_000_003, 100_000_011):
        ls = sample_landscape_v1(seed, (64, 64))
        a = generate_all(ls.resistance, ls.nodata_mask, cfg, seed)
        b = generate_all(ls.resistance, ls.nodata_mask, cfg, seed)
        assert set(a) >= {"points", "advanced", "omniscape"}
        for k, s in a.items():
            assert s.meta["connected"], k
            if s.focal_mask is not None:
                assert np.array_equal(s.focal_mask, b[k].focal_mask)
                assert not (s.focal_mask[ls.nodata_mask] > 0).any()
            if s.source_strength is not None:
                assert np.array_equal(s.source_strength, b[k].source_strength)
                assert s.source_strength[ls.nodata_mask].sum() == 0
        assert np.isclose(a["advanced"].source_strength.sum(), 1.0)
        assert (a["advanced"].source_strength[a["advanced"].ground > 0] == 0).all()
