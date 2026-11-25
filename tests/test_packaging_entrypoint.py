from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tomllib
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import acteo.main as acteo_main

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_declares_editable_app_entrypoint() -> None:
    pyproject = ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    poetry = data.get("tool", {}).get("poetry", {})
    scripts = poetry.get("scripts", {})

    assert scripts.get("acteo") == "acteo.main:main"
    assert any(pkg.get("include") == "acteo" for pkg in poetry.get("packages", []))


def test_main_module_runs_with_help_flag() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [sys.executable, "-m", "acteo.main", "--help"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()
    assert "acteo" in result.stdout.lower()


def test_qt_application_arguments_for_explicit_and_process_argv(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["Acteo.exe", "--input", "C:\\images"])

    assert acteo_main._qt_application_arguments(["--input", "C:\\images"]) == [
        "Acteo.exe"
    ]
    assert acteo_main._qt_application_arguments(None) == [
        "Acteo.exe",
        "--input",
        "C:\\images",
    ]


def test_main_runs_with_input_argument(monkeypatch, tmp_path: Path) -> None:
    class DummyWindow:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def set_classifier(self, classifier: object) -> None:
            pass

        def show(self) -> None:
            pass

    class DummyClassifier:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def start(self) -> None:
            pass

    class DummyQApplication:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def exec(self) -> int:
            return 0

    monkeypatch.setattr(acteo_main, "QApplication", DummyQApplication)
    monkeypatch.setattr(acteo_main, "MainWindow", DummyWindow)
    monkeypatch.setattr(acteo_main, "Classifier", DummyClassifier)
    monkeypatch.setattr(acteo_main, "scan_folder", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        acteo_main.Settings,
        "load",
        classmethod(lambda cls: acteo_main.Settings(input_folder=str(tmp_path))),
    )

    assert acteo_main.main(["--input", str(tmp_path)]) == 0


def test_release_smoke_startup_with_sample_directory() -> None:
    sample_dir = ROOT / "resources" / "samples"
    assert sample_dir.exists()

    script = f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'src')!r})
import acteo.main as m

class DummyQApplication:
    def __init__(self, argv=None):
        self.argv = argv

    def exec(self):
        return 0

class DummyWindow:
    def __init__(self, *args, **kwargs):
        pass

    def set_classifier(self, classifier):
        pass

    def show(self):
        pass

class DummyClassifier:
    def __init__(self, settings):
        self.settings = settings

    def start(self):
        pass

m.QApplication = DummyQApplication
m.MainWindow = DummyWindow
m.Classifier = DummyClassifier
m.scan_folder = lambda path: [str(p) for p in Path(path).glob('*') if p.is_file()]

settings = m.Settings(
    input_folder={str(sample_dir)!r},
    output_folder={str(ROOT / 'resources' / 'test_out')!r},
    discard_folder={str(ROOT / 'resources' / 'discard')!r},
)
m.Settings.load = classmethod(lambda cls: settings)

print(m.main(['--input', {str(sample_dir)!r}]))
"""

    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "0" in result.stdout
    assert sample_dir.is_dir()


def test_packaging_entrypoint_delegates_to_acteo_main() -> None:
    entrypoint = ROOT / "src" / "acteo" / "packaging_entrypoint.py"

    assert entrypoint.is_file()
    source = entrypoint.read_text(encoding="utf-8")
    assert "from acteo.main import main" in source
    assert "sys.exit(run())" in source


def test_pyinstaller_spec_uses_windowed_directory_bundle() -> None:
    spec_path = ROOT / "acteo.spec"

    assert spec_path.is_file()
    spec = spec_path.read_text(encoding="utf-8")
    assert '["src/acteo/packaging_entrypoint.py"]' in spec
    assert '["src"]' in spec
    assert '("schemas/settings.schema.json", "schemas")' in spec
    assert "console=False" in spec
    assert 'name="Acteo"' in spec


def test_windows_build_script_is_reproducible() -> None:
    script_path = ROOT / "build" / "package_windows.ps1"

    assert script_path.is_file()
    script = script_path.read_text(encoding="utf-8")
    assert '$ErrorActionPreference = "Stop"' in script
    assert "requirements-windows-build.txt" in script
    assert '"-m", "PyInstaller"' in script
    assert "dist\\Acteo\\Acteo.exe" in script


def test_readme_documents_windows_build_script() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "pwsh -File .\\build\\package_windows.ps1" in readme


def test_inno_setup_script_uses_per_user_layout() -> None:
    installer_script = ROOT / "build" / "acteo.iss"

    assert installer_script.is_file()
    script = installer_script.read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in script
    assert "{localappdata}\\Programs\\{#AppName}" in script
    assert "{autoprograms}" in script
    assert "UninstallDisplayName" in script
    assert 'Source: "dist\\Acteo\\*"' in script
    assert "LicenseFile=LICENSE" in script


def test_installer_helper_reads_project_version() -> None:
    helper = ROOT / "build" / "package_installer.ps1"

    assert helper.is_file()
    source = helper.read_text(encoding="utf-8")
    assert '["tool"]["poetry"]["version"]' in source
    assert "INNO_SETUP_COMPILER" in source
    assert "Acteo-$Version-Setup.exe" in source


def test_readme_documents_installer_build() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "pwsh -File .\\build\\package_installer.ps1" in readme


def test_frozen_resource_environment_is_mockable(monkeypatch, tmp_path: Path) -> None:
    bundle_dir = tmp_path / "_MEIPASS"
    schema_dir = bundle_dir / "schemas"
    schema_dir.mkdir(parents=True)
    (schema_dir / "settings.schema.json").write_text(
        (ROOT / "schemas" / "settings.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    import acteo.settings as settings_module

    assert settings_module.bundled_application_root() == bundle_dir.resolve()
    assert settings_module.bundled_resource_path(
        "schemas", "settings.schema.json"
    ).is_file()


def test_windows_smoke_script_starts_and_terminates_mock_process(
    monkeypatch, tmp_path: Path
) -> None:
    executable = tmp_path / "Acteo.exe"
    executable.touch()
    sample_directory = tmp_path / "samples"
    sample_directory.mkdir()

    script_path = ROOT / "build" / "smoke_windows.py"
    spec = importlib.util.spec_from_file_location("acteo_windows_smoke", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    process = types.SimpleNamespace(
        poll=lambda: None,
        terminate=lambda: setattr(process, "poll", lambda: 0),
        wait=lambda timeout=None: 0,
        kill=lambda: None,
    )

    monkeypatch.setattr(
        module.subprocess,
        "Popen",
        lambda *args, **kwargs: process,
    )

    result = module.smoke_packaged_executable(executable, sample_directory, 0.01)

    assert result["alive"] is True


def test_windows_smoke_script_reports_missing_executable(tmp_path: Path) -> None:
    script_path = ROOT / "build" / "smoke_windows.py"
    spec = importlib.util.spec_from_file_location("acteo_windows_smoke_missing", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    try:
        module.smoke_packaged_executable(
            tmp_path / "missing.exe", tmp_path / "samples", 0.01
        )
    except RuntimeError as exc:
        assert "Packaged executable not found" in str(exc)
    else:
        raise AssertionError("Missing executable should raise RuntimeError")


def test_windows_build_requirements_are_separate_from_runtime() -> None:
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    windows_build = (
        ROOT / "requirements-windows-build.txt"
    ).read_text(encoding="utf-8").lower()

    assert "pyinstaller" not in runtime
    assert "-r requirements.txt" in windows_build
    assert "pyinstaller>=6.0,<7.0" in windows_build


def test_workflow_contains_windows_smoke_job() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "windows-package:" in workflow
    assert "runs-on: windows-latest" in workflow
    assert "smoke_windows.py" in workflow
    assert "package_installer.ps1" in workflow
    assert "dist/installer/" in workflow
    assert "build/*.log" in workflow
    assert "QT_QPA_PLATFORM: offscreen" in workflow
    assert "signing" not in workflow.lower()
