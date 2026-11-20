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
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from config.i18n import tr
from config.settings import UiSettings
from ui.theme import Color, resolve
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
        self._chip_texts: list[tuple[QPushButton, str, str]] = []    # (ปุ่ม, ข้อความเต็ม, แบบย่อ)
        self._compact = False
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    # ---- ช่องแคบ (หน้าต่างเล็ก / ขยายตัวอักษร): ชื่อเส้นย่อเหลือสัญลักษณ์ (ชื่อเต็มใน tooltip) ไม่บังคับให้หน้าต่างกว้างเกินจอ
    # (2026-11-20: หัวกราฟ Flow รายช่วงเคยต้องการ ~1,100 px — หน้าต่างผลย้อนหลังล้นจอ)
    def minimumSizeHint(self) -> QSize:
        return QSize(120, 26)

    def _full_width(self) -> int:
        chips = sum(b.fontMetrics().horizontalAdvance(full) + 26 for b, full, _ in self._chip_texts)
        styles = sum(self._styles.itemAt(i).widget().sizeHint().width() for i in range(self._styles.count())
                     if self._styles.itemAt(i).widget())
        return self._title.sizeHint().width() + chips + styles + 40

    def _fit(self) -> None:
        compact = self.isVisible() and self.width() < self._full_width()     # ยังไม่แสดงบนจอ = ชื่อเต็ม
        if compact == self._compact:
            return
        self._compact = compact
        for button, full, short in self._chip_texts:
            button.setText(short if compact else full)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit()

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
        self._chip_texts = []
        for entry in module._legend:
            color, name = resolve(entry[0]), entry[1]
            symbol = entry[2] if len(entry) > 2 and entry[2] else "●"
            key = entry[3] if len(entry) > 3 else None
            on = key is None or module.series_visible(key)
            chip = QPushButton(f"{symbol}  {tr(name)}")
            chip.setProperty("variant", "legendChip")
            chip.setMinimumWidth(0)
            chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            self._chip_texts.append((chip, f"{symbol}  {tr(name)}", symbol))
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
        self._compact = None            # คำนวณใหม่ตามความกว้างตอนนี้
        self._fit()


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
