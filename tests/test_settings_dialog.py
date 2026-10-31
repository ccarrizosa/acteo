from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication

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
