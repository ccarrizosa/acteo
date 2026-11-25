from __future__ import annotations

from pathlib import Path

import pytest

from acteo.i18n import get_locale, set_locale, t
from acteo.settings import Settings

REQUIRED_KEYS = [
    "app_title",
    "settings.title",
    "settings.input_folder",
    "main.open_folder",
    "main.settings",
    "main.export_report",
    "viewer.selected_image",
]


def test_default_locale_is_english() -> None:
    set_locale("en")
    assert get_locale() == "en"
    assert t("app_title") == "Acteo — Trail Camera Image Classifier"


def test_invalid_locale_falls_back_to_english() -> None:
    set_locale("fr")
    assert get_locale() == "en"
    assert t("settings.title") == "Acteo settings"


def test_supported_locales_have_required_strings() -> None:
    for locale in ("en", "es", "ca"):
        set_locale(locale)
        for key in REQUIRED_KEYS:
            assert t(key, locale=locale)
            assert t(key, locale=locale) != key


def test_explicit_locale_override_is_respected() -> None:
    set_locale("en")
    assert t("settings.title", locale="es") == "Configuración de Acteo"
    assert t("main.open_folder", locale="ca") == "Obrir carpeta"


def test_settings_rejects_invalid_locale_value() -> None:
    with pytest.raises(ValueError, match="Unsupported locale"):
        Settings.from_dict({"locale": "fr"})


def test_settings_save_and_load_persist_locale(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.json"
    settings = Settings(locale="ca")

    settings.save(str(config_path))
    reloaded = Settings.load(str(config_path))

    assert settings.locale == "ca"
    assert reloaded.locale == "ca"
    assert config_path.exists()
