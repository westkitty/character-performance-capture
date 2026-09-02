from __future__ import annotations

from dataclasses import dataclass

from cpc.app import build_parser


@dataclass(frozen=True)
class CapabilityMapping:
    cli_flag: str
    dest: str
    ui_component: str
    workspace: str
    description: str


# Explicit Parity Registry mapping every CLI user-facing capability to GUI controls/screens
CLI_UI_PARITY_REGISTRY: dict[str, CapabilityMapping] = {
    "camera": CapabilityMapping(
        cli_flag="--camera",
        dest="camera",
        ui_component="SourcePanel.camera_index_spin",
        workspace="Live",
        description="Camera device index selector",
    ),
    "video": CapabilityMapping(
        cli_flag="--video",
        dest="video",
        ui_component="SourcePanel.video_path_edit",
        workspace="Live",
        description="Local video file picker",
    ),
    "loop": CapabilityMapping(
        cli_flag="--loop",
        dest="loop",
        ui_component="SourcePanel.loop_checkbox",
        workspace="Live",
        description="Video file looping toggle",
    ),
    "width": CapabilityMapping(
        cli_flag="--width",
        dest="width",
        ui_component="SourcePanel.width_spin / AdvancedPanel.width_spin",
        workspace="Live",
        description="Requested capture width",
    ),
    "height": CapabilityMapping(
        cli_flag="--height",
        dest="height",
        ui_component="SourcePanel.height_spin / AdvancedPanel.height_spin",
        workspace="Live",
        description="Requested capture height",
    ),
    "fps": CapabilityMapping(
        cli_flag="--fps",
        dest="fps",
        ui_component="SourcePanel.fps_spin / AdvancedPanel.fps_spin",
        workspace="Live",
        description="Requested capture frame rate",
    ),
    "mirror": CapabilityMapping(
        cli_flag="--mirror",
        dest="mirror",
        ui_component="SourcePanel.mirror_checkbox",
        workspace="Live",
        description="Horizontal frame mirroring toggle",
    ),
    "tracker": CapabilityMapping(
        cli_flag="--tracker",
        dest="tracker",
        ui_component="TrackerPanel.tracker_combo",
        workspace="Live",
        description="Tracker backend selector (null / mediapipe)",
    ),
    "model": CapabilityMapping(
        cli_flag="--model",
        dest="model",
        ui_component="TrackerPanel.model_path_edit / CharacterWorkspace.model_edit",
        workspace="Live / Character & Rig",
        description="Face Landmarker .task model picker",
    ),
    "tracker_delegate": CapabilityMapping(
        cli_flag="--tracker-delegate",
        dest="tracker_delegate",
        ui_component="TrackerPanel.delegate_combo",
        workspace="Live / Character & Rig",
        description="Inference delegate (cpu / gpu)",
    ),
    "render": CapabilityMapping(
        cli_flag="--render",
        dest="render",
        ui_component="RendererPanel.renderer_combo",
        workspace="Live",
        description="Renderer selector (passthrough / rig)",
    ),
    "character": CapabilityMapping(
        cli_flag="--character",
        dest="character",
        ui_component="RendererPanel.character_edit / CharacterWorkspace.character_edit",
        workspace="Live / Character & Rig",
        description="Character reference image picker",
    ),
    "rig": CapabilityMapping(
        cli_flag="--rig",
        dest="rig",
        ui_component="RendererPanel.rig_edit / CharacterWorkspace.rig_edit",
        workspace="Live / Character & Rig",
        description="Explicit rig sidecar file picker",
    ),
    "derive_rig": CapabilityMapping(
        cli_flag="--derive-rig",
        dest="derive_rig",
        ui_component="CharacterWorkspace.derive_button / RendererPanel.derive_button",
        workspace="Character & Rig",
        description="Derive rig from character image and model",
    ),
    "expression_gain": CapabilityMapping(
        cli_flag="--expression-gain",
        dest="expression_gain",
        ui_component="RendererPanel.expression_gain_spin",
        workspace="Live",
        description="Facial expression deformation gain",
    ),
    "head_gain": CapabilityMapping(
        cli_flag="--head-gain",
        dest="head_gain",
        ui_component="RendererPanel.head_gain_spin",
        workspace="Live",
        description="Head motion rotational gain",
    ),
    "record_performance": CapabilityMapping(
        cli_flag="--record-performance",
        dest="record_performance",
        ui_component="OutputsPanel.record_cpc_checkbox + path_edit",
        workspace="Live",
        description="Portable performance state (.cpc) recording",
    ),
    "record_video": CapabilityMapping(
        cli_flag="--record-video",
        dest="record_video",
        ui_component="OutputsPanel.record_video_checkbox + path_edit",
        workspace="Live",
        description="Rendered preview MP4 recording",
    ),
    "virtual_camera": CapabilityMapping(
        cli_flag="--virtual-camera",
        dest="virtual_camera",
        ui_component="OutputsPanel.vcam_checkbox",
        workspace="Live",
        description="Virtual camera broadcast output",
    ),
    "vcam_size": CapabilityMapping(
        cli_flag="--vcam-size",
        dest="vcam_size",
        ui_component="OutputsPanel.vcam_size_combo",
        workspace="Live",
        description="Virtual camera output resolution",
    ),
    "no_window": CapabilityMapping(
        cli_flag="--no-window",
        dest="no_window",
        ui_component="AdvancedPanel.show_preview_checkbox",
        workspace="Live",
        description="Show or hide rendered preview stream",
    ),
    "frames": CapabilityMapping(
        cli_flag="--frames",
        dest="frames",
        ui_component="AdvancedPanel.frames_limit_spin",
        workspace="Live",
        description="Stop session after N processed frames",
    ),
    "inspect_performance": CapabilityMapping(
        cli_flag="--inspect-performance",
        dest="inspect_performance",
        ui_component="TakesWorkspace.open_take_button / drop_target",
        workspace="Takes",
        description="Capture Inspector for .cpc and partial takes",
    ),
    "doctor": CapabilityMapping(
        cli_flag="--doctor",
        dest="doctor",
        ui_component="DiagnosticsWorkspace.run_doctor_button",
        workspace="Diagnostics",
        description="Hardware and runtime probe diagnostics",
    ),
    "doctor_frames": CapabilityMapping(
        cli_flag="--doctor-frames",
        dest="doctor_frames",
        ui_component="DiagnosticsWorkspace.sample_frames_spin",
        workspace="Diagnostics",
        description="Number of probe sample frames for doctor",
    ),
}

# Non-functional or internal flags excluded from capability parity check
EXCLUDED_CLI_DESTS = {"help"}


def verify_cli_ui_parity() -> tuple[bool, list[str]]:
    """Assert that every user-facing CLI flag in build_parser() is mapped in the registry."""
    parser = build_parser()
    missing: list[str] = []

    for action in parser._actions:
        dest = action.dest
        if dest in EXCLUDED_CLI_DESTS:
            continue
        if dest not in CLI_UI_PARITY_REGISTRY:
            missing.append(f"CLI option '{action.option_strings}' (dest='{dest}') is missing from UI parity registry")

    return len(missing) == 0, missing
