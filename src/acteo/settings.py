from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, List, Optional

DEFAULT_CONFIG_NAME = "acteo_settings.json"

@dataclass
class Settings:
    """
    Application settings for Acteo.

    Each attribute below controls a specific aspect of scanning, grouping,
    presentation, file operations, or persistence. Brief descriptions:

    - input_folder: Path to the directory containing images to process.
    - output_folder: Destination folder where classified images are placed.
    - discard_folder: Destination folder where discarded sequences are moved.

    - grouping_mode: How images are grouped into sequences. Options:
        * "timestamp_gap": group consecutive images if their timestamps are within
            `timestamp_gap_seconds`.
        * "fixed_size": group images into consecutive batches of
            `fixed_group_size`.
        * "manual": no automatic grouping, sequences are formed manually by user.
        * "filename_pattern": group by filename ordering/patterns.
    - timestamp_gap_seconds: Number of seconds used when `grouping_mode` is
        "timestamp_gap". Two images whose timestamps differ by <= this value are
        considered part of the same sequence. Use a small value (e.g. 5–30) for
        burst shots; larger values group temporally distant images together.
    - fixed_group_size: Number of images per sequence when `grouping_mode` is
        "fixed_size".

    - images_per_sequence: Default number of images to present in the UI grid
        for each sequence. The UI may still show fewer images for short sequences.
    - autoplay_interval_seconds: Time in seconds between automatic image changes
        while the viewer is playing a sequence.

    - move_mode: Defines file operation when classifying a sequence: "move"
        will relocate originals to the `output_folder`; "copy" will duplicate
        files leaving originals in place.
    - preserve_folder_structure: When true, keep subfolder layout from the
        `input_folder` when moving/copying to the `output_folder`.
    - safe_delete: When enabled, discard operations will not permanently delete
        files — they will be moved to the `discard_folder` instead. If false,
        discard may perform permanent deletion depending on platform and config.

    - category_file_path: Path to a JSON file storing user-defined categories.
    - metadata_file_path: Path to the CSV file where classification metadata
        (one row per sequence) will be appended.
    - thumbnails_cache_dir: Directory where generated thumbnails are cached to
        speed up UI listing and reduce repeated image decoding.

    - concurrency: Number of concurrent IO workers used for move/copy and
        thumbnail generation. Increase for faster disks; reduce for low-RAM
        environments.
    - exif_priority: Prefer reading EXIF DateTimeOriginal when available; if
        false, the loader will prefer filesystem mtime.
    - file_patterns: Glob patterns to include when scanning for images.

    - operator_name: Optional name of the current operator to include in logs.
    - last_scanned: ISO timestamp of the last successful folder scan; used to
        show recency in the UI.
    """
    # Folders
    input_folder: Optional[str] = None
    output_folder: Optional[str] = None
    discard_folder: Optional[str] = None

    # Grouping
    grouping_mode: str = (
        "timestamp_gap"  # timestamp_gap | fixed_size | manual | filename_pattern
    )
    timestamp_gap_seconds: int = 10
    fixed_group_size: int = 3

    # Presentation
    images_per_sequence: int = 3
    autoplay_interval_seconds: int = 1

    # File operations
    move_mode: str = "move"  # move | copy
    preserve_folder_structure: bool = False
    safe_delete: bool = False

    # Paths for auxiliary files
    category_file_path: Optional[str] = None
    metadata_file_path: Optional[str] = None
    thumbnails_cache_dir: Optional[str] = None

    # IO & behavior
    concurrency: int = 2
    exif_priority: bool = True  # prefer EXIF timestamp over mtime
    file_patterns: List[str] = field(
        default_factory=lambda: ["*.jpg", "*.jpeg", "*.png"]
    )

    # Operator
    operator_name: Optional[str] = None

    # Misc
    last_scanned: Optional[str] = None  # ISO timestamp

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Settings":
        # Basic normalization
        if "timestamp_gap_seconds" in d:
            try:
                d["timestamp_gap_seconds"] = int(d["timestamp_gap_seconds"])
            except Exception:
                d["timestamp_gap_seconds"] = cls().timestamp_gap_seconds
        if "images_per_sequence" in d:
            try:
                d["images_per_sequence"] = int(d["images_per_sequence"])
            except Exception:
                d["images_per_sequence"] = cls().images_per_sequence
        if "autoplay_interval_seconds" in d:
            try:
                d["autoplay_interval_seconds"] = max(
                    1, int(d["autoplay_interval_seconds"])
                )
            except Exception:
                d["autoplay_interval_seconds"] = cls().autoplay_interval_seconds
        if "fixed_group_size" in d:
            try:
                d["fixed_group_size"] = int(d["fixed_group_size"])
            except Exception:
                d["fixed_group_size"] = cls().fixed_group_size
        if "grouping_mode" in d and d["grouping_mode"] not in {
            "timestamp_gap",
            "fixed_size",
            "manual",
            "filename_pattern",
        }:
            d["grouping_mode"] = cls().grouping_mode
        return cls(**d)

    def save(self, path: Optional[str] = None) -> None:
        path = path or default_config_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Settings":
        path = path or default_config_path()
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        s = cls.from_dict(data)
        return s

    def update_last_scanned(self) -> None:
        self.last_scanned = datetime.utcnow().isoformat()


def default_config_dir() -> str:
    # Respect XDG on Linux, fall back to home
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config"
    )
    return os.path.join(xdg, "acteo")


def default_config_path() -> str:
    return os.path.join(default_config_dir(), DEFAULT_CONFIG_NAME)


def ensure_paths(settings: Settings) -> Settings:
    # Expand user and create default folders for paths if needed
    def _expand(p: Optional[str]) -> Optional[str]:
        if not p:
            return None
        p = os.path.expanduser(p)
        return os.path.abspath(p)

    s = settings
    s.input_folder = _expand(s.input_folder)
    s.output_folder = _expand(s.output_folder)
    s.discard_folder = _expand(s.discard_folder)
    config_dir = default_config_dir()
    s.category_file_path = (
        _expand(s.category_file_path) or os.path.join(config_dir, "categories.json")
    )
    config_dir = default_config_dir()
    s.metadata_file_path = _expand(s.metadata_file_path) or os.path.join(
        config_dir, "metadata.csv"
    )
    s.thumbnails_cache_dir = _expand(s.thumbnails_cache_dir) or os.path.join(
        config_dir, "thumbnails"
    )
    return s


if __name__ == "__main__":
    # Quick manual smoke test
    cfg = Settings()
    cfg.input_folder = "~/Pictures/trailcam_input"
    cfg.output_folder = "~/Pictures/trailcam_output"
    cfg.discard_folder = "~/Pictures/trailcam_discard"
    cfg.operator_name = os.getenv("USER")
    cfg.update_last_scanned()
    cfg = ensure_paths(cfg)
    print(json.dumps(cfg.to_dict(), indent=2))
