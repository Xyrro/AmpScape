"""Every script under scripts/ must be a non-empty, parseable Python file (or a syntactically valid shell script).

2026-09-25: `scripts/transfer_eval.py` was truncated to 0 bytes by a failed write at the scratch quota and committed
empty; the transfer jobs then ran nothing for two hours. This test fails the build on an empty or unparseable script.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sorted((ROOT / "scripts").rglob("*.py"))
SH = sorted(list((ROOT / "scripts").rglob("*.sh")) + list((ROOT / "scripts").rglob("*.sbatch")))


@pytest.mark.parametrize("path", PY, ids=lambda p: str(p.relative_to(ROOT)))
def test_python_script_parses(path: pathlib.Path):
    text = path.read_text()
    assert text.strip(), f"{path} is empty"
    tree = ast.parse(text, filename=str(path))
    assert tree.body, f"{path} has no statements"
    if "__pycache__" in path.parts:
        return
    # an entry-point script defines a main() or has top-level code beyond imports
    kinds = {type(n).__name__ for n in tree.body}
    assert kinds - {"Import", "ImportFrom", "Expr"}, f"{path} contains only imports/docstrings"


@pytest.mark.parametrize("path", SH, ids=lambda p: str(p.relative_to(ROOT)))
def test_shell_script_syntax(path: pathlib.Path):
    assert path.read_text().strip(), f"{path} is empty"
    r = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
