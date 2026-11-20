"""ชิ้นส่วน UI พื้นฐานที่ใช้ซ้ำทุกหน้า (การ์ด, ป้ายข้อความ, pill, ตัวจัดรูปตัวเลข)"""
from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from ui.theme import set_tone


def label(text: str = "", role: str | None = None) -> QLabel:
    widget = QLabel(text)
    if role:
        widget.setProperty("role", role)
    return widget


class WrapLabel(QLabel):
    """ป้ายข้อความหลายบรรทัดที่ได้ความสูงพอเสมอ

    QLabel ที่ตัดบรรทัด (wordWrap) บอกความสูงจากความกว้างประมาณ ไม่ใช่ความกว้างจริง — ในคอลัมน์กว้างตายตัว
    (แผงแผนทดสอบ 310 px) ข้อความที่ตัดเป็นหลายบรรทัดจึงได้ความสูงไม่พอ บรรทัดทับ/ขาด (ผู้ใช้ 2026-11-19)
    แก้: ทุกครั้งที่ขนาด/ข้อความเปลี่ยน ตั้งความสูงขั้นต่ำ = ความสูงที่ต้องใช้จริงที่ความกว้างปัจจุบัน
    """

    def __init__(self, text: str = "", role: str | None = None):
        super().__init__(text)
        self.setWordWrap(True)
        if role:
            self.setProperty("role", role)

    def setText(self, text: str) -> None:
        super().setText(text)
        self._fit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # ฟอนต์จาก stylesheet (role) มาหลังสร้าง — ความสูงที่คำนวณก่อนหน้าใช้ฟอนต์ผิด บรรทัดจึงทับกันได้
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange, QEvent.Type.PolishRequest):
            self._fit()

    def _fit(self) -> None:
        self.ensurePolished()
        width = self.width() if self.width() > 20 else self.sizeHint().width()
        needed = self.heightForWidth(width)
        if needed > 0 and needed != self.minimumHeight():
            self.setMinimumHeight(needed)


class ElidedLabel(QLabel):
    """ป้ายบรรทัดเดียวที่ไม่ล้น/ไม่ทับ: ข้อความยาวกว่าที่ว่างจะตัดท้ายเป็น "…" และมี tooltip ข้อความเต็ม
    (ใช้แทนป้ายตัดบรรทัดในที่แคบ เช่น แผนทดสอบหลาย rate — ผู้ใช้ 2026-11-20 "อักษรซ้อนกัน")"""

    def __init__(self, text: str = "", role: str | None = None):
        super().__init__()
        self._full = ""
        if role:
            self.setProperty("role", role)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setText(text)

    def setText(self, text: str) -> None:
        self._full = text or ""
        self.setToolTip(self._full if self._full else "")
        self._elide()

    def text_full(self) -> str:
        return self._full

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        return QSize(10, hint.height())

    def sizeHint(self):
        metrics = self.fontMetrics()
        return QSize(metrics.horizontalAdvance(self._full) + 4, metrics.height() + 2)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._elide()

    def _elide(self) -> None:
        width = max(10, self.width())
        shown = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, width)
        super().setText(shown)


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


def fmt_duration(seconds: float | None) -> str:
    """ระยะเวลาของผล (ไม่ใช่นาฬิกาเดิน) แบบมีหน่วย "10 min 54.28 s" — เหมือนในใบรายงาน (ผู้ใช้ 2026-11-20)"""
    from core.models import format_duration
    return format_duration(seconds)


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
