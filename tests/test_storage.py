from pathlib import Path

from acteo.storage import bulk_skip, safe_copy, safe_move


def test_safe_copy_and_move(tmp_path: Path) -> None:
    src = tmp_path / "a.txt"
    src.write_text("data")
    dst = tmp_path / "out" / "a.txt"
    safe_copy(str(src), str(dst))
    assert dst.exists()

    # move
    dst2 = tmp_path / "out2" / "a.txt"
    safe_move(str(dst), str(dst2))
    assert dst2.exists()


def test_bulk_skip_can_delete_instead_of_moving(tmp_path: Path) -> None:
    src = tmp_path / "a.txt"
    src.write_text("data")
    discard_dir = tmp_path / "discard"

    destinations = bulk_skip([str(src)], str(discard_dir), safe=False)

    assert not src.exists()
    assert destinations == []
    assert not discard_dir.exists()
