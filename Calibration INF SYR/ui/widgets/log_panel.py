"""LogPanel: แสดงข้อความจากระบบ logging (ต่อกับ LogBridge.message)"""
from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListView, QListWidget, QListWidgetItem, QPushButton

from config.i18n import tr
from ui.theme import Color
from ui.widgets.common import Card

_LEVEL_COLORS = {"WARNING": Color.WARNING, "ERROR": Color.DANGER, "CRITICAL": Color.DANGER}
MAX_LINES = 500


class LogPanel(Card):
    def __init__(self):
        super().__init__(tr("Activity log"))
        clear = QPushButton(tr("Clear"))
        clear.setProperty("variant", "ghost")
        self.header.addWidget(clear)

        self._list = QListWidget()
        self._list.setObjectName("logList")
        self._list.setWordWrap(True)
        self._list.setResizeMode(QListView.ResizeMode.Adjust)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.body.addWidget(self._list, 1)
        clear.clicked.connect(self._list.clear)

    @Slot(str, str, str)
    def append(self, level: str, time_text: str, message: str) -> None:
        item = QListWidgetItem(f"{time_text}  {message}")
        item.setForeground(QColor(_LEVEL_COLORS.get(level, Color.TEXT_MUTED)))
        self._list.addItem(item)
        if self._list.count() > MAX_LINES:
            self._list.takeItem(0)
        self._list.scrollToBottom()
