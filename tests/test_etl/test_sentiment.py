"""Testy modułu sentymentu opartego na VADER."""
from __future__ import annotations

import pandas as pd
import pytest

from backend.etl.sentiment import (
    SENTIMENT_BUCKETS,
    aggregate_per_game,
    compound_to_label,
    score_review,
)


def test_score_review_returns_compound_in_range() -> None:
    s = score_review("This is a fantastic game, love it!")
    assert -1.0 <= s <= 1.0
    assert s > 0.5  # clearly positive


def test_score_review_negative() -> None:
    s = score_review("Worst game ever. Hate it.")
    assert s < -0.5


def test_score_review_neutral_for_empty() -> None:
    assert score_review("") == 0.0
    assert score_review(None) == 0.0


@pytest.mark.parametrize(
    "compound,expected",
    [
        (-0.9, "Very Negative"),
        (-0.5, "Very Negative"),
        (-0.49, "Negative"),
        (-0.2, "Negative"),
        (-0.1, "Mixed"),
        (0.0, "Mixed"),
        (0.09, "Mixed"),
        (0.1, "Positive"),
        (0.4, "Positive"),
        (0.5, "Very Positive"),
        (1.0, "Very Positive"),
    ],
)
def test_compound_to_label(compound: float, expected: str) -> None:
    assert compound_to_label(compound) == expected


def test_sentiment_buckets_cover_full_range() -> None:
    # The 5 buckets must tile [-1, 1] without gaps.
    sorted_buckets = sorted(SENTIMENT_BUCKETS, key=lambda b: b["score_min"])
    assert sorted_buckets[0]["score_min"] == -1.0
    assert sorted_buckets[-1]["score_max"] == 1.0
    for prev, nxt in zip(sorted_buckets, sorted_buckets[1:], strict=False):
        assert prev["score_max"] == nxt["score_min"]


def test_aggregate_per_game_returns_one_row_per_game() -> None:
    df = pd.DataFrame(
        [
            {"appid": 70, "review_text": "Love this!"},
            {"appid": 70, "review_text": "Great fun."},
            {"appid": 220, "review_text": "Awful pacing, hated it."},
        ]
    )
    result = aggregate_per_game(df)
    assert set(result.columns) >= {"appid", "avg_compound", "sentiment_label"}
    assert sorted(result["appid"].tolist()) == [70, 220]
    pos = result[result["appid"] == 70].iloc[0]
    neg = result[result["appid"] == 220].iloc[0]
    assert pos["avg_compound"] > 0.1
    assert neg["avg_compound"] < -0.1
    assert pos["sentiment_label"] in {"Positive", "Very Positive"}
    assert neg["sentiment_label"] in {"Negative", "Very Negative"}


def test_aggregate_per_game_handles_empty_input() -> None:
    df = pd.DataFrame(columns=["appid", "review_text"])
    result = aggregate_per_game(df)
    assert len(result) == 0
    assert set(result.columns) >= {"appid", "avg_compound", "sentiment_label"}
