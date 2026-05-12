"""Pobieranie zbioru danych Steam z Kaggle przez oficjalne SDK.

SDK autentykuje się poprzez `~/.kaggle/kaggle.json` lub zmienne środowiskowe
`KAGGLE_USERNAME` + `KAGGLE_KEY` (ładowane z `.env` w `backend.config`).
"""
from __future__ import annotations

import logging
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

from backend.config import INGESTION, PATHS

logger = logging.getLogger(__name__)


def download_kaggle_dataset(
    dataset_id: str | None = None,
    target_dir: Path | None = None,
    force: bool = False,
) -> Path:
    """Pobiera dataset z Kaggle i zwraca ścieżkę do pliku CSV.

    - `dataset_id`: identyfikator typu "owner/slug". Domyślnie z `INGESTION`.
    - `target_dir`: katalog docelowy. Domyślnie `PATHS.kaggle_dir`.
    - `force`: jeśli False, pomija pobieranie gdy plik CSV już istnieje (idempotencja).

    Jeśli rozpakowane archiwum zawiera CSV pod inną nazwą, zostaje on
    zmieniony na `INGESTION.kaggle_csv_filename`.
    """
    dataset_id = dataset_id or INGESTION.kaggle_dataset_id
    target_dir = target_dir or PATHS.kaggle_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    csv_path = target_dir / INGESTION.kaggle_csv_filename
    if csv_path.exists() and not force:
        logger.info("CSV already at %s — skipping (force=True to override)", csv_path)
        return csv_path

    api = KaggleApi()
    api.authenticate()
    logger.info("Downloading Kaggle dataset %s → %s", dataset_id, target_dir)
    api.dataset_download_files(dataset_id, path=str(target_dir), unzip=True)

    if not csv_path.exists():
        csvs = sorted(target_dir.glob("*.csv"))
        if not csvs:
            raise FileNotFoundError(
                f"No CSV found in {target_dir} after downloading {dataset_id}"
            )
        csvs[0].rename(csv_path)
        logger.info("Renamed %s → %s", csvs[0].name, csv_path.name)

    return csv_path
