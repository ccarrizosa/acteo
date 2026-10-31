copilot-instructions
=====================

Purpose
-------
Guidance for humans and Copilot-style agents contributing code to Acteo.

High-level rules
----------------
- Language: Python 3.11+ (use `pyproject.toml` or `requirements.txt` to pin deps).
- Use type annotations throughout public functions, methods, and dataclass fields.
- Docstrings: prefer **Google** style (consistent across the project) so Sphinx/MkDocs tools can parse them. Example:

  def foo(x: int) -> int:
      """Compute something.

      Args:
          x: input integer.

      Returns:
          Computed integer.
      """

- Formatting: use `black` for formatting and `ruff` (or `flake8`) for linting. Add `mypy` for optional static checks.
- Imports: use explicit imports. Avoid star imports.
- Keep functions small and single-responsibility. Prefer composition over large classes.

Project structure & tests
-------------------------
- Source: `src/acteo/`
- Tests: `tests/` using `pytest`.
- Unit tests are required for:
  - All core backend functions (grouping, storage, logger).
  - Any algorithmic logic or edge-case handling.
- Use `tmp_path` fixtures for filesystem tests. Do not commit large sample images; use small generated test fixtures or add a separate sample-data release.

Portability & performance
-------------------------
- Use `pathlib.Path` for path manipulation and `os.replace()` for atomic moves.
- Avoid POSIX-only features; prefer standard library functions that work across Windows/macOS/Linux.
- For file locks or single-writer guarantees, prefer a single background writer thread instead of relying on `fcntl`.
- Read EXIF via Pillow. Normalize timestamps to UTC internally using `python-dateutil`.
- Thumbnail generation should be backgrounded and cached to disk (`thumbnails/` in config dir).

Concurrency & IO
----------------
- Use `concurrent.futures.ThreadPoolExecutor` or Qt `QThreadPool` for IO-bound tasks.
- Ensure thread-safety when updating shared state; marshal changes back to the main/UI thread via signals.

Logging & error handling
------------------------
- Use the `logging` module with structured messages. Log to `logs/` in the config directory.
- Surface IO failures to the UI with clear user actions (Retry / Skip / Skip All / Abort).

Testing & CI
------------
- CI must run `pytest --maxfail=1 -q` and `ruff`/`black --check`.
- Tests should include edge cases (missing EXIF, identical timestamps, cross-device moves).

Commit & PR workflow
--------------------
- Work in feature branches. Make small commits with clear messages.
- Add a short description of the Copilot prompts used (if any) in the PR body under `Agent prompts`.
- PR checklist:
  - [ ] Tests added/updated
  - [ ] Docstrings and type annotations present
  - [ ] Formatting and linting pass locally
  - [ ] CI green

Project defaults
----------------
The repository uses the following defaults unless you request otherwise. These were agreed during setup and are recorded here for contributors and automated agents.

- Docstring style: **Google** (use Google-style docstrings for public APIs so docs tooling can parse them).
- Formatter / linter: **black + ruff** (CI will run `black --check` and `ruff`).
- `mypy`: **strict** (enable `mypy` strict mode now to enforce type-safety across the codebase).
- License: **GPL-3.0-or-later** (see `LICENSE`).

If you want to change any of these defaults, open an issue or propose the change in a PR and update this file. When changes are accepted, CI and configuration files (`pyproject.toml`, `mypy.ini`, `ruff.toml`) will be updated accordingly.