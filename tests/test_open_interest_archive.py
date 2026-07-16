"""OI archive writer safety: atomic writes and corrupt-archive quarantine.

Regression for the 2026-07-12 crash that left both OI archives truncated
(no PAR1 footer) and broke the hourly archiver for four days.
"""

from datetime import UTC, datetime

import polars as pl
import pytest

from cryptoacademy.data.open_interest import _atomic_write_parquet, _load_archive


@pytest.fixture
def df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "open_interest": [1.0, 2.0],
            "open_interest_usd": [100.0, 200.0],
            "time": [
                datetime(2026, 7, 1, tzinfo=UTC),
                datetime(2026, 7, 1, 1, tzinfo=UTC),
            ],
            "fetched_at_utc": [datetime(2026, 7, 2, tzinfo=UTC)] * 2,
        }
    )


def test_atomic_write_roundtrip_and_no_tmp_left(tmp_path, df):
    path = tmp_path / "oi.parquet"
    _atomic_write_parquet(df, path)
    assert pl.read_parquet(path).equals(df)
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_write_replaces_existing(tmp_path, df):
    path = tmp_path / "oi.parquet"
    _atomic_write_parquet(df.head(1), path)
    _atomic_write_parquet(df, path)
    assert len(pl.read_parquet(path)) == 2


def test_load_archive_missing_returns_none(tmp_path):
    assert _load_archive(tmp_path / "nope.parquet") is None


def test_load_archive_reads_good_file(tmp_path, df):
    path = tmp_path / "oi.parquet"
    _atomic_write_parquet(df, path)
    assert _load_archive(path).equals(df)


def test_load_archive_quarantines_truncated_file(tmp_path, df):
    path = tmp_path / "oi.parquet"
    _atomic_write_parquet(df, path)
    # Simulate the 2026-07-12 crash: tail zeroed, PAR1 footer gone.
    raw = path.read_bytes()
    path.write_bytes(raw[:-16] + b"\x00" * 16)

    assert _load_archive(path) is None
    assert not path.exists()
    quarantined = list(tmp_path.glob("oi.parquet.corrupt-*"))
    assert len(quarantined) == 1
    assert quarantined[0].read_bytes()[-4:] == b"\x00" * 4
