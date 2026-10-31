import os
from datetime import datetime
from pathlib import Path

import pytest

from acteo.sequence_loader import (
    extract_image_timestamp,
    group_by_timestamp_gap,
)


def test_extract_image_timestamp_fallback(tmp_path: Path) -> None:
    # create a dummy file and set its mtime
    f = tmp_path / "img1.jpg"
    f.write_bytes(b"\xff\xd8\xff\xd9")  # minimal JPEG bytes
    ts = 1600000000.0
    os.utime(f, (ts, ts))
    dt = extract_image_timestamp(str(f), exif_priority=False)
    assert isinstance(dt, datetime)
    assert abs(dt.timestamp() - ts) < 1


@pytest.mark.skipif(
    not Path("resources/samples").exists(),
    reason="No sample images available",
)
def test_extract_image_timestamp_prefers_exif() -> None:
    # find the first sample image that has EXIF DateTimeOriginal
    samples = list(Path("resources/samples").glob("**/*.*"))
    assert samples, "No sample images found"
    found = False
    for s in samples:
        dt = extract_image_timestamp(str(s), exif_priority=True)
        if dt is not None:
            found = True
            break
    assert found, "No sample image with readable timestamp found"


def test_group_by_timestamp_gap_orders_and_groups(tmp_path: Path) -> None:
    # Create three files with timestamps such that first two are within gap
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    c = tmp_path / "c.jpg"
    a.write_bytes(b"\xff\xd8\xff\xd9")
    b.write_bytes(b"\xff\xd8\xff\xd9")
    c.write_bytes(b"\xff\xd8\xff\xd9")
    t0 = 1600000000.0
    os.utime(a, (t0, t0))
    os.utime(b, (t0 + 5, t0 + 5))
    os.utime(c, (t0 + 100, t0 + 100))
    files = [str(p) for p in sorted(tmp_path.iterdir())]
    seqs = group_by_timestamp_gap(files, gap_seconds=10)
    assert len(seqs) == 2
    assert len(seqs[0].image_paths) == 2
    assert len(seqs[1].image_paths) == 1
