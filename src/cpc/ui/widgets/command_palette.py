from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class CommandPaletteDialog(QDialog):
    """Sleek Spotlight-style Quick Actions modal (Cmd+K)."""

    def __init__(self, actions: list[tuple[str, str, str, Callable[[], None]]], parent=None) -> None:
        """
        actions: list of (title, subtitle, shortcut_text, callback)
        """
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(560)
        self.setMaximumWidth(640)
        self._all_actions = actions
        self._filtered_actions = list(actions)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        container = QListWidget(self)
        container.setStyleSheet("""
            QListWidget {
                background-color: #16161c;
                border: 1px solid #2e2e3a;
                border-radius: 10px;
                padding: 6px;
                color: #f4f4f6;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-radius: 6px;
                margin-bottom: 2px;
            }
            QListWidget::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            QListWidget::item:hover:!selected {
                background-color: #202028;
            }
        """)

        # Search bar
        self._search_edit = QLineEdit(self)
        self._search_edit.setPlaceholderText("Type a command or search action (e.g. Start, Video, Character, Doctor)...")
        self._search_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a24;
                border: 1px solid #2c2c38;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                color: #ffffff;
                margin: 8px 8px 4px 8px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
        """)
        self._search_edit.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search_edit)

        self._list_widget = container
        self._list_widget.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self._list_widget)

        self._populate_list(self._all_actions)
        self._search_edit.setFocus()

    def _populate_list(self, actions: list[tuple[str, str, str, Callable[[], None]]]) -> None:
        self._list_widget.clear()
        self._filtered_actions = actions
        for title, subtitle, shortcut_str, _ in actions:
            item_text = f"{title}"
            if subtitle:
                item_text += f"  —  {subtitle}"
            if shortcut_str:
                item_text += f"   [{shortcut_str}]"

            item = QListWidgetItem(item_text)
            self._list_widget.addItem(item)

        if self._list_widget.count() > 0:
            self._list_widget.setCurrentRow(0)

    def _on_search_changed(self, text: str) -> None:
        query = text.strip().lower()
        if not query:
            self._populate_list(self._all_actions)
            return

        filtered = [
            act for act in self._all_actions
            if query in act[0].lower() or (act[1] and query in act[1].lower())
        ]
        self._populate_list(filtered)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        row = self._list_widget.row(item)
        if 0 <= row < len(self._filtered_actions):
            _, _, _, callback = self._filtered_actions[row]
            self.accept()
            callback()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key_Down:
            curr = self._list_widget.currentRow()
            if curr < self._list_widget.count() - 1:
                self._list_widget.setCurrentRow(curr + 1)
        elif event.key() == Qt.Key_Up:
            curr = self._list_widget.currentRow()
            if curr > 0:
                self._list_widget.setCurrentRow(curr - 1)
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            curr_item = self._list_widget.currentItem()
            if curr_item:
                self._on_item_activated(curr_item)
        else:
            super().keyPressEvent(event)
