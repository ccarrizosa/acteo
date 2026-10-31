# Acteo

Acteo is a lightweight desktop application to help classify trail-cam image sequences.

Quick start (development)

Run from the repository without installing the package (recommended for development):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Ensure the package source is importable and run the module:
PYTHONPATH=src python -m acteo.main --input /path/to/images
```

On Windows (PowerShell):

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = 'src'
python -m acteo.main --input C:\path\to\images
```

Alternatively, install the package in editable mode and run via the package entrypoint:

```bash
python -m pip install -e .
acteo --input /path/to/images
```

For local CI-equivalent validation, run:

```bash
python -m pip install -r requirements.txt
python -m pip install ruff mypy
ruff check src tests
mypy --config-file mypy.ini
PYTHONPATH=src python -m pytest -q
```

Release smoke test (headless/offscreen Qt):

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m pytest tests/test_packaging_entrypoint.py -k release_smoke -q
```

See `docs/SETTINGS.md` for configuration details.
