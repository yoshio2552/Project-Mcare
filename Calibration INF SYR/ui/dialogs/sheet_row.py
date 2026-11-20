"""แก้ข้อมูลของงานใน Google Sheet จากหน้าประวัติ (ผู้ใช้ 2026-11-20: "edit แก้เข้า google sheet ได้ add ข้อมูลในแถวนั้น
คอลัมน์ใหม่ๆ ที่ตั้งหรือเดิมได้")

ต้องเป็นแหล่งแบบ Apps Script (services/sheets.py) · หาแถวด้วยคอลัมน์กุญแจ (เช่น เลขงาน) · ไม่เจอแถว = เพิ่มแถวใหม่ได้
ปุ่ม "เติมจาก DeltaM" ใส่ค่าจากข้อมูลงาน (ผลทดสอบ/วันที่/ผล) ลงคอลัมน์ที่จับคู่ไว้ · คอลัมน์ใหม่ = เพิ่มหัวคอลัมน์ท้ายตาราง
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)

from config.i18n import tr
from services import sheets
from ui.widgets.common import label


class SheetRowDialog(QDialog):
    def __init__(self, parent, job: dict, summary: dict | None = None, settings=None):
        super().__init__(parent)
        self.job, self.summary, self.settings = job, summary or {}, settings
        self.store = sheets.store()
        self.sources = [s for s in self.store.sources if s.enabled and s.writable]
        self.setWindowTitle(tr("Edit in Google Sheet"))
        self.resize(720, 640)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 14)
        root.setSpacing(10)
        root.addWidget(label(tr("Edit in Google Sheet"), "pageTitle"))
        top = QHBoxLayout()
        self.source_box = QComboBox()
        for source in self.sources:
            self.source_box.addItem(source.label(), source.id)
        top.addWidget(label(tr("Sheet"), "fieldLabel"))
        top.addWidget(self.source_box, 1)
        root.addLayout(top)
        self.status = label("", "hint")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self._grid_holder = QWidget()
        self.grid = QGridLayout(self._grid_holder)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(6)
        self.grid.setColumnStretch(1, 1)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(self._grid_holder)
        root.addWidget(area, 1)
        add_row = QHBoxLayout()
        self.new_name = QLineEdit()
        self.new_name.setPlaceholderText(tr("New column name"))
        self.new_value = QLineEdit()
        self.new_value.setPlaceholderText(tr("Value"))
        add = QPushButton(tr("Add column"))
        add_row.addWidget(self.new_name)
        add_row.addWidget(self.new_value, 1)
        add_row.addWidget(add)
        root.addLayout(add_row)
        buttons = QHBoxLayout()
        self.btn_fill = QPushButton(tr("Fill from DeltaM"))
        self.btn_fill.setToolTip(tr("Put this job's values into the matched columns"))
        buttons.addWidget(self.btn_fill)
        buttons.addStretch(1)
        cancel = QPushButton(tr("Cancel"))
        self.btn_save = QPushButton(tr("Save to the sheet"))
        self.btn_save.setProperty("variant", "primary")
        buttons.addWidget(cancel)
        buttons.addWidget(self.btn_save)
        root.addLayout(buttons)
        self._edits: dict[str, QLineEdit] = {}
        self._original: dict[str, str] = {}
        cancel.clicked.connect(self.reject)
        add.clicked.connect(self._add_column)
        self.btn_save.clicked.connect(self._save)
        self.btn_fill.clicked.connect(self._fill_from_job)
        self.source_box.currentIndexChanged.connect(self._load_source)
        if not self.sources:
            self.status.setText(tr("No editable sheet — add an Apps Script source in Settings → Google Sheet."))
            self.btn_save.setEnabled(False)
            self.btn_fill.setEnabled(False)
        else:
            self._load_source()

    @property
    def source(self) -> sheets.SheetSource | None:
        return self.store.source(self.source_box.currentData()) if self.source_box.count() else None

    def _key(self) -> str:
        source = self.source
        header = source.key_header() if source else None
        field_name = source.columns.get(header, "job_no") if source and header else "job_no"
        return str(self.job.get(field_name) or "").strip()

    def _load_source(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._edits.clear()
        source = self.source
        if source is None:
            return
        state = self.store.state(source.id)
        headers = list(state.get("headers") or source.columns.keys())
        key_header = source.key_header()
        key = self._key()
        row = next((r for r in state.get("rows") or [] if key_header and
                    " ".join(str(r.get(key_header) or "").split()).lower() == key.lower()), None)
        self._original = {h: str((row or {}).get(h) or "") for h in headers}
        if not key_header:
            self.status.setText(tr("Choose the key column for this sheet in Settings → Google Sheet first."))
        elif not key:
            self.status.setText(tr("This job has no value for the key column '{column}'.", column=key_header))
        elif row is None:
            self.status.setText(tr("No row with {column} = {key} — saving adds a new row.", column=key_header, key=key))
        else:
            self.status.setText(tr("Row with {column} = {key}. Changed cells are written to the sheet.",
                                   column=key_header, key=key))
        for index, header in enumerate(headers):
            mapped = source.columns.get(header)
            name = header + (f"  ·  {tr(sheets.FIELDS[mapped])}" if mapped in sheets.FIELDS else "")
            edit = QLineEdit(self._original.get(header, ""))
            if header == key_header:
                edit.setReadOnly(True)
                edit.setText(self._original.get(header) or key)
            self.grid.addWidget(label(name, "fieldLabel"), index, 0)
            self.grid.addWidget(edit, index, 1)
            self._edits[header] = edit
        self.btn_save.setEnabled(bool(key_header and key))

    def _add_column(self) -> None:
        name = self.new_name.text().strip()
        if not name or name in self._edits:
            return
        index = self.grid.rowCount()
        edit = QLineEdit(self.new_value.text())
        self.grid.addWidget(label(name + "  ·  " + tr("new column"), "fieldLabel"), index, 0)
        self.grid.addWidget(edit, index, 1)
        self._edits[name] = edit
        self._original.setdefault(name, "")
        self.new_name.clear()
        self.new_value.clear()

    def _fill_from_job(self) -> None:
        source = self.source
        if source is None:
            return
        for header, field_name in source.columns.items():
            value = self.job.get(field_name)
            if header in self._edits and value not in (None, "") and not self._edits[header].isReadOnly():
                self._edits[header].setText(", ".join(value) if isinstance(value, list) else str(value))

    def changes(self) -> dict:
        return {h: e.text() for h, e in self._edits.items()
                if not e.isReadOnly() and e.text() != self._original.get(h, "")}

    def _save(self) -> None:
        source = self.source
        values = self.changes()
        if source is None or not values:
            self.accept()
            return
        key = self._key()
        timeout = self.settings.sheets.timeout_s if self.settings is not None else 15.0
        try:
            row = sheets.write_row(source, key, values, append=True, timeout=timeout)
        except IOError as exc:
            QMessageBox.warning(self, tr("Edit in Google Sheet"), tr("Could not write to the sheet: {error}", error=exc))
            return
        self.store.update_cached(source, source.key_header(), key, values)
        QMessageBox.information(self, tr("Edit in Google Sheet"),
                                tr("Saved {n} cell(s) to row {row}.", n=len(values), row=row))
        self.accept()
