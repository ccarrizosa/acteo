"""Pytest configuration for headless Qt tests.

The application uses PySide6 and needs a Qt platform plugin even when
running under CI or a headless local environment. Defaulting to the
"offscreen" platform avoids the fatal "Could not initialize Qt platform"
error that otherwise aborts pytest before any tests run.
"""

from __future__ import annotations

import os

# Set this before PySide6 imports happen during test collection.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
