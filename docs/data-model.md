# Model danych

Schemat hurtowni: star schema w SQLite (`db/steam_warehouse.db`).
DDL: [`backend/warehouse/schema.sql`](../backend/warehouse/schema.sql).
Widoki: [`backend/warehouse/views.sql`](../backend/warehouse/views.sql).

```
                        ┌──────────────┐
                        │  dim_date    │
                        └──────┬───────┘
                               │ review_date_key
                               │
          ┌────────────────┐   │   ┌──────────────────┐
          │  dim_genre     │◄──┤ ──►│  dim_developer   │
          └────────┬───────┘   │   └────────┬─────────┘
                   │           │            │
                   │ genre_key │            │ developer_key
                   ▼           │            ▼
              ┌────────────────┴─────────────────────┐
              │  fact_games (PK: game_id)            │
              │  price_range_key  ►  dim_price_range │
              │  release_period_key►dim_release_period│
              │  sentiment_key    ►  dim_sentiment   │
              └──────┬──────────────────┬────────────┘
                     │                  │
       game_id      ▼                  ▼  game_id
   ┌──────────────────────┐    ┌──────────────────────┐
   │  bridge_game_genre   │    │  bridge_game_platform │
   │  (game_id, genre_key)│    │  (game_id, platform_key)
   └──────────────────────┘    └──────────────────────┘
                                          │
                                          ▼
                                  ┌──────────────┐
                                  │ dim_platform │
                                  └──────────────┘

              ┌─────────────────────────────────────┐
              │  fact_reviews (PK: review_id)       │
              │  game_id        ►  fact_games       │
              │  review_date_key►  dim_date         │
              │  sentiment_label_key ► dim_sentiment│
              └─────────────────────────────────────┘
```

## Tabele wymiarów

### `dim_genre`

| Kolumna | Typ | Opis |
|---|---|---|
| `genre_key` | INTEGER PK AUTOINCREMENT | Klucz surogatowy. |
| `name` | TEXT NOT NULL UNIQUE | Nazwa gatunku z Steam/Kaggle (np. „Action"). |

Ładowany z `stg_kaggle.genres` (CSV-string) + `stg_steam_api.genres`.
`load_dimensions.load_all_dimensions` rozbija string po przecinku
i deduplikuje.

### `dim_developer`

| Kolumna | Typ | Opis |
|---|---|---|
| `developer_key` | INTEGER PK AUTOINCREMENT | Klucz surogatowy. |
| `name` | TEXT NOT NULL UNIQUE | Nazwa dewelopera (pierwszy z CSV gdy wielu). |
| `games_count` | INTEGER NOT NULL | Liczba gier tego dewelopera (precomputed). |
| `developer_class` | TEXT NOT NULL CHECK IN ('indie', 'AA', 'AAA') | Klasa wg progów na `games_count`. |

`developer_class` jest wyliczany w `load_dimensions.classify_developer`:
< 3 gier → `indie`, 3–10 → `AA`, > 10 → `AAA`. To uproszczenie — w realu
klasy zależą od budżetu, nie od liczby tytułów.

### `dim_platform`

Trzy stałe wiersze: `Windows`, `Mac`, `Linux`. Używane przez
`bridge_game_platform`.

### `dim_price_range`

Sześć stałych przedziałów cenowych z `_PRICE_RANGES`
w [`load_dimensions.py`](../backend/etl/load_dimensions.py):

| label | min_price | max_price |
|---|---:|---:|
| Free | 0.00 | 0.00 |
| $0.01-4.99 | 0.01 | 4.99 |
| $5.00-9.99 | 5.00 | 9.99 |
| $10.00-19.99 | 10.00 | 19.99 |
| $20.00-39.99 | 20.00 | 39.99 |
| $40.00+ | 40.00 | NULL |

Każda gra w `fact_games` jest przypisywana do dokładnie jednego przedziału.

### `dim_release_period`

| Kolumna | Typ | Opis |
|---|---|---|
| `release_period_key` | INTEGER PK | |
| `year` | INTEGER NOT NULL | Rok wydania. |
| `quarter` | INTEGER CHECK 1-4 | Kwartał. |
| `month` | INTEGER CHECK 1-12 | Miesiąc. |
| `month_name` | TEXT | Nazwa miesiąca (en). |
| `season` | TEXT | Pora roku (Spring/Summer/Autumn/Winter). |

UNIQUE na `(year, month)` — jeden wiersz per miesiąc kalendarzowy.
Generowany dynamicznie z dat premier występujących w danych
(`release_date_to_period` w [`parsers.py`](../backend/etl/parsers.py)).

### `dim_sentiment`

| label | score_min | score_max |
|---|---:|---:|
| Negative | -1.00 | -0.50 |
| Mostly Negative | -0.50 | -0.05 |
| Mixed | -0.05 | 0.05 |
| Positive | 0.05 | 0.50 |
| Very Positive | 0.50 | 1.00 |

Pięć koszyków z `SENTIMENT_BUCKETS` w
[`sentiment.py`](../backend/etl/sentiment.py). Granice to compound
score VADER-a. Przypisywane do `fact_games.sentiment_key` na podstawie
średniego compound z recenzji gry oraz do `fact_reviews.sentiment_label_key`
per recenzja.

### `dim_date`

Pełen wymiar kalendarzowy (year/quarter/month/day/day_of_week). Używany
przez `fact_reviews.review_date_key`. Obecnie ładowany leniwie — pusty,
jeśli zescrapowane recenzje nie mają daty.

## Tabele faktów

### `fact_games`

Główna tabela analityczna. Jeden wiersz per gra Steam (PK = appid).

| Kolumna | Typ | Opis |
|---|---|---|
| `game_id` | INTEGER PK | Steam appid (np. 70 = Half-Life). |
| `name` | TEXT NOT NULL | Nazwa gry. |
| `genre_key` | INTEGER FK | **Podstawowy** gatunek (pierwszy z CSV); pełna lista jest w bridge_game_genre. |
| `developer_key` | INTEGER FK | **Podstawowy** deweloper (pierwszy z CSV). |
| `price_range_key` | INTEGER FK | Koszyk cenowy. |
| `release_period_key` | INTEGER FK | Rok+miesiąc premiery (NULL jeśli brak/nieparsowalna data). |
| `sentiment_key` | INTEGER FK | Sentyment uśredniony z recenzji (NULL = brak recenzji). |
| `price_usd` | REAL | Cena katalogowa USD. |
| `rating_score` | REAL | 0-100, `positive / (positive + negative) * 100`. NULL jeśli brak głosów. |
| `review_count` | INTEGER | Łączna liczba recenzji (`positive + negative`). |
| `positive_review_count` | INTEGER | |
| `negative_review_count` | INTEGER | |
| `estimated_owners` | INTEGER | Midpoint przedziału z SteamSpy. NULL jeśli SteamSpy nie był fetchowany dla tego appida. |
| `estimated_revenue_usd` | REAL | `estimated_owners × price_usd`. NULL gdy brak owners. |
| `release_date` | TEXT | Surowy string z Kaggle/Steam API (np. „Nov 19, 1998"). |
| `playtime_avg_hours` | REAL | Z SteamSpy `average_forever_minutes / 60`. |

**Indeksy:** genre, developer, price_range, release_date, rating_score
(pod typowe agregacje).

### `fact_reviews`

Jeden wiersz per zescrapowana recenzja.

| Kolumna | Typ | Opis |
|---|---|---|
| `review_id` | TEXT PK | Hash MD5 z `(appid, treść)` — deterministyczny dedupe. |
| `game_id` | INTEGER NOT NULL FK | → `fact_games.game_id`. |
| `review_date_key` | INTEGER FK | → `dim_date`. |
| `sentiment_score` | REAL | VADER compound score (-1..1). |
| `sentiment_label_key` | INTEGER FK | → `dim_sentiment` (koszyk dla tej recenzji). |
| `helpful_count` | INTEGER | Liczba „helpful" z Steam Community. |
| `playtime_at_review_hours` | REAL | Godziny gry autora w momencie recenzji. |
| `voted_up` | INTEGER CHECK 0/1/NULL | Czy recenzja jest „Recommended". |

## Tabele bridge (M:N)

### `bridge_game_genre`

`(game_id, genre_key)` — gra może mieć wiele gatunków (np. Action + RPG).
PK na obu kolumnach (deduplikacja).

### `bridge_game_platform`

`(game_id, platform_key)` — gra może być na wielu platformach
(Windows/Mac/Linux).

## Widoki analityczne

Wszystkie widoki są w [`views.sql`](../backend/warehouse/views.sql).
Każdy zaczyna się od `DROP VIEW IF EXISTS` → `CREATE VIEW`, więc
`init_views()` jest idempotentny.

| Widok | Wiersze | Klucz biznesowy |
|---|---|---|
| `vw_overview` | dokładnie 1 | KPI nagłówka dashboardu. |
| `vw_top_rated_games` | gry z ≥10 recenzjami | Ranking po `rating_score DESC`, `review_count DESC`. |
| `vw_genre_stats` | 1 per gatunek | `COUNT/AVG` po `fact_games` z `GROUP BY genre`. |
| `vw_developer_leaderboard` | 1 per deweloper | `SUM(estimated_revenue_usd) NULLS LAST` z klasą. |
| `vw_price_range_distribution` | 1 per przedział cenowy | `COUNT` per koszyk + śr. ocena. |
| `vw_sentiment_per_genre` | 1 per (gatunek, sentyment) | Rozkład krzyżowy. |
| `vw_monthly_releases` | 1 per (rok, miesiąc) | Liczba premier + śr. ocena. |
| `vw_game_detail` | 1 per gra | `fact_games LEFT JOIN` wszystkich wymiarów (dla `/api/games/{id}`). |

### Pułapki

- **`vw_developer_leaderboard` z `NULLS LAST`:** deweloperzy bez SteamSpy
  enrichmentu mają `total_estimated_revenue_usd = NULL` i wpadają na koniec.
  Jeśli widać tylko 4 Valve — patrz [README → Bogatszy dashboard](../README.md#bogatszy-dashboard-opcjonalnie).
- **`vw_sentiment_per_genre` z `INNER JOIN dim_sentiment`:** gry bez
  recenzji nie pojawiają się w widoku (mają `sentiment_key = NULL`).
- **`vw_top_rated_games` próg ≥ 10 recenzji:** drobne gry z 1 pozytywną
  recenzją i ratingiem 100% NIE wchodzą do rankingu. Próg twardo
  zakodowany w SQL — żeby zmienić, edytuj `views.sql`.

## Staging tables (`stg_*`)

Tymczasowe tabele odzwierciedlające 1:1 surowe pliki (z normalizacją nazw
kolumn do `snake_case`). Tworzone przez `if_exists='replace'` w każdym
przebiegu ETL — nie polegaj na ich trwałości między uruchomieniami.

- `stg_kaggle` — 39 kolumn z `games.csv` (po fixie nagłówka — patrz
  [architecture.md](architecture.md#etl-backendetl)).
- `stg_steam_api` — wynik `appdetails` per appid.
- `stg_steamspy` — wynik SteamSpy API per appid.
- `stg_reviews` — sparsowane recenzje z HTML.

Nie używaj `stg_*` w API ani widokach — to jest „surowizna z nakładką
typów", nie warstwa wynikowa.
