"""แผงคัดกรองขั้นสูงของหน้าประวัติ (ผู้ใช้ 2026-11-19) — กางใต้ช่องค้นหา ตารางยังเห็นอยู่

ตัวเลือกมาจากข้อมูลจริงในแท็บ (พิมพ์บางส่วนได้ — เทียบแบบมีคำนี้อยู่) · รุ่นแสดงเฉพาะของยี่ห้อที่เลือก
· เลือกปี = ตั้งช่วงวันที่ 1 ม.ค. – 31 ธ.ค. ของปีนั้นให้เอง (ไม่ขัดกัน) · แก้วันที่เอง = ปีกลับเป็น "ทุกปี"
· ตัวกรองที่ใช้อยู่ขึ้นเป็นป้ายมี × ให้เอาออกทีละอัน (chips)
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QDateTime, QEvent, QObject, QTime, Qt, Signal
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import (QComboBox, QDateEdit, QFrame, QGridLayout, QHBoxLayout, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from config.i18n import tr
from services import history_search
from ui.widgets.common import label

_NO_DATE = QDate(2000, 1, 1)            # ค่าต่ำสุด = ไม่กรอง (แสดง —)
TEXT_FIELDS = [("site", "Hospital / site"), ("brand", "Brand"), ("model", "Model"), ("ivset", "IV set / syringe"),
               ("operator", "Operator")]


def _thai() -> bool:
    return tr("Pass") != "Pass"


class BuddhistDateEdit(QDateEdit):
    """ช่องวันที่แสดง/รับปี พ.ศ. (dd/MM/ปปปป) — PySide6 ไม่มีปฏิทินพุทธในตัว · ค่าข้างในยังเป็น ค.ศ."""
    OFFSET = 543

    def textFromDateTime(self, value: QDateTime) -> str:
        if value.date() == self.minimumDate() and self.specialValueText():
            return self.specialValueText()
        day = value.date()
        return f"{day.day():02d}/{day.month():02d}/{day.year() + self.OFFSET}"

    def _parse(self, text: str) -> QDate | None:
        parts = text.strip().split("/")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            return None
        year = int(parts[2])
        day = QDate(year - self.OFFSET if year > 2400 else year, int(parts[1]), int(parts[0]))
        return day if day.isValid() else None

    def dateTimeFromText(self, text: str) -> QDateTime:
        day = self._parse(text)
        return QDateTime(day if day is not None else self.minimumDate(), QTime(12, 0), self.timeSpec())   # เที่ยงวัน: ไม่เลื่อนวันตามเขตเวลา

    def validate(self, text: str, pos: int):
        if text == self.specialValueText() or self._parse(text) is not None:
            return QValidator.State.Acceptable, text, pos
        return QValidator.State.Intermediate, text, pos


class _OpenAtToday(QObject):
    """ปฏิทินของช่องวันที่ที่ยังว่าง: เปิดที่เดือนปัจจุบัน (เดิมเปิดที่ ม.ค. 2000 ซึ่งเป็นค่า "ว่าง") — ผู้ใช้ 2026-11-19"""

    def __init__(self, box: QDateEdit):
        super().__init__(box)
        self._box = box

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Show and self._box.date() == _NO_DATE:
            today = QDate.currentDate()
            obj.setCurrentPage(today.year(), today.month())
            obj.setSelectedDate(today)
        return False


class AdvancedFilters(QFrame):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.setProperty("card", True)
        self._records: list[dict] = []
        self._loading = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        self.boxes: dict[str, QComboBox] = {}
        for name, _text in TEXT_FIELDS:
            box = QComboBox()
            box.setEditable(True)
            box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            box.lineEdit().setPlaceholderText(tr("Any"))
            box.lineEdit().setClearButtonEnabled(True)
            box.setMinimumWidth(150)
            box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            box.currentTextChanged.connect(lambda _t, n=name: self._on_text(n))
            self.boxes[name] = box
        self.pump = QComboBox()
        for value, text in (("", "Any"), ("infusion", "Infusion pump"), ("syringe", "Syringe pump")):
            self.pump.addItem(tr(text), value)
        self.pump.currentIndexChanged.connect(self._emit)
        self.year = QComboBox()
        self.year.currentIndexChanged.connect(self._on_year)
        self.date_from, self.date_to = self._date_box(), self._date_box()
        self.date_from.dateChanged.connect(self._on_dates)
        self.date_to.dateChanged.connect(self._on_dates)

        cells = [("Hospital / site", self.boxes["site"]), ("Device type", self.pump), ("Brand", self.boxes["brand"]),
                 ("Model", self.boxes["model"]), ("IV set / syringe", self.boxes["ivset"]),
                 ("Operator", self.boxes["operator"]), ("Year", self.year)]
        for index, (text, widget) in enumerate(cells):
            row, col = divmod(index, 4)
            grid.addWidget(label(tr(text), "fieldLabel"), row * 2, col)
            grid.addWidget(widget, row * 2 + 1, col)
        dates = QHBoxLayout()
        dates.setSpacing(6)
        dates.addWidget(self.date_from, 1)
        dates.addWidget(label("–", "fieldLabel"))
        dates.addWidget(self.date_to, 1)
        grid.addWidget(label(tr("Date from – to"), "fieldLabel"), 2, 3)
        grid.addLayout(dates, 3, 3)
        for col in range(4):
            grid.setColumnStretch(col, 1)
        outer.addLayout(grid)
        bottom = QHBoxLayout()
        self.summary = label("", "hint")
        self.btn_clear = QPushButton(tr("Clear filters"))
        self.btn_clear.setProperty("variant", "ghost")
        self.btn_clear.clicked.connect(self.clear)
        bottom.addWidget(self.summary, 1)
        bottom.addWidget(self.btn_clear)
        outer.addLayout(bottom)

    @staticmethod
    def _date_box() -> QDateEdit:
        box = BuddhistDateEdit() if _thai() else QDateEdit()      # ฉบับไทยแสดง พ.ศ.
        box.setCalendarPopup(True)
        box.setDisplayFormat("dd/MM/yyyy")
        box.setMinimumDate(_NO_DATE)
        box.setSpecialValueText("—")
        box.setDate(_NO_DATE)
        box.setMinimumWidth(110)
        box.calendarWidget().installEventFilter(_OpenAtToday(box))
        return box

    # ------------------------------------------------------------ ข้อมูล
    def set_records(self, records: list[dict]) -> None:
        """เติมตัวเลือกจากผลในแท็บ (คงค่าที่เลือก/พิมพ์ไว้)"""
        self._records = records
        self._loading = True
        for name, box in self.boxes.items():
            self._fill(box, history_search.distinct(records, name, self._where(name)))
        current = self.year.currentData()
        self.year.blockSignals(True)
        self.year.clear()
        self.year.addItem(tr("Any year"), None)
        for year in history_search.years(records):
            self.year.addItem(str(year if _thai() else year - 543), year)
        self.year.setCurrentIndex(max(0, self.year.findData(current)))
        self.year.blockSignals(False)
        self._loading = False

    def _where(self, name: str) -> dict | None:
        if name == "model" and self.boxes["brand"].currentText().strip():
            return {"brand": self.boxes["brand"].currentText().strip()}
        return None

    @staticmethod
    def _fill(box: QComboBox, values: list[str]) -> None:
        text = box.currentText()
        box.blockSignals(True)
        box.clear()
        box.addItem("")
        box.addItems(values)
        box.setEditText(text)
        box.blockSignals(False)

    # ------------------------------------------------------------ ค่า
    def value(self) -> history_search.AdvancedFilter:
        def day(box: QDateEdit) -> date | None:
            return None if box.date() == _NO_DATE else box.date().toPython()
        return history_search.AdvancedFilter(
            site=self.boxes["site"].currentText().strip(), pump=self.pump.currentData() or "",
            brand=self.boxes["brand"].currentText().strip(), model=self.boxes["model"].currentText().strip(),
            ivset=self.boxes["ivset"].currentText().strip(), operator=self.boxes["operator"].currentText().strip(),
            date_from=day(self.date_from), date_to=day(self.date_to))

    def chips(self) -> list[tuple[str, str]]:
        """[(ช่อง, ข้อความป้าย)] ของตัวกรองที่ใช้อยู่"""
        out = []
        names = dict(TEXT_FIELDS)
        for name, box in self.boxes.items():
            if box.currentText().strip():
                out.append((name, f"{tr(names[name])}: {box.currentText().strip()}"))
        if self.pump.currentData():
            out.append(("pump", self.pump.currentText()))
        if self.year.currentData():
            out.append(("year", f"{tr('Year')} {self.year.currentText()}"))
        elif self.date_from.date() != _NO_DATE or self.date_to.date() != _NO_DATE:
            start = self.date_from.text() if self.date_from.date() != _NO_DATE else "…"
            end = self.date_to.text() if self.date_to.date() != _NO_DATE else "…"
            out.append(("dates", f"{start} – {end}"))
        return out

    def remove(self, name: str) -> None:
        if name in self.boxes:
            self.boxes[name].setEditText("")
        elif name == "pump":
            self.pump.setCurrentIndex(0)
        elif name in ("year", "dates"):
            self._set_dates(None, None)
            self.year.blockSignals(True)
            self.year.setCurrentIndex(0)
            self.year.blockSignals(False)
            self._emit()

    def clear(self) -> None:
        self._loading = True
        for box in self.boxes.values():
            box.setEditText("")
        self.pump.setCurrentIndex(0)
        self.year.setCurrentIndex(0)
        self._set_dates(None, None)
        self._loading = False
        self._emit()

    # ------------------------------------------------------------ เหตุการณ์
    def _on_text(self, name: str) -> None:
        if name == "brand" and not self._loading:           # รุ่นตามยี่ห้อที่เลือก
            self._loading = True
            self._fill(self.boxes["model"], history_search.distinct(self._records, "model", self._where("model")))
            self._loading = False
        self._emit()

    def _on_year(self, _index: int) -> None:
        year = self.year.currentData()
        if year:
            self._set_dates(date(year - 543, 1, 1), date(year - 543, 12, 31))
        elif not self._loading:
            self._set_dates(None, None)
        self._emit()

    def _on_dates(self, _value) -> None:
        year = self.year.currentData()
        if year:                                # แก้วันที่เอง -> ไม่ใช่ทั้งปีแล้ว
            whole = (self.date_from.date() == QDate(year - 543, 1, 1) and self.date_to.date() == QDate(year - 543, 12, 31))
            if not whole:
                self.year.blockSignals(True)
                self.year.setCurrentIndex(0)
                self.year.blockSignals(False)
        if self.date_from.date() != _NO_DATE and self.date_to.date() != _NO_DATE \
                and self.date_from.date() > self.date_to.date():      # กลับด้าน = สลับให้
            start, end = self.date_to.date(), self.date_from.date()
            self._set_dates(start.toPython(), end.toPython())
        self._emit()

    def _set_dates(self, start: date | None, end: date | None) -> None:
        for box, value in ((self.date_from, start), (self.date_to, end)):
            box.blockSignals(True)
            box.setDate(QDate(value) if value else _NO_DATE)
            box.blockSignals(False)

    def _emit(self, *_args) -> None:
        if self._loading:
            return
        count = len(self.chips())
        self.summary.setText(tr("{n} filters in use", n=count) if count else tr("No filters — showing everything"))
        self.changed.emit()


class FilterChips(QWidget):
    """ป้ายตัวกรองที่ใช้อยู่ — กด × เพื่อเอาออก"""
    removed = Signal(str)

    def __init__(self):
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

    def set_chips(self, chips: list[tuple[str, str]]) -> None:
        while self._layout.count():
            widget = self._layout.takeAt(0).widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()            # ปุ่มที่กดอยู่ยังรันสัญญาณ — ลบทีหลัง
        for name, text in chips:
            button = QPushButton(f"{text}   ×")
            button.setProperty("variant", "chip")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(tr("Remove this filter"))
            button.clicked.connect(lambda _=False, n=name: self.removed.emit(n))
            self._layout.addWidget(button)
        self._layout.addStretch(1)
        self.setVisible(bool(chips))
