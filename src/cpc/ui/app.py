from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from cpc.ui.main_window import MainWindow
from cpc.ui.theme import CREATOR_DARK_STYLESHEET


def main() -> int:
    """Launch the Character Performance Capture desktop application."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("Character Performance Capture")
    app.setOrganizationName("WestKitty")
    app.setStyleSheet(CREATOR_DARK_STYLESHEET)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
