"""StatCard: การ์ดตัวเลขสรุป — ค่าเด่น 1 ค่า (hero) + ค่ารองเป็นรายการ

    card = StatCard("Flow error", unit="%", metrics=[("a", "Chain A"), ("b", "Chain B")])
    card.set_hero("+1.52", tone="success");  card.set("a", "+1.40 %")
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout

from ui.theme import TONES
from ui.widgets.common import Card, label


class StatCard(Card):
    def __init__(self, title: str, unit: str = "", metrics: list[tuple] = ()):
        """metrics: [(key, ชื่อ)] หรือ [(key, ชื่อ, สี)] — สีใช้จับคู่กับเส้นกราฟ"""
        super().__init__(title)
        self.body.setSpacing(6)

        hero_row = QHBoxLayout()
        hero_row.setSpacing(6)
        self._hero = label("—", "hero")
        self._unit = label(unit, "heroUnit")
        hero_row.addWidget(self._hero)
        hero_row.addWidget(self._unit, alignment=Qt.AlignmentFlag.AlignBottom)
        hero_row.addStretch()
        self.body.addLayout(hero_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(3)
        grid.setColumnStretch(1, 1)
        self._values = {}
        for row, (key, name, *color) in enumerate(metrics):
            name_label = label(name, "metricName")
            value_label = label("—", "metricValue")
            if color:
                name_label.setText(f'<span style="color:{color[0]}">●</span>&nbsp; {name}')
            grid.addWidget(name_label, row, 0)
            grid.addWidget(value_label, row, 1, alignment=Qt.AlignmentFlag.AlignRight)
            self._values[key] = value_label
        self.body.addLayout(grid)
        self.body.addStretch()

    def set_hero(self, text: str, tone: str = "neutral") -> None:
        self._hero.setText(text)
        self._hero.setStyleSheet(f"color: {TONES.get(tone, TONES['neutral'])};")

    def set(self, key: str, text: str) -> None:
        self._values[key].setText(text)

    def reset(self) -> None:
        self.set_hero("—")
        for value in self._values.values():
            value.setText("—")
