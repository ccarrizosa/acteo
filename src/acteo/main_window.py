"""Main window for Acteo application.

This module implements the primary application window with toolbar, sequence
list panel, image viewer, category buttons, and status bar.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QKeyEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from typing_extensions import override

from .categories import load_categories, save_categories
from .classifier import Classifier
from .image_viewer import ImageViewer
from .logger import export_sequence_report
from .sequence_loader import (
    Sequence,
    group_by_fixed_size,
    group_by_timestamp_gap,
    scan_folder,
)
from .settings import Settings
from .settings_dialog import SettingsDialog
from .storage import bulk_skip, discard_files
from .undo import Action, ActionType, UndoStack

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for Acteo.

    Provides a toolbar, sequence list (left), image viewer (center),
    category buttons (right), and status bar.
    """

    def __init__(
        self,
        settings: Settings,
        sequences: Optional[List[Sequence]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the main window.

        Args:
            settings: Application settings object.
            sequences: List of Sequence objects to display (can be set later).
            parent: Parent widget.
        """
        super().__init__(parent)
        self.settings = settings
        self._sequences = sequences or []
        self._current_sequence_index = 0
        self._classifier: Optional[Classifier] = None
        self._undo_stack = UndoStack()
        self._classification_rows: List[dict[str, object]] = []
        self._categories = self._load_categories_from_disk()
        self._autoplay_timer = QTimer(self)
        self._autoplay_timer.setSingleShot(False)
        self._autoplay_timer.timeout.connect(self._advance_autoplay)
        self._is_playing = False
        self._play_pause_action: Optional[object] = None

        self.setWindowTitle("Acteo — Trail Camera Image Classifier")
        self.setGeometry(100, 100, 1400, 900)

        self._init_ui()
        self._refresh_category_buttons()
        if sequences:
            self.set_sequences(sequences)

    def _init_ui(self) -> None:
        """Initialize the UI components."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        # Left panel: Sequence list
        self._sequence_list = QListWidget()
        self._sequence_list.itemClicked.connect(self._on_sequence_selected)
        main_layout.addWidget(self._sequence_list, 1)

        # Center panel: Image viewer
        self._image_viewer = ImageViewer()
        self._image_viewer.image_selected.connect(self._on_image_selected)
        main_layout.addWidget(self._image_viewer, 3)

        # Right panel: Controls
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)

        # Category buttons (will be populated dynamically)
        self._category_buttons: List[QPushButton] = []
        self._category_container = QWidget()
        self._category_layout = QVBoxLayout()
        self._category_container.setLayout(self._category_layout)
        right_layout.addWidget(self._category_container)

        # Add/Rename/Remove category buttons
        add_cat_btn = QPushButton("+ Add Category")
        add_cat_btn.clicked.connect(self._add_category)
        right_layout.addWidget(add_cat_btn)

        rename_cat_btn = QPushButton("Rename Category")
        rename_cat_btn.clicked.connect(self._rename_category_prompt)
        right_layout.addWidget(rename_cat_btn)

        remove_cat_btn = QPushButton("- Remove Category")
        remove_cat_btn.clicked.connect(self._remove_category)
        right_layout.addWidget(remove_cat_btn)

        # Discard button
        discard_btn = QPushButton("Discard Sequence")
        discard_btn.setStyleSheet("background-color: #f44336; color: white;")
        discard_btn.clicked.connect(self._discard_sequence)
        right_layout.addWidget(discard_btn)

        # Undo button
        undo_btn = QPushButton("Undo")
        undo_btn.clicked.connect(self._undo_action)
        right_layout.addWidget(undo_btn)

        right_layout.addStretch()
        main_layout.addWidget(right_panel, 1)

        # Toolbar
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        open_btn = toolbar.addAction("Open Folder")
        open_btn.triggered.connect(self._open_folder)

        settings_btn = toolbar.addAction("Settings")
        settings_btn.triggered.connect(self._show_settings)

        export_btn = toolbar.addAction("Export Report")
        export_btn.triggered.connect(self._export_report)

        toolbar.addSeparator()

        prev_btn = toolbar.addAction("< Previous")
        prev_btn.triggered.connect(self._previous_sequence)

        next_btn = toolbar.addAction("Next >")
        next_btn.triggered.connect(self._next_sequence)

        self._play_pause_action = toolbar.addAction("▶ Play")
        self._play_pause_action.triggered.connect(self._toggle_play_pause)
        self._apply_play_pause_icon()

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("Ready")
        self._status_bar.addWidget(self._status_label)

    def _rebuild_sequences_for_current_settings(self) -> None:
        """Re-scan the current input folder using the active grouping settings."""
        folder = getattr(self.settings, "input_folder", None)
        if not folder:
            self._status_label.setText("No input folder selected")
            return

        if not Path(folder).exists() or not Path(folder).is_dir():
            self._status_label.setText(f"Input folder is missing or invalid: {folder}")
            QMessageBox.warning(
                self,
                "Invalid input folder",
                "The selected input folder does not exist or is not a directory: "
                f"{folder}",
            )
            return

        files = scan_folder(folder)
        if not files:
            self._sequences = []
            self._image_viewer.set_sequence("empty", [])
            self._refresh_sequence_list()
            self._status_label.setText(f"No images found in {folder}")
            self._status_bar.showMessage(f"No images found in {folder}", 4000)
            return

        gap_seconds = getattr(self.settings, "timestamp_gap_seconds", 10)
        exif_priority = getattr(self.settings, "exif_priority", True)
        grouping_mode = getattr(self.settings, "grouping_mode", "timestamp_gap")
        fixed_group_size = getattr(self.settings, "fixed_group_size", 3)

        if grouping_mode == "fixed_size":
            self._sequences = group_by_fixed_size(
                files, group_size=fixed_group_size, exif_priority=exif_priority
            )
        else:
            self._sequences = group_by_timestamp_gap(
                files, gap_seconds=gap_seconds, exif_priority=exif_priority
            )

        self._current_sequence_index = 0
        self._refresh_sequence_list()
        if self._sequences:
            self._display_sequence(0)
        self._status_label.setText(
            f"Loaded {len(self._sequences)} sequences from {folder}"
        )

    def _open_folder(self) -> None:
        """Open a folder and scan for images."""
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if not folder:
            return

        self.settings.input_folder = folder
        self._rebuild_sequences_for_current_settings()

    def _show_settings(self) -> None:
        """Show the settings dialog and apply the updated values."""
        dialog = SettingsDialog(self.settings, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.settings = dialog.settings
            self._rebuild_sequences_for_current_settings()
            self._status_label.setText("Settings updated")

    def set_sequences(self, sequences: List[Sequence]) -> None:
        """Set the sequences to display.

        Args:
            sequences: List of Sequence objects.
        """
        self._sequences = sequences
        self._current_sequence_index = 0
        self._refresh_sequence_list()
        if sequences:
            self._display_sequence(0)

    def _refresh_sequence_list(self) -> None:
        """Refresh the left panel sequence list."""
        self._sequence_list.clear()
        for seq in self._sequences:
            label = f"Seq {seq.id}: {len(seq.image_paths)} images"
            if seq.is_classified:
                category_label = seq.category or "classified"
                label = f"{label} [classified: {category_label}]"
            item = QListWidgetItem(label)
            self._sequence_list.addItem(item)

    def _on_sequence_selected(self, item: QListWidgetItem) -> None:
        """Handle sequence selection from list."""
        idx = self._sequence_list.row(item)
        self._current_sequence_index = idx
        self._display_sequence(idx)

    def _display_sequence(self, index: int) -> None:
        """Display a sequence in the image viewer.

        Args:
            index: Index of the sequence in the list.
        """
        if not (0 <= index < len(self._sequences)):
            return
        seq = self._sequences[index]
        self._image_viewer.set_sequence(seq.id, seq.image_paths)
        self._status_label.setText(
            f"Sequence {seq.id}: {len(seq.image_paths)} images "
            f"[{seq.start_ts} to {seq.end_ts}]"
        )

    def _previous_sequence(self) -> None:
        """Go to previous sequence."""
        if self._sequences:
            idx = (self._current_sequence_index - 1) % len(self._sequences)
            self._current_sequence_index = idx
            self._display_sequence(idx)

    def _next_sequence(self) -> None:
        """Go to next sequence."""
        if self._sequences:
            idx = (self._current_sequence_index + 1) % len(self._sequences)
            self._current_sequence_index = idx
            self._display_sequence(idx)

    def _on_image_selected(self, sequence_id: str, index: int) -> None:
        """Handle image selection in viewer."""
        msg = f"Selected image {index} from sequence {sequence_id}"
        self._status_label.setText(msg)

    def _apply_play_pause_icon(self) -> None:
        """Set the play/pause icon and text for the current running state."""
        if self._play_pause_action is None:
            return

        if self._is_playing:
            self._play_pause_action.setText("❚❚ Pause")
            self._play_pause_action.setToolTip("Pause autoplay")
            icon = QIcon.fromTheme("media-playback-pause")
            if icon.isNull():
                icon = QIcon.fromTheme("media-playback-pause-symbolic")
            if not icon.isNull():
                self._play_pause_action.setIcon(icon)
        else:
            self._play_pause_action.setText("▶ Play")
            self._play_pause_action.setToolTip("Play autoplay")
            icon = QIcon.fromTheme("media-playback-start")
            if icon.isNull():
                icon = QIcon.fromTheme("media-playback-start-symbolic")
            if not icon.isNull():
                self._play_pause_action.setIcon(icon)

    def _toggle_play_pause(self) -> None:
        """Toggle autoplay for the active sequence."""
        if not self._sequences:
            return

        if self._is_playing:
            self._autoplay_timer.stop()
            self._is_playing = False
            self._apply_play_pause_icon()
            self._status_label.setText("Autoplay paused")
            return

        interval_seconds = int(
            getattr(self.settings, "autoplay_interval_seconds", 1)
        )
        interval_ms = max(250, interval_seconds * 1000)
        self._autoplay_timer.setInterval(interval_ms)
        self._autoplay_timer.start()
        self._is_playing = True
        self._apply_play_pause_icon()
        self._status_label.setText("Autoplay playing")

    def _advance_autoplay(self) -> None:
        """Move to the next image in the active sequence when autoplay is running."""
        if not self._sequences or not self._is_playing:
            return

        if not (0 <= self._current_sequence_index < len(self._sequences)):
            self._toggle_play_pause()
            return

        current_sequence = self._sequences[self._current_sequence_index]
        if not current_sequence.image_paths:
            self._toggle_play_pause()
            return

        next_index = (self._image_viewer.get_selected_index() + 1) % len(
            current_sequence.image_paths
        )
        self._image_viewer._on_tile_clicked(next_index)

    def _load_categories_from_disk(self) -> List[dict[str, object]]:
        """Load categories from the configured category file, if present."""
        path = getattr(self.settings, "category_file_path", None)
        if not path:
            return []
        try:
            return load_categories(path)
        except Exception:
            logger.exception("Failed to load categories from %s", path)
            return []

    def _save_categories_to_disk(self) -> None:
        """Persist the current category list to disk."""
        path = getattr(self.settings, "category_file_path", None)
        if not path:
            return
        try:
            save_categories(path, self._categories)
        except Exception:
            logger.exception("Failed to save categories to %s", path)

    def _add_category(self) -> None:
        """Add a new category."""
        name, ok = QInputDialog.getText(self, "New Category", "Enter category name:")
        if not ok or not name:
            return
        clean_name = str(name).strip()
        if not clean_name:
            QMessageBox.warning(
                self,
                "Invalid Category",
                "Category name cannot be empty",
            )
            return
        if any(
            str(cat.get("name", "")).strip().lower() == clean_name.lower()
            for cat in self._categories
        ):
            QMessageBox.warning(
                self,
                "Duplicate Category",
                f"{clean_name} already exists",
            )
            return
        cat_id = f"cat_{len(self._categories)}"
        self._categories.append({"id": cat_id, "name": clean_name})
        self._save_categories_to_disk()
        self._refresh_category_buttons()

    def _rename_category_prompt(self) -> None:
        """Rename a selected category via dialog."""
        if not self._categories:
            QMessageBox.warning(self, "No Categories", "No categories to rename")
            return
        names = [str(cat.get("name", "")) for cat in self._categories]
        old_name, ok = QInputDialog.getItem(
            self, "Rename Category", "Select category to rename:", names
        )
        if not ok or not old_name:
            return
        new_name, ok_new = QInputDialog.getText(
            self, "Rename Category", "New category name:", text=str(old_name)
        )
        if ok_new and new_name:
            self._rename_category(str(old_name), str(new_name))

    def _rename_category(self, old_name: str, new_name: str) -> None:
        """Rename a category in the list and persist the results."""
        clean_old = str(old_name).strip()
        clean_new = str(new_name).strip()
        if not clean_old or not clean_new:
            return
        if any(
            str(cat.get("name", "")).strip().lower() == clean_new.lower()
            and str(cat.get("name", "")).strip().lower() != clean_old.lower()
            for cat in self._categories
        ):
            QMessageBox.warning(
                self,
                "Duplicate Category",
                f"{clean_new} already exists",
            )
            return
        for cat in self._categories:
            if str(cat.get("name", "")).strip() == clean_old:
                cat["name"] = clean_new
                break
        self._save_categories_to_disk()
        self._refresh_category_buttons()

    def _remove_category(self, category_name: Optional[str] = None) -> None:
        """Remove a category."""
        if not self._categories:
            QMessageBox.warning(self, "No Categories", "No categories to remove")
            return

        if category_name is None:
            names = [str(c.get("name", "")) for c in self._categories]
            name, ok = QInputDialog.getItem(
                self, "Remove Category", "Select category:", names
            )
            if not ok or not name:
                return
            category_name = str(name)

        self._categories = [
            c
            for c in self._categories
            if str(c.get("name", "")).strip()
            != str(category_name).strip()
        ]
        self._save_categories_to_disk()
        self._refresh_category_buttons()

    def _refresh_category_buttons(self) -> None:
        """Refresh category buttons in right panel."""
        # Clear old buttons
        while self._category_layout.count():
            item = self._category_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        self._category_buttons.clear()

        # Create new buttons
        for cat in self._categories:
            name = str(cat.get("name", ""))
            cat_id = str(cat.get("id", ""))
            self._create_category_button(name, cat_id)

    def _create_category_button(self, name: str, cat_id: str) -> None:
        """Create a category button and connect it.

        Args:
            name: Display name of the category.
            cat_id: Unique identifier for the category.
        """
        btn = QPushButton(name)
        btn.clicked.connect(lambda checked=False: self._classify_sequence(cat_id, name))
        self._category_layout.addWidget(btn)
        self._category_buttons.append(btn)

    def _record_classification_row(
        self,
        seq: Sequence,
        category_name: str,
        destination_paths: list[str],
        operation: str,
    ) -> None:
        """Add a row describing a classification for CSV export."""
        self._classification_rows.append(
            {
                "sequence_id": seq.id,
                "image_count": len(seq.image_paths),
                "image_paths": json.dumps(seq.image_paths, ensure_ascii=False),
                "start_ts": seq.start_ts.isoformat(),
                "end_ts": seq.end_ts.isoformat(),
                "category": category_name,
                "operator": getattr(self.settings, "operator_name", "") or "",
                "timestamp_processed": datetime.utcnow().isoformat(),
                "operation": operation,
                "destination_paths": json.dumps(
                    destination_paths, ensure_ascii=False
                ),
            }
        )

    def _export_report(self) -> None:
        """Export the current classification rows to a CSV file."""
        if not self._classification_rows:
            QMessageBox.information(
                self,
                "No report data",
                "There are no classified sequences to export yet.",
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export classification report",
            str(Path.home() / "acteo_report.csv"),
            "CSV files (*.csv)",
        )
        if not path:
            return

        try:
            export_sequence_report(path, self._classification_rows)
            self._status_label.setText(f"Exported report to {path}")
        except Exception as exc:  # pragma: no cover - defensive UX path
            QMessageBox.critical(self, "Export Failed", str(exc))
            logger.exception("Failed to export report: %s", exc)

    def _validate_output_folder_for_classification(self) -> Optional[Path]:
        """Validate that an output folder is configured and usable."""
        output_folder = getattr(self.settings, "output_folder", None)
        if not output_folder:
            QMessageBox.warning(
                self,
                "Output folder missing",
                "Configure an output folder in settings before classifying images.",
            )
            return None

        path = Path(output_folder).expanduser()
        if path.exists() and not path.is_dir():
            QMessageBox.warning(
                self,
                "Invalid output folder",
                f"The output folder is invalid: {output_folder}",
            )
            return None

        return path

    def _validate_discard_folder_for_action(self) -> Optional[Path]:
        """Validate that a discard folder is configured and usable."""
        discard_folder = getattr(self.settings, "discard_folder", None)
        if not discard_folder:
            QMessageBox.warning(
                self,
                "Discard folder missing",
                "Configure a discard folder in settings before discarding images.",
            )
            return None

        path = Path(discard_folder).expanduser()
        if path.exists() and not path.is_dir():
            QMessageBox.warning(
                self,
                "Invalid discard folder",
                f"The discard folder is invalid: {discard_folder}",
            )
            return None

        return path

    def _classify_sequence(self, category_id: str, category_name: str) -> None:
        """Classify the current sequence.

        Args:
            category_id: Unique ID of the category.
            category_name: Display name of the category.
        """
        if not self._classifier:
            QMessageBox.warning(
                self, "Not Ready", "Classifier not yet initialized"
            )
            return

        if not (0 <= self._current_sequence_index < len(self._sequences)):
            return

        output_path = self._validate_output_folder_for_classification()
        if output_path is None:
            return

        seq = self._sequences[self._current_sequence_index]
        try:
            result = self._classifier.classify_sequence(seq, category_name)
            seq.is_classified = True
            seq.category = category_name
            self._record_classification_row(
                seq,
                category_name,
                result.destination_paths,
                result.operation,
            )

            # Record action in undo stack
            action = Action(
                action_type=ActionType.CLASSIFY,
                src_paths=seq.image_paths,
                dst_paths=result.destination_paths,
                sequence_id=seq.id,
                category=category_name,
                operator=getattr(self.settings, "operator_name", "unknown"),
            )
            self._undo_stack.push(action)

            self._status_label.setText(
                f"Classified sequence {seq.id} as {category_name}"
            )
            self._refresh_sequence_list()

            # Move to next sequence
            self._next_sequence()
        except Exception as e:
            QMessageBox.critical(self, "Classification Error", str(e))
            logger.exception("Failed to classify sequence: %s", e)

    def _skip_selected_images(self) -> None:
        """Move the currently selected image(s) to the discard folder."""
        if not self._sequences or not (
            0 <= self._current_sequence_index < len(self._sequences)
        ):
            return

        seq = self._sequences[self._current_sequence_index]
        discard_folder = self._validate_discard_folder_for_action()
        if discard_folder is None:
            return

        selected_index = self._image_viewer.get_selected_index()
        all_paths = list(seq.image_paths)
        skipped_paths = (
            [all_paths[selected_index]]
            if 0 <= selected_index < len(all_paths)
            else all_paths
        )

        if not skipped_paths:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Skip",
            (
                f"Move {len(skipped_paths)} image(s) from sequence {seq.id} "
                "to the discard folder?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            dest_paths = bulk_skip(skipped_paths, str(discard_folder))
            remaining_paths = [path for path in all_paths if path not in skipped_paths]
            self._sequences[self._current_sequence_index] = Sequence(
                id=seq.id,
                image_paths=remaining_paths,
                start_ts=seq.start_ts,
                end_ts=seq.end_ts,
            )
            self._undo_stack.push(
                Action(
                    action_type=ActionType.DISCARD,
                    src_paths=skipped_paths,
                    dst_paths=dest_paths,
                    sequence_id=seq.id,
                    category=None,
                    operator=getattr(self.settings, "operator_name", "unknown"),
                )
            )
            self._status_label.setText(
                f"Skipped {len(skipped_paths)} image(s) from sequence {seq.id}"
            )
            self._refresh_sequence_list()
            if remaining_paths:
                self._display_sequence(self._current_sequence_index)
            else:
                self._next_sequence()
        except Exception as exc:  # pragma: no cover - defensive UX path
            QMessageBox.critical(self, "Skip Failed", str(exc))
            logger.exception("Failed to skip files from sequence %s: %s", seq.id, exc)

    def _discard_sequence(self) -> None:
        """Discard the current sequence."""
        if not (0 <= self._current_sequence_index < len(self._sequences)):
            return

        seq = self._sequences[self._current_sequence_index]
        reply = QMessageBox.question(
            self,
            "Confirm Discard",
            f"Discard sequence {seq.id} ({len(seq.image_paths)} images)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        discard_folder = self._validate_discard_folder_for_action()
        if discard_folder is None:
            return

        try:
            dest_paths: list[str] = []
            original_paths = list(seq.image_paths)
            discard_files(original_paths, str(discard_folder), safe=True)
            discard_root = Path(discard_folder)
            for src in original_paths:
                src_path = Path(str(src))
                dest_paths.append(str(discard_root / src_path.name))

            action = Action(
                action_type=ActionType.DISCARD,
                src_paths=original_paths,
                dst_paths=dest_paths,
                sequence_id=seq.id,
                category=None,
                operator=getattr(self.settings, "operator_name", "unknown"),
            )
            self._undo_stack.push(action)
            self._status_label.setText(f"Discarded sequence {seq.id}")
            self._next_sequence()
        except Exception as exc:  # pragma: no cover - defensive UX path
            QMessageBox.critical(self, "Discard Failed", str(exc))
            logger.exception("Failed to discard sequence %s: %s", seq.id, exc)

    def _restore_sequence_paths_after_undo(self, action: Action) -> None:
        """Restore the in-memory sequence paths after undoing a discard/skip."""
        if action.action_type != ActionType.DISCARD:
            return

        for idx, seq in enumerate(self._sequences):
            if seq.id != action.sequence_id:
                continue

            restored_paths = list(
                dict.fromkeys([*action.src_paths, *seq.image_paths])
            )
            self._sequences[idx] = Sequence(
                id=seq.id,
                image_paths=restored_paths,
                start_ts=seq.start_ts,
                end_ts=seq.end_ts,
            )
            self._refresh_sequence_list()
            if 0 <= self._current_sequence_index < len(self._sequences):
                self._display_sequence(self._current_sequence_index)
            break

    def _undo_action(self) -> None:
        """Undo the most recent action."""
        if not self._undo_stack.can_undo():
            QMessageBox.information(self, "No Action", "Nothing to undo")
            return

        action = self._undo_stack.pop()
        if action:
            self._undo_stack.reverse_action(action)
            self._restore_sequence_paths_after_undo(action)
            self._status_label.setText(f"Undid action on sequence {action.sequence_id}")

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle review shortcuts.

        Keyboard shortcuts:
        - Space: next sequence
        - Backspace: undo if available; otherwise previous sequence
        - D: discard current sequence
        - L/R: rotate selected image left/right
        - +/-: zoom selected image in/out
        - 1..9: apply the matching category if present
        """
        key = event.key()

        if key == Qt.Key.Key_Space:
            self._next_sequence()
            return
        if key == Qt.Key.Key_Backspace:
            self._handle_backspace_shortcut()
            return
        if key == Qt.Key.Key_D:
            self._discard_sequence()
            return
        if key == Qt.Key.Key_L:
            self._image_viewer.rotate_selected_left()
            return
        if key == Qt.Key.Key_R:
            self._image_viewer.rotate_selected_right()
            return
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self._image_viewer.zoom_selected_in()
            return
        if key == Qt.Key.Key_Minus:
            self._image_viewer.zoom_selected_out()
            return
        if Qt.Key.Key_1 <= key <= Qt.Key.Key_9:
            self._handle_category_shortcut(key)
            return

        super().keyPressEvent(event)

    def _handle_backspace_shortcut(self) -> None:
        """Handle Backspace as undo-or-previous navigation."""
        if self._undo_stack.can_undo():
            self._undo_action()
        else:
            self._previous_sequence()

    def _handle_category_shortcut(self, key: int) -> None:
        """Apply the category bound to a numeric shortcut key."""
        index = key - Qt.Key.Key_1
        if 0 <= index < len(self._categories):
            cat = self._categories[index]
            cat_id = str(cat.get("id", ""))
            category_name = str(cat.get("name", ""))
            if cat_id and category_name:
                self._classify_sequence(cat_id, category_name)

    def set_classifier(self, classifier: Classifier) -> None:
        """Set the classifier for performing classifications.

        Args:
            classifier: Classifier instance to use.
        """
        self._classifier = classifier

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        if self._classifier:
            self._classifier.stop()
        event.accept()
