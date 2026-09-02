from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QTabWidget,
)

from cpc.ui.settings import AppSettings
from cpc.ui.workspaces.character_workspace import CharacterWorkspace
from cpc.ui.workspaces.diagnostics_workspace import DiagnosticsWorkspace
from cpc.ui.workspaces.live_workspace import LiveWorkspace
from cpc.ui.workspaces.settings_workspace import SettingsWorkspace
from cpc.ui.workspaces.takes_workspace import TakesWorkspace


class MainWindow(QMainWindow):
    """Main Application Window for Character Performance Capture."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Character Performance Capture")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        self._settings = AppSettings()
        self._init_ui()
        self._load_preferences()
        self._setup_shortcuts()

    def _init_ui(self) -> None:
        self._tabs = QTabWidget(self)
        self._tabs.setDocumentMode(True)

        # Tab 1: Live Performance Studio
        self.live_workspace = LiveWorkspace(self)
        self.live_workspace.open_character_workspace.connect(self._goto_character_studio)
        self._tabs.addTab(self.live_workspace, "Studio (Live)")

        # Tab 2: Character & Rig Studio
        self.character_workspace = CharacterWorkspace(self)
        self.character_workspace.character_selected.connect(self._on_character_chosen)
        self._tabs.addTab(self.character_workspace, "Character & Rig")

        # Tab 3: Takes Inspector
        self.takes_workspace = TakesWorkspace(self)
        self._tabs.addTab(self.takes_workspace, "Takes")

        # Tab 4: Diagnostics
        self.diagnostics_workspace = DiagnosticsWorkspace(self)
        self._tabs.addTab(self.diagnostics_workspace, "Diagnostics")

        # Tab 5: Settings / About
        self.settings_workspace = SettingsWorkspace(self)
        self._tabs.addTab(self.settings_workspace, "Settings / About")

        self.setCentralWidget(self._tabs)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _setup_shortcuts(self) -> None:
        # Settings shortcut (Cmd+, on macOS, Ctrl+, elsewhere)
        settings_action = QAction(self)
        settings_action.setShortcut(QKeySequence.Preferences)
        settings_action.triggered.connect(lambda: self._tabs.setCurrentIndex(4))
        self.addAction(settings_action)

    def keyPressEvent(self, event) -> None:
        # Global Esc to stop active capture
        if event.key() == Qt.Key_Escape and self.live_workspace.is_running():
            self.live_workspace.stop_session()
            event.accept()
            return

        # Space to Start / Stop when focus is not inside a text edit
        if event.key() == Qt.Key_Space:
            focus_widget = self.focusWidget()
            from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QTextEdit
            if not isinstance(focus_widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
                if self.live_workspace.is_running():
                    self.live_workspace.stop_session()
                elif self.live_workspace.start_btn.isEnabled():
                    self.live_workspace.start_session()
                event.accept()
                return

        super().keyPressEvent(event)

    def _goto_character_studio(self) -> None:
        cfg = self.live_workspace.get_session_config()
        if cfg.character_path:
            self.character_workspace.set_selected_character(cfg.character_path, cfg.model_path)
        self._tabs.setCurrentIndex(1)

    def _on_character_chosen(self, char_path: Path, rig_path: Path) -> None:
        cfg = self.live_workspace.get_session_config()
        cfg.renderer_type = "rig"
        cfg.character_path = char_path
        cfg.rig_path = rig_path
        self.live_workspace.set_session_config(cfg)
        self._tabs.setCurrentIndex(0)
        self.status_bar.showMessage(f"Selected character: {char_path.name}", 4000)

    def _load_preferences(self) -> None:
        cfg = self._settings.load_session_config()
        self.live_workspace.set_session_config(cfg)

    def _save_preferences(self) -> None:
        cfg = self.live_workspace.get_session_config()
        self._settings.save_session_config(cfg)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.live_workspace.is_running():
            self.status_bar.showMessage("Stopping active session before closing...")
            self.live_workspace.stop_session()
            # Wait up to 3 seconds for worker to finish
            if self.live_workspace._worker is not None:
                self.live_workspace._worker.wait(3000)

        self._save_preferences()
        event.accept()
