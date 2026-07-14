"""Input-schema contract: the frozen wheel's defense against silent data drift.

The CryptoBot repo vendors this package as a wheel built at a tagged commit.
Its models were trained on frames with a specific shape; if an upstream API or
a fetcher patch ever changes a column name, dtype, or timezone, the frozen
feature code would silently produce plausible-but-wrong features. This module
makes that failure loud instead:

- The lab exports a versioned contract (`export_contract`) describing every
  input frame block the promoted model consumes (column names + dtypes + row
  ordering key). The contract JSON ships with the model card.
- The bot validates every fetched frame against the contract at runtime
  (`validate_frame`); a violation is a NO-OP-and-page event, same class as
  stale data.
- CI runs golden-day tests: assembled feature vectors for pinned historical
  dates must match lab-computed vectors.

Deliberately dependency-light: polars + stdlib only.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

CONTRACT_VERSION = 1


class ContractViolation(RuntimeError):
    """A fetched frame does not match the schema the frozen pipeline expects."""


def frame_signature(df: pl.DataFrame | pl.LazyFrame) -> dict[str, str]:
    """Column-name → dtype-string signature of a frame (order-preserving)."""
    schema = df.collect_schema() if isinstance(df, pl.LazyFrame) else df.schema
    return {name: str(dtype) for name, dtype in schema.items()}


def build_contract(
    blocks: dict[str, pl.DataFrame | pl.LazyFrame],
    *,
    generated_by: str,
    version: int = CONTRACT_VERSION,
) -> dict:
    """Build a contract dict from named input frames ("blocks")."""
    return {
        "contract_version": version,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "generated_by": generated_by,
        "blocks": {name: {"columns": frame_signature(df)} for name, df in blocks.items()},
    }


def export_contract(contract: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return path


def load_contract(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def contract_from_parquet_dir(
    raw_dir: Path, patterns: dict[str, str], *, generated_by: str
) -> dict:
    """Build a contract by introspecting one representative parquet per block.

    `patterns` maps block name → glob under `raw_dir` (the newest match is
    used, so the signature reflects the current live schema)."""
    blocks: dict[str, pl.DataFrame | pl.LazyFrame] = {}
    for name, pattern in patterns.items():
        files = sorted(raw_dir.glob(pattern))
        if not files:
            raise FileNotFoundError(f"contract block '{name}': no files match {pattern}")
        blocks[name] = pl.scan_parquet(files[-1])
    return build_contract(blocks, generated_by=generated_by)


def validate_frame(
    df: pl.DataFrame | pl.LazyFrame,
    contract: dict,
    block: str,
    *,
    allow_extra_columns: bool = False,
) -> None:
    """Raise ContractViolation unless `df` matches the contract for `block`.

    Checks: block known; no missing columns; no unexpected columns (unless
    allowed); exact dtype match per column. Extra columns default to a
    violation because a renamed column shows up as one missing + one extra."""
    if block not in contract.get("blocks", {}):
        raise ContractViolation(f"unknown contract block '{block}'")
    expected: dict[str, str] = contract["blocks"][block]["columns"]
    actual = frame_signature(df)

    problems: list[str] = []
    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    if missing:
        problems.append(f"missing columns: {missing}")
    if extra and not allow_extra_columns:
        problems.append(f"unexpected columns: {extra}")
    for col, dtype in expected.items():
        if col in actual and actual[col] != dtype:
            problems.append(f"dtype mismatch on '{col}': expected {dtype}, got {actual[col]}")
    if problems:
        raise ContractViolation(
            f"frame does not match contract block '{block}' "
            f"(contract v{contract.get('contract_version')}): " + "; ".join(problems)
        )
