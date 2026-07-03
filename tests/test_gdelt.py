"""GDELT GKG line parsing: keyword filter, asset tagging, tone extraction."""

from datetime import UTC, datetime

from cryptoacademy.news.gdelt import _parse_line

FILE_TIME = datetime(2023, 5, 1, 12, 0, tzinfo=UTC)


def _gkg_line(
    text: str,
    tone: str = "-3.5,2.1,5.6,7.7,21.5,0.5,170",
    themes: str = "TAX_FNCACT;EPU_POLICY;",
) -> bytes:
    cols = [""] * 27
    cols[0] = "20230501120000-123"
    cols[1] = "20230501114500"
    cols[3] = "coindesk.com"
    cols[4] = f"https://coindesk.com/{text.replace(' ', '-')}"
    cols[7] = themes
    cols[15] = tone
    cols[23] = text.upper()
    return "\t".join(cols).encode()


def test_bitcoin_line_matched_and_tagged():
    row = _parse_line(_gkg_line("bitcoin surges past 100k"), FILE_TIME)
    assert row is not None
    assert "BTC" in row["assets"]
    assert row["tone"] == -3.5
    assert row["gkg_time"] == datetime(2023, 5, 1, 11, 45, tzinfo=UTC)
    assert row["source"] == "coindesk.com"


def test_ethereum_line_tagged_eth():
    row = _parse_line(_gkg_line("ethereum upgrade complete"), FILE_TIME)
    assert row is not None
    assert "ETH" in row["assets"]


def test_irrelevant_line_filtered():
    assert _parse_line(_gkg_line("weather forecast for madrid"), FILE_TIME) is None


def test_malformed_tone_is_nan_not_crash():
    row = _parse_line(_gkg_line("bitcoin etf approved", tone="bad,data"), FILE_TIME)
    assert row is not None
    assert row["tone"] != row["tone"]  # NaN


def test_short_line_ignored():
    assert _parse_line(b"BITCOIN\tonly-two-cols", FILE_TIME) is None
