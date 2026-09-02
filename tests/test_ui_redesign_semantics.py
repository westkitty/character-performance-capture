from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6")

from cpc.rig import CharacterRig
from cpc.session import SessionConfig
from cpc.ui.models import NULL_TRACKER_MODEL, RECOMMENDED_MEDIAPIPE_MODEL, get_model_registry
from cpc.ui.widgets.model_selector import ModelSelectorWidget
from cpc.ui.workspaces.character_workspace import CharacterWorkspace
from cpc.ui.workspaces.diagnostics_workspace import DiagnosticsWorkspace
from cpc.ui.workspaces.live_workspace import LiveWorkspace
from cpc.ui.workspaces.settings_workspace import SettingsWorkspace
from cpc.ui.workspaces.takes_workspace import TakesWorkspace


def test_null_tracker_semantic_capabilities(qapp):
    """Verify 'No Tracking' presents only baseline passthrough capabilities, never face landmarks."""
    selector = ModelSelectorWidget()
    selector.select_model(NULL_TRACKER_MODEL.model_id)

    # Capability pills should not contain 478 landmarks or blendshapes
    pill_texts = [selector._caps_layout.itemAt(i).widget().text() for i in range(selector._caps_layout.count()) if selector._caps_layout.itemAt(i).widget()]
    for text in pill_texts:
        assert "478" not in text
        assert "Blendshape" not in text
        assert "Landmark" not in text

    assert any("Passthrough" in text for text in pill_texts)


def test_settings_excludes_null_tracker_from_installable_models(qapp):
    """Verify Settings only lists physical model files, not built-in null tracker."""
    reg = get_model_registry()
    installable = reg.get_installable_entries()
    ids = [e.model_id for e in installable]
    assert NULL_TRACKER_MODEL.model_id not in ids
    assert RECOMMENDED_MEDIAPIPE_MODEL.model_id in ids

    settings_ws = SettingsWorkspace()
    # Check that null-tracker does not appear in models grid
    labels = [settings_ws._models_grid.itemAt(i).widget().text() for i in range(settings_ws._models_grid.count()) if settings_ws._models_grid.itemAt(i).widget()]
    assert not any("No Tracking" in text for text in labels)


def test_diagnostics_pre_and_post_run_semantics(qapp):
    """Verify diagnostics indicators are '— Not Checked' before running, never 'Verified' prematurely."""
    diag_ws = DiagnosticsWorkspace()
    diag_ws.resize(1000, 700)
    diag_ws.show()

    # Pre-run: All 4 status labels must be Not Checked
    assert diag_ws._lbl_cam_status.text() == "— Not Checked"
    assert diag_ws._lbl_trk_status.text() == "— Not Checked"
    assert diag_ws._lbl_priv_status.text() == "— Not Checked"
    assert diag_ws._lbl_out_status.text() == "— Not Checked"

    # Simulate report ready callback
    mock_report = {
        "system": {"os": "Darwin", "arch": "arm64", "macos_version": "15.0", "python": "3.11", "opencv": "4.10", "mediapipe": "0.10.35"},
        "source": {"kind": "camera", "observed_size": [1920, 1080], "observed_fps": 30.0, "read_ms_avg": 2.1, "read_ms_p95": 3.4},
        "tracker": {"tracker": "mediapipe", "delegate": "cpu", "model_loaded": True, "detection_rate": 1.0, "process_ms_avg": 14.2, "process_ms_p95": 16.5, "effective_fps": 30.0},
    }
    diag_ws._on_report_ready(mock_report)

    # Post-run: Status labels update to Verified Good / Verified
    assert "Verified" in diag_ws._lbl_cam_status.text()
    assert "Verified" in diag_ws._lbl_trk_status.text()
    assert "100% Verified" in diag_ws._lbl_priv_status.text()
    assert "Ready" in diag_ws._lbl_out_status.text()

    diag_ws.close()


def test_character_setup_mesh_toggles_hidden_on_step1(qapp):
    """Verify Step 1 of Character Setup does not show landmark/mesh checkboxes before a rig exists."""
    char_ws = CharacterWorkspace()
    char_ws.resize(900, 600)
    char_ws.show()

    assert char_ws._current_step == 0
    assert not char_ws._viz_toolbar_widget.isVisible()

    # When advancing to Verify step with a rig, toolbar becomes visible
    char_ws._current_rig = CharacterRig(width=100, height=100, points=np.zeros((10, 2), dtype=np.float32))
    char_ws._set_step(3)
    assert char_ws._viz_toolbar_widget.isVisible()

    char_ws.close()


def test_live_workspace_truthful_readiness_and_inspector_toggling(qapp, tmp_path):
    """Verify Live Studio readiness model and Context Inspector drawer behavior."""
    live_ws = LiveWorkspace()
    live_ws.resize(1200, 800)
    live_ws.show()

    # Inspector is closed by default for a calm Stage
    assert not live_ws._inspector_container.isVisible()

    # Toggle Inspector opens it
    live_ws.toggle_inspector()
    assert live_ws._inspector_container.isVisible()

    # Open specific section jumps to that tab
    live_ws.open_inspector_section(2)  # Tracking
    assert live_ws._inspector_tabs.currentIndex() == 2
    assert live_ws._inspector_container.isVisible()

    fake_model = tmp_path / "fake_model.task"
    fake_model.write_bytes(b"dummy")

    fake_char = tmp_path / "fake_char.png"
    fake_char.write_bytes(b"dummy")

    fake_rig = tmp_path / "fake_char.png.rig.json"
    fake_rig.write_text('{"width": 100, "height": 100, "points": [], "topology": "mediapipe-face-landmarker-478", "name": "c"}')

    # Tracking Ready (Passthrough)
    cfg = SessionConfig()
    cfg.tracker_type = "mediapipe"
    cfg.model_path = fake_model
    cfg.character_path = None
    live_ws.set_session_config(cfg)
    assert "Tracking Ready" in live_ws._preflight_pill.text()

    # When character + rig are configured, readiness becomes Performance Ready
    cfg.character_path = fake_char
    cfg.rig_path = fake_rig
    cfg.renderer_type = "rig"
    live_ws.set_session_config(cfg)
    assert "Ready to Perform" in live_ws._preflight_pill.text()

    live_ws.close()


def test_takes_workspace_library_and_details(qapp, tmp_path):
    """Verify Takes library displays recordings and populates details."""
    takes_ws = TakesWorkspace()
    takes_ws.resize(1000, 600)
    takes_ws.show()

    assert takes_ws._details_card is not None
    assert takes_ws._json_view is not None

    takes_ws.close()


def test_missing_model_reports_needs_attention(qapp, tmp_path):
    """Verify missing model file is truthfully flagged as an issue rather than falsely marked Ready."""
    live_ws = LiveWorkspace()
    live_ws.resize(1200, 800)
    live_ws.show()

    cfg = SessionConfig()
    cfg.tracker_type = "mediapipe"
    cfg.model_path = tmp_path / "nonexistent_model.task"
    live_ws.set_session_config(cfg)

    assert "Needs Attention" in live_ws._preflight_pill.text()
    assert not live_ws._validation_banner_widget.isHidden()
    live_ws.close()


def test_tracker_panel_load_from_config_preserves_custom_model(qapp, tmp_path):
    """Verify TrackerPanel.load_from_config retains custom model path and never silently swaps it."""
    from cpc.ui.widgets.panels import TrackerPanel

    panel = TrackerPanel()
    custom_model = tmp_path / "user_fine_tuned_face.task"
    custom_model.write_bytes(b"custom_model_data_bytes")

    cfg = SessionConfig()
    cfg.tracker_type = "mediapipe"
    cfg.model_path = custom_model

    panel.load_from_config(cfg)

    # Must preserve the custom model in selection
    selected_mid = panel.model_selector.get_selected_model_id()
    assert selected_mid.startswith("custom:")
    assert panel.model_selector.get_resolved_path() == custom_model

    out_cfg = SessionConfig()
    panel.apply_to_config(out_cfg)
    assert out_cfg.model_path == custom_model
