"""Every source in data/sources/manifest.json must have a licence recorded and be documented in docs/licenses.md."""

from __future__ import annotations

import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "sources" / "manifest.json"
pytestmark = pytest.mark.skipif(not MANIFEST.exists(), reason="no source manifest on this machine")

ALLOWED = ("CC BY 4.0", "CC0", "CC-BY", "Copernicus", "HydroSHEDS", "MIT")


def test_manifest_licences_and_docs():
    m = json.loads(MANIFEST.read_text())
    doc = (ROOT / "docs" / "licenses.md").read_text()
    for k, v in m.items():
        assert v.get("license"), f"{k}: no licence recorded"
        assert any(a in v["license"] for a in ALLOWED), f"{k}: licence not in the allowed set: {v['license']}"
        assert len(v.get("sha256", "")) == 64, f"{k}: no sha256"
        key = k.split("_v10_")[0] if k.startswith("hydrorivers") else k.split("_region")[0] if k.startswith("grip4") else k
        assert key in doc or k in doc, f"{k}: not documented in docs/licenses.md"
