"""Append-only trial registry. EVERY tested configuration is one row — model
sweeps, factor candidates, threshold choices. The row count is N_trials, a
required input of the Deflated Sharpe Ratio: undercounting trials is how v2
fooled itself, so writing here is not optional.

JSONL on purpose: append-only by construction, human-auditable, diff-able.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from datetime import UTC, datetime
from typing import Any

from cryptoacademy import config

REGISTRY_PATH = config.DATA_DIR / "trials" / "trials.jsonl"


def _git_rev() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=config.PROJECT_ROOT, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _canonical(obj: Any) -> Any:
    """JSON-safe, deterministic representation (numpy scalars, sets)."""
    import numpy as np

    if isinstance(obj, dict):
        return {str(k): _canonical(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (list, tuple)):
        return [_canonical(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(_canonical(v) for v in obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _identity_hash(phase: str, model: str, horizon: str, trial_config: dict) -> str:
    """The FULL selection identity. Hashing only trial_config would collapse
    distinct model/horizon trials into one and undercount N for DSR (the v2
    failure mode this module exists to prevent)."""
    payload = json.dumps(
        {"phase": phase, "model": model, "horizon": horizon,
         "config": _canonical(trial_config)},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def register_trial(
    phase: str, model: str, horizon: str, trial_config: dict[str, Any], notes: str = ""
) -> str:
    """Register INTENT before evaluating. Even a crashed trial then counts —
    the conservative direction for DSR."""
    return _append(phase, model, horizon, trial_config, metrics=None, notes=notes)


def log_trial(
    phase: str,
    model: str,
    horizon: str,
    trial_config: dict[str, Any],
    metrics: dict[str, Any] | None,
    notes: str = "",
) -> str:
    """Append one completed trial. Returns the trial id."""
    return _append(phase, model, horizon, trial_config, metrics, notes)


def _append(
    phase: str, model: str, horizon: str, trial_config: dict[str, Any],
    metrics: dict[str, Any] | None, notes: str,
) -> str:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "trial_id": uuid.uuid4().hex[:12],
        "at_utc": datetime.now(UTC).isoformat(),
        "git": _git_rev(),
        "phase": phase,
        "model": model,
        "horizon": horizon,
        "config_hash": _identity_hash(phase, model, horizon, trial_config),
        "config": _canonical(trial_config),
        "metrics": _canonical(metrics) if metrics is not None else None,
        "notes": notes,
    }
    with open(REGISTRY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")
    return row["trial_id"]


def load_trials(
    phase: str | None = None, model: str | None = None, horizon: str | None = None
) -> list[dict]:
    if not REGISTRY_PATH.exists():
        return []
    out = []
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if phase and row["phase"] != phase:
                continue
            if model and row["model"] != model:
                continue
            if horizon and row["horizon"] != horizon:
                continue
            out.append(row)
    return out


def n_trials(**filters: str) -> int:
    """Trial count for DSR: distinct selection identities (re-runs of the
    same identity add no selection opportunity; crashed registrations count)."""
    rows = load_trials(**filters)
    return len({r["config_hash"] for r in rows})
