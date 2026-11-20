"""ข้อมูลใบรายงาน: สิ่งที่ใบต้องใช้แต่ไม่ใช่ผลวัด — แก้ได้ทุกเมื่อ (หลังทดสอบ / จากหน้าตัวอย่าง) บันทึกในข้อมูลงานชุดเดียวของงาน (ตาราง jobs)

ผลวัดในฐานข้อมูลไม่ถูกแก้ · ค่าเริ่มต้นมาจากข้อมูลงานใน wizard (JobInfo) แล้วทับด้วยที่บันทึกไว้ที่นี่

จัดเป็นแท็บ (ผู้ใช้ 2026-11-20: "ยัดรวมกันยาวๆ ควรแยกแท็บประเภทอย่างมืออาชีพ + โหมด Advanced"):
    งานและเครื่อง   เลขงาน โรงพยาบาล จังหวัด หน่วยงาน S/N ครุภัณฑ์ ผู้ทดสอบ + หมายเหตุ
    บริการและผู้ติดต่อ  ประเภทงาน (ติ๊กแก้ได้) ผู้ติดต่อ เบอร์โทร
    ผลตรวจรายข้อ     รายการตรวจของใบ
    ค่าที่วัดด้วยมือ    การอุดตัน ไฟฟ้า ตรวจขั้นสุดท้าย (+ ตุ้มน้ำหนักตรวจตราชั่ง — Calibration)
    ขั้นสูง (ติ๊ก "แสดงช่องขั้นสูง")  ยี่ห้อชุดสาย อุปกรณ์ที่มากับเครื่อง ตราชั่งมาตรฐาน — แก้นานๆ ครั้ง
ยี่ห้อ/รุ่น/ชุดสาย (รุ่น) แก้ไม่ได้ที่นี่ = กุญแจโปรไฟล์ปั๊ม (แสดงให้เห็นอย่างเดียว)
"""
from __future__ import annotations

import copy

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QTabWidget,
    QVBoxLayout, QWidget,
)

from config.i18n import tr
from services.report.model import SERVICE_KINDS, ReportInfo, ReportJob
from ui.widgets.common import Card, label
from ui.widgets.inspection_checks import InspectionChecks
from ui.widgets.report_extras import FIELDS, ReportExtras, get, number, put

DEVICE_FIELDS = [("job_no", "Job no."), ("site", "Hospital / site"), ("province", "Province"),
                 ("department", "Department"), ("serial_no", "Serial no."), ("asset_id", "Asset ID"), ("operator", "Operator")]
# ช่องขั้นสูง (แก้นานๆ ครั้ง) — แสดงเมื่อติ๊ก "แสดงช่องขั้นสูง"
ADVANCED_FIELDS = [("accessory_brand", "IV set brand"), ("balance_id", "Balance ID")]
EXTRA_FIELDS = FIELDS


def _page(*widgets, stretch: bool = True) -> QScrollArea:
    holder = QWidget()
    box = QVBoxLayout(holder)
    box.setContentsMargins(2, 12, 8, 8)
    box.setSpacing(12)
    for widget in widgets:
        box.addWidget(widget)
    if stretch:
        box.addStretch(1)
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.Shape.NoFrame)
    area.setWidget(holder)
    return area


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

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setProperty("tabsStyle", "settings")
        root.addWidget(self.tabs, 1)

        # ---- แท็บ 1: งานและเครื่อง — แก้ครั้งเดียว ใช้กับทุก rate ของงาน
        card = Card(tr("Job and device"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        self.device_edits: dict[str, QLineEdit] = {}
        for index, (name, text) in enumerate(DEVICE_FIELDS):
            edit = QLineEdit(str(job.job.get(name) or ""))
            self.device_edits[name] = edit
            grid.addWidget(label(tr(text), "fieldLabel"), index // 2, (index % 2) * 2)
            grid.addWidget(edit, index // 2, (index % 2) * 2 + 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        card.body.addLayout(grid)
        fixed = " · ".join(p for p in (job.job.get("brand"), job.job.get("model"), job.job.get("accessory")) if p)
        note_fixed = label(tr("Brand, model and IV set cannot be changed here: {device}", device=fixed or "—"), "hint")
        note_fixed.setWordWrap(True)
        card.body.addWidget(note_fixed)
        remark = Card(tr("Remark"))
        self.notes = QPlainTextEdit(str(job.job.get("notes") or ""))
        self.notes.setPlaceholderText(tr("Remarks about this job (also shown in History)"))
        self.notes.setMaximumHeight(120)
        remark.body.addWidget(self.notes)

        # ช่องขั้นสูง
        self.advanced = Card(tr("Advanced"))
        adv = QGridLayout()
        adv.setHorizontalSpacing(12)
        for index, (name, text) in enumerate(ADVANCED_FIELDS):
            edit = QLineEdit(str(job.job.get(name) or ""))
            self.device_edits[name] = edit
            adv.addWidget(label(tr(text), "fieldLabel"), index, 0)
            adv.addWidget(edit, index, 1)
        self.accessories = QLineEdit(", ".join(job.job.get("accessories") or []))
        self.accessories.setPlaceholderText(tr("Comma separated"))
        adv.addWidget(label(tr("Accessories"), "fieldLabel"), len(ADVANCED_FIELDS), 0)
        adv.addWidget(self.accessories, len(ADVANCED_FIELDS), 1)
        adv.setColumnStretch(1, 1)
        self.advanced.body.addLayout(adv)
        hint = label(tr("Rarely changed. Parts replaced and warranty claims are kept with the warranty history and "
                        "are not edited here."), "hint")
        hint.setWordWrap(True)
        self.advanced.body.addWidget(hint)
        self.tabs.addTab(_page(card, remark, self.advanced), tr("Job and device"))

        # ---- แท็บ 2: บริการและผู้ติดต่อ
        card = Card(tr("Service and contact"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
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
        self.contact = QLineEdit(self.info.contact)
        self.phone = QLineEdit(self.info.contact_phone)
        grid.addWidget(label(tr("Service type"), "fieldLabel"), 0, 0)
        grid.addLayout(boxes, 0, 1, 1, 3)
        grid.addWidget(label(tr("Contact person"), "fieldLabel"), 1, 0)
        grid.addWidget(self.contact, 1, 1)
        grid.addWidget(label(tr("Contact phone"), "fieldLabel"), 1, 2)
        grid.addWidget(self.phone, 1, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        card.body.addLayout(grid)
        auto = label(tr("The service type is set automatically from the mode and the parts replaced — "
                        "untick or tick to change it on this report."), "hint")
        auto.setWordWrap(True)
        card.body.addWidget(auto)
        self.tabs.addTab(_page(card), tr("Service and contact"))

        # ---- แท็บ 3: ผลตรวจรายข้อ
        checks_card = Card(tr("Checklist results for the report"))
        self.checks = InspectionChecks(job.pump)
        self.checks.set_values(self.info.checks, self.info.check_notes)
        checks_card.body.addWidget(self.checks)
        self.tabs.addTab(_page(checks_card, stretch=False), tr("Checklist"))

        # ---- แท็บ 4: ค่าที่วัดด้วยมือ (+ ตุ้มน้ำหนัก — Calibration)
        card = Card(tr("Measured by hand"))
        self.extras = ReportExtras(job.options.leak_limit_ua, ticks_default=False)
        self.extras.set_values({name: getattr(self.info, name) for name in EXTRA_FIELDS})
        card.body.addWidget(self.extras)
        widgets = [card]
        if calibration:
            balance = Card(tr("Balance check before use"))
            grid = QGridLayout()
            grid.setHorizontalSpacing(10)
            self.weight, self.reading = number(10000, 3, " g"), number(10000, 3, " g")
            put(self.weight, self.info.check_weight_g)
            put(self.reading, self.info.check_reading_g)
            grid.addWidget(label(tr("Test weight"), "fieldLabel"), 0, 0)
            grid.addWidget(self.weight, 0, 1)
            grid.addWidget(label(tr("Balance reading"), "fieldLabel"), 0, 2)
            grid.addWidget(self.reading, 0, 3)
            grid.setColumnStretch(5, 1)
            balance.body.addLayout(grid)
            widgets.append(balance)
        self.tabs.addTab(_page(*widgets), tr("Measured values"))

        buttons = QHBoxLayout()
        self.show_advanced = QCheckBox(tr("Show advanced fields"))
        self.show_advanced.toggled.connect(self.advanced.setVisible)
        self.advanced.setVisible(False)
        buttons.addWidget(self.show_advanced)
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
        values["notes"] = self.notes.toPlainText().strip()
        values["accessories"] = [p.strip() for p in self.accessories.text().split(",") if p.strip()]
        from services.report.model import auto_service_types
        chosen = [key for key, box in self.service_boxes.items() if box.isChecked()]
        auto = auto_service_types(self.job.kind, self.job.job.get("parts_replaced"))
        values["service_kinds"] = chosen if set(chosen) != auto else []      # เหมือนที่คิดเอง = ว่าง (คิดเอง)
        return values

    def _save(self) -> None:
        self.result_info()
        self.accept()
