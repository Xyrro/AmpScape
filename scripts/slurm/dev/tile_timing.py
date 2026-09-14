"""Time the extraction of one tile per tier with the decimated reader (freeze checklist c)."""
import json, pathlib, sys, time
sys.path.insert(0, "/storage/ice1/1/8/yxiao413/EcoFlowBench")
from ampscape.landscapes import real
sources = real.local_sources_from_dir("data/sources")
for tier in sys.argv[1:]:
    specs = json.loads(pathlib.Path(f"data/tiles/v1/specs/{tier}/tile_specs.json").read_text())["selected"]
    s = real.TileSpec(**specs[0])
    t0 = time.time()
    ch, grid, qc = real.extract_tile(s, sources)
    dt = time.time() - t0
    print(f"{tier} {s.tile_id} ({s.lat:.1f},{s.lon:.1f}) size={s.size} px={s.pixel_m}: {dt:.0f} s; accept={qc['accept']} unusable={qc['frac_unusable']:.2f} "
          f"dem_nan={qc['frac_dem_nan']:.3f} roads={qc['n_road_features']} rivers={qc['n_river_features']}; resampling={json.dumps({k: v.get('decimation', v.get('rule')) for k, v in qc['resampling'].items()})}", flush=True)
