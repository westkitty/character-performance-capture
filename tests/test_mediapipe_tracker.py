from pathlib import Path

import pytest

from cpc.mediapipe_tracker import MediaPipeFaceTracker


def test_mediapipe_tracker_checks_model_before_optional_import(tmp_path: Path):
    tracker = MediaPipeFaceTracker(tmp_path / "missing.task")

    with pytest.raises(FileNotFoundError, match="MediaPipe model not found"):
        tracker.start()
