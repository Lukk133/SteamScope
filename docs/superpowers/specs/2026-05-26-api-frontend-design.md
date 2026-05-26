# Spec: domknięcie API (Faza 4) + frontend dashboard (Faza 5)

Data: 2026-05-26

## Cel

Doprowadzić SteamScope do stanu „ready to run": działające API z kompletem
endpointów pod dashboard oraz frontend Vue 3 prezentujący dane z hurtowni.
Po uruchomieniu pipeline'u ingestion/ETL przez użytkownika (ma klucz Kaggle)
dashboard pokazuje realne dane; przed tym — czytelne stany puste.

## Kontekst (stan wyjściowy)

- Fazy 1–3 gotowe: ingestion, ETL (star schema, SQLite), warstwa wynikowa (6 widoków).
- Faza 4 w toku: szkielet FastAPI (`backend/api/`), endpointy `/`, `/api/health`
  i 6 endpointów nad widokami (`/api/views/*`) z testami i CORS dla `:5173`.
- Brak: dodatkowych endpointów (overview, games), całego frontendu (`frontend/`).
- `fact_games.game_id` = klucz główny gry (Steam appid). Bogaty zestaw metryk
  (cena, ocena, recenzje, właściciele, przychód, playtime).

## Zakres

### Część A — Nowe endpointy API (Faza 4 cd.)

Trzymamy istniejący wzorzec: zapytania po **nazwanych widokach SQL** (nazwy to
stałe modułowe; dane użytkownika trafiają wyłącznie jako parametry zapytań —
brak powierzchni na SQL injection).

**Nowe widoki w `backend/warehouse/views.sql`:**

- `vw_overview` — jeden wiersz agregatów:
  `total_games`, `total_developers`, `total_genres`, `avg_rating`,
  `avg_price_usd`, `total_estimated_owners`, `total_reviews`,
  `total_estimated_revenue_usd`.
- `vw_game_detail` — `fact_games` LEFT JOIN ze wszystkimi wymiarami
  (genre, developer, price_range, release_period, sentiment) + wszystkie
  metryki gry. Kolumny: `game_id`, `name`, `genre`, `developer`,
  `developer_class`, `price_range_label`, `release_year`, `release_month`,
  `release_month_name`, `season`, `sentiment_label`, `price_usd`,
  `rating_score`, `review_count`, `positive_review_count`,
  `negative_review_count`, `estimated_owners`, `estimated_revenue_usd`,
  `release_date`, `playtime_avg_hours`.

**Nowe routery:**

- `backend/api/routers/overview.py` → `GET /api/overview`
  - Zwraca pojedynczy obiekt z `vw_overview` (pierwszy/jedyny wiersz).
- `backend/api/routers/games.py`
  - `GET /api/games?q=&limit=&offset=` → `{items, total}`.
    - `q` (opcjonalne): filtr po nazwie, `WHERE name LIKE ?` (parametr `%q%`),
      case-insensitive (SQLite `LIKE` jest domyślnie case-insensitive dla ASCII).
    - `limit`: `Query(50, ge=1, le=200)`, `offset`: `Query(0, ge=0)` — jak w
      istniejących endpointach.
    - `total` = liczba wierszy po filtrze (przed paginacją).
    - Sortowanie: `rating_score DESC NULLS LAST, review_count DESC`.
  - `GET /api/games/{game_id}` → pełny obiekt z `vw_game_detail`
    (`WHERE game_id = ?`) lub **404** (`HTTPException`) gdy brak.

Oba routery rejestrowane w `create_app()` obok `views_router`.

**Testy (Część A):**

- `tests/test_api/test_overview.py`: 200, obecność kluczy KPI, typy.
- `tests/test_api/test_games.py`: lista (items+total), filtr `q`, paginacja
  (limit/offset), walidacja (limit poza zakresem → 422), detal istniejącej gry,
  404 dla nieistniejącej.
- `tests/test_warehouse/test_views.py`: nowe widoki istnieją i mają oczekiwane
  kolumny; `vw_overview` zwraca dokładnie 1 wiersz.
- Aktualizacja `test_views.py` (OpenAPI) o nowe ścieżki, jeśli dotyczy.

### Część B — Frontend (Faza 5)

Katalog `frontend/`. Stack zgodny z README: **Vite + Vue 3 + TypeScript**,
**Tailwind CSS + shadcn-vue**, **Pinia**, **Apache ECharts**, testy **vitest**.

**Struktura:**

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js / postcss.config.js
├── tsconfig*.json
├── components.json            # konfiguracja shadcn-vue
├── .env.example               # VITE_API_BASE_URL=http://localhost:8000
└── src/
    ├── main.ts
    ├── App.vue
    ├── api/
    │   ├── client.ts          # typowany fetch wrapper (baza z VITE_API_BASE_URL)
    │   └── types.ts           # interfejsy odpowiedzi API
    ├── stores/
    │   ├── dashboard.ts        # useDashboardStore: overview + 6 widoków, loading/error
    │   └── games.ts            # useGamesStore: query, wyniki, wybrana gra, drawer
    ├── components/
    │   ├── ui/                 # komponenty shadcn-vue (card, button, input, table...)
    │   ├── charts/
    │   │   ├── BaseChart.vue       # wrapper ECharts (resize, opcje)
    │   │   ├── TopRatedChart.vue
    │   │   ├── GenreStatsChart.vue
    │   │   ├── DeveloperChart.vue
    │   │   ├── PriceRangeChart.vue
    │   │   ├── SentimentChart.vue
    │   │   └── MonthlyReleasesChart.vue
    │   ├── KpiCards.vue
    │   ├── GameSearch.vue
    │   └── GameDetailDrawer.vue
    └── views/
        └── Dashboard.vue
```

**Layout dashboardu (jedna przewijana strona):**

1. Nagłówek „SteamScope".
2. Rząd kafelków KPI (`/api/overview`).
3. Wyszukiwarka gier (`/api/games?q=`); klik w wynik → drawer ze szczegółami
   (`/api/games/{id}`).
4. Siatka kart z wykresami (po jednym na widok):
   - Top oceniane — bar (poziomy, top N po `rating_score`).
   - Statystyki gatunków — bar (`games_count` / `avg_rating`).
   - Deweloperzy — bar (`total_estimated_revenue_usd`).
   - Przedziały cenowe — pie (`games_count` per `price_range_label`).
   - Sentyment/gatunek — stacked bar (`sentiment_label` per `genre`).
   - Premiery wg miesiąca — line (`games_count` w czasie) + filtr zakresu lat
     (przekazywany do `/api/views/monthly-releases?year_from=&year_to=`).

**Komunikacja:** klient `fetch` strzela bezpośrednio do `VITE_API_BASE_URL`
(CORS na backendzie już skonfigurowany dla `:5173`). Bez proxy Vite.

**Stany:** każda sekcja ma `loading` (skeleton/spinner) i `empty`
(czytelny komunikat „brak danych") — dashboard nie wywala się na pustej bazie.

**Testy (vitest):** klient API (budowa URL, parsowanie odpowiedzi z mockowanym
`fetch`) oraz ≥1 komponent (np. `KpiCards` renderuje wartości, stan pusty).

### Część C — „Ready to run" i dokumentacja

- Backend: `uvicorn backend.api.main:app --reload`.
- Frontend: `cd frontend && npm install && npm run dev` → `http://localhost:5173`.
- README: nowa sekcja **Faza 4** (lista endpointów) i **Faza 5** (uruchomienie
  frontendu, zmienna `VITE_API_BASE_URL`).
- `.gitignore`: dodać `frontend/node_modules`, `frontend/dist`.

## Poza zakresem (YAGNI)

- Rozszerzenie ML (Random Forest) — osobna faza, nie tutaj.
- Auth/uwierzytelnianie API (publiczny, read-only).
- Build produkcyjny / deployment frontendu (tylko tryb dev „do odpalenia").
- Generowanie danych syntetycznych — użytkownik uruchamia realny ingestion.

## Kryteria akceptacji

1. `pytest` zielony, w tym nowe testy API i widoków.
2. `ruff check backend tests scripts` bez błędów.
3. `uvicorn backend.api.main:app` startuje; `/api/overview`, `/api/games`,
   `/api/games/{id}` zwracają poprawne odpowiedzi (200 / 404).
4. `npm run dev` w `frontend/` startuje bez błędów; dashboard renderuje się
   z czytelnymi stanami pustymi na pustej bazie i z danymi po przebiegu ETL.
5. `npm run test` (vitest) zielony.
6. README opisuje uruchomienie obu warstw.
```
