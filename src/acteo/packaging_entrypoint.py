"""Packaging-safe executable entrypoint for Acteo."""

from __future__ import annotations

import sys

from acteo.main import main


def run() -> int:
    """Run Acteo and return the application exit status.

    Returns:
        Exit code returned by the Acteo main function.
    """
    return main()


if __name__ == "__main__":
    sys.exit(run())
