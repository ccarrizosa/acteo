from __future__ import annotations

import json
from pathlib import Path

import pytest

import acteo.settings as settings_module
from acteo.settings import (
    Settings,
    bundled_application_root,
    bundled_resource_path,
    default_config_dir,
    ensure_paths,
    validate_settings_data,
)


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


def test_settings_load_accepts_valid_locale_value(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "grouping_mode": "fixed_size",
                "timestamp_gap_seconds": 12,
                "move_mode": "move",
                "fixed_group_size": 5,
                "autoplay_interval_seconds": 2,
                "locale": "es",
            }
        ),
        encoding="utf-8",
    )

    settings = Settings.load(str(config_path))

    assert settings.locale == "es"


def test_settings_load_rejects_unsupported_locale_value(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "grouping_mode": "fixed_size",
                "timestamp_gap_seconds": 12,
                "move_mode": "move",
                "fixed_group_size": 5,
                "autoplay_interval_seconds": 2,
                "locale": "fr",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        Settings.load(str(config_path))


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


def test_windows_config_dir_prefers_local_app_data(monkeypatch, tmp_path: Path) -> None:
    local_app_data = tmp_path / "LocalAppData"
    app_data = tmp_path / "AppData"
    monkeypatch.setattr(
        settings_module.os,
        "environ",
        {
            "LOCALAPPDATA": str(local_app_data),
            "APPDATA": str(app_data),
        },
    )

    result = Path(default_config_dir("win32"))

    assert result == (local_app_data / "Acteo").resolve()


def test_windows_config_dir_falls_back_to_app_data(monkeypatch, tmp_path: Path) -> None:
    app_data = tmp_path / "AppData"
    monkeypatch.setattr(settings_module.os, "environ", {"APPDATA": str(app_data)})

    result = Path(default_config_dir("win32"))

    assert result == (app_data / "Acteo").resolve()


def test_windows_config_dir_falls_back_to_user_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings_module.os, "environ", {})
    monkeypatch.setattr(settings_module.Path, "home", classmethod(lambda cls: tmp_path))

    result = Path(default_config_dir("win32"))

    assert result == (tmp_path / "AppData" / "Local" / "Acteo").resolve()


def test_linux_config_dir_respects_xdg(monkeypatch, tmp_path: Path) -> None:
    xdg_config_home = tmp_path / "xdg"
    monkeypatch.setattr(
        settings_module.os,
        "environ",
        {"XDG_CONFIG_HOME": str(xdg_config_home)},
    )

    result = Path(default_config_dir("linux"))

    assert result == (xdg_config_home / "acteo").resolve()


def test_linux_config_dir_falls_back_to_dot_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings_module.os, "environ", {})
    monkeypatch.setattr(settings_module.Path, "home", classmethod(lambda cls: tmp_path))

    result = Path(default_config_dir("linux"))

    assert result == (tmp_path / ".config" / "acteo").resolve()


def test_macos_config_dir_preserves_unix_fallback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        settings_module.os,
        "environ",
        {"XDG_CONFIG_HOME": str(tmp_path / "config")},
    )

    result = Path(default_config_dir("darwin"))

    assert result == (tmp_path / "config" / "acteo").resolve()


def test_bundled_application_root_for_source_execution(monkeypatch) -> None:
    monkeypatch.delattr(settings_module.sys, "frozen", raising=False)
    monkeypatch.delattr(settings_module.sys, "_MEIPASS", raising=False)

    root = bundled_application_root()

    assert root == Path(settings_module.__file__).resolve().parents[2]
    assert bundled_resource_path("schemas", "settings.schema.json").is_file()


def test_bundled_application_root_for_frozen_execution(monkeypatch, tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    schema_dir = bundle_dir / "schemas"
    schema_dir.mkdir(parents=True)
    source_schema = Path(settings_module.__file__).resolve().parents[2] / "schemas" / "settings.schema.json"
    (schema_dir / "settings.schema.json").write_text(
        source_schema.read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(settings_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(settings_module.sys, "_MEIPASS", str(bundle_dir), raising=False)

    root = bundled_application_root()
    schema_path = bundled_resource_path("schemas", "settings.schema.json")

    assert root == bundle_dir.resolve()
    assert schema_path == (bundle_dir / "schemas" / "settings.schema.json").resolve()
    assert schema_path.is_file()
    validate_settings_data(Settings().to_dict())


def test_settings_schema_resolves_and_validates_from_source() -> None:
    schema_path = bundled_resource_path("schemas", "settings.schema.json")

    assert schema_path.is_file()
    validate_settings_data(Settings().to_dict())


def test_ensure_paths_keeps_auxiliary_paths_in_application_data(monkeypatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "Acteo"
    monkeypatch.setattr(settings_module, "default_config_dir", lambda: str(config_dir))

    settings = ensure_paths(Settings())

    assert settings.category_file_path == str(config_dir / "categories.json")
    assert settings.metadata_file_path == str(config_dir / "metadata.csv")
    assert settings.thumbnails_cache_dir == str(config_dir / "thumbnails")
