# Steam Analytics

System analityczny umożliwiający eksplorację rynku gier na platformie Steam
(~100 tys. tytułów). Pełen pipeline: ingestion z 4 źródeł (CSV/JSON/HTML)
→ ETL → hurtownia w schemacie gwiazdy (SQLite) → warstwa wynikowa
(widoki SQL, eksporty CSV/XLSX) → backend (FastAPI) → dashboard (Vue 3
+ shadcn-vue + ECharts). Rozszerzenie: predykcja ocen (Random Forest)
i analiza sentymentu recenzji (VADER).


## Stos technologiczny

**Backend / ETL / ML:**
- Python 3.11+
- pandas, pyarrow, requests, BeautifulSoup4
- SQLAlchemy + SQLite
- scikit-learn, NLTK (VADER)
- FastAPI + uvicorn

**Frontend:**
- Vue 3 + Vite + TypeScript
- Pinia (state)
- Tailwind CSS + shadcn-vue (komponenty UI)
- Apache ECharts (wizualizacje)

**Testy:** pytest, vitest.

## Struktura katalogów

```
.
├── data/
│   ├── raw/         # surowe dane (gitignored)
│   ├── processed/   # po ETL (gitignored)
│   └── exports/     # CSV/XLSX wynikowe
├── db/              # SQLite (plik gitignored)
├── backend/
│   ├── ingestion/   # wczytywanie z 4 źródeł
│   ├── etl/         # transformacje
│   ├── warehouse/   # DDL star schemy + widoki SQL
│   ├── analytics/   # eksporty
│   ├── ml/          # sentyment + predykcja
│   └── api/         # FastAPI
├── frontend/        # Vue 3 dashboard
├── notebooks/       # eksploracja, prototypowanie
├── scripts/         # orkiestracja pipeline'u
└── tests/
```

## Instalacja środowiska

```powershell
python -m venv .venv
# Jeśli aktywacja jest zablokowana przez PowerShell ExecutionPolicy:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
# Otwórz .env i zastąp KAGGLE_USERNAME / KAGGLE_KEY rzeczywistymi danymi
# (token: https://www.kaggle.com/settings/account → Create New Token)
```

## Faza 1 — Ingestion

Pipeline ingestion pobiera dane z 4 źródeł do `data/raw/`. Wszystkie kroki są idempotentne — kolejne uruchomienie pomija pliki, które już zostały pobrane (chyba że dodasz `--force`).

### Pojedyncze źródła

```powershell
# Kaggle (wymaga .env z kluczem)
python -m scripts.run_ingestion --source kaggle

# Steam Web API (rate-limited do ~1 req/1.5s)
python -m scripts.run_ingestion --source steam --appids 70,220,440,400

# SteamSpy API
python -m scripts.run_ingestion --source steamspy --appids 70,220,440,400

# Scrapowane recenzje (BeautifulSoup)
python -m scripts.run_ingestion --source reviews --appids 70,220,440,400
```

### Pełny przebieg

Uwaga: `--appids` jest wymagany dla `--source all` (potrzebny dla kroków Steam / SteamSpy / Reviews).

```powershell
python -m scripts.run_ingestion --source all --appids 70,220,440,400
```

### Wymuszenie ponownego pobrania

```powershell
python -m scripts.run_ingestion --source steam --appids 70 --force
```

### Logi

Każde uruchomienie zapisuje log do `logs/ingestion.log` (plik gitignorowany).

## Faza 2 — ETL

Pipeline ETL ładuje dane z `data/raw/` do hurtowni SQLite w schemacie gwiazdy (`db/steam_warehouse.db`). Uruchomienie sterowane jest flagą `--step`:

- `schema` — tworzy DDL hurtowni (tabele wymiarów, faktów i bridge).
- `staging` — wczytuje surowe pliki Kaggle/Steam API/SteamSpy/Reviews do tabel `stg_*`.
- `dimensions` — ładuje wymiary (`dim_genre`, `dim_developer`, `dim_platform`, `dim_price_range`, `dim_release_period`, `dim_sentiment`, `dim_date`).
- `facts` — ładuje `fact_games`, `fact_reviews` oraz tabele `bridge_*`.
- `all` — pełny przebieg (schema → staging → dimensions → facts).

```powershell
python -m scripts.run_etl --step all
```

Pipeline jest idempotentny — ponowne uruchomienie aktualizuje hurtownię bez duplikatów. Log uruchomienia trafia do `logs/etl.log`.

## Faza 3 — Warstwa wynikowa

Warstwa wynikowa udostępnia analityczne widoki SQL nad hurtownią oraz eksporty CSV/XLSX do `data/exports/` dla narzędzi BI i dashboardu.

| Widok | Opis |
|---|---|
| `vw_top_rated_games` | Ranking gier z co najmniej 10 recenzjami, posortowany malejąco po `rating_score`. |
| `vw_genre_stats` | Statystyki per gatunek (liczba gier, średnia ocena, średnia cena, średnia liczba właścicieli). |
| `vw_developer_leaderboard` | Liderzy wśród deweloperów wg szacunkowego przychodu, z klasą (indie/AA/AAA). |
| `vw_price_range_distribution` | Rozkład gier po przedziałach cenowych. |
| `vw_sentiment_per_genre` | Rozkład sentymentu (na podstawie recenzji) per gatunek. |
| `vw_monthly_releases` | Liczba premier per rok/miesiąc wraz ze średnią oceną. |

```powershell
# tworzy widoki w hurtowni
python -m scripts.run_analytics --step views

# eksport każdego widoku do osobnego pliku CSV (data/exports/csv/)
python -m scripts.run_analytics --step export-csv

# eksport wszystkich widoków do jednego XLSX (data/exports/steam_analytics.xlsx)
# — każdy widok jako osobny arkusz
python -m scripts.run_analytics --step export-xlsx

# pełny przebieg: widoki + CSV + XLSX
python -m scripts.run_analytics --step all

# opcjonalnie: zmień katalog wyjściowy
python -m scripts.run_analytics --step all --out-dir D:\reports\steam
```

Warstwa jest idempotentna — można uruchamiać wielokrotnie. Log uruchomienia trafia do `logs/analytics.log`.

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

## Testy

```powershell
pytest                  # wszystkie testy
pytest -v --cov=backend # z pokryciem
ruff check backend tests scripts  # linter
```
