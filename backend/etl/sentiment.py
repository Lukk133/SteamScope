"""Analiza sentymentu recenzji oparta na VADER (rule-based).

VADER zwraca `compound` score w [-1, 1]. Mapujemy na 5 etykiet:
    Very Negative ≤ -0.5 < Negative < -0.1 ≤ Mixed < 0.1 ≤ Positive < 0.5 ≤ Very Positive
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

SENTIMENT_BUCKETS: list[dict] = [
    {"label": "Very Negative", "score_min": -1.0, "score_max": -0.5},
    {"label": "Negative",      "score_min": -0.5, "score_max": -0.1},
    {"label": "Mixed",         "score_min": -0.1, "score_max":  0.1},
    {"label": "Positive",      "score_min":  0.1, "score_max":  0.5},
    {"label": "Very Positive", "score_min":  0.5, "score_max":  1.0},
]


@lru_cache(maxsize=1)
def _analyzer() -> SentimentIntensityAnalyzer:
    return SentimentIntensityAnalyzer()


def score_review(text: str | None) -> float:
    """Zwraca VADER `compound` score dla pojedynczej recenzji. None/"" → 0.0."""
    if not text:
        return 0.0
    return float(_analyzer().polarity_scores(text)["compound"])


def compound_to_label(compound: float) -> str:
    """Mapuje compound score (∈[-1,1]) na etykietę z 5-bucketów.

    Granice skrajne: -0.5 → "Very Negative", 1.0 → "Very Positive".
    """
    # Krawędzie skrajne
    if compound <= -0.5:
        return "Very Negative"
    if compound >= 0.5:
        return "Very Positive"
    for bucket in SENTIMENT_BUCKETS[1:-1]:  # Negative, Mixed, Positive
        if bucket["score_min"] <= compound < bucket["score_max"]:
            return bucket["label"]
    return "Mixed"


def aggregate_per_game(reviews_df: pd.DataFrame) -> pd.DataFrame:
    """Agreguje sentyment do poziomu gry.

    Wejście: DataFrame z kolumnami `appid`, `review_text`.
    Wyjście: DataFrame z `appid`, `avg_compound`, `sentiment_label`.
    """
    if reviews_df.empty:
        return pd.DataFrame(columns=["appid", "avg_compound", "sentiment_label"])

    scored = reviews_df.copy()
    scored["compound"] = scored["review_text"].apply(score_review)
    agg = (
        scored.groupby("appid", as_index=False)["compound"]
        .mean()
        .rename(columns={"compound": "avg_compound"})
    )
    agg["sentiment_label"] = agg["avg_compound"].apply(compound_to_label)
    return agg
