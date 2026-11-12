"""StatCard: การ์ดตัวเลขสรุปแบบกะทัดรัด — ค่าเด่น 1 ค่า (hero) ทางซ้าย + ค่ารองทางขวา

    ┌ FLOW ERROR ──────────────────────────────┐
    │ +1.48 %        Flow เฉลี่ย     10.148 ml/h │
    │                2 SD             ± 2.08 %  │
    └──────────────────────────────────────────┘
(เตี้ยกว่าแบบเดิมเกือบครึ่ง เพื่อเหลือพื้นที่ให้กราฟ)

    card = StatCard("Flow error", unit="%", metrics=[("a", "Chain A"), ("b", "Chain B")])
    card.set_hero("+1.52", tone="success");  card.set("a", "+1.40 %")
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QVBoxLayout

from ui.theme import TONES
from ui.widgets.common import label


class StatCard(QFrame):
    def __init__(self, title: str, unit: str = "", metrics: list[tuple] = ()):
        """metrics: [(key, ชื่อ)] หรือ [(key, ชื่อ, สี)] — สีใช้จับคู่กับเส้นกราฟ"""
        super().__init__()
        self.setProperty("card", True)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(0)
        left.addWidget(label(title.upper(), "sectionTitle"))
        hero_row = QHBoxLayout()
        hero_row.setSpacing(4)
        self._hero = label("—", "heroCompact")
        self._unit = label(unit, "heroUnit")
        hero_row.addWidget(self._hero)
        hero_row.addWidget(self._unit, alignment=Qt.AlignmentFlag.AlignBottom)
        hero_row.addStretch()
        left.addLayout(hero_row)
        left.addStretch()
        row.addLayout(left)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(1)
        grid.setColumnStretch(0, 1)
        self._values = {}
        self._names = {}
        for index, (key, name, *color) in enumerate(metrics):
            name_label = label(name, "metricName")
            value_label = label("—", "metricValue")
            if color:
                name_label.setText(f'<span style="color:{color[0]}">●</span>&nbsp;{name}')
            grid.addWidget(name_label, index, 0, alignment=Qt.AlignmentFlag.AlignRight)
            grid.addWidget(value_label, index, 1, alignment=Qt.AlignmentFlag.AlignRight)
            self._values[key] = value_label
            self._names[key] = name_label
        box = QVBoxLayout()
        box.addStretch()
        box.addLayout(grid)
        box.addStretch()
        row.addLayout(box, 1)

    def set_hero(self, text: str, tone: str = "neutral") -> None:
        self._hero.setText(text)
        self._hero.setStyleSheet(f"color: {TONES.get(tone, TONES['neutral'])};")

    def set(self, key: str, text: str) -> None:
        self._values[key].setText(text)

    def set_metric_visible(self, key: str, visible: bool) -> None:
        self._names[key].setVisible(visible)
        self._values[key].setVisible(visible)

    def reset(self) -> None:
        self.set_hero("—")
        for value in self._values.values():
            value.setText("—")
