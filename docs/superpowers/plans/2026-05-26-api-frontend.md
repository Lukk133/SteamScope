# API (overview/games) + Frontend Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Doprowadzić SteamScope do stanu „ready to run" — dokończyć API (endpointy `/api/overview`, `/api/games`, `/api/games/{id}`) i zbudować frontend Vue 3 (dashboard z KPI, wyszukiwarką + drawerem i 6 wykresami).

**Architecture:** Backend trzyma istniejący wzorzec — endpointy odpytują **nazwane widoki SQL** (nazwy widoków to stałe; dane użytkownika idą wyłącznie jako parametry → brak SQL injection). Frontend to osobny projekt Vite w `frontend/`, strzelający `fetch`-em do API (CORS dla `:5173` już skonfigurowany). Dwa store'y Pinia: `dashboard` (dane read-only 6 widoków + overview) i `games` (interaktywne: wyszukiwanie + wybrana gra).

**Tech Stack:** Backend — FastAPI, SQLite, pytest. Frontend — Vite, Vue 3, TypeScript, Tailwind CSS, shadcn-vue, Pinia, Apache ECharts (przez `vue-echarts`), vitest.

**Uwaga o przepływie pracy:** Projekt commituje bezpośrednio na `main` (Fazy 1–4). Kontynuujemy tę konwencję — commity po polsku w stylu Conventional Commits.

**Uwaga o testach widoków:** Fixtura `views_conn` (`tests/conftest.py`) buduje hurtownię z danych przykładowych i wywołuje `init_views()`, które czyta `backend/warehouse/views.sql`. Każdy nowy widok dodany do `views.sql` jest więc automatycznie dostępny w testach (`views_conn`) i przez fixturę `client` (`tests/test_api/conftest.py`).

---

## CZĘŚĆ A — API

### Task A1: Widok `vw_overview`

**Files:**
- Modify: `backend/warehouse/views.sql` (dopisać na końcu)
- Test: `tests/test_warehouse/test_views.py`

- [ ] **Step 1: Write the failing test**

Dopisz na końcu `tests/test_warehouse/test_views.py`:

```python
def test_vw_overview_returns_single_row_with_kpis(views_conn) -> None:
    df = pd.read_sql("SELECT * FROM vw_overview", views_conn)
    assert len(df) == 1
    expected_cols = {
        "total_games",
        "total_developers",
        "total_genres",
        "avg_rating",
        "avg_price_usd",
        "total_estimated_owners",
        "total_reviews",
        "total_estimated_revenue_usd",
    }
    assert expected_cols.issubset(set(df.columns))
    # Hurtownia z fixture ma co najmniej jedną grę i jeden gatunek.
    assert int(df["total_games"].iloc[0]) >= 1
    assert int(df["total_genres"].iloc[0]) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_warehouse/test_views.py::test_vw_overview_returns_single_row_with_kpis -v`
Expected: FAIL — `OperationalError: no such table: vw_overview`.

- [ ] **Step 3: Add the view to views.sql**

Dopisz na końcu `backend/warehouse/views.sql`:

```sql

-- Jednowierszowy agregat KPI dla nagłówka dashboardu.
DROP VIEW IF EXISTS vw_overview;
CREATE VIEW vw_overview AS
SELECT
    (SELECT COUNT(*)                    FROM fact_games)    AS total_games,
    (SELECT COUNT(*)                    FROM dim_developer) AS total_developers,
    (SELECT COUNT(*)                    FROM dim_genre)     AS total_genres,
    (SELECT AVG(rating_score)           FROM fact_games)    AS avg_rating,
    (SELECT AVG(price_usd)              FROM fact_games)    AS avg_price_usd,
    (SELECT SUM(estimated_owners)       FROM fact_games)    AS total_estimated_owners,
    (SELECT SUM(review_count)           FROM fact_games)    AS total_reviews,
    (SELECT SUM(estimated_revenue_usd)  FROM fact_games)    AS total_estimated_revenue_usd;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_warehouse/test_views.py::test_vw_overview_returns_single_row_with_kpis -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/warehouse/views.sql tests/test_warehouse/test_views.py
git commit -m "feat(warehouse): widok vw_overview (agregat KPI)"
```

---

### Task A2: Widok `vw_game_detail`

**Files:**
- Modify: `backend/warehouse/views.sql` (dopisać na końcu)
- Test: `tests/test_warehouse/test_views.py`

- [ ] **Step 1: Write the failing test**

Dopisz na końcu `tests/test_warehouse/test_views.py`:

```python
def test_vw_game_detail_has_expected_columns_and_joins(views_conn) -> None:
    df = pd.read_sql("SELECT * FROM vw_game_detail", views_conn)
    expected_cols = {
        "game_id",
        "name",
        "genre",
        "developer",
        "developer_class",
        "price_range_label",
        "release_year",
        "release_month",
        "release_month_name",
        "season",
        "sentiment_label",
        "price_usd",
        "rating_score",
        "review_count",
        "positive_review_count",
        "negative_review_count",
        "estimated_owners",
        "estimated_revenue_usd",
        "release_date",
        "playtime_avg_hours",
    }
    assert expected_cols.issubset(set(df.columns))
    # Tyle wierszy, ile gier w fact_games (LEFT JOIN nie multiplikuje).
    total = int(views_conn.execute("SELECT COUNT(*) FROM fact_games").fetchone()[0])
    assert len(df) == total
    assert df["name"].notna().all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_warehouse/test_views.py::test_vw_game_detail_has_expected_columns_and_joins -v`
Expected: FAIL — `no such table: vw_game_detail`.

- [ ] **Step 3: Add the view to views.sql**

Dopisz na końcu `backend/warehouse/views.sql`:

```sql

-- Pełny rekord gry: fact_games złączony ze wszystkimi wymiarami.
-- LEFT JOIN — brak wymiaru nie usuwa gry z wyniku.
DROP VIEW IF EXISTS vw_game_detail;
CREATE VIEW vw_game_detail AS
SELECT
    f.game_id,
    f.name,
    g.name             AS genre,
    d.name             AS developer,
    d.developer_class  AS developer_class,
    pr.label           AS price_range_label,
    rp.year            AS release_year,
    rp.month           AS release_month,
    rp.month_name      AS release_month_name,
    rp.season          AS season,
    s.label            AS sentiment_label,
    f.price_usd,
    f.rating_score,
    f.review_count,
    f.positive_review_count,
    f.negative_review_count,
    f.estimated_owners,
    f.estimated_revenue_usd,
    f.release_date,
    f.playtime_avg_hours
FROM fact_games f
LEFT JOIN dim_genre          g  ON f.genre_key          = g.genre_key
LEFT JOIN dim_developer      d  ON f.developer_key      = d.developer_key
LEFT JOIN dim_price_range    pr ON f.price_range_key    = pr.price_range_key
LEFT JOIN dim_release_period rp ON f.release_period_key = rp.release_period_key
LEFT JOIN dim_sentiment      s  ON f.sentiment_key      = s.sentiment_key;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_warehouse/test_views.py::test_vw_game_detail_has_expected_columns_and_joins -v`
Expected: PASS.

- [ ] **Step 5: Aktualizacja testu idempotencji widoków**

W `tests/test_warehouse/test_views.py`, w `test_init_views_is_idempotent`, rozszerz zbiór `expected`:

```python
    expected = {
        "vw_top_rated_games",
        "vw_genre_stats",
        "vw_developer_leaderboard",
        "vw_price_range_distribution",
        "vw_sentiment_per_genre",
        "vw_monthly_releases",
        "vw_overview",
        "vw_game_detail",
    }
```

- [ ] **Step 6: Run full warehouse view tests**

Run: `pytest tests/test_warehouse/test_views.py -v`
Expected: PASS (wszystkie, w tym idempotencja z nowymi widokami).

- [ ] **Step 7: Commit**

```bash
git add backend/warehouse/views.sql tests/test_warehouse/test_views.py
git commit -m "feat(warehouse): widok vw_game_detail (gra + wszystkie wymiary)"
```

---

### Task A3: Router `/api/overview`

**Files:**
- Create: `backend/api/routers/overview.py`
- Modify: `backend/api/main.py`
- Test: `tests/test_api/test_overview.py`

- [ ] **Step 1: Write the failing test**

Utwórz `tests/test_api/test_overview.py`:

```python
"""Testy endpointu zbiorczego KPI /api/overview."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_overview_returns_kpi_object(client: TestClient) -> None:
    res = client.get("/api/overview")
    assert res.status_code == 200
    body = res.json()
    for key in (
        "total_games",
        "total_developers",
        "total_genres",
        "avg_rating",
        "avg_price_usd",
        "total_estimated_owners",
        "total_reviews",
        "total_estimated_revenue_usd",
    ):
        assert key in body, f"Brak klucza {key} w odpowiedzi /api/overview"
    assert isinstance(body["total_games"], int)
    assert body["total_games"] >= 1


def test_overview_in_openapi(client: TestClient) -> None:
    res = client.get("/openapi.json")
    assert res.status_code == 200
    assert "/api/overview" in res.json()["paths"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api/test_overview.py -v`
Expected: FAIL — 404 (endpoint nie istnieje).

- [ ] **Step 3: Create the router**

Utwórz `backend/api/routers/overview.py`:

```python
"""Endpoint zbiorczy KPI nad widokiem vw_overview.

Widok ``vw_overview`` zawsze zwraca dokładnie jeden wiersz agregatów.
Nazwa widoku jest stałą modułową — brak powierzchni na SQL injection.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.dependencies import DbConn

router = APIRouter(prefix="/api", tags=["overview"])

_VIEW_OVERVIEW = "vw_overview"


@router.get("/overview")
def overview(conn: DbConn) -> dict:
    """Zwraca jeden wiersz KPI dla nagłówka dashboardu."""
    row = conn.execute(f"SELECT * FROM {_VIEW_OVERVIEW}").fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Brak danych overview")
    return dict(row)
```

- [ ] **Step 4: Register the router**

W `backend/api/main.py` dodaj import obok istniejącego:

```python
from backend.api.routers import overview as overview_router
from backend.api.routers import views as views_router
```

oraz rejestrację w `create_app()` po `app.include_router(views_router.router)`:

```python
    app.include_router(views_router.router)
    app.include_router(overview_router.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_api/test_overview.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/api/routers/overview.py backend/api/main.py tests/test_api/test_overview.py
git commit -m "feat(api): endpoint /api/overview (KPI dashboardu)"
```

---

### Task A4: Router `/api/games` (lista + szczegóły)

**Files:**
- Create: `backend/api/routers/games.py`
- Modify: `backend/api/main.py`
- Test: `tests/test_api/test_games.py`

- [ ] **Step 1: Write the failing test**

Utwórz `tests/test_api/test_games.py`:

```python
"""Testy endpointów /api/games (lista, filtr, paginacja, szczegóły)."""
from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient


def test_list_games_returns_items_and_total(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    res = client.get("/api/games")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    expected = int(views_conn.execute("SELECT COUNT(*) FROM vw_game_detail").fetchone()[0])
    assert body["total"] == expected
    if body["items"]:
        assert "game_id" in body["items"][0]
        assert "name" in body["items"][0]


def test_list_games_pagination(client: TestClient) -> None:
    res = client.get("/api/games", params={"limit": 1, "offset": 0})
    assert res.status_code == 200
    assert len(res.json()["items"]) <= 1


def test_list_games_rejects_invalid_limit(client: TestClient) -> None:
    res = client.get("/api/games", params={"limit": 999})
    assert res.status_code == 422


def test_list_games_filter_by_name(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    row = views_conn.execute(
        "SELECT name FROM vw_game_detail WHERE name IS NOT NULL LIMIT 1"
    ).fetchone()
    assert row is not None
    name = row[0]
    fragment = name[: max(1, len(name) // 2)]
    res = client.get("/api/games", params={"q": fragment})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert all(fragment.lower() in item["name"].lower() for item in body["items"])


def test_game_detail_returns_full_record(
    client: TestClient, views_conn: sqlite3.Connection
) -> None:
    row = views_conn.execute("SELECT game_id FROM vw_game_detail LIMIT 1").fetchone()
    assert row is not None
    game_id = int(row[0])
    res = client.get(f"/api/games/{game_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["game_id"] == game_id
    assert "rating_score" in body
    assert "developer" in body


def test_game_detail_404_for_unknown_id(client: TestClient) -> None:
    res = client.get("/api/games/999999999")
    assert res.status_code == 404


def test_games_endpoints_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/games" in paths
    assert "/api/games/{game_id}" in paths
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api/test_games.py -v`
Expected: FAIL — 404 (endpointy nie istnieją).

- [ ] **Step 3: Create the router**

Utwórz `backend/api/routers/games.py`:

```python
"""Endpointy listy/wyszukiwania gier i szczegółów pojedynczej gry.

Zapytania idą po stałym widoku ``vw_game_detail``; ``q`` i ``game_id``
trafiają wyłącznie jako parametry — brak powierzchni na SQL injection.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException, Query

from backend.api.dependencies import DbConn

router = APIRouter(prefix="/api/games", tags=["games"])

_VIEW_GAME_DETAIL = "vw_game_detail"


@router.get("")
def list_games(
    conn: DbConn,
    q: str | None = Query(None, description="Filtr po nazwie (LIKE, bez rozróżniania wielkości)."),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Lista gier z opcjonalnym filtrem nazwy i paginacją.

    Zwraca ``{"items": [...], "total": <int>}`` — ``total`` po filtrze,
    przed paginacją.
    """
    where_sql = ""
    where_params: list[str] = []
    if q:
        where_sql = " WHERE name LIKE ?"
        where_params.append(f"%{q}%")

    rows = conn.execute(
        f"SELECT * FROM {_VIEW_GAME_DETAIL}{where_sql} "
        "ORDER BY rating_score DESC, review_count DESC LIMIT ? OFFSET ?",
        (*where_params, limit, offset),
    ).fetchall()
    total_row = conn.execute(
        f"SELECT COUNT(*) AS c FROM {_VIEW_GAME_DETAIL}{where_sql}",
        where_params,
    ).fetchone()
    return {"items": [dict(r) for r in rows], "total": int(total_row["c"])}


@router.get("/{game_id}")
def game_detail(conn: DbConn, game_id: int) -> dict:
    """Pełny rekord pojedynczej gry albo 404, gdy brak."""
    row: sqlite3.Row | None = conn.execute(
        f"SELECT * FROM {_VIEW_GAME_DETAIL} WHERE game_id = ?",
        (game_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono gry")
    return dict(row)
```

- [ ] **Step 4: Register the router**

W `backend/api/main.py` dodaj import:

```python
from backend.api.routers import games as games_router
```

i rejestrację w `create_app()` po `overview_router`:

```python
    app.include_router(overview_router.router)
    app.include_router(games_router.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_api/test_games.py -v`
Expected: PASS (wszystkie 7).

- [ ] **Step 6: Commit**

```bash
git add backend/api/routers/games.py backend/api/main.py tests/test_api/test_games.py
git commit -m "feat(api): endpointy /api/games (lista/filtr) i /api/games/{id}"
```

---

### Task A5: Pełny przebieg testów + lint API

**Files:** brak zmian — weryfikacja.

- [ ] **Step 1: Run full test suite**

Run: `pytest`
Expected: PASS (wszystkie, w tym nowe API i widoki).

- [ ] **Step 2: Run linter**

Run: `ruff check backend tests scripts`
Expected: brak błędów. Jeśli są — napraw inline i ponów.

- [ ] **Step 3: Smoke test serwera (opcjonalny, manualny)**

Run: `uvicorn backend.api.main:app --port 8000` (Ctrl+C aby zatrzymać)
Sprawdź `http://localhost:8000/docs` — widoczne `/api/overview`, `/api/games`, `/api/games/{game_id}`.

---

### Task A6: README — sekcja Faza 4

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the section**

Dopisz w `README.md` po sekcji „Faza 3 — Warstwa wynikowa", przed „## Testy":

```markdown
## Faza 4 — API (FastAPI)

REST API udostępnia warstwę wynikową hurtowni. Uruchomienie serwera dev:

```powershell
uvicorn backend.api.main:app --reload --port 8000
```

Dokumentacja interaktywna: `http://localhost:8000/docs`.

| Endpoint | Opis |
|---|---|
| `GET /` | Metadane aplikacji (odsyła do `/docs`). |
| `GET /api/health` | Status zdrowia (monitoring/smoke-test). |
| `GET /api/overview` | Zbiorcze KPI (liczba gier, deweloperów, śr. ocena, przychód…). |
| `GET /api/games?q=&limit=&offset=` | Lista/wyszukiwanie gier (filtr po nazwie, paginacja). |
| `GET /api/games/{game_id}` | Szczegóły pojedynczej gry (404, gdy brak). |
| `GET /api/views/top-rated-games` | Ranking najwyżej ocenianych gier (paginacja). |
| `GET /api/views/genre-stats` | Statystyki per gatunek. |
| `GET /api/views/developer-leaderboard` | Liderzy deweloperów (paginacja). |
| `GET /api/views/price-range-distribution` | Rozkład przedziałów cenowych. |
| `GET /api/views/sentiment-per-genre` | Rozkład sentymentu per gatunek. |
| `GET /api/views/monthly-releases?year_from=&year_to=` | Premiery wg miesiąca (filtr lat). |

CORS jest włączony dla serwera dev frontendu (`http://localhost:5173`).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README — Faza 4 (API FastAPI)"
```

---

## CZĘŚĆ B — FRONTEND

> **Uwaga dla wykonawcy:** Frontend tworzymy ręcznie (bez interaktywnych kreatorów). Wszystkie polecenia uruchamiamy z katalogu `frontend/`. Node.js ≥ 18 wymagany. Jeśli `npm`/`node` nie istnieje — zatrzymaj się i zgłoś użytkownikowi.

### Task B1: Scaffold projektu Vite + zależności

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/index.html`
- Create: `frontend/.env.example`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/style.css`
- Modify: `.gitignore`

- [ ] **Step 1: Create package.json**

Utwórz `frontend/package.json`:

```json
{
  "name": "steamscope-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "pinia": "^2.1.0",
    "echarts": "^5.5.0",
    "vue-echarts": "^7.0.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.3.0",
    "lucide-vue-next": "^0.400.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "vue-tsc": "^2.0.0",
    "vitest": "^1.6.0",
    "@vue/test-utils": "^2.4.0",
    "jsdom": "^24.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

- [ ] **Step 2: Create vite.config.ts**

Utwórz `frontend/vite.config.ts`:

```typescript
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
```

- [ ] **Step 3: Create tsconfig.json and tsconfig.node.json**

Utwórz `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] },
    "types": ["vitest/globals"]
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Utwórz `frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "noEmit": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create index.html**

Utwórz `frontend/index.html`:

```html
<!doctype html>
<html lang="pl" class="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SteamScope</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 5: Create .env.example**

Utwórz `frontend/.env.example`:

```
VITE_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 6: Create Tailwind config + PostCSS + base CSS**

Utwórz `frontend/postcss.config.js`:

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

Utwórz `frontend/tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{vue,ts}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        primary: "hsl(var(--primary))",
        "primary-foreground": "hsl(var(--primary-foreground))",
      },
    },
  },
  plugins: [],
};
```

Utwórz `frontend/src/style.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 222 47% 11%;
    --foreground: 210 40% 98%;
    --card: 222 47% 14%;
    --card-foreground: 210 40% 98%;
    --muted: 217 33% 22%;
    --muted-foreground: 215 20% 65%;
    --primary: 199 89% 48%;
    --primary-foreground: 210 40% 98%;
    --border: 217 33% 24%;
  }

  body {
    @apply bg-background text-foreground;
    margin: 0;
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  }
}
```

- [ ] **Step 7: Update .gitignore**

Dopisz na końcu `.gitignore` (w katalogu głównym projektu):

```
# Frontend
frontend/node_modules/
frontend/dist/
frontend/.env
```

- [ ] **Step 8: Install dependencies**

Run (z katalogu `frontend/`): `npm install`
Expected: instalacja bez błędów; powstaje `frontend/node_modules` i `frontend/package-lock.json`.

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/tsconfig.json frontend/tsconfig.node.json frontend/index.html frontend/.env.example frontend/postcss.config.js frontend/tailwind.config.js frontend/src/style.css .gitignore
git commit -m "chore(frontend): scaffold Vite + Vue 3 + TS + Tailwind (Faza 5)"
```

---

### Task B2: Warstwa `lib/utils` + komponenty UI (shadcn-vue style)

**Files:**
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/components/ui/Card.vue`
- Create: `frontend/src/components/ui/Input.vue`
- Create: `frontend/components.json`

> **Uwaga:** zamiast uruchamiać kreator `shadcn-vue`, tworzymy ręcznie minimalny zestaw komponentów w stylu shadcn-vue (te same prymitywy: `cn()` na `clsx`+`tailwind-merge`, komponenty oparte na Tailwind). `components.json` zostawiamy jako konfigurację na wypadek dogrywania kolejnych komponentów CLI.

- [ ] **Step 1: Create cn() helper**

Utwórz `frontend/src/lib/utils.ts`:

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Create Card component**

Utwórz `frontend/src/components/ui/Card.vue`:

```vue
<script setup lang="ts">
import { cn } from "@/lib/utils";

defineProps<{ title?: string; class?: string }>();
</script>

<template>
  <div
    :class="cn('rounded-xl border border-border bg-card text-card-foreground shadow-sm', $props.class)"
  >
    <div v-if="title" class="border-b border-border px-4 py-3">
      <h3 class="text-sm font-semibold tracking-tight">{{ title }}</h3>
    </div>
    <div class="p-4">
      <slot />
    </div>
  </div>
</template>
```

- [ ] **Step 3: Create Input component**

Utwórz `frontend/src/components/ui/Input.vue`:

```vue
<script setup lang="ts">
import { cn } from "@/lib/utils";

defineProps<{ modelValue?: string; placeholder?: string; class?: string }>();
defineEmits<{ "update:modelValue": [value: string] }>();
</script>

<template>
  <input
    :value="modelValue"
    :placeholder="placeholder"
    :class="
      cn(
        'flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm',
        'placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary',
        $props.class,
      )
    "
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>
```

- [ ] **Step 4: Create components.json**

Utwórz `frontend/components.json`:

```json
{
  "$schema": "https://shadcn-vue.com/schema.json",
  "style": "default",
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "src/style.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils"
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/utils.ts frontend/src/components/ui/Card.vue frontend/src/components/ui/Input.vue frontend/components.json
git commit -m "feat(frontend): prymitywy UI (cn, Card, Input) w stylu shadcn-vue"
```

---

### Task B3: Klient API + typy (z testem vitest)

**Files:**
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.test.ts`

- [ ] **Step 1: Create types**

Utwórz `frontend/src/api/types.ts`:

```typescript
export interface Overview {
  total_games: number;
  total_developers: number;
  total_genres: number;
  avg_rating: number | null;
  avg_price_usd: number | null;
  total_estimated_owners: number | null;
  total_reviews: number | null;
  total_estimated_revenue_usd: number | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
}

export interface TopRatedGame {
  game_id: number;
  name: string;
  genre: string | null;
  developer: string | null;
  price_usd: number | null;
  rating_score: number | null;
  review_count: number | null;
  estimated_owners: number | null;
}

export interface GenreStat {
  genre: string;
  games_count: number;
  avg_rating: number | null;
  avg_price_usd: number | null;
  avg_estimated_owners: number | null;
  total_review_count: number | null;
}

export interface DeveloperRow {
  developer: string;
  developer_class: string;
  games_count: number;
  avg_rating: number | null;
  total_estimated_revenue_usd: number | null;
  total_estimated_owners: number | null;
}

export interface PriceRangeRow {
  price_range_label: string;
  min_price: number;
  max_price: number | null;
  games_count: number;
  avg_rating: number | null;
}

export interface SentimentRow {
  genre: string;
  sentiment_label: string;
  games_count: number;
}

export interface MonthlyReleaseRow {
  year: number;
  month: number;
  month_name: string;
  season: string;
  games_count: number;
  avg_rating: number | null;
}

export interface GameDetail {
  game_id: number;
  name: string;
  genre: string | null;
  developer: string | null;
  developer_class: string | null;
  price_range_label: string | null;
  release_year: number | null;
  release_month: number | null;
  release_month_name: string | null;
  season: string | null;
  sentiment_label: string | null;
  price_usd: number | null;
  rating_score: number | null;
  review_count: number | null;
  positive_review_count: number | null;
  negative_review_count: number | null;
  estimated_owners: number | null;
  estimated_revenue_usd: number | null;
  release_date: string | null;
  playtime_avg_hours: number | null;
}
```

- [ ] **Step 2: Write the failing test**

Utwórz `frontend/src/api/client.test.ts`:

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./client";

afterEach(() => {
  vi.restoreAllMocks();
});

function mockFetch(body: unknown, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(body),
  } as Response);
}

describe("api client", () => {
  it("buduje URL z bazą i zwraca sparsowane JSON", async () => {
    const fetchMock = mockFetch({ total_games: 5 });
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.overview();

    expect(fetchMock).toHaveBeenCalledOnce();
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/api/overview");
    expect(result.total_games).toBe(5);
  });

  it("dokleja parametry zapytania do /api/games", async () => {
    const fetchMock = mockFetch({ items: [], total: 0 });
    vi.stubGlobal("fetch", fetchMock);

    await api.games({ q: "half", limit: 10 });

    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/api/games");
    expect(calledUrl).toContain("q=half");
    expect(calledUrl).toContain("limit=10");
  });

  it("rzuca błąd przy odpowiedzi nie-ok", async () => {
    vi.stubGlobal("fetch", mockFetch({ detail: "nope" }, false, 404));
    await expect(api.gameDetail(1)).rejects.toThrow();
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run (z `frontend/`): `npm run test`
Expected: FAIL — `Cannot find module './client'` lub brak eksportu `api`.

- [ ] **Step 4: Create the client**

Utwórz `frontend/src/api/client.ts`:

```typescript
import type {
  DeveloperRow,
  GameDetail,
  GenreStat,
  MonthlyReleaseRow,
  Overview,
  Paginated,
  PriceRangeRow,
  SentimentRow,
  TopRatedGame,
} from "./types";

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

type QueryValue = string | number | undefined | null;

function buildUrl(path: string, params?: Record<string, QueryValue>): string {
  const url = new URL(path, BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function get<T>(path: string, params?: Record<string, QueryValue>): Promise<T> {
  const res = await fetch(buildUrl(path, params));
  if (!res.ok) {
    throw new Error(`API ${path} → ${res.status}`);
  }
  return (await res.json()) as T;
}

export const api = {
  overview: () => get<Overview>("/api/overview"),
  topRatedGames: (params?: { limit?: number; offset?: number }) =>
    get<Paginated<TopRatedGame>>("/api/views/top-rated-games", params),
  genreStats: () => get<Paginated<GenreStat>>("/api/views/genre-stats"),
  developerLeaderboard: (params?: { limit?: number; offset?: number }) =>
    get<Paginated<DeveloperRow>>("/api/views/developer-leaderboard", params),
  priceRangeDistribution: () =>
    get<Paginated<PriceRangeRow>>("/api/views/price-range-distribution"),
  sentimentPerGenre: () => get<Paginated<SentimentRow>>("/api/views/sentiment-per-genre"),
  monthlyReleases: (params?: { year_from?: number; year_to?: number }) =>
    get<Paginated<MonthlyReleaseRow>>("/api/views/monthly-releases", params),
  games: (params?: { q?: string; limit?: number; offset?: number }) =>
    get<Paginated<GameDetail>>("/api/games", params),
  gameDetail: (gameId: number) => get<GameDetail>(`/api/games/${gameId}`),
};
```

- [ ] **Step 5: Run test to verify it passes**

Run (z `frontend/`): `npm run test`
Expected: PASS (3 testy klienta).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "feat(frontend): typowany klient API + testy vitest"
```

---

### Task B4: Store'y Pinia

**Files:**
- Create: `frontend/src/stores/dashboard.ts`
- Create: `frontend/src/stores/games.ts`

- [ ] **Step 1: Create dashboard store**

Utwórz `frontend/src/stores/dashboard.ts`:

```typescript
import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "@/api/client";
import type {
  DeveloperRow,
  GenreStat,
  MonthlyReleaseRow,
  Overview,
  PriceRangeRow,
  SentimentRow,
  TopRatedGame,
} from "@/api/types";

export const useDashboardStore = defineStore("dashboard", () => {
  const overview = ref<Overview | null>(null);
  const topRated = ref<TopRatedGame[]>([]);
  const genreStats = ref<GenreStat[]>([]);
  const developers = ref<DeveloperRow[]>([]);
  const priceRanges = ref<PriceRangeRow[]>([]);
  const sentiment = ref<SentimentRow[]>([]);
  const monthly = ref<MonthlyReleaseRow[]>([]);

  const loading = ref(false);
  const error = ref<string | null>(null);

  async function loadAll(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const [ov, tr, gs, dev, pr, se, mo] = await Promise.all([
        api.overview(),
        api.topRatedGames({ limit: 15 }),
        api.genreStats(),
        api.developerLeaderboard({ limit: 15 }),
        api.priceRangeDistribution(),
        api.sentimentPerGenre(),
        api.monthlyReleases(),
      ]);
      overview.value = ov;
      topRated.value = tr.items;
      genreStats.value = gs.items;
      developers.value = dev.items;
      priceRanges.value = pr.items;
      sentiment.value = se.items;
      monthly.value = mo.items;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Błąd ładowania danych";
    } finally {
      loading.value = false;
    }
  }

  async function loadMonthly(yearFrom?: number, yearTo?: number): Promise<void> {
    const res = await api.monthlyReleases({ year_from: yearFrom, year_to: yearTo });
    monthly.value = res.items;
  }

  return {
    overview,
    topRated,
    genreStats,
    developers,
    priceRanges,
    sentiment,
    monthly,
    loading,
    error,
    loadAll,
    loadMonthly,
  };
});
```

- [ ] **Step 2: Create games store**

Utwórz `frontend/src/stores/games.ts`:

```typescript
import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "@/api/client";
import type { GameDetail } from "@/api/types";

export const useGamesStore = defineStore("games", () => {
  const query = ref("");
  const results = ref<GameDetail[]>([]);
  const searching = ref(false);
  const selected = ref<GameDetail | null>(null);
  const drawerOpen = ref(false);

  async function search(): Promise<void> {
    const q = query.value.trim();
    if (!q) {
      results.value = [];
      return;
    }
    searching.value = true;
    try {
      const res = await api.games({ q, limit: 20 });
      results.value = res.items;
    } finally {
      searching.value = false;
    }
  }

  async function openGame(gameId: number): Promise<void> {
    selected.value = await api.gameDetail(gameId);
    drawerOpen.value = true;
  }

  function closeDrawer(): void {
    drawerOpen.value = false;
  }

  return { query, results, searching, selected, drawerOpen, search, openGame, closeDrawer };
});
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/dashboard.ts frontend/src/stores/games.ts
git commit -m "feat(frontend): store'y Pinia (dashboard + games)"
```

---

### Task B5: Wrapper ECharts `BaseChart`

**Files:**
- Create: `frontend/src/components/charts/BaseChart.vue`
- Create: `frontend/src/echarts.ts`

- [ ] **Step 1: Register ECharts components**

Utwórz `frontend/src/echarts.ts`:

```typescript
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, LineChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
]);
```

- [ ] **Step 2: Create BaseChart**

Utwórz `frontend/src/components/charts/BaseChart.vue`:

```vue
<script setup lang="ts">
import VChart from "vue-echarts";
import type { EChartsOption } from "echarts";
import "@/echarts";

defineProps<{ option: EChartsOption; empty?: boolean; height?: string }>();
</script>

<template>
  <div :style="{ height: height ?? '320px' }" class="w-full">
    <div
      v-if="empty"
      class="flex h-full items-center justify-center text-sm text-muted-foreground"
    >
      Brak danych — uruchom pipeline ingestion/ETL.
    </div>
    <VChart v-else :option="option" autoresize class="h-full w-full" />
  </div>
</template>
```

- [ ] **Step 3: Smoke check types**

Run (z `frontend/`): `npx vue-tsc --noEmit`
Expected: brak błędów typów w nowych plikach. (Jeśli `EChartsOption` nie rozwiązuje się — upewnij się, że `echarts` zainstalowany; typ pochodzi z pakietu `echarts`.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/echarts.ts frontend/src/components/charts/BaseChart.vue
git commit -m "feat(frontend): wrapper ECharts (BaseChart) + rejestracja modułów"
```

---

### Task B6: Komponenty wykresów (6)

**Files:**
- Create: `frontend/src/components/charts/TopRatedChart.vue`
- Create: `frontend/src/components/charts/GenreStatsChart.vue`
- Create: `frontend/src/components/charts/DeveloperChart.vue`
- Create: `frontend/src/components/charts/PriceRangeChart.vue`
- Create: `frontend/src/components/charts/SentimentChart.vue`
- Create: `frontend/src/components/charts/MonthlyReleasesChart.vue`

- [ ] **Step 1: TopRatedChart (bar poziomy)**

Utwórz `frontend/src/components/charts/TopRatedChart.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { TopRatedGame } from "@/api/types";

const props = defineProps<{ data: TopRatedGame[] }>();

const option = computed<EChartsOption>(() => {
  const sorted = [...props.data].sort(
    (a, b) => (a.rating_score ?? 0) - (b.rating_score ?? 0),
  );
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 140, right: 16, top: 16, bottom: 24 },
    xAxis: { type: "value", max: 100 },
    yAxis: { type: "category", data: sorted.map((g) => g.name) },
    series: [
      {
        type: "bar",
        data: sorted.map((g) => g.rating_score ?? 0),
        itemStyle: { color: "#38bdf8" },
      },
    ],
  };
});
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" />
</template>
```

- [ ] **Step 2: GenreStatsChart (bar pionowy)**

Utwórz `frontend/src/components/charts/GenreStatsChart.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { GenreStat } from "@/api/types";

const props = defineProps<{ data: GenreStat[] }>();

const option = computed<EChartsOption>(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 48, right: 16, top: 16, bottom: 64 },
  xAxis: {
    type: "category",
    data: props.data.map((g) => g.genre),
    axisLabel: { rotate: 35, interval: 0 },
  },
  yAxis: { type: "value" },
  series: [
    {
      type: "bar",
      name: "Liczba gier",
      data: props.data.map((g) => g.games_count),
      itemStyle: { color: "#818cf8" },
    },
  ],
}));
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" />
</template>
```

- [ ] **Step 3: DeveloperChart (bar poziomy, przychód)**

Utwórz `frontend/src/components/charts/DeveloperChart.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { DeveloperRow } from "@/api/types";

const props = defineProps<{ data: DeveloperRow[] }>();

const option = computed<EChartsOption>(() => {
  const sorted = [...props.data].sort(
    (a, b) => (a.total_estimated_revenue_usd ?? 0) - (b.total_estimated_revenue_usd ?? 0),
  );
  return {
    tooltip: { trigger: "axis", valueFormatter: (v) => `$${Number(v).toLocaleString()}` },
    grid: { left: 160, right: 24, top: 16, bottom: 24 },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: sorted.map((d) => d.developer) },
    series: [
      {
        type: "bar",
        data: sorted.map((d) => d.total_estimated_revenue_usd ?? 0),
        itemStyle: { color: "#34d399" },
      },
    ],
  };
});
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" />
</template>
```

- [ ] **Step 4: PriceRangeChart (pie)**

Utwórz `frontend/src/components/charts/PriceRangeChart.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { PriceRangeRow } from "@/api/types";

const props = defineProps<{ data: PriceRangeRow[] }>();

const option = computed<EChartsOption>(() => ({
  tooltip: { trigger: "item" },
  legend: { bottom: 0, textStyle: { color: "#cbd5e1" } },
  series: [
    {
      type: "pie",
      radius: ["40%", "70%"],
      data: props.data.map((p) => ({ name: p.price_range_label, value: p.games_count })),
    },
  ],
}));
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" />
</template>
```

- [ ] **Step 5: SentimentChart (stacked bar)**

Utwórz `frontend/src/components/charts/SentimentChart.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { SentimentRow } from "@/api/types";

const props = defineProps<{ data: SentimentRow[] }>();

const option = computed<EChartsOption>(() => {
  const genres = [...new Set(props.data.map((r) => r.genre))];
  const labels = [...new Set(props.data.map((r) => r.sentiment_label))];
  const series = labels.map((label) => ({
    name: label,
    type: "bar" as const,
    stack: "sentiment",
    data: genres.map((genre) => {
      const match = props.data.find((r) => r.genre === genre && r.sentiment_label === label);
      return match ? match.games_count : 0;
    }),
  }));
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { top: 0, textStyle: { color: "#cbd5e1" } },
    grid: { left: 48, right: 16, top: 32, bottom: 64 },
    xAxis: { type: "category", data: genres, axisLabel: { rotate: 35, interval: 0 } },
    yAxis: { type: "value" },
    series,
  };
});
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" />
</template>
```

- [ ] **Step 6: MonthlyReleasesChart (line)**

Utwórz `frontend/src/components/charts/MonthlyReleasesChart.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import type { EChartsOption } from "echarts";
import BaseChart from "./BaseChart.vue";
import type { MonthlyReleaseRow } from "@/api/types";

const props = defineProps<{ data: MonthlyReleaseRow[] }>();

const option = computed<EChartsOption>(() => {
  const labels = props.data.map((r) => `${r.year}-${String(r.month).padStart(2, "0")}`);
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 48, right: 16, top: 24, bottom: 48 },
    xAxis: { type: "category", data: labels, axisLabel: { rotate: 35 } },
    yAxis: { type: "value" },
    series: [
      {
        type: "line",
        smooth: true,
        data: props.data.map((r) => r.games_count),
        areaStyle: { opacity: 0.15 },
        itemStyle: { color: "#fbbf24" },
      },
    ],
  };
});
</script>

<template>
  <BaseChart :option="option" :empty="data.length === 0" />
</template>
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/charts/
git commit -m "feat(frontend): 6 komponentów wykresów ECharts"
```

---

### Task B7: KPI cards (z testem vitest)

**Files:**
- Create: `frontend/src/components/KpiCards.vue`
- Test: `frontend/src/components/KpiCards.test.ts`

- [ ] **Step 1: Write the failing test**

Utwórz `frontend/src/components/KpiCards.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import KpiCards from "./KpiCards.vue";
import type { Overview } from "@/api/types";

const sample: Overview = {
  total_games: 1234,
  total_developers: 56,
  total_genres: 12,
  avg_rating: 78.5,
  avg_price_usd: 14.99,
  total_estimated_owners: 5000000,
  total_reviews: 99999,
  total_estimated_revenue_usd: 12345678,
};

describe("KpiCards", () => {
  it("renderuje liczbę gier gdy overview podane", () => {
    const wrapper = mount(KpiCards, { props: { overview: sample } });
    expect(wrapper.text()).toContain("1");
    expect(wrapper.text()).toContain("Gry");
  });

  it("pokazuje stan pusty gdy overview = null", () => {
    const wrapper = mount(KpiCards, { props: { overview: null } });
    expect(wrapper.text()).toContain("Brak danych");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (z `frontend/`): `npm run test`
Expected: FAIL — `Cannot find module './KpiCards.vue'`.

- [ ] **Step 3: Create KpiCards**

Utwórz `frontend/src/components/KpiCards.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import Card from "@/components/ui/Card.vue";
import type { Overview } from "@/api/types";

const props = defineProps<{ overview: Overview | null }>();

function fmt(value: number | null, opts?: Intl.NumberFormatOptions): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("pl-PL", opts).format(value);
}

const cards = computed(() => {
  if (!props.overview) return [];
  const o = props.overview;
  return [
    { label: "Gry", value: fmt(o.total_games) },
    { label: "Deweloperzy", value: fmt(o.total_developers) },
    { label: "Gatunki", value: fmt(o.total_genres) },
    { label: "Śr. ocena", value: o.avg_rating === null ? "—" : fmt(o.avg_rating, { maximumFractionDigits: 1 }) },
    { label: "Recenzje", value: fmt(o.total_reviews) },
    {
      label: "Szac. przychód",
      value: o.total_estimated_revenue_usd === null ? "—" : `$${fmt(o.total_estimated_revenue_usd, { maximumFractionDigits: 0 })}`,
    },
  ];
});
</script>

<template>
  <div v-if="cards.length" class="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
    <Card v-for="c in cards" :key="c.label">
      <div class="text-xs uppercase tracking-wide text-muted-foreground">{{ c.label }}</div>
      <div class="mt-1 text-2xl font-bold">{{ c.value }}</div>
    </Card>
  </div>
  <Card v-else>
    <div class="text-sm text-muted-foreground">Brak danych — uruchom pipeline ingestion/ETL.</div>
  </Card>
</template>
```

- [ ] **Step 4: Run test to verify it passes**

Run (z `frontend/`): `npm run test`
Expected: PASS (klient API + KpiCards).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/KpiCards.vue frontend/src/components/KpiCards.test.ts
git commit -m "feat(frontend): kafelki KPI + test vitest"
```

---

### Task B8: Wyszukiwarka gier + drawer szczegółów

**Files:**
- Create: `frontend/src/components/GameSearch.vue`
- Create: `frontend/src/components/GameDetailDrawer.vue`

- [ ] **Step 1: Create GameSearch**

Utwórz `frontend/src/components/GameSearch.vue`:

```vue
<script setup lang="ts">
import Card from "@/components/ui/Card.vue";
import Input from "@/components/ui/Input.vue";
import { useGamesStore } from "@/stores/games";

const store = useGamesStore();
</script>

<template>
  <Card title="Wyszukiwarka gier">
    <Input
      v-model="store.query"
      placeholder="Wpisz nazwę gry i naciśnij Enter…"
      @keyup.enter="store.search()"
    />
    <div v-if="store.searching" class="mt-3 text-sm text-muted-foreground">Szukam…</div>
    <ul v-else-if="store.results.length" class="mt-3 divide-y divide-border">
      <li
        v-for="g in store.results"
        :key="g.game_id"
        class="flex cursor-pointer items-center justify-between py-2 hover:text-primary"
        @click="store.openGame(g.game_id)"
      >
        <span>{{ g.name }}</span>
        <span class="text-sm text-muted-foreground">
          {{ g.rating_score === null ? "—" : Math.round(g.rating_score) }}
        </span>
      </li>
    </ul>
    <div v-else-if="store.query.trim()" class="mt-3 text-sm text-muted-foreground">
      Brak wyników.
    </div>
  </Card>
</template>
```

- [ ] **Step 2: Create GameDetailDrawer**

Utwórz `frontend/src/components/GameDetailDrawer.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import { useGamesStore } from "@/stores/games";

const store = useGamesStore();
const g = computed(() => store.selected);

function fmt(v: number | null | undefined, prefix = ""): string {
  if (v === null || v === undefined) return "—";
  return prefix + new Intl.NumberFormat("pl-PL").format(v);
}
</script>

<template>
  <div
    v-if="store.drawerOpen"
    class="fixed inset-0 z-50 flex justify-end bg-black/50"
    @click.self="store.closeDrawer()"
  >
    <aside class="h-full w-full max-w-md overflow-y-auto border-l border-border bg-card p-6">
      <div class="flex items-start justify-between">
        <h2 class="text-xl font-bold">{{ g?.name }}</h2>
        <button class="text-muted-foreground hover:text-foreground" @click="store.closeDrawer()">
          ✕
        </button>
      </div>
      <dl v-if="g" class="mt-4 space-y-2 text-sm">
        <div class="flex justify-between"><dt class="text-muted-foreground">Gatunek</dt><dd>{{ g.genre ?? "—" }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Deweloper</dt><dd>{{ g.developer ?? "—" }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Klasa</dt><dd>{{ g.developer_class ?? "—" }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Cena</dt><dd>{{ fmt(g.price_usd, "$") }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Ocena</dt><dd>{{ fmt(g.rating_score) }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Recenzje</dt><dd>{{ fmt(g.review_count) }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Pozytywne</dt><dd>{{ fmt(g.positive_review_count) }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Negatywne</dt><dd>{{ fmt(g.negative_review_count) }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Wł. (szac.)</dt><dd>{{ fmt(g.estimated_owners) }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Przychód (szac.)</dt><dd>{{ fmt(g.estimated_revenue_usd, "$") }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Premiera</dt><dd>{{ g.release_date ?? "—" }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Sentyment</dt><dd>{{ g.sentiment_label ?? "—" }}</dd></div>
        <div class="flex justify-between"><dt class="text-muted-foreground">Śr. czas gry (h)</dt><dd>{{ fmt(g.playtime_avg_hours) }}</dd></div>
      </dl>
    </aside>
  </div>
</template>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/GameSearch.vue frontend/src/components/GameDetailDrawer.vue
git commit -m "feat(frontend): wyszukiwarka gier + drawer szczegółów"
```

---

### Task B9: Dashboard, App, main + bootstrap

**Files:**
- Create: `frontend/src/views/Dashboard.vue`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/components/MonthlyFilter.vue`

- [ ] **Step 1: Create MonthlyFilter**

Utwórz `frontend/src/components/MonthlyFilter.vue`:

```vue
<script setup lang="ts">
import { ref } from "vue";
import Input from "@/components/ui/Input.vue";

const emit = defineEmits<{ apply: [from: number | undefined, to: number | undefined] }>();
const from = ref("");
const to = ref("");

function apply(): void {
  emit("apply", from.value ? Number(from.value) : undefined, to.value ? Number(to.value) : undefined);
}
</script>

<template>
  <div class="mb-3 flex items-center gap-2">
    <Input v-model="from" placeholder="Rok od" class="w-28" />
    <Input v-model="to" placeholder="Rok do" class="w-28" />
    <button
      class="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"
      @click="apply"
    >
      Filtruj
    </button>
  </div>
</template>
```

- [ ] **Step 2: Create Dashboard**

Utwórz `frontend/src/views/Dashboard.vue`:

```vue
<script setup lang="ts">
import { onMounted } from "vue";
import { useDashboardStore } from "@/stores/dashboard";
import Card from "@/components/ui/Card.vue";
import KpiCards from "@/components/KpiCards.vue";
import GameSearch from "@/components/GameSearch.vue";
import GameDetailDrawer from "@/components/GameDetailDrawer.vue";
import MonthlyFilter from "@/components/MonthlyFilter.vue";
import TopRatedChart from "@/components/charts/TopRatedChart.vue";
import GenreStatsChart from "@/components/charts/GenreStatsChart.vue";
import DeveloperChart from "@/components/charts/DeveloperChart.vue";
import PriceRangeChart from "@/components/charts/PriceRangeChart.vue";
import SentimentChart from "@/components/charts/SentimentChart.vue";
import MonthlyReleasesChart from "@/components/charts/MonthlyReleasesChart.vue";

const store = useDashboardStore();

onMounted(() => store.loadAll());
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-6">
    <header class="mb-6">
      <h1 class="text-3xl font-bold tracking-tight">SteamScope</h1>
      <p class="text-sm text-muted-foreground">Eksploracja rynku gier Steam</p>
    </header>

    <div v-if="store.error" class="mb-4 rounded-md border border-border bg-card p-4 text-sm">
      Nie udało się połączyć z API ({{ store.error }}). Czy backend działa na
      <code>VITE_API_BASE_URL</code>?
    </div>

    <KpiCards :overview="store.overview" />

    <div class="mt-6">
      <GameSearch />
    </div>

    <div class="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card title="Najwyżej oceniane gry"><TopRatedChart :data="store.topRated" /></Card>
      <Card title="Statystyki gatunków"><GenreStatsChart :data="store.genreStats" /></Card>
      <Card title="Liderzy deweloperów (przychód)"><DeveloperChart :data="store.developers" /></Card>
      <Card title="Rozkład przedziałów cenowych"><PriceRangeChart :data="store.priceRanges" /></Card>
      <Card title="Sentyment per gatunek"><SentimentChart :data="store.sentiment" /></Card>
      <Card title="Premiery wg miesiąca">
        <MonthlyFilter @apply="(f, t) => store.loadMonthly(f, t)" />
        <MonthlyReleasesChart :data="store.monthly" />
      </Card>
    </div>

    <GameDetailDrawer />
  </div>
</template>
```

- [ ] **Step 3: Create App.vue**

Utwórz `frontend/src/App.vue`:

```vue
<script setup lang="ts">
import Dashboard from "@/views/Dashboard.vue";
</script>

<template>
  <Dashboard />
</template>
```

- [ ] **Step 4: Create main.ts**

Utwórz `frontend/src/main.ts`:

```typescript
import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import "./style.css";

createApp(App).use(createPinia()).mount("#app");
```

- [ ] **Step 5: Type-check + tests**

Run (z `frontend/`): `npx vue-tsc --noEmit && npm run test`
Expected: brak błędów typów; testy vitest PASS.

- [ ] **Step 6: Build smoke test**

Run (z `frontend/`): `npm run build`
Expected: build kończy się sukcesem (`dist/` powstaje).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/Dashboard.vue frontend/src/App.vue frontend/src/main.ts frontend/src/components/MonthlyFilter.vue
git commit -m "feat(frontend): dashboard (KPI + 6 wykresów + wyszukiwarka + drawer)"
```

---

### Task B10: Manualna weryfikacja end-to-end

**Files:** brak — weryfikacja manualna.

- [ ] **Step 1: Uruchom backend**

Run (z katalogu głównego): `uvicorn backend.api.main:app --reload --port 8000`

- [ ] **Step 2: Uruchom frontend (drugi terminal)**

Run (z `frontend/`): `npm run dev`
Otwórz `http://localhost:5173`.

- [ ] **Step 3: Sprawdź zachowanie**

- Na pustej bazie: KPI pokazuje „Brak danych", wykresy pokazują komunikat pustego stanu, brak błędów w konsoli (poza ewentualnym błędem połączenia, jeśli backend nie działa).
- Po uruchomieniu pełnego pipeline'u (`python -m scripts.run_ingestion ...`, `run_etl`, `run_analytics --step views`): odśwież → KPI i wykresy mają dane; wyszukiwarka zwraca gry; klik otwiera drawer ze szczegółami.

> Jeśli coś nie działa — to sygnał do `systematic-debugging`, nie do obejścia.

---

### Task B11: README — sekcja Faza 5

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the section**

Dopisz w `README.md` po sekcji „Faza 4 — API", przed „## Testy":

```markdown
## Faza 5 — Frontend (dashboard Vue 3)

Dashboard prezentuje dane z API. Wymaga Node.js ≥ 18.

```powershell
cd frontend
npm install
Copy-Item .env.example .env   # w razie potrzeby zmień VITE_API_BASE_URL
npm run dev
```

Aplikacja startuje na `http://localhost:5173` i odpytuje API pod adresem
z `VITE_API_BASE_URL` (domyślnie `http://localhost:8000`). Backend musi
działać równolegle (`uvicorn backend.api.main:app --reload --port 8000`).

Na pustej hurtowni dashboard pokazuje stany puste — dane pojawią się po
uruchomieniu pipeline'u Faz 1–3. Testy frontendu: `npm run test` (vitest).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README — Faza 5 (frontend dashboard)"
```

---

## Self-Review (wykonane przy pisaniu planu)

- **Pokrycie spec:** Część A (vw_overview/vw_game_detail + 3 endpointy + testy + README) → Tasks A1–A6. Część B (scaffold, UI, klient, store'y, wykresy, KPI, wyszukiwarka+drawer, dashboard, testy vitest, README, .gitignore) → Tasks B1–B11. Kryteria akceptacji 1–6 pokryte (testy: A5/B3/B7; lint: A5; serwer: A5/B10; dashboard+stany puste: B10; README: A6/B11).
- **Spójność typów:** nazwy pól TS w `types.ts` zgodne z kolumnami widoków SQL (`total_estimated_revenue_usd`, `rating_score`, `games_count`, `sentiment_label`, `price_range_label` itd.); metody `api.*` używane w store'ach istnieją w `client.ts`; `useDashboardStore`/`useGamesStore` używane w komponentach mają zadeklarowane pola.
- **Brak placeholderów:** każdy krok zawiera pełny kod/komendę i oczekiwany wynik.
```
