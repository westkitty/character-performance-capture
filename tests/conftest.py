from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

try:
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False


@pytest.fixture(scope="session")
def qapp() -> Generator[Any, None, None]:
    """Provide a single global QApplication instance for the test session in offscreen mode."""
    if not HAS_PYSIDE6:
        yield None
        return

    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    yield app


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Hermetically isolate QSettings and ModelRegistry between tests."""
    if HAS_PYSIDE6:
        # Redirect QSettings to a temporary isolated INI file per test
        settings_dir = tmp_path / "qsettings"
        settings_dir.mkdir(parents=True, exist_ok=True)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(settings_dir))

        # Reset global model registry singleton with an isolated empty directory per test
        models_dir = tmp_path / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        from cpc.ui.models import ModelRegistry, reset_model_registry

        reset_model_registry(ModelRegistry(base_dir=models_dir))

    yield

    if HAS_PYSIDE6:
        from cpc.ui.models import reset_model_registry

        reset_model_registry(None)
