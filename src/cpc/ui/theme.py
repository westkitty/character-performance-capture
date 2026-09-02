from __future__ import annotations

# Professional Dark Neutral Creator-Tool Stylesheet
CREATOR_DARK_STYLESHEET = """
QMainWindow, QDialog, QWidget {
    background-color: #121214;
    color: #f4f4f5;
    font-family: ".AppleSystemUIFont", "Helvetica Neue", "Segoe UI", Arial;
    font-size: 13px;
    font-weight: 400;
}

/* Tab Bar / Workspace Navigation */
QTabBar::tab {
    background: #18181b;
    color: #a1a1aa;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #27272a;
    border-bottom: none;
    font-weight: 500;
}

QTabBar::tab:selected {
    background: #27272a;
    color: #fafafa;
    border-color: #3f3f46;
}

QTabBar::tab:hover:!selected {
    background: #202024;
    color: #e4e4e7;
}

QTabWidget::pane {
    border: 1px solid #27272a;
    background: #18181b;
    border-radius: 6px;
    padding: 12px;
}

/* Group Boxes / Panels */
QGroupBox {
    border: 1px solid #27272a;
    border-radius: 6px;
    margin-top: 18px;
    padding: 16px 12px 12px 12px;
    background-color: #18181b;
    font-weight: 600;
    color: #e4e4e7;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #18181b;
    color: #38bdf8;
}

/* Form Controls */
QLabel {
    color: #e4e4e7;
}

QLabel[secondary="true"] {
    color: #a1a1aa;
    font-size: 12px;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #202024;
    color: #fafafa;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    padding: 6px 8px;
    selection-background-color: #2563eb;
    min-height: 20px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #38bdf8;
    background-color: #27272a;
}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    background-color: #141416;
    color: #71717a;
    border-color: #27272a;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #3f3f46;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}

QComboBox QAbstractItemView {
    background-color: #202024;
    color: #fafafa;
    border: 1px solid #3f3f46;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    padding: 4px;
}

/* Buttons */
QPushButton {
    background-color: #27272a;
    color: #fafafa;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    padding: 7px 14px;
    font-weight: 500;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #3f3f46;
    border-color: #52525b;
}

QPushButton:pressed {
    background-color: #18181b;
}

QPushButton:disabled {
    background-color: #18181b;
    color: #52525b;
    border-color: #27272a;
}

QPushButton:focus {
    border: 1px solid #38bdf8;
}

/* Primary Action Buttons */
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
    background-color: #1e3a8a;
    color: #93c5fd;
    border-color: #1e3a8a;
}

/* Danger / Stop Buttons */
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

/* Checkboxes & Radio buttons */
QCheckBox, QRadioButton {
    color: #e4e4e7;
    spacing: 8px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3f3f46;
    border-radius: 3px;
    background: #202024;
}

QRadioButton::indicator {
    border-radius: 8px;
}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #2563eb;
    border-color: #3b82f6;
}

QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
    border-color: #27272a;
    background: #18181b;
}

/* Scroll Areas and Bars */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background: #18181b;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #3f3f46;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #52525b;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* Splitters */
QSplitter::handle {
    background-color: #27272a;
}

QSplitter::handle:hover {
    background-color: #38bdf8;
}

/* Text Views and Code Blocks */
QTextEdit, QPlainTextEdit {
    background-color: #121214;
    color: #f4f4f5;
    border: 1px solid #27272a;
    border-radius: 4px;
    font-family: "SF Mono", Menlo, Monaco, Consolas, monospace;
    font-size: 12px;
    padding: 8px;
}

/* Status Bar */
QStatusBar {
    background: #121214;
    color: #a1a1aa;
    border-top: 1px solid #27272a;
}

QStatusBar::item {
    border: none;
}

/* Tooltips */
QToolTip {
    background-color: #27272a;
    color: #fafafa;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 12px;
}

/* Sliders */
QSlider::groove:horizontal {
    border: 1px solid #27272a;
    height: 6px;
    background: #202024;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #2563eb;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #fafafa;
    border: 1px solid #3f3f46;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #38bdf8;
}
"""
