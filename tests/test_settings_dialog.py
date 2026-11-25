from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from acteo.i18n import get_locale, set_locale, t
from acteo.settings import Settings
from acteo.settings_dialog import SettingsDialog


def test_settings_dialog_saves_and_applies_values(tmp_path: Path) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    config_path = tmp_path / "settings.json"
    settings = Settings(
        input_folder="/tmp/input",
        output_folder="/tmp/output",
        discard_folder="/tmp/discard",
        timestamp_gap_seconds=15,
        exif_priority=True,
        move_mode="move",
    )

    dialog = SettingsDialog(settings, config_path=str(config_path))
    dialog.input_folder_edit.setText(str(tmp_path / "new_input"))
    dialog.output_folder_edit.setText(str(tmp_path / "new_output"))
    dialog.discard_folder_edit.setText(str(tmp_path / "new_discard"))
    dialog.timestamp_gap_spin.setValue(60)
    dialog.exif_priority_check.setChecked(False)
    dialog.move_mode_combo.setCurrentText("copy")
    dialog.grouping_mode_combo.setCurrentText("fixed_size")
    dialog.fixed_group_size_spin.setValue(5)

    dialog.apply_to_settings()

    assert settings.input_folder == str(tmp_path / "new_input")
    assert settings.output_folder == str(tmp_path / "new_output")
    assert settings.discard_folder == str(tmp_path / "new_discard")
    assert settings.timestamp_gap_seconds == 60
    assert settings.grouping_mode == "fixed_size"
    assert settings.fixed_group_size == 5
    assert settings.exif_priority is False
    assert settings.move_mode == "copy"
    assert config_path.exists()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["timestamp_gap_seconds"] == 60
    assert payload["grouping_mode"] == "fixed_size"
    assert payload["fixed_group_size"] == 5
    assert payload["move_mode"] == "copy"


def test_settings_dialog_save_and_load_locale(tmp_path: Path) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    settings = Settings(locale="ca")
    dialog = SettingsDialog(settings, config_path=str(tmp_path / "settings.json"))

    assert dialog.locale_combo.currentText() == "Català"

    dialog.locale_combo.setCurrentText("Español")
    dialog.apply_to_settings()

    assert settings.locale == "es"
    payload = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert payload["locale"] == "es"


def test_settings_dialog_translates_labels_for_supported_locales() -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    for locale in ("en", "es", "ca"):
        set_locale(locale)
        settings = Settings(locale=locale)
        dialog = SettingsDialog(settings)

        label_texts = {label.text() for label in dialog.findChildren(QLabel)}
        button_texts = {button.text() for button in dialog.findChildren(QPushButton)}

        assert dialog.windowTitle() == t("settings.title", locale=locale)
        assert t("settings.input_folder", locale=locale) in label_texts
        assert t("settings.browse", locale=locale) in button_texts
        assert get_locale() == locale


def test_settings_dialog_saves_missing_optional_settings(tmp_path: Path) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    settings = Settings(
        category_file_path="/tmp/categories.json",
        metadata_file_path="/tmp/metadata.csv",
        thumbnails_cache_dir="/tmp/thumbs",
        operator_name="Alice",
        safe_delete=True,
    )

    dialog = SettingsDialog(settings, config_path=str(tmp_path / "settings.json"))
    dialog.category_file_edit.setText(str(tmp_path / "new_categories.json"))
    dialog.metadata_file_edit.setText(str(tmp_path / "new_metadata.csv"))
    dialog.thumbnails_cache_edit.setText(str(tmp_path / "new_thumbs"))
    dialog.operator_name_edit.setText("Bob")
    dialog.safe_delete_check.setChecked(False)

    dialog.apply_to_settings()

    assert settings.category_file_path == str(tmp_path / "new_categories.json")
    assert settings.metadata_file_path == str(tmp_path / "new_metadata.csv")
    assert settings.thumbnails_cache_dir == str(tmp_path / "new_thumbs")
    assert settings.operator_name == "Bob"
    assert settings.safe_delete is False
