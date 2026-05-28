# Architektura SteamScope

Dokument opisuje, jak dane płyną przez system, gdzie są kontrakty między
warstwami i dlaczego podjęto kluczowe decyzje projektowe. Dla schematu
hurtowni patrz [`data-model.md`](data-model.md); dla referencji endpointów
patrz [`api.md`](api.md).

## Przepływ danych

```
                         ┌──────────────────────────────────────┐
                         │  data/raw/  (gitignored, surowe pliki)│
                         └──────────────────────────────────────┘
                                          ▲
                            ingestion CLI ┴ (Kaggle/SteamAPI/SteamSpy/scrap)
                                          │
   ┌───────────────────┐                  │
   │ Kaggle dataset    │──── games.csv ───┤
   │ (fronkongames/    │                  │
   │  steam-games-…)   │                  │
   └───────────────────┘                  │
   ┌───────────────────┐                  │
   │ Steam Web API     │──── {appid}.json ┤  scripts/run_ingestion.py
   └───────────────────┘                  │
   ┌───────────────────┐                  │
   │ SteamSpy API      │──── {appid}.json ┤
   └───────────────────┘                  │
   ┌───────────────────┐                  │
   │ Strony recenzji   │──── {appid}.html ┘
   │ (Steam Community) │
   └───────────────────┘

                                          ▼
                         ┌──────────────────────────────────────┐
                         │  db/steam_warehouse.db  (SQLite)      │
                         │                                       │
                         │  stg_kaggle, stg_steam_api,           │
                         │  stg_steamspy, stg_reviews            │
                         │           │                           │
                         │           ▼ ETL (transformacje)       │
                         │  dim_genre, dim_developer, …          │
                         │  fact_games, fact_reviews             │
                         │  bridge_game_genre, bridge_…          │
                         │           │                           │
                         │           ▼ widoki analityczne        │
                         │  vw_overview, vw_top_rated_games, …   │
                         └──────────────────────────────────────┘
                                          ▲
                                          │ czyta widoki (read-only)
                         ┌──────────────────────────────────────┐
                         │  FastAPI  (backend.api)               │
                         │  /api/overview, /api/games, …         │
                         └──────────────────────────────────────┘
                                          ▲
                                          │ HTTP (CORS :5173)
                         ┌──────────────────────────────────────┐
                         │  Frontend Vue 3 (frontend/)           │
                         │  Pinia stores → ECharts wykresy + UI  │
                         └──────────────────────────────────────┘
```

## Warstwy i ich kontrakty

### Ingestion (`backend/ingestion/`)

**Zadanie:** pobrać surowe dane z 4 źródeł do `data/raw/`.

**Wejście:** sieć (Kaggle API, Steam Web API, SteamSpy API, scrap HTML),
plus klucze w `.env` (`KAGGLE_USERNAME`, `KAGGLE_KEY`).

**Wyjście:** pliki na dysku z formatami źródłowymi (CSV / JSON / HTML).
Idempotentne — kolejne uruchomienie pomija pliki obecne na dysku, chyba
że `--force`.

**Rate-limity:**
- Steam API: ~1 req/1.5 s (`backend/config.py:steam_api_rate_limit_seconds`).
- SteamSpy: ~1 req/1 s.
- Scrap recenzji: ~1 req/2 s.

**Brak dotyku DB.** Ta warstwa NIE wie nic o hurtowni — jest sterylną
warstwą pobrania surowizny. Pozwala to przebudowywać schemat hurtowni
bez ponownego pobierania ~400 MB Kaggle CSV.

### ETL (`backend/etl/`)

**Zadanie:** wczytać `data/raw/` do hurtowni w trzech etapach (staging
→ dimensions → facts).

**Wejście:** pliki w `data/raw/`, schemat z `backend/warehouse/schema.sql`.

**Wyjście:** wypełnione tabele w `db/steam_warehouse.db`.

**Idempotencja:** `staging` używa `if_exists='replace'` (drop + recreate);
`load_fact_games` używa `INSERT OR REPLACE` po PK; bridges `INSERT OR IGNORE`.
Można uruchamiać wielokrotnie bez duplikatów.

**Dwa niuanse danych warte uwagi (z komentarzami w kodzie):**

1. **Kaggle CSV ma sklejony nagłówek.** `fronkongames/steam-games-dataset`
   ma w nagłówku 39 nazw kolumn, ale wiersze danych mają 40 pól (twórca
   zlepił „Discount" i „DLC count" przez brakujący przecinek). `stage_kaggle`
   wykrywa ten konkretny case i nadpisuje nagłówek pełną 40-kolumnową listą.
   Inne (zdrowe) pliki czytane są bez modyfikacji ([staging.py:60-80](../backend/etl/staging.py)).

2. **`estimated_owners` z SteamSpy, nie z Kaggle.** Kaggle podaje przedział
   tekstowy (`"10000000 - 20000000"`); SteamSpy daje pojedynczą liczbę
   midpoint. `_read_staged_games` świadomie wybiera SteamSpy
   ([load_facts.py:40](../backend/etl/load_facts.py)). Konsekwencja:
   `estimated_owners` jest NULL dla wszystkich gier nie objętych
   ingestionem SteamSpy — domyślny pipeline ingestion fetchuje SteamSpy
   tylko dla appidów z `--appids`, więc tylko one mają niezerowy
   `estimated_owners`/`estimated_revenue_usd`/`sentiment_label`.

**Sentyment:** [`backend/etl/sentiment.py`](../backend/etl/sentiment.py)
używa VADER (vaderSentiment), uśrednia compound score per gra, mapuje
na 5 koszyków (`Negative` / `Mostly Negative` / `Mixed` / `Positive`
/ `Very Positive`) — patrz `SENTIMENT_BUCKETS`. Wyzwalany tylko dla gier
ze zescrapowanymi recenzjami.

### Warehouse + widoki (`backend/warehouse/`)

**Zadanie:** trwałe przechowanie + warstwa wynikowa.

- [`schema.sql`](../backend/warehouse/schema.sql) — DDL star schemy.
- [`views.sql`](../backend/warehouse/views.sql) — 8 widoków analitycznych
  (`vw_*`). Każdy zaczyna się od `DROP VIEW IF EXISTS`, więc `init_views()`
  jest idempotentny — można aktualizować definicje bez resetu hurtowni.

**Połączenia:** [`connect()`](../backend/warehouse/connection.py) tworzy
`sqlite3.Connection` z:
- `PRAGMA foreign_keys = ON` (SQLite domyślnie wyłącza FK).
- `check_same_thread=False` — FastAPI woła dependency w innym wątku niż
  handler (asyncio threadpool); połączenie jest per-request i zamykane
  w `finally`, więc to bezpieczne.

Patrz [`data-model.md`](data-model.md).

### Analytics (`backend/analytics/`)

**Zadanie:** eksport widoków do CSV/XLSX dla narzędzi BI.
[`backend/analytics/exports.py`](../backend/analytics/exports.py) używa
`pandas.read_sql` na każdy widok i `to_csv` / `openpyxl`. Nie jest częścią
ścieżki API ↔ frontend — to osobny side-channel dla zewnętrznych odbiorców.

### API (`backend/api/`)

**Zadanie:** udostępnić warstwę wynikową przez REST.

**Wzorzec:** każdy endpoint queryuje **stałą nazwę widoku** (`_VIEW_XXX = "vw_..."`).
Dane użytkownika (`q`, `game_id`, limit/offset/year_from/year_to) trafiają
**wyłącznie jako parametry bound queries** — brak f-stringowej interpolacji
danych w SQL. Powierzchnia na SQL injection nie istnieje.

**Connection lifecycle:** dependency `get_db()`
([dependencies.py](../backend/api/dependencies.py)) otwiera nowe połączenie
per-request i zamyka w `finally`. Bez pula — SQLite ma niski koszt
otwarcia połączenia, a krótkotrwałość zapobiega problemom z blokowaniem
przy równoległym ETL.

**Walidacja:** używamy `fastapi.Query` z `ge`/`le`/typami; FastAPI zwraca
422 dla niepoprawnego inputu, 404 ręcznie przez `HTTPException`.

**CORS:** `backend/api/main.py:_CORS_ORIGINS` zawiera `http://localhost:5173`
i `127.0.0.1:5173`. Tylko `GET`. Bez auth — API jest read-only.

### Frontend (`frontend/`)

**Zadanie:** wizualizować dane z API.

**Architektura warstw:**

- `src/api/` — typowany klient REST (`client.ts`) + interfejsy odpowiedzi
  (`types.ts`). Wszystkie wywołania API są typowane — TypeScript wymusza
  zgodność z kontraktami backendu.
- `src/stores/` — dwa store'y Pinia:
  - `useDashboardStore` — read-only dane z 7 endpointów (`/api/overview`
    + 6 widoków). `loadAll()` strzela `Promise.all` ze wszystkimi.
  - `useGamesStore` — interaktywny: query, wyniki wyszukiwania, wybrana
    gra, stan drawera.
- `src/components/charts/` — 6 wykresów ECharts + wrapper `BaseChart.vue`
  obsługujący stany `loading` / `empty`.
- `src/components/` — UI nie-wykresowe (`KpiCards`, `GameSearch`,
  `GameDetailDrawer`, `MonthlyFilter`).
- `src/components/ui/` — prymitywy w stylu shadcn-vue (`Card`, `Input`)
  + helper `cn()` na `clsx` + `tailwind-merge`.
- `src/views/Dashboard.vue` — orkiestracja: `onMounted` woła `loadAll()`,
  przekazuje `store.loading` do KPI i wszystkich wykresów.

**Komunikacja z API:** `fetch` bezpośrednio do `VITE_API_BASE_URL`
(domyślnie `http://localhost:8000`). Brak proxy Vite — CORS na backendzie
załatwia sprawę.

**Stany ładowania:** każda karta dashboardu ma 3 stany:
1. `loading=true && empty` → animowany skeleton (`animate-pulse`).
2. `loading=false && empty` → komunikat „Brak danych — uruchom pipeline…".
3. `loading=false && !empty` → render wykresu.

## Kluczowe decyzje projektowe

### Dlaczego SQLite, a nie Postgres/DuckDB

- **Zero setupu:** projekt edukacyjny / portfolio. Klon repo + `pip install`
  daje gotową hurtownię — bez Dockera, bez serwera bazy.
- **120 tys. wierszy:** SQLite obsługuje to z głowy. Cały dataset
  + indeksy + bridges + recenzje mieści się w ~150 MB pliku.
- **WAL nie potrzebny:** API jest read-only, ETL działa lokalnie
  pojedynczym procesem. Pojedynczy plik DB wystarcza.

### Dlaczego star schema

Standardowa decyzja dla analityki. Wymiary (`dim_genre`, `dim_developer`,
itp.) są małe i powolnie zmienne. Fakty (`fact_games`, `fact_reviews`)
są wąskimi tabelami z FK do wymiarów — pozwalają na szybkie agregacje
z `GROUP BY dim.<atrybut>`. Bridges (`bridge_game_genre`) obsługują
relacje M:N (gra może mieć wiele gatunków).

### Dlaczego widoki SQL, a nie zapytania w API

- **Centralizacja logiki:** definicja KPI mieszka w SQL obok schematu,
  nie rozsiana po Pythonie. Modyfikacja `vw_genre_stats` nie wymaga
  zmiany kodu API.
- **Powierzchnia ataku = 0:** nazwy widoków są stałymi modułowymi
  w routerach — backend nigdy nie interpoluje stringów użytkownika
  w SQL.
- **Eksporty BI dostają identyczny output co API:** `analytics/exports.py`
  i routery FastAPI queryują te same widoki — zero rozjazdu między
  „dla narzędzia" i „dla dashboardu".

### Dlaczego osobna warstwa ingestion (a nie ETL od razu z sieci)

Pobranie Kaggle to ~400 MB i kilka minut. Rate-limity Steam/SteamSpy
mogą blokować eksperymenty z transformacjami. Trzymając `data/raw/` jako
checkpoint, ETL można przebudowywać dziesiątki razy bez ponownego
pobierania.

### Dlaczego frontend strzela bezpośrednio do API zamiast przez proxy Vite

Proxy Vite byłoby kolejnym pośrednikiem, który trzeba konfigurować
i utrzymywać. CORS na backendzie (`_CORS_ORIGINS` w `main.py`) załatwia
sprawę w 5 linijkach. `VITE_API_BASE_URL` jako env var pozwala wskazać
inny host bez zmiany kodu.

### Dlaczego Pinia, a nie sam composition API

`useDashboardStore` agreguje stan z 7 zapytań i jest konsumowany przez
~10 komponentów. Pinia daje:
- Jeden punkt prawdy (komponenty nie duplikują state'u).
- `Promise.all` w `loadAll()` z jednoczesną aktualizacją `loading` i `error`.
- Lekka separacja interaktywnego store'a wyszukiwania od read-only
  store'a dashboardu.

## Testy

- **Backend (`pytest`, 232 testy):** każda warstwa ma osobny `test_*`
  pakiet. Fixtura `views_conn` ([tests/conftest.py](../tests/conftest.py))
  buduje pełną hurtownię od zera z fixture'ów w `tests/fixtures/`
  — testy API i widoków używają tej samej, deterministycznej małej
  hurtowni.
- **Frontend (`vitest`, 5 testów):** unit testy klienta API (mockowany
  `fetch`) i komponentu `KpiCards`. `vue-tsc --noEmit` sprawdza
  zgodność typów end-to-end.
- **Linter:** `ruff check backend tests scripts`.

## Co nie istnieje, a planowane jest

- **ML (`backend/ml/`)** — predykcja ocen Random Forest. Sentyment z VADER
  jest już zaimplementowany w ETL ([sentiment.py](../backend/etl/sentiment.py)),
  ale predykcja jeszcze nie.
- **Build produkcyjny frontu z deployem** — obecnie dev only.
- **Autentykacja API** — nie jest planowana; dane są publiczne (Steam +
  Kaggle), API read-only.
