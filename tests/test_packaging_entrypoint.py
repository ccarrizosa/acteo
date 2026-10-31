from __future__ import annotations

import os
import subprocess
import sys
import tomllib
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
