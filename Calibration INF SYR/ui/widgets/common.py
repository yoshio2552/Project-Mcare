"""ชิ้นส่วน UI พื้นฐานที่ใช้ซ้ำทุกหน้า (การ์ด, ป้ายข้อความ, pill, ตัวจัดรูปตัวเลข)"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from ui.theme import set_tone


def label(text: str = "", role: str | None = None) -> QLabel:
    widget = QLabel(text)
    if role:
        widget.setProperty("role", role)
    return widget


def number_box(minimum: float, maximum: float, value: float, decimals: int = 1, suffix: str = "") -> QDoubleSpinBox:
    """ช่องกรอกตัวเลขทศนิยม (ไม่มีปุ่มขึ้นลง ชิดขวา)"""
    box = QDoubleSpinBox()
    box.setRange(minimum, maximum)
    box.setDecimals(decimals)
    box.setValue(value)
    box.setSuffix(suffix)
    box.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return box


def int_box(minimum: int, maximum: int, value: int, suffix: str = "", step: int = 1) -> QSpinBox:
    box = QSpinBox()
    box.setRange(minimum, maximum)
    box.setSingleStep(step)
    box.setValue(value)
    box.setSuffix(suffix)
    box.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return box


def divider() -> QFrame:
    line = QFrame()
    line.setProperty("divider", True)
    return line


def fmt(value: float | None, decimals: int = 2, unit: str = "", signed: bool = False, prefix: str = "") -> str:
    """จัดรูปตัวเลขให้เหมือนกันทั้งแอป — ค่าว่าง/NaN แสดงเป็น —"""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    sign = "+" if signed else ""
    return f"{prefix}{value:{sign}.{decimals}f}{unit}"


def fmt_clock(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


class Card(QFrame):
    """กรอบการ์ดมาตรฐาน พร้อมหัวข้อ (ถ้ามี) — ใส่เนื้อหาผ่าน card.body"""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", True)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(14, 12, 14, 14)
        self.body.setSpacing(10)
        self.header = QHBoxLayout()
        self.header.setSpacing(8)
        if title:
            self.header.addWidget(label(title.upper(), "sectionTitle"))
            self.header.addStretch()
            self.body.addLayout(self.header)


class StatusPill(QLabel):
    def __init__(self, text: str = "", tone: str = "neutral"):
        super().__init__(text)
        self.setProperty("role", "pill")
        self.set(text, tone)

    def set(self, text: str, tone: str = "neutral") -> None:
        self.setText(text)
        set_tone(self, tone)


class PageHeader(QWidget):
    """หัวหน้าเพจ: ชื่อ + คำอธิบาย ทางซ้าย และพื้นที่ใส่ widget ทางขวา (self.actions)"""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        text = QVBoxLayout()
        text.setSpacing(0)
        text.addWidget(label(title, "pageTitle"))
        self.subtitle = label(subtitle, "pageSubtitle")
        text.addWidget(self.subtitle)
        row.addLayout(text)
        row.addStretch()
        self.actions = QHBoxLayout()
        self.actions.setSpacing(10)
        row.addLayout(self.actions)
