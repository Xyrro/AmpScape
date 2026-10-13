"""No login-node script may kill processes by name pattern.

2026-10-10/13: with the keepalive and the GPU driver running, the owner's tmux/screen attaches were SIGKILLed and the
SSH session closed. The audit found no pattern kill in the repository (the cause was the 4 GB per-user memory cgroup
OOM-killing under unreclaimed page cache; see ampscape/io/pagecache.py), but an earlier session had lost its shell to
a `pkill -f <pattern>` that matched the Bash tool's own command line (DECISIONS.md 2026-10-02). Rule, enforced here:
processes are addressed by a pid from a lease / pid file, or by an exact `python <script>` match — never by
`pkill`, `killall`, `kill -9 <pattern>`, `pgrep -f`, `killpg`, and no selector may match tmux, screen, sshd, bash or
the Claude CLI.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN_DIRS = ["scripts", "ampscape", "tests", "AmpScapeSolve.jl", ".claude", "work"]
EXTS = (".py", ".sh", ".sbatch", ".jl", ".bash")
NAMED = ("Makefile", "justfile")


def _tracked() -> list[pathlib.Path]:
    """Every tracked file plus the scan dirs (untracked helpers in work/ and .claude/ hooks included): the 2026-10-13
    audit widened the scope from scripts/ampscape/tests to the whole repository and the Claude hook scripts."""
    out: set[pathlib.Path] = set()
    try:
        ls = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        out.update(ROOT / ln for ln in ls.splitlines() if ln)
    except (OSError, subprocess.CalledProcessError):
        pass
    for d in SCAN_DIRS:
        if (ROOT / d).exists():
            out.update(p for p in (ROOT / d).rglob("*") if p.is_file())
    return sorted(
        p
        for p in out
        if (p.suffix in EXTS or p.name in NAMED)
        and "__pycache__" not in p.parts
        and ".venv" not in p.parts
        and p.name != "test_no_pattern_kills.py"
    )


FILES = _tracked()
FORBIDDEN = [
    (re.compile(r"\bpkill\b"), "pkill"),
    (re.compile(r"\bkillall\b"), "killall"),
    (re.compile(r"\bpgrep\s+-[a-zA-Z]*f"), "pgrep -f"),
    (re.compile(r"\bkill\s+-(9|KILL|s\s+KILL|SIGKILL)\b"), "kill -9"),
    (re.compile(r"\bkill\s+-f\b"), "kill -f"),
    (re.compile(r"\bkillpg\b"), "killpg"),
    (re.compile(r"\bSIGKILL\b"), "SIGKILL"),
    (re.compile(r"\bkill\s+\$\(\s*(pgrep|ps)\b"), "kill $(pgrep/ps ...)"),
    (re.compile(r"\bxargs\s+(-[^\s]+\s+)*kill\b"), "xargs kill"),
]
# a `kill` in shell is only allowed as the liveness probe `kill -0 <pid>`; in Python only `os.kill(<pid>, 0)`
SHELL_KILL = re.compile(r"(?<![\w./-])kill\s+(?!-0\b)")
PY_KILL = re.compile(r"\bos\.kill\((.*)\)")
# what a selector must never match (a `ps -eo args` listing)
INNOCENT = [
    "tmux attach -t work",
    "tmux new -d -s work",
    "screen -r main",
    "screen -S main",
    "sshd-session: yxiao413@pts/20",
    "-bash",
    "bash scripts/slurm/gpu/keepalive.sh",
    "/bin/bash -c -l eval 'python scripts/slurm/gpu/offload_runs.py --loop 600 | tail'",
    "claude",
    "node /usr/bin/claude --resume",
    "python -c import json;print(json.load(open('logs/lease_gpu_driver.json'))['pid'])",
]
OFFLOADER = "python scripts/slurm/gpu/offload_runs.py --loop 600"


def _strip_comments(text: str, path: pathlib.Path) -> str:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        out.append(line.split(" # ")[0] if path.suffix in (".sh", ".sbatch") else line)
    return "\n".join(out)


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_pattern_kill(path: pathlib.Path):
    text = _strip_comments(path.read_text(errors="replace"), path)
    for rx, what in FORBIDDEN:
        m = rx.search(text)
        assert m is None, f"{path.relative_to(ROOT)}: forbidden '{what}' at offset {m.start() if m else 0}"
    if path.suffix in (".sh", ".sbatch"):
        for m in SHELL_KILL.finditer(text):
            # allow quoted documentation like 'kill $(cat $PIDF)' only when it kills a pid file's pid
            tail = text[m.end() : m.end() + 40]
            assert tail.startswith("$(cat "), (
                f"{path.relative_to(ROOT)}: shell `kill` must be `kill -0 <pid>` or `kill $(cat <pidfile>)`: "
                f"'{text[m.start():m.end()+40]}'"
            )
    else:
        for m in PY_KILL.finditer(text):
            args = m.group(1)
            assert args.rstrip().endswith(", 0"), (
                f"{path.relative_to(ROOT)}: os.kill must be a liveness probe os.kill(pid, 0): {m.group(0)}"
            )


def test_keepalive_selectors_do_not_match_innocent_processes():
    """Run the keepalive's process selector (the awk filter over `ps -eo args`) on a synthetic listing: only the
    offloader line may match."""
    text = (ROOT / "scripts/slurm/gpu/keepalive.sh").read_text()
    awks = re.findall(r"awk '([^']*)'", text)
    assert awks, "keepalive.sh no longer selects the offloader with an awk filter — update this test"
    listing = "\n".join(["COMMAND", *INNOCENT, OFFLOADER]) + "\n"
    for prog in awks:
        r = subprocess.run(["awk", prog], input=listing, capture_output=True, text=True, check=True)
        matched = [ln for ln in r.stdout.splitlines() if ln.strip()]
        assert matched == [OFFLOADER], f"awk selector matched {matched}"
    # the driver is addressed by its lease pid (ps -p <pid>), never by a listing-wide pattern
    assert "lease_gpu_driver.json" in text and "ps -o args= -p" in text
    assert not re.search(r"ps\s+-e[^|]*\|\s*grep[^|\n]*gpu_driver", text)


def test_keepalive_evicts_page_cache():
    text = (ROOT / "scripts/slurm/gpu/keepalive.sh").read_text()
    assert "scripts/evict_cache.py" in text and "memory.current" in text
