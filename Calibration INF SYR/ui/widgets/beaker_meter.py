"""BeakerMeter: ภาพบีกเกอร์ + ระดับน้ำ (วาดเอง) — ใช้ในการ์ดตราชั่ง, popup เตือน และหน้าต่างตั้งบีกเกอร์

ระดับน้ำสีตามสถานะ: ปกติ = ฟ้าน้ำ · ใกล้เต็ม = เหลืองอำพัน · จะล้น = แดง · ขีดประบนผนัง = เกณฑ์เตือน/เกณฑ์ล้น
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ui.theme import Color


class BeakerMeter(QWidget):
    def __init__(self, size: QSize = QSize(44, 56), parent=None):
        super().__init__(parent)
        self._fill: float | None = None     # % (None = ไม่รู้)
        self._warn, self._alarm = 85.0, 95.0
        self._pulse = 0.0
        self.setFixedSize(size)

    def set_level(self, fill_pct: float | None, warn_pct: float = 85.0, alarm_pct: float = 95.0) -> None:
        self._fill, self._warn, self._alarm = fill_pct, warn_pct, alarm_pct
        self.update()

    def set_pulse(self, value: float) -> None:
        """0–1 (popup เตือนใช้ทำให้ผิวน้ำกะพริบนุ่มๆ)"""
        self._pulse = value
        self.update()

    def _color(self) -> QColor:
        fill = self._fill or 0.0
        if fill >= self._alarm:
            return QColor(Color.DANGER)
        if fill >= self._warn:
            return QColor(Color.WARNING)
        return QColor("#38BDF8")

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        lip = max(3.0, w * 0.10)
        body = QRectF(lip, h * 0.08, w - 2 * lip, h * 0.88)
        # น้ำ
        if self._fill is not None:
            level = max(0.0, min(1.0, self._fill / 100.0))
            top = body.bottom() - body.height() * level
            water = QColor(self._color())
            water.setAlphaF(0.55 + 0.35 * self._pulse)
            path = QPainterPath()
            path.addRoundedRect(QRectF(body.left() + 1.5, top, body.width() - 3, body.bottom() - top - 1.5), 3, 3)
            p.fillPath(path, water)
        # ขีดเกณฑ์
        for pct, color in ((self._warn, Color.WARNING), (self._alarm, Color.DANGER)):
            y = body.bottom() - body.height() * pct / 100.0
            pen = QPen(QColor(color), 1.2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawLine(QPointF(body.left() + 2, y), QPointF(body.right() - 2, y))
        # ตัวบีกเกอร์ (ผนัง + ก้น + ปากเท)
        pen = QPen(QColor(Color.TEXT_MUTED), max(1.6, w / 28.0))
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        outline = QPainterPath()
        outline.moveTo(body.left() - lip * 0.6, body.top())
        outline.lineTo(body.left(), body.top() + lip * 0.5)
        outline.lineTo(body.left(), body.bottom() - 3)
        outline.quadTo(body.left(), body.bottom(), body.left() + 3, body.bottom())
        outline.lineTo(body.right() - 3, body.bottom())
        outline.quadTo(body.right(), body.bottom(), body.right(), body.bottom() - 3)
        outline.lineTo(body.right(), body.top())
        p.drawPath(outline)
        # ขีดสเกล
        pen.setWidthF(1.0)
        p.setPen(pen)
        for i in range(1, 5):
            y = body.bottom() - body.height() * i / 5.0
            p.drawLine(QPointF(body.right() - w * 0.18, y), QPointF(body.right(), y))
        p.end()
