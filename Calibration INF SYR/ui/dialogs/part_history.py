"""popup ประวัติอะไหล่ + ประกัน — ขึ้นเมื่อเครื่องที่เคยเปลี่ยนอะไหล่กลับมาอีกครั้ง (wizard ขั้น 2)

    เครื่องนี้เคยเปลี่ยนอะไหล่ — รอบนี้มีเคลมประกันไหม?
    ┌──┬──────────────┬────────────┬────────────┬───────────────────────┐
    │☐ │ Battery      │ 2026-03-02 │ 2027-03-02 │ ● ในประกัน เหลือ 109 วัน │
    │☐ │ Keypad       │ 2025-10-20 │ 2026-10-20 │ ● Late เกินมา 24 วัน      │  ← ให้พิจารณา
    │  │ Display      │ 2024-01-05 │ 2025-01-05 │ ● หมดประกัน               │  ← ติ๊กไม่ได้
    └──┴──────────────┴────────────┴────────────┴───────────────────────┘
    [ไม่มีเคลม]                                   [เคลมรายการที่ติ๊ก (2)]

ติ๊กแล้วยืนยัน -> ชิ้นนั้นไปอยู่ใน "อะไหล่ที่เปลี่ยน" พร้อมสถานะประกันอัตโนมัติ (วันเริ่มประกันเดิม ไม่นับใหม่)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)
from PySide6.QtGui import QColor

from config.i18n import tr
from core.warranty import ACTIVE, LATE, PartWarranty
from ui.theme import Color
from ui.widgets.common import label

STATE_COLORS = {ACTIVE: Color.WARRANTY, LATE: Color.WARRANTY_LATE}


def state_text(item: PartWarranty) -> str:
    s = item.status
    if s.state == ACTIVE:
        return tr("In warranty · {d} days left", d=s.days_left)
    if s.state == LATE:
        return tr("Late · {d} days past warranty — consider", d=-s.days_left)
    return tr("Warranty ended")


class PartHistoryDialog(QDialog):
    """claims = ชื่ออะไหล่ที่ผู้ใช้ติ๊กว่าจะเคลม (หลัง accept)"""

    def __init__(self, parent, device: str, items: list[PartWarranty], already: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Parts replaced before"))
        self.setModal(True)
        self.resize(720, 420)
        self.claims: list[str] = []
        self._items = items
        already_keys = {" ".join(a.lower().split()) for a in already or []}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(10)
        root.addWidget(label(tr("This device has had parts replaced — any warranty claim this time?"), "pageTitle"))
        claimable = sum(item.status.claimable for item in items)
        subtitle = label(tr("{device} · {n} parts still claimable. Tick the ones to claim; they are added to "
                            "\"Parts replaced\" marked as warranty. The warranty start date stays the same.",
                            device=device, n=claimable), "pageSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        self.table = QTableWidget(len(items), 5)
        self.table.setHorizontalHeaderLabels(["", tr("Part"), tr("Warranty from"), tr("Warranty until"), tr("Status")])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        self.table.setProperty("claims", True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for row, item in enumerate(items):
            check = QTableWidgetItem()
            if item.status.claimable:
                check.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                ticked = " ".join(item.part.lower().split()) in already_keys
                check.setCheckState(Qt.CheckState.Checked if ticked else Qt.CheckState.Unchecked)
            else:
                check.setFlags(Qt.ItemFlag.NoItemFlags)
            self.table.setItem(row, 0, check)
            times = f"  ·  {tr('replaced {n}×', n=item.times)}" if item.times > 1 else ""
            cells = [item.part + times, item.first_at, item.status.until.isoformat(), "●  " + state_text(item)]
            for column, text in enumerate(cells, start=1):
                cell = QTableWidgetItem(text)
                cell.setFlags(Qt.ItemFlag.ItemIsEnabled)
                color = STATE_COLORS.get(item.status.state, Color.WARRANTY_EXPIRED)
                cell.setForeground(QColor(color if column == 4 else Color.TEXT if item.status.claimable
                                          else Color.TEXT_FAINT))
                if item.last_at != item.first_at and column == 2:
                    cell.setToolTip(tr("Last replaced {date}", date=item.last_at))
                self.table.setItem(row, column, cell)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.itemChanged.connect(lambda *_: self._update_button())
        root.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        none = QPushButton(tr("No claim this time"))
        self._claim = QPushButton()
        self._claim.setProperty("variant", "primary")
        buttons.addWidget(none)
        buttons.addStretch()
        buttons.addWidget(self._claim)
        root.addLayout(buttons)
        none.clicked.connect(self.reject)
        self._claim.clicked.connect(self._accept)
        self._update_button()

    def _on_cell_clicked(self, row: int, column: int) -> None:
        """คลิกที่ไหนของแถวก็ติ๊กได้ (เฉพาะแถวที่ยังเคลมได้)"""
        check = self.table.item(row, 0)
        if column != 0 and check.flags() & Qt.ItemFlag.ItemIsUserCheckable:
            check.setCheckState(Qt.CheckState.Unchecked if check.checkState() == Qt.CheckState.Checked
                                else Qt.CheckState.Checked)

    def selected(self) -> list[str]:
        return [item.part for row, item in enumerate(self._items)
                if self.table.item(row, 0).checkState() == Qt.CheckState.Checked]

    def _update_button(self) -> None:
        n = len(self.selected())
        self._claim.setText(tr("Claim ticked parts ({n})", n=n) if n else tr("Claim ticked parts"))
        self._claim.setEnabled(n > 0)

    def _accept(self) -> None:
        self.claims = self.selected()
        self.accept()
