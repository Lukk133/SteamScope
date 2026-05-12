"""Testy ładowania danych z Kaggle (SDK zmockowane)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.ingestion import load_kaggle


def _fake_kaggle_writes_csv(target_dir: Path, csv_name: str = "games.csv") -> MagicMock:
    """Tworzy mock KaggleApi, który symuluje zapisanie pliku CSV po wywołaniu download."""
    api = MagicMock()

    def _download(_dataset_id: str, path: str, unzip: bool) -> None:
        (Path(path) / csv_name).write_text("appid,name\n1,Half-Life\n", encoding="utf-8")

    api.dataset_download_files.side_effect = _download
    return api


def test_skips_download_when_csv_already_exists(tmp_path: Path) -> None:
    target = tmp_path / "kaggle"
    target.mkdir()
    existing = target / "games.csv"
    existing.write_text("already here", encoding="utf-8")

    with patch.object(load_kaggle, "KaggleApi") as cls:
        result = load_kaggle.download_kaggle_dataset(
            dataset_id="x/y", target_dir=target, force=False
        )

    cls.assert_not_called()
    assert result == existing
    assert existing.read_text(encoding="utf-8") == "already here"


def test_downloads_when_csv_missing(tmp_path: Path) -> None:
    target = tmp_path / "kaggle"
    api = _fake_kaggle_writes_csv(target)

    with patch.object(load_kaggle, "KaggleApi", return_value=api):
        result = load_kaggle.download_kaggle_dataset(
            dataset_id="x/y", target_dir=target, force=False
        )

    api.authenticate.assert_called_once()
    api.dataset_download_files.assert_called_once_with("x/y", path=str(target), unzip=True)
    assert result == target / "games.csv"
    assert result.exists()


def test_force_redownloads_even_if_csv_exists(tmp_path: Path) -> None:
    target = tmp_path / "kaggle"
    target.mkdir()
    (target / "games.csv").write_text("stale", encoding="utf-8")
    api = _fake_kaggle_writes_csv(target)

    with patch.object(load_kaggle, "KaggleApi", return_value=api):
        result = load_kaggle.download_kaggle_dataset(
            dataset_id="x/y", target_dir=target, force=True
        )

    api.dataset_download_files.assert_called_once()
    assert result.read_text(encoding="utf-8") == "appid,name\n1,Half-Life\n"


def test_renames_other_csv_to_canonical_name(tmp_path: Path) -> None:
    target = tmp_path / "kaggle"
    api = _fake_kaggle_writes_csv(target, csv_name="steam_dataset.csv")

    with patch.object(load_kaggle, "KaggleApi", return_value=api):
        result = load_kaggle.download_kaggle_dataset(
            dataset_id="x/y", target_dir=target, force=False
        )

    assert result == target / "games.csv"
    assert result.exists()
    assert not (target / "steam_dataset.csv").exists()


def test_raises_when_no_csv_downloaded(tmp_path: Path) -> None:
    target = tmp_path / "kaggle"
    target.mkdir()
    api = MagicMock()  # no side_effect: nothing gets written

    with patch.object(load_kaggle, "KaggleApi", return_value=api):
        with pytest.raises(FileNotFoundError, match="No CSV found"):
            load_kaggle.download_kaggle_dataset(
                dataset_id="x/y", target_dir=target, force=False
            )
