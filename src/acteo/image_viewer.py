"""Image viewer widget for displaying a grid of images with zoom/rotate.

This module provides the ImageViewer PySide6 widget that displays a selected
image in a large top pane and a thumbnail strip with filenames at the bottom.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from typing_extensions import override

from .thumbnail_cache import ThumbnailCache

if TYPE_CHECKING:
    from PySide6.QtGui import QMouseEvent, QResizeEvent


class ImageTile(QWidget):
    """A single thumbnail tile in the grid that includes the thumbnail and name."""

    clicked = Signal(int)  # Emit index when clicked

    def __init__(
        self,
        path: str,
        index: int,
        size: int = 150,
        cache: Optional[ThumbnailCache] = None,
    ) -> None:
        """Initialize a tile.

        Args:
            path: File path to the image.
            index: Index in the sequence.
            size: Desired tile size in pixels.
            cache: Shared thumbnail cache used to avoid repeated decoding.
        """
        super().__init__()
        self.path = path
        self.index = index
        self.tile_size = size
        self.zoom_factor = 1.0
        self.rotation = 0  # degrees
        self.selected = False
        self._cache = cache or ThumbnailCache()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._display_label = QLabel()
        self._display_label.setFixedSize(size, size)
        self._display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display_label.setStyleSheet(
            "border: 1px solid #cccccc; background: #f3f3f3;"
        )
        self._layout.addWidget(self._display_label)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("border: 1px solid #cccccc; padding: 2px;")
        self._load_and_display()

    def _load_and_display(self) -> None:
        """Load image from disk and paint it together with its filename."""
        try:
            cached = self._cache.get(self.path, size=self.tile_size)
            if cached is None:
                self._display_label.setText(f"Error loading\n{Path(self.path).name}")
                return

            pixmap = cached
            if self.rotation != 0:
                transform = QTransform()
                transform.rotate(self.rotation)
                pixmap = pixmap.transformed(
                    transform, Qt.TransformationMode.SmoothTransformation
                )

            base = pixmap.scaledToWidth(
                int(self.tile_size * self.zoom_factor),
                Qt.TransformationMode.SmoothTransformation,
            )
            if base.height() > self.tile_size:
                base = pixmap.scaledToHeight(
                    int(self.tile_size * self.zoom_factor),
                    Qt.TransformationMode.SmoothTransformation,
                )

            canvas = QPixmap(self.tile_size, self.tile_size)
            canvas.fill("#f3f3f3")

            painter = QPainter(canvas)
            try:
                x_offset = max(0, (self.tile_size - base.width()) // 2)
                y_offset = 0
                painter.drawPixmap(x_offset, y_offset, base)

                footer_height = max(14, int(self.tile_size * 0.18))
                footer_rect = canvas.rect().adjusted(
                    0,
                    self.tile_size - footer_height,
                    0,
                    0,
                )
                painter.fillRect(footer_rect, QColor(245, 245, 245, 220))
                painter.setPen(Qt.GlobalColor.black)
                painter.setFont(self.font())
                painter.drawText(
                    footer_rect.adjusted(4, 0, -4, 0),
                    Qt.AlignmentFlag.AlignCenter,
                    Path(self.path).name,
                )
            finally:
                painter.end()

            self._display_label.setPixmap(canvas)
            self._display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception as exc:  # pragma: no cover - defensive UI fallback
            self._display_label.setText(f"Error: {str(exc)[:20]}")

    def rotate_right(self) -> None:
        """Rotate image 90 degrees clockwise."""
        self.rotation = (self.rotation + 90) % 360
        self._load_and_display()

    def rotate_left(self) -> None:
        """Rotate image 90 degrees counter-clockwise."""
        self.rotation = (self.rotation - 90) % 360
        self._load_and_display()

    def zoom_in(self) -> None:
        """Zoom in (increase scale)."""
        self.zoom_factor = min(self.zoom_factor + 0.1, 2.0)
        self._load_and_display()

    def zoom_out(self) -> None:
        """Zoom out (decrease scale)."""
        self.zoom_factor = max(self.zoom_factor - 0.1, 0.5)
        self._load_and_display()

    def set_selected(self, selected: bool) -> None:
        """Highlight this tile as selected."""
        self.selected = selected
        if selected:
            self.setStyleSheet("border: 2px solid #0078d4; padding: 2px;")
        else:
            self.setStyleSheet("border: 1px solid #cccccc; padding: 2px;")

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Emit clicked signal when tile is clicked."""
        self.clicked.emit(self.index)


class ImageViewer(QWidget):
    """Viewer with a large selected-image pane and thumbnail strip."""

    image_selected = Signal(str, int)  # sequence_id, image_index

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the image viewer."""
        super().__init__(parent)
        self._sequence_id: Optional[str] = None
        self._image_paths: List[str] = []
        self._tiles: List[ImageTile] = []
        self._selected_index = 0
        self._cols = 4
        self._thumbnail_cache = ThumbnailCache()

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI layout."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._preview_container = QWidget()
        self._preview_layout = QVBoxLayout(self._preview_container)
        self._preview_layout.setContentsMargins(8, 8, 8, 8)

        self._preview_title = QLabel("Selected image")
        self._preview_title.setStyleSheet("font-weight: 600; margin-bottom: 4px;")
        self._preview_label = QLabel("No image selected")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet(
            "background: #f4f4f4; border: 1px solid #d0d0d0; min-height: 320px;"
        )
        self._preview_label.setWordWrap(True)

        self._preview_name = QLabel("")
        self._preview_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_name.setStyleSheet("color: #444444; margin-top: 4px;")

        self._preview_layout.addWidget(self._preview_title)
        self._preview_layout.addWidget(self._preview_label, 1)
        self._preview_layout.addWidget(self._preview_name)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout()
        self._grid_layout.setSpacing(6)
        self._grid_widget.setLayout(self._grid_layout)
        self._scroll.setWidget(self._grid_widget)

        layout.addWidget(self._preview_container, 3)
        layout.addWidget(self._scroll, 2)
        self.setLayout(layout)

    def _update_selected_preview(self) -> None:
        """Refresh the large preview based on the currently selected tile."""
        if not self._tiles:
            self._preview_label.setText("No image selected")
            self._preview_name.setText("")
            return

        path = self._image_paths[self._selected_index]
        pixmap = self._thumbnail_cache.get(
            path,
            size=max(1, self._preview_label.width()),
        )
        if pixmap is None:
            self._preview_label.setText(f"Error loading\n{Path(path).name}")
            self._preview_name.setText(Path(path).name)
            return

        preview_size = self._preview_label.size()
        scaled = pixmap.scaled(
            preview_size.width() - 20,
            preview_size.height() - 20,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_label.setPixmap(scaled)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_name.setText(Path(path).name)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        """Keep the selected preview scaled to the current pane size."""
        super().resizeEvent(event)
        self._update_selected_preview()

    def set_sequence(self, sequence_id: str, image_paths: List[str]) -> None:
        """Display a sequence of images."""
        self._sequence_id = sequence_id
        self._image_paths = image_paths
        self._selected_index = 0

        while self._tiles:
            tile = self._tiles.pop()
            tile.deleteLater()

        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        for i, path in enumerate(image_paths):
            tile = ImageTile(path, i, size=130, cache=self._thumbnail_cache)
            tile.clicked.connect(self._on_tile_clicked)
            self._tiles.append(tile)

        for i, tile in enumerate(self._tiles):
            row = i // self._cols
            col = i % self._cols
            self._grid_layout.addWidget(tile, row, col)

        if self._tiles:
            self._tiles[0].set_selected(True)
        self._update_selected_preview()

    def _on_tile_clicked(self, index: int) -> None:
        """Handle tile click."""
        if 0 <= index < len(self._tiles):
            if self._selected_index < len(self._tiles):
                self._tiles[self._selected_index].set_selected(False)
            self._selected_index = index
            self._tiles[index].set_selected(True)
            self._update_selected_preview()
            if self._sequence_id:
                self.image_selected.emit(self._sequence_id, index)

    def rotate_selected_right(self) -> None:
        """Rotate the selected image 90 degrees clockwise."""
        if 0 <= self._selected_index < len(self._tiles):
            self._tiles[self._selected_index].rotate_right()
            self._update_selected_preview()

    def rotate_selected_left(self) -> None:
        """Rotate the selected image 90 degrees counter-clockwise."""
        if 0 <= self._selected_index < len(self._tiles):
            self._tiles[self._selected_index].rotate_left()
            self._update_selected_preview()

    def zoom_selected_in(self) -> None:
        """Zoom in on the selected image."""
        if 0 <= self._selected_index < len(self._tiles):
            self._tiles[self._selected_index].zoom_in()
            self._update_selected_preview()

    def zoom_selected_out(self) -> None:
        """Zoom out on the selected image."""
        if 0 <= self._selected_index < len(self._tiles):
            self._tiles[self._selected_index].zoom_out()
            self._update_selected_preview()

    def get_selected_index(self) -> int:
        """Return the index of the currently selected image."""
        return self._selected_index

    def select_next(self) -> None:
        """Select the next image in the grid."""
        if self._tiles:
            next_idx = (self._selected_index + 1) % len(self._tiles)
            self._on_tile_clicked(next_idx)

    def select_previous(self) -> None:
        """Select the previous image in the grid."""
        if self._tiles:
            prev_idx = (self._selected_index - 1) % len(self._tiles)
            self._on_tile_clicked(prev_idx)
