"""Headless smoke test for a packaged Acteo executable on Windows."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def smoke_packaged_executable(
    executable: Path,
    sample_directory: Path,
    wait_seconds: float = 5.0,
) -> dict[str, Any]:
    """Start the packaged executable and verify it remains alive briefly.

    Args:
        executable: Path to the packaged Acteo executable.
        sample_directory: Existing directory passed as the Acteo input folder.
        wait_seconds: Maximum startup interval before declaring smoke success.

    Returns:
        Structured smoke-test result containing process state and log messages.

    Raises:
        RuntimeError: If the executable is missing or exits during startup.
    """
    if not executable.is_file():
        raise RuntimeError(f"Packaged executable not found: {executable}")
    if not sample_directory.is_dir():
        raise RuntimeError(f"Smoke-test sample directory not found: {sample_directory}")

    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"

    print(f"SMOKE: starting {executable}")
    print(f"SMOKE: input directory {sample_directory}")
    process = subprocess.Popen(
        [str(executable), "--input", str(sample_directory)],
        cwd=str(executable.parent),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    deadline = time.monotonic() + wait_seconds
    try:
        while time.monotonic() < deadline:
            return_code = process.poll()
            if return_code is not None:
                stdout, stderr = process.communicate(timeout=1)
                raise RuntimeError(
                    "Packaged executable exited during startup "
                    f"with code {return_code}. stdout={stdout!r} stderr={stderr!r}"
                )
            time.sleep(0.1)

        print(f"SMOKE: executable remained alive for {wait_seconds:.1f}s")
        return {"executable": str(executable), "alive": True}
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
                print("SMOKE: executable terminated cleanly")
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                print("SMOKE: executable required forced termination")


def main(argv: list[str] | None = None) -> int:
    """Run the packaged executable smoke test from the command line.

    Args:
        argv: Optional command-line arguments for testing.

    Returns:
        Zero on success, one on failure.
    """
    arguments = argv if argv is not None else sys.argv[1:]
    repository = Path(__file__).resolve().parents[1]
    executable = (
        Path(arguments[0]).resolve()
        if arguments
        else repository / "dist" / "Acteo" / "Acteo.exe"
    )
    sample_directory = (
        Path(arguments[1]).resolve()
        if len(arguments) > 1
        else repository / "resources" / "samples"
    )

    try:
        smoke_packaged_executable(executable, sample_directory)
        return 0
    except Exception as exc:
        print(f"SMOKE FAILURE: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
