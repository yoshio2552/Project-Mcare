"""PlotCell: 1 ช่องกราฟ = หัวกราฟแบบ Qt (PlotHeader) + กราฟ pyqtgraph — ใช้ทั้งหน้าทดสอบและหน้าประวัติ

    ┌───────────────────────────────────────────────────────────────────┐
    │ Flow รายช่วง   ● สาย A  ● สาย B  ━ Moving avg  ┄ ค่าเฉลี่ยรวม   [ขั้นบันได|จุด] │
    │  (กราฟ)                                                            │
    └───────────────────────────────────────────────────────────────────┘

- ชื่อเส้นบนหัวกราฟเป็นปุ่ม: กดเพื่อซ่อน/แสดงเส้นนั้น (ซ่อนแล้วจะจางลง) — เฉพาะเส้นที่โมดูลให้ key ไว้
- ปุ่มรูปแบบการวาด (ถ้าโมดูลมี styles) อยู่ชิดขวาของหัวกราฟ
ตัวเลือกจึงอยู่ "บนกราฟที่มันควบคุม" และไม่กินพื้นที่ของตัวกราฟ
"""
from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from config.i18n import tr
from config.settings import UiSettings
from ui.theme import Color
from ui.widgets.common import label


class PlotHeader(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(26)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 0, 4, 0)
        row.setSpacing(4)
        self._title = label("", "plotTitle")
        row.addWidget(self._title)
        row.addSpacing(8)
        self._chips = QHBoxLayout()
        self._chips.setSpacing(2)
        row.addLayout(self._chips)
        row.addStretch()
        self._styles = QHBoxLayout()
        self._styles.setSpacing(0)
        row.addLayout(self._styles)

    @staticmethod
    def _clear(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()               # ซ่อนทันที (deleteLater ลบจริงรอบถัดไป — ไม่ให้ค้างทับหัวกราฟ)
                widget.setParent(None)
                widget.deleteLater()

    def render(self, module) -> None:
        self._title.setText(tr(module._title))
        self._clear(self._chips)
        for entry in module._legend:
            color, name = entry[0], entry[1]
            symbol = entry[2] if len(entry) > 2 and entry[2] else "●"
            key = entry[3] if len(entry) > 3 else None
            on = key is None or module.series_visible(key)
            chip = QPushButton(f"{symbol}  {tr(name)}")
            chip.setProperty("variant", "legendChip")
            chip.setStyleSheet(f"color: {color if on else Color.TEXT_FAINT};" + ("" if on else " text-decoration: line-through;"))
            if key is None:
                chip.setEnabled(False)
                chip.setProperty("static", True)
            else:
                chip.setCursor(Qt.CursorShape.PointingHandCursor)
                chip.setToolTip(tr("Click to hide this line") if on else tr("Click to show this line"))
                chip.clicked.connect(lambda _=False, k=key, v=not on: module.set_series_visible(k, v))
            self._chips.addWidget(chip)

        self._clear(self._styles)
        current = module.current_style()
        for index, (key, name) in enumerate(module.styles):
            button = QPushButton(tr(name))
            button.setProperty("variant", "segmentSmall")
            button.setProperty("position", "first" if index == 0 else "last" if index == len(module.styles) - 1 else "mid")
            button.setCheckable(True)
            button.setChecked(key == current)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, k=key: module.set_style(k))
            self._styles.addWidget(button)


class PlotCell(QFrame):
    """กรอบการ์ด 1 ช่อง: หัวกราฟ + กราฟ — self.module คือ PlotModule ที่สร้างให้"""

    def __init__(self, module_class, ui: UiSettings):
        super().__init__()
        self.setProperty("plotCell", True)
        box = QVBoxLayout(self)
        box.setContentsMargins(4, 6, 6, 4)
        box.setSpacing(0)
        self.header = PlotHeader()
        self.widget = pg.PlotWidget()
        self.widget.setStyleSheet("border: none;")
        box.addWidget(self.header)
        box.addWidget(self.widget, 1)
        self.module = module_class(self.widget.getPlotItem(), ui)
        self.module.attach_header(self.header)
