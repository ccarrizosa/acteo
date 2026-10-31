from datetime import datetime
from pathlib import Path

from acteo.classifier import Classifier
from acteo.sequence_loader import Sequence
from acteo.settings import Settings


def make_seq(tmp_path: Path, count: int = 2) -> Sequence:
    imgs: list[str] = []
    for i in range(count):
        p = tmp_path / f"img{i}.jpg"
        p.write_bytes(b"\xff\xd8\xff\xd9")
        imgs.append(str(p))
    start = datetime.utcnow()
    end = datetime.utcnow()
    return Sequence(id="s1", image_paths=imgs, start_ts=start, end_ts=end)


def test_classifier_move_and_log(tmp_path: Path) -> None:
    out = tmp_path / "out"
    settings = Settings()
    settings.output_folder = str(out)
    settings.metadata_file_path = str(tmp_path / "meta.csv")
    settings.move_mode = "move"
    clf = Classifier(settings)
    clf.start()
    seq = make_seq(tmp_path)
    res = clf.classify_sequence(seq, category="test")
    assert res.operation == "move"
    clf.stop()
    category_dir = out / "test"
    for p in seq.image_paths:
        assert not Path(p).exists()
        expected = category_dir / Path(p).name
        assert expected.exists()
    assert Path(settings.metadata_file_path).exists()


def test_classifier_copy_and_log(tmp_path: Path) -> None:
    out = tmp_path / "out2"
    settings = Settings()
    settings.output_folder = str(out)
    settings.metadata_file_path = str(tmp_path / "meta2.csv")
    settings.move_mode = "copy"
    clf = Classifier(settings)
    clf.start()
    seq = make_seq(tmp_path)
    res = clf.classify_sequence(seq, category="test2")
    assert res.operation == "copy"
    clf.stop()
    category_dir = out / "test2"
    for p in seq.image_paths:
        assert Path(p).exists()
        expected = category_dir / Path(p).name
        assert expected.exists()
    assert Path(settings.metadata_file_path).exists()
