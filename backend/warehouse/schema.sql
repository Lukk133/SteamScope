-- Star schema for Steam analytics warehouse.
-- All tables use IF NOT EXISTS so init_schema() is idempotent.

-- ============================================================
-- DIMENSIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_genre (
    genre_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_developer (
    developer_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    games_count     INTEGER NOT NULL,
    developer_class TEXT NOT NULL CHECK (developer_class IN ('indie', 'AA', 'AAA'))
);

CREATE TABLE IF NOT EXISTS dim_platform (
    platform_key INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_price_range (
    price_range_key INTEGER PRIMARY KEY AUTOINCREMENT,
    label           TEXT NOT NULL UNIQUE,
    min_price       REAL NOT NULL,
    max_price       REAL
);

CREATE TABLE IF NOT EXISTS dim_release_period (
    release_period_key INTEGER PRIMARY KEY AUTOINCREMENT,
    year       INTEGER NOT NULL,
    quarter    INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month      INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name TEXT NOT NULL,
    season     TEXT NOT NULL,
    UNIQUE (year, month)
);

CREATE TABLE IF NOT EXISTS dim_sentiment (
    sentiment_key INTEGER PRIMARY KEY AUTOINCREMENT,
    label         TEXT NOT NULL UNIQUE,
    score_min     REAL NOT NULL,
    score_max     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key    INTEGER PRIMARY KEY,
    date        TEXT NOT NULL UNIQUE,
    year        INTEGER NOT NULL,
    quarter     INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month       INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    day         INTEGER NOT NULL CHECK (day BETWEEN 1 AND 31),
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6)
);

-- ============================================================
-- FACTS
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_games (
    game_id                INTEGER PRIMARY KEY,
    name                   TEXT NOT NULL,
    genre_key              INTEGER REFERENCES dim_genre(genre_key),
    developer_key          INTEGER REFERENCES dim_developer(developer_key),
    price_range_key        INTEGER REFERENCES dim_price_range(price_range_key),
    release_period_key     INTEGER REFERENCES dim_release_period(release_period_key),
    sentiment_key          INTEGER REFERENCES dim_sentiment(sentiment_key),
    price_usd              REAL,
    rating_score           REAL,
    review_count           INTEGER,
    positive_review_count  INTEGER,
    negative_review_count  INTEGER,
    estimated_owners       INTEGER,
    estimated_revenue_usd  REAL,
    release_date           TEXT,
    playtime_avg_hours     REAL
);

CREATE TABLE IF NOT EXISTS fact_reviews (
    review_id                 TEXT PRIMARY KEY,
    game_id                   INTEGER NOT NULL REFERENCES fact_games(game_id),
    review_date_key           INTEGER REFERENCES dim_date(date_key),
    sentiment_score           REAL,
    sentiment_label_key       INTEGER REFERENCES dim_sentiment(sentiment_key),
    helpful_count             INTEGER,
    playtime_at_review_hours  REAL,
    voted_up                  INTEGER CHECK (voted_up IN (0, 1) OR voted_up IS NULL)
);

-- ============================================================
-- BRIDGES
-- ============================================================

CREATE TABLE IF NOT EXISTS bridge_game_genre (
    game_id   INTEGER NOT NULL REFERENCES fact_games(game_id),
    genre_key INTEGER NOT NULL REFERENCES dim_genre(genre_key),
    PRIMARY KEY (game_id, genre_key)
);

CREATE TABLE IF NOT EXISTS bridge_game_platform (
    game_id      INTEGER NOT NULL REFERENCES fact_games(game_id),
    platform_key INTEGER NOT NULL REFERENCES dim_platform(platform_key),
    PRIMARY KEY (game_id, platform_key)
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS ix_fact_games_genre        ON fact_games(genre_key);
CREATE INDEX IF NOT EXISTS ix_fact_games_developer    ON fact_games(developer_key);
CREATE INDEX IF NOT EXISTS ix_fact_games_price_range  ON fact_games(price_range_key);
CREATE INDEX IF NOT EXISTS ix_fact_games_release_date ON fact_games(release_date);
CREATE INDEX IF NOT EXISTS ix_fact_games_rating       ON fact_games(rating_score);
CREATE INDEX IF NOT EXISTS ix_fact_reviews_game       ON fact_reviews(game_id);
