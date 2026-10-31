"""Safe file operations with atomic commit semantics.

This module provides small helpers for moving, copying and discarding files
while attempting to perform operations atomically where possible. These
helpers intentionally avoid platform-specific locks and instead prefer
temporary-file + `os.replace()` semantics which are available on major OSes.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterable, List

logger = logging.getLogger(__name__)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def safe_move(src: str, dst: str) -> None:
    """Move `src` to `dst` using an atomic replace when possible.

    Args:
        src: Source file path.
        dst: Destination file path.
    """
    s = Path(src)
    d = Path(dst)
    _ensure_parent(d)
    try:
        # Attempt an atomic rename first (fast on same filesystem)
        s.replace(d)
    except Exception:
        # Fall back to copy+remove for cross-device moves
        tmp = None
        try:
            tmpf = tempfile.NamedTemporaryFile(delete=False, dir=str(d.parent))
            tmp = Path(tmpf.name)
            tmpf.close()
            shutil.copy2(s, tmp)
            os.replace(tmp, d)
            s.unlink()
        finally:
            if tmp and tmp.exists():
                try:
                    tmp.unlink()
                except Exception:
                    logger.debug("Failed to remove temp file %s", tmp)


def safe_copy(src: str, dst: str) -> None:
    """Copy `src` to `dst` atomically where possible.

    Args:
        src: Source file path.
        dst: Destination file path.
    """
    s = Path(src)
    d = Path(dst)
    _ensure_parent(d)
    tmp: Path | None = None
    try:
        tmpf = tempfile.NamedTemporaryFile(delete=False, dir=str(d.parent))
        tmp = Path(tmpf.name)
        tmpf.close()
        shutil.copy2(s, tmp)
        os.replace(tmp, d)
    finally:
        if tmp and tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                logger.debug("Failed to remove temp file %s", tmp)


def discard_files(paths: Iterable[str], discard_folder: str, safe: bool = True) -> None:
    """Discard files by moving them to `discard_folder` or deleting.

    Args:
        paths: Iterable of file paths to discard.
        discard_folder: Destination folder for safe discards.
        safe: If True, move files to `discard_folder`; otherwise delete.
    """
    d = Path(discard_folder)
    d.mkdir(parents=True, exist_ok=True)
    for p in paths:
        src = Path(p)
        dest = d / src.name
        if safe:
            safe_move(str(src), str(dest))
        else:
            try:
                src.unlink()
            except Exception as exc:
                logger.exception("Failed to delete %s: %s", src, exc)


def bulk_skip(paths: Iterable[str], discard_folder: str) -> List[str]:
    """Move several files to a discard directory and return their destination paths.

    This is the bulk counterpart to `discard_files` and is intended for Phase D
    “skip” operations in the UI.
    """
    destinations: List[str] = []
    d = Path(discard_folder)
    d.mkdir(parents=True, exist_ok=True)
    for p in paths:
        src = Path(p)
        dst = d / src.name
        safe_move(str(src), str(dst))
        destinations.append(str(dst))
    return destinations


def bulk_skip_sequence(sequence_paths: Iterable[str], discard_folder: str) -> List[str]:
    """Skip all files in a sequence by moving them to the discard folder.

    Args:
        sequence_paths: Image paths to discard.
        discard_folder: Destination folder for discarded images.

    Returns:
        List of destination file paths that were moved.
    """
    return bulk_skip(sequence_paths, discard_folder)
