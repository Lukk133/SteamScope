"""Testy warstwy staging — raw pliki → stg_* tabele w SQLite."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.etl.staging import (
    stage_kaggle,
    stage_reviews,
    stage_steam_api,
    stage_steamspy,
)
from backend.warehouse.connection import connect

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    yield c
    c.close()


def test_stage_kaggle_writes_rows(conn) -> None:
    rows = stage_kaggle(FIXTURES / "etl_sample_kaggle.csv", conn)
    assert rows == 5
    df = pd.read_sql("SELECT * FROM stg_kaggle", conn)
    assert len(df) == 5
    assert {"appid", "name", "price", "release_date"}.issubset(df.columns)


def test_stage_kaggle_normalizes_appid_to_int(conn) -> None:
    stage_kaggle(FIXTURES / "etl_sample_kaggle.csv", conn)
    df = pd.read_sql("SELECT appid FROM stg_kaggle", conn)
    assert df["appid"].dtype.kind == "i"  # integer kind


def test_stage_kaggle_handles_boolean_columns(conn) -> None:
    stage_kaggle(FIXTURES / "etl_sample_kaggle.csv", conn)
    df = pd.read_sql("SELECT windows, mac, linux FROM stg_kaggle WHERE appid = 70", conn)
    assert int(df["windows"].iloc[0]) == 1
    assert int(df["mac"].iloc[0]) == 1
    assert int(df["linux"].iloc[0]) == 1


def test_stage_steam_api_skips_missing_marker(conn) -> None:
    rows = stage_steam_api(FIXTURES / "etl_sample_steam_api", conn)
    assert rows == 2  # 99999.json has _missing marker — skipped
    df = pd.read_sql("SELECT appid, name FROM stg_steam_api ORDER BY appid", conn)
    assert df["appid"].tolist() == [70, 220]
    assert df["name"].tolist() == ["Half-Life", "Half-Life 2"]


def test_stage_steam_api_extracts_nested_fields(conn) -> None:
    stage_steam_api(FIXTURES / "etl_sample_steam_api", conn)
    df = pd.read_sql(
        "SELECT appid, price_usd, windows, mac, linux, release_date, genres FROM stg_steam_api WHERE appid = 70",
        conn,
    )
    assert df["price_usd"].iloc[0] == pytest.approx(9.99)
    assert int(df["windows"].iloc[0]) == 1
    assert df["release_date"].iloc[0] == "Nov 8, 1998"
    assert "Action" in df["genres"].iloc[0]


def test_stage_steamspy_parses_owners_midpoint(conn) -> None:
    rows = stage_steamspy(FIXTURES / "etl_sample_steamspy", conn)
    assert rows == 2
    df = pd.read_sql(
        "SELECT appid, estimated_owners FROM stg_steamspy ORDER BY appid", conn
    )
    assert df["appid"].tolist() == [70, 220]
    assert df["estimated_owners"].tolist() == [7_500_000, 15_000_000]


def test_stage_reviews_flattens_to_rows(conn) -> None:
    rows = stage_reviews(FIXTURES / "etl_sample_reviews", conn)
    assert rows == 4  # 2 per file
    df = pd.read_sql("SELECT appid, author, voted_up FROM stg_reviews ORDER BY appid, author", conn)
    assert len(df) == 4
    assert df["appid"].tolist() == [70, 70, 220, 220]
    assert int(df.loc[df["author"] == "User1", "voted_up"].iloc[0]) == 1


def test_stage_reviews_handles_empty_dir(conn, tmp_path) -> None:
    rows = stage_reviews(tmp_path / "empty", conn)
    assert rows == 0
    df = pd.read_sql("SELECT * FROM stg_reviews", conn)
    assert len(df) == 0


def test_stage_steam_api_skips_malformed_json(tmp_path: Path, conn) -> None:
    source = tmp_path / "steam_api"
    source.mkdir()
    (source / "70.json").write_text(
        '{"steam_appid": 70, "name": "OK", "is_free": false}', encoding="utf-8"
    )
    (source / "bad.json").write_text("not json {{{", encoding="utf-8")
    rows = stage_steam_api(source, conn)
    assert rows == 1
    df = pd.read_sql("SELECT appid FROM stg_steam_api", conn)
    assert df["appid"].tolist() == [70]


def test_stage_kaggle_replace_idempotent(conn) -> None:
    rows1 = stage_kaggle(FIXTURES / "etl_sample_kaggle.csv", conn)
    rows2 = stage_kaggle(FIXTURES / "etl_sample_kaggle.csv", conn)
    assert rows1 == rows2 == 5
    df = pd.read_sql("SELECT COUNT(*) AS c FROM stg_kaggle", conn)
    assert df["c"].iloc[0] == 5  # NOT 10


def test_stage_reviews_skips_review_without_appid(tmp_path: Path, conn) -> None:
    source = tmp_path / "reviews"
    source.mkdir()
    (source / "abc_reviews.json").write_text(
        '[{"author": "X", "voted_up": true, "review_text": "no appid"}]',
        encoding="utf-8",
    )
    # File stem 'abc' is not a digit → no fallback appid → review is skipped.
    rows = stage_reviews(source, conn)
    assert rows == 0


def test_stage_kaggle_missing_csv_creates_empty_table(tmp_path: Path, conn) -> None:
    rows = stage_kaggle(tmp_path / "nope.csv", conn)
    assert rows == 0
    df = pd.read_sql("SELECT * FROM stg_kaggle", conn)
    assert len(df) == 0
    assert {"appid", "genres", "developers", "release_date"}.issubset(df.columns)


def test_stage_steam_api_missing_dir_creates_empty_table(tmp_path: Path, conn) -> None:
    rows = stage_steam_api(tmp_path / "nope", conn)
    assert rows == 0
    df = pd.read_sql("SELECT * FROM stg_steam_api", conn)
    assert len(df) == 0
    assert {"appid", "genres", "release_date"}.issubset(df.columns)


def test_stage_steamspy_missing_dir_creates_empty_table(tmp_path: Path, conn) -> None:
    rows = stage_steamspy(tmp_path / "nope", conn)
    assert rows == 0
    df = pd.read_sql("SELECT * FROM stg_steamspy", conn)
    assert len(df) == 0
    assert {"appid", "estimated_owners", "positive", "negative"}.issubset(df.columns)
