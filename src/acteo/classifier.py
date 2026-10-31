"""Classification actions that move/copy/discard sequences and log metadata.

This module provides a small `Classifier` class that encapsulates the
BackgroundCSVWriter and performs file operations using the safe helpers in
`storage`. It is intentionally minimal but typed and covered by tests.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .logger import BackgroundCSVWriter
from .sequence_loader import Sequence as SequenceModel
from .settings import Settings
from .storage import safe_copy, safe_move

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of a classification action.

    Attributes:
        sequence_id: Identifier of the sequence.
        operation: One of 'move' or 'copy'.
        destination_paths: List of destination file paths created.
    """

    sequence_id: str
    operation: str
    destination_paths: List[str]


classifier_fieldnames = [
    "sequence_id",
    "image_count",
    "image_paths",
    "start_ts",
    "end_ts",
    "category",
    "operator",
    "timestamp_processed",
    "operation",
    "destination_paths",
]


class Classifier:
    """Performs classification file ops and logs metadata asynchronously.

    Example:
        clf = Classifier(settings)
        clf.start()
        clf.classify_sequence(seq, category='deer')
        clf.stop()
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        metadata_path = settings.metadata_file_path or "metadata.csv"
        self._writer = BackgroundCSVWriter(metadata_path, classifier_fieldnames)

    def start(self) -> None:
        """Start the background writer thread."""
        self._writer.start()

    def stop(self, flush: bool = True, timeout: Optional[float] = None) -> None:
        """Stop the writer thread, optionally flushing queued writes."""
        self._writer.stop(flush=flush, timeout=timeout)

    def classify_sequence(
        self,
        sequence: SequenceModel,
        category: str,
    ) -> ClassificationResult:
        """Apply classification to `sequence` and log metadata.

        `sequence` is expected to have attributes: `id`, `image_paths`,
        `start_ts`, `end_ts`. The method respects `Settings.move_mode` which
        can be 'move' or 'copy'. Images are stored in a category-named
        subdirectory under the configured output folder.
        """
        imgs: List[str] = list(sequence.image_paths)
        dests: List[str] = []
        op = self._settings.move_mode or "move"
        out_dir = self._settings.output_folder
        if not out_dir:
            raise ValueError("output_folder must be configured in settings")

        category_name = str(category).strip() or "uncategorized"
        category_dir = Path(out_dir) / category_name
        category_dir.mkdir(parents=True, exist_ok=True)

        for src in imgs:
            srcp = Path(src)
            dst = category_dir / srcp.name
            if op == "copy":
                safe_copy(src, str(dst))
            else:
                safe_move(src, str(dst))
            dests.append(str(dst))

        # Prepare metadata row
        row: Dict[str, object] = {
            "sequence_id": str(sequence.id),
            "image_count": len(imgs),
            "image_paths": json.dumps(imgs, ensure_ascii=False),
                "start_ts": sequence.start_ts.isoformat(),
                "end_ts": sequence.end_ts.isoformat(),
            "category": category,
            "operator": self._settings.operator_name or "",
            "timestamp_processed": datetime.utcnow().isoformat(),
            "operation": op,
            "destination_paths": json.dumps(dests, ensure_ascii=False),
        }

        # Queue the metadata write
        try:
            self._writer.put(row)
        except Exception:
            logger.exception(
                "Failed to queue metadata row; falling back to synchronous write"
            )
            # fallback: write synchronously
            from .logger import append_sequence_metadata
            append_sequence_metadata(
                self._settings.metadata_file_path or "metadata.csv",
                row,
                classifier_fieldnames,
            )

        return ClassificationResult(
            sequence_id=str(sequence.id), operation=op, destination_paths=dests
        )
