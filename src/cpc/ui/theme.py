from __future__ import annotations

# =============================================================================
# CPC STUDIO — SEMANTIC CREATOR-TOOL DESIGN SYSTEM
# =============================================================================

CREATOR_DARK_STYLESHEET = """
/* Global Application Reset & Typography */
QMainWindow, QDialog, QWidget {
    background-color: #0d0d12;
    color: #f4f4f6;
    font-family: ".AppleSystemUIFont", "SF Pro Text", "Helvetica Neue", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    font-weight: 400;
}

/* Header & Top Navigation Bar */
#topHeaderBar {
    background-color: #121218;
    border-bottom: 1px solid #1f1f2a;
    padding: 6px 16px;
}

#brandTitle {
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.5px;
}

#privacyBadge {
    background-color: #132219;
    color: #10b981;
    border: 1px solid #065f46;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
}

/* Modern Tab Navigation */
QTabBar {
    background-color: transparent;
    border: none;
    qproperty-drawBase: 0;
}

QTabBar::tab {
    background: transparent;
    color: #9ca3af;
    padding: 8px 18px;
    margin-right: 4px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    border: 1px solid transparent;
}

QTabBar::tab:selected {
    background: #1b1b24;
    color: #ffffff;
    border: 1px solid #282838;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background: #15151e;
    color: #d1d1d6;
}

QTabWidget::pane {
    border: none;
    background: transparent;
    margin: 0;
    padding: 0;
}

/* Container Cards & Panels */
QGroupBox {
    border: 1px solid #1f1f2c;
    border-radius: 8px;
    margin-top: 14px;
    padding: 16px 14px 14px 14px;
    background-color: #13131b;
    font-weight: 600;
    font-size: 13px;
    color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #13131b;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
}

/* Scroll Areas */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* Form Controls */
QLabel {
    color: #e4e4e7;
}

QLabel[secondary="true"] {
    color: #9ca3af;
    font-size: 12px;
}

QLabel[heading="true"] {
    color: #ffffff;
    font-size: 15px;
    font-weight: 600;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #171722;
    color: #ffffff;
    border: 1px solid #282838;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #3b82f6;
    min-height: 24px;
    font-size: 13px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
    background-color: #1b1b28;
}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    background-color: #101015;
    color: #52525b;
    border-color: #1a1a22;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #282838;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #a1a1aa;
    width: 0;
    height: 0;
    margin-right: 2px;
}

QComboBox QAbstractItemView {
    background-color: #171722;
    border: 1px solid #282838;
    border-radius: 6px;
    padding: 4px;
    color: #ffffff;
    selection-background-color: #2563eb;
    outline: none;
}

/* Buttons */
QPushButton {
    background-color: #1b1b26;
    color: #f4f4f6;
    border: 1px solid #282838;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    min-height: 24px;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #242434;
    border-color: #3b3b4e;
}

QPushButton:pressed {
    background-color: #151520;
}

QPushButton:disabled {
    background-color: #101016;
    color: #52525b;
    border-color: #181822;
}

QPushButton[primary="true"] {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
    font-weight: 600;
}

QPushButton[primary="true"]:hover {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}

QPushButton[primary="true"]:pressed {
    background-color: #1e40af;
}

QPushButton[primary="true"]:disabled {
    background-color: #172554;
    color: #60a5fa;
    border-color: #1e3a8a;
    opacity: 0.6;
}

QPushButton[danger="true"] {
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #ef4444;
    font-weight: 600;
}

QPushButton[danger="true"]:hover {
    background-color: #b91c1c;
    border-color: #f87171;
}

QPushButton[danger="true"]:pressed {
    background-color: #991b1b;
}

QPushButton[danger="true"]:disabled {
    background-color: #450a0a;
    color: #fca5a5;
    border-color: #7f1d1d;
    opacity: 0.6;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 4px;
    background: #252534;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #93c5fd;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #bfdbfe;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    color: #e4e4e7;
    spacing: 8px;
    font-weight: 400;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3a3a4c;
    border-radius: 4px;
    background-color: #171722;
}

QRadioButton::indicator {
    border-radius: 8px;
}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #2563eb;
    border-color: #3b82f6;
}

/* Splitters */
QSplitter::handle {
    background-color: #181824;
}

QSplitter::handle:hover {
    background-color: #3b82f6;
}

/* Scrollbars */
QScrollBar:vertical {
    background: transparent;
    width: 7px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #262638;
    min-height: 24px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #3a3a50;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 7px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #262638;
    min-width: 24px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal:hover {
    background: #3a3a50;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #101015;
    color: #8e8e93;
    border-top: 1px solid #1a1a24;
    font-size: 12px;
}

/* Text Editors & JSON Code Views */
QTextEdit, QPlainTextEdit {
    background-color: #101016;
    color: #f4f4f6;
    border: 1px solid #1f1f2c;
    border-radius: 6px;
    padding: 8px;
    font-family: "SF Mono", "Menlo", "Monaco", "Consolas", monospace;
    font-size: 12px;
}

/* Progress Bars */
QProgressBar {
    background-color: #171722;
    border: 1px solid #282838;
    border-radius: 4px;
    text-align: center;
    color: #f4f4f6;
    font-weight: 600;
    font-size: 11px;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 3px;
}

/* Session Strip & Stage Components */
#session_strip {
    background-color: #12121c;
    border: 1px solid #1f1f2e;
    border-radius: 8px;
    padding: 4px 8px;
}

#session_strip QPushButton {
    background-color: #1a1a27;
    color: #e2e8f0;
    border: 1px solid #2d2d3e;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
}

#session_strip QPushButton:hover {
    background-color: #262638;
    border-color: #3b82f6;
    color: #ffffff;
}

#session_strip QPushButton:pressed {
    background-color: #151522;
}

#transport_bar {
    background-color: #12121a;
    border: 1px solid #1e1e2c;
    border-radius: 8px;
    padding: 8px 12px;
}

#inspector_drawer {
    background-color: #12121a;
    border-left: 1px solid #1f1f2e;
}
"""
