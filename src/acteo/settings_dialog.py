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

        self.autoplay_interval_spin = QSpinBox()
        self.autoplay_interval_spin.setRange(1, 300)

        self.fixed_group_size_spin = QSpinBox()
        self.fixed_group_size_spin.setRange(1, 1000)

        self.exif_priority_check = QCheckBox()
        self.move_mode_combo = QComboBox()
        self.move_mode_combo.addItems(["move", "copy"])

        self.safe_delete_check = QCheckBox()
        self.category_file_edit = QLineEdit()
        self.metadata_file_edit = QLineEdit()
        self.thumbnails_cache_edit = QLineEdit()
        self.operator_name_edit = QLineEdit()

        for label, widget in (
            ("Input folder", self._make_browse_widget(self.input_folder_edit)),
            ("Output folder", self._make_browse_widget(self.output_folder_edit)),
            ("Discard folder", self._make_browse_widget(self.discard_folder_edit)),
            ("Grouping mode", self.grouping_mode_combo),
            ("Timestamp gap (s)", self.timestamp_gap_spin),
            ("Autoplay interval (s)", self.autoplay_interval_spin),
            ("Fixed group size", self.fixed_group_size_spin),
            ("Prefer EXIF timestamps", self.exif_priority_check),
            ("Move mode", self.move_mode_combo),
            ("Safe delete", self.safe_delete_check),
            ("Category file", self._make_browse_widget(self.category_file_edit, is_file=True)),
            ("Metadata file", self._make_browse_widget(self.metadata_file_edit, is_file=True)),
            ("Thumbnails cache dir", self._make_browse_widget(self.thumbnails_cache_edit)),
            ("Operator name", self.operator_name_edit),
        ):
            form.addRow(label, widget)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _make_browse_widget(self, line_edit: QLineEdit, *, is_file: bool = False) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(line_edit)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(lambda: self._browse_path(line_edit, is_file=is_file))
        row.addWidget(browse_btn)
        return widget

    def _browse_path(self, target: QLineEdit, *, is_file: bool = False) -> None:
        if is_file:
            path, _ = QFileDialog.getOpenFileName(self, "Select file")
        else:
            path = QFileDialog.getExistingDirectory(self, "Select folder")
        if path:
            target.setText(path)

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
        self.autoplay_interval_spin.setValue(
            max(1, int(settings.autoplay_interval_seconds))
        )
        self.fixed_group_size_spin.setValue(int(settings.fixed_group_size))
        self.exif_priority_check.setChecked(bool(settings.exif_priority))
        self.safe_delete_check.setChecked(bool(settings.safe_delete))
        self.category_file_edit.setText(settings.category_file_path or "")
        self.metadata_file_edit.setText(settings.metadata_file_path or "")
        self.thumbnails_cache_edit.setText(settings.thumbnails_cache_dir or "")
        self.operator_name_edit.setText(settings.operator_name or "")
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
        self.settings.autoplay_interval_seconds = int(
            self.autoplay_interval_spin.value()
        )
        self.settings.fixed_group_size = int(self.fixed_group_size_spin.value())
        self.settings.exif_priority = bool(self.exif_priority_check.isChecked())
        self.settings.move_mode = self.move_mode_combo.currentText()
        self.settings.safe_delete = bool(self.safe_delete_check.isChecked())
        self.settings.category_file_path = self.category_file_edit.text().strip() or None
        self.settings.metadata_file_path = self.metadata_file_edit.text().strip() or None
        self.settings.thumbnails_cache_dir = self.thumbnails_cache_edit.text().strip() or None
        self.settings.operator_name = self.operator_name_edit.text().strip() or None
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
