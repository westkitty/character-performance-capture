from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings

from cpc.session import SessionConfig

ORGANIZATION_NAME = "WestKitty"
APPLICATION_NAME = "CharacterPerformanceCapture"
PRESET_SCHEMA_VERSION = 1


def generate_timestamped_filename(prefix: str, ext: str, directory: str | Path | None = None) -> Path:
    """Generate a deterministic, human-readable, non-colliding timestamped output file path."""
    target_dir = Path(directory) if directory else Path.cwd()
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
    base_name = f"{prefix}_{timestamp}"
    ext = ext.lstrip(".")
    candidate = target_dir / f"{base_name}.{ext}"

    # Handle rapid successive creations with counter suffix
    counter = 1
    while candidate.exists():
        candidate = target_dir / f"{base_name}_{counter:02d}.{ext}"
        counter += 1

    return candidate


class AppSettings:
    """Manages local UI preferences, presets, recents, character memory, and layout persistence using QSettings."""

    def __init__(self) -> None:
        self._settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)

    # -----------------------------------------------------------------
    # Session Configuration Persistence
    # -----------------------------------------------------------------
    def load_session_config(self) -> SessionConfig:
        """Restore saved session preferences into a SessionConfig."""
        cfg = SessionConfig()

        cfg.camera_index = int(self._settings.value("camera_index", 0))
        cfg.mirror = bool(self._settings.value("mirror", False, type=bool))

        video_path_str = self._settings.value("video_path", "")
        if video_path_str and Path(video_path_str).is_file():
            cfg.video_path = Path(video_path_str)
            cfg.source_type = "video"

        cfg.loop_video = bool(self._settings.value("loop_video", True, type=bool))
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

    # -----------------------------------------------------------------
    # First-Run Experience
    # -----------------------------------------------------------------
    def is_first_run_completed(self) -> bool:
        return bool(self._settings.value("first_run_completed", False, type=bool))

    def set_first_run_completed(self, completed: bool = True) -> None:
        self._settings.setValue("first_run_completed", completed)

    # -----------------------------------------------------------------
    # Session Presets (Named Local Configurations)
    # -----------------------------------------------------------------
    def list_presets(self) -> list[str]:
        raw = self._settings.value("presets_json", "{}")
        try:
            presets = json.loads(str(raw))
            return sorted(presets.keys())
        except (ValueError, TypeError):
            return []

    def get_preset_data(self, name: str) -> dict[str, Any] | None:
        raw = self._settings.value("presets_json", "{}")
        try:
            presets = json.loads(str(raw))
            return presets.get(name)
        except (ValueError, TypeError):
            return None

    def save_preset(self, name: str, cfg: SessionConfig) -> None:
        raw = self._settings.value("presets_json", "{}")
        try:
            presets = json.loads(str(raw))
        except (ValueError, TypeError):
            presets = {}

        preset_data = {
            "schema_version": PRESET_SCHEMA_VERSION,
            "name": name,
            "source_type": cfg.source_type,
            "camera_index": cfg.camera_index,
            "video_path": str(cfg.video_path) if cfg.video_path else None,
            "loop_video": cfg.loop_video,
            "mirror": cfg.mirror,
            "tracker_type": cfg.tracker_type,
            "model_path": str(cfg.model_path) if cfg.model_path else None,
            "tracker_delegate": cfg.tracker_delegate,
            "renderer_type": cfg.renderer_type,
            "character_path": str(cfg.character_path) if cfg.character_path else None,
            "rig_path": str(cfg.rig_path) if cfg.rig_path else None,
            "expression_gain": cfg.expression_gain,
            "head_gain": cfg.head_gain,
            "virtual_camera": cfg.virtual_camera,
            "vcam_size": list(cfg.vcam_size),
        }
        presets[name] = preset_data
        self._settings.setValue("presets_json", json.dumps(presets))

    def load_preset(self, name: str) -> SessionConfig | None:
        raw = self._settings.value("presets_json", "{}")
        try:
            presets = json.loads(str(raw))
            if name not in presets:
                return None
            data = presets[name]
            cfg = SessionConfig()
            cfg.source_type = data.get("source_type", "camera")
            cfg.camera_index = int(data.get("camera_index", 0))
            if data.get("video_path"):
                cfg.video_path = Path(data["video_path"])
            cfg.loop_video = bool(data.get("loop_video", True))
            cfg.mirror = bool(data.get("mirror", False))
            cfg.tracker_type = data.get("tracker_type", "null")
            if data.get("model_path"):
                cfg.model_path = Path(data["model_path"])
            cfg.tracker_delegate = data.get("tracker_delegate", "cpu")
            cfg.renderer_type = data.get("renderer_type", "passthrough")
            if data.get("character_path"):
                cfg.character_path = Path(data["character_path"])
            if data.get("rig_path"):
                cfg.rig_path = Path(data["rig_path"])
            cfg.expression_gain = float(data.get("expression_gain", 1.0))
            cfg.head_gain = float(data.get("head_gain", 1.0))
            cfg.virtual_camera = bool(data.get("virtual_camera", False))
            if data.get("vcam_size") and len(data["vcam_size"]) == 2:
                cfg.vcam_size = (int(data["vcam_size"][0]), int(data["vcam_size"][1]))
            return cfg
        except (ValueError, TypeError, KeyError):
            return None

    def delete_preset(self, name: str) -> None:
        raw = self._settings.value("presets_json", "{}")
        try:
            presets = json.loads(str(raw))
            if name in presets:
                del presets[name]
                self._settings.setValue("presets_json", json.dumps(presets))
        except (ValueError, TypeError):
            pass

    def duplicate_preset(self, src_name: str, dst_name: str) -> bool:
        data = self.get_preset_data(src_name)
        if data is None:
            return False
        new_data = dict(data)
        new_data["name"] = dst_name
        raw = self._settings.value("presets_json", "{}")
        try:
            presets = json.loads(str(raw))
            presets[dst_name] = new_data
            self._settings.setValue("presets_json", json.dumps(presets))
            return True
        except (ValueError, TypeError):
            return False

    def rename_preset(self, old_name: str, new_name: str) -> bool:
        if old_name == new_name:
            return True
        data = self.get_preset_data(old_name)
        if data is None:
            return False
        self.delete_preset(old_name)
        data["name"] = new_name
        raw = self._settings.value("presets_json", "{}")
        try:
            presets = json.loads(str(raw)) if raw else {}
            presets[new_name] = data
            self._settings.setValue("presets_json", json.dumps(presets))
            return True
        except (ValueError, TypeError):
            return False

    def is_config_matching_preset(self, name: str, cfg: SessionConfig) -> bool:
        saved_cfg = self.load_preset(name)
        if saved_cfg is None:
            return False
        return (
            cfg.source_type == saved_cfg.source_type
            and cfg.camera_index == saved_cfg.camera_index
            and cfg.video_path == saved_cfg.video_path
            and cfg.loop_video == saved_cfg.loop_video
            and cfg.mirror == saved_cfg.mirror
            and cfg.tracker_type == saved_cfg.tracker_type
            and cfg.model_path == saved_cfg.model_path
            and cfg.tracker_delegate == saved_cfg.tracker_delegate
            and cfg.renderer_type == saved_cfg.renderer_type
            and cfg.character_path == saved_cfg.character_path
            and cfg.rig_path == saved_cfg.rig_path
            and abs(cfg.expression_gain - saved_cfg.expression_gain) < 0.001
            and abs(cfg.head_gain - saved_cfg.head_gain) < 0.001
            and cfg.virtual_camera == saved_cfg.virtual_camera
            and cfg.vcam_size == saved_cfg.vcam_size
        )

    def export_preset_json(self, name: str, dest_path: Path) -> bool:
        raw = self._settings.value("presets_json", "{}")
        try:
            presets = json.loads(str(raw))
            if name in presets:
                dest_path.write_text(json.dumps(presets[name], indent=2), encoding="utf-8")
                return True
            return False
        except (ValueError, TypeError, OSError):
            return False

    def import_preset_json(self, src_path: Path) -> str | None:
        try:
            data = json.loads(src_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return None
            name = str(data.get("name") or src_path.stem)
            raw = self._settings.value("presets_json", "{}")
            presets = json.loads(str(raw)) if raw else {}
            presets[name] = data
            self._settings.setValue("presets_json", json.dumps(presets))
            return name
        except (ValueError, TypeError, OSError):
            return None

    # -----------------------------------------------------------------
    # Per-Character Memory (Gains & Rig Bindings)
    # -----------------------------------------------------------------
    def set_character_memory(
        self,
        char_path: str | Path,
        rig_path: str | Path | None = None,
        exp_gain: float = 1.0,
        head_gain: float = 1.0,
    ) -> None:
        key = "character_memory_json"
        raw = self._settings.value(key, "{}")
        try:
            memory = json.loads(str(raw))
        except (ValueError, TypeError):
            memory = {}

        p_str = str(Path(char_path).resolve())
        memory[p_str] = {
            "rig_path": str(Path(rig_path).resolve()) if rig_path else None,
            "expression_gain": exp_gain,
            "head_gain": head_gain,
        }
        self._settings.setValue(key, json.dumps(memory))

    def get_character_memory(self, char_path: str | Path) -> dict[str, Any] | None:
        key = "character_memory_json"
        raw = self._settings.value(key, "{}")
        try:
            memory = json.loads(str(raw))
            p_str = str(Path(char_path).resolve())
            return memory.get(p_str)
        except (ValueError, TypeError):
            return None

    # -----------------------------------------------------------------
    # Favorites (Characters, Presets)
    # -----------------------------------------------------------------
    def toggle_favorite(self, category: str, item_id: str | Path) -> bool:
        key = f"favorites_{category}"
        raw = self._settings.value(key, "[]")
        try:
            favs: list[str] = json.loads(str(raw))
        except (ValueError, TypeError):
            favs = []

        item_str = str(item_id)
        if item_str in favs:
            favs.remove(item_str)
            result = False
        else:
            favs.append(item_str)
            result = True

        self._settings.setValue(key, json.dumps(favs))
        return result

    def is_favorite(self, category: str, item_id: str | Path) -> bool:
        key = f"favorites_{category}"
        raw = self._settings.value(key, "[]")
        try:
            favs: list[str] = json.loads(str(raw))
            return str(item_id) in favs
        except (ValueError, TypeError):
            return False

    def list_favorites(self, category: str) -> list[str]:
        key = f"favorites_{category}"
        raw = self._settings.value(key, "[]")
        try:
            return json.loads(str(raw))
        except (ValueError, TypeError):
            return []

    # -----------------------------------------------------------------
    # Recent Items (Videos, Characters, Takes)
    # -----------------------------------------------------------------
    def add_recent_item(self, category: str, path: str | Path) -> None:
        key = f"recent_{category}"
        raw = self._settings.value(key, "[]")
        try:
            items = json.loads(str(raw))
        except (ValueError, TypeError):
            items = []

        path_str = str(Path(path).resolve())
        if path_str in items:
            items.remove(path_str)
        items.insert(0, path_str)
        # Keep up to 10 recents
        items = items[:10]
        self._settings.setValue(key, json.dumps(items))

    def get_recent_items(self, category: str) -> list[str]:
        key = f"recent_{category}"
        raw = self._settings.value(key, "[]")
        try:
            items = json.loads(str(raw))
            # Filter existing paths
            return [p for p in items if Path(p).exists()]
        except (ValueError, TypeError):
            return []

    def clear_recent_items(self, category: str | None = None) -> None:
        if category:
            self._settings.remove(f"recent_{category}")
        else:
            self._settings.remove("recent_videos")
            self._settings.remove("recent_characters")
            self._settings.remove("recent_takes")

    # -----------------------------------------------------------------
    # Countdown & Output Preferences
    # -----------------------------------------------------------------
    def get_countdown_seconds(self) -> int:
        return int(self._settings.value("countdown_seconds", 0))

    def set_countdown_seconds(self, seconds: int) -> None:
        self._settings.setValue("countdown_seconds", max(0, min(10, seconds)))

    def get_default_output_directory(self) -> str:
        return str(self._settings.value("default_output_directory", str(Path.cwd() / "takes")))

    def set_default_output_directory(self, path: str | Path) -> None:
        self._settings.setValue("default_output_directory", str(Path(path).resolve()))

    # -----------------------------------------------------------------
    # Layout & General Preferences
    # -----------------------------------------------------------------
    def get_last_directory(self) -> str:
        return str(self._settings.value("last_directory", str(Path.home())))

    def set_last_directory(self, path: str | Path) -> None:
        p = Path(path)
        dir_path = p.parent if p.is_file() else p
        self._settings.setValue("last_directory", str(dir_path))

    def reset_all(self) -> None:
        """Clear all stored preferences and reset to fresh state."""
        self._settings.clear()
