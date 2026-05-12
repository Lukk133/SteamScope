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
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
# uzupełnij KAGGLE_USERNAME i KAGGLE_KEY w .env (https://www.kaggle.com/settings/account → Create New Token)
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

```powershell
python -m scripts.run_ingestion --source all --appids 70,220,440,400
```

### Wymuszenie ponownego pobrania

```powershell
python -m scripts.run_ingestion --source steam --appids 70 --force
```

### Logi

Każde uruchomienie zapisuje log do `logs/ingestion.log` (plik gitignorowany).

## Testy

```powershell
pytest                  # wszystkie testy
pytest -v --cov=backend # z pokryciem
ruff check backend tests scripts  # linter
```
