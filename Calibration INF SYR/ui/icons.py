"""ไอคอนจากฟอนต์ไอคอนของ Windows (Segoe Fluent Icons / MDL2) — ไม่ต้องมีไฟล์รูป

ถ้าเครื่องไม่มีฟอนต์ จะคืน QIcon ว่าง (ปุ่มยังใช้งานได้ด้วยข้อความ)
"""
from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap

from ui.theme import Color


class Glyph:
    DASHBOARD = ""
    HISTORY = ""
    SETTINGS = ""
    PLAY = ""
    STOP = ""
    REFRESH = ""
    FOLDER = ""
    SAVE = ""


_family: str | None = None


def _icon_family() -> str:
    global _family
    if _family is None:
        available = set(QFontDatabase.families())
        _family = next((f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in available), "")
    return _family


def _pixmap(glyph: str, color: str, size: int) -> QPixmap:
    scale = 2   # วาด 2 เท่าเพื่อความคมบนจอ HiDPI
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    font = QFont(_icon_family())
    font.setPixelSize(int(size * scale * 0.9))
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(QRect(0, 0, size * scale, size * scale), Qt.AlignmentFlag.AlignCenter, glyph)
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    return pixmap


def glyph_icon(glyph: str, color: str = Color.TEXT_MUTED, active_color: str | None = None,
               disabled_color: str | None = None, size: int = 20) -> QIcon:
    icon = QIcon()
    if not _icon_family():
        return icon
    icon.addPixmap(_pixmap(glyph, color, size), QIcon.Mode.Normal, QIcon.State.Off)
    if active_color:
        icon.addPixmap(_pixmap(glyph, active_color, size), QIcon.Mode.Normal, QIcon.State.On)
    if disabled_color:
        icon.addPixmap(_pixmap(glyph, disabled_color, size), QIcon.Mode.Disabled, QIcon.State.Off)
    return icon
