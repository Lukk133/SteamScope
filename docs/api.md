# Referencja REST API

Pełna lista endpointów z parametrami, kontraktem odpowiedzi i przykładami.
Dokumentacja interaktywna (Swagger): **http://localhost:8000/docs**
(po uruchomieniu `uvicorn backend.api.main:app`). Dla architektury patrz
[`architecture.md`](architecture.md), dla schematu hurtowni
[`data-model.md`](data-model.md).

## Konwencje

- **Baza URL** w devie: `http://localhost:8000`.
- **CORS** włączony dla `http://localhost:5173` (frontend dev). Tylko `GET`.
- **Brak autentykacji** — API read-only.
- **Format odpowiedzi:**
  - Endpointy zwracające listę: `{"items": [...], "total": <int>}`,
    gdzie `total` to liczba wierszy widoku po filtrze, przed paginacją.
  - Endpointy zwracające pojedynczy rekord: czysty obiekt lub 404.
- **Paginacja:** `limit` (1–200, domyślnie 50), `offset` (≥0, domyślnie 0).
- **Walidacja:** błędny parametr → `422 Unprocessable Entity`
  z FastAPI-owym opisem; brak rekordu w endpointach `{id}` → `404 Not Found`.
- **SQL injection:** nazwy widoków są stałymi modułowymi; dane użytkownika
  trafiają wyłącznie jako bound parameters — powierzchnia ataku nie istnieje.

## Health / metadata

### `GET /`

Metadane aplikacji.

```bash
curl http://localhost:8000/
```

```json
{"name": "SteamScope API", "docs": "/docs"}
```

### `GET /api/health`

Status zdrowia (monitoring / smoke-test).

```bash
curl http://localhost:8000/api/health
```

```json
{"status": "ok"}
```

## KPI nagłówka

### `GET /api/overview`

Jednowierszowy agregat dla kafelków KPI. Czyta `vw_overview`.

```bash
curl http://localhost:8000/api/overview
```

```json
{
  "total_games": 122611,
  "total_developers": 75469,
  "total_genres": 33,
  "avg_rating": 75.83,
  "avg_price_usd": 4.77,
  "total_estimated_owners": 120000000,
  "total_reviews": 148872261,
  "total_estimated_revenue_usd": 89550000.0
}
```

Pola `avg_*` / `total_*` mogą być `null` na pustej hurtowni.

## Gry

### `GET /api/games`

Lista/wyszukiwanie gier. Czyta `vw_game_detail`.

**Query parameters:**

| Parametr | Typ | Domyślnie | Opis |
|---|---|---|---|
| `q` | string | — | Filtr po nazwie (`LIKE '%q%'`, case-insensitive dla ASCII). |
| `limit` | int (1-200) | 50 | Max liczba zwróconych wierszy. |
| `offset` | int (≥0) | 0 | Przesunięcie paginacji. |

**Sortowanie:** `rating_score DESC, review_count DESC`.

```bash
curl "http://localhost:8000/api/games?q=portal&limit=2"
```

```json
{
  "items": [
    {
      "game_id": 400,
      "name": "Portal",
      "genre": "Action",
      "developer": "Valve",
      "developer_class": "AAA",
      "price_range_label": "$5.00-9.99",
      "release_year": 2007,
      "release_month": 10,
      "release_month_name": "October",
      "season": "Autumn",
      "sentiment_label": "Very Positive",
      "price_usd": 9.99,
      "rating_score": 98.47,
      "review_count": 177741,
      "positive_review_count": 175027,
      "negative_review_count": 2714,
      "estimated_owners": 15000000,
      "estimated_revenue_usd": 149850000.0,
      "release_date": "Oct 10, 2007",
      "playtime_avg_hours": 7.5
    }
  ],
  "total": 14
}
```

`limit=999` → 422 `value_error.number.not_le`.

### `GET /api/games/{game_id}`

Pełny rekord pojedynczej gry albo `404`.

```bash
curl http://localhost:8000/api/games/440
```

```json
{
  "game_id": 440,
  "name": "Team Fortress 2",
  "genre": "Action",
  "developer": "Valve",
  "developer_class": "AAA",
  "price_range_label": "Free",
  "release_year": 2007,
  "release_month": 10,
  "release_month_name": "October",
  "season": "Autumn",
  "sentiment_label": "Positive",
  "price_usd": 0.0,
  "rating_score": 89.91,
  "review_count": 1161472,
  "positive_review_count": 1044264,
  "negative_review_count": 117208,
  "estimated_owners": 75000000,
  "estimated_revenue_usd": 0.0,
  "release_date": "Oct 10, 2007",
  "playtime_avg_hours": 230.5
}
```

```bash
curl -i http://localhost:8000/api/games/999999999
# HTTP/1.1 404 Not Found
# {"detail":"Nie znaleziono gry"}
```

## Widoki analityczne (`/api/views/*`)

Każdy endpoint zwraca `{"items": [...], "total": <int>}` — listę wierszy
widoku i ich całkowitą liczbę. Schemat każdego widoku w
[`data-model.md`](data-model.md#widoki-analityczne).

### `GET /api/views/top-rated-games`

Ranking gier z ≥10 recenzjami. Paginowany.

| Param | Domyślnie | Zakres |
|---|---|---|
| `limit` | 50 | 1–200 |
| `offset` | 0 | ≥0 |

```bash
curl "http://localhost:8000/api/views/top-rated-games?limit=3"
```

```json
{
  "items": [
    {"game_id": 400, "name": "Portal", "genre": "Action", "developer": "Valve", "price_usd": 9.99, "rating_score": 98.47, "review_count": 177741, "estimated_owners": 15000000},
    {"game_id": 220, "name": "Half-Life 2", "genre": "Action", "developer": "Valve", "price_usd": 9.99, "rating_score": 97.60, "review_count": 245627, "estimated_owners": 15000000},
    {"game_id": 70, "name": "Half-Life", "genre": "Action", "developer": "Valve", "price_usd": 9.99, "rating_score": 96.54, "review_count": 148221, "estimated_owners": 15000000}
  ],
  "total": 4321
}
```

### `GET /api/views/genre-stats`

Statystyki per gatunek (pełna lista, niewielki zbiór).

```bash
curl http://localhost:8000/api/views/genre-stats
```

```json
{
  "items": [
    {"genre": "Indie", "games_count": 89234, "avg_rating": 76.12, "avg_price_usd": 4.21, "avg_estimated_owners": null, "total_review_count": 12348901},
    {"genre": "Action", "games_count": 32101, "avg_rating": 78.45, "avg_price_usd": 7.89, "avg_estimated_owners": null, "total_review_count": 89234567}
  ],
  "total": 33
}
```

### `GET /api/views/developer-leaderboard`

Liderzy wśród deweloperów po szacowanym przychodzie. Paginowany.

| Param | Domyślnie | Zakres |
|---|---|---|
| `limit` | 50 | 1–200 |
| `offset` | 0 | ≥0 |

```bash
curl "http://localhost:8000/api/views/developer-leaderboard?limit=2"
```

```json
{
  "items": [
    {"developer": "Game Science", "developer_class": "AA", "games_count": 3, "avg_rating": 96.5, "total_estimated_revenue_usd": 4499250000.0, "total_estimated_owners": 75000000},
    {"developer": "FromSoftware", "developer_class": "AAA", "games_count": 7, "avg_rating": 92.1, "total_estimated_revenue_usd": 1814575000.0, "total_estimated_owners": 28000000}
  ],
  "total": 75469
}
```

Deweloperzy bez `estimated_revenue_usd` (gry spoza ingestion SteamSpy)
mają `NULL` i wpadają na koniec rankingu (`NULLS LAST`).

### `GET /api/views/price-range-distribution`

Rozkład gier po przedziałach cenowych (zwykle 6 wierszy).

```bash
curl http://localhost:8000/api/views/price-range-distribution
```

```json
{
  "items": [
    {"price_range_label": "Free", "min_price": 0.0, "max_price": 0.0, "games_count": 23456, "avg_rating": 71.2},
    {"price_range_label": "$0.01-4.99", "min_price": 0.01, "max_price": 4.99, "games_count": 67890, "avg_rating": 75.8},
    {"price_range_label": "$5.00-9.99", "min_price": 5.0, "max_price": 9.99, "games_count": 18901, "avg_rating": 77.3}
  ],
  "total": 6
}
```

### `GET /api/views/sentiment-per-genre`

Rozkład sentymentu (z recenzji) per gatunek. Pokazuje tylko gry, dla
których VADER policzył sentyment (czyli mające zescrapowane recenzje).

```bash
curl http://localhost:8000/api/views/sentiment-per-genre
```

```json
{
  "items": [
    {"genre": "Action", "sentiment_label": "Positive", "games_count": 32},
    {"genre": "Action", "sentiment_label": "Mixed", "games_count": 9},
    {"genre": "Action", "sentiment_label": "Very Positive", "games_count": 4},
    {"genre": "Adventure", "sentiment_label": "Positive", "games_count": 2}
  ],
  "total": 11
}
```

### `GET /api/views/monthly-releases`

Liczba premier per (rok, miesiąc) z opcjonalnym filtrem zakresu lat.

| Param | Typ | Opis |
|---|---|---|
| `year_from` | int? | Dolne ograniczenie roku (włącznie). |
| `year_to` | int? | Górne ograniczenie roku (włącznie). |

```bash
curl "http://localhost:8000/api/views/monthly-releases?year_from=2024&year_to=2024"
```

```json
{
  "items": [
    {"year": 2024, "month": 1, "month_name": "January", "season": "Winter", "games_count": 1234, "avg_rating": 72.5},
    {"year": 2024, "month": 2, "month_name": "February", "season": "Winter", "games_count": 1156, "avg_rating": 71.9}
  ],
  "total": 12
}
```

## Kody statusów

| Status | Kiedy |
|---|---|
| `200 OK` | Sukces. |
| `404 Not Found` | `/api/games/{id}` dla nieistniejącego appida. |
| `422 Unprocessable Entity` | Niepoprawny parametr (`limit` poza zakresem, niepoprawny typ). |
| `500 Internal Server Error` | Nie powinno się zdarzać — baza musi mieć utworzony schemat. Patrz [README → Rozwiązywanie problemów](../README.md#rozwiązywanie-problemów). |

## Przykład integracji z poziomu klienta

[`frontend/src/api/client.ts`](../frontend/src/api/client.ts) jest
referencyjną implementacją typowanego klienta. Pełen kontrakt typów:
[`frontend/src/api/types.ts`](../frontend/src/api/types.ts).

```typescript
import { api } from "@/api/client";

// Pojedyncze wywołanie
const overview = await api.overview();
console.log(overview.total_games);

// Z parametrami
const games = await api.games({ q: "portal", limit: 10 });
games.items.forEach(g => console.log(g.name, g.rating_score));

// 404 jako rzucony błąd
try {
  const game = await api.gameDetail(999999999);
} catch (e) {
  console.error("Nie ma takiej gry");
}

// Równoległe ładowanie wszystkiego (jak w useDashboardStore.loadAll)
const [ov, top, genres] = await Promise.all([
  api.overview(),
  api.topRatedGames({ limit: 15 }),
  api.genreStats(),
]);
```
