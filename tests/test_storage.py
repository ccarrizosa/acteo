from pathlib import Path

from acteo.storage import safe_copy, safe_move


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
