"""Testy parsera HTML recenzji Steam."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
import responses

from backend.ingestion import scrape_reviews as scraper_mod
from backend.ingestion.scrape_reviews import (
    REVIEWS_URL_TEMPLATE,
    Review,
    ReviewScrapingError,
    parse_reviews_html,
    scrape_many,
    scrape_reviews,
)


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


@responses.activate
def test_scrape_reviews_returns_parsed(sample_reviews_html: str) -> None:
    responses.add(
        responses.GET,
        REVIEWS_URL_TEMPLATE.format(appid=70),
        body=sample_reviews_html,
        status=200,
        content_type="text/html",
    )
    reviews = scrape_reviews(appid=70)
    assert len(reviews) == 3
    assert reviews[0].author == "ExampleUser"


@responses.activate
def test_scrape_reviews_raises_on_http_error() -> None:
    responses.add(
        responses.GET,
        REVIEWS_URL_TEMPLATE.format(appid=70),
        body="Forbidden",
        status=403,
    )
    with pytest.raises(ReviewScrapingError):
        scrape_reviews(appid=70)


@responses.activate
def test_scrape_many_writes_and_skips(
    tmp_path: Path, sample_reviews_html: str
) -> None:
    responses.add(
        responses.GET,
        REVIEWS_URL_TEMPLATE.format(appid=70),
        body=sample_reviews_html, status=200,
    )
    (tmp_path / "71_reviews.json").write_text("[]", encoding="utf-8")

    with patch.object(scraper_mod, "time") as mock_time:
        mock_time.sleep = lambda *_: None
        statuses = scrape_many([70, 71], target_dir=tmp_path, rate_limit_seconds=0)

    assert statuses == {70: "fetched", 71: "skipped"}
    data = json.loads((tmp_path / "70_reviews.json").read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 3
    assert data[0]["author"] == "ExampleUser"
    assert data[0]["appid"] == 70


@responses.activate
def test_scrape_many_records_error(tmp_path: Path) -> None:
    responses.add(
        responses.GET,
        REVIEWS_URL_TEMPLATE.format(appid=70),
        body=requests.ConnectionError("boom"),
    )
    with patch.object(scraper_mod, "time") as mock_time:
        mock_time.sleep = lambda *_: None
        statuses = scrape_many([70], target_dir=tmp_path, rate_limit_seconds=0)
    assert statuses == {70: "error"}
    assert not (tmp_path / "70_reviews.json").exists()


@responses.activate
def test_scrape_many_handles_disk_write_error(
    tmp_path: Path, sample_reviews_html: str
) -> None:
    responses.add(
        responses.GET,
        REVIEWS_URL_TEMPLATE.format(appid=70),
        body=sample_reviews_html,
        status=200,
    )

    with patch.object(scraper_mod, "time") as mock_time, \
         patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
        mock_time.sleep = lambda *_: None
        statuses = scrape_many([70], target_dir=tmp_path, rate_limit_seconds=0)

    assert statuses == {70: "error"}
