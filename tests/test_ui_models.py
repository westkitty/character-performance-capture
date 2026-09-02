from __future__ import annotations

import io
from unittest.mock import patch

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from cpc.ui.models import (
    ModelDownloadWorker,
    ModelRegistry,
    ModelStatus,
    get_managed_models_dir,
    get_model_registry,
)


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_curated_model_catalog_metadata():
    """Verify built-in catalog contains official recommended MediaPipe entry and passthrough baseline."""
    reg = ModelRegistry()
    entries = reg.get_entries()
    assert len(entries) >= 2

    rec = reg.get_recommended_entry()
    assert rec.model_id == "mediapipe-face-landmarker"
    assert rec.is_recommended is True
    assert "MediaPipe" in rec.name
    assert rec.backend == "mediapipe"
    assert "478" in rec.description
    assert len(rec.capabilities) >= 3
    assert "storage.googleapis.com" in rec.source_url
    assert rec.filename == "face_landmarker.task"
    assert rec.license_name == "Apache 2.0"
    assert rec.default_delegate == "cpu"

    null_entry = reg.get_entry("null-tracker")
    assert null_entry is not None
    assert null_entry.backend == "null"
    assert null_entry.is_recommended is False


def test_managed_models_directory_resolution():
    """Verify managed directory creates a valid writable path."""
    dest_dir = get_managed_models_dir()
    assert dest_dir.is_dir()
    assert dest_dir.exists()


def test_model_status_and_path_resolution(tmp_path):
    """Verify status reporting for ready, not installed, and missing models."""
    reg = ModelRegistry()

    # Null tracker is always ready
    assert reg.get_status("null-tracker") == ModelStatus.READY
    assert reg.resolve_model_path("null-tracker") is None

    # Custom model registration and readiness
    custom_file = tmp_path / "custom_face.task"
    custom_file.write_bytes(b"0" * 60000)  # Dummy payload

    with patch.object(reg, "validate_model_file", return_value=(True, "OK")):
        entry = reg.register_custom_model(custom_file, copy_to_managed=False)
        assert entry.model_id.startswith("custom:")
        assert reg.get_status(entry.model_id) == ModelStatus.READY
        assert reg.resolve_model_path(entry.model_id) == custom_file


def test_model_download_worker_success(qapp, tmp_path):
    """Verify download worker writes atomically, reports progress, and emits completion."""
    dest_file = tmp_path / "installed" / "face_landmarker.task"
    fake_content = b"fake_task_binary_data" * 1000

    mock_response = io.BytesIO(fake_content)
    mock_response.headers = {"Content-Length": str(len(fake_content))}

    worker = ModelDownloadWorker(
        source_url="https://fake.url/face_landmarker.task",
        dest_path=dest_file,
        expected_size=len(fake_content),
    )

    progress_events = []
    finished_paths = []
    error_events = []

    worker.progress_updated.connect(lambda pct, msg: progress_events.append((pct, msg)))
    worker.download_finished.connect(lambda p: finished_paths.append(p))
    worker.error_occurred.connect(lambda u, t: error_events.append((u, t)))

    with patch("urllib.request.urlopen", return_value=mock_response):
        worker.run()

    assert len(error_events) == 0
    assert len(finished_paths) == 1
    assert finished_paths[0] == dest_file
    assert dest_file.is_file()
    assert dest_file.read_bytes() == fake_content
    assert len(progress_events) > 0
    assert progress_events[-1][0] == 100


def test_model_download_worker_cancellation(qapp, tmp_path):
    """Verify cancellation deletes temp file and emits error."""
    dest_file = tmp_path / "cancelled" / "face_landmarker.task"

    worker = ModelDownloadWorker(
        source_url="https://fake.url/face_landmarker.task",
        dest_path=dest_file,
    )
    worker.cancel()

    error_events = []
    worker.error_occurred.connect(lambda u, t: error_events.append((u, t)))

    fake_stream = io.BytesIO(b"data" * 500)
    fake_stream.headers = {"Content-Length": "2000"}

    with patch("urllib.request.urlopen", return_value=fake_stream):
        worker.run()

    assert len(error_events) == 1
    assert "cancelled" in error_events[0][0].lower()
    assert not dest_file.exists()


def test_model_download_worker_network_error(qapp, tmp_path):
    """Verify download worker catches network errors gracefully."""
    dest_file = tmp_path / "failed" / "face_landmarker.task"

    worker = ModelDownloadWorker(
        source_url="https://nonexistent.invalid.url/model.task",
        dest_path=dest_file,
    )

    error_events = []
    worker.error_occurred.connect(lambda u, t: error_events.append((u, t)))

    with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
        worker.run()

    assert len(error_events) == 1
    assert "could not be installed" in error_events[0][0]
    assert not dest_file.exists()


def test_offline_guarantee_no_network_on_query():
    """Verify querying registry triggers zero network calls."""
    with patch("urllib.request.urlopen", side_effect=AssertionError("Network called!")):
        reg = get_model_registry()
        _ = reg.get_entries()
        _ = reg.get_recommended_entry()
        _ = reg.get_status("mediapipe-face-landmarker")
        _ = reg.resolve_model_path("mediapipe-face-landmarker")


def test_validate_model_file_tiny_invalid(tmp_path):
    """Verify validate_model_file rejects files smaller than 50KB."""
    reg = ModelRegistry()
    tiny_file = tmp_path / "tiny.task"
    tiny_file.write_bytes(b"dummy")

    valid, reason = reg.validate_model_file(tiny_file)
    assert valid is False
    assert "too small" in reason.lower()


def test_validate_model_file_missing():
    """Verify validate_model_file rejects missing files."""
    reg = ModelRegistry()
    from pathlib import Path
    missing_file = Path("/tmp/definitely_missing_task_file_123.task")

    valid, reason = reg.validate_model_file(missing_file)
    assert valid is False
    assert "does not exist" in reason.lower()


def test_register_custom_path_preserves_path_without_heavy_validation(tmp_path):
    """Verify register_custom_path registers and preserves custom file path."""
    reg = ModelRegistry()
    custom_file = tmp_path / "custom_model.task"
    custom_file.write_bytes(b"fake_data_bytes")

    entry = reg.register_custom_path(custom_file)
    assert entry.model_id.startswith("custom:")
    assert entry.custom_path == custom_file.resolve()
    assert reg.resolve_model_path(entry.model_id) == custom_file.resolve()
    assert reg.get_status(entry.model_id) == ModelStatus.READY
