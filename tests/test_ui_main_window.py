from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
from pytest import MonkeyPatch

from acteo.classifier import ClassificationResult
from acteo.image_viewer import ImageTile
from acteo.main_window import MainWindow
from acteo.sequence_loader import Sequence
from acteo.settings import Settings
from acteo.thumbnail_cache import ThumbnailCache
from acteo.undo import ActionType


def test_main_window_sets_sequences_and_populates_viewer(tmp_path: Path) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    img1 = tmp_path / "example_1.jpg"
    img2 = tmp_path / "example_2.jpg"
    img1.write_bytes(b"\xff\xd8\xff\xd9")
    img2.write_bytes(b"\xff\xd8\xff\xd9")

    seq = Sequence(
        id="seq-1",
        image_paths=[str(img1), str(img2)],
        start_ts=datetime.utcnow(),
        end_ts=datetime.utcnow(),
    )

    window = MainWindow(settings=Settings(), sequences=[seq])

    assert window._sequence_list.count() == 1
    assert len(window._image_viewer._tiles) == 2
    assert window._image_viewer.get_selected_index() == 0


def test_main_window_autoplay_cycles_images_in_current_sequence(tmp_path: Path) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    img1 = tmp_path / "autoplay_1.jpg"
    img2 = tmp_path / "autoplay_2.jpg"
    img1.write_bytes(b"\xff\xd8\xff\xd9")
    img2.write_bytes(b"\xff\xd8\xff\xd9")

    seq = Sequence(
        id="seq-auto",
        image_paths=[str(img1), str(img2)],
        start_ts=datetime.utcnow(),
        end_ts=datetime.utcnow(),
    )

    settings = Settings(autoplay_interval_seconds=1)
    window = MainWindow(settings=settings, sequences=[seq])

    assert window.settings.autoplay_interval_seconds == 1
    window._toggle_play_pause()
    assert window._autoplay_timer.isActive()

    window._advance_autoplay()
    assert window._image_viewer.get_selected_index() == 1

    window._toggle_play_pause()
    assert not window._autoplay_timer.isActive()


def test_thumbnail_tile_size_matches_thumbnail_dimensions(tmp_path: Path) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    img = tmp_path / "miniature.jpg"
    img.write_bytes(b"\xff\xd8\xff\xd9")

    tile = ImageTile(str(img), 0, size=130, cache=ThumbnailCache())

    assert tile._display_label.size().height() == 130
    assert tile._display_label.size().width() == 130


def test_main_window_discard_sequence_moves_files_and_supports_undo(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    discard_dir = tmp_path / "discard"
    settings = Settings(discard_folder=str(discard_dir))

    img1 = tmp_path / "discard_1.jpg"
    img2 = tmp_path / "discard_2.jpg"
    img1.write_bytes(b"\xff\xd8\xff\xd9")
    img2.write_bytes(b"\xff\xd8\xff\xd9")

    seq = Sequence(
        id="seq-discard",
        image_paths=[str(img1), str(img2)],
        start_ts=datetime.utcnow(),
        end_ts=datetime.utcnow(),
    )

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    window = MainWindow(settings=settings, sequences=[seq])
    window._discard_sequence()

    assert not img1.exists()
    assert not img2.exists()
    assert (discard_dir / img1.name).exists()
    assert (discard_dir / img2.name).exists()
    assert window._undo_stack.size() == 1
    peeked = window._undo_stack.peek()
    assert peeked is not None
    assert peeked.action_type == ActionType.DISCARD

    window._undo_action()

    assert img1.exists()
    assert img2.exists()
    assert not (discard_dir / img1.name).exists()
    assert not (discard_dir / img2.name).exists()


def test_main_window_bulk_skip_selected_images_and_undo(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    discard_dir = tmp_path / "discard"
    settings = Settings(discard_folder=str(discard_dir))

    img1 = tmp_path / "skip_1.jpg"
    img2 = tmp_path / "skip_2.jpg"
    img1.write_bytes(b"\xff\xd8\xff\xd9")
    img2.write_bytes(b"\xff\xd8\xff\xd9")

    seq = Sequence(
        id="seq-skip",
        image_paths=[str(img1), str(img2)],
        start_ts=datetime.utcnow(),
        end_ts=datetime.utcnow(),
    )

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    window = MainWindow(settings=settings, sequences=[seq])
    window._image_viewer._selected_index = 0

    window._skip_selected_images()

    assert not img1.exists()
    assert img2.exists()
    assert (discard_dir / img1.name).exists()
    assert len(window._sequences[0].image_paths) == 1
    assert window._undo_stack.size() == 1
    peeked = window._undo_stack.peek()
    assert peeked is not None
    assert peeked.action_type == ActionType.DISCARD

    window._undo_action()

    assert img1.exists()
    assert not (discard_dir / img1.name).exists()
    assert window._sequences[0].image_paths == [str(img1), str(img2)]


def test_main_window_handles_empty_scan_without_crashing(tmp_path: Path) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    empty_dir = tmp_path / "empty folder"
    empty_dir.mkdir()

    window = MainWindow(settings=Settings(input_folder=str(empty_dir)))
    window._rebuild_sequences_for_current_settings()

    assert window._sequence_list.count() == 0
    assert "No images found" in window._status_label.text()


def test_main_window_warns_for_missing_output_or_discard_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    img = tmp_path / "img.jpg"
    img.write_bytes(b"\xff\xd8\xff\xd9")
    seq = Sequence(
        id="seq-config",
        image_paths=[str(img)],
        start_ts=datetime.utcnow(),
        end_ts=datetime.utcnow(),
    )
    settings = Settings(output_folder=None, discard_folder=None)
    window = MainWindow(settings=settings, sequences=[seq])

    warnings: list[tuple[str, str]] = []

    def fake_warning(parent, title, message):
        warnings.append((title, message))

    monkeypatch.setattr(QMessageBox, "warning", fake_warning)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    window._discard_sequence()
    assert warnings and warnings[0][0] == "Discard folder missing"

    class FakeClassifier:
        def classify_sequence(self, sequence: Sequence, category: str):
            raise ValueError("output_folder must be configured in settings")

    window.set_classifier(FakeClassifier())  # type: ignore[arg-type]
    window._classify_sequence("cat_1", "deer")
    assert any(title == "Output folder missing" for title, _ in warnings)


def test_main_window_marks_classified_sequences_in_sequence_view(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    img1 = tmp_path / "classified_1.jpg"
    img2 = tmp_path / "classified_2.jpg"
    img1.write_bytes(b"\xff\xd8\xff\xd9")
    img2.write_bytes(b"\xff\xd8\xff\xd9")

    seq = Sequence(
        id="seq-classified",
        image_paths=[str(img1), str(img2)],
        start_ts=datetime.utcnow(),
        end_ts=datetime.utcnow(),
    )

    class FakeClassifier:
        def classify_sequence(
            self,
            sequence: Sequence,
            category: str,
        ) -> ClassificationResult:
            return ClassificationResult(
                sequence_id=sequence.id,
                operation="move",
                destination_paths=[str(output_dir / category / img1.name)],
            )

    window = MainWindow(
        settings=Settings(output_folder=str(output_dir)), sequences=[seq]
    )
    window.set_classifier(FakeClassifier())  # type: ignore[arg-type]

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)

    window._classify_sequence("cat_1", "deer")

    display_labels = [
        window._sequence_list.item(i).text()
        for i in range(window._sequence_list.count())
    ]
    assert any("classified" in label.lower() for label in display_labels)


def test_main_window_rebuilds_sequences_when_grouping_mode_changes(
    tmp_path: Path,
) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    input_dir = tmp_path / "images"
    input_dir.mkdir()

    for idx in range(1, 7):
        image = input_dir / f"img{idx}.jpg"
        image.write_bytes(b"\xff\xd8\xff\xd9")

    settings = Settings(
        input_folder=str(input_dir),
        grouping_mode="timestamp_gap",
        timestamp_gap_seconds=10,
        fixed_group_size=3,
        exif_priority=False,
    )
    window = MainWindow(settings=settings)

    window.settings.grouping_mode = "fixed_size"
    window.settings.fixed_group_size = 3
    window._rebuild_sequences_for_current_settings()

    assert len(window._sequences) == 2
    assert [len(seq.image_paths) for seq in window._sequences] == [3, 3]


def test_main_window_keyboard_shortcuts_via_qt_events(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    img1 = tmp_path / "shortcut_1.jpg"
    img2 = tmp_path / "shortcut_2.jpg"
    img1.write_bytes(b"\xff\xd8\xff\xd9")
    img2.write_bytes(b"\xff\xd8\xff\xd9")

    seq1 = Sequence(
        id="s1",
        image_paths=[str(img1)],
        start_ts=datetime.utcnow(),
        end_ts=datetime.utcnow(),
    )
    seq2 = Sequence(
        id="s2",
        image_paths=[str(img2)],
        start_ts=datetime.utcnow(),
        end_ts=datetime.utcnow(),
    )

    settings = Settings()
    window = MainWindow(settings=settings, sequences=[seq1, seq2])
    window.setFocus()
    window._categories = [
        {"id": "cat_1", "name": "deer"},
        {"id": "cat_2", "name": "boar"},
    ]
    window._refresh_category_buttons()

    calls: list[tuple[str, str]] = []

    def fake_classify(category_id: str, category_name: str) -> None:
        calls.append((category_id, category_name))

    monkeypatch.setattr(window, "_classify_sequence", fake_classify)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    QTest.keyClick(window, Qt.Key.Key_Space)
    assert window._current_sequence_index == 1

    QTest.keyClick(window, Qt.Key.Key_Backspace)
    assert window._current_sequence_index == 0

    window._image_viewer._selected_index = 0
    QTest.keyClick(window, Qt.Key.Key_L)
    assert window._image_viewer._tiles[0].rotation == 270

    QTest.keyClick(window, Qt.Key.Key_R)
    assert window._image_viewer._tiles[0].rotation == 0

    before_zoom = window._image_viewer._tiles[0].zoom_factor
    QTest.keyClick(window, Qt.Key.Key_Plus)
    assert window._image_viewer._tiles[0].zoom_factor > before_zoom

    QTest.keyClick(window, Qt.Key.Key_1)
    assert calls == [("cat_1", "deer")]
