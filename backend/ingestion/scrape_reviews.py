"""Scraper recenzji ze Steam Community.

Strategia: parsujemy stronę publiczną `steamcommunity.com/app/{appid}/reviews/`.
W tym module wprowadzamy najpierw czystą funkcję `parse_reviews_html` (Task 7),
a w Task 8 — wrapper HTTP `scrape_reviews` / `scrape_many`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class Review:
    appid: int
    author: str
    voted_up: bool
    playtime_hours: float | None
    review_text: str
    posted_date: str | None
    helpful_count: int | None = None


def _parse_float_from_hours(text: str) -> float | None:
    cleaned = "".join(c for c in text if c.isdigit() or c == ".")
    if not cleaned or cleaned == ".":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_reviews_html(html: str, appid: int) -> list[Review]:
    """Parsuje HTML strony recenzji Steam i zwraca listę obiektów Review."""
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("div.apphub_Card")
    reviews: list[Review] = []

    for card in cards:
        title_el = card.select_one(".title")
        voted_up = (
            title_el.get_text(strip=True).strip().lower() == "recommended"
            if title_el
            else False
        )

        hours_el = card.select_one(".hours")
        playtime = _parse_float_from_hours(hours_el.get_text(strip=True)) if hours_el else None

        text_el = card.select_one("div.apphub_CardTextContent")
        review_text = text_el.get_text(separator=" ", strip=True) if text_el else ""

        author_el = card.select_one("div.apphub_CardContentAuthorName a")
        author = author_el.get_text(strip=True) if author_el else "unknown"

        date_el = card.select_one("div.date_posted")
        posted_date = date_el.get_text(strip=True) if date_el else None

        reviews.append(
            Review(
                appid=appid,
                author=author,
                voted_up=voted_up,
                playtime_hours=playtime,
                review_text=review_text,
                posted_date=posted_date,
            )
        )

    return reviews
