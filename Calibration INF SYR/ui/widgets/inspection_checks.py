"""ผลตรวจรายข้อของใบรายงาน: ผ่าน / ไม่ผ่าน / ไม่มี (services/report/checklist.py) — ใช้ใน wizard ขั้น 2 และข้อมูลใบรายงาน

wizard ตั้งต้นทุกข้อ "ผ่าน" (ผู้ใช้กดเฉพาะข้อยกเว้น) — เก็บลงฐานข้อมูลเฉพาะข้อยกเว้น (checklist.compress)

แต่ละข้อมีปุ่ม 3 ปุ่มแบบเลือกได้อันเดียว (กดซ้ำ = ยกเลิก กลับเป็นยังไม่ได้ตรวจ) · ปุ่ม "ผ่านทั้งหมด" ติ๊กเฉพาะข้อที่ยังว่าง
· ข้อที่มีรายละเอียด (แบตเตอรี่) มีช่องกรอกสั้น · เปลี่ยนชนิดเครื่อง = รายการเปลี่ยน ค่าเดิมของข้อที่ชื่อตรงกันยังอยู่
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from config.i18n import tr
from services.report import checklist
from ui.theme import Color
from ui.widgets.common import label

GROUP_TITLES = {"visual": "Visual inspection", "function": "Function inspection", "performance": "Performance inspection"}
STATUS_TEXT = {checklist.PASS: "Pass", checklist.FAIL: "Fail", checklist.NA: "N/A"}


class InspectionChecks(QWidget):
    changed = Signal()

    def __init__(self, pump: str = "infusion", parent: QWidget | None = None, scroll: bool = True):
        super().__init__(parent)
        self._pump = ""
        self._values: dict[str, str] = {}
        self._notes: dict[str, str] = {}
        self._groups: dict[str, QButtonGroup] = {}
        self._buttons: dict[str, dict[str, QPushButton]] = {}
        self._note_edits: dict[str, QLineEdit] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        head = QHBoxLayout()
        self.title = label(tr("Checklist results for the report"), "cardTitle")
        self.summary = label("", "hint")
        self.btn_all = QPushButton(tr("Pass all blank items"))
        self.btn_all.setProperty("variant", "ghost")
        self.btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_all.clicked.connect(self.pass_all)
        self.btn_clear = QPushButton(tr("Clear"))
        self.btn_clear.setProperty("variant", "ghost")
        self.btn_clear.clicked.connect(self.clear)
        head.addWidget(self.title)
        head.addWidget(self.summary, 1)
        head.addWidget(self.btn_all)
        head.addWidget(self.btn_clear)
        root.addLayout(head)
        # ผลครั้งก่อนของเครื่องเดียวกัน (ข้อความจาง ไม่ติ๊กให้เอง — ขั้นตรวจเครื่องเริ่มใหม่ทุกครั้ง)
        self.previous = label("", "hint")
        self.previous.setWordWrap(True)
        self.previous.hide()
        root.addWidget(self.previous)

        self._body = QWidget()
        self._grid = QGridLayout(self._body)
        self._grid.setContentsMargins(0, 0, 4, 0)
        self._grid.setHorizontalSpacing(10)
        self._grid.setVerticalSpacing(2)
        if scroll:
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setFrameShape(QScrollArea.Shape.NoFrame)
            area.setWidget(self._body)
            root.addWidget(area, 1)
        else:
            root.addWidget(self._body)
        self.set_pump(pump)

    # ------------------------------------------------------------- ข้อมูล
    def set_pump(self, pump: str) -> None:
        pump = pump if pump in checklist.ITEMS else "infusion"
        if pump == self._pump:
            return
        self._pump = pump
        self._rebuild()

    def set_values(self, checks: dict | None, notes: dict | None = None) -> None:
        self._values = {k: v for k, v in (checks or {}).items() if v in checklist.STATUSES}
        self._notes = {k: str(v) for k, v in (notes or {}).items() if str(v).strip()}
        self._sync()

    def set_previous(self, text: str) -> None:
        self.previous.setText(text)
        self.previous.setVisible(bool(text))

    def values(self) -> dict:
        keys = set(checklist.all_keys(self._pump))
        return {k: v for k, v in self._values.items() if k in keys}

    def notes(self) -> dict:
        return {k: v for k, v in self._notes.items() if v.strip()}

    def pass_all(self) -> None:
        for key in checklist.all_keys(self._pump):
            self._values.setdefault(key, checklist.PASS)
        self._sync()
        self.changed.emit()

    def clear(self) -> None:
        self._values = {}
        self._sync()
        self.changed.emit()

    # ------------------------------------------------------------- จอ
    def _rebuild(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for group in self._groups.values():
            group.deleteLater()
        self._groups, self._buttons, self._note_edits = {}, {}, {}
        lang_th = tr("Pass") != "Pass"           # ชื่อรายการตามภาษาของโปรแกรม
        row = 0
        for group in checklist.GROUPS:
            caption = label(tr(GROUP_TITLES[group]), "fieldLabel")
            caption.setStyleSheet(f"color: {Color.ACCENT}; font-weight: 600; padding-top: 4px;")
            self._grid.addWidget(caption, row, 0, 1, 8)
            row += 1
            items = checklist.items(self._pump, group)
            half = (len(items) + 1) // 2
            for index, (key, th, en) in enumerate(items):
                r, col = row + (index % half), (index // half) * 4
                name = QLabel(th if lang_th else en)
                name.setMinimumWidth(120)
                self._grid.addWidget(name, r, col)
                buttons = QHBoxLayout()
                buttons.setSpacing(2)
                group_box = QButtonGroup(self)
                group_box.setExclusive(False)
                self._buttons[key] = {}
                for status in checklist.STATUSES:
                    button = QPushButton(tr(STATUS_TEXT[status]))
                    button.setCheckable(True)
                    button.setProperty("variant", "chip")
                    button.setProperty("status", status)
                    button.setFixedHeight(24)
                    button.setMinimumWidth(52)
                    button.setCursor(Qt.CursorShape.PointingHandCursor)
                    button.clicked.connect(lambda checked, k=key, s=status: self._on_click(k, s, checked))
                    group_box.addButton(button)
                    buttons.addWidget(button)
                    self._buttons[key][status] = button
                self._groups[key] = group_box
                holder = QWidget()
                holder.setLayout(buttons)
                buttons.setContentsMargins(0, 0, 0, 0)
                self._grid.addWidget(holder, r, col + 1)
                if key in checklist.NOTE_ITEMS:
                    edit = QLineEdit()
                    edit.setPlaceholderText(checklist.NOTE_ITEMS[key][0 if lang_th else 1])
                    edit.setMinimumWidth(150)
                    edit.textEdited.connect(lambda text, k=key: self._on_note(k, text))
                    self._grid.addWidget(edit, r, col + 2)
                    self._note_edits[key] = edit
            row += half
        self._grid.setColumnStretch(3, 1)
        self._grid.setColumnStretch(7, 1)
        self._grid.setRowStretch(row, 1)
        self._sync()

    def _on_click(self, key: str, status: str, checked: bool) -> None:
        if checked:
            self._values[key] = status
        elif self._values.get(key) == status:
            self._values.pop(key, None)
        self._sync()
        self.changed.emit()

    def _on_note(self, key: str, text: str) -> None:
        self._notes[key] = text
        self.changed.emit()

    def _sync(self) -> None:
        colors = {checklist.PASS: Color.SUCCESS, checklist.FAIL: Color.DANGER, checklist.NA: Color.TEXT_MUTED}
        for key, buttons in self._buttons.items():
            current = self._values.get(key, "")
            for status, button in buttons.items():
                button.blockSignals(True)
                button.setChecked(status == current)
                button.blockSignals(False)
                if status == current:
                    button.setStyleSheet(f"background: {colors[status]}; color: white; border-color: {colors[status]};"
                                         " padding: 2px 8px; font-weight: 600;")
                else:
                    button.setStyleSheet("padding: 2px 8px;")
        for key, edit in self._note_edits.items():
            if edit.text() != self._notes.get(key, ""):
                edit.setText(self._notes.get(key, ""))
        count = checklist.summary(self._pump, self._values)
        self.summary.setText(tr("{ok} pass · {fail} fail · {na} N/A · {blank} not checked", ok=count[checklist.PASS],
                                fail=count[checklist.FAIL], na=count[checklist.NA], blank=count["blank"]))
        self.summary.setStyleSheet(f"color: {Color.DANGER};" if count[checklist.FAIL] else "")
