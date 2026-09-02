from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

from cpc.session import SessionConfig

ORGANIZATION_NAME = "WestKitty"
APPLICATION_NAME = "CharacterPerformanceCapture"


class AppSettings:
    """Manages local UI preferences persistence using QSettings."""

    def __init__(self) -> None:
        self._settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)

    def load_session_config(self) -> SessionConfig:
        """Restore saved session preferences into a SessionConfig."""
        cfg = SessionConfig()

        cfg.camera_index = int(self._settings.value("camera_index", 0))
        cfg.mirror = bool(self._settings.value("mirror", False, type=bool))

        video_path_str = self._settings.value("video_path", "")
        if video_path_str and Path(video_path_str).is_file():
            cfg.video_path = Path(video_path_str)

        cfg.loop_video = bool(self._settings.value("loop_video", False, type=bool))
        cfg.tracker_type = str(self._settings.value("tracker_type", "null"))

        model_path_str = self._settings.value("model_path", "")
        if model_path_str and Path(model_path_str).is_file():
            cfg.model_path = Path(model_path_str)

        cfg.tracker_delegate = str(self._settings.value("tracker_delegate", "cpu"))
        cfg.renderer_type = str(self._settings.value("renderer_type", "passthrough"))

        char_path_str = self._settings.value("character_path", "")
        if char_path_str and Path(char_path_str).is_file():
            cfg.character_path = Path(char_path_str)

        rig_path_str = self._settings.value("rig_path", "")
        if rig_path_str and Path(rig_path_str).is_file():
            cfg.rig_path = Path(rig_path_str)

        cfg.expression_gain = float(self._settings.value("expression_gain", 1.0))
        cfg.head_gain = float(self._settings.value("head_gain", 1.0))

        vcam_size_str = str(self._settings.value("vcam_size", "1280x720"))
        try:
            parts = vcam_size_str.lower().split("x", 1)
            cfg.vcam_size = (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            cfg.vcam_size = (1280, 720)

        cfg.virtual_camera = bool(self._settings.value("virtual_camera", False, type=bool))
        return cfg

    def save_session_config(self, cfg: SessionConfig) -> None:
        """Persist session preferences."""
        self._settings.setValue("camera_index", cfg.camera_index)
        self._settings.setValue("mirror", cfg.mirror)
        if cfg.video_path:
            self._settings.setValue("video_path", str(cfg.video_path))
        self._settings.setValue("loop_video", cfg.loop_video)
        self._settings.setValue("tracker_type", cfg.tracker_type)
        if cfg.model_path:
            self._settings.setValue("model_path", str(cfg.model_path))
        self._settings.setValue("tracker_delegate", cfg.tracker_delegate)
        self._settings.setValue("renderer_type", cfg.renderer_type)
        if cfg.character_path:
            self._settings.setValue("character_path", str(cfg.character_path))
        if cfg.rig_path:
            self._settings.setValue("rig_path", str(cfg.rig_path))
        self._settings.setValue("expression_gain", cfg.expression_gain)
        self._settings.setValue("head_gain", cfg.head_gain)
        self._settings.setValue("vcam_size", f"{cfg.vcam_size[0]}x{cfg.vcam_size[1]}")
        self._settings.setValue("virtual_camera", cfg.virtual_camera)

    def get_last_directory(self) -> str:
        return str(self._settings.value("last_directory", str(Path.home())))

    def set_last_directory(self, path: str | Path) -> None:
        p = Path(path)
        dir_path = p.parent if p.is_file() else p
        self._settings.setValue("last_directory", str(dir_path))

    def reset_all(self) -> None:
        """Clear all stored preferences."""
        self._settings.clear()
