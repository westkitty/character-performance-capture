from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from cpc.ui.widgets.command_palette import CommandPaletteDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_command_palette_filtering_and_action(qapp):
    executed = []

    actions = [
        ("Start Session", "Begin capture", "Space", lambda: executed.append("start")),
        ("Stop Session", "Stop capture", "Space", lambda: executed.append("stop")),
        ("Toggle Performance Mode", "Full preview view", "Cmd+P", lambda: executed.append("perf")),
        ("Open Video Source...", "Open file", "Cmd+O", lambda: executed.append("video")),
    ]

    dialog = CommandPaletteDialog(actions)
    dialog.resize(560, 320)
    dialog.show()

    # Initial state
    assert dialog._list_widget.count() == 4

    # Search filter "perf"
    dialog._search_edit.setText("perf")
    assert dialog._list_widget.count() == 1
    assert "Performance" in dialog._list_widget.item(0).text()

    # Trigger action
    dialog._on_item_activated(dialog._list_widget.item(0))
    assert executed == ["perf"]

    dialog.close()


def test_command_palette_key_navigation(qapp):
    actions = [
        ("Action A", "", "", lambda: None),
        ("Action B", "", "", lambda: None),
        ("Action C", "", "", lambda: None),
    ]

    dialog = CommandPaletteDialog(actions)
    dialog.show()

    assert dialog._list_widget.currentRow() == 0

    # Down arrow
    event_down = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Down, Qt.NoModifier)
    dialog.keyPressEvent(event_down)
    assert dialog._list_widget.currentRow() == 1

    # Up arrow
    event_up = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Up, Qt.NoModifier)
    dialog.keyPressEvent(event_up)
    assert dialog._list_widget.currentRow() == 0

    dialog.close()


def test_main_window_copy_cli_command(qapp):
    from cpc.ui.main_window import MainWindow

    win = MainWindow()
    win.show()

    # Verify _copy_cli_command executes cleanly and sets clipboard
    win._copy_cli_command()
    clipboard_text = QApplication.clipboard().text()
    assert clipboard_text.startswith("cpc")
    assert "CLI command copied to clipboard" in win.status_bar.currentMessage()

    win.close()
