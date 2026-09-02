from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from cpc.ui.settings import AppSettings
from cpc.ui.widgets.command_palette import CommandPaletteDialog
from cpc.ui.workspaces.character_workspace import CharacterWorkspace
from cpc.ui.workspaces.diagnostics_workspace import DiagnosticsWorkspace
from cpc.ui.workspaces.live_workspace import LiveWorkspace
from cpc.ui.workspaces.settings_workspace import SettingsWorkspace
from cpc.ui.workspaces.takes_workspace import TakesWorkspace


class MainWindow(QMainWindow):
    """Authoritative top-level application window for CPC Studio."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Character Performance Capture Studio")
        self.setMinimumSize(1024, 680)
        self.resize(1360, 860)

        self._settings = AppSettings()
        self._init_ui()
        self._init_menus()
        self._init_shortcuts()
        self._load_initial_state()

    def _init_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        # 1. Live Studio
        self.live_workspace = LiveWorkspace()
        self.live_workspace.open_character_workspace.connect(lambda: self._tabs.setCurrentIndex(1))
        self.live_workspace.open_takes_workspace.connect(self._on_open_take)
        self.live_workspace.open_diagnostics_workspace.connect(lambda: self._tabs.setCurrentIndex(3))
        self._tabs.addTab(self.live_workspace, "Studio (Live)")

        # 2. Character & Rig Studio
        self.character_workspace = CharacterWorkspace()
        self.character_workspace.character_selected.connect(self._on_character_rig_selected)
        self._tabs.addTab(self.character_workspace, "Character && Rig")

        # 3. Takes Inspector
        self.takes_workspace = TakesWorkspace()
        self._tabs.addTab(self.takes_workspace, "Takes")

        # 4. Diagnostics
        self.diagnostics_workspace = DiagnosticsWorkspace()
        self._tabs.addTab(self.diagnostics_workspace, "Diagnostics")

        # 5. Settings / About
        self.settings_workspace = SettingsWorkspace()
        self._tabs.addTab(self.settings_workspace, "Settings / About")

        layout.addWidget(self._tabs)
        self.setCentralWidget(central)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready")
        self.setStatusBar(self.status_bar)

    def _init_menus(self) -> None:
        menubar = self.menuBar()

        # -------------------------------------------------------------
        # File Menu
        # -------------------------------------------------------------
        file_menu = menubar.addMenu("File")

        act_open_vid = QAction("Open Performer Video...", self)
        act_open_vid.setShortcut(QKeySequence.Open)
        act_open_vid.triggered.connect(self._open_performer_video_dialog)
        file_menu.addAction(act_open_vid)

        act_open_char = QAction("Open Character Image...", self)
        act_open_char.setShortcut(QKeySequence("Ctrl+Shift+O" if sys.platform != "darwin" else "Cmd+Shift+O"))
        act_open_char.triggered.connect(self._open_character_image_dialog)
        file_menu.addAction(act_open_char)

        act_open_take = QAction("Open Performance Take (.cpc)...", self)
        act_open_take.triggered.connect(self._open_take_dialog)
        file_menu.addAction(act_open_take)

        file_menu.addSeparator()

        act_reveal_take = QAction("Reveal Captures Folder in Finder", self)
        act_reveal_take.triggered.connect(self._reveal_captures_folder)
        file_menu.addAction(act_reveal_take)

        file_menu.addSeparator()

        act_quit = QAction("Quit CPC Studio", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # -------------------------------------------------------------
        # Session Menu
        # -------------------------------------------------------------
        session_menu = menubar.addMenu("Session")

        self._act_toggle_session = QAction("Start / Stop Session", self)
        self._act_toggle_session.setShortcut(QKeySequence("Space"))
        self._act_toggle_session.triggered.connect(self._toggle_session)
        session_menu.addAction(self._act_toggle_session)

        act_perf_mode = QAction("Toggle Performance Mode", self)
        act_perf_mode.setShortcut(QKeySequence("Ctrl+P" if sys.platform != "darwin" else "Cmd+P"))
        act_perf_mode.triggered.connect(self.live_workspace.toggle_performance_mode)
        session_menu.addAction(act_perf_mode)

        # -------------------------------------------------------------
        # View Menu
        # -------------------------------------------------------------
        view_menu = menubar.addMenu("View")

        act_tab_0 = QAction("Studio (Live)", self)
        act_tab_0.setShortcut(QKeySequence("Ctrl+1" if sys.platform != "darwin" else "Cmd+1"))
        act_tab_0.triggered.connect(lambda: self._tabs.setCurrentIndex(0))
        view_menu.addAction(act_tab_0)

        act_tab_1 = QAction("Character && Rig Studio", self)
        act_tab_1.setShortcut(QKeySequence("Ctrl+2" if sys.platform != "darwin" else "Cmd+2"))
        act_tab_1.triggered.connect(lambda: self._tabs.setCurrentIndex(1))
        view_menu.addAction(act_tab_1)

        act_tab_2 = QAction("Takes Inspector", self)
        act_tab_2.setShortcut(QKeySequence("Ctrl+3" if sys.platform != "darwin" else "Cmd+3"))
        act_tab_2.triggered.connect(lambda: self._tabs.setCurrentIndex(2))
        view_menu.addAction(act_tab_2)

        act_tab_3 = QAction("Diagnostics", self)
        act_tab_3.setShortcut(QKeySequence("Ctrl+4" if sys.platform != "darwin" else "Cmd+4"))
        act_tab_3.triggered.connect(lambda: self._tabs.setCurrentIndex(3))
        view_menu.addAction(act_tab_3)

        act_tab_4 = QAction("Settings / About", self)
        act_tab_4.setShortcut(QKeySequence("Ctrl+5" if sys.platform != "darwin" else "Cmd+5"))
        act_tab_4.triggered.connect(lambda: self._tabs.setCurrentIndex(4))
        view_menu.addAction(act_tab_4)

        view_menu.addSeparator()

        act_palette = QAction("Quick Actions / Command Palette...", self)
        act_palette.setShortcut(QKeySequence("Ctrl+K" if sys.platform != "darwin" else "Cmd+K"))
        act_palette.triggered.connect(self._open_command_palette)
        view_menu.addAction(act_palette)

        # -------------------------------------------------------------
        # Tools Menu
        # -------------------------------------------------------------
        tools_menu = menubar.addMenu("Tools")

        act_derive = QAction("Derive Rig for Character...", self)
        act_derive.triggered.connect(lambda: self._tabs.setCurrentIndex(1))
        tools_menu.addAction(act_derive)

        act_diag = QAction("Run Hardware Diagnostics Probe...", self)
        act_diag.triggered.connect(lambda: self._tabs.setCurrentIndex(3))
        tools_menu.addAction(act_diag)

        act_copy_cli = QAction("Copy CLI Terminal Command", self)
        act_copy_cli.setShortcut(QKeySequence("Ctrl+Shift+C" if sys.platform != "darwin" else "Cmd+Shift+C"))
        act_copy_cli.triggered.connect(self._copy_cli_command)
        tools_menu.addAction(act_copy_cli)

        # -------------------------------------------------------------
        # Help Menu
        # -------------------------------------------------------------
        help_menu = menubar.addMenu("Help")

        act_about = QAction("About Character Performance Capture", self)
        act_about.triggered.connect(lambda: self._tabs.setCurrentIndex(4))
        help_menu.addAction(act_about)

    def _init_shortcuts(self) -> None:
        # Command palette global shortcut
        cmd_k = QShortcut(QKeySequence("Ctrl+K" if sys.platform != "darwin" else "Cmd+K"), self)
        cmd_k.activated.connect(self._open_command_palette)

    def _open_command_palette(self) -> None:
        actions = [
            ("Start Session", "Begin live capture and rendering pipeline", "Space", self.live_workspace.start_session),
            ("Stop Session", "Stop currently running capture cleanly", "Space", self.live_workspace.stop_session),
            ("Toggle Performance Mode", "Full-preview distraction-free canvas view", "Cmd+P", self.live_workspace.toggle_performance_mode),
            ("Go to Studio (Live)", "Primary live capture workspace", "Cmd+1", lambda: self._tabs.setCurrentIndex(0)),
            ("Go to Character & Rig Studio", "Character artwork & landmark derivation", "Cmd+2", lambda: self._tabs.setCurrentIndex(1)),
            ("Go to Takes Inspector", "Inspect .cpc takes & performance metrics", "Cmd+3", lambda: self._tabs.setCurrentIndex(2)),
            ("Go to Diagnostics", "Hardware probe & benchmark doctor", "Cmd+4", lambda: self._tabs.setCurrentIndex(3)),
            ("Go to Settings / About", "System readiness, preferences & license", "Cmd+5", lambda: self._tabs.setCurrentIndex(4)),
            ("Open Performer Video...", "Choose a recorded video file as input", "Cmd+O", self._open_performer_video_dialog),
            ("Open Character Image...", "Choose character PNG reference", "Cmd+Shift+O", self._open_character_image_dialog),
            ("Open Performance Take (.cpc)...", "Inspect a recorded .cpc file", "", self._open_take_dialog),
            ("Copy CLI Command", "Copy equivalent terminal command line", "Cmd+Shift+C", self._copy_cli_command),
            ("Save Session Preset...", "Save current configuration to local preset", "", self.live_workspace._save_current_preset),
            ("Reset UI Settings", "Restore all preferences to defaults", "", self.settings_workspace._reset_settings),
        ]
        dialog = CommandPaletteDialog(actions, self)
        dialog.exec()

    def _toggle_session(self) -> None:
        if self.live_workspace.is_running():
            self.live_workspace.stop_session()
        else:
            self.live_workspace.start_session()

    def _open_performer_video_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Performer Video",
            self._settings.get_last_directory(),
            "Video Files (*.mp4 *.mov *.avi *.mkv);;All Files (*)",
        )
        if path:
            self._settings.set_last_directory(path)
            self._settings.add_recent_item("videos", path)
            cfg = self.live_workspace.get_session_config()
            cfg.source_type = "video"
            cfg.video_path = Path(path)
            self.live_workspace.set_session_config(cfg)
            self._tabs.setCurrentIndex(0)

    def _open_character_image_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Image",
            self._settings.get_last_directory(),
            "Image Files (*.png *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if path:
            self._settings.set_last_directory(path)
            self._settings.add_recent_item("characters", path)
            self.character_workspace.set_selected_character(Path(path))
            self._tabs.setCurrentIndex(1)

    def _open_take_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Performance Capture Take",
            self._settings.get_last_directory(),
            "CPC Takes (*.cpc *.partial);;All Files (*)",
        )
        if path:
            self._settings.set_last_directory(path)
            self._settings.add_recent_item("takes", path)
            self._on_open_take(Path(path))

    def _reveal_captures_folder(self) -> None:
        dest = Path("takes").resolve() if Path("takes").exists() else Path.cwd().resolve()
        QDesktopServices.openUrl(f"file://{dest}")

    def _copy_cli_command(self) -> None:
        cfg = self.live_workspace.get_session_config()
        cmd = cfg.to_cli_command()
        QApplication.clipboard().setText(cmd)
        self.status_bar.showMessage("CLI command copied to clipboard", 3000)

    def _on_character_rig_selected(self, char_path: Path, rig_path: Path) -> None:
        cfg = self.live_workspace.get_session_config()
        cfg.renderer_type = "rig"
        cfg.character_path = char_path
        cfg.rig_path = rig_path
        self.live_workspace.set_session_config(cfg)
        self._tabs.setCurrentIndex(0)
        self.status_bar.showMessage(f"Character '{char_path.name}' applied to Live Studio", 4000)

    def _on_open_take(self, take_path: Path) -> None:
        self.takes_workspace.inspect_path(take_path)
        self._tabs.setCurrentIndex(2)

    def _load_initial_state(self) -> None:
        cfg = self._settings.load_session_config()
        self.live_workspace.set_session_config(cfg)

    def closeEvent(self, event: QCloseEvent) -> None:
        # Save session configuration on clean exit
        if self.live_workspace.is_running():
            self.live_workspace.stop_session()
            # Brief wait to ensure worker thread cleans up resources safely
            worker = self.live_workspace._worker
            if worker is not None:
                worker.wait(1500)

        cfg = self.live_workspace.get_session_config()
        self._settings.save_session_config(cfg)
        event.accept()
