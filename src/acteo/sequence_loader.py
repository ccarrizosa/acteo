"""Sequence loader utilities.

This module provides lightweight helpers for scanning a folder for image
files and grouping them into sequences using a timestamp-gap heuristic. The
implementation is intentionally small and testable; it will be extended to
read EXIF timestamps and to handle large folders incrementally.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, cast

from dateutil import parser as _date_parser
from PIL import Image
from PIL.ExifTags import TAGS


@dataclass
class Sequence:
    """Represents a group of images captured together.

    Attributes:
        id: Deterministic identifier for the sequence (string).
        image_paths: Ordered list of file paths in the sequence.
        start_ts: Timestamp of the first image.
        end_ts: Timestamp of the last image.
        is_classified: Whether the sequence has already been classified.
        category: Category assigned to the sequence, if any.
    """

    id: str
    image_paths: List[str]
    start_ts: datetime
    end_ts: datetime
    is_classified: bool = False
    category: Optional[str] = None


def scan_folder(
    input_folder: Optional[str], *, patterns: Optional[Iterable[str]] = None
) -> List[str]:
    """Scan `input_folder` and return a sorted list of image file paths.

    Args:
        input_folder: Path to scan. If falsy, returns an empty list.
        patterns: Iterable of suffixes (e.g. ['.jpg', '.png']). Case-insensitive.

    Returns:
        Sorted list of absolute file paths as strings.
    """
    if not input_folder:
        return []
    p = Path(input_folder).expanduser()
    if not p.exists() or not p.is_dir():
        return []
    allowed = {s.lower() for s in (patterns or [".jpg", ".jpeg", ".png"]) }
    files: List[Path] = [
        f for f in p.iterdir() if f.is_file() and f.suffix.lower() in allowed
    ]
    files.sort()
    return [str(f.resolve()) for f in files]


def _resolve_timestamps(paths: List[str], exif_priority: bool) -> List[float]:
    """Resolve timestamps for a list of file paths.

    Returns a list of float POSIX timestamps, using EXIF when available.
    """
    rst: List[float] = []
    for fp in paths:
        dt = extract_image_timestamp(fp, exif_priority=exif_priority)
        if dt is None:
            rst.append(0.0)
        else:
            try:
                rst.append(float(dt.timestamp()))
            except Exception:
                rst.append(0.0)
    return rst


def _build_sequences(groups: List[List[str]], exif_priority: bool) -> List[Sequence]:
    """Build Sequence objects for grouped file paths."""
    results: List[Sequence] = []
    for i, grp in enumerate(groups):
        start_dt = extract_image_timestamp(grp[0], exif_priority=exif_priority)
        if not start_dt:
            try:
                start_dt = datetime.fromtimestamp(Path(grp[0]).stat().st_mtime)
            except Exception:
                start_dt = datetime.fromtimestamp(0)
        end_dt = extract_image_timestamp(grp[-1], exif_priority=exif_priority)
        if not end_dt:
            try:
                end_dt = datetime.fromtimestamp(Path(grp[-1]).stat().st_mtime)
            except Exception:
                end_dt = datetime.fromtimestamp(0)
        results.append(
            Sequence(id=str(i), image_paths=grp, start_ts=start_dt, end_ts=end_dt)
        )
    return results


def group_by_timestamp_gap(
    file_paths: List[str], gap_seconds: int = 10, *, exif_priority: bool = True
) -> List[Sequence]:
    """Group sorted `file_paths` into sequences using timestamps.

    Timestamps are obtained using `extract_image_timestamp`, which will prefer
    EXIF timestamps when `exif_priority=True` and fall back to filesystem
    modification time when EXIF is absent or unreadable.

    Args:
        file_paths: Sorted list of file paths (strings).
        gap_seconds: Maximum allowed gap in seconds between consecutive images
            for them to be considered part of the same sequence.
        exif_priority: If True, attempt to use EXIF DateTimeOriginal before
            falling back to mtime.

    Returns:
        List of `Sequence` objects.
    """
    if not file_paths:
        return []

    # Resolve timestamps using EXIF preference when requested.
    pts = _resolve_timestamps(file_paths, exif_priority)

    seqs: List[List[str]] = []
    cur: List[str] = [file_paths[0]]
    prev_ts = pts[0]
    for path, ts in zip(file_paths[1:], pts[1:], strict=True):
        if ts - prev_ts <= float(gap_seconds):
            cur.append(path)
        else:
            seqs.append(cur)
            cur = [path]
        prev_ts = ts
    if cur:
        seqs.append(cur)

    out: List[Sequence] = _build_sequences(seqs, exif_priority)
    return out


def group_by_fixed_size(
    file_paths: List[str], group_size: int = 3, *, exif_priority: bool = True
) -> List[Sequence]:
    """Group sorted `file_paths` into fixed-size consecutive batches.

    Each sequence contains at most `group_size` images. The final sequence may be
    shorter when the total number of images is not divisible by `group_size`.
    """
    if not file_paths:
        return []

    size = max(1, int(group_size))
    seqs: List[List[str]] = [
        file_paths[index : index + size]
        for index in range(0, len(file_paths), size)
    ]
    return _build_sequences(seqs, exif_priority)


def _get_exif_datetime(path: str) -> Optional[datetime]:
    """Attempt to extract EXIF DateTimeOriginal or DateTime from an image.

    Returns a timezone-naive datetime in local time parsed from EXIF, or None
    if no valid EXIF timestamp is present.
    """
    try:
        img = Image.open(path)
        exif = img.getexif()
        if not exif:
            return None
        # exif is a mapping of tag id -> value
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag in ("DateTimeOriginal", "DateTime") and isinstance(value, str):
                try:
                    dt = _date_parser.parse(value)
                    # dateutil returns a datetime-like value; cast for mypy
                    return cast(datetime, dt)
                except Exception:
                    continue
    except Exception:
        return None
    return None


def extract_image_timestamp(
    path: str, *, exif_priority: bool = True
) -> Optional[datetime]:
    """Return the best-effort timestamp for `path`.

    If `exif_priority` is True, attempt EXIF extraction first and fall back
    to filesystem mtime. Returns None only if both methods fail.
    """
    p = Path(path)
    if exif_priority:
        dt = _get_exif_datetime(path)
        if dt:
            return dt
    # fallback to mtime
    try:
        return datetime.fromtimestamp(p.stat().st_mtime)
    except Exception:
        return None
