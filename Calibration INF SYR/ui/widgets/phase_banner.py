"""PhaseBanner: แถบบอกว่า "ตอนนี้ระบบกำลังทำอะไร / ผู้ใช้ต้องทำอะไรต่อ" พร้อมปุ่มลัด (ถ้ามี)"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton

from ui.theme import set_tone
from ui.widgets.common import label


class PhaseBanner(QFrame):
    action_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setProperty("banner", True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 10, 8)
        layout.setSpacing(12)
        self._text = label("", "bannerText")
        self._text.setWordWrap(True)
        self._button = QPushButton()
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.clicked.connect(self.action_clicked)
        layout.addWidget(self._text, 1)
        layout.addWidget(self._button)
        self._tone = None
        self.hide()

    def show_message(self, text: str, tone: str = "info", button: str | None = None) -> None:
        self._text.setText(text)
        self._button.setVisible(button is not None)
        if button is not None:
            self._button.setText(button)
        if tone != self._tone:
            self._tone = tone
            set_tone(self, tone)
        self.show()
