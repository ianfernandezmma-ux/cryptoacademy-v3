"""Farside ETF flows: table parsing (all-data layout, compact-page split
header, '(x)' negative / '-' null / footer conventions) and the graceful
degradation of download_etf_flows when Cloudflare blocks the source."""

from datetime import UTC, datetime

import polars as pl

from cryptoacademy.data import macro_onchain as mo
from cryptoacademy.data.macro_onchain import _parse_farside_table

ALL_DATA_HTML = """
<html><body><table>
<tr><th>Date</th><th>IBIT</th><th>FBTC</th><th>Total</th></tr>
<tr><td>Seed</td><td>10.0</td><td>10.0</td><td>20.0</td></tr>
<tr><td>09 Jul 2026</td><td>(39.9)</td><td>0.3</td><td>(39.6)</td></tr>
<tr><td>10 Jul 2026</td><td>1,250.5</td><td>-</td><td>1,250.5</td></tr>
<tr><td>Total</td><td>1210.6</td><td>0.3</td><td>1210.9</td></tr>
<tr><td>Average</td><td>605.3</td><td>0.15</td><td>605.45</td></tr>
</table></body></html>
"""

# farside.co.uk/btc/ splits the header: 'Total' on its own row above the
# ticker row (both with a blank first cell)
COMPACT_HTML = """
<html><body><table>
<tr><td></td><td></td><td></td><td>Total</td></tr>
<tr><td></td><td>IBIT</td><td>FBTC</td><td></td></tr>
<tr><td>Fee</td><td>0.25%</td><td>0.25%</td><td></td></tr>
<tr><td>09 Jul 2026</td><td>(39.9)</td><td>0.3</td><td>(39.6)</td></tr>
<tr><td>Total</td><td>(39.9)</td><td>0.3</td><td>(39.6)</td></tr>
</table></body></html>
"""


def test_all_data_layout():
    df = _parse_farside_table(ALL_DATA_HTML)
    assert set(df["fund"].unique()) == {"IBIT", "FBTC", "Total"}
    # dates only — Seed/Total/Average footer rows skipped
    assert df["date"].n_unique() == 2
    d9 = df.filter(pl.col("date") == datetime(2026, 7, 9, tzinfo=UTC))
    assert d9.filter(pl.col("fund") == "IBIT")["flow_musd"][0] == -39.9
    d10 = df.filter(pl.col("date") == datetime(2026, 7, 10, tzinfo=UTC))
    assert d10.filter(pl.col("fund") == "IBIT")["flow_musd"][0] == 1250.5  # comma
    assert d10.filter(pl.col("fund") == "FBTC")["flow_musd"][0] is None  # '-'


def test_compact_split_header():
    df = _parse_farside_table(COMPACT_HTML)
    # per-fund columns AND the Total column must both survive the merged
    # header — matrix.py sums all funds incl. Total, the scale convention
    # of the training history
    assert set(df["fund"].unique()) == {"IBIT", "FBTC", "Total"}
    assert len(df) == 3  # one data row; Fee and footer-Total rows skipped
    assert df.filter(pl.col("fund") == "Total")["flow_musd"][0] == -39.6


# --------------------------------------------- download_etf_flows degradation


class _Resp:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


class _FakeClient:
    """Stands in for httpx.Client; serves a canned response per URL."""

    def __init__(self, responses: dict[str, _Resp]):
        self._responses = responses
        self.calls: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url: str) -> _Resp:
        self.calls.append(url)
        return self._responses.get(url, _Resp(403))


def _prior_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [datetime(2024, 1, 11, tzinfo=UTC), datetime(2024, 1, 11, tzinfo=UTC)],
            "fund": ["IBIT", "ETHA"],
            "flow_musd": [100.0, 50.0],
            "asset": ["BTC", "ETH"],
            "published_at_utc": [datetime(2024, 1, 12, 12, tzinfo=UTC)] * 2,
        }
    )


def _setup(monkeypatch, tmp_path, responses: dict[str, _Resp]) -> tuple[list[str], "pl.DataFrame"]:
    """Point RAW_DIR at tmp, seed a prior parquet, stub client/sleep/telegram."""
    monkeypatch.setattr(mo.config, "RAW_DIR", tmp_path)
    monkeypatch.setattr(mo.time, "sleep", lambda _s: None)
    alerts: list[str] = []
    from cryptoacademy.notify import telegram

    monkeypatch.setattr(telegram, "send", alerts.append)
    monkeypatch.setattr(mo.httpx, "Client", lambda **_kw: _FakeClient(responses))
    prior = _prior_frame()
    (tmp_path / "etf_flows").mkdir(parents=True)
    prior.write_parquet(tmp_path / "etf_flows" / "farside.parquet")
    return alerts, prior


def test_all_blocked_keeps_prior_and_alerts(monkeypatch, tmp_path):
    alerts, prior = _setup(monkeypatch, tmp_path, {})  # every URL -> 403
    out = mo.download_etf_flows()
    assert out.equals(prior)  # served last good data, no exception
    assert pl.read_parquet(tmp_path / "etf_flows" / "farside.parquet").equals(prior)
    assert not (tmp_path / "etf_flows" / "farside_vintages.parquet").exists()
    assert len(alerts) == 1 and "BTC, ETH" in alerts[0]


def test_fallback_page_merges_with_history(monkeypatch, tmp_path):
    # primary all-data URLs blocked; compact fallback serves recent rows
    responses = {
        mo.FARSIDE["BTC"][1]: _Resp(200, COMPACT_HTML),
        mo.FARSIDE["ETH"][1]: _Resp(200, COMPACT_HTML),
    }
    alerts, _prior = _setup(monkeypatch, tmp_path, responses)
    out = mo.download_etf_flows()
    assert alerts == []
    # fresh 2026 rows present AND 2024 history retained for both assets
    for asset in ("BTC", "ETH"):
        sub = out.filter(pl.col("asset") == asset)
        assert sub["date"].min() == datetime(2024, 1, 11, tzinfo=UTC)
        assert sub["date"].max() == datetime(2026, 7, 9, tzinfo=UTC)
    # vintages only contain the freshly observed rows, never carried-forward data
    vint = pl.read_parquet(tmp_path / "etf_flows" / "farside_vintages.parquet")
    assert vint["date"].min() == datetime(2026, 7, 9, tzinfo=UTC)


def test_no_prior_and_blocked_raises(monkeypatch, tmp_path):
    import pytest

    alerts, _prior = _setup(monkeypatch, tmp_path, {})
    (tmp_path / "etf_flows" / "farside.parquet").unlink()
    with pytest.raises(RuntimeError, match="no prior data"):
        mo.download_etf_flows()
    assert len(alerts) == 1
