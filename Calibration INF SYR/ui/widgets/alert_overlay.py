"""AlertOverlay: popup เตือนขนาดใหญ่แบบทันสมัย (ระบบความปลอดภัยบีกเกอร์ — ผู้ใช้ 2026-11-20)

    ┌──────────────────────────────────────────────┐   ขอบสีตามความรุนแรง (แดง = จะล้น กะพริบนุ่มๆ,
    │  [บีกเกอร์]  บีกเกอร์ใกล้จะล้น                 │   อำพัน = ใกล้เต็ม, ฟ้า = แจ้ง)
    │             น้ำ 143 จาก 150 ml (95 %) …       │   ลอยอยู่กลางหน้าต่างหลัก ไม่บล็อกการทดสอบ
    │  ████████████████████████████░░  95 %        │   (การทดสอบเดินต่อได้) จนกว่าจะกดปุ่ม
    │                  [ ตั้งบีกเกอร์… ] [ ปิดเสียง ] │
    └──────────────────────────────────────────────┘
รับ Alert จาก services/beaker_guard.py (None = ซ่อน) · ปุ่มรับทราบ -> acknowledged(kind) · ปุ่มตั้งบีกเกอร์ -> setup_clicked
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from config.i18n import tr
from ui.theme import Color
from ui.widgets.beaker_meter import BeakerMeter

SEVERITY_COLOR = {"danger": "DANGER", "warning": "WARNING", "info": "INFO"}


class AlertOverlay(QWidget):
    acknowledged = Signal(str)
    setup_clicked = Signal()

    def __init__(self, host: QWidget):
        super().__init__(host, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self._host = host
        self._alert = None
        self._phase = 0.0
        self.setFixedWidth(620)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)       # พื้นที่ของเงา
        self._card = QWidget()
        self._card.setObjectName("alertCard")
        root.addWidget(self._card)

        body = QVBoxLayout(self._card)
        body.setContentsMargins(26, 22, 26, 20)
        body.setSpacing(14)
        top = QHBoxLayout()
        top.setSpacing(18)
        self.meter = BeakerMeter(QSize(70, 88))
        top.addWidget(self.meter, alignment=Qt.AlignmentFlag.AlignTop)
        texts = QVBoxLayout()
        texts.setSpacing(6)
        self.kicker = QLabel("")
        self.title = QLabel("")
        self.title.setWordWrap(True)
        self.message = QLabel("")
        self.message.setWordWrap(True)
        texts.addWidget(self.kicker)
        texts.addWidget(self.title)
        texts.addWidget(self.message)
        top.addLayout(texts, 1)
        body.addLayout(top)

        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        self.bar_text = QLabel("")
        bar_row = QHBoxLayout()
        bar_row.addWidget(self.bar, 1)
        bar_row.addWidget(self.bar_text)
        body.addLayout(bar_row)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.btn_setup = QPushButton(tr("Beaker and re-zero…"))
        self.btn_ack = QPushButton(tr("Silence"))
        self.btn_ack.setProperty("variant", "primary")
        for button in (self.btn_setup, self.btn_ack):
            button.setMinimumHeight(38)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            buttons.addWidget(button)
        body.addLayout(buttons)
        self.btn_ack.clicked.connect(self._ack)
        self.btn_setup.clicked.connect(self.setup_clicked)

        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self.hide()

    # ------------------------------------------------------------ แสดง
    def show_alert(self, alert) -> None:
        self._alert = alert
        if alert is None:
            self._timer.stop()
            self.hide()
            return
        color = getattr(Color, SEVERITY_COLOR.get(alert.severity, "INFO"))
        kicker = {"danger": tr("SAFETY ALARM"), "warning": tr("WARNING"), "info": tr("NOTICE")}[alert.severity]
        self.kicker.setText(kicker)
        self.kicker.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 700; letter-spacing: 2px;")
        self.title.setText(alert.title)
        self.title.setStyleSheet(f"color: {Color.TEXT}; font-size: 24px; font-weight: 700;")
        self.message.setText(alert.message)
        self.message.setStyleSheet(f"color: {Color.TEXT_MUTED}; font-size: 15px;")
        has_level = alert.fill_pct is not None
        self.meter.setVisible(True)
        self.meter.set_level(alert.fill_pct if has_level else None, alert.warn_pct, alert.alarm_pct)
        self.bar.setVisible(has_level)
        self.bar_text.setVisible(has_level)
        if has_level:
            self.bar.setValue(int(max(0.0, min(100.0, alert.fill_pct)) * 10))
            self.bar.setStyleSheet(
                f"QProgressBar {{ background: {Color.SURFACE_ALT}; border: none; border-radius: 5px; }}"
                f"QProgressBar::chunk {{ background: {color}; border-radius: 5px; }}")
            self.bar_text.setText(f"{alert.water_ml:.0f} / {alert.capacity_ml:g} ml · {alert.fill_pct:.0f} %")
            self.bar_text.setStyleSheet(f"color: {Color.TEXT}; font-weight: 600;")
        self.btn_ack.setText(alert.ack_text or tr("Got it"))
        self.btn_setup.setVisible(alert.kind in ("overflow", "next", "warn", "zero"))
        self.adjustSize()
        self._place()
        if not self.isVisible():
            self.show()
        self.raise_()
        if alert.severity == "danger":
            self._timer.start()
        else:
            self._timer.stop()
            self._phase = 0.0
        self.update()

    def _place(self) -> None:
        host = self._host.window()
        center = host.mapToGlobal(QPoint(host.width() // 2, host.height() // 2))
        self.move(center.x() - self.width() // 2, center.y() - self.height() // 2 - 40)

    def _ack(self) -> None:
        if self._alert is not None:
            self.acknowledged.emit(self._alert.kind)

    def _tick(self) -> None:
        self._phase = (self._phase + 0.05) % 1.0
        self.meter.set_pulse(0.5 + 0.5 * math.sin(self._phase * 2 * math.pi))
        self.update()

    # ------------------------------------------------------------ วาดการ์ด (ขอบสีตามความรุนแรง)
    def paintEvent(self, _event) -> None:
        if self._alert is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self._card.geometry()).adjusted(0.5, 0.5, -0.5, -0.5)
        # เงานุ่ม (วาดเอง — QGraphicsDropShadowEffect ใส่เงาให้ตัวอักษร/ปุ่มข้างในด้วย ดูเลอะ)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(12, 0, -1):
            shade = QColor(0, 0, 0, int(5 + (12 - i) * 1.2))
            p.setBrush(shade)
            p.drawRoundedRect(rect.adjusted(-i, -i + 8, i, i + 8), 16 + i, 16 + i)
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)
        p.fillPath(path, QColor(Color.SURFACE))
        color = QColor(getattr(Color, SEVERITY_COLOR.get(self._alert.severity, "INFO")))
        glow = 0.55 + 0.45 * math.sin(self._phase * 2 * math.pi) if self._alert.severity == "danger" else 1.0
        color.setAlphaF(max(0.35, glow))
        p.setPen(QPen(color, 3 if self._alert.severity == "danger" else 2))
        p.drawPath(path)
        band = QPainterPath()             # แถบสีด้านบนของการ์ด
        band.addRoundedRect(QRectF(rect.left(), rect.top(), rect.width(), 8), 4, 4)
        p.fillPath(band, color)
        p.end()
