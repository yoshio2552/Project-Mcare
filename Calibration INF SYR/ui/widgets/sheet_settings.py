"""ตั้งค่า → Google Sheet (ผู้ใช้ 2026-11-20): หลายลิงก์ · จับคู่คอลัมน์ · ทดสอบการเชื่อมต่อ · ดึงเดี๋ยวนี้ · โค้ด Apps Script

    ┌ แหล่งข้อมูล ───────────────────────────────────────────────────────────────┐
    │ ชื่อ        ชนิด            แถว   ดึงล่าสุด          สถานะ                      │
    │ งานปี 69    อ่าน+แก้ (Script) 412  2026-11-20 14:02   ✓                        │
    │ [เพิ่ม] [แก้] [ลบ]                                   [ดึงทุกแหล่งเดี๋ยวนี้]       │
    └──────────────────────────────────────────────────────────────────────────────┘
ค่าจริงเก็บใน settings.sheets.sources (บันทึกตอนกด Save ของหน้าตั้งค่า) · ข้อมูลที่ดึงมา = data/sheets_cache.json
"""
from __future__ import annotations

import copy

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox, QPlainTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from config.i18n import tr
from services import sheets
from ui.widgets.common import Card, label

KINDS = [("csv", "Read only — shared / published link (CSV)"), ("script", "Read and edit — Apps Script web app")]


class _Bridge(QObject):
    done = Signal(object)


class SourceDialog(QDialog):
    """แก้ 1 แหล่ง: ชื่อ ชนิด ลิงก์ แท็บ token คอลัมน์กุญแจ + ตารางจับคู่คอลัมน์ (ดึงหัวคอลัมน์จากลิงก์ได้)"""

    def __init__(self, parent, source: sheets.SheetSource, timeout: float = 15.0):
        super().__init__(parent)
        self.source = copy.deepcopy(source)
        self._timeout = timeout
        self._headers: list[str] = list(self.source.columns.keys())
        self.setWindowTitle(tr("Google Sheet source"))
        self.resize(760, 680)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 14)
        root.setSpacing(10)
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        self.name = QLineEdit(self.source.name)
        self.kind = QComboBox()
        for key, text in KINDS:
            self.kind.addItem(tr(text), key)
        self.kind.setCurrentIndex(max(0, self.kind.findData(self.source.kind)))
        self.url = QLineEdit(self.source.url)
        self.url.setPlaceholderText(tr("Paste the Google Sheet link (or the Apps Script /exec link)"))
        self.sheet = QLineEdit(self.source.sheet)
        self.sheet.setPlaceholderText(tr("Blank = first tab"))
        self.token = QLineEdit(self.source.token)
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.key = QComboBox()
        self.key.setEditable(True)
        self.enabled = QCheckBox(tr("Use this source"))
        self.enabled.setChecked(self.source.enabled)
        form.addRow(tr("Name"), self.name)
        form.addRow(tr("Type"), self.kind)
        form.addRow(tr("Link"), self.url)
        form.addRow(tr("Tab name"), self.sheet)
        form.addRow(tr("Secret token"), self.token)
        form.addRow(tr("Key column (to find the row when editing)"), self.key)
        form.addRow("", self.enabled)
        root.addLayout(form)
        self.help = label("", "hint")
        self.help.setWordWrap(True)
        root.addWidget(self.help)

        bar = QHBoxLayout()
        self.btn_test = QPushButton(tr("Test and load the columns"))
        self.btn_guess = QPushButton(tr("Match columns automatically"))
        self.btn_script = QPushButton(tr("Copy the Apps Script code"))
        bar.addWidget(self.btn_test)
        bar.addWidget(self.btn_guess)
        bar.addStretch(1)
        bar.addWidget(self.btn_script)
        root.addLayout(bar)
        self.status = label("", "hint")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        root.addWidget(label(tr("Columns: which DeltaM field each sheet column fills (blank = not used)"), "fieldLabel"))
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([tr("Sheet column"), tr("DeltaM field")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        root.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(tr("Cancel"))
        ok = QPushButton(tr("Save"))
        ok.setProperty("variant", "primary")
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        root.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self._accept)
        self.kind.currentIndexChanged.connect(self._on_kind)
        self.btn_test.clicked.connect(self._test)
        self.btn_guess.clicked.connect(self._guess)
        self.btn_script.clicked.connect(self._copy_script)
        self._fill_table()
        self._on_kind()

    def _on_kind(self) -> None:
        script = self.kind.currentData() == "script"
        self.sheet.setEnabled(script)
        self.token.setEnabled(script)
        self.btn_script.setVisible(script)
        self.help.setText(tr("Apps Script: paste the code into the sheet (Extensions → Apps Script), deploy it as a web "
                             "app (execute as me, access: anyone), then paste the /exec link and the same token here. "
                             "DeltaM can then edit rows and add new columns.") if script else
                          tr("Read only: share the sheet as 'Anyone with the link can view' (or File → Share → Publish "
                             "to web → CSV) and paste the link. No Google account is stored in DeltaM."))

    def _fill_table(self) -> None:
        choices = [("", "—")] + [(key, tr(text)) for key, text in sheets.FIELDS.items()]
        self.table.setRowCount(len(self._headers))
        for row, header in enumerate(self._headers):
            item = QTableWidgetItem(header)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 0, item)
            box = QComboBox()
            for key, text in choices:
                box.addItem(text, key)
            box.setCurrentIndex(max(0, box.findData(self.source.columns.get(header, ""))))
            self.table.setCellWidget(row, 1, box)
        current = self.key.currentText() or self.source.key_column
        self.key.clear()
        self.key.addItem("")
        self.key.addItems(self._headers)
        self.key.setCurrentText(current)

    def _columns(self) -> dict:
        out = {}
        for row, header in enumerate(self._headers):
            box = self.table.cellWidget(row, 1)
            if box is not None and box.currentData():
                out[header] = box.currentData()
        return out

    def _read(self) -> sheets.SheetSource:
        s = self.source
        s.name, s.kind, s.url = self.name.text().strip(), self.kind.currentData(), self.url.text().strip()
        s.sheet, s.token, s.key_column = self.sheet.text().strip(), self.token.text(), self.key.currentText().strip()
        s.enabled = self.enabled.isChecked()
        s.columns = self._columns()
        return s

    def _test(self) -> None:
        source = self._read()
        self.status.setText(tr("Connecting…"))
        self.repaint()
        try:
            headers, rows = sheets.fetch(source, self._timeout)
        except IOError as exc:
            self.status.setText("✗ " + tr("Could not read the sheet: {error}", error=exc))
            return
        self._headers = headers
        if not source.columns:
            self.source.columns = sheets.guess_columns(headers)
        self._fill_table()
        self.status.setText("✓ " + tr("{n} rows · {c} columns", n=len(rows), c=len(headers)))

    def _guess(self) -> None:
        self.source.columns = sheets.guess_columns(self._headers)
        self._fill_table()

    def _copy_script(self) -> None:
        QGuiApplication.clipboard().setText(sheets.APPS_SCRIPT)
        self.status.setText(tr("The Apps Script code is on the clipboard — change TOKEN in the first lines."))

    def _accept(self) -> None:
        source = self._read()
        if not source.url:
            QMessageBox.information(self, tr("Google Sheet source"), tr("Paste the link first."))
            return
        if not source.name:
            source.name = tr("Sheet {n}", n=source.id[-4:])
        self.accept()


class SheetSettings(QWidget):
    """รายการแหล่ง + ปุ่ม (ฝังในแท็บ Google Sheet ของหน้าตั้งค่า)"""

    def __init__(self):
        super().__init__()
        self._sources: list[sheets.SheetSource] = []
        self._timeout = 15.0
        self._settings = None
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        card = Card(tr("Sheet sources"))
        intro = label(tr("Rows are matched to jobs by Job no., serial no. or asset ID. Several links with the same or "
                         "different columns can be used together."), "hint")
        intro.setWordWrap(True)
        card.body.addWidget(intro)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([tr("Name"), tr("Type"), tr("Rows"), tr("Last read"), tr("Status")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(180)
        card.body.addWidget(self.table)
        buttons = QHBoxLayout()
        self.btn_add = QPushButton(tr("Add"))
        self.btn_edit = QPushButton(tr("Edit"))
        self.btn_remove = QPushButton(tr("Remove"))
        self.btn_sync = QPushButton(tr("Read all sources now"))
        self.btn_sync.setProperty("variant", "primary")
        for button in (self.btn_add, self.btn_edit, self.btn_remove):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_sync)
        card.body.addLayout(buttons)
        self.status = label("", "hint")
        self.status.setWordWrap(True)
        card.body.addWidget(self.status)
        box.addWidget(card)
        box.addStretch(1)
        self._bridge = _Bridge()
        self._bridge.done.connect(self._on_synced)
        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_remove.clicked.connect(self._remove)
        self.btn_sync.clicked.connect(self._sync)
        self.table.cellDoubleClicked.connect(lambda *_: self._edit())

    # ------------------------------------------------------------ ค่าตั้ง
    def load(self, settings) -> None:
        self._settings = settings
        self._timeout = settings.sheets.timeout_s
        self._sources = [sheets.SheetSource.from_dict(s) for s in settings.sheets.sources if isinstance(s, dict)]
        self._refresh()

    def store(self, settings) -> None:
        settings.sheets.sources = sheets.source_dicts(self._sources)
        sheets.store().configure(settings.sheets.sources)

    def _refresh(self) -> None:
        store = sheets.store()
        kinds = dict(KINDS)
        self.table.setRowCount(len(self._sources))
        for row, source in enumerate(self._sources):
            state = store.state(source.id)
            status = state.get("status", "")
            values = [source.label(), tr("Read and edit") if source.writable else tr("Read only"),
                      str(state.get("rows_count", "—")), state.get("synced_at", "—"),
                      ("✓" if status == "ok" else status) if source.enabled else tr("Not used")]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(kinds.get(source.kind, "") if col == 1 else value)
                self.table.setItem(row, col, item)

    def _current(self) -> int:
        return self.table.currentRow()

    def _add(self) -> None:
        dialog = SourceDialog(self, sheets.SheetSource.from_dict({}), self._timeout)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._sources.append(dialog.source)
            self._refresh()
            self.status.setText(tr("Press Save at the top to keep the change."))

    def _edit(self) -> None:
        index = self._current()
        if not 0 <= index < len(self._sources):
            return
        dialog = SourceDialog(self, self._sources[index], self._timeout)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._sources[index] = dialog.source
            self._refresh()
            self.status.setText(tr("Press Save at the top to keep the change."))

    def _remove(self) -> None:
        index = self._current()
        if not 0 <= index < len(self._sources):
            return
        source = self._sources[index]
        if QMessageBox.question(self, tr("Remove"), tr("Remove the source '{name}'? The sheet itself is not changed.",
                                                       name=source.label())) == QMessageBox.StandardButton.Yes:
            del self._sources[index]
            self._refresh()

    def _sync(self) -> None:
        if self._settings is None:
            return
        temp = copy.deepcopy(self._settings)
        temp.sheets.sources = sheets.source_dicts(self._sources)
        self.btn_sync.setEnabled(False)
        self.status.setText(tr("Reading the sheets…"))
        sheets.sync_in_background(temp, self._bridge.done.emit)

    def _on_synced(self, results) -> None:
        self.btn_sync.setEnabled(True)
        for source in self._sources:                # คอลัมน์ที่เดาให้ตอนดึงครั้งแรก
            fresh = sheets.store().source(source.id)
            if fresh is not None and not source.columns and fresh.columns:
                source.columns = dict(fresh.columns)
        self._refresh()
        self.status.setText(" · ".join(f"{name}: {text}" for name, text in results) or tr("No sources to read"))
