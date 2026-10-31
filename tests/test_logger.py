import concurrent.futures
from pathlib import Path

from acteo.logger import BackgroundCSVWriter, append_sequence_metadata


def test_append_sequence_metadata(tmp_path: Path) -> None:
    p = tmp_path / "meta.csv"
    row = {"sequence_id": "1", "image_count": 2}
    append_sequence_metadata(str(p), row, fieldnames=["sequence_id", "image_count"])
    assert p.exists()


def test_background_writer_concurrent(tmp_path: Path) -> None:
    p = tmp_path / "meta_bg.csv"
    fieldnames = ["id", "value"]
    writer = BackgroundCSVWriter(str(p), fieldnames)
    writer.start()
    items = [{"id": str(i), "value": i} for i in range(50)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as exc:
        futures = [exc.submit(writer.put, it) for it in items]
        for f in concurrent.futures.as_completed(futures):
            f.result()
    writer.stop()
    # simple sanity: file exists and has expected number of data lines
    lines = p.read_text(encoding="utf-8").splitlines()
    # 1 header + 50 rows
    assert len(lines) == 1 + len(items)
