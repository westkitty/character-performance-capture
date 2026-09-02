from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from cpc.session import SessionConfig
from cpc.ui.settings import AppSettings, generate_timestamped_filename


def test_app_settings_preset_lifecycle(tmp_path):
    settings = AppSettings()
    preset_name = "test_custom_studio_preset"

    cfg = SessionConfig(
        source_type="camera",
        camera_index=2,
        mirror=True,
        tracker_type="mediapipe",
        model_path=Path("/tmp/model.task"),
        tracker_delegate="cpu",
        renderer_type="rig",
        character_path=Path("/tmp/char.png"),
        rig_path=Path("/tmp/char.rig.json"),
        expression_gain=1.35,
        head_gain=0.85,
        virtual_camera=True,
        vcam_size=(1920, 1080),
    )

    # Save preset
    settings.save_preset(preset_name, cfg)
    assert preset_name in settings.list_presets()
    assert settings.is_config_matching_preset(preset_name, cfg) is True

    # Modified config check
    cfg_mod = SessionConfig(
        source_type="camera",
        camera_index=1,
    )
    assert settings.is_config_matching_preset(preset_name, cfg_mod) is False

    # Duplicate preset
    dup_name = "test_custom_studio_preset_copy"
    assert settings.duplicate_preset(preset_name, dup_name) is True
    assert dup_name in settings.list_presets()

    # Rename preset
    renamed_name = "test_custom_studio_preset_renamed"
    assert settings.rename_preset(dup_name, renamed_name) is True
    assert dup_name not in settings.list_presets()
    assert renamed_name in settings.list_presets()

    # Load preset
    loaded = settings.load_preset(preset_name)
    assert loaded is not None
    assert loaded.source_type == "camera"
    assert loaded.camera_index == 2
    assert loaded.mirror is True
    assert loaded.tracker_type == "mediapipe"
    assert loaded.tracker_delegate == "cpu"
    assert loaded.renderer_type == "rig"
    assert loaded.expression_gain == 1.35
    assert loaded.head_gain == 0.85
    assert loaded.virtual_camera is True
    assert loaded.vcam_size == (1920, 1080)

    # Export preset to JSON
    export_file = tmp_path / "exported_preset.json"
    assert settings.export_preset_json(preset_name, export_file) is True
    assert export_file.is_file()

    # Import preset under new name
    imported_name = settings.import_preset_json(export_file)
    assert imported_name == preset_name

    # Delete presets
    settings.delete_preset(preset_name)
    settings.delete_preset(renamed_name)
    assert preset_name not in settings.list_presets()
    assert renamed_name not in settings.list_presets()


def test_app_settings_recent_items(tmp_path):
    settings = AppSettings()
    settings.clear_recent_items()

    file1 = tmp_path / "vid1.mp4"
    file2 = tmp_path / "vid2.mp4"
    file1.touch()
    file2.touch()

    settings.add_recent_item("videos", file1)
    settings.add_recent_item("videos", file2)

    recents = settings.get_recent_items("videos")
    assert len(recents) == 2
    assert recents[0] == str(file2.resolve())
    assert recents[1] == str(file1.resolve())

    # Re-adding file1 moves it to top
    settings.add_recent_item("videos", file1)
    recents = settings.get_recent_items("videos")
    assert len(recents) == 2
    assert recents[0] == str(file1.resolve())

    settings.clear_recent_items("videos")
    assert len(settings.get_recent_items("videos")) == 0


def test_app_settings_character_memory_and_favorites(tmp_path):
    settings = AppSettings()
    char_file = tmp_path / "hero.png"
    rig_file = tmp_path / "hero.png.rig.json"
    char_file.touch()
    rig_file.touch()

    # Character Memory
    settings.set_character_memory(char_file, rig_file, exp_gain=1.4, head_gain=0.75)
    mem = settings.get_character_memory(char_file)
    assert mem is not None
    assert mem["rig_path"] == str(rig_file.resolve())
    assert mem["expression_gain"] == 1.4
    assert mem["head_gain"] == 0.75

    # Favorites
    assert settings.is_favorite("characters", char_file) is False
    assert settings.toggle_favorite("characters", char_file) is True
    assert settings.is_favorite("characters", char_file) is True
    assert str(char_file) in settings.list_favorites("characters")
    assert settings.toggle_favorite("characters", char_file) is False
    assert settings.is_favorite("characters", char_file) is False


def test_generate_timestamped_filename(tmp_path):
    p1 = generate_timestamped_filename("take", "cpc", tmp_path)
    assert p1.suffix == ".cpc"
    assert p1.parent == tmp_path
    assert "take_" in p1.name

    # Touch p1 to simulate existing file and prove collision avoidance
    p1.touch()
    p2 = generate_timestamped_filename("take", "cpc", tmp_path)
    assert p2 != p1
    assert p2.name.endswith("_01.cpc") or p2.name != p1.name


def test_app_settings_preferences():
    settings = AppSettings()
    settings.set_countdown_seconds(5)
    assert settings.get_countdown_seconds() == 5

    settings.set_countdown_seconds(0)
    assert settings.get_countdown_seconds() == 0

    settings.set_first_run_completed(False)
    assert settings.is_first_run_completed() is False

    settings.set_first_run_completed(True)
    assert settings.is_first_run_completed() is True
