"""Category management (CRUD) utilities.

Categories are persisted as a JSON array of objects. Each category object is a
mapping with at least `id` and `name` keys. This module provides tiny helpers
to load and save categories.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_categories(path: str) -> List[Dict[str, Any]]:
    """Load categories from `path`.

    Returns an empty list on any error to simplify caller handling.
    """
    p = Path(path)
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_categories(path: str, categories: List[Dict[str, Any]]) -> None:
    """Save `categories` to `path`, creating parent directories as needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(categories, f, indent=2, ensure_ascii=False)


def export_categories(path: str, categories: List[Dict[str, Any]]) -> None:
    """Persist categories to disk in a JSON representation.

    This is a thin convenience wrapper around `save_categories` for Phase D
    import/export flows.
    """
    save_categories(path, categories)


def import_categories(path: str) -> List[Dict[str, Any]]:
    """Load categories from disk and return them as a list of dictionaries."""
    return load_categories(path)
