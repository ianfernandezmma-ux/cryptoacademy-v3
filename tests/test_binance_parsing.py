"""Binance data quirks: header rows, ms vs us timestamps, dedup, gap detection."""

import io
import zipfile
from datetime import UTC, datetime

import polars as pl

from cryptoacademy.data.binance_vision import (
    KLINE_COLS,
    _kline_df,
    _read_zip_csv,
    gap_report,
)

ROW_MS = (
    "1577836800000,7195.24,7196.25,7178.64,7179.78,555.9,"
    "1577840399999,3994924.1,4400,266.4,1913864.6,0"
)
ROW_US = (
    "1735689600000000,93500.0,93800.0,93200.0,93600.0,1000.0,"
    "1735693199999999,93500000.0,50000,500.0,46750000.0,0"
)
HEADER = ",".join(KLINE_COLS)


def _zip_bytes(csv_text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.csv", csv_text)
    return buf.getvalue()


def test_header_row_is_skipped():
    df = _read_zip_csv(_zip_bytes(HEADER + "\n" + ROW_MS), KLINE_COLS)
    assert len(df) == 1


def test_no_header_is_fine():
    df = _read_zip_csv(_zip_bytes(ROW_MS), KLINE_COLS)
    assert len(df) == 1


def test_microsecond_timestamps_normalized_to_same_scale():
    df = _read_zip_csv(_zip_bytes(ROW_MS + "\n" + ROW_US), KLINE_COLS)
    out = _kline_df(df)
    times = out["open_time"].to_list()
    assert times[0] == datetime(2020, 1, 1, 0, 0, tzinfo=UTC)
    assert times[1] == datetime(2025, 1, 1, 0, 0, tzinfo=UTC)


def test_duplicate_bars_deduped():
    df = _read_zip_csv(_zip_bytes(ROW_MS + "\n" + ROW_MS), KLINE_COLS)
    assert len(_kline_df(df)) == 1


def test_gap_report_flags_missing_bars():
    df = pl.DataFrame(
        {
            "open_time": [
                datetime(2026, 1, 1, h, 0, tzinfo=UTC) for h in (0, 1, 2, 5)
            ]
        }
    )
    gaps = gap_report(df, interval_minutes=60)
    assert len(gaps) == 1
    assert gaps["gap_minutes"][0] == 180
