from __future__ import annotations

# =============================================================================
# CPC STUDIO — SEMANTIC CREATOR-TOOL DESIGN SYSTEM
# =============================================================================

CREATOR_DARK_STYLESHEET = """
/* Global Application Reset & Typography */
QMainWindow, QDialog, QWidget {
    background-color: #0e0e11;
    color: #f4f4f6;
    font-family: ".AppleSystemUIFont", "Helvetica Neue", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    font-weight: 400;
}

/* Header & Top Navigation Bar */
#topHeaderBar {
    background-color: #141418;
    border-bottom: 1px solid #23232a;
    padding: 6px 14px;
}

#brandTitle {
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.5px;
}

#privacyBadge {
    background-color: #1a271f;
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
    color: #8e8e93;
    padding: 8px 16px;
    margin-right: 6px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    border: 1px solid transparent;
}

QTabBar::tab:selected {
    background: #1f1f26;
    color: #ffffff;
    border: 1px solid #2e2e38;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background: #181820;
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
    border: 1px solid #22222a;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 12px 12px 12px;
    background-color: #141418;
    font-weight: 600;
    font-size: 12px;
    color: #d1d1d6;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #141418;
    color: #60a5fa;
    font-weight: 600;
    font-size: 12px;
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
    color: #8e8e93;
    font-size: 12px;
}

QLabel[heading="true"] {
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1a1a22;
    color: #ffffff;
    border: 1px solid #2c2c36;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #3b82f6;
    min-height: 22px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
    background-color: #1e1e28;
}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    background-color: #121216;
    color: #52525b;
    border-color: #1e1e24;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #2c2c36;
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
    background-color: #181820;
    border: 1px solid #2c2c36;
    border-radius: 6px;
    padding: 4px;
    color: #ffffff;
    selection-background-color: #2563eb;
    outline: none;
}

/* Buttons */
QPushButton {
    background-color: #1f1f28;
    color: #f4f4f6;
    border: 1px solid #2c2c36;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    min-height: 22px;
}

QPushButton:hover {
    background-color: #282834;
    border-color: #3f3f4e;
}

QPushButton:pressed {
    background-color: #16161d;
}

QPushButton:disabled {
    background-color: #121216;
    color: #52525b;
    border-color: #1c1c22;
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
    background: #272732;
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
    border: 1px solid #3f3f4e;
    border-radius: 4px;
    background-color: #1a1a22;
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
    background-color: #1a1a20;
}

QSplitter::handle:hover {
    background-color: #3b82f6;
}

/* Scrollbars */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #272732;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #3f3f4e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #272732;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #3f3f4e;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #121216;
    color: #8e8e93;
    border-top: 1px solid #1e1e24;
    font-size: 12px;
}

/* Text Editors & JSON Code Views */
QTextEdit, QPlainTextEdit {
    background-color: #121216;
    color: #f4f4f6;
    border: 1px solid #22222a;
    border-radius: 6px;
    padding: 8px;
    font-family: "SF Mono", "Menlo", "Monaco", "Consolas", monospace;
    font-size: 12px;
}

/* Progress Bars */
QProgressBar {
    background-color: #1a1a22;
    border: 1px solid #2c2c36;
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
"""
