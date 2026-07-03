"""Scoring schema and helpers (no live LLM calls in CI)."""

import pytest
from pydantic import ValidationError

from cryptoacademy.news.scoring import ArticleScore, cosine


def test_schema_accepts_valid_score():
    s = ArticleScore.model_validate_json(
        '{"assets":["BTC"],"sentiment":-0.6,"confidence":0.8,'
        '"event_type":"etf_flow","severity":3,"is_price_report":false}'
    )
    assert s.event_type.value == "etf_flow"


def test_schema_rejects_out_of_range_sentiment():
    with pytest.raises(ValidationError):
        ArticleScore.model_validate_json(
            '{"assets":["BTC"],"sentiment":-2,"confidence":0.5,'
            '"event_type":"macro","severity":3,"is_price_report":false}'
        )


def test_schema_rejects_unknown_event_type():
    with pytest.raises(ValidationError):
        ArticleScore.model_validate_json(
            '{"assets":["ETH"],"sentiment":0,"confidence":0.5,'
            '"event_type":"gossip","severity":1,"is_price_report":true}'
        )


def test_cosine_bounds():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine([], []) == 0.0
