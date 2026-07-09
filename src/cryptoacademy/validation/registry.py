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


def log_trial(
    phase: str,
    model: str,
    horizon: str,
    trial_config: dict[str, Any],
    metrics: dict[str, Any],
    notes: str = "",
) -> str:
    """Append one trial. Returns the trial id."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg_json = json.dumps(trial_config, sort_keys=True, default=str)
    row = {
        "trial_id": uuid.uuid4().hex[:12],
        "at_utc": datetime.now(UTC).isoformat(),
        "git": _git_rev(),
        "phase": phase,
        "model": model,
        "horizon": horizon,
        "config_hash": hashlib.sha256(cfg_json.encode()).hexdigest()[:12],
        "config": trial_config,
        "metrics": metrics,
        "notes": notes,
    }
    with open(REGISTRY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")
    return row["trial_id"]


def load_trials(phase: str | None = None, model: str | None = None) -> list[dict]:
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
            out.append(row)
    return out


def n_trials(**filters: str) -> int:
    """Trial count for DSR. Distinct configs, not raw rows (a re-run of the
    same config is not an additional selection opportunity)."""
    rows = load_trials(**filters)
    return len({r["config_hash"] for r in rows})
