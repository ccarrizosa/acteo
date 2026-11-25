from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional, cast

import jsonschema

DEFAULT_CONFIG_NAME = "acteo_settings.json"


def _load_schema() -> dict[str, Any]:
    schema_path = bundled_resource_path("schemas", "settings.schema.json")
    with schema_path.open("r", encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def validate_settings_data(data: dict[str, Any]) -> None:
    try:
        jsonschema.validate(data, _load_schema())
    except jsonschema.ValidationError as exc:
        raise ValueError(f"Invalid settings: {exc.message}") from exc


def _filter_known_settings(data: dict[str, Any]) -> dict[str, Any]:
    """Return only settings keys recognized by the current schema.

    Legacy or removed fields are ignored so older config files do not block app
    startup.
    """
    schema = _load_schema()
    allowed = set(schema.get("properties", {}).keys())
    return {key: value for key, value in data.items() if key in allowed}

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
    - timestamp_gap_seconds: Number of seconds used when `grouping_mode` is
        "timestamp_gap". Two images whose timestamps differ by <= this value are
        considered part of the same sequence. Use a small value (e.g. 5–30) for
        burst shots; larger values group temporally distant images together.
    - fixed_group_size: Number of images per sequence when `grouping_mode` is
        "fixed_size".

    - autoplay_interval_seconds: Time in seconds between automatic image changes
        while the viewer is playing a sequence.

    - move_mode: Defines file operation when classifying a sequence: "move"
        will relocate originals to the `output_folder`; "copy" will duplicate
        files leaving originals in place.
    - safe_delete: When enabled, discard operations will not permanently delete
        files — they will be moved to the `discard_folder` instead. If false,
        discard may perform permanent deletion depending on platform and config.

    - category_file_path: Path to a JSON file storing user-defined categories.
    - metadata_file_path: Path to the CSV file where classification metadata
        (one row per sequence) will be appended.
    - thumbnails_cache_dir: Directory where generated thumbnails are cached to
        speed up UI listing and reduce repeated image decoding.

    - exif_priority: Prefer reading EXIF DateTimeOriginal when available; if
        false, the loader will prefer filesystem mtime.

    - locale: User interface language. Supported values are "en", "es", and
        "ca".

    - operator_name: Optional name of the current operator to include in logs.
    """
    # Folders
    input_folder: Optional[str] = None
    output_folder: Optional[str] = None
    discard_folder: Optional[str] = None

    # Grouping
    grouping_mode: str = "timestamp_gap"  # timestamp_gap | fixed_size
    timestamp_gap_seconds: int = 10
    fixed_group_size: int = 3

    # Presentation
    autoplay_interval_seconds: int = 1

    # File operations
    move_mode: str = "move"  # move | copy
    safe_delete: bool = False

    # Paths for auxiliary files
    category_file_path: Optional[str] = None
    metadata_file_path: Optional[str] = None
    thumbnails_cache_dir: Optional[str] = None

    # IO & behavior
    exif_priority: bool = True  # prefer EXIF timestamp over mtime

    # Localization
    locale: str = "en"  # en | es | ca

    # Operator
    operator_name: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Settings":
        d = _filter_known_settings(d)
        defaults = cls().to_dict()
        merged = defaults.copy()
        merged.update(d)
        d = merged

        # Basic normalization
        if "timestamp_gap_seconds" in d:
            try:
                d["timestamp_gap_seconds"] = int(d["timestamp_gap_seconds"])
            except Exception:
                d["timestamp_gap_seconds"] = cls().timestamp_gap_seconds
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
        }:
            raise ValueError(
                "Unsupported grouping_mode. Supported values are: "
                "'timestamp_gap' and 'fixed_size'."
            )
        if "locale" in d and d["locale"] not in {"en", "es", "ca"}:
            raise ValueError(
                "Unsupported locale. Supported values are: 'en', 'es', and 'ca'."
            )
        validate_settings_data(d)
        return cls(**d)

    def save(self, path: Optional[str] = None) -> None:
        path = path or default_config_path()
        payload = self.to_dict()
        validate_settings_data(payload)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Settings":
        path = path or default_config_path()
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        settings = cls.from_dict(data)
        normalized = settings.to_dict()
        filtered_data = _filter_known_settings(data)
        if filtered_data != normalized:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(normalized, f, indent=2, ensure_ascii=False)
        return settings

def _windows_config_dir(environ: Mapping[str, str], home_dir: Path) -> Path:
    """Resolve the Windows Acteo configuration directory.

    Args:
        environ: Environment-variable mapping to inspect.
        home_dir: User home directory used for fallback resolution.

    Returns:
        A platform-appropriate, absolute Acteo configuration path.
    """
    base = environ.get("LOCALAPPDATA") or environ.get("APPDATA")
    if base:
        return (Path(base).expanduser() / "Acteo").resolve()
    return (home_dir / "AppData" / "Local" / "Acteo").resolve()


def _unix_config_dir(environ: Mapping[str, str], home_dir: Path) -> Path:
    """Resolve the Acteo directory using the existing Unix/XDG layout.

    Args:
        environ: Environment-variable mapping to inspect.
        home_dir: User home directory used for fallback resolution.

    Returns:
        An absolute Acteo configuration path.
    """
    xdg_base = environ.get("XDG_CONFIG_HOME")
    if not xdg_base:
        xdg_base = str(home_dir / ".config")
    return (Path(xdg_base).expanduser() / "acteo").resolve()


def default_config_dir(
    platform_name: Optional[str] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> str:
    """Return the platform-specific Acteo configuration directory.

    Args:
        platform_name: Optional platform override, such as ``"win32"`` or
            ``"linux"``. Uses ``sys.platform`` when omitted.
        environ: Optional environment mapping for testable platform resolution.
            Uses ``os.environ`` when omitted.

    Returns:
        Absolute path to the Acteo configuration directory.
    """
    platform = platform_name or sys.platform
    environment = environ if environ is not None else os.environ
    home_dir = Path.home()

    if platform == "win32":
        return str(_windows_config_dir(environment, home_dir))
    return str(_unix_config_dir(environment, home_dir))


def default_config_path() -> str:
    return str((Path(default_config_dir()) / DEFAULT_CONFIG_NAME).resolve())


def ensure_paths(settings: Settings) -> Settings:
    # Expand user and create default folders for paths if needed
    def _expand(p: Optional[str]) -> Optional[str]:
        if not p:
            return None
        return str(Path(p).expanduser().resolve())

    s = settings
    s.input_folder = _expand(s.input_folder)
    s.output_folder = _expand(s.output_folder)
    s.discard_folder = _expand(s.discard_folder)
    config_dir = default_config_dir()
    s.category_file_path = (
        _expand(s.category_file_path)
        or str((Path(config_dir) / "categories.json").resolve())
    )
    s.metadata_file_path = _expand(s.metadata_file_path) or str(
        (Path(config_dir) / "metadata.csv").resolve()
    )
    s.thumbnails_cache_dir = _expand(s.thumbnails_cache_dir) or str(
        (Path(config_dir) / "thumbnails").resolve()
    )
    return s


def bundled_application_root() -> Path:
    """Return the source or PyInstaller root containing application resources.

    Returns:
        The repository root when running from source, or the PyInstaller
        extraction directory when running from a frozen executable.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()

    return Path(__file__).resolve().parents[2]


def bundled_resource_path(*relative_parts: str) -> Path:
    """Resolve a repository resource in source and frozen applications.

    Args:
        *relative_parts: Path components relative to the application root.

    Returns:
        Absolute path to the requested resource.
    """
    return (bundled_application_root().joinpath(*relative_parts)).resolve()


SETTINGS_SCHEMA_PATH = bundled_resource_path("schemas", "settings.schema.json")


if __name__ == "__main__":
    # Quick manual smoke test
    cfg = Settings()
    cfg.input_folder = "~/Pictures/trailcam_input"
    cfg.output_folder = "~/Pictures/trailcam_output"
    cfg.discard_folder = "~/Pictures/trailcam_discard"
    cfg.operator_name = os.getenv("USER")
    cfg = ensure_paths(cfg)
    print(json.dumps(cfg.to_dict(), indent=2))
