"""ช่องวันที่ของหน้าตั้งค่า (ผู้ใช้ 2026-11-20: วันสอบเทียบ/ครบกำหนดของตราชั่ง) — เลือกจากปฏิทิน ว่างได้

ค่าเก็บเป็น ISO "YYYY-MM-DD" ("" = ไม่ได้ตั้ง) · จอภาษาไทยแสดงปี พ.ศ. (BuddhistDateEdit) · ปุ่ม × ล้างค่า
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit, QHBoxLayout, QPushButton, QWidget

from config.i18n import tr
from ui.widgets.history_filters import _NO_DATE, BuddhistDateEdit, _OpenAtToday, _thai


class DateField(QWidget):
    def __init__(self):
        super().__init__()
        box = QHBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(6)
        self.edit = BuddhistDateEdit() if _thai() else QDateEdit()
        self.edit.setCalendarPopup(True)
        self.edit.setMinimumDate(_NO_DATE)
        self.edit.setSpecialValueText("—")
        if not _thai():
            self.edit.setDisplayFormat("dd/MM/yyyy")
        self.edit.calendarWidget().installEventFilter(_OpenAtToday(self.edit))
        clear = QPushButton("×")
        clear.setFixedWidth(28)
        clear.setToolTip(tr("Clear"))
        clear.clicked.connect(lambda: self.edit.setDate(_NO_DATE))
        box.addWidget(self.edit, 1)
        box.addWidget(clear)
        self.edit.setDate(_NO_DATE)

    def text(self) -> str:
        day = self.edit.date()
        return "" if day == _NO_DATE or not day.isValid() else day.toString("yyyy-MM-dd")

    def setText(self, value: str) -> None:
        try:
            day = date.fromisoformat(str(value or "").strip())
        except ValueError:
            self.edit.setDate(_NO_DATE)
            return
        self.edit.setDate(QDate(day.year, day.month, day.day))
