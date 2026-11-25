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

### Windows packaging dependencies

Use a dedicated virtual environment for Windows builds. The build requirements file includes the normal runtime dependencies plus PyInstaller; it is not needed for application users or normal Linux development:

```powershell
python -m venv .venv-build
. .\.venv-build\Scripts\Activate.ps1
python -m pip install -r requirements-windows-build.txt
```

Keep `requirements.txt` limited to runtime and test dependencies. Build-time packaging tools belong in `requirements-windows-build.txt`.

### Build the Windows application bundle

Run the PowerShell 7 build script from the repository root. It creates a dedicated `.venv-build`, installs `requirements-windows-build.txt`, cleans prior PyInstaller outputs, and verifies the executable:

```powershell
pwsh -File .\build\package_windows.ps1
```

Supported options include `-Clean:$false`, `-DebugBuild`, `-Version 'x.y.z'`, and `-VirtualEnvPath '.venv-custom'`. This creates `dist/Acteo/Acteo.exe`; the specification bundles `schemas/settings.schema.json` and does not create a console window.

### Build the Windows installer

After creating `dist/Acteo/Acteo.exe`, build the per-user Inno Setup installer with PowerShell 7:

```powershell
pwsh -File .\build\package_installer.ps1
```

The helper reads the Acteo version from `pyproject.toml`, searches standard Inno Setup locations, and creates `dist/installer/Acteo-<version>-Setup.exe`. Pass `-InnoSetupCompiler` or set `INNO_SETUP_COMPILER` if ISCC is installed outside the standard locations.

### Smoke-test the packaged executable

On Windows CI or a Windows test machine, verify that the PyInstaller bundle starts without an immediate crash:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
python build\smoke_windows.py dist\Acteo\Acteo.exe resources\samples
```

The smoke test starts Acteo offscreen, passes the sample directory as input, requires it to remain alive briefly, and terminates it cleanly.
