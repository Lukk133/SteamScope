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
