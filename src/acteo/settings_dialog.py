"""Settings dialog for Acteo."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .settings import Settings, default_config_path, ensure_paths


class SettingsDialog(QDialog):
    """Dialog for editing Acteo settings."""

    def __init__(
        self,
        settings: Settings,
        parent: Optional[QWidget] = None,
        config_path: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.config_path = config_path or default_config_path()
        self._init_ui()
        self.load_from_settings(settings)

    def _init_ui(self) -> None:
        self.setWindowTitle("Acteo settings")
        self.resize(620, 280)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.input_folder_edit = QLineEdit()
        self.output_folder_edit = QLineEdit()
        self.discard_folder_edit = QLineEdit()

        self.grouping_mode_combo = QComboBox()
        self.grouping_mode_combo.addItems(["timestamp_gap", "fixed_size"])

        self.timestamp_gap_spin = QSpinBox()
        self.timestamp_gap_spin.setRange(1, 3600)

        self.fixed_group_size_spin = QSpinBox()
        self.fixed_group_size_spin.setRange(1, 1000)

        self.exif_priority_check = QCheckBox()
        self.move_mode_combo = QComboBox()
        self.move_mode_combo.addItems(["move", "copy"])

        for label, widget in (
            ("Input folder", self._make_browse_widget(self.input_folder_edit)),
            ("Output folder", self._make_browse_widget(self.output_folder_edit)),
            ("Discard folder", self._make_browse_widget(self.discard_folder_edit)),
            ("Grouping mode", self.grouping_mode_combo),
            ("Timestamp gap (s)", self.timestamp_gap_spin),
            ("Fixed group size", self.fixed_group_size_spin),
            ("Prefer EXIF timestamps", self.exif_priority_check),
            ("Move mode", self.move_mode_combo),
        ):
            form.addRow(label, widget)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _make_browse_widget(self, line_edit: QLineEdit) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(line_edit)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(lambda: self._browse_folder(line_edit))
        row.addWidget(browse_btn)
        return widget

    def _browse_folder(self, target: QLineEdit) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select folder")
        if directory:
            target.setText(directory)

    def load_from_settings(self, settings: Settings) -> None:
        self.input_folder_edit.setText(settings.input_folder or "")
        self.output_folder_edit.setText(settings.output_folder or "")
        self.discard_folder_edit.setText(settings.discard_folder or "")
        self.grouping_mode_combo.setCurrentText(
            settings.grouping_mode
            if settings.grouping_mode in {"timestamp_gap", "fixed_size"}
            else "timestamp_gap"
        )
        self.timestamp_gap_spin.setValue(int(settings.timestamp_gap_seconds))
        self.fixed_group_size_spin.setValue(int(settings.fixed_group_size))
        self.exif_priority_check.setChecked(bool(settings.exif_priority))
        if settings.move_mode in {"move", "copy"}:
            self.move_mode_combo.setCurrentText(settings.move_mode)
        else:
            self.move_mode_combo.setCurrentText("move")

    def validate(self) -> bool:
        gap = self.timestamp_gap_spin.value()
        if gap <= 0:
            return False

        if self.grouping_mode_combo.currentText() == "fixed_size":
            if self.fixed_group_size_spin.value() <= 0:
                return False

        for value in (
            self.input_folder_edit.text().strip(),
            self.output_folder_edit.text().strip(),
            self.discard_folder_edit.text().strip(),
        ):
            if not value:
                continue
            path = Path(value)
            if path.exists() and not path.is_dir():
                return False

        return True

    def apply_to_settings(self) -> Settings:
        self.settings.input_folder = self.input_folder_edit.text().strip() or None
        self.settings.output_folder = self.output_folder_edit.text().strip() or None
        self.settings.discard_folder = self.discard_folder_edit.text().strip() or None
        self.settings.grouping_mode = self.grouping_mode_combo.currentText()
        self.settings.timestamp_gap_seconds = int(self.timestamp_gap_spin.value())
        self.settings.fixed_group_size = int(self.fixed_group_size_spin.value())
        self.settings.exif_priority = bool(self.exif_priority_check.isChecked())
        self.settings.move_mode = self.move_mode_combo.currentText()
        self.settings = ensure_paths(self.settings)
        self.settings.save(self.config_path)
        return self.settings

    def accept(self) -> None:
        if not self.validate():
            QMessageBox.warning(
                self,
                "Invalid settings",
                "Please provide valid folder paths, a positive timestamp gap, "
                "and a valid fixed group size when needed.",
            )
            return
        self.apply_to_settings()
        super().accept()
