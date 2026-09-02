from __future__ import annotations

import cv2
import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from cpc.rig import CharacterRig, default_rig_path, save_rig
from cpc.ui.workspaces.character_workspace import CharacterWorkspace
from cpc.ui.workspaces.live_workspace import LiveWorkspace


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_character_setup_step_progression_and_rail(qapp):
    """Verify 6-stage step navigation and rail state."""
    workspace = CharacterWorkspace()
    workspace.resize(1000, 700)
    workspace.show()

    assert workspace._current_step == 0
    assert workspace._stack.currentIndex() == 0
    assert len(workspace._step_buttons) == 6
    assert workspace._step_buttons[0].isChecked()

    # Step buttons are titled properly
    assert "1. Character" in workspace._step_buttons[0].text()
    assert "6. Ready" in workspace._step_buttons[5].text()

    workspace.close()


def test_character_setup_step1_character_loading(qapp, tmp_path):
    """Verify loading a character artwork image updates dimensions and enables step progression."""
    workspace = CharacterWorkspace()
    workspace.resize(900, 600)

    char_img = tmp_path / "hero.png"
    img = np.zeros((200, 150, 3), dtype=np.uint8)
    cv2.imwrite(str(char_img), img)

    # Before load
    assert not workspace._btn_step1_next.isEnabled()

    # Set image path
    workspace._char_edit.setText(str(char_img))
    assert workspace._btn_step1_next.isEnabled()
    assert "150 × 200 px" in workspace._char_info_lbl.text()
    assert workspace._step_completed[0] is True

    # Advance to Step 2
    workspace._btn_step1_next.click()
    assert workspace._current_step == 1
    assert workspace._stack.currentIndex() == 1

    workspace.close()


def test_character_setup_step2_tracking_model_selection(qapp):
    """Verify ModelSelectorWidget is embedded in Step 2 with Recommended model."""
    workspace = CharacterWorkspace()
    assert workspace.model_selector is not None
    assert workspace.model_selector.get_selected_model_id() == "mediapipe-face-landmarker"
    workspace.close()


def test_character_setup_step3_rig_derivation_success(qapp, tmp_path):
    """Verify rig derivation progresses to Step 4 upon successful completion."""
    workspace = CharacterWorkspace()

    char_img = tmp_path / "avatar.png"
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(str(char_img), img)

    model_file = tmp_path / "face_landmarker.task"
    model_file.write_bytes(b"mock_task_model")

    workspace._char_edit.setText(str(char_img))
    workspace._model_path = model_file
    workspace._set_step(2)  # Go to Build Rig

    # Simulate successful rig derivation callback
    pts = np.zeros((478, 2), dtype=np.float32)
    fake_rig = CharacterRig(width=100, height=100, points=pts)
    rig_path = default_rig_path(char_img)
    save_rig(fake_rig, rig_path)

    workspace._on_rig_derived(fake_rig, str(rig_path))

    # Auto-advanced to Step 4 Verify
    assert workspace._current_step == 3
    assert workspace._step_completed[2] is True
    assert workspace._step_completed[3] is True

    workspace.close()


def test_character_setup_step4_verify_to_step5_calibrate(qapp):
    """Verify verification checklists and calibration countdown."""
    workspace = CharacterWorkspace()
    workspace.resize(900, 600)
    workspace.show()
    workspace._set_step(3)  # Step 4 Verify

    # Click continue to calibration
    workspace._btn_step4_next.click()
    assert workspace._current_step == 4  # Step 5 Calibrate

    # Simulate calibration tick
    workspace._countdown_val = 1
    workspace._on_calibration_tick()
    assert workspace._is_calibrated is True
    assert not workspace._calib_status_banner.isHidden()
    assert workspace._step_completed[4] is True

    # Click continue to ready
    workspace._btn_step5_next.click()
    assert workspace._current_step == 5  # Step 6 Ready

    workspace.close()


def test_character_setup_step6_start_performing_live_handoff(qapp, tmp_path):
    """Verify 'Start Performing' emits complete configuration and LiveStudio applies it."""
    char_workspace = CharacterWorkspace()
    live_workspace = LiveWorkspace()

    char_img = tmp_path / "performer.png"
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(str(char_img), img)

    rig_file = default_rig_path(char_img)
    save_rig(CharacterRig(width=100, height=100, points=np.zeros((10, 2), dtype=np.float32)), rig_file)

    char_workspace._char_edit.setText(str(char_img))
    char_workspace._rig_path = rig_file

    received_setups = []
    char_workspace.start_performing_requested.connect(lambda s: received_setups.append(s))

    char_workspace._start_performing()

    assert len(received_setups) == 1
    setup = received_setups[0]
    assert setup["character_path"] == char_img
    assert setup["rig_path"] == rig_file
    assert setup["tracker_type"] == "mediapipe"
    assert setup["renderer_type"] == "rig"

    # Transfer into LiveStudio
    live_workspace.apply_character_setup(setup)
    cfg = live_workspace.get_session_config()
    assert cfg.character_path == char_img
    assert cfg.rig_path == rig_file
    assert cfg.renderer_type == "rig"
    assert cfg.tracker_type == "mediapipe"

    char_workspace.close()
    live_workspace.close()


def test_character_setup_state_invalidation(qapp, tmp_path):
    """Verify changing character invalidates downstream steps."""
    workspace = CharacterWorkspace()

    char_img1 = tmp_path / "char1.png"
    cv2.imwrite(str(char_img1), np.zeros((100, 100, 3), dtype=np.uint8))

    workspace._char_edit.setText(str(char_img1))
    assert workspace._step_completed[0] is True

    # Clear character
    workspace._char_edit.setText("")
    assert workspace._character_path is None
    assert all(comp is False for comp in workspace._step_completed)

    workspace.close()
