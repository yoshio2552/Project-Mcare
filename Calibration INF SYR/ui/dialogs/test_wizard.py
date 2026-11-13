"""TestWizard: สร้างแผนทดสอบ 4 ขั้น
    1) ข้อมูลงาน/เครื่อง — พิมพ์ค้นเครื่องที่เคยทดสอบแล้วดึงข้อมูลมาเติมได้
    2) ตรวจเครื่อง — อุปกรณ์ที่มากับเครื่อง, อะไหล่ที่เปลี่ยน (เลือกจากรายการกลางในหน้าตั้งค่า)
    3) เลือกโหมด: Calibration / Inspection / Quick Test
    4) ตั้งค่าการวัดของโหมดนั้น (rate, วิธีจับ, เงื่อนไขจบ, วิธีเริ่มวัด, ขนาดหน้าต่าง)
ผลลัพธ์คือ TestPlan (อ่านจาก .plan หลัง dialog ปิดแบบ accept)

เพิ่มช่องกรอกข้อมูลงาน: เพิ่ม field ใน core.models.JobInfo แล้วเพิ่ม 1 บรรทัดใน JOB_FIELDS
ทุกช่อง (ยกเว้นหมายเหตุ) เสนอค่าจากงานที่เคยบันทึกเป็นตัวอักษรจาง — กด Tab/Enter เพื่อรับ (services.job_suggestions)

หน้าต่างจับรอบปั๊ม (เฉพาะวิธีที่ใช้รอบปั๊ม): ทุกแถว rate แสดงค่าของตัวเอง (คาบ · regression · n̄ · จุดต่อรอบ · ที่มา)
กด "สร้างการทดสอบ" แล้วรุ่นนี้ยังไม่ได้สอบเทียบที่ rate ใด / จุดต่อรอบน้อย -> CalibrationPromptDialog
(วิธีจับตามเวลาไม่ถาม — ไม่ได้ใช้รอบปั๊ม)
"""
from __future__ import annotations

import copy

from PySide6.QtCore import QStringListModel, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox, QCompleter, QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from config.constants import (
    DEFAULT_STRATEGY, DEFAULT_TOLERANCE_PCT, MODE_DEFAULTS, RATE_PRESETS, WINDOW_CHOICES_S,
)
from config.i18n import tr
from config.settings import AppSettings
from config.provinces import PROVINCES
from core.models import (
    JOB_PREFIXES, EndMode, JobInfo, PumpType, RunMode, StartMode, StepConfig, TestPlan, job_no_for_pump,
    pump_from_job_no,
)
from core.warranty import summarize
from core.strategies import STRATEGIES
from config.settings import prerun_group
from ui.dialogs.accessory_change import ask_accessory_change
from ui.dialogs.calibration_prompt import CalibrationPromptDialog
from ui.dialogs.part_history import PartHistoryDialog
from ui.dialogs.prerun_criteria import PrerunCriteriaDialog
from ui.dialogs.recalibrate import RecalibrateDialog
from ui.theme import Color
from ui.widgets.common import Card, divider, int_box, label, number_box
from services.job_suggestions import NO_SUGGESTIONS, JobSuggester
from services.window_plan import FIT_TEXT, plan_windows, sample_period_estimate
from ui.widgets.checklist import Checklist
from ui.widgets.pump_type import PumpBadge, PumpBar, PumpTypeSelector, pump_name
from ui.widgets.smart_edit import SmartLineEdit

# (ชื่อ field ใน JobInfo, ป้าย, ข้อความตัวอย่าง, คอลัมน์)  — "top" = แถวงานบนสุด (เลขงาน · โรงพยาบาล · จังหวัด)
# รุ่นอยู่เหนือยี่ห้อ: กรอกรุ่นแล้วระบบเสนอยี่ห้อ + ชนิดเครื่องที่รุ่นนี้เคยบันทึก (ผู้ใช้ 2026-11-13)
# รหัสตราชั่งย้ายไปหน้าตั้งค่า (ตราชั่งมาตรฐาน) — บันทึกลงผลให้อัตโนมัติ
JOB_FIELDS = [
    ("job_no", "Job no.", "MCI… = Infusion · MCS… = Syringe", "top"),
    ("site", "Hospital / site", "", "top"),
    ("province", "Province", "", "top"),
    ("model", "Model", "Type the model — brand and pump type follow", 0),
    ("brand", "Brand", "", 0),
    ("serial_no", "Serial no.", "", 0),
    ("asset_id", "Asset ID", "", 0),
    ("department", "Department", "", 0),
    ("operator", "Operator", "", 0),
    ("accessory", "IV set", "Model — part of the pump profile", 1),
    ("accessory_brand", "IV set brand", "", 1),
    ("temperature_c", "Liquid temperature (°C)", "Water density for g → ml", 1),
    ("humidity_pct", "Humidity (%RH)", "Air buoyancy — blank = Settings", 1),
    ("air_temp_c", "Air temperature (°C)", "Blank = liquid temperature", 1),
    ("pressure_hpa", "Air pressure (hPa)", "Blank = Settings", 1),
    ("notes", "Notes", "", 1),
]
# ป้ายของช่องชุดสายตามชนิดเครื่อง: (รุ่น, ยี่ห้อ)
ACCESSORY_LABELS = {"infusion": ("IV set", "IV set brand"), "syringe": ("Syringe used", "Syringe brand")}
_NUMERIC_FIELDS = {"temperature_c", "humidity_pct", "air_temp_c", "pressure_hpa"}
_DEVICE_FIELDS = ("brand", "model", "serial_no", "asset_id", "department", "accessory", "accessory_brand",
                  "site", "province")

SEARCH_SCOPES = [("all", "All"), ("job", "Job"), ("serial", "Serial"), ("code", "Code")]

MODES = [
    (RunMode.CALIBRATION, "Calibration", "Several flow rates in sequence. A result is recorded for every rate."),
    (RunMode.INSPECTION, "Inspection", "One flow rate, full-length test against the tolerance."),
    (RunMode.QUICK_TEST, "Quick Test", "A short check to see that the pump and balance behave as expected."),
]
START_MODES = [
    (StartMode.IMMEDIATE, "Immediately", "Measurement starts as soon as Start is pressed."),
    (StartMode.DELAY, "After a pre-run delay", "The pump runs first for the set time (with countdown and live graphs), then measurement starts from zero."),
    (StartMode.AUTO, "Automatically when flow is stable", "Measurement starts by itself once the flow stops drifting. You can still start it by hand."),
    (StartMode.MANUAL, "When I press the button", "Watch the live graphs and press Start measuring when the pump looks ready."),
]
END_MODES = [(EndMode.TIME, "By time"), (EndMode.COUNT, "By number of pump cycles")]
# ("กำหนดเอง ค่าเดียวทุก rate" ถูกเอาออก — ค่าแต่ละ rate แก้ได้ที่ ตั้งค่า -> ข้อมูลสอบเทียบรอบปั๊ม หรือใน popup ตอนสร้าง)
WINDOW_SOURCES = [
    ("profile", "From the pump profile"),
    ("measure", "Measure the pump cycle before each rate"),
    ("recalibrate", "Calibrate the pump cycle again (replace this model's data)"),
]
PAGE_JOB, PAGE_CHECK, PAGE_MODE, PAGE_SETTINGS = range(4)


class _ModeCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, description: str):
        super().__init__()
        self.setProperty("modeCard", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        layout.addWidget(label(title, "modeTitle"))
        text = label(description, "pageSubtitle")
        text.setWordWrap(True)
        layout.addWidget(text)
        layout.addStretch()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()


class DeviceSearch(QWidget):
    """ช่องค้นเครื่องที่เคยทดสอบ: พิมพ์แล้วรายการที่ตรงจะขึ้นทันที เลือกขอบเขตการค้นได้"""
    picked = Signal(dict)

    def __init__(self, repository):
        super().__init__()
        self._repository = repository
        self._rows: list[dict] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.scope = QComboBox()
        for key, text in SEARCH_SCOPES:
            self.scope.addItem(tr(text), key)
        self.scope.setFixedWidth(110)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(tr("Type to search devices tested before…"))
        self.edit.setClearButtonEnabled(True)
        self.recent = QPushButton(tr("Recent"))
        self.recent.setToolTip(tr("Show the most recently tested devices"))
        layout.addWidget(self.scope)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.recent)

        self._model = QStringListModel(self)
        self._completer = QCompleter(self._model, self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setMaxVisibleItems(10)
        self.edit.setCompleter(self._completer)

        self.edit.textEdited.connect(self.search)
        self.scope.currentIndexChanged.connect(lambda: self.search(self.edit.text()))
        self.recent.clicked.connect(lambda: self.search("", force=True))
        self._completer.activated[str].connect(self._on_activated)

    @staticmethod
    def _describe(device: dict) -> str:
        parts = [" ".join(str(device.get(k) or "") for k in ("brand", "model")).strip(),
                 f'S/N {device["serial_no"]}' if device.get("serial_no") else "",
                 str(device.get("asset_id") or ""), str(device.get("job_id") or ""),
                 f'{device.get("last_date", "")} {device.get("last_verdict", "")}'.strip()]
        return "   ·   ".join(part for part in parts if part)

    def search(self, text: str, force: bool = False) -> None:
        if not text.strip() and not force:
            self._completer.popup().hide()
            return
        self._rows = self._repository.search_devices(text, self.scope.currentData())
        self._model.setStringList([self._describe(row) for row in self._rows] or [tr("No matching device")])
        self._completer.complete()

    def _on_activated(self, text: str) -> None:
        row = next((r for r in self._rows if self._describe(r) == text), None)
        self.edit.clear()
        if row is not None:
            self.picked.emit(row)


class TestWizard(QDialog):
    def __init__(self, parent: QWidget, repository, settings: AppSettings, initial: TestPlan | None = None,
                 sample_period_s: float | None = None):
        """sample_period_s: ช่วงเวลาต่อจุดของตราชั่งที่วัดได้ตอนว่าง (ใช้คำนวณจำนวนจุดของหน้าต่างราย rate)"""
        super().__init__(parent)
        self.setWindowTitle(tr("New test"))
        self.setModal(True)
        self.resize(900, 640)
        self.plan: TestPlan | None = None
        self._repository = repository
        self._settings = settings
        self._initial = copy.deepcopy(initial) if initial else TestPlan()
        self._mode = self._initial.run_mode
        self._rows: list[dict] = []
        self._sample_period, self._sample_source = sample_period_estimate(settings, sample_period_s, repository)
        self._rows_pump: str | None = None      # ชนิดเครื่องที่ค่าในหน้า 4 ถูกตั้งไว้ (เปลี่ยนชนิด = ตั้งใหม่)
        try:                                    # คำแนะนำของช่องกรอก เรียนรู้จากงานที่เคยบันทึก
            self._suggester = JobSuggester(repository.job_history())
        except Exception:
            self._suggester = JobSuggester([])

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._bar = PumpBar()               # แถบสีประจำชนิดเครื่อง บนสุดของหน้าต่าง (เห็นทุกหน้า)
        outer.addWidget(self._bar)
        root = QVBoxLayout()
        root.setContentsMargins(22, 14, 22, 18)
        root.setSpacing(14)
        outer.addLayout(root, 1)
        self._title = label("", "pageTitle")
        self._subtitle = label("", "pageSubtitle")
        self._badge = PumpBadge()
        heading = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(self._title)
        titles.addWidget(self._subtitle)
        heading.addLayout(titles, 1)
        heading.addWidget(self._badge, alignment=Qt.AlignmentFlag.AlignTop)
        root.addLayout(heading)

        self._pages = QStackedWidget()
        for build in (self._build_job_page, self._build_check_page, self._build_mode_page, self._build_settings_page):
            self._pages.addWidget(build())
        root.addWidget(self._pages, 1)

        buttons = QHBoxLayout()
        cancel = QPushButton(tr("Cancel"))
        self._back = QPushButton(tr("Back"))
        self._next = QPushButton(tr("Next"))
        self._next.setProperty("variant", "primary")
        self._next.setStyleSheet("padding: 8px 22px; font-size: 13px;")
        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(self._back)
        buttons.addWidget(self._next)
        root.addLayout(buttons)

        cancel.clicked.connect(self.reject)
        self._back.clicked.connect(lambda: self._go(self._pages.currentIndex() - 1))
        self._next.clicked.connect(self._on_next)
        self._load_job(self._initial.job)
        # ขั้นตรวจเครื่องเริ่มว่างทุกครั้ง (อุปกรณ์ที่ติดมา/อะไหล่เป็นของงานนี้ ไม่ยกมาจากงานก่อน — ผู้ใช้ 2026-11-13)
        self._load_checklists([], [], force=True, warranty=[])
        self._go(PAGE_JOB)

    # ================================================================ หน้า 1
    def _build_job_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        card = Card()
        card.body.setSpacing(8)
        self._search = DeviceSearch(self._repository)
        self._search.picked.connect(self._on_recall)
        recall = QHBoxLayout()
        recall.addWidget(label(tr("Recall"), "fieldLabel"))
        recall.addWidget(self._search, 1)
        card.body.addLayout(recall)
        card.body.addWidget(divider())

        # ชนิดเครื่อง: การ์ดใหญ่สองใบ สีต่างกัน (เลือกผิดเห็นทันที) — เลือกแล้วเลขงานขึ้นต้น MCI / MCS ให้เอง
        self._pump_type = PumpTypeSelector()
        self._pump_type.changed.connect(self._on_pump_type)
        card.body.addWidget(label(tr("Pump type"), "fieldLabel"))
        card.body.addWidget(self._pump_type)
        card.body.addWidget(divider())

        self._job_edits: dict[str, QLineEdit] = {}
        self._job_labels: dict[str, QLabel] = {}
        top = QGridLayout()
        top.setHorizontalSpacing(14)
        top.setVerticalSpacing(3)
        columns = [self._form(), self._form()]
        top_index = 0
        for name, text, placeholder, column in JOB_FIELDS:
            edit = QLineEdit() if name in NO_SUGGESTIONS else \
                SmartLineEdit(lambda typed, field=name: self._suggest(field, typed))
            edit.setPlaceholderText(tr(placeholder) if placeholder else "")
            caption = label(tr(text), "fieldLabel")
            self._job_edits[name] = edit
            self._job_labels[name] = caption
            if column == "top":
                top.addWidget(caption, 0, top_index)
                top.addWidget(edit, 1, top_index)
                top.setColumnStretch(top_index, (2, 3, 2)[top_index])
                top_index += 1
            else:
                columns[column].addRow(caption, edit)
        card.body.addLayout(top)
        card.body.addWidget(divider())
        grid = QHBoxLayout()
        grid.setSpacing(28)
        grid.addLayout(columns[0], 1)
        grid.addLayout(columns[1], 1)
        card.body.addLayout(grid)
        # บรรทัดบอกค่าที่ระบบเสนอจากรุ่น (จาง รอ Tab/Enter)
        self._autofill = label("", "hint")
        self._autofill.setStyleSheet(f"color: {Color.ACCENT};")
        card.body.addWidget(self._autofill)
        layout.addWidget(card)

        self._balance_note = label("", "hint")
        layout.addWidget(self._balance_note)
        layout.addWidget(label(tr("Faint text is a suggestion from earlier tests — press Tab or Enter to accept it, "
                                  "↓ for more, Esc to ignore. Nothing is filled in until you accept."), "hint"))
        layout.addStretch()

        edits = self._job_edits
        edits["job_no"].textEdited.connect(self._on_job_no_edited)
        edits["model"].textEdited.connect(self._on_model_changed)
        edits["model"].accepted.connect(self._on_model_accepted)
        edits["model"].confirmed.connect(self._on_model_confirmed)
        edits["brand"].accepted.connect(lambda _v: self._confirm_device(skip_brand=True))
        edits["brand"].textEdited.connect(lambda _t: self._refresh_standard())
        edits["site"].textEdited.connect(lambda _t: self._refresh_standard())
        edits["site"].accepted.connect(lambda _v: self._refresh_standard())
        edits["accessory"].textEdited.connect(self._on_accessory_changed)
        edits["accessory"].accepted.connect(self._on_accessory_accepted)
        edits["accessory"].confirmed.connect(self._on_accessory_confirmed)
        self._pending: dict[str, str] = {}          # ค่าที่เสนอจากรุ่น รอยืนยัน {"brand", "pump_type"}
        self._just_accepted: set[str] = set()       # ช่องที่เพิ่งรับคำแนะนำของตัวเองในการกดครั้งนี้
        self._accessory_usage = ""                  # ผลเทียบกับชุดสายมาตรฐานของโรงพยาบาล (JobInfo.accessory_usage)
        self._usage_key: tuple | None = None
        return page

    def _suggest(self, field: str, typed: str) -> list[str]:
        """คำแนะนำของช่อง field ตามบริบทของช่องอื่นที่กรอกแล้ว"""
        job = {name: edit.text().strip() for name, edit in self._job_edits.items()}
        job["pump_type"] = self._pump_type.currentData()
        items = self._suggester.suggest(field, job, typed)
        if field == "accessory":
            standard = self._standard()
            if standard and standard["iv_set"].lower().startswith(typed.strip().lower()):
                items = [standard["iv_set"]] + [i for i in items if i.lower() != standard["iv_set"].lower()]
        if field == "province":                     # รายชื่อจังหวัด 77 จังหวัด (กันสะกดผิด)
            key = typed.strip()
            if key:
                known = {i for i in items}
                items += [p for p in PROVINCES if p.startswith(key) and p not in known]
                items += [p for p in PROVINCES if key in p and not p.startswith(key) and p not in known]
            items = items[:8]
        return items

    def _on_pump_type(self, key: str) -> None:
        """เปลี่ยนชนิดเครื่อง: สีแถบ/ป้ายเปลี่ยนตาม, เลขงานขึ้นต้น MCI/MCS, ป้ายช่องชุดสาย
        และค่าเริ่มต้นของการวัด (rate, วิธีจับ) ต้องตั้งใหม่"""
        self._bar.set_pump(key)
        self._badge.set_pump(key)
        self._rows_pump = None
        edit = self._job_edits["job_no"]
        text = job_no_for_pump(edit.text(), key)
        if text != edit.text():
            edit.setText(text)
        model_text, brand_text = ACCESSORY_LABELS.get(key, ACCESSORY_LABELS["infusion"])
        self._job_labels["accessory"].setText(tr(model_text))
        self._job_labels["accessory_brand"].setText(tr(brand_text))
        self._pending.pop("pump_type", None)
        self._show_autofill()
        self._refresh_standard()

    def _on_job_no_edited(self, text: str) -> None:
        """พิมพ์เลขงานก่อน: MCI… = Infusion, MCS… = Syringe (เลือกชนิดให้ทันที)"""
        pump = pump_from_job_no(text)
        if pump and pump != self._pump_type.currentData():
            self._pump_type.setCurrentIndex(self._pump_type.findData(pump))

    # ---------------------------------------------------------- เติมจากรุ่น
    def _on_model_changed(self, *_args) -> None:
        """รุ่นที่เคยบันทึก -> เสนอยี่ห้อ (ตัวจางในช่องยี่ห้อ) + ชนิดเครื่อง (การ์ดขอบประ) รอยืนยัน"""
        model = self._job_edits["model"].text().strip()
        info = self._suggester.infer_device(model) if model else {}
        brand_edit = self._job_edits["brand"]
        self._pending = {}
        brand, pump = info.get("brand", ""), info.get("pump_type", "")
        if brand and brand.lower() != brand_edit.text().strip().lower():
            self._pending["brand"] = brand
        if pump in ("infusion", "syringe") and pump != self._pump_type.currentData():
            self._pending["pump_type"] = pump
        brand_edit.set_preview(self._pending.get("brand", "") if not brand_edit.text().strip() else "")
        self._pump_type.suggest(self._pending.get("pump_type"))
        self._show_autofill()
        self._refresh_standard()

    def _on_model_accepted(self, _value: str) -> None:
        self._just_accepted.add("model")
        self._on_model_changed()

    def _on_model_confirmed(self) -> None:
        """Tab/Enter ในช่องรุ่น = ยืนยันยี่ห้อ + ชนิดที่เสนอ (ถ้ากดครั้งนี้เพื่อรับชื่อรุ่น -> ยังไม่ยืนยัน ให้เห็นตัวจางก่อน)"""
        if "model" in self._just_accepted:
            self._just_accepted.discard("model")
            return
        self._confirm_device()

    def _confirm_device(self, skip_brand: bool = False) -> None:
        brand_edit = self._job_edits["brand"]
        if "brand" in self._pending and not skip_brand:
            brand_edit.setText(self._pending.pop("brand"))
            brand_edit.set_preview("")
        if "pump_type" in self._pending:
            self._pump_type.setCurrentIndex(self._pump_type.findData(self._pending.pop("pump_type")))
        self._pending = {}
        self._pump_type.suggest(None)
        self._show_autofill()
        self._refresh_standard()

    def _show_autofill(self) -> None:
        parts = []
        if "brand" in self._pending:
            parts.append(self._pending["brand"])
        if "pump_type" in self._pending:
            parts.append(pump_name(self._pending["pump_type"]))
        model = self._job_edits["model"].text().strip()
        self._autofill.setText(tr("↹ Tab / Enter in Model confirms what {model} was recorded as: {values}",
                                  model=model, values=" · ".join(parts)) if parts else "")
        self._autofill.setVisible(bool(parts))

    # ---------------------------------------------------------- ชุดสาย
    def _standard(self) -> dict | None:
        """ชุดสายมาตรฐานของโรงพยาบาลนี้ + เครื่องรุ่นนี้ (ถ้ามี)"""
        get = lambda name: self._job_edits[name].text().strip()         # noqa: E731
        try:
            return self._repository.site_standard(get("site"), get("brand"), get("model"), self._pump_type.currentData())
        except Exception:
            return None

    def _refresh_standard(self) -> None:
        """โรงพยาบาลนี้เคยใช้ชุดสายใดกับเครื่องรุ่นนี้ -> เสนอเป็นตัวจาง (ช่องยังว่าง)"""
        standard = self._standard()
        accessory, brand = self._job_edits["accessory"], self._job_edits["accessory_brand"]
        accessory.set_preview(standard["iv_set"] if standard and not accessory.text().strip() else "")
        if not brand.text().strip():
            if standard and (not accessory.text().strip()
                             or accessory.text().strip().lower() == standard["iv_set"].lower()):
                brand.set_preview(standard.get("iv_set_brand") or "")
            elif accessory.text().strip():
                brand.set_preview(self._suggester.infer_accessory_brand(accessory.text().strip()))
            else:
                brand.set_preview("")

    def _on_accessory_changed(self, *_args) -> None:
        self._refresh_standard()

    def _on_accessory_accepted(self, _value: str) -> None:
        self._just_accepted.add("accessory")
        self._refresh_standard()

    def _on_accessory_confirmed(self) -> None:
        """Tab/Enter ในช่องรุ่นชุดสาย = รับยี่ห้อที่เสนอ (ถ้ากดเพื่อรับชื่อรุ่น -> ให้เห็นตัวจางก่อน)"""
        if "accessory" in self._just_accepted:
            self._just_accepted.discard("accessory")
            return
        brand = self._job_edits["accessory_brand"]
        if not brand.text().strip():
            brand.take_preview()

    def _check_accessory_standard(self) -> bool:
        """ก่อนไปขั้น 2: ชุดสายต่างจากมาตรฐานของโรงพยาบาลนี้ไหม -> ถามชั่วคราว/ถาวร (False = กลับไปแก้)"""
        get = lambda name: self._job_edits[name].text().strip()         # noqa: E731
        site, model, accessory = get("site"), get("model"), get("accessory")
        if not (site and model and accessory):
            self._accessory_usage = ""
            return True
        standard = self._standard()
        key = (site.lower(), get("brand").lower(), model.lower(), self._pump_type.currentData(), accessory.lower())
        if standard is None:
            self._accessory_usage = "first"         # ครั้งแรกของโรงพยาบาล + รุ่นนี้ -> ตั้งเป็นมาตรฐาน
            return True
        if standard["iv_set"].strip().lower() == accessory.lower():
            self._accessory_usage = "standard"
            return True
        if self._usage_key == key and self._accessory_usage in ("temporary", "new_standard"):
            return True                             # ตอบไปแล้วสำหรับค่าชุดนี้
        kind = tr(ACCESSORY_LABELS.get(self._pump_type.currentData(), ACCESSORY_LABELS["infusion"])[0])
        device = " ".join(part for part in (get("brand"), model) if part)
        old = " ".join(part for part in (standard.get("iv_set_brand") or "", standard["iv_set"]) if part)
        new = " ".join(part for part in (get("accessory_brand"), accessory) if part)
        decision = self._ask_accessory_change(site, device, kind, old, new)
        if decision is None:
            self._job_edits["accessory"].setFocus()
            return False
        self._accessory_usage, self._usage_key = decision, key
        return True

    def _ask_accessory_change(self, site, device, kind, old, new):
        """แยกเป็นเมธอดเพื่อให้ทดสอบแทนที่ได้ (popup ค้างสคริปต์)"""
        return ask_accessory_change(self, site, device, kind, old, new)

    @staticmethod
    def _form() -> QFormLayout:
        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        return form

    def _on_recall(self, device: dict) -> None:
        """เติมข้อมูลตัวเครื่องจากรายการที่เลือก (ไม่ทับข้อมูลของงานครั้งนี้ เช่น เลขงาน ผู้ทดสอบ อุณหภูมิ)"""
        job = self._read_job()
        for name in _DEVICE_FIELDS:
            setattr(job, name, device.get(name, "") or "")
        try:
            job.pump_type = PumpType(device.get("pump_type", job.pump_type.value))
        except ValueError:
            pass
        self._load_job(job)

    def _load_job(self, job: JobInfo) -> None:
        self._pump_type.setCurrentIndex(max(0, self._pump_type.findData(job.pump_type.value)))
        for name, edit in self._job_edits.items():
            value = getattr(job, name)
            edit.setText("" if value is None else f"{value:g}" if isinstance(value, float) else str(value))
        self._on_pump_type(self._pump_type.currentData())       # เลขงาน MCI/MCS + ป้ายชุดสาย
        self._on_model_changed()
        self._balance_note.setText(tr("Reference balance: {balance} — change it in Settings",
                                      balance=self._settings.balance.label or "—"))

    def _read_job(self) -> JobInfo:
        job = JobInfo(pump_type=PumpType(self._pump_type.currentData()))
        for name, edit in self._job_edits.items():
            text = edit.text().strip()
            if name in _NUMERIC_FIELDS:
                try:
                    setattr(job, name, float(text) if text else None)
                except ValueError:
                    setattr(job, name, None)
            else:
                setattr(job, name, text)
        if job.job_no.upper() in JOB_PREFIXES.values():  # มีแต่คำนำหน้า = ยังไม่ได้กรอกเลขงาน
            job.job_no = ""
        job.balance_id = self._settings.balance.label
        job.accessory_usage = self._accessory_usage
        job.accessories = self._accessories.values()
        job.parts_replaced = self._parts.values()
        job.parts_warranty = self._parts.warranty_values()
        return job

    # ================================================================ หน้า 2
    def _build_check_page(self) -> QWidget:
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        self._accessories = Checklist(tr("Accessories received with the device"), "received")
        self._parts = Checklist(tr("Parts replaced"), "replaced")
        self._accessories.forget_requested.connect(lambda item: self._forget("accessory", item))
        self._parts.forget_requested.connect(lambda item: self._forget("part", item))
        # ประวัติอะไหล่ + ประกันของเครื่องนี้ (เปิดซ้ำได้ทุกเมื่อ)
        self._history_button = QPushButton(tr("Warranty history"))
        self._history_button.setProperty("variant", "ghost")
        self._history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._history_button.clicked.connect(self._show_part_history)
        self._history_button.hide()
        self._parts.header.insertWidget(self._parts.header.count() - 1, self._history_button)
        self._warranty_note = label("", "hint")
        self._warranty_note.setWordWrap(True)
        self._warranty_note.hide()
        self._parts.layout().insertWidget(2, self._warranty_note)
        row.addWidget(self._accessories, 1)
        row.addWidget(self._parts, 1)
        self._checklist_device: tuple | None = None     # รุ่นที่รายการบนจอเป็นของมัน
        self._warranty_device: tuple | None = None      # เครื่องที่ถามเรื่องเคลมประกันไปแล้ว
        self._warranty_items: list = []
        return page

    def _device_key(self) -> tuple[str, str]:
        return self._job_edits["brand"].text().strip(), self._job_edits["model"].text().strip()

    def _load_checklists(self, accessories: list[str], parts: list[str], force: bool = False,
                         warranty: list[str] | None = None) -> None:
        """เติมรายการตรวจเครื่องของรุ่นที่กรอกอยู่ (เรียกเมื่อเข้าหน้านี้ หรือเมื่อรุ่นเปลี่ยน)"""
        brand, model = self._device_key()
        if not force and self._checklist_device == (brand.lower(), model.lower()):
            return
        self._checklist_device = (brand.lower(), model.lower())
        device = " ".join(part for part in (brand, model) if part)
        catalog = self._settings.catalog
        self._accessories.set_items(device, self._repository.model_items(brand, model, "accessory"),
                                    catalog.accessories, accessories)
        self._parts.set_items(device, self._repository.model_items(brand, model, "part"), catalog.parts, parts,
                              warranty if warranty is not None else self._parts.warranty_values())

    def _forget(self, kind: str, item: str) -> None:
        brand, model = self._device_key()
        self._repository.forget_item(brand, model, kind, item)

    def _remember_checklists(self) -> None:
        """สร้างการทดสอบแล้ว: จำสิ่งที่ติ๊ก/เพิ่ม ไว้กับรุ่นนี้ (ยิ่งใช้ รายการของรุ่นยิ่งครบ)
        + ชุดสายมาตรฐานของโรงพยาบาล (ครั้งแรก / ผู้ใช้เลือกเปลี่ยนถาวร)"""
        brand, model = self._device_key()
        self._repository.remember_items(brand, model, "accessory", self._accessories.custom_items(), self._accessories.values())
        self._repository.remember_items(brand, model, "part", self._parts.custom_items(), self._parts.values())
        job = self.plan.job if self.plan else self._read_job()
        if job.accessory_usage in ("first", "new_standard"):
            self._repository.set_site_standard(job.site, job.brand, job.model, job.pump_type.value,
                                               job.accessory, job.accessory_brand)

    def _offer_warranty_claims(self) -> None:
        """เครื่องที่เคยเปลี่ยนอะไหล่กลับมา: แจ้งรายการที่ยังมีประกัน/late แล้วให้ติ๊กว่าจะเคลมไหม (ครั้งเดียวต่อเครื่อง)"""
        if self._pages.currentIndex() != PAGE_CHECK:
            return
        job = self._read_job()
        key = tuple(" ".join(str(getattr(job, n) or "").lower().split()) for n in ("brand", "model", "serial_no", "asset_id"))
        if key == self._warranty_device:
            return
        self._warranty_device = key
        warranty = self._settings.warranty
        try:
            history = self._repository.part_history(job)
        except Exception:
            history = []
        self._warranty_items = summarize(history, months=warranty.months, grace_months=warranty.grace_months)
        claimable = [item for item in self._warranty_items if item.status.claimable]
        self._history_button.setVisible(bool(self._warranty_items))
        if self._warranty_items:
            self._warranty_note.setText(
                tr("This device had {n} parts replaced before · {m} still under warranty or late.",
                   n=len(self._warranty_items), m=len(claimable)))
        self._warranty_note.setVisible(bool(self._warranty_items))
        if claimable:
            self._show_part_history()

    def _show_part_history(self) -> None:
        if not self._warranty_items:
            return
        brand, model = self._device_key()
        serial = self._job_edits["serial_no"].text().strip()
        device = " ".join(part for part in (brand, model, f"S/N {serial}" if serial else "") if part)
        dialog = PartHistoryDialog(self, device, self._warranty_items, already=self._parts.warranty_values())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for part in dialog.claims:
                self._parts.tick(part, warranty=True)       # ลงช่องอะไหล่ที่เปลี่ยนพร้อมสถานะประกัน

    def _confirm_empty_lists(self) -> bool:
        """ไปต่อจากขั้น 2 ตอนรายการว่าง: ถามว่าไม่มีจริงไหม (กันลืมกรอก) — True = ไปต่อ"""
        empty = [title for title, checklist in ((tr("Accessories received with the device"), self._accessories),
                                                (tr("Parts replaced"), self._parts)) if not checklist.values()]
        if not empty:
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(tr("Nothing ticked"))
        box.setText(tr("Nothing is ticked in:") + "\n• " + "\n• ".join(empty))
        box.setInformativeText(tr("Is that correct — really none? It is easy to forget."))
        yes = box.addButton(tr("Correct, none"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("Go back and tick"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(yes)
        box.exec()
        return box.clickedButton() is yes

    # ================================================================ หน้า 3
    def _build_mode_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.setSpacing(16)
        for mode, title, description in MODES:
            card = _ModeCard(tr(title), tr(description))
            card.setFixedHeight(190)
            card.clicked.connect(lambda m=mode: self._choose_mode(m))
            row.addWidget(card, 1)
        column.addStretch(1)
        column.addLayout(row)
        column.addStretch(2)
        return page

    def _choose_mode(self, mode: RunMode) -> None:
        # กลับมาโหมดเดิมและชนิดเครื่องเดิม -> คงค่าที่ตั้งไว้ (เปลี่ยนชนิดเครื่อง = ใช้ค่าเริ่มต้นของชนิดใหม่)
        keep = self._mode is mode and bool(self._rows) and self._rows_pump == self._pump_type.currentData()
        self._mode = mode
        if not keep:
            self._apply_mode_defaults()
        self._go(PAGE_SETTINGS)

    def _apply_mode_defaults(self) -> None:
        pump = self._pump_type.currentData()
        self._rows_pump = pump
        plan = self._initial
        if plan.run_mode is self._mode and plan.job_id and plan.job.pump_type.value == pump:   # แก้แผนเดิม -> ใช้ค่าเดิม
            steps, strategy, tolerance = plan.steps, plan.strategy, plan.tolerance_pct
            end_mode, start_mode, delay, window = plan.end_mode, plan.start_mode, plan.start_delay_s, plan.window_source
        else:
            defaults = MODE_DEFAULTS[self._mode.value]
            rates = defaults["rates"] or RATE_PRESETS[pump]
            steps = [StepConfig(target_flow=rate, duration_min=defaults["duration_min"]) for rate in rates]
            strategy, tolerance = DEFAULT_STRATEGY[pump], DEFAULT_TOLERANCE_PCT[pump]
            end_mode, start_mode, delay, window = EndMode.TIME, StartMode.IMMEDIATE, 30.0, "profile"

        self._strategy.setCurrentIndex(max(0, self._strategy.findData(strategy)))
        self._end_mode.setCurrentIndex(max(0, self._end_mode.findData(end_mode.value)))
        self._start_mode.setCurrentIndex(max(0, self._start_mode.findData(start_mode.value)))
        self._window_source.setCurrentIndex(max(0, self._window_source.findData(window)))
        self._delay.setValue(delay)
        self._tolerance.setValue(tolerance)
        while self._rows:
            self._remove_row(self._rows[-1])
        for step in steps:
            self._add_row(step)
        self._refresh_settings()

    # ================================================================ หน้า 4
    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ---- วิธีวัด
        method = Card(tr("Measurement"))
        self._strategy = QComboBox()
        for key, text in STRATEGIES.choices():
            self._strategy.addItem(tr(text), key)
        self._end_mode = QComboBox()
        for mode, text in END_MODES:
            self._end_mode.addItem(tr(text), mode.value)
        self._start_mode = QComboBox()
        for mode, text, _ in START_MODES:
            self._start_mode.addItem(tr(text), mode.value)
        self._window_source = QComboBox()
        for key, text in WINDOW_SOURCES:
            self._window_source.addItem(tr(text), key)
        self._delay = number_box(1, 3600, 30, 0, " s")
        self._tolerance = number_box(0.1, 50, 5, 1, " %")
        self._tolerance.setPrefix("± ")

        left, right = self._form(), self._form()
        left.addRow(label(tr("Method"), "fieldLabel"), self._strategy)
        left.addRow(label(tr("End condition"), "fieldLabel"), self._end_mode)
        left.addRow(label(tr("Tolerance"), "fieldLabel"), self._tolerance)
        right.addRow(label(tr("Start measuring"), "fieldLabel"), self._start_mode)
        right.addRow(label(tr("Pre-run delay"), "fieldLabel"), self._delay)
        # ปุ่ม Calibration รอบปั๊ม: เรียนรู้รุ่นนี้ใหม่ แทนที่ข้อมูลเดิม (มีเมื่อรุ่นนี้เคยเรียนรู้แล้ว)
        self._recalibrate_button = QPushButton(tr("Calibration…"))
        self._recalibrate_button.setProperty("variant", "chip")
        self._recalibrate_button.setToolTip(tr("Learn this model's pump cycle again and replace its earlier data"))
        self._recalibrate_button.clicked.connect(self._ask_recalibrate)
        window_row = QWidget()
        window_box = QHBoxLayout(window_row)
        window_box.setContentsMargins(0, 0, 0, 0)
        window_box.setSpacing(6)
        window_box.addWidget(self._window_source, 1)
        window_box.addWidget(self._recalibrate_button)
        right.addRow(label(tr("Window sizes"), "fieldLabel"), window_row)
        self._window_source.activated.connect(self._on_window_source_picked)
        self._window_choice = "profile"
        columns = QHBoxLayout()
        columns.setSpacing(28)
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)
        method.body.addLayout(columns)
        self._hint = label("", "hint")
        self._hint.setWordWrap(True)
        method.body.addWidget(self._hint)
        # เกณฑ์ flow นิ่ง (เฉพาะโหมดเริ่มอัตโนมัติ): ค่าเริ่มต้นของกลุ่ม หรือค่าเฉพาะ รุ่น + ชนิด + ชุดสาย
        self._criteria_row = QWidget()
        criteria_row = QHBoxLayout(self._criteria_row)
        criteria_row.setContentsMargins(0, 0, 0, 0)
        self._criteria_text = label("", "hint")
        self._criteria_text.setWordWrap(True)
        self._criteria_button = QPushButton(tr("Adjust for this model…"))
        self._criteria_button.setProperty("variant", "chip")
        self._criteria_button.clicked.connect(self._edit_criteria)
        criteria_row.addWidget(self._criteria_text, 1)
        criteria_row.addWidget(self._criteria_button)
        method.body.addWidget(self._criteria_row)
        layout.addWidget(method)

        # ---- รายการ rate
        rates = Card(tr("Flow rates"))
        self._add_button = QPushButton(tr("+ Add rate"))
        self._add_button.setProperty("variant", "ghost")
        rates.header.addWidget(self._add_button)
        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(10)
        self._grid.setVerticalSpacing(8)
        for column, text in enumerate(("", "Target rate", "Duration", "Pump cycles", "Interval length",
                                       "Peak-detection windows", "")):
            self._grid.addWidget(label(tr(text) if text else "", "fieldLabel"), 0, column)
        self._windows_header = self._grid.itemAtPosition(0, 5).widget()
        for column in (1, 2, 3, 4):
            self._grid.setColumnStretch(column, 1)
        rates.body.addLayout(self._grid)
        layout.addWidget(rates)
        layout.addStretch()

        self._add_button.clicked.connect(lambda: (self._add_row(self._last_step()), self._refresh_settings()))
        for combo in (self._strategy, self._end_mode, self._start_mode, self._window_source):
            combo.currentIndexChanged.connect(self._refresh_settings)
        return page

    def _last_step(self) -> StepConfig:
        return self._read_step(self._rows[-1]) if self._rows else StepConfig()

    def _add_row(self, step: StepConfig) -> None:
        row = {
            "index": label("", "stepIndex"),
            "rate": number_box(0.1, 2000, step.target_flow, 1, " ml/h"),
            "duration": number_box(0.5, 1440, step.duration_min, 1, " min"),
            "cycles": int_box(1, 10000, step.cycle_count),
            "window": QComboBox(),
            "remove": QPushButton("✕"),
            "info": label("", "hint"),
            "window_s": step.window_s,
            # สัดส่วนที่กำหนดในแผนเดิม (แก้แผน) — แถวใหม่ = ใช้ค่าที่จำไว้ของรุ่น
            "fractions": (step.regression_fraction, step.half_fraction) if step.regression_fraction > 0 else None,
        }
        row["index"].setAlignment(Qt.AlignmentFlag.AlignCenter)
        row["remove"].setProperty("variant", "ghost")
        row["remove"].setToolTip(tr("Remove this rate"))
        row["remove"].clicked.connect(lambda: (self._remove_row(row), self._refresh_settings()))
        row["duration"].valueChanged.connect(lambda: self._fill_windows(row))
        row["rate"].valueChanged.connect(lambda: self._refresh_criteria())     # เวลาที่ต้องใช้ตรวจนิ่งขึ้นกับ rate
        row["rate"].valueChanged.connect(lambda: (row.__setitem__("fractions", None), self._refresh_windows()))
        row["window"].activated.connect(lambda: row.__setitem__("window_s", row["window"].currentData()))
        self._rows.append(row)
        self._fill_windows(row)
        self._layout_rows()

    def _remove_row(self, row: dict) -> None:
        self._rows.remove(row)
        for key in ("index", "rate", "duration", "cycles", "window", "info", "remove"):
            self._grid.removeWidget(row[key])
            row[key].setParent(None)
            row[key].deleteLater()
        self._layout_rows()

    def _layout_rows(self) -> None:
        for number, row in enumerate(self._rows, start=1):
            row["index"].setText(str(number))
            for column, key in enumerate(("index", "rate", "duration", "cycles", "window", "info", "remove")):
                self._grid.addWidget(row[key], number, column)

    def _fill_windows(self, row: dict) -> None:
        """เติมตัวเลือกความยาวช่วง เฉพาะค่าที่หารเวลาทดสอบลงตัว"""
        total = round(row["duration"].value() * 60)
        combo: QComboBox = row["window"]
        combo.clear()
        for seconds in WINDOW_CHOICES_S:
            if seconds < total and total % seconds == 0:
                text = f"{seconds} s" if seconds < 60 else f"{seconds // 60} min"
                combo.addItem(f"{text}   ({total // seconds} {tr('intervals')})", float(seconds))
        if combo.count() == 0:
            combo.addItem(tr("Whole duration"), float(total))
        index = combo.findData(float(row["window_s"]))
        combo.setCurrentIndex(index if index >= 0 else min(combo.count() - 1, max(0, combo.findData(30.0))))
        row["window_s"] = combo.currentData()

    def _profile(self):
        job = self._read_job()
        return self._repository.get_profile(job.brand, job.model, job.accessory, job.pump_type.value)

    def _refresh_settings(self) -> None:
        """เปิด/ปิดช่องตามวิธีวัดที่เลือก และอัปเดตคำอธิบาย"""
        strategy = STRATEGIES.get(self._strategy.currentData())
        can_count = "count" in strategy.end_modes
        if not can_count:
            self._end_mode.setCurrentIndex(self._end_mode.findData(EndMode.TIME.value))
        self._end_mode.setEnabled(can_count)
        by_count = self._end_mode.currentData() == EndMode.COUNT.value
        self._delay.setEnabled(self._start_mode.currentData() == StartMode.DELAY.value)
        self._window_source.setEnabled(strategy.uses_cycles)
        known = self._profile()
        self._recalibrate_button.setEnabled(strategy.uses_cycles and bool(known and known.runs))
        for row in self._rows:
            row["duration"].setEnabled(not by_count)
            row["cycles"].setEnabled(by_count)
            row["window"].setEnabled(strategy.uses_window)
            row["remove"].setEnabled(len(self._rows) > 1)

        hints = [tr(next(text for mode, _, text in START_MODES if mode.value == self._start_mode.currentData()))]
        if strategy.uses_cycles:
            hints.append(tr("Cycles are counted peak-to-peak and valley-to-valley; the test stops when both have reached the set number.")
                         if by_count else tr("When the time is up the test keeps going until the pump cycle in progress is complete."))
            source, profile = self._window_source.currentData(), self._profile()
            if source == "profile" and profile and profile.runs:
                hints.append(tr("Pump profile found: {ml:.3f} ml per cycle from {n} earlier runs.",
                                ml=profile.stroke_volume_ml, n=profile.runs))
            elif source == "profile" and profile and profile.provisional:
                hints.append(tr("This model uses a default of {ml:.3f} ml per cycle until it has been measured.",
                                ml=profile.stroke_volume_ml))
            elif source == "recalibrate":
                hints.append(tr("Calibration: the first rate measures the pump cycle; when its result is kept, this "
                                "model's earlier pump-cycle data stops being used (kept for audit)."))
            elif source == "profile":
                hints.append(tr("No profile for this pump yet — the pump cycle will be measured before each rate and saved as its profile."))
        self._hint.setText("  ".join(hints))
        self._refresh_criteria(strategy)
        self._refresh_windows(strategy)

    # ------------------------------------------------ หน้าต่างราย rate (ข้อ ก)
    def _rate_windows(self, steps=None, stroke_ml: float | None = None):
        """RateWindow ของทุกแถว (ค่าเดียวกับที่ controller จะใช้)"""
        job = self._read_job()
        if steps is None:
            steps = [self._read_step(row) for row in self._rows]
        overrides = {st.target_flow: (st.regression_fraction, st.half_fraction) for st in steps if st.regression_fraction > 0}
        return plan_windows(self._repository, self._settings.engine, job, [st.target_flow for st in steps],
                            self._sample_period, overrides, stroke_ml)

    def _refresh_windows(self, strategy=None) -> None:
        strategy = strategy or STRATEGIES.get(self._strategy.currentData())
        visible = strategy.uses_cycles
        self._windows_header.setVisible(visible)
        if not self._rows:
            return
        items = self._rate_windows() if visible else []
        for row, item in zip(self._rows, items or [None] * len(self._rows)):
            row["info"].setVisible(visible)
            if item is None:
                continue
            period = f"{item.period_s:.1f} s" if item.period_s else "—"
            if item.windows:
                text = tr("cycle {p} · reg {r} · n̄ {h} · {ppc:.1f} pts/cycle", p=period, r=item.windows.regression,
                          h=item.windows.half, ppc=item.windows.points_per_cycle)
            else:
                text = tr("cycle {p} · reg {r:.2f} · n̄ {h:.2f} × cycle", p=period, r=item.regression_fraction,
                          h=item.half_fraction)
            status = tr(FIT_TEXT.get(item.fit, item.fit))
            if item.level in ("low", "too_low"):
                status = "⚠ " + tr("few points per cycle") + " · " + status
            row["info"].setText(text + "\n" + status)
            color = Color.SUCCESS if item.calibrated and item.level == "ok" and not item.problems else \
                Color.DANGER if item.blocking else Color.WARNING
            row["info"].setStyleSheet(f"color: {color};")

    # ------------------------------------------------ Calibration รอบปั๊ม
    def _on_window_source_picked(self, _index: int) -> None:
        if self._window_source.currentData() == "recalibrate":
            if not self._ask_recalibrate():
                self._window_source.setCurrentIndex(max(0, self._window_source.findData(self._window_choice)))
        else:
            self._window_choice = self._window_source.currentData()

    def _ask_recalibrate(self) -> bool:
        """ยืนยัน Calibration รอบปั๊มใหม่ (แสดงค่าที่จำไว้ + เสนอเรียง rate สูงไปต่ำ)"""
        job = self._read_job()
        device = " ".join(p for p in (job.brand, job.model, job.accessory) if p) or tr("This pump")
        profile = self._profile()
        tuned = self._repository.tuned_windows(job.brand, job.model, job.accessory, job.pump_type.value)
        rates = [self._read_step(row).target_flow for row in self._rows]
        dialog = RecalibrateDialog(self, device, profile, tuned, rates)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        if dialog.reorder.isChecked():
            self._set_steps(sorted((self._read_step(row) for row in self._rows),
                                   key=lambda step: step.target_flow, reverse=True))
        self._window_source.setCurrentIndex(self._window_source.findData("recalibrate"))
        self._refresh_settings()
        return True

    def _set_steps(self, steps) -> None:
        while self._rows:
            self._remove_row(self._rows[-1])
        for step in steps:
            self._add_row(step)
        self._refresh_settings()

    def _criteria_context(self, strategy=None):
        """(job, กลุ่ม, เกณฑ์ที่จะใช้, เป็นค่าเฉพาะรุ่นไหม)"""
        import dataclasses
        job = self._read_job()
        strategy = strategy or STRATEGIES.get(self._strategy.currentData())
        group = prerun_group(job.pump_type.value, strategy.uses_cycles)
        criteria = dataclasses.replace(self._settings.prerun.group(group))
        override = self._repository.prerun_criteria(job.brand, job.model, job.accessory, job.pump_type.value, group)
        for name, value in (override or {}).items():
            if hasattr(criteria, name):
                setattr(criteria, name, type(getattr(criteria, name))(value))
        return job, group, criteria, bool(override)

    def _refresh_criteria(self, strategy=None) -> None:
        from services.session_controller import PRERUN_GROUP_NAMES
        auto = self._start_mode.currentData() == StartMode.AUTO.value
        self._criteria_row.setVisible(auto)
        if not auto:
            return
        job, group, criteria, specific = self._criteria_context(strategy)
        wait = tr("start anyway after {m:g} min", m=criteria.max_wait_min) if criteria.max_wait_min else tr("no time limit")
        text = tr("Stable-flow criteria: {group} · {source} · ±{pct:g} % · {wait}",
                  group=tr(PRERUN_GROUP_NAMES[group]), source=tr("this model") if specific else tr("defaults"),
                  pct=criteria.stability_pct, wait=wait)
        too_slow = [rate for rate, need in self._stability_needs(job, criteria)
                    if criteria.max_wait_min and need > criteria.max_wait_min * 60.0]
        if too_slow:
            text += "\n⚠ " + tr("At {rates} ml/h the data needed to confirm stable flow takes longer than the limit — "
                                "measuring will start without confirmation (recorded with the result).",
                                rates=", ".join(f"{r:g}" for r in too_slow))
        self._criteria_text.setText(text)
        self._criteria_button.setEnabled(bool(job.brand or job.model))
        self._criteria_button.setToolTip("" if job.brand or job.model else
                                         tr("Enter brand and model in step 1 to keep values for this model."))

    def _stability_needs(self, job, criteria) -> list[tuple[float, float]]:
        """[(rate, วินาทีขั้นต่ำที่ต้องมีข้อมูลก่อนตรวจนิ่งได้)] — คาบจากโปรไฟล์ หรือเดาจากปริมาตรต่อรอบเริ่มต้น"""
        from core.prerun import block_length
        needs = []
        for row in self._rows:
            rate = row["rate"].value()
            period = self._repository.expected_period(job.brand, job.model, job.accessory, rate, job.pump_type.value)
            if period is None and job.pump_type.value == "infusion":
                stroke = self._settings.engine.default_stroke_volume_ml
                period = stroke * 3600.0 / rate if stroke > 0 and rate > 0 else None
            block = block_length(criteria.block_mode, criteria.block_cycles, criteria.block_s, criteria.min_block_mg,
                                 criteria.align_to_cycle, rate, period)
            needs.append((rate, block * criteria.blocks))
        return needs

    def _edit_criteria(self) -> None:
        from services.session_controller import PRERUN_GROUP_NAMES
        job, group, criteria, specific = self._criteria_context()
        device = " ".join(p for p in (job.brand, job.model, job.accessory) if p)
        dialog = PrerunCriteriaDialog(self, device, tr(PRERUN_GROUP_NAMES[group]), criteria, specific)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.action:
            self._repository.save_prerun_criteria(job.brand, job.model, job.accessory, job.pump_type.value, group,
                                                  dialog.values if dialog.action == "save" else None)
        self._refresh_criteria()

    def _read_step(self, row: dict) -> StepConfig:
        fractions = row.get("fractions") or (0.0, 0.0)
        return StepConfig(
            target_flow=row["rate"].value(), duration_min=row["duration"].value(),
            cycle_count=row["cycles"].value(), window_s=float(row["window"].currentData() or 30.0),
            regression_fraction=fractions[0], half_fraction=fractions[1],
        )

    # ============================================================ นำทาง
    def _go(self, index: int) -> None:
        index = max(PAGE_JOB, min(PAGE_SETTINGS, index))
        self._pages.setCurrentIndex(index)
        mode_title = next(tr(title) for mode, title, _ in MODES if mode is self._mode)
        titles = [
            (tr("Step 1 of 4 · Device and job details"), tr("Who and what is being tested")),
            (tr("Step 2 of 4 · Device check"), tr("Tick what came with the device and what was replaced")),
            (tr("Step 3 of 4 · Choose the test mode"), tr("Click a mode to continue")),
            (tr("Step 4 of 4 · {mode} settings", mode=mode_title), tr("Flow rates and how they are measured")),
        ]
        self._title.setText(titles[index][0])
        self._subtitle.setText(titles[index][1])
        self._back.setVisible(index > PAGE_JOB)
        self._next.setVisible(index != PAGE_MODE)
        self._next.setText(tr("Create test") if index == PAGE_SETTINGS else tr("Next"))
        if index == PAGE_CHECK:
            self._load_checklists(self._accessories.values(), self._parts.values())
            QTimer.singleShot(0, self, self._offer_warranty_claims)     # ให้หน้า 2 ขึ้นก่อน แล้วจึงถามเรื่องเคลม
        if index == PAGE_SETTINGS:
            self._refresh_settings()

    def _on_next(self) -> None:
        index = self._pages.currentIndex()
        if index == PAGE_JOB and not self._check_accessory_standard():
            return
        if index == PAGE_CHECK and not self._confirm_empty_lists():
            return
        if index < PAGE_SETTINGS:
            self._go(index + 1)
            return
        window_source = self._window_source.currentData()
        strategy_key = self._strategy.currentData()
        steps = [self._read_step(row) for row in self._rows]
        if STRATEGIES.get(strategy_key).uses_cycles and window_source != "recalibrate":
            decision = self._check_calibration(steps, window_source)
            if decision is None:
                return
            strategy_key, window_source, steps = decision
        self.plan = TestPlan(
            job=self._read_job(), run_mode=self._mode,
            strategy=strategy_key,
            end_mode=EndMode(self._end_mode.currentData()) if "count" in STRATEGIES.get(strategy_key).end_modes
            else EndMode.TIME,
            start_mode=StartMode(self._start_mode.currentData()),
            start_delay_s=self._delay.value(),
            tolerance_pct=self._tolerance.value(),
            window_source=window_source,
            steps=steps,
        )
        self._remember_checklists()
        self.accept()

    def _check_calibration(self, steps: list[StepConfig], window_source: str):
        """ก่อนสร้างแผนจับรอบปั๊ม: รุ่นนี้สอบเทียบ regression / n̄ ทุก rate แล้วหรือยัง (ข้อ ค + คำขอผู้ใช้ 2026-11-13)

        คืน (วิธีจับ, ที่มาของหน้าต่าง, ขั้น) หรือ None = กลับไปแก้
        """
        import dataclasses
        job = self._read_job()
        profile = self._profile()
        known_volume = bool(profile and profile.stroke_volume_ml > 0)
        stroke = None if known_volume else (self._settings.engine.default_stroke_volume_ml or 0.16)
        items = self._rate_windows(steps, stroke)
        if not any(item.warnings for item in items):
            return self._strategy.currentData(), window_source, steps
        dialog = self._prompt_calibration(job, items, known_volume, stroke,
                                          recompute=None if known_volume else lambda ml: self._rate_windows(steps, ml))
        if dialog is None or dialog.action is None:
            return None
        strategy_key = self._strategy.currentData()
        if dialog.action == "calibrate":
            # วัดคาบก่อนทุก rate แล้วปรับหน้าต่างจากผลที่เก็บ (ค่าที่ปรับได้ = "สอบเทียบแล้ว") — rate สูงก่อนถ้าเลือก
            if getattr(dialog, "reorder", None) is not None and dialog.reorder.isChecked():
                steps = sorted(steps, key=lambda st: st.target_flow, reverse=True)
            return strategy_key, "measure" if profile and profile.runs else "profile", steps
        if dialog.action == "time":
            steps = [dataclasses.replace(st, window_s=dialog.time_windows.get(st.target_flow, st.window_s))
                     for st in steps]
            return "time_interval", window_source, steps
        # ใช้โดยไม่สอบเทียบ: ค่าที่แก้ใช้กับแผนนี้ · กดบันทึก = จำให้รุ่นนี้ (ยังไม่ได้สอบเทียบ)
        values = dialog.values
        edited = set(dialog.table.edited_rates()) if hasattr(dialog, "table") else set()
        if dialog.save:
            for item in items:
                if item.calibrated and item.rate not in edited:
                    continue
                r, h = values.get(item.rate, (item.regression_fraction, item.half_fraction))
                source = "manual" if item.fit == "manual" else "uncalibrated"
                self._repository.save_window(job.brand, job.model, job.accessory, job.pump_type.value, item.rate,
                                             r, h, source, item.period_s, self._sample_period)
            if not known_volume and dialog.stroke_ml:
                self._repository.set_model_default(job.brand, job.model, job.accessory, dialog.stroke_ml,
                                                   job.pump_type.value)
        steps = [dataclasses.replace(st, regression_fraction=values[st.target_flow][0],
                                     half_fraction=values[st.target_flow][1])
                 if st.target_flow in edited or (not dialog.save and st.target_flow in values
                                                  and not next(i for i in items if i.rate == st.target_flow).calibrated)
                 else st for st in steps]
        return strategy_key, window_source, steps

    def _prompt_calibration(self, job, items, known_volume: bool, stroke: float | None, recompute=None):
        """เปิด popup เตือนสอบเทียบ คืน dialog ที่ปิดแล้ว (None = กลับไปแก้) — test แทนที่เมธอดนี้ได้"""
        device = " ".join(part for part in (job.brand, job.model, job.accessory) if part)
        dialog = CalibrationPromptDialog(self, device, items, self._sample_period, self._sample_source,
                                         can_remember=bool(job.brand or job.model),
                                         can_calibrate=known_volume, stroke_ml=stroke, recompute=recompute)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog
