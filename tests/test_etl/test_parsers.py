"""Unit tests for pure helper functions used in ETL."""
from __future__ import annotations

import math

import pytest

from backend.etl.parsers import (
    classify_developer,
    parse_owners_range,
    parse_review_date,
    price_to_range_label,
    release_date_to_period,
)

# parse_owners_range -----------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("5,000,000 .. 10,000,000", 7_500_000),
        ("0 .. 20,000", 10_000),
        ("100,000 .. 200,000", 150_000),
        ("0 .. 0", 0),
    ],
)
def test_parse_owners_range_midpoint(raw: str, expected: int) -> None:
    assert parse_owners_range(raw) == expected


@pytest.mark.parametrize("raw", ["", None, "n/a", "bogus", "abc .. def"])
def test_parse_owners_range_returns_none_on_garbage(raw) -> None:
    assert parse_owners_range(raw) is None


# price_to_range_label ---------------------------------------------------------

@pytest.mark.parametrize(
    "price,expected",
    [
        (0.0, "Free"),
        (None, "Free"),
        (0.01, "$0.01-4.99"),
        (4.99, "$0.01-4.99"),
        (5.0, "$5-14.99"),
        (14.99, "$5-14.99"),
        (15.0, "$15-29.99"),
        (29.99, "$15-29.99"),
        (30.0, "$30-59.99"),
        (59.99, "$30-59.99"),
        (60.0, "$60+"),
        (199.99, "$60+"),
    ],
)
def test_price_to_range_label(price, expected) -> None:
    assert price_to_range_label(price) == expected


def test_price_to_range_label_handles_nan() -> None:
    assert price_to_range_label(math.nan) == "Free"


def test_price_to_range_label_handles_sub_cent() -> None:
    # Sub-cent positive prices are placed in the smallest non-free bucket.
    assert price_to_range_label(0.005) == "$0.01-4.99"


# classify_developer -----------------------------------------------------------

@pytest.mark.parametrize(
    "count,expected",
    [
        (1, "indie"),
        (2, "indie"),
        (3, "AA"),
        (10, "AA"),
        (11, "AAA"),
        (100, "AAA"),
    ],
)
def test_classify_developer(count: int, expected: str) -> None:
    assert classify_developer(count) == expected


@pytest.mark.parametrize("invalid", [0, -1, -100])
def test_classify_developer_invalid_count_raises(invalid: int) -> None:
    with pytest.raises(ValueError):
        classify_developer(invalid)


# release_date_to_period -------------------------------------------------------

def test_release_date_to_period_iso() -> None:
    p = release_date_to_period("2024-03-15")
    assert p == {
        "year": 2024,
        "quarter": 1,
        "month": 3,
        "month_name": "March",
        "season": "Spring",
    }


def test_release_date_to_period_steam_format() -> None:
    p = release_date_to_period("Nov 8, 1998")
    assert p == {
        "year": 1998,
        "quarter": 4,
        "month": 11,
        "month_name": "November",
        "season": "Autumn",
    }


@pytest.mark.parametrize(
    "month,expected_season",
    [(1, "Winter"), (4, "Spring"), (7, "Summer"), (10, "Autumn"), (12, "Winter")],
)
def test_release_date_to_period_seasons(month: int, expected_season: str) -> None:
    p = release_date_to_period(f"2024-{month:02d}-15")
    assert p["season"] == expected_season


def test_release_date_to_period_returns_none_on_garbage() -> None:
    assert release_date_to_period("not a date") is None
    assert release_date_to_period(None) is None
    assert release_date_to_period("") is None


def test_release_date_to_period_reverse_steam_format() -> None:
    p = release_date_to_period("8 Nov, 1998")
    assert p == {
        "year": 1998,
        "quarter": 4,
        "month": 11,
        "month_name": "November",
        "season": "Autumn",
    }


@pytest.mark.parametrize("non_str", [42, 3.14, [], {}, True])
def test_release_date_to_period_handles_non_string(non_str) -> None:
    assert release_date_to_period(non_str) is None


# parse_review_date ------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2024-03-15", "2024-03-15"),
        ("Nov 8, 2023", "2023-11-08"),
        ("November 8, 2023", "2023-11-08"),
        ("8 Nov, 2023", "2023-11-08"),
        # Steam Community "Posted: …" prefix used by scrape_reviews
        ("Posted: March 1, 2024", "2024-03-01"),
        ("Posted: Nov 8, 2023", "2023-11-08"),
        ("Posted: January 15, 2024", "2024-01-15"),
        # tolerate whitespace
        ("  Posted:  Feb 20, 2024  ", "2024-02-20"),
    ],
)
def test_parse_review_date_accepts_known_formats(raw: str, expected: str) -> None:
    assert parse_review_date(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "   ", "not a date", "Posted:", "Posted: Nov 8"])
def test_parse_review_date_returns_none_on_unparsable(raw) -> None:
    assert parse_review_date(raw) is None


@pytest.mark.parametrize("non_str", [42, 3.14, [], {}, True])
def test_parse_review_date_handles_non_string(non_str) -> None:
    assert parse_review_date(non_str) is None
