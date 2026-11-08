"""Shared Qt stylesheet for TaskNudge."""

GLOBAL_STYLE = """
QWidget {
    color: #e9f2f4;
    font-family: "Segoe UI", "Inter", "Noto Sans", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog {
    background-color: #0b141c;
}
QFrame#panel {
    background-color: #121f29;
    border: 1px solid #213541;
    border-radius: 14px;
}
QFrame#statsBar {
    background-color: #101b24;
    border: 1px solid #1e303b;
    border-radius: 12px;
}
QFrame#popupCard {
    background-color: #101e28;
    border: 1px solid #2b4554;
    border-radius: 20px;
}
QFrame#divider {
    background-color: #223541;
    max-height: 1px;
    border: none;
}
QLabel {
    background: transparent;
}
QLabel#appTitle {
    font-size: 24px;
    font-weight: 700;
    color: #f5fbfc;
}
QLabel#dialogTitle {
    font-size: 20px;
    font-weight: 700;
    color: #f5fbfc;
}
QLabel#eyebrow {
    color: #6fdfc3;
    font-size: 10px;
    font-weight: 700;
}
QLabel#muted, QLabel#hint {
    color: #8da7b5;
}
QLabel#hint {
    font-size: 11px;
}
QLabel#taskHeadline {
    font-size: 19px;
    font-weight: 650;
    color: #f6fbfc;
}
QLabel#summaryHeadline {
    font-size: 21px;
    font-weight: 650;
    color: #f6fbfc;
}
QLabel#chip {
    background-color: #1a2d39;
    color: #b9d1db;
    border: 1px solid #29414f;
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#statValue {
    font-size: 26px;
    font-weight: 700;
    color: #f4fcfd;
}
QLabel#statCaption {
    color: #8fa8b5;
    font-size: 11px;
}
QLabel#statusPaused {
    color: #f3bd72;
    font-size: 11px;
    font-weight: 600;
}
QLabel#emptyTitle {
    font-size: 18px;
    font-weight: 650;
    color: #dbe9ed;
}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit {
    background-color: #0e1922;
    color: #e9f3f5;
    border: 1px solid #2a404d;
    border-radius: 8px;
    padding: 7px 9px;
    selection-background-color: #2b8d7a;
    selection-color: #ffffff;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus,
QDateEdit:focus, QTimeEdit:focus {
    border: 1px solid #6fdfc3;
}
QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled,
QSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled {
    color: #607582;
    background-color: #0c151c;
    border-color: #1e2d36;
}
QComboBox::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down,
QSpinBox::up-button, QSpinBox::down-button {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    background-color: #14222c;
    border: 1px solid #2a414e;
    selection-background-color: #254454;
    selection-color: #ffffff;
    padding: 4px;
}
QPushButton {
    background-color: #1a2a35;
    color: #deebee;
    border: 1px solid #2a414e;
    border-radius: 8px;
    padding: 8px 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #223744;
    border-color: #3b5866;
}
QPushButton:pressed {
    background-color: #172732;
}
QPushButton:disabled {
    color: #5b707c;
    background-color: #111d25;
    border-color: #1d2d36;
}
QPushButton[variant="primary"] {
    background-color: #71e2c3;
    color: #07231c;
    border: 1px solid #71e2c3;
}
QPushButton[variant="primary"]:hover {
    background-color: #8bf0d5;
    border-color: #8bf0d5;
}
QPushButton[variant="primary"]:pressed {
    background-color: #5bcbac;
}
QPushButton[variant="ghost"] {
    background-color: transparent;
    border: 1px solid #2b414e;
    color: #b7ccd5;
}
QPushButton[variant="ghost"]:hover {
    background-color: #172630;
    color: #eef7f8;
}
QPushButton[variant="danger"] {
    background-color: transparent;
    border: 1px solid #5b3434;
    color: #ff9c8e;
}
QPushButton[variant="danger"]:hover {
    background-color: #3a2020;
}
QPushButton[variant="link"] {
    background: transparent;
    border: none;
    color: #7fe6cc;
    padding: 2px 0;
    font-weight: 600;
}
QPushButton[variant="link"]:hover {
    color: #a5f3df;
}
QPushButton#closeButton {
    background: transparent;
    border: none;
    color: #82a0ae;
    font-size: 19px;
    font-weight: 500;
    padding: 0;
}
QPushButton#closeButton:hover {
    color: #ffffff;
    background-color: #20343f;
    border-radius: 12px;
}
QPushButton::menu-indicator {
    image: none;
    width: 0px;
}
QToolButton {
    background-color: #1a2a35;
    color: #deebee;
    border: 1px solid #2a414e;
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 600;
}
QToolButton:hover {
    background-color: #223744;
}
QMenu {
    background-color: #14222c;
    border: 1px solid #2b4350;
    border-radius: 8px;
    padding: 5px;
}
QMenu::item {
    padding: 7px 26px 7px 12px;
    border-radius: 5px;
}
QMenu::item:selected {
    background-color: #274454;
}
QMenu::separator {
    height: 1px;
    background-color: #253b47;
    margin: 5px 8px;
}
QCheckBox {
    spacing: 8px;
    color: #dce9ed;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3a5260;
    border-radius: 4px;
    background-color: #0d1820;
}
QCheckBox::indicator:hover {
    border-color: #6fdfc3;
}
QCheckBox::indicator:checked {
    background-color: #71e2c3;
    border-color: #71e2c3;
}
QCheckBox::indicator:disabled {
    border-color: #24353f;
    background-color: #101b23;
}
QTreeWidget {
    background-color: #0f1a23;
    alternate-background-color: #111f29;
    border: 1px solid #223641;
    border-radius: 12px;
    padding: 4px;
    outline: none;
}
QTreeWidget::item {
    height: 42px;
    border-bottom: 1px solid #182933;
    padding-left: 4px;
}
QTreeWidget::item:hover {
    background-color: #142630;
}
QTreeWidget::item:selected {
    background-color: #1c3542;
    color: #ffffff;
}
QTreeWidget::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #3d5865;
    border-radius: 4px;
    background-color: #0d1820;
}
QTreeWidget::indicator:checked {
    background-color: #71e2c3;
    border-color: #71e2c3;
}
QHeaderView::section {
    background-color: #0f1a23;
    color: #7893a1;
    border: none;
    border-bottom: 1px solid #223641;
    padding: 8px 6px;
    font-size: 10px;
    font-weight: 700;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 3px;
}
QScrollBar::handle:vertical {
    background: #2a414d;
    min-height: 28px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #385565;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #2a414d;
    min-width: 28px;
    border-radius: 4px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QProgressBar {
    background-color: #20333e;
    border: none;
    border-radius: 2px;
    height: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #6fdfc3;
    border-radius: 2px;
}
QGroupBox {
    border: 1px solid #223641;
    border-radius: 12px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #a9c2cc;
}
QToolTip {
    background-color: #172833;
    color: #e9f3f5;
    border: 1px solid #365161;
    padding: 5px;
}
QMessageBox {
    background-color: #0b141c;
}
QDialogButtonBox QPushButton {
    min-width: 86px;
}
"""
