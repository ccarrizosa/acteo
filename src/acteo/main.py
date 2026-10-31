"""Entrypoint for Acteo application (PySide6).

This module provides the `main` function for running the Acteo UI and
connecting backend services to the PySide6 interface.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import QApplication

from .classifier import Classifier
from .main_window import MainWindow
from .sequence_loader import group_by_fixed_size, group_by_timestamp_gap, scan_folder
from .settings import Settings, ensure_paths

logger = logging.getLogger(__name__)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the Acteo application with UI.

    Args:
        argv: Optional list of command-line arguments (for testing).

    Returns:
        Exit code for the application.
    """
    parser = argparse.ArgumentParser(prog="acteo")
    parser.add_argument("--input", help="Input folder to scan", required=False)
    parser.add_argument(
        "--gap", type=int, default=10, help="Gap seconds for grouping"
    )
    args = parser.parse_args(argv)

    # Load settings
    cfg = Settings.load()
    if args.input:
        cfg.input_folder = str(Path(args.input).expanduser())
    cfg = ensure_paths(cfg)

    logger.info("Acteo settings loaded")

    # Scan folder if provided
    sequences = []
    if cfg.input_folder:
        files = scan_folder(cfg.input_folder)
        if files:
            if cfg.grouping_mode == "fixed_size":
                sequences = group_by_fixed_size(
                    files,
                    group_size=cfg.fixed_group_size,
                    exif_priority=cfg.exif_priority,
                )
            else:
                sequences = group_by_timestamp_gap(
                    files, gap_seconds=args.gap, exif_priority=cfg.exif_priority
                )
            logger.info(
                "Scanned %d sequences from %s", len(sequences), cfg.input_folder
            )

    # Create Qt app
    app = QApplication(sys.argv)

    # Create main window
    window = MainWindow(cfg, sequences=sequences)

    # Initialize classifier
    classifier = Classifier(cfg)
    classifier.start()
    window.set_classifier(classifier)

    window.show()
    logger.info("MainWindow shown")

    return app.exec()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
