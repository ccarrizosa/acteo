"""CSV metadata writer (append-only) for sequence classification.

This module provides a small helper to append a single metadata row for a
classified sequence. It is intentionally simple; a robust production system may
use a background writer thread or a SQLite backend instead.
"""
from __future__ import annotations

import csv
import queue
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Optional


def append_sequence_metadata(
    path: str,
    row: Dict[str, object],
    fieldnames: Iterable[str],
) -> None:
    """Append `row` to CSV at `path`, creating parent directories when needed.

    This is a convenience helper that performs a synchronous append. For high
    concurrency use `BackgroundCSVWriter` below which provides a single-writer
    queue.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    exists = p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def export_sequence_report(path: str, rows: List[Dict[str, object]]) -> None:
    """Export a list of sequence rows to a CSV report.

    The file uses a stable field ordering that follows the keys encountered in
    the first row, or falls back to a standard report set.
    """
    if not rows:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class BackgroundCSVWriter:
    """Background single-writer CSV appender.

    Usage:
        writer = BackgroundCSVWriter(path, fieldnames)
        writer.start()
        writer.put(row)
        writer.stop()
    """

    def __init__(self, path: str, fieldnames: Iterable[str], maxsize: int = 0) -> None:
        self._path = Path(path)
        self._fieldnames = list(fieldnames)
        # Typed queue holding optional row dictionaries
        self._queue: "queue.Queue[Optional[Dict[str, object]]]" = queue.Queue(
            maxsize=maxsize
        )
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the background writer thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def put(self, row: Dict[str, object]) -> None:
        """Queue a row to be written; blocks if the queue is full."""
        self._queue.put(row)

    def stop(self, flush: bool = True, timeout: Optional[float] = None) -> None:
        """Stop the writer thread. If `flush` is True, wait until queue is empty."""
        if not self._thread:
            return
        if flush:
            # Wait until queue is empty
            self._queue.join()
        # Signal thread to exit
        self._stop_event.set()
        # Put sentinel to ensure thread wakes
        self._queue.put(None)
        self._thread.join(timeout=timeout)
        self._thread = None

    def _run(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        exists = self._path.exists()
        with self._path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self._fieldnames)
            if not exists:
                writer.writeheader()
            while True:
                item = self._queue.get()
                try:
                    if item is None:
                        # Sentinel: break loop
                        break
                    writer.writerow(item)
                    f.flush()
                finally:
                    self._queue.task_done()
                if self._stop_event.is_set() and self._queue.empty():
                    break
