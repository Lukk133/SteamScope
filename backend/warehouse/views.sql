-- Warstwa wynikowa: analityczne widoki nad schematem gwiazdy.
-- Wszystkie widoki używają IF NOT EXISTS, dzięki czemu init_views() jest idempotentne.

-- Ranking gier po ocenie, ograniczony do tytułów z minimum 10 recenzjami.
CREATE VIEW IF NOT EXISTS vw_top_rated_games AS
SELECT
    f.game_id,
    f.name,
    g.name           AS genre,
    d.name           AS developer,
    f.price_usd,
    f.rating_score,
    f.review_count,
    f.estimated_owners
FROM fact_games f
LEFT JOIN dim_genre     g ON f.genre_key     = g.genre_key
LEFT JOIN dim_developer d ON f.developer_key = d.developer_key
WHERE f.review_count >= 10
  AND f.rating_score IS NOT NULL
ORDER BY f.rating_score DESC, f.review_count DESC;

-- Statystyki zagregowane per gatunek (liczba gier, średnia ocen i ceny, suma recenzji).
CREATE VIEW IF NOT EXISTS vw_genre_stats AS
SELECT
    g.name                       AS genre,
    COUNT(f.game_id)             AS games_count,
    AVG(f.rating_score)          AS avg_rating,
    AVG(f.price_usd)             AS avg_price_usd,
    AVG(f.estimated_owners)      AS avg_estimated_owners,
    SUM(f.review_count)          AS total_review_count
FROM fact_games f
JOIN dim_genre g ON f.genre_key = g.genre_key
GROUP BY g.name
ORDER BY games_count DESC;

-- Liderzy wśród deweloperów po szacowanym przychodzie (klasa z dim_developer).
CREATE VIEW IF NOT EXISTS vw_developer_leaderboard AS
SELECT
    d.name                              AS developer,
    d.developer_class                   AS developer_class,
    COUNT(f.game_id)                    AS games_count,
    AVG(f.rating_score)                 AS avg_rating,
    SUM(f.estimated_revenue_usd)        AS total_estimated_revenue_usd,
    SUM(f.estimated_owners)             AS total_estimated_owners
FROM fact_games f
JOIN dim_developer d ON f.developer_key = d.developer_key
GROUP BY d.name, d.developer_class
ORDER BY total_estimated_revenue_usd DESC NULLS LAST;

-- Rozkład liczby gier w przedziałach cenowych.
CREATE VIEW IF NOT EXISTS vw_price_range_distribution AS
SELECT
    pr.label             AS price_range_label,
    pr.min_price,
    pr.max_price,
    COUNT(f.game_id)     AS games_count,
    AVG(f.rating_score)  AS avg_rating
FROM fact_games f
JOIN dim_price_range pr ON f.price_range_key = pr.price_range_key
GROUP BY pr.price_range_key, pr.label, pr.min_price, pr.max_price
ORDER BY pr.min_price ASC;

-- Rozkład sentymentu (z fact_games.sentiment_key) per gatunek.
CREATE VIEW IF NOT EXISTS vw_sentiment_per_genre AS
SELECT
    g.name               AS genre,
    s.label              AS sentiment_label,
    COUNT(f.game_id)     AS games_count
FROM fact_games f
JOIN dim_genre     g ON f.genre_key     = g.genre_key
JOIN dim_sentiment s ON f.sentiment_key = s.sentiment_key
GROUP BY g.name, s.label
ORDER BY g.name ASC, games_count DESC;

-- Liczba premier per rok/miesiąc wraz ze średnią oceną.
CREATE VIEW IF NOT EXISTS vw_monthly_releases AS
SELECT
    rp.year,
    rp.month,
    rp.month_name,
    rp.season,
    COUNT(f.game_id)     AS games_count,
    AVG(f.rating_score)  AS avg_rating
FROM fact_games f
JOIN dim_release_period rp ON f.release_period_key = rp.release_period_key
GROUP BY rp.year, rp.month, rp.month_name, rp.season
ORDER BY rp.year ASC, rp.month ASC;
