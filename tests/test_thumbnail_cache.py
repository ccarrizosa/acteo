from __future__ import annotations

import os
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication

from acteo.thumbnail_cache import ThumbnailCache


def test_thumbnail_cache_hits_for_same_file_and_size(tmp_path: Path) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    img = tmp_path / "cache_hit.jpg"
    Image.new("RGB", (64, 64), color="blue").save(img)

    cache = ThumbnailCache()
    first = cache.get(str(img), size=120)
    second = cache.get(str(img), size=120)

    assert first is not None
    assert second is not None
    assert cache.hits == 1
    assert cache.misses == 1


def test_thumbnail_cache_invalidates_when_file_changes(tmp_path: Path) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    img = tmp_path / "cache_invalidate.jpg"
    Image.new("RGB", (64, 64), color="red").save(img)

    cache = ThumbnailCache()
    first = cache.get(str(img), size=150)
    assert first is not None

    Image.new("RGB", (128, 128), color="green").save(img)
    os.utime(img, (img.stat().st_atime + 5, img.stat().st_mtime + 5))

    second = cache.get(str(img), size=150)

    assert second is not None
    assert first is not second
    assert cache.invalidations == 1
