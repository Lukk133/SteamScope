# SteamScope

System analityczny do eksploracji rynku gier na platformie Steam (~120 tys.
tytułów). Pełny pipeline: **ingestion** z 4 źródeł (Kaggle CSV / Steam Web API
/ SteamSpy / scrap recenzji) → **ETL** → **hurtownia** w schemacie gwiazdy
(SQLite) → **warstwa wynikowa** (widoki SQL, eksporty CSV/XLSX) → **API**
(FastAPI) → **dashboard** (Vue 3 + Tailwind + shadcn-vue + ECharts).
Rozszerzenie: predykcja ocen (Random Forest) i analiza sentymentu recenzji
(VADER).

## Stos technologiczny

**Backend / ETL / ML:**
- Python 3.11+
- pandas, pyarrow, requests, BeautifulSoup4
- SQLAlchemy + SQLite
- scikit-learn, vaderSentiment
- FastAPI + uvicorn

**Frontend:**
- Vue 3 + Vite + TypeScript
- Pinia (state)
- Tailwind CSS + shadcn-vue (komponenty UI)
- Apache ECharts (wizualizacje)

**Testy:** pytest (backend), vitest (frontend), ruff (linter).

## Wymagania

- **Python 3.11+** (testowane na 3.11 i 3.13).
- **Node.js ≥ 18** + npm.
- **Konto Kaggle** z wygenerowanym tokenem API
  ([Kaggle Settings → Create New Token](https://www.kaggle.com/settings/account)).
  Bez tokenu można uruchomić cały stos „na sucho" — backend i dashboard
  ruszą, ale pokażą stany puste, dopóki nie uruchomisz ingestion.
- Windows / macOS / Linux. Przykłady poleceń są w PowerShell; pod bashem
  zamień `Copy-Item` na `cp`, a `.venv\Scripts\Activate.ps1` na
  `source .venv/bin/activate`.

## Szybki start

Po sklonowaniu repozytorium:

```powershell
# 1. Backend: środowisko + zależności
python -m venv .venv
.venv\Scripts\Activate.ps1
# (jeśli PowerShell blokuje aktywację: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
pip install -e ".[dev]"

# 2. Konfiguracja Kaggle (opcjonalna — bez niej ingestion się nie odpali,
#    ale reszta stosu zadziała ze stanami pustymi)
Copy-Item .env.example .env
# Otwórz .env i wpisz KAGGLE_USERNAME / KAGGLE_KEY

# 3. Pipeline danych — pobierz, załaduj, zbuduj widoki
#    (Kaggle ~400 MB CSV; Steam/SteamSpy/reviews przez rate-limit ~3 min)
python -m scripts.run_ingestion --source all --appids 70,220,440,400
python -m scripts.run_etl --step all
python -m scripts.run_analytics --step views

# 4. Backend — REST API na :8000
uvicorn backend.api.main:app --reload --port 8000
```

W **drugim terminalu**:

```powershell
# 5. Frontend — dashboard na :5173
cd frontend
npm install
Copy-Item .env.example .env       # ustawia VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Otwórz **http://localhost:5173** — zobaczysz dashboard z KPI, wykresami
i wyszukiwarką gier. Backend Swagger: **http://localhost:8000/docs**.

### Bogatszy dashboard (opcjonalnie)

Domyślny ingestion fetchuje dane „głębokie" (SteamSpy `estimated_owners`
+ zescrapowane recenzje) tylko dla appidów podanych w `--appids`. Wykresy
**Liderzy deweloperów** i **Sentyment per gatunek** pokażą tylko te gry.
Żeby je rozbudować, dodaj więcej appidów:

```powershell
# Wyciąga top 50 appidów po liczbie rekomendacji z hurtowni
python -c "from backend.warehouse.connection import connect; c=connect(); print(','.join(str(r[0]) for r in c.execute('SELECT appid FROM stg_kaggle WHERE recommendations IS NOT NULL ORDER BY CAST(recommendations AS INTEGER) DESC LIMIT 50')))"
# Skopiuj listę → następnie:
python -m scripts.run_ingestion --source steamspy --appids <wklejone>
python -m scripts.run_ingestion --source reviews  --appids <wklejone>
python -m scripts.run_etl --step all
```

## Struktura katalogów

```
.
├── data/
│   ├── raw/         # surowe dane (gitignored)
│   ├── processed/   # po ETL (gitignored)
│   └── exports/     # CSV/XLSX wynikowe
├── db/              # SQLite (plik gitignored)
├── backend/
│   ├── ingestion/   # 4 źródła danych
│   ├── etl/         # transformacje + sentyment
│   ├── warehouse/   # DDL star schemy + widoki SQL
│   ├── analytics/   # eksporty CSV/XLSX
│   ├── ml/          # (planowane) predykcja ocen
│   └── api/         # FastAPI (routery, dependencies)
├── frontend/        # Vue 3 dashboard
│   └── src/
│       ├── api/         # typowany klient REST
│       ├── stores/      # Pinia (dashboard + games)
│       ├── components/  # UI + wykresy
│       └── views/       # Dashboard.vue
├── docs/            # dokumentacja architektury i API
├── notebooks/       # eksploracja, prototypowanie
├── scripts/         # orkiestracja pipeline'u (CLI)
└── tests/           # pytest backend
```

## Fazy (referencja)

Każda faza ma osobny CLI; można je uruchamiać niezależnie i wielokrotnie
(każdy krok jest idempotentny).

### Faza 1 — Ingestion

```powershell
# Kaggle (wymaga .env z kluczem)
python -m scripts.run_ingestion --source kaggle

# Steam Web API (rate-limited ~1 req/1.5 s)
python -m scripts.run_ingestion --source steam --appids 70,220,440,400

# SteamSpy API
python -m scripts.run_ingestion --source steamspy --appids 70,220,440,400

# Scrapowane recenzje (BeautifulSoup, ~2 s/appid)
python -m scripts.run_ingestion --source reviews --appids 70,220,440,400

# Pełny przebieg
python -m scripts.run_ingestion --source all --appids 70,220,440,400

# Wymuszenie ponownego pobrania (pomija cache na dysku)
python -m scripts.run_ingestion --source steam --appids 70 --force
```

Log uruchomienia: `logs/ingestion.log`.

### Faza 2 — ETL

Wczytuje surowe pliki do staging tables (`stg_*`), buduje wymiary,
fakty i bridge-tabele:

- `schema` — DDL hurtowni (wymiary + fakty + bridges).
- `staging` — `stg_kaggle`, `stg_steam_api`, `stg_steamspy`, `stg_reviews`.
- `dimensions` — wszystkie `dim_*`.
- `facts` — `fact_games`, `fact_reviews`, `bridge_*`.
- `parquet` — zrzut staging tables do plików kolumnowych
  w `data/processed/<table>.parquet` (do dalszej analizy w notebookach
  lub narzędziach BI bez podłączania się do SQLite).
- `all` — pełny przebieg (włącznie z parquet na końcu).

```powershell
python -m scripts.run_etl --step all
```

Log: `logs/etl.log`.

### Faza 3 — Warstwa wynikowa

| Widok | Opis |
|---|---|
| `vw_overview` | Jednowierszowy agregat KPI (liczba gier/dev/gatunków, śr. ocena, sumy). |
| `vw_top_rated_games` | Ranking gier z co najmniej 10 recenzjami. |
| `vw_genre_stats` | Statystyki per gatunek (liczba gier, śr. ocena, śr. cena…). |
| `vw_developer_leaderboard` | Liderzy deweloperów wg szac. przychodu (z klasą indie/AA/AAA). |
| `vw_price_range_distribution` | Rozkład gier po przedziałach cenowych. |
| `vw_sentiment_per_genre` | Rozkład sentymentu (z recenzji) per gatunek. |
| `vw_monthly_releases` | Liczba premier per rok/miesiąc + śr. ocena. |
| `vw_game_detail` | Pełny rekord gry (fakt + wszystkie wymiary). |

```powershell
python -m scripts.run_analytics --step views        # tylko widoki
python -m scripts.run_analytics --step export-csv   # CSV per widok
python -m scripts.run_analytics --step export-xlsx  # jeden XLSX (arkusz/widok)
python -m scripts.run_analytics --step all          # widoki + CSV + XLSX
python -m scripts.run_analytics --step all --out-dir D:\reports\steam
```

Log: `logs/analytics.log`.

### Faza 4 — API (FastAPI)

```powershell
uvicorn backend.api.main:app --reload --port 8000
```

Dokumentacja interaktywna (Swagger): **http://localhost:8000/docs**.

| Endpoint | Opis |
|---|---|
| `GET /` | Metadane aplikacji. |
| `GET /api/health` | Status zdrowia (monitoring/smoke-test). |
| `GET /api/overview` | KPI nagłówka dashboardu. |
| `GET /api/games?q=&limit=&offset=` | Lista/wyszukiwanie gier (filtr nazwy, paginacja). |
| `GET /api/games/{game_id}` | Szczegóły gry (404, gdy brak). |
| `GET /api/views/top-rated-games?limit=&offset=` | Ranking gier. |
| `GET /api/views/genre-stats` | Statystyki per gatunek. |
| `GET /api/views/developer-leaderboard?limit=&offset=` | Liderzy deweloperów. |
| `GET /api/views/price-range-distribution` | Rozkład cen. |
| `GET /api/views/sentiment-per-genre` | Sentyment per gatunek. |
| `GET /api/views/monthly-releases?year_from=&year_to=` | Premiery wg miesiąca. |

CORS włączony dla `http://localhost:5173`.

### Faza 5 — Frontend (Vue 3)

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev          # → http://localhost:5173
npm run build        # produkcyjny build (dist/)
npm run test         # vitest
```

`VITE_API_BASE_URL` w `frontend/.env` ustawia adres API
(domyślnie `http://localhost:8000`). Dashboard wymaga uruchomionego
backendu równolegle. Na pustej hurtowni pokazuje **skeleton loadery**
podczas pierwszego ładowania i stany puste po nieudanym fetchu.

## Testy

```powershell
# Backend
pytest                            # wszystkie
pytest -v --cov=backend           # z pokryciem
ruff check backend tests scripts  # linter

# Frontend (z katalogu frontend/)
npm run test                      # vitest
npx vue-tsc --noEmit              # type-check
```

## Rozwiązywanie problemów

**„No module named 'requests'" / „No module named 'fastapi'":** masz aktywne
niewłaściwe środowisko Pythona. Sprawdź `python -c "import sys; print(sys.executable)"` —
musi pokazywać `.venv/Scripts/python.exe` z projektu. Jeśli nie: aktywuj
venv (`.venv\Scripts\Activate.ps1`) lub wywołuj jawnie
`.\.venv\Scripts\python.exe -m scripts.run_ingestion …`.

**`db is locked` przy ETL z uruchomionym uvicorn:** SQLite blokuje przy
zapisie, kiedy ktoś trzyma otwarte połączenie. Zatrzymaj backend
(`Ctrl+C` w terminalu z uvicorn), odpal ETL, ponownie uruchom backend.

**`UnicodeEncodeError: 'charmap' codec` w logach ETL/ingestion (Polski
Windows):** błąd kosmetyczny przy logowaniu znaków spoza cp1250 — nie
przerywa działania pipeline'u. Jeśli przeszkadza:
`$env:PYTHONIOENCODING="utf-8"` przed uruchomieniem.

**Dashboard pokazuje „Failed to fetch":** backend nie odpowiada na
`VITE_API_BASE_URL`. Sprawdź czy `curl http://localhost:8000/api/health`
zwraca `{"status":"ok"}`. Jeśli backend działa, ale frontend nadal nie
działa — sprawdź CORS (`backend/api/main.py` musi mieć `:5173` na liście)
i zakładkę Network w DevTools.

**Wykres „Liderzy deweloperów" pokazuje tylko Valve / sentyment tylko
1 gatunek:** masz wąski zestaw appidów w ingestion. SteamSpy
`estimated_owners` i zescrapowane recenzje są pobierane wyłącznie dla
appidów z `--appids`. Patrz sekcja [Bogatszy dashboard](#bogatszy-dashboard-opcjonalnie)
powyżej.

## Dokumentacja

Dla devów wchodzących w projekt — szczegółowe materiały w katalogu `docs/`:

- [`docs/architecture.md`](docs/architecture.md) — przepływ danych
  ingestion → ETL → API → frontend, kontrakty między warstwami,
  decyzje projektowe (dlaczego SQLite, dlaczego widoki, dlaczego star
  schema).
- [`docs/data-model.md`](docs/data-model.md) — schemat hurtowni
  (wymiary, fakty, bridges) z diagramem i opisem każdej kolumny.
- [`docs/api.md`](docs/api.md) — pełna referencja endpointów REST
  z przykładami requestów i odpowiedzi.

Wewnętrzne notatki Claude Code (specs, plans, memory) leżą pod
`docs/superpowers/` i są gitignorowane.
