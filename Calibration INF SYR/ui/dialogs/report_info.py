"""ข้อมูลใบรายงาน: สิ่งที่ใบต้องใช้แต่ไม่ใช่ผลวัด — แก้ได้ทุกเมื่อ (หลังทดสอบ / จากหน้าตัวอย่าง) บันทึกในข้อมูลงานชุดเดียวของงาน (ตาราง jobs)

ผลวัดในฐานข้อมูลไม่ถูกแก้ · ค่าเริ่มต้นมาจากข้อมูลงานใน wizard (JobInfo) แล้วทับด้วยที่บันทึกไว้ที่นี่
"""
from __future__ import annotations

import copy

from PySide6.QtWidgets import QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from config.i18n import tr
from services.report.model import SERVICE_KINDS, ReportInfo, ReportJob
from ui.widgets.common import Card, label
from ui.widgets.inspection_checks import InspectionChecks
from ui.widgets.report_extras import FIELDS, ReportExtras, get, number, put

DEVICE_FIELDS = [("job_no", "Job no."), ("site", "Hospital / site"), ("province", "Province"),
                 ("department", "Department"), ("serial_no", "Serial no."), ("asset_id", "Asset ID"), ("operator", "Operator")]
EXTRA_FIELDS = FIELDS


class ReportInfoDialog(QDialog):
    def __init__(self, parent: QWidget | None, job: ReportJob):
        super().__init__(parent)
        self.job = job
        self.info: ReportInfo = copy.deepcopy(job.info)
        calibration = job.kind == "calibration"
        self.setWindowTitle(tr("Report data") + " · " + (job.job_no or "—"))
        self.setModal(True)
        self.resize(980, 760)
        from ui.dialogs.report_preview import fit_to_screen
        fit_to_screen(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)
        root.addWidget(label(tr("Report data") + " · " + job.label, "pageTitle"))
        note = label(tr("Things the report needs that are not measured by the program. "
                        "The measured results are not changed."), "pageSubtitle")
        note.setWordWrap(True)
        root.addWidget(note)

        # ---- ข้อมูลเครื่องและงาน: แก้ที่นี่ครั้งเดียว ใช้กับทุก rate ของงาน (ตาราง jobs) — ยี่ห้อ/รุ่น/ชุดสายแก้ไม่ได้ (กุญแจโปรไฟล์ปั๊ม)
        card = Card()
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        self.device_edits: dict[str, QLineEdit] = {}
        for index, (name, text) in enumerate(DEVICE_FIELDS):
            edit = QLineEdit(str(job.job.get(name) or ""))
            self.device_edits[name] = edit
            grid.addWidget(label(tr(text), "fieldLabel"), index // 4, (index % 4) * 2)
            grid.addWidget(edit, index // 4, (index % 4) * 2 + 1)
        fixed = " · ".join(p for p in (job.job.get("brand"), job.job.get("model"), job.job.get("accessory")) if p)
        note_fixed = label(tr("Brand, model and IV set cannot be changed here: {device}", device=fixed or "—"), "hint")
        grid.addWidget(note_fixed, (len(DEVICE_FIELDS) + 3) // 4, 0, 1, 8)
        card.body.addLayout(grid)
        root.addWidget(card)

        # ---- งาน: ประเภทงาน (ตั้งให้เอง แก้ได้ — ผู้ใช้ 2026-11-20) + ผู้ติดต่อ
        card = Card()
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        kinds = job.service_types()
        self.service_boxes: dict[str, QCheckBox] = {}
        names = {"pm": "Preventive maintenance", "repair": "Repair", "calib": "Calibration service"}
        boxes = QHBoxLayout()
        boxes.setSpacing(18)
        for key in SERVICE_KINDS:
            box = QCheckBox(tr(names[key]))
            box.setChecked(key in kinds)
            self.service_boxes[key] = box
            boxes.addWidget(box)
        boxes.addStretch(1)
        grid.addWidget(label(tr("Service type"), "fieldLabel"), 1, 0)
        grid.addLayout(boxes, 1, 1, 1, 3)
        self.contact = QLineEdit(self.info.contact)
        self.phone = QLineEdit(self.info.contact_phone)
        grid.addWidget(label(tr("Contact person"), "fieldLabel"), 0, 0)
        grid.addWidget(self.contact, 0, 1)
        grid.addWidget(label(tr("Contact phone"), "fieldLabel"), 0, 2)
        grid.addWidget(self.phone, 0, 3)
        card.body.addLayout(grid)
        root.addWidget(card)

        # ---- รายการตรวจ
        checks_card = Card()
        self.checks = InspectionChecks(job.pump)
        self.checks.set_values(self.info.checks, self.info.check_notes)
        checks_card.body.addWidget(self.checks)
        root.addWidget(checks_card, 1)

        # ---- การอุดตัน / ไฟฟ้า / ตรวจขั้นสุดท้าย (ชุดเดียวกับ wizard ขั้นที่ 2) + ตุ้มน้ำหนัก (Calibration)
        card = Card()
        self.extras = ReportExtras(job.options.leak_limit_ua, ticks_default=False)
        self.extras.set_values({name: getattr(self.info, name) for name in EXTRA_FIELDS})
        card.body.addWidget(self.extras)
        if calibration:
            grid = QGridLayout()
            grid.setHorizontalSpacing(10)
            grid.addWidget(label(tr("Balance check before use"), "cardTitle"), 0, 0, 1, 6)
            self.weight, self.reading = number(10000, 3, " g"), number(10000, 3, " g")
            put(self.weight, self.info.check_weight_g)
            put(self.reading, self.info.check_reading_g)
            grid.addWidget(label(tr("Test weight"), "fieldLabel"), 1, 0)
            grid.addWidget(self.weight, 1, 1)
            grid.addWidget(label(tr("Balance reading"), "fieldLabel"), 1, 2)
            grid.addWidget(self.reading, 1, 3)
            grid.setColumnStretch(5, 1)
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
        info.contact, info.contact_phone = self.contact.text().strip(), self.phone.text().strip()
        info.checks, info.check_notes = self.checks.values(), self.checks.notes()
        for name, value in self.extras.values().items():
            setattr(info, name, value)
        if self.job.kind == "calibration":
            info.check_weight_g, info.check_reading_g = get(self.weight), get(self.reading)
        return info

    def device_values(self) -> dict:
        values = {name: edit.text().strip() for name, edit in self.device_edits.items()}
        from services.report.model import auto_service_types
        chosen = [key for key, box in self.service_boxes.items() if box.isChecked()]
        auto = auto_service_types(self.job.kind, self.job.job.get("parts_replaced"))
        values["service_kinds"] = chosen if set(chosen) != auto else []      # เหมือนที่คิดเอง = ว่าง (คิดเอง)
        return values

    def _save(self) -> None:
        self.result_info()
        self.accept()
