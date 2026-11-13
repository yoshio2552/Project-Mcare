"""WindowTable: ตารางหน้าต่างจับรอบปั๊ม "ราย rate" (regression / n̄) — ใช้ทั้ง popup เตือนสอบเทียบและหน้าข้อมูลสอบเทียบ

แต่ละแถว = 1 rate: คาบ (+ที่มา) · regression · n̄ · จุดต่อรอบ · สถานะ
แก้ได้ (editable): รู้ช่วงเวลาต่อจุดของตราชั่ง = กรอกเป็นจำนวนจุด (แสดงสัดส่วนของคาบใน tooltip)
                   ไม่รู้ = กรอกเป็นสัดส่วนของคาบ
ค่าที่คืน (values) เป็นสัดส่วนของคาบเสมอ — เก็บแบบนี้จึงใช้ได้ทั้งตราชั่ง 5 Hz และ 10 Hz
"""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

from config.i18n import tr
from core.windows import (
    MIN_HALF_POINTS, MIN_REGRESSION_POINTS, cycle_windows, fraction_problems, fractions_from_points,
)
from services.window_plan import FIT_TEXT, PERIOD_TEXT, RateWindow
from ui.theme import Color
from ui.widgets.common import int_box, number_box

COLUMNS = ("Rate", "Pump cycle", "Regression", "n̄ (peak left/right)", "Points per cycle", "Status")
COL_REG, COL_HALF, COL_PPC, COL_STATUS = 2, 3, 4, 5
LEVEL_TEXT = {"low": "⚠ Few points per cycle", "too_low": "⛔ Too few points per cycle — use time-based capture",
              "unknown": "Points per cycle known once the balance is read"}


def status_text(item: RateWindow) -> tuple[str, str]:
    """(ข้อความ, สี) ของคอลัมน์สถานะ"""
    parts, color = [tr(FIT_TEXT.get(item.fit, item.fit))], Color.SUCCESS if item.calibrated else Color.WARNING
    if item.level in ("low", "too_low"):
        parts.append(tr(LEVEL_TEXT[item.level]))
        color = Color.DANGER if item.level == "too_low" else Color.WARNING
    for kind, text in item.problems:
        parts.append(("⛔ " if kind == "error" else "⚠ ") + tr(text))
        color = Color.DANGER if kind == "error" else color if color == Color.DANGER else Color.WARNING
    return "  ·  ".join(parts), color


def period_text(item: RateWindow) -> str:
    if not item.period_s:
        return "—"
    return f"{item.period_s:.2f} s  ({tr(PERIOD_TEXT.get(item.period_source, item.period_source))})"


class WindowTable(QTableWidget):
    changed = Signal()

    def __init__(self, editable: bool = False, parent=None):
        super().__init__(0, len(COLUMNS), parent)
        self._editable = editable
        self._items: list[RateWindow] = []
        self._dt: float | None = None
        self._edited: set[int] = set()
        self.setHorizontalHeaderLabels([tr(c) for c in COLUMNS])
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.horizontalHeader()
        for column in range(len(COLUMNS) - 1):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeMode.Stretch)

    # ------------------------------------------------------------------ data
    def set_rows(self, items: list[RateWindow], sample_period_s: float | None) -> None:
        self._items, self._dt, self._edited = [replace(i) for i in items], sample_period_s, set()
        self.setRowCount(len(items))
        for row, item in enumerate(self._items):
            self._set_text(row, 0, f"{item.rate:g} ml/h")
            self._set_text(row, 1, period_text(item))
            if self._editable:
                self._make_editors(row, item)
            self._refresh_row(row)
        self.resizeRowsToContents()

    def fit_height(self, maximum: int = 360) -> None:
        """สูงพอดีทุกแถว (ไม่ต้องเลื่อน) แต่ไม่เกิน maximum"""
        self.resizeRowsToContents()
        rows = sum(self.rowHeight(r) for r in range(self.rowCount()))
        self.setFixedHeight(min(maximum, self.horizontalHeader().height() + rows + 2 * self.frameWidth() + 4))

    def items(self) -> list[RateWindow]:
        return list(self._items)

    def values(self) -> dict[float, tuple[float, float]]:
        """{rate: (r, h)} สัดส่วนของคาบที่แสดงอยู่ (รวมที่แก้แล้ว)"""
        return {i.rate: (i.regression_fraction, i.half_fraction) for i in self._items}

    def edited_rates(self) -> list[float]:
        return [self._items[row].rate for row in sorted(self._edited)]

    def selected_rate(self) -> float | None:
        row = self.currentRow()
        return self._items[row].rate if 0 <= row < len(self._items) else None

    @property
    def by_points(self) -> bool:
        return bool(self._dt)

    # --------------------------------------------------------------- editors
    def _make_editors(self, row: int, item: RateWindow) -> None:
        if self.by_points and item.windows is not None:
            reg = int_box(MIN_REGRESSION_POINTS, 100000, item.windows.regression, " " + tr("pts"))
            half = int_box(MIN_HALF_POINTS, 100000, item.windows.half, " " + tr("pts"))
        else:
            reg = number_box(0.05, 1.0, item.regression_fraction, 2, " × " + tr("cycle"))
            half = number_box(0.05, 1.0, item.half_fraction, 2, " × " + tr("cycle"))
        for column, box in ((COL_REG, reg), (COL_HALF, half)):
            box.valueChanged.connect(lambda _v, r=row: self._on_edit(r))
            self.setCellWidget(row, column, box)

    def _on_edit(self, row: int) -> None:
        item = self._items[row]
        reg, half = self.cellWidget(row, COL_REG).value(), self.cellWidget(row, COL_HALF).value()
        if self.by_points and item.period_s:
            r, h = fractions_from_points(int(reg), int(half), item.period_s, self._dt)
        else:
            r, h = float(reg), float(half)
        item.regression_fraction, item.half_fraction, item.fit = r, h, "manual" if self._editable else item.fit
        item.windows = cycle_windows(item.period_s, self._dt, r, h)
        item.problems = fraction_problems(r, h)
        self._edited.add(row)
        self._refresh_row(row)
        self.changed.emit()

    # ---------------------------------------------------------------- render
    def _set_text(self, row: int, column: int, text: str, color: str | None = None, tip: str = "") -> None:
        cell = QTableWidgetItem(text)
        cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        if color:
            cell.setForeground(QColor(color))
        if tip:
            cell.setToolTip(tip)
        self.setItem(row, column, cell)

    def _refresh_row(self, row: int) -> None:
        item = self._items[row]
        w = item.windows
        fractions = tr("{r:.2f} × cycle / {h:.2f} × cycle", r=item.regression_fraction, h=item.half_fraction)
        if not self._editable:
            self._set_text(row, COL_REG, f"{w.regression} {tr('pts')}" if w else f"{item.regression_fraction:.2f} × {tr('cycle')}",
                           tip=fractions)
            self._set_text(row, COL_HALF, f"{w.half} {tr('pts')}" if w else f"{item.half_fraction:.2f} × {tr('cycle')}",
                           tip=fractions)
        else:
            for column in (COL_REG, COL_HALF):
                self.cellWidget(row, column).setToolTip(fractions)
        ppc_color = {"low": Color.WARNING, "too_low": Color.DANGER}.get(item.level)
        self._set_text(row, COL_PPC, f"{w.points_per_cycle:.1f}" if w else "—", ppc_color,
                       tip=tr("Balance points per pump cycle (fewer than 12 = coarse, fewer than 8 = not allowed)"))
        text, color = status_text(item)
        self._set_text(row, COL_STATUS, text, color)
