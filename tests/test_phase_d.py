from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog
from pytest import MonkeyPatch

from acteo.categories import export_categories, import_categories
from acteo.logger import export_sequence_report
from acteo.main_window import MainWindow
from acteo.settings import Settings
from acteo.storage import bulk_skip


def test_categories_import_export_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "categories.json"
    categories = [
        {"id": "cat_1", "name": "deer"},
        {"id": "cat_2", "name": "fox"},
    ]

    export_categories(str(path), categories)
    reloaded = import_categories(str(path))

    assert reloaded == categories


def test_export_sequence_report_writes_csv(tmp_path: Path) -> None:
    path = tmp_path / "report.csv"
    rows = [
        {
            "sequence_id": "seq-1",
            "image_count": 2,
            "category": "deer",
            "operation": "move",
        },
        {
            "sequence_id": "seq-2",
            "image_count": 3,
            "category": "fox",
            "operation": "copy",
        },
    ]

    export_sequence_report(str(path), rows)

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "sequence_id" in text
    assert "seq-1" in text
    assert "seq-2" in text


def test_bulk_skip_moves_files_to_discard_folder(tmp_path: Path) -> None:
    source = tmp_path / "source"
    discard = tmp_path / "discard"
    source.mkdir()

    captured = source / "sample.jpg"
    captured.write_bytes(b"test")

    bulk_skip([str(captured)], str(discard))

    assert not captured.exists()
    assert (discard / "sample.jpg").exists()


def test_main_window_export_report_writes_csv(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    export_path = tmp_path / "exports" / "report.csv"
    window = MainWindow(settings=Settings())
    window._classification_rows = [
        {
            "sequence_id": "seq-1",
            "image_count": 2,
            "image_paths": '["/tmp/a.jpg", "/tmp/b.jpg"]',
            "start_ts": "2024-01-01T00:00:00",
            "end_ts": "2024-01-01T00:00:05",
            "category": "deer",
            "operator": "tester",
            "timestamp_processed": "2024-01-01T00:00:30",
            "operation": "move",
            "destination_paths": '["/tmp/output/deer/a.jpg", "/tmp/output/deer/b.jpg"]',
        }
    ]

    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(export_path), "CSV files (*.csv)"),
    )

    window._export_report()

    assert export_path.exists()
    text = export_path.read_text(encoding="utf-8")
    assert "sequence_id" in text
    assert "image_count" in text
    assert "category" in text
    assert "seq-1" in text
    assert "deer" in text
    assert "destination_paths" in text
