"""ข้อมูลใบรายงาน: สิ่งที่ใบต้องใช้แต่ไม่ใช่ผลวัด — แก้ได้ทุกเมื่อ (หลังทดสอบ / จากหน้าตัวอย่าง) บันทึกในตาราง job_reports

ผลวัดในฐานข้อมูลไม่ถูกแก้ · ค่าเริ่มต้นมาจากข้อมูลงานใน wizard (JobInfo) แล้วทับด้วยที่บันทึกไว้ที่นี่
"""
from __future__ import annotations

import copy

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLineEdit,
                               QPushButton, QVBoxLayout, QWidget)

from config.i18n import tr
from services.report.model import ReportInfo, ReportJob
from ui.widgets.common import Card, label
from ui.widgets.inspection_checks import InspectionChecks

SERVICE_TYPES = [("pm", "Preventive maintenance"), ("repair", "Repair"), ("calib", "Calibration"), ("", "Not set")]


def _number(maximum: float, decimals: int = 0, suffix: str = "") -> QDoubleSpinBox:
    """ช่องตัวเลขที่ว่างได้ (ค่าต่ำสุด = ว่าง แสดงเป็น —)"""
    box = QDoubleSpinBox()
    box.setRange(-1, maximum)
    box.setDecimals(decimals)
    box.setSpecialValueText("—")
    box.setSuffix(suffix)
    box.setValue(-1)
    box.setMinimumWidth(96)
    return box


def _get(box: QDoubleSpinBox) -> float | None:
    return None if box.value() < 0 else box.value()


def _set(box: QDoubleSpinBox, value) -> None:
    box.setValue(-1 if value is None or value == "" else float(value))


class ReportInfoDialog(QDialog):
    def __init__(self, parent: QWidget | None, job: ReportJob):
        super().__init__(parent)
        self.job = job
        self.info: ReportInfo = copy.deepcopy(job.info)
        calibration = job.kind == "calibration"
        self.setWindowTitle(tr("Report data") + " · " + (job.job_no or "—"))
        self.setModal(True)
        self.resize(980, 760)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)
        root.addWidget(label(tr("Report data") + " · " + job.label, "pageTitle"))
        note = label(tr("Things the report needs that are not measured by the program. "
                        "The measured results are not changed."), "pageSubtitle")
        note.setWordWrap(True)
        root.addWidget(note)

        # ---- งาน
        card = Card()
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        self.service = QComboBox()
        for value, text in SERVICE_TYPES:
            self.service.addItem(tr(text), value)
        self.service.setCurrentIndex(max(0, self.service.findData(self.info.service_type)))
        self.contact = QLineEdit(self.info.contact)
        self.phone = QLineEdit(self.info.contact_phone)
        grid.addWidget(label(tr("Contact person"), "fieldLabel"), 0, 0)
        grid.addWidget(self.contact, 0, 1)
        grid.addWidget(label(tr("Contact phone"), "fieldLabel"), 0, 2)
        grid.addWidget(self.phone, 0, 3)
        if not calibration:
            grid.addWidget(label(tr("Service type"), "fieldLabel"), 0, 4)
            grid.addWidget(self.service, 0, 5)
        card.body.addLayout(grid)
        root.addWidget(card)

        # ---- รายการตรวจ
        checks_card = Card()
        self.checks = InspectionChecks(job.pump)
        self.checks.set_values(self.info.checks, self.info.check_notes)
        checks_card.body.addWidget(self.checks)
        root.addWidget(checks_card, 1)

        # ---- การอุดตัน / ไฟฟ้า / ตรวจขั้นสุดท้าย / ตราชั่ง
        card = Card()
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        row = 0
        if calibration:
            grid.addWidget(label(tr("Occlusion alarm"), "cardTitle"), row, 0, 1, 8)
            row += 1
            self.occl_level = QLineEdit(self.info.occl_level)
            self.occl_level.setPlaceholderText(tr("e.g. M"))
            self.occl_level.setMaximumWidth(80)
            self.occl_unit = QComboBox()
            for unit in ("kPa", "mmHg", "psi", "bar"):
                self.occl_unit.addItem(unit, unit)
            self.occl_unit.setCurrentIndex(max(0, self.occl_unit.findData(self.info.occl_unit or "kPa")))
            self.occl_runs = [_number(10000, 1) for _ in range(3)]
            for box, value in zip(self.occl_runs, self.info.occl_runs):
                _set(box, value)
            self.occl_low, self.occl_high = _number(10000, 1), _number(10000, 1)
            _set(self.occl_low, self.info.occl_low)
            _set(self.occl_high, self.info.occl_high)
            grid.addWidget(label(tr("Level set"), "fieldLabel"), row, 0)
            grid.addWidget(self.occl_level, row, 1)
            grid.addWidget(self.occl_unit, row, 2)
            runs = QHBoxLayout()
            for index, box in enumerate(self.occl_runs, 1):
                runs.addWidget(label(tr("Run {n}", n=index), "fieldLabel"))
                runs.addWidget(box)
            holder = QWidget()
            holder.setLayout(runs)
            runs.setContentsMargins(0, 0, 0, 0)
            grid.addWidget(holder, row, 3, 1, 3)
            row += 1
            grid.addWidget(label(tr("Manufacturer's limit"), "fieldLabel"), row, 0)
            limits = QHBoxLayout()
            limits.addWidget(self.occl_low)
            limits.addWidget(label("–", "fieldLabel"))
            limits.addWidget(self.occl_high)
            limits.addStretch(1)
            holder = QWidget()
            holder.setLayout(limits)
            limits.setContentsMargins(0, 0, 0, 0)
            grid.addWidget(holder, row, 1, 1, 3)
            row += 1
        grid.addWidget(label(tr("Electrical safety"), "cardTitle"), row, 0, 1, 8)
        row += 1
        self.supply, self.leak = _number(1000, 0, " V"), _number(100000, 0, " µA")
        _set(self.supply, self.info.supply_v)
        _set(self.leak, self.info.leak_ua)
        grid.addWidget(label(tr("Supply voltage"), "fieldLabel"), row, 0)
        grid.addWidget(self.supply, row, 1)
        grid.addWidget(label(tr("Equipment leakage current"), "fieldLabel"), row, 2)
        grid.addWidget(self.leak, row, 3)
        self.leak_note = label(tr("Limit {v:g} µA", v=job.options.leak_limit_ua), "hint")
        grid.addWidget(self.leak_note, row, 4, 1, 2)
        row += 1
        self.whole = QCheckBox(tr("Whole unit checked"))
        self.whole.setChecked(bool(self.info.whole_checked))
        self.label_box = QCheckBox(tr("Inspection label attached"))
        self.label_box.setChecked(bool(self.info.label_attached))
        if not calibration:
            grid.addWidget(self.whole, row, 0, 1, 2)
            grid.addWidget(self.label_box, row, 2, 1, 2)
            row += 1
        if calibration:
            grid.addWidget(label(tr("Balance check before use"), "cardTitle"), row, 0, 1, 8)
            row += 1
            self.weight, self.reading = _number(10000, 3, " g"), _number(10000, 3, " g")
            _set(self.weight, self.info.check_weight_g)
            _set(self.reading, self.info.check_reading_g)
            grid.addWidget(label(tr("Test weight"), "fieldLabel"), row, 0)
            grid.addWidget(self.weight, row, 1)
            grid.addWidget(label(tr("Balance reading"), "fieldLabel"), row, 2)
            grid.addWidget(self.reading, row, 3)
            row += 1
        grid.setColumnStretch(7, 1)
        card.body.addLayout(grid)
        root.addWidget(card)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(tr("Cancel"))
        self.btn_save = QPushButton(tr("Save"))
        self.btn_save.setProperty("variant", "primary")
        buttons.addWidget(cancel)
        buttons.addWidget(self.btn_save)
        root.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._save)

    def result_info(self) -> ReportInfo:
        info = self.info
        info.service_type = self.service.currentData() or ""
        info.contact, info.contact_phone = self.contact.text().strip(), self.phone.text().strip()
        info.checks, info.check_notes = self.checks.values(), self.checks.notes()
        info.supply_v, info.leak_ua = _get(self.supply), _get(self.leak)
        info.whole_checked, info.label_attached = self.whole.isChecked(), self.label_box.isChecked()
        if self.job.kind == "calibration":
            info.occl_level = self.occl_level.text().strip()
            info.occl_unit = self.occl_unit.currentData()
            info.occl_runs = [_get(box) for box in self.occl_runs]
            info.occl_low, info.occl_high = _get(self.occl_low), _get(self.occl_high)
            info.check_weight_g, info.check_reading_g = _get(self.weight), _get(self.reading)
        return info

    def _save(self) -> None:
        self.result_info()
        self.accept()
