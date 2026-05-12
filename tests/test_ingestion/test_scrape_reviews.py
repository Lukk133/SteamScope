"""Testy parsera HTML recenzji Steam."""
from __future__ import annotations

from backend.ingestion.scrape_reviews import Review, parse_reviews_html


def test_parses_three_reviews(sample_reviews_html: str) -> None:
    reviews = parse_reviews_html(sample_reviews_html, appid=70)
    assert len(reviews) == 3
    assert all(isinstance(r, Review) for r in reviews)
    assert all(r.appid == 70 for r in reviews)


def test_extracts_voted_up_recommended(sample_reviews_html: str) -> None:
    reviews = parse_reviews_html(sample_reviews_html, appid=70)
    assert reviews[0].voted_up is True
    assert reviews[1].voted_up is False
    assert reviews[2].voted_up is True


def test_extracts_playtime(sample_reviews_html: str) -> None:
    reviews = parse_reviews_html(sample_reviews_html, appid=70)
    assert reviews[0].playtime_hours == 123.4
    assert reviews[1].playtime_hours == 2.1
    assert reviews[2].playtime_hours is None  # not present in fixture


def test_extracts_review_text(sample_reviews_html: str) -> None:
    reviews = parse_reviews_html(sample_reviews_html, appid=70)
    assert "Great classic" in reviews[0].review_text
    assert "Didn't age well" in reviews[1].review_text
    assert reviews[2].review_text == "Short and sweet."


def test_extracts_author_when_present(sample_reviews_html: str) -> None:
    reviews = parse_reviews_html(sample_reviews_html, appid=70)
    assert reviews[0].author == "ExampleUser"
    assert reviews[1].author == "CriticalPlayer"
    assert reviews[2].author == "unknown"


def test_extracts_posted_date(sample_reviews_html: str) -> None:
    reviews = parse_reviews_html(sample_reviews_html, appid=70)
    assert reviews[0].posted_date == "Posted: January 15, 2024"
    assert reviews[1].posted_date == "Posted: March 3, 2024"
    assert reviews[2].posted_date is None


def test_handles_empty_html() -> None:
    reviews = parse_reviews_html("<html><body></body></html>", appid=70)
    assert reviews == []


def test_handles_malformed_review() -> None:
    html = '<div class="apphub_Card"></div>'
    reviews = parse_reviews_html(html, appid=70)
    assert len(reviews) == 1
    assert reviews[0].appid == 70
    assert reviews[0].voted_up is False
    assert reviews[0].review_text == ""
    assert reviews[0].author == "unknown"
