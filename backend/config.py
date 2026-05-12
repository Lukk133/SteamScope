"""Globalna konfiguracja: ścieżki w projekcie i parametry warstwy ingestion.

Zarówno `Paths` jak i `IngestionConfig` są frozen dataclassami, aby zapobiec
przypadkowym mutacjom w trakcie pracy programu. Testy mogą wstrzyknąć własny
`project_root` przez konstruktor `Paths`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Paths:
    project_root: Path = _DEFAULT_PROJECT_ROOT

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def kaggle_dir(self) -> Path:
        return self.raw_dir / "kaggle"

    @property
    def steam_api_dir(self) -> Path:
        return self.raw_dir / "steam_api"

    @property
    def steamspy_dir(self) -> Path:
        return self.raw_dir / "steamspy"

    @property
    def scraped_dir(self) -> Path:
        return self.raw_dir / "scraped"

    @property
    def db_dir(self) -> Path:
        return self.project_root / "db"

    @property
    def db_path(self) -> Path:
        return self.db_dir / "steam_warehouse.db"

    @property
    def logs_dir(self) -> Path:
        return self.project_root / "logs"

    def ensure(self) -> None:
        """Tworzy wszystkie katalogi danych/db/logów. Idempotentne."""
        for p in (
            self.raw_dir, self.processed_dir, self.exports_dir,
            self.kaggle_dir, self.steam_api_dir, self.steamspy_dir, self.scraped_dir,
            self.db_dir, self.logs_dir,
        ):
            p.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class IngestionConfig:
    kaggle_dataset_id: str = field(
        default_factory=lambda: os.getenv(
            "KAGGLE_DATASET_ID", "fronkongames/steam-games-dataset"
        )
    )
    kaggle_csv_filename: str = "games.csv"
    steam_api_rate_limit_seconds: float = 1.5
    steamspy_rate_limit_seconds: float = 1.0
    reviews_rate_limit_seconds: float = 2.0
    # Reserved for Phase 2 retry logic; currently unused in fetch_many.
    steam_api_max_retries: int = 3
    http_timeout_seconds: int = 30
    user_agent: str = "SteamAnalyticsProject/1.0 (educational; +https://github.com/local)"


PATHS = Paths()
INGESTION = IngestionConfig()
