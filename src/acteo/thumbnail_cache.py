"""Minimal in-memory thumbnail cache for Acteo.

This cache avoids repeatedly decoding the same image when the viewer rebuilds the
thumbnail strip or re-renders the selected preview. The implementation is kept
small and testable: it caches decoded QPixmap objects keyed by file path and the
requested display size. Entries are invalidated when the underlying file's mtime
or size changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication


@dataclass
class _CacheEntry:
    """Cached thumbnail payload for one file/size combination."""

    pixmap: QPixmap
    mtime_ns: int
    size: int
    file_size: int


class ThumbnailCache:
    """Simple cache for decoded image thumbnails in memory."""

    def __init__(self) -> None:
        self._cache: Dict[tuple[str, int], _CacheEntry] = {}
        self.hits = 0
        self.misses = 0
        self.invalidations = 0

    def get(self, path: str, *, size: int) -> Optional[QPixmap]:
        """Return a cached thumbnail if still valid, else decode and cache it."""
        key = (str(path), max(1, int(size)))
        stat = Path(path).stat() if Path(path).exists() else None
        if stat is None:
            return None

        current_mtime_ns = int(stat.st_mtime_ns)
        current_file_size = int(stat.st_size)
        entry = self._cache.get(key)
        if entry is not None and (
            entry.mtime_ns == current_mtime_ns and entry.file_size == current_file_size
        ):
            self.hits += 1
            return entry.pixmap

        if entry is not None:
            self.invalidations += 1
            self._cache.pop(key, None)

        if QApplication.instance() is None:
            return None

        pixmap = QPixmap(path)
        if pixmap.isNull():
            return None

        scaled = pixmap.scaled(
            max(1, int(size)),
            max(1, int(size)),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._cache[key] = _CacheEntry(
            pixmap=scaled,
            mtime_ns=current_mtime_ns,
            size=size,
            file_size=current_file_size,
        )
        self.misses += 1
        return scaled

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
        self.invalidations = 0
