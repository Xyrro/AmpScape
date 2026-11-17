"""Site-specific Slurm settings, read from the environment (owner 2026-11-16: no account, QoS, partition, host or
user names in the public repo).

The values are exported by the untracked `scripts/env.local.sh` (template: `scripts/env.local.sh.example`), which
`scripts/env.sh` sources. Unset values are simply left out of the sbatch arguments, so imports and tests work without
the file.
"""

from __future__ import annotations

import json
import os


def _get(name: str) -> str | None:
    return os.environ.get(name) or None


def account() -> str | None:
    return _get("AMPSCAPE_ACCOUNT")


def qos() -> str | None:
    return _get("AMPSCAPE_QOS")


def partition(kind: str = "cpu") -> str | None:
    return _get("AMPSCAPE_GPU_PARTITION" if kind == "gpu" else "AMPSCAPE_CPU_PARTITION")


def sbatch_args(
    kind: str = "cpu", qos_name: str | None = None, partition_name: str | None = None
) -> list[str]:
    """`-A <account> -q <qos> -p <partition>` for sbatch, each only when set."""
    out = []
    for flag, value in (
        ("-A", account()),
        ("-q", qos_name or qos()),
        ("-p", partition_name or partition(kind)),
    ):
        if value:
            out += [flag, value]
    return out


def gpu_pools() -> list[tuple[str, str, str]]:
    """GPU pools in priority order, [(partition, qos, gres), ...] from AMPSCAPE_GPU_POOLS (JSON)."""
    return [tuple(p) for p in json.loads(os.environ.get("AMPSCAPE_GPU_POOLS", "[]"))]


def qos_legs() -> dict[str, int]:
    """Concurrent two-hour GPU legs allowed per QoS, from AMPSCAPE_GPU_QOS_LEGS (JSON)."""
    return {k: int(v) for k, v in json.loads(os.environ.get("AMPSCAPE_GPU_QOS_LEGS", "{}")).items()}


def quota_cmd() -> list[str]:
    """Command printing a `Scratch: <used GB> <quota GB> ...` line (AMPSCAPE_QUOTA_CMD)."""
    return (_get("AMPSCAPE_QUOTA_CMD") or "quota").split()


def scratch_fs() -> str | None:
    """Mount point of the scratch file system, for `lfs quota` (AMPSCAPE_SCRATCH_FS)."""
    return _get("AMPSCAPE_SCRATCH_FS")


def user() -> str:
    return os.environ.get("USER", "")
