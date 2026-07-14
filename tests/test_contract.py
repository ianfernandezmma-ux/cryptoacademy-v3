"""Input-schema contract: the frozen-wheel defense against silent data drift.
A renamed column, changed dtype, or vanished field in any input frame must be
a loud ContractViolation, never a silent feature corruption."""

import polars as pl
import pytest

from cryptoacademy.contract import (
    ContractViolation,
    build_contract,
    export_contract,
    load_contract,
    validate_frame,
)


@pytest.fixture()
def frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "open_time": pl.datetime_range(
                pl.datetime(2024, 1, 1), pl.datetime(2024, 1, 2), "1h", eager=True
            ),
            "close": pl.Series([100.0] * 25, dtype=pl.Float64),
            "volume": pl.Series([1.0] * 25, dtype=pl.Float64),
        }
    )


@pytest.fixture()
def contract(frame: pl.DataFrame) -> dict:
    return build_contract({"klines": frame}, generated_by="test")


def test_valid_frame_passes(frame, contract):
    validate_frame(frame, contract, "klines")  # must not raise


def test_roundtrip_through_json(tmp_path, frame, contract):
    path = export_contract(contract, tmp_path / "contract.json")
    validate_frame(frame, load_contract(path), "klines")


def test_missing_column_fails(frame, contract):
    with pytest.raises(ContractViolation, match="missing"):
        validate_frame(frame.drop("volume"), contract, "klines")


def test_renamed_column_fails(frame, contract):
    with pytest.raises(ContractViolation):
        validate_frame(frame.rename({"close": "close_px"}), contract, "klines")


def test_extra_column_fails_by_default(frame, contract):
    with pytest.raises(ContractViolation, match="unexpected"):
        validate_frame(frame.with_columns(pl.lit(1).alias("surprise")), contract, "klines")


def test_extra_column_allowed_when_opted_in(frame, contract):
    validate_frame(
        frame.with_columns(pl.lit(1).alias("surprise")),
        contract,
        "klines",
        allow_extra_columns=True,
    )


def test_dtype_change_fails(frame, contract):
    changed = frame.with_columns(pl.col("close").cast(pl.Float32))
    with pytest.raises(ContractViolation, match="dtype mismatch"):
        validate_frame(changed, contract, "klines")


def test_unknown_block_fails(frame, contract):
    with pytest.raises(ContractViolation, match="unknown contract block"):
        validate_frame(frame, contract, "funding")


def test_lazyframe_supported(frame, contract):
    validate_frame(frame.lazy(), contract, "klines")
