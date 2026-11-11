from __future__ import annotations

import json
from pathlib import Path

import pytest

from acteo.settings import Settings


def test_settings_load_rejects_unsupported_grouping_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "grouping_mode": "manual",
                "timestamp_gap_seconds": 12,
                "move_mode": "move",
                "fixed_group_size": 5,
                "autoplay_interval_seconds": 2,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        Settings.load(str(config_path))


def test_settings_load_accepts_valid_fixed_size_config(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "grouping_mode": "fixed_size",
                "timestamp_gap_seconds": 12,
                "move_mode": "move",
                "fixed_group_size": 5,
                "autoplay_interval_seconds": 2,
            }
        ),
        encoding="utf-8",
    )

    settings = Settings.load(str(config_path))

    assert settings.grouping_mode == "fixed_size"
    assert settings.fixed_group_size == 5
    assert settings.autoplay_interval_seconds == 2


def test_settings_load_applies_defaults_and_persists_missing_legacy_key(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "grouping_mode": "fixed_size",
                "timestamp_gap_seconds": 12,
                "move_mode": "copy",
                "fixed_group_size": 4,
            }
        ),
        encoding="utf-8",
    )

    settings = Settings.load(str(config_path))

    assert settings.autoplay_interval_seconds == 1
    assert json.loads(config_path.read_text(encoding="utf-8"))["autoplay_interval_seconds"] == 1


def test_settings_load_ignores_unknown_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "grouping_mode": "fixed_size",
                "timestamp_gap_seconds": 12,
                "move_mode": "copy",
                "fixed_group_size": 4,
                "autoplay_interval_seconds": 3,
                "concurrency": 8,
                "file_patterns": ["*.jpg"],
                "images_per_sequence": 5,
                "preserve_folder_structure": True,
            }
        ),
        encoding="utf-8",
    )

    settings = Settings.load(str(config_path))

    assert settings.autoplay_interval_seconds == 3
    assert settings.move_mode == "copy"
    assert settings.grouping_mode == "fixed_size"
    assert settings.fixed_group_size == 4
    assert json.loads(config_path.read_text(encoding="utf-8")).get("concurrency") is None
