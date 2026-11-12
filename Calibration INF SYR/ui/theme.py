"""Design system ของแอป: สี ฟอนต์ และ stylesheet กลาง (แก้หน้าตาทั้งแอปที่ไฟล์นี้ไฟล์เดียว)

widget ต่างๆ ไม่เขียน stylesheet เอง แต่ติดป้ายด้วย property แล้วให้ QSS ตรงนี้จัดการ เช่น
    frame.setProperty("card", True)        button.setProperty("variant", "primary")
"""
from __future__ import annotations

from pathlib import Path

import pyqtgraph as pg
from PySide6.QtCore import QLocale
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


class Color:
    BG = "#0E1217"            # พื้นหลังหน้าต่าง
    SURFACE = "#161B22"       # การ์ด/แผง
    SURFACE_ALT = "#1D242D"   # ช่องกรอก, แถวสลับ
    BORDER = "#2A323D"
    TEXT = "#E6EAF0"
    TEXT_MUTED = "#8793A3"
    TEXT_FAINT = "#5B6675"
    ACCENT = "#2DD4BF"
    ACCENT_HOVER = "#5EEAD4"
    ON_ACCENT = "#06231F"
    SUCCESS = "#34D399"
    WARNING = "#FBBF24"
    DANGER = "#F87171"
    INFO = "#60A5FA"

    # สีของเส้นกราฟ (ใช้ซ้ำกับตัวเลขบนการ์ดให้ตรงกัน)
    SERIES_A = "#22D3EE"
    SERIES_B = "#F472B6"
    SERIES_ALL = "#34D399"
    SERIES_MEAN = "#FACC15"
    SERIES_SLOPE = "#60A5FA"
    SERIES_WEIGHT = "#A78BFA"

    # สีประจำชนิดเครื่อง — ใช้ทุกที่ที่บอกชนิดเครื่อง เพื่อให้สังเกตได้ทันทีถ้าเลือกผิด
    INFUSION = "#38BDF8"      # ฟ้า
    SYRINGE = "#F472B6"       # ชมพูม่วง


PUMP_COLORS = {"infusion": Color.INFUSION, "syringe": Color.SYRINGE}


TONES = {
    "neutral": Color.TEXT, "muted": Color.TEXT_MUTED, "accent": Color.ACCENT,
    "success": Color.SUCCESS, "warning": Color.WARNING, "danger": Color.DANGER, "info": Color.INFO,
}

ASSETS = Path(__file__).resolve().parent / "assets"

FONT_FAMILY = "Segoe UI"
FONT_FALLBACKS = ["Leelawadee UI", "Tahoma"]    # รองรับภาษาไทย


def _stylesheet() -> str:
    c = Color
    chevron = (ASSETS / "chevron-down.svg").as_posix()
    return f"""
    QWidget {{ color: {c.TEXT}; font-size: 13px; }}
    QMainWindow, QWidget#page, QStackedWidget {{ background: {c.BG}; }}
    QToolTip {{ background: {c.SURFACE_ALT}; color: {c.TEXT}; border: 1px solid {c.BORDER}; padding: 4px 6px; }}

    /* ---------- โครง ---------- */
    QFrame#navRail {{ background: {c.SURFACE}; border: none; border-right: 1px solid {c.BORDER}; }}
    QFrame[card="true"] {{ background: {c.SURFACE}; border: 1px solid {c.BORDER}; border-radius: 10px; }}
    QFrame[divider="true"] {{ background: {c.BORDER}; border: none; max-height: 1px; min-height: 1px; }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}

    QFrame[modeCard="true"] {{ background: {c.SURFACE}; border: 1px solid {c.BORDER}; border-radius: 12px; }}
    QFrame[modeCard="true"]:hover {{ border-color: {c.ACCENT}; background: {c.SURFACE_ALT}; }}
    QFrame[banner="true"] {{ background: {c.SURFACE_ALT}; border: 1px solid {c.BORDER}; border-left: 3px solid {c.INFO}; border-radius: 8px; }}
    QFrame[banner="true"][tone="accent"]  {{ border-left-color: {c.ACCENT}; }}
    QFrame[banner="true"][tone="success"] {{ border-left-color: {c.SUCCESS}; }}
    QFrame[banner="true"][tone="warning"] {{ border-left-color: {c.WARNING}; }}
    QFrame[banner="true"][tone="danger"]  {{ border-left-color: {c.DANGER}; }}
    QDialog {{ background: {c.BG}; }}

    /* ---------- ตัวอักษร ---------- */
    QLabel {{ background: transparent; }}
    QLabel[role="logo"] {{ color: {c.ACCENT}; font-size: 20px; font-weight: 800; }}
    QLabel[role="pageTitle"] {{ font-size: 20px; font-weight: 600; }}
    QLabel[role="pageSubtitle"] {{ color: {c.TEXT_MUTED}; font-size: 13px; }}
    QLabel[role="sectionTitle"] {{ color: {c.TEXT_MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
    QLabel[role="fieldLabel"] {{ color: {c.TEXT_MUTED}; font-size: 12px; }}
    QLabel[role="hero"] {{ font-size: 26px; font-weight: 700; }}
    QLabel[role="heroUnit"] {{ color: {c.TEXT_MUTED}; font-size: 12px; padding-bottom: 4px; }}
    QLabel[role="metricName"] {{ color: {c.TEXT_MUTED}; font-size: 12px; }}
    QLabel[role="metricValue"] {{ font-size: 13px; font-weight: 600; }}
    QLabel[role="clock"] {{ font-size: 18px; font-weight: 600; }}
    QLabel[role="modeTitle"] {{ font-size: 17px; font-weight: 700; }}
    QLabel[role="bannerText"] {{ font-size: 13px; font-weight: 600; }}
    QLabel[role="weight"] {{ font-size: 22px; font-weight: 700; }}
    QLabel[role="stepIndex"] {{ color: {c.TEXT_MUTED}; background: {c.SURFACE_ALT}; border: 1px solid {c.BORDER};
                               border-radius: 10px; min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px; font-size: 11px; font-weight: 700; }}
    QLabel[role="stepIndex"][tone="accent"]  {{ color: {c.ACCENT};  border-color: {c.ACCENT}; }}
    QLabel[role="stepIndex"][tone="success"] {{ color: {c.SUCCESS}; border-color: {c.SUCCESS}; }}
    QLabel[role="stepIndex"][tone="danger"]  {{ color: {c.DANGER};  border-color: {c.DANGER}; }}
    QLabel[role="hint"] {{ color: {c.TEXT_MUTED}; font-size: 12px; }}
    QLabel[role="trackerStep"] {{ color: {c.ACCENT}; font-size: 26px; font-weight: 800; }}
    QLabel[role="trackerPhase"] {{ font-size: 13px; font-weight: 700; }}
    QLabel[role="trackerPercent"] {{ color: {c.TEXT_MUTED}; font-size: 13px; font-weight: 700; }}
    QLabel[role="heroCompact"] {{ font-size: 22px; font-weight: 700; }}
    QWidget#tracker {{ background: {c.SURFACE}; border: 1px solid {c.BORDER}; border-radius: 10px; }}

    /* ---------- สถานะ ---------- */
    QLabel[role="pill"] {{ border-radius: 11px; padding: 3px 12px; font-size: 11px; font-weight: 700;
                           background: {c.SURFACE_ALT}; color: {c.TEXT_MUTED}; border: 1px solid {c.BORDER}; }}
    QLabel[role="pill"][tone="accent"]  {{ color: {c.ACCENT};  border-color: {c.ACCENT}; }}
    QLabel[role="pill"][tone="success"] {{ color: {c.SUCCESS}; border-color: {c.SUCCESS}; }}
    QLabel[role="pill"][tone="warning"] {{ color: {c.WARNING}; border-color: {c.WARNING}; }}
    QLabel[role="pill"][tone="danger"]  {{ color: {c.DANGER};  border-color: {c.DANGER}; }}

    /* ---------- ปุ่ม ---------- */
    QPushButton {{ background: {c.SURFACE_ALT}; border: 1px solid {c.BORDER}; border-radius: 6px;
                   padding: 7px 14px; font-weight: 600; }}
    QPushButton:hover {{ border-color: {c.TEXT_FAINT}; background: #232B36; }}
    QPushButton:pressed {{ background: {c.SURFACE}; }}
    QPushButton:disabled {{ color: {c.TEXT_FAINT}; background: {c.SURFACE}; border-color: {c.BORDER}; }}
    QPushButton[variant="primary"] {{ background: {c.ACCENT}; color: {c.ON_ACCENT}; border: none; padding: 10px 14px; font-size: 14px; }}
    QPushButton[variant="primary"]:hover {{ background: {c.ACCENT_HOVER}; }}
    QPushButton[variant="primary"]:disabled {{ background: {c.SURFACE_ALT}; color: {c.TEXT_FAINT}; }}
    QPushButton[variant="danger"] {{ background: transparent; color: {c.DANGER}; border: 1px solid {c.DANGER}; padding: 10px 14px; font-size: 14px; }}
    QPushButton[variant="danger"]:hover {{ background: rgba(248, 113, 113, 0.14); }}
    QPushButton[variant="danger"]:disabled {{ color: {c.TEXT_FAINT}; border-color: {c.BORDER}; }}
    QPushButton[variant="chip"] {{ padding: 3px 10px; border-radius: 11px; font-size: 12px; font-weight: 500; color: {c.TEXT_MUTED}; }}
    QPushButton[variant="chip"]:hover {{ color: {c.ACCENT}; border-color: {c.ACCENT}; }}
    QPushButton[variant="ghost"] {{ background: transparent; border: none; color: {c.TEXT_MUTED}; padding: 2px 8px; font-size: 12px; }}
    QPushButton[variant="ghost"]:hover {{ color: {c.TEXT}; }}
    QPushButton[variant="segment"] {{ background: {c.SURFACE_ALT}; color: {c.TEXT_MUTED}; border: 1px solid {c.BORDER};
        border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: 600; text-align: left; }}
    QPushButton[variant="segment"]:hover {{ color: {c.TEXT}; border-color: {c.TEXT_FAINT}; }}
    QPushButton[variant="segment"]:checked {{ background: rgba(45, 212, 191, 0.14); color: {c.ACCENT}; border-color: {c.ACCENT}; }}
    QFrame[plotCell="true"] {{ background: {c.SURFACE}; border: 1px solid {c.BORDER}; border-radius: 10px; }}
    QLabel[role="plotTitle"] {{ font-size: 13px; font-weight: 700; }}
    QPushButton[variant="legendChip"] {{ background: transparent; border: 1px solid transparent; border-radius: 10px;
        padding: 1px 7px; font-size: 12px; font-weight: 600; }}
    QPushButton[variant="legendChip"]:hover {{ background: {c.SURFACE_ALT}; border-color: {c.BORDER}; }}
    QPushButton[variant="legendChip"]:disabled {{ background: transparent; }}
    QPushButton[variant="segmentSmall"] {{ background: {c.SURFACE_ALT}; color: {c.TEXT_MUTED}; border: 1px solid {c.BORDER};
        border-radius: 0; padding: 2px 10px; font-size: 11px; font-weight: 600; }}
    QPushButton[variant="segmentSmall"][position="first"] {{ border-top-left-radius: 6px; border-bottom-left-radius: 6px; }}
    QPushButton[variant="segmentSmall"][position="last"] {{ border-top-right-radius: 6px; border-bottom-right-radius: 6px; border-left: none; }}
    QPushButton[variant="segmentSmall"]:hover {{ color: {c.TEXT}; }}
    QPushButton[variant="segmentSmall"]:checked {{ background: rgba(45, 212, 191, 0.16); color: {c.ACCENT}; border-color: {c.ACCENT}; }}

    QToolButton[nav="true"] {{ background: transparent; border: none; border-radius: 8px; color: {c.TEXT_MUTED};
                               font-size: 11px; padding: 8px 2px 6px 2px; }}
    QToolButton[nav="true"]:hover {{ background: {c.SURFACE_ALT}; color: {c.TEXT}; }}
    QToolButton[nav="true"]:checked {{ background: rgba(45, 212, 191, 0.12); color: {c.ACCENT}; }}

    /* ---------- ช่องกรอก ---------- */
    QLineEdit, QComboBox, QAbstractSpinBox {{ background: {c.SURFACE_ALT}; border: 1px solid {c.BORDER};
        border-radius: 6px; padding: 5px 8px; min-height: 20px; selection-background-color: {c.ACCENT}; selection-color: {c.ON_ACCENT}; }}
    QLineEdit:focus, QComboBox:focus, QAbstractSpinBox:focus {{ border-color: {c.ACCENT}; }}
    QLineEdit:disabled, QComboBox:disabled, QAbstractSpinBox:disabled {{ color: {c.TEXT_FAINT}; background: {c.SURFACE}; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox::down-arrow {{ image: url("{chevron}"); width: 12px; height: 12px; }}
    QComboBox QAbstractItemView {{ background: {c.SURFACE_ALT}; border: 1px solid {c.BORDER}; outline: 0;
        selection-background-color: {c.ACCENT}; selection-color: {c.ON_ACCENT}; }}

    QPlainTextEdit {{ background: {c.SURFACE_ALT}; border: 1px solid {c.BORDER}; border-radius: 6px; padding: 5px 8px;
        selection-background-color: {c.ACCENT}; selection-color: {c.ON_ACCENT}; }}
    QPlainTextEdit:focus {{ border-color: {c.ACCENT}; }}
    QListView {{ background: {c.SURFACE_ALT}; border: 1px solid {c.BORDER}; border-radius: 6px; outline: 0; }}
    QListView::item {{ padding: 6px 10px; }}
    QListView::item:hover {{ background: #232B36; }}
    QListView::item:selected {{ background: rgba(45, 212, 191, 0.22); color: {c.TEXT}; }}
    QListView::indicator, QCheckBox::indicator {{ width: 15px; height: 15px; border: 1px solid {c.TEXT_FAINT};
        border-radius: 4px; background: {c.SURFACE}; }}
    QListView::indicator:checked, QCheckBox::indicator:checked {{ background: {c.ACCENT}; border-color: {c.ACCENT}; }}
    QPushButton[variant="hero"] {{ background: {c.ACCENT}; color: {c.ON_ACCENT}; border: none; border-radius: 8px;
        padding: 16px 14px; font-size: 15px; font-weight: 700; }}
    QPushButton[variant="hero"]:hover {{ background: {c.ACCENT_HOVER}; }}
    QTabBar {{ background: transparent; }}
    QTabBar::tab {{ background: transparent; color: {c.TEXT_MUTED}; border: none; border-bottom: 2px solid transparent;
        padding: 8px 18px; font-weight: 600; }}
    QTabBar::tab:hover {{ color: {c.TEXT}; }}
    QTabBar::tab:selected {{ color: {c.ACCENT}; border-bottom-color: {c.ACCENT}; }}

    /* ---------- ชนิดเครื่อง (Infusion / Syringe) ---------- */
    QFrame[pumpCard="true"] {{ background: {c.SURFACE_ALT}; border: 2px solid {c.BORDER}; border-radius: 12px; }}
    QFrame[pumpCard="true"]:hover {{ border-color: {c.TEXT_FAINT}; }}
    QFrame[pumpCard="true"][pump="infusion"][selected="true"] {{ background: rgba(56, 189, 248, 0.13); border-color: {c.INFUSION}; }}
    QFrame[pumpCard="true"][pump="syringe"][selected="true"]  {{ background: rgba(244, 114, 182, 0.13); border-color: {c.SYRINGE}; }}
    QFrame[pumpCard="true"]:focus {{ border-style: dashed; }}
    QLabel[role="pumpTitle"] {{ font-size: 15px; font-weight: 800; letter-spacing: 1px; color: {c.TEXT_MUTED}; }}
    QLabel[role="pumpTitle"][pump="infusion"][selected="true"] {{ color: {c.INFUSION}; }}
    QLabel[role="pumpTitle"][pump="syringe"][selected="true"]  {{ color: {c.SYRINGE}; }}
    QLabel[role="pumpBadge"] {{ border-radius: 11px; padding: 3px 12px; font-size: 11px; font-weight: 800; letter-spacing: 1px; }}
    QLabel[role="pumpBadge"][pump="infusion"] {{ color: {c.INFUSION}; background: rgba(56, 189, 248, 0.14); border: 1px solid {c.INFUSION}; }}
    QLabel[role="pumpBadge"][pump="syringe"]  {{ color: {c.SYRINGE}; background: rgba(244, 114, 182, 0.14); border: 1px solid {c.SYRINGE}; }}
    QFrame[pumpBar="true"] {{ border: none; border-radius: 2px; min-height: 4px; max-height: 4px; }}
    QFrame[pumpBar="true"][pump="infusion"] {{ background: {c.INFUSION}; }}
    QFrame[pumpBar="true"][pump="syringe"]  {{ background: {c.SYRINGE}; }}
    QFrame[optionCard="true"] {{ background: {c.SURFACE}; border: 1px solid {c.BORDER}; border-radius: 8px; }}
    QRadioButton {{ font-weight: 600; spacing: 8px; }}
    QRadioButton:disabled {{ color: {c.TEXT_FAINT}; }}
    QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 8px; border: 1px solid {c.TEXT_FAINT}; background: {c.SURFACE}; }}
    QRadioButton::indicator:checked {{ width: 8px; height: 8px; border-radius: 8px; border: 4px solid {c.ACCENT}; background: {c.ON_ACCENT}; }}

    /* ---------- อื่นๆ ---------- */
    QProgressBar {{ background: {c.SURFACE_ALT}; border: none; border-radius: 3px; max-height: 6px; min-height: 6px; }}
    QProgressBar::chunk {{ background: {c.ACCENT}; border-radius: 3px; }}

    QListWidget#logList {{ background: transparent; border: none; outline: 0; font-size: 12px; }}
    QListWidget#logList::item {{ padding: 3px 2px; border: none; }}

    QTableWidget {{ background: {c.SURFACE}; alternate-background-color: {c.SURFACE_ALT}; border: 1px solid {c.BORDER};
        border-radius: 10px; gridline-color: transparent; outline: 0; }}
    QTableWidget::item {{ padding: 6px 10px; border: none; }}
    QTableWidget::item:selected {{ background: rgba(45, 212, 191, 0.18); color: {c.TEXT}; }}
    QHeaderView::section {{ background: {c.SURFACE}; color: {c.TEXT_MUTED}; border: none; border-bottom: 1px solid {c.BORDER};
        padding: 8px 10px; font-size: 11px; font-weight: 700; }}
    QTableCornerButton::section {{ background: {c.SURFACE}; border: none; }}

    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c.BORDER}; border-radius: 3px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {c.TEXT_FAINT}; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {c.BORDER}; border-radius: 3px; min-width: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; border: none; width: 0; height: 0; }}
    """


def apply_theme(app: QApplication) -> None:
    # ตัวเลขใช้รูปแบบสากลเสมอ (0-9 และจุดทศนิยม) ไม่ขึ้นกับภาษาของ Windows
    QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    app.setStyle("Fusion")
    font = QFont(FONT_FAMILY, 10)
    font.setFamilies([FONT_FAMILY, *FONT_FALLBACKS])
    app.setFont(font)

    palette = QPalette()
    for role, color in {
        QPalette.ColorRole.Window: Color.BG, QPalette.ColorRole.Base: Color.SURFACE_ALT,
        QPalette.ColorRole.AlternateBase: Color.SURFACE, QPalette.ColorRole.Button: Color.SURFACE_ALT,
        QPalette.ColorRole.WindowText: Color.TEXT, QPalette.ColorRole.Text: Color.TEXT,
        QPalette.ColorRole.ButtonText: Color.TEXT, QPalette.ColorRole.PlaceholderText: Color.TEXT_FAINT,
        QPalette.ColorRole.Highlight: Color.ACCENT, QPalette.ColorRole.HighlightedText: Color.ON_ACCENT,
        QPalette.ColorRole.ToolTipBase: Color.SURFACE_ALT, QPalette.ColorRole.ToolTipText: Color.TEXT,
    }.items():
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(_stylesheet())

    pg.setConfigOptions(background=Color.SURFACE, foreground=Color.TEXT_MUTED, antialias=True)


def set_property(widget, name: str, value) -> None:
    """ตั้ง property ที่ QSS ใช้ แล้วให้ stylesheet คำนวณใหม่ทันที"""
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def set_tone(widget, tone: str) -> None:
    """เปลี่ยนโทนสีของ widget ที่ QSS รองรับ property 'tone' (เช่น pill)"""
    widget.setProperty("tone", tone)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
