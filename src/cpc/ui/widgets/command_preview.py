from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
)

from cpc.session import SessionConfig


class CommandPreviewWidget(QGroupBox):
    """Collapsible command preview displaying equivalent CLI command with one-click copy."""

    def __init__(self, parent=None) -> None:
        super().__init__("Equivalent CLI Command", parent)
        self.setCheckable(True)
        self.setChecked(False)  # Collapsible by default
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(8)

        self._cmd_edit = QLineEdit()
        self._cmd_edit.setReadOnly(True)
        self._cmd_edit.setStyleSheet("font-family: monospace; font-size: 11px; background: #121214;")
        layout.addWidget(self._cmd_edit, 1)

        self._copy_button = QPushButton("Copy Command")
        self._copy_button.clicked.connect(self._copy_to_clipboard)
        layout.addWidget(self._copy_button)

    def update_command(self, config: SessionConfig) -> None:
        """Regenerate the equivalent CLI command string from session configuration."""
        cmd = config.to_command_string()
        self._cmd_edit.setText(cmd)
        self._cmd_edit.setCursorPosition(0)

    def _copy_to_clipboard(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(self._cmd_edit.text())
            orig_text = self._copy_button.text()
            self._copy_button.setText("Copied!")
            self._copy_button.setEnabled(False)
            from PySide6.QtCore import QTimer

            QTimer.singleShot(1200, lambda: self._reset_copy_btn(orig_text))

    def _reset_copy_btn(self, text: str) -> None:
        self._copy_button.setText(text)
        self._copy_button.setEnabled(True)
