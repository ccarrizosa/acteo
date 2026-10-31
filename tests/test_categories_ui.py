from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from acteo.categories import load_categories, save_categories
from acteo.main_window import MainWindow
from acteo.settings import Settings


def test_categories_round_trip_from_disk(tmp_path: Path) -> None:
    path = tmp_path / "categories.json"
    items = [{"id": "cat_1", "name": "deer"}, {"id": "cat_2", "name": "boar"}]
    save_categories(str(path), items)

    assert load_categories(str(path)) == items


def test_main_window_category_crud_and_missing_file(tmp_path: Path) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    settings = Settings(category_file_path=str(tmp_path / "missing_categories.json"))
    window = MainWindow(settings=settings)

    assert window._categories == []
    assert window._load_categories_from_disk() == []

    window._categories = [{"id": "cat_1", "name": "deer"}]
    window._save_categories_to_disk()
    assert load_categories(str(settings.category_file_path)) == [
        {"id": "cat_1", "name": "deer"}
    ]

    window._rename_category("deer", "elk")
    assert window._categories == [{"id": "cat_1", "name": "elk"}]

    window._remove_category("elk")
    assert window._categories == []
