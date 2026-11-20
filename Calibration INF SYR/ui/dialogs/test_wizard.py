"""TestWizard: สร้างแผนทดสอบ 6 ขั้น (ผู้ใช้ 2026-11-20 — ค่าที่วัดแยกจากผลตรวจ เดิมแคบ)
    1) ข้อมูลงาน/เครื่อง — พิมพ์ค้นเครื่องที่เคยทดสอบแล้วดึงข้อมูลมาเติมได้
    2) ตรวจเครื่อง — อุปกรณ์ที่มากับเครื่อง, อะไหล่ที่เปลี่ยน (เลือกจากรายการกลางในหน้าตั้งค่า)
    3) เลือกโหมด: Calibration / Inspection / Quick Test
    4) ผลตรวจรายข้อ + ประเภทงานในใบ (บำรุงรักษา/ซ่อม/สอบเทียบ — ตั้งให้เอง แก้ได้)
    5) ค่าที่วัด/ตรวจด้วยมือ (การอุดตันเฉพาะ Calibration, ไฟฟ้า, แบตเตอรี่, ตรวจขั้นสุดท้าย)
    6) ตั้งค่าการวัดของโหมดนั้น (rate, วิธีจับ, เงื่อนไขจบ, วิธีเริ่มวัด, ขนาดหน้าต่าง)
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
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QCompleter, QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QRadioButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from config.constants import (
    DEFAULT_STRATEGY, DEFAULT_TOLERANCE_PCT, MODE_DEFAULTS, RATE_PRESETS, WINDOW_CHOICES_S,
)
from config.i18n import tr
from config.settings import AppSettings
from config.provinces import PROVINCES
from core.models import (
    EndMode, JobInfo, PumpType, RunMode, StartMode, StepConfig, TestPlan, join_job_no, pump_from_prefix, split_job_no,
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
from services.autofill import Autofill, has
from services.job_suggestions import NO_SUGGESTIONS, JobSuggester
from services.window_plan import FIT_TEXT, plan_windows, sample_period_estimate
from ui.widgets.checklist import Checklist
from services.report import checklist as report_checklist
from ui.widgets.inspection_checks import InspectionChecks
from ui.widgets.report_extras import ReportExtras, defaults_from
from ui.widgets.pump_type import PumpBadge, PumpBar, PumpTypeSelector, pump_name
from ui.widgets.smart_edit import SmartLineEdit

# (ชื่อ field ใน JobInfo, ป้าย, ข้อความตัวอย่าง, คอลัมน์)  — "top" = แถวงานบนสุด (เลขงาน · โรงพยาบาล · จังหวัด)
# รุ่นอยู่เหนือยี่ห้อ: กรอกรุ่นแล้วระบบเสนอยี่ห้อ + ชนิดเครื่องที่รุ่นนี้เคยบันทึก (ผู้ใช้ 2026-11-13)
# รหัสตราชั่งย้ายไปหน้าตั้งค่า (ตราชั่งมาตรฐาน) — บันทึกลงผลให้อัตโนมัติ
JOB_FIELDS = [
    ("job_no", "Job no.", "e.g. 26-2201", "top"),           # ช่องเลข — คำนำหน้า MCI/MCS แยกช่องข้างหน้า (2026-11-20)
    ("site", "Hospital / site", "", "top"),
    ("province", "Province", "", "top"),
    ("model", "Model", "Type the model — brand and pump type follow", 0),
    ("brand", "Brand", "", 0),
    ("serial_no", "Serial no.", "", 0),
    ("asset_id", "Asset ID", "", 0),
    ("department", "Department", "", 0),
    ("operator", "Operator", "", 0),
    ("contact", "Contact person", "Hospital staff — shown on the report", 0),
    ("contact_phone", "Contact phone", "", 0),
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
# ขั้นที่ 3 (ผลตรวจรายข้อ + ค่าที่วัดด้วยมือ) แยกจากขั้นอุปกรณ์/อะไหล่ (ผู้ใช้ 2026-11-19) -> 5 ขั้น
# ลำดับขั้น (ผู้ใช้ 2026-11-19): เลือกโหมดก่อน แล้วจึงกรอกผลตรวจ/ค่าที่วัดด้วยมือ — ช่องที่ขึ้นตามโหมด (การอุดตัน = Calibration)
# 2026-11-20: ขั้น 4 ผลตรวจ + ประเภทงาน · ขั้น 5 ค่าที่วัด (ย้ายออกจากขั้น 4) · ขั้น 6 ตั้งค่า -> 6 ขั้น
PAGE_JOB, PAGE_CHECK, PAGE_MODE, PAGE_REPORT, PAGE_VALUES, PAGE_SETTINGS = range(6)
STEP_COUNT = PAGE_SETTINGS + 1
SERVICE_KINDS = [("pm", "Preventive maintenance"), ("repair", "Repair"), ("calib", "Calibration service")]


def fit_combo(combo: QComboBox, chars: int = 8) -> QComboBox:
    """ช่องเลือกที่หดได้ (เดิมกว้างตามตัวเลือกที่ยาวสุด 370–720 px -> หน้า 5 กว้างเกินจอ ช่องขวาถูกตัด — ผู้ใช้ 2026-11-19)
    รายการที่กางออกยังกว้างพอแสดงข้อความเต็ม"""
    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(chars)
    combo.view().setMinimumWidth(combo.view().sizeHintForColumn(0) + 24)
    return combo


def wrap(widget):
    widget.setWordWrap(True)
    widget.setMinimumWidth(120)
    return widget


# คอลัมน์ของแถว rate (หน้า 5) — วิธีจับตั้งแยกได้ทุกแถว
ROW_KEYS = ("index", "rate", "method", "duration", "cycles", "window", "info", "remove")
ROW_HEADERS = ("", "Target rate", "Method", "Duration", "Pump cycles", "Interval length", "Peak-detection windows", "")


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



def _sheet_pump(text: str) -> str:
    """ชนิดเครื่องจากข้อความใน Sheet (Infusion / Syringe / MCI / ไซริงค์ …) -> infusion | syringe | """""
    from services.history_search import PUMP_WORDS
    word = " ".join(str(text or "").lower().split())
    for key, words in PUMP_WORDS.items():
        if word in words or any(w in word for w in words if len(w) > 3):
            return key
    return ""

class TestWizard(QDialog):
    def __init__(self, parent: QWidget, repository, settings: AppSettings, initial: TestPlan | None = None,
                 sample_period_s: float | None = None):
        """sample_period_s: ช่วงเวลาต่อจุดของตราชั่งที่วัดได้ตอนว่าง (ใช้คำนวณจำนวนจุดของหน้าต่างราย rate)"""
        super().__init__(parent)
        self.setWindowTitle(tr("New test"))
        self.setModal(True)
        self.resize(900, 640)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:                  # ไม่สูง/กว้างเกินพื้นที่จอที่ใช้ได้ (เหนือแถบงาน)
            area = screen.availableGeometry()
            self.setMaximumSize(area.width(), area.height() - 40)
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
        for build in (self._build_job_page, self._build_check_page, self._build_mode_page, self._build_report_page,
                      self._build_values_page, self._build_settings_page):
            # แต่ละหน้าเลื่อนขึ้นลงได้ — จอเล็ก/เนื้อหายาว ปุ่ม ถัดไป/ย้อนกลับ ยังอยู่ในจอเสมอ (ผู้ใช้เจอกดไม่ได้ 2026-11-18)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)   # จอแคบมาก: เลื่อนได้ ไม่ถูกตัดเงียบๆ
            scroll.setWidget(build())
            self._pages.addWidget(scroll)
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
                if name == "job_no":            # คำนำหน้า (MCI/MCS แก้ได้) + เลข -> ประกอบเป็นเลขงานแบบเดิม
                    self._job_prefix = QLineEdit()
                    self._job_prefix.setMaximumWidth(72)
                    self._job_prefix.setToolTip(tr("Job no. prefix — follows the pump type, can be changed"))
                    holder = QWidget()
                    pair = QHBoxLayout(holder)
                    pair.setContentsMargins(0, 0, 0, 0)
                    pair.setSpacing(6)
                    pair.addWidget(self._job_prefix)
                    pair.addWidget(edit, 1)
                    top.addWidget(holder, 1, top_index)
                else:
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
        # เติมทันทีจากฐานข้อมูลที่สะสม (ผู้ใช้ 2026-11-20 — ไม่ต้องรอ Tab): ค่าที่จำไว้ตรงทั้งคำ -> ช่องปลายทางที่ยังว่าง
        # หรือยังเป็นค่าที่ระบบเติมเอง (ช่องที่ผู้ใช้พิมพ์เองไม่ถูกทับ) · ต้นทางเปลี่ยนจนไม่ตรง -> เอาค่าที่เติมเองออก
        self._auto: dict[str, tuple[str, str]] = {}     # ช่อง -> (ค่าที่เติม, ต้นทาง)
        self._auto_pump: str | None = None              # ต้นทางที่ตั้งชนิดเครื่องให้ (model/device)
        self._filling = False
        self._job_prefix.textEdited.connect(self._on_prefix_edited)
        edits["job_no"].textEdited.connect(self._on_job_no_edited)
        edits["site"].textChanged.connect(lambda _t: self._autofill_from("site"))
        edits["model"].textChanged.connect(lambda _t: self._autofill_from("model"))
        edits["brand"].textChanged.connect(lambda _t: self._autofill_from("site"))     # ชุดสายมาตรฐาน: โรงพยาบาล + เครื่อง
        edits["accessory"].textChanged.connect(lambda _t: self._autofill_from("accessory"))
        edits["serial_no"].textChanged.connect(lambda _t: self._autofill_from("device"))
        edits["asset_id"].textChanged.connect(lambda _t: self._autofill_from("device"))
        # Google Sheet (ผู้ใช้ 2026-11-20): เลขงาน / S/N / ครุภัณฑ์ ตรงกับแถวใน Sheet -> เติมช่องที่ยังว่าง (services/sheets.py)
        self._sheet_busy = False
        self._sheet_source = ""
        for name in ("job_no", "serial_no", "asset_id"):
            edits[name].textChanged.connect(lambda _t: self._sheet_fill())
        self._job_prefix.textChanged.connect(lambda _t: self._sheet_fill())
        self._accessory_usage = ""                  # ผลเทียบกับชุดสายมาตรฐานของโรงพยาบาล (JobInfo.accessory_usage)
        self._usage_key: tuple | None = None
        self._province_update: bool | None = None   # จังหวัดต่างจากที่จำไว้: True = จำทับ · False = เฉพาะงานนี้
        self._province_key: tuple | None = None
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
        # คำนำหน้าเลขงานตามชนิด — เฉพาะเมื่อว่างหรือเป็นคำนำหน้ามาตรฐาน (ที่แก้เองเป็นแบบอื่นไม่ทับ)
        prefixes = self._settings.jobs.prefixes()
        current = self._job_prefix.text().strip()
        if not current or pump_from_prefix(current, prefixes) is not None:
            self._job_prefix.setText(prefixes.get(key, ""))
        if getattr(self, "_checks", None) is not None:      # รายการตรวจของใบรายงานตามชนิดเครื่อง
            self._checks.set_pump(key)
            self._checks.pass_all()             # ข้อของชนิดเครื่องใหม่ตั้งต้น "ผ่าน"
        model_text, brand_text = ACCESSORY_LABELS.get(key, ACCESSORY_LABELS["infusion"])
        self._job_labels["accessory"].setText(tr(model_text))
        self._job_labels["accessory_brand"].setText(tr(brand_text))
        if getattr(self, "_extras", None) is not None:      # ค่าตั้งต้นการอุดตันแยก Infusion/Syringe (ขั้น 5)
            self._apply_value_defaults(key)
        self._refresh_standard()

    def _on_prefix_edited(self, text: str) -> None:
        """พิมพ์คำนำหน้าเลขงาน: MCI = Infusion, MCS = Syringe (ตามค่าตั้ง) -> เลือกชนิดให้ทันที"""
        pump = pump_from_prefix(text, self._settings.jobs.prefixes())
        if pump and pump != self._pump_type.currentData():
            self._pump_type.setCurrentIndex(self._pump_type.findData(pump))

    def _on_job_no_edited(self, text: str) -> None:
        """วางเลขงานเต็ม (มีคำนำหน้า) ลงช่องเลข -> แยกคำนำหน้าไปช่องหน้า + เลือกชนิด (เข้ากับการพิมพ์แบบเดิม)"""
        prefixes = self._settings.jobs.prefixes()
        prefix, number = split_job_no(text, prefixes)
        if prefix and pump_from_prefix(prefix, prefixes):
            self._job_edits["job_no"].setText(number)
            self._job_prefix.setText(prefix)
            self._on_prefix_edited(prefix)

    # ---------------------------------------------------------- เติมทันที (services/autofill.py — ผู้ใช้ 2026-11-20)
    @property
    def _book(self) -> Autofill:
        return Autofill(self._repository, self._suggester)

    def _text(self, name: str) -> str:
        return self._job_edits[name].text().strip()

    def _can_fill(self, name: str) -> bool:
        """ช่องนี้เติมให้ได้ไหม: ว่าง หรือยังเป็นค่าที่ระบบเติมเอง (ผู้ใช้ไม่ได้แก้)"""
        text = self._text(name)
        return not text or (name in self._auto and self._auto[name][0] == text)

    def _fill(self, name: str, value: str, source: str) -> None:
        if not has(value) or not self._can_fill(name):
            return
        edit = self._job_edits[name]
        if edit.text().strip() != value:
            edit.setText(value)
        if hasattr(edit, "set_preview"):
            edit.set_preview("")
        self._auto[name] = (value, source)

    def _unfill(self, source: str, keep: tuple = ()) -> None:
        """ต้นทางไม่ตรงแล้ว: ล้างช่องที่ยังเป็นค่าที่ต้นทางนี้เติมเอง (ช่องที่ผู้ใช้แก้แล้วไม่แตะ)"""
        for name, (value, origin) in list(self._auto.items()):
            if origin == source and name not in keep:
                if self._text(name) == value:
                    self._job_edits[name].setText("")
                del self._auto[name]
        if self._auto_pump == source:
            self._auto_pump = None

    def _set_pump(self, pump: str, source: str) -> None:
        """รุ่น/เครื่องที่จำไว้บอกชนิดเครื่อง (รุ่นเฉพาะเจาะจงกว่า — ผู้ใช้ 2026-11-20) -> ตั้งให้ทันที"""
        if pump not in ("infusion", "syringe"):
            return
        if pump != self._pump_type.currentData():
            self._pump_type.setCurrentIndex(self._pump_type.findData(pump))
        self._auto_pump = source

    def _autofill_from(self, source: str) -> None:
        """ต้นทางเปลี่ยน -> เติมช่องที่เกี่ยวข้องทันที (ต่อกันได้: S/N -> รุ่น -> ยี่ห้อ -> ชุดสาย)"""
        if self._filling:
            return
        self._filling = True
        follow: tuple = ()
        try:
            book, pump = self._book, self._pump_type.currentData()
            if source == "device":
                found = book.device(self._text("serial_no"), self._text("asset_id"))
                model = self._text("model")
                if found and model and not self._can_fill("model") and found.get("model", "").lower() != model.lower():
                    found = {}                  # S/N ตรงแต่คนละรุ่นกับที่ผู้ใช้พิมพ์ = คนละเครื่อง ไม่เติม
                if not found:
                    self._unfill("device")
                for name in ("site", "province", "department", "model", "brand", "accessory", "accessory_brand"):
                    self._fill(name, found.get(name, ""), "device")
                self._set_pump(found.get("pump_type", ""), "device")
                follow = ("model", "site", "accessory")         # ค่าที่เพิ่งเติมพาไปเติมช่องที่ยังว่างต่อ
            elif source == "site":
                site = self._text("site")
                province = book.province(site) if site else ""
                if province:
                    self._fill("province", province, "site")
                else:
                    self._unfill("site")
                standard = book.site_accessory(site, self._text("brand"), self._text("model"), pump) if site else None
                if standard and has(standard.get("iv_set")):
                    self._fill("accessory", standard.get("iv_set", ""), "standard")
                    self._fill("accessory_brand", standard.get("iv_set_brand") or "", "standard")
                else:
                    self._unfill("standard")
            elif source == "model":
                model = self._text("model")
                info = book.model_info(model) if model else {}
                if info.get("brand") or info.get("pump_type"):
                    self._fill("brand", info.get("brand", ""), "model")
                    self._set_pump(info.get("pump_type", ""), "model")
                else:
                    self._unfill("model")
                follow = ("site",)                              # ชุดสายมาตรฐานของ โรงพยาบาล + รุ่นนี้
            elif source == "accessory":
                accessory = self._text("accessory")
                brand = book.accessory_brand(accessory, pump) if accessory else ""
                if brand:
                    self._fill("accessory_brand", brand, "accessory")
                else:
                    self._unfill("accessory")
        finally:
            self._filling = False
        for name in follow:
            self._autofill_from(name)
        self._show_autofill()

    def _sheet_fill(self) -> None:
        """แถวใน Google Sheet ที่ตรงกับ เลขงาน (รวมคำนำหน้า/เฉพาะเลข) > S/N > ครุภัณฑ์ -> เติมช่องที่ยังว่าง
        (ช่องที่ผู้ใช้พิมพ์เองไม่ถูกทับ — ใช้กลไกเดียวกับเติมจากประวัติ)"""
        sheets_settings = getattr(self._settings, "sheets", None)
        if self._sheet_busy or sheets_settings is None or not sheets_settings.use_in_wizard:
            return
        try:
            from services import sheets
            store = sheets.store()
            if not store.has_rows():
                return
            full = join_job_no(self._job_prefix.text(), self._text("job_no"))
            found = None
            for name, value in (("job_no", full), ("job_no", self._text("job_no")),
                                ("serial_no", self._text("serial_no")), ("asset_id", self._text("asset_id"))):
                found = store.lookup(name, value)
                if found:
                    break
        except Exception:
            return
        self._sheet_busy = True
        try:
            if not found:
                self._unfill("sheet")
                self._sheet_source = ""
            else:
                self._sheet_source = found.get("_source", "")
                for name in ("site", "province", "department", "model", "brand", "serial_no", "asset_id",
                             "accessory", "accessory_brand", "operator", "contact", "contact_phone", "notes"):
                    if name in self._job_edits:
                        self._fill(name, found.get(name, ""), "sheet")
                pump = _sheet_pump(found.get("pump_type", ""))
                if pump:
                    self._set_pump(pump, "sheet")
        finally:
            self._sheet_busy = False
        self._show_autofill()

    def _show_autofill(self) -> None:
        """บรรทัดบอกว่าช่องไหนเติมจากประวัติ (แก้ได้ — พิมพ์ทับเมื่อไม่ตรง)"""
        model_text, brand_text = ACCESSORY_LABELS.get(self._pump_type.currentData(), ACCESSORY_LABELS["infusion"])
        names = {"province": "Province", "brand": "Brand", "model": "Model", "site": "Hospital / site",
                 "department": "Department", "accessory": model_text, "accessory_brand": brand_text,
                 "serial_no": "Serial no.", "asset_id": "Asset ID", "operator": "Operator",
                 "contact": "Contact person", "contact_phone": "Contact phone", "notes": "Notes"}
        filled = [tr(names[name]) for name, (value, _src) in self._auto.items()
                  if name in names and self._text(name) == value]
        from_sheet = any(src == "sheet" and self._text(name) == value for name, (value, src) in self._auto.items())
        if from_sheet and filled:
            self._autofill.setText(tr("Filled in from Google Sheet '{source}' and earlier jobs: {fields} — type over "
                                      "anything that has changed", source=self._sheet_source,
                                      fields=" · ".join(filled)))
            self._autofill.setVisible(True)
            return
        if self._auto_pump:
            filled.append(pump_name(self._pump_type.currentData()))
        self._autofill.setText(tr("Filled in from earlier jobs: {fields} — type over anything that has changed",
                                  fields=" · ".join(filled)) if filled else "")
        self._autofill.setVisible(bool(filled))

    # ---------------------------------------------------------- ชุดสาย
    def _standard(self) -> dict | None:
        """ชุดสายมาตรฐานของโรงพยาบาลนี้ + เครื่องรุ่นนี้ (ถ้ามี)"""
        return self._book.site_accessory(self._text("site"), self._text("brand"), self._text("model"),
                                         self._pump_type.currentData())

    def _refresh_standard(self) -> None:
        """ชนิดเครื่องเปลี่ยน -> ชุดสายมาตรฐานของชนิดนั้น (เติมทันทีเมื่อช่องว่าง)"""
        if hasattr(self, "_auto"):
            self._autofill_from("site")

    def _check_site_province(self) -> bool:
        """ก่อนไปขั้น 2: จังหวัดต่างจากที่จำไว้ของโรงพยาบาลนี้ -> ถามว่าจำทับไหม (False = กลับไปแก้)"""
        site, province = self._text("site"), self._text("province")
        try:
            known = (self._repository.memory("site", " ".join(site.lower().split())) or {}).get("province", "")
        except Exception:
            known = ""
        if not (site and has(province) and has(known)) or known.strip().lower() == province.lower():
            self._province_update = None
            return True
        key = (site.lower(), province.lower())
        if self._province_key == key and self._province_update is not None:
            return True                         # ตอบไปแล้วสำหรับค่าชุดนี้
        decision = self._ask_province_change(site, known, province)
        if decision is None:
            self._job_edits["province"].setFocus()
            return False
        self._province_update, self._province_key = decision, key
        return True

    def _ask_province_change(self, site: str, old: str, new: str):
        """True = จำจังหวัดใหม่ทับของเดิม · False = ใช้เฉพาะงานนี้ · None = กลับไปแก้ (แยกเมธอดให้ทดสอบแทนได้)"""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(tr("Province changed"))
        box.setText(tr("{site} was saved with the province {old}. This job says {new}.", site=site, old=old, new=new))
        box.setInformativeText(tr("Save {new} as the province of this site for next time?", new=new))
        save = box.addButton(tr("Save as the new province"), QMessageBox.ButtonRole.AcceptRole)
        once = box.addButton(tr("This job only"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(tr("Go back and edit"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(save)
        box.exec()
        return True if box.clickedButton() is save else False if box.clickedButton() is once else None

    def _remember_autofill(self, job: JobInfo) -> None:
        """สร้างการทดสอบแล้ว: จำ โรงพยาบาล->จังหวัด, รุ่น->ยี่ห้อ, ชุดสาย->ยี่ห้อ, S/N/รหัส->เครื่อง (ไว้เติมครั้งหน้า)"""
        data = {name: getattr(job, name) for name in ("site", "province", "department", "model", "brand", "serial_no",
                                                      "asset_id", "accessory", "accessory_brand")}
        data["pump_type"] = job.pump_type.value
        try:
            self._book.remember(data, province_update=self._province_update is not False)
        except Exception:                       # จำไม่ได้ไม่ควรขวางการสร้างการทดสอบ
            pass

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
        # เลขงาน (คำนำหน้า + ตัวเลข) ของงานล่าสุดของเครื่องนี้ — เติมเมื่อช่องเลขยังว่าง (ผู้ใช้ 2026-11-20: "ไม่ยอมดึงตัวเลขข้าง Job")
        # งานเดียวกันมักทำต่อกันหลายโหมด (Inspection แล้ว Calibration เลขงานเดียวกัน) · ช่องที่พิมพ์ไว้แล้วไม่ทับ
        if not self._job_edits["job_no"].text().strip() and str(device.get("job_no") or "").strip():
            job.job_no = str(device["job_no"]).strip()
        try:
            job.pump_type = PumpType(device.get("pump_type", job.pump_type.value))
        except ValueError:
            pass
        self._load_job(job)

    def _load_job(self, job: JobInfo) -> None:
        self._filling = True                    # ค่าที่โหลดมาเป็นค่าจริงของงาน — ไม่เติมทับระหว่างใส่ทีละช่อง
        try:
            self._pump_type.setCurrentIndex(max(0, self._pump_type.findData(job.pump_type.value)))
            prefix, number = split_job_no(job.job_no, self._settings.jobs.prefixes())
            for name, edit in self._job_edits.items():
                value = number if name == "job_no" else getattr(job, name)
                edit.setText("" if value is None else f"{value:g}" if isinstance(value, float) else str(value))
            self._job_prefix.setText(prefix)
        finally:
            self._filling = False
        self._auto, self._auto_pump = {}, None
        self._on_pump_type(self._pump_type.currentData())       # คำนำหน้าเลขงาน MCI/MCS (ถ้าว่าง) + ป้ายชุดสาย
        self._show_autofill()
        self._balance_note.setText(self._balance_text())

    def _balance_text(self) -> str:
        """ตราชั่งมาตรฐาน + วันครบกำหนดสอบเทียบ (เลยกำหนด = เตือน — ผู้ใช้ 2026-11-20)"""
        from datetime import date
        balance = self._settings.balance
        text = tr("Reference balance: {balance} — change it in Settings", balance=balance.label or "—")
        due = (balance.due_date or "").strip()
        self._balance_note.setStyleSheet("")
        if due:
            try:
                day = date.fromisoformat(due)
            except ValueError:
                return text
            overdue = day < date.today()
            thai = tr("Pass") != "Pass"             # จอภาษาไทย = ปี พ.ศ.
            shown = f"{day.day}/{day.month}/{day.year + 543 if thai else day.year}"
            text += "  ·  " + (tr("calibration overdue since {date}", date=shown) if overdue
                               else tr("calibration due {date}", date=shown))
            if overdue:
                self._balance_note.setStyleSheet(f"color: {Color.WARNING};")
        return text

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
        # คำนำหน้า + เลข -> เลขงานแบบเดิม ("MCI" + "26-2201") · ไม่มีเลข = ยังไม่ได้กรอก
        job.job_no = join_job_no(self._job_prefix.text(), self._job_edits["job_no"].text())
        job.balance_id = self._settings.balance.label
        job.accessory_usage = self._accessory_usage
        job.accessories = self._accessories.values()
        job.parts_replaced = self._parts.values()
        job.parts_warranty = self._parts.warranty_values()
        if getattr(self, "_checks", None) is not None:
            pump = self._pump_type.currentData() or "infusion"
            job.checks = report_checklist.compress(pump, self._checks.values())     # เก็บเฉพาะข้อยกเว้น
            job.checks_version = report_checklist.CHECKLIST_VERSION
            job.check_notes = self._checks.notes()
        if getattr(self, "_extras", None) is not None:
            job.report = self._extras.values()      # การอุดตัน ไฟฟ้า ตรวจขั้นสุดท้าย -> ข้อมูลใบของงาน
        if getattr(self, "_trap_yes", None) is not None:
            job.evaporation_trap = "yes" if self._trap_yes.isChecked() else "no"
        if getattr(self, "_service_boxes", None) is not None and self._service_touched:
            chosen = self._service_values()
            # ติ๊กเองและต่างจากที่คิดเอง -> เก็บ · เหมือนกัน -> ว่าง (= คิดเอง)
            job.service_kinds = chosen if set(chosen) != self._auto_service() else []
        return job

    # ================================================================ หน้า 2
    def _build_check_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)
        row = QHBoxLayout()
        row.setSpacing(14)
        outer.addLayout(row, 1)
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

    # ================================================================ หน้า 3
    def _build_report_page(self) -> QWidget:
        """ขั้น 4: ประเภทงานในใบ + ผลตรวจรายข้อ — แก้ภายหลังได้ในข้อมูลใบรายงาน"""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)
        # ประเภทงาน (ผู้ใช้ 2026-11-20): ตั้งให้เองตามโหมด + อะไหล่ (บำรุงรักษาเสมอ) — ติ๊กแก้ได้เฉพาะงานนี้
        service_card = Card(tr("Service type on the report"))
        row = QHBoxLayout()
        row.setSpacing(18)
        self._service_boxes: dict[str, QCheckBox] = {}
        for key, text in SERVICE_KINDS:
            box = QCheckBox(tr(text))
            box.toggled.connect(self._on_service_toggled)
            self._service_boxes[key] = box
            row.addWidget(box)
        row.addStretch(1)
        self._service_auto = QPushButton(tr("Set automatically"))
        self._service_auto.setProperty("variant", "ghost")
        self._service_auto.setToolTip(tr("Preventive maintenance always · Calibration in Calibration mode · "
                                         "Repair when parts were replaced"))
        self._service_auto.clicked.connect(lambda: self._apply_auto_service(force=True))
        row.addWidget(self._service_auto)
        service_card.body.addLayout(row)
        self._service_note = label("", "hint")
        self._service_note.setWordWrap(True)
        service_card.body.addWidget(self._service_note)
        outer.addWidget(service_card)
        self._service_touched = bool(self._initial.job.service_kinds)   # แก้แผนเดิมที่ติ๊กเองไว้ -> คงไว้
        self._service_setting = False
        if self._service_touched:
            self._set_service_boxes(set(self._initial.job.service_kinds))
        checks_card = Card()
        self._checks = InspectionChecks(self._pump_type.currentData() or "infusion")
        self._checks.pass_all()                 # ตั้งต้นทุกข้อ "ผ่าน" — กดเฉพาะข้อที่ไม่ผ่าน/ไม่มี (ผู้ใช้ 2026-11-18)
        checks_card.body.addWidget(self._checks)
        outer.addWidget(checks_card, 1)          # รายการตรวจได้ความสูงที่เหลือทั้งหมด (ไม่เลื่อนในกล่องเล็ก)
        return page

    # ---- ประเภทงาน
    def _auto_service(self) -> set[str]:
        from services.report.model import auto_service_types
        kind = "calibration" if self._mode is RunMode.CALIBRATION else "inspection"
        return auto_service_types(kind, self._parts.values())

    def _set_service_boxes(self, kinds: set[str]) -> None:
        self._service_setting = True
        for key, box in self._service_boxes.items():
            box.setChecked(key in kinds)
        self._service_setting = False
        self._update_service_note()

    def _apply_auto_service(self, force: bool = False) -> None:
        """ตั้งประเภทงานตามโหมด + อะไหล่ — ไม่ทับที่ผู้ใช้ติ๊กเองแล้ว (ยกเว้นกด "ตั้งให้อัตโนมัติ")"""
        if force:
            self._service_touched = False
        if not self._service_touched:
            self._set_service_boxes(self._auto_service())

    def _on_service_toggled(self, _checked: bool) -> None:
        if not self._service_setting:
            self._service_touched = True
            self._update_service_note()

    def _service_values(self) -> list[str]:
        return [key for key, box in self._service_boxes.items() if box.isChecked()]

    def _update_service_note(self) -> None:
        manual = self._service_touched and set(self._service_values()) != self._auto_service()
        self._service_note.setText(tr("Changed by hand for this job.") if manual else
                                   tr("Set automatically: preventive maintenance always, calibration in Calibration "
                                      "mode, repair when parts were replaced — tick to change."))

    def _build_values_page(self) -> QWidget:
        """ขั้น 5: ค่าที่วัด/ตรวจด้วยมือสำหรับใบรายงาน (ย้ายจากขั้น 4 — ผู้ใช้ 2026-11-20 ขั้นเดิมแคบ)"""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)
        extras_card = Card(tr("Measured by hand for the report"))
        self._extras = ReportExtras(self._settings.report.leak_limit_ua)
        pump = self._initial.job.pump_type.value
        self._extras_defaults = defaults_from(self._settings.report, pump)   # ค่าตั้งต้นในหน้าตั้งค่า (ตามชนิดเครื่อง)
        self._extras.set_values(self._initial.job.report or self._extras_defaults)
        extras_card.body.addWidget(self._extras)
        outer.addWidget(extras_card)

        # การระเหยระหว่างวัด (ผู้ใช้ 2026-11-20): ใช้ evaporation trap = ไม่แก้ค่า · ไม่ใช้ = ชดเชยการระเหย (core/evaporation.py)
        evap_card = Card(tr("Evaporation during the measurement"))
        self._trap_group = QButtonGroup(self)
        self._trap_no = QRadioButton(tr("No evaporation trap — correct the result for evaporation"))
        self._trap_yes = QRadioButton(tr("Evaporation trap used (oil layer or cover) — no correction"))
        for button in (self._trap_no, self._trap_yes):
            self._trap_group.addButton(button)
            evap_card.body.addWidget(button)
        trap = self._initial.job.evaporation_trap
        (self._trap_yes if trap == "yes" or (trap == "" and self._settings.evaporation.default_trap)
         else self._trap_no).setChecked(True)
        self._trap_note = label("", "hint")
        self._trap_note.setWordWrap(True)
        evap_card.body.addWidget(self._trap_note)
        self._trap_yes.toggled.connect(lambda _on: self._update_trap_note())
        self._update_trap_note()
        outer.addWidget(evap_card)
        outer.addStretch(1)
        return page

    def _update_trap_note(self) -> None:
        e = self._settings.evaporation
        if self._trap_yes.isChecked():
            text = tr("The report shows the estimated evaporation struck through, with the reason. "
                      "The starting choice is in Settings → New test defaults.")
        else:
            text = tr("Today's self-check is used if there is one; otherwise evaporation is calculated from the vessel "
                      "(Ø {d:g} mm, {v:g} ml at the start) and the air temperature, humidity and pressure — "
                      "vessel size in Settings → Calculation.", d=e.vessel_diameter_mm, v=e.start_volume_ml)
        self._trap_note.setText(text)

    def _apply_value_defaults(self, pump: str) -> None:
        """ชนิดเครื่องเปลี่ยน -> ค่าตั้งต้นการอุดตันของชนิดนั้น (เฉพาะที่ยังเป็นค่าตั้งต้นเดิม)"""
        new = defaults_from(self._settings.report, pump)
        self._extras.apply_defaults(new, self._extras_defaults)
        self._extras_defaults = new

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

    def _show_previous_checks(self) -> None:
        """ผลตรวจรายข้อครั้งล่าสุดของเครื่องนี้ (ยี่ห้อ + รุ่น + S/N) เป็นข้อความจาง — ไม่ติ๊กให้เอง"""
        brand, model = self._device_key()
        serial = self._job_edits["serial_no"].text().strip()
        try:
            found = self._repository.last_device_checks(brand, model, serial)
        except Exception:
            found = None
        if not found:
            self._checks.set_previous("")
            return
        started, job = found
        pump = str(job.get("pump_type") or "infusion")
        full = report_checklist.expand(pump, job.get("checks") or {}, int(job.get("checks_version") or 0))
        lang = "th" if tr("Pass") != "Pass" else "en"
        self._checks.set_previous(tr("Last time ({date}): {result}", date=started[:10],
                                     result=report_checklist.describe(pump, full, lang)))

    def _fill_occlusion_limits(self) -> None:
        """เกณฑ์การอุดตันของผู้ผลิต: เติมจากงานก่อนของรุ่นเดียวกัน (เฉพาะช่องที่ยังว่าง)"""
        brand, model = self._device_key()
        try:
            found = self._repository.last_model_report(brand, model)
        except Exception:
            found = {}
        if found:
            self._extras.set_limits(found, self._extras_defaults)

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

    # ================================================================ หน้า 4
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
        # ประเภทงานในใบ (services.report.model.auto_service_types): บำรุงรักษาเสมอ · Calibration -> สอบเทียบ ด้วย
        # · มีอะไหล่ที่เปลี่ยน -> ซ่อม ด้วย — แก้ได้ในขั้น 4 (ผู้ใช้ 2026-11-20)
        note = label(tr("Service type on the report is set automatically (preventive maintenance always, calibration "
                        "in Calibration mode, repair when parts were replaced) and can be changed in step 4."), "hint")
        note.setWordWrap(True)
        column.addSpacing(14)
        column.addWidget(note)
        column.addStretch(2)
        return page

    def _choose_mode(self, mode: RunMode) -> None:
        # กลับมาโหมดเดิมและชนิดเครื่องเดิม -> คงค่าที่ตั้งไว้ (เปลี่ยนชนิดเครื่อง = ใช้ค่าเริ่มต้นของชนิดใหม่)
        keep = self._mode is mode and bool(self._rows) and self._rows_pump == self._pump_type.currentData()
        self._mode = mode
        if not keep:
            self._apply_mode_defaults()
        self._extras.set_occlusion_visible(mode is RunMode.CALIBRATION)
        self._go(PAGE_REPORT)

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

    # ================================================================ หน้า 5
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
        for column, text in enumerate(ROW_HEADERS):
            self._grid.addWidget(label(tr(text) if text else "", "fieldLabel"), 0, column)
        self._windows_header = self._grid.itemAtPosition(0, ROW_KEYS.index("info")).widget()
        for column in (1, 2, 3, 4, 5):
            self._grid.setColumnStretch(column, 1)
        rates.body.addLayout(self._grid)
        layout.addWidget(rates)
        layout.addStretch()

        self._add_button.clicked.connect(lambda: (self._add_row(self._last_step()), self._refresh_settings()))
        for combo in (self._strategy, self._end_mode, self._start_mode, self._window_source):
            combo.currentIndexChanged.connect(self._refresh_settings)
        self._strategy.currentIndexChanged.connect(self._apply_strategy_to_rows)    # เปลี่ยนวิธีด้านบน = ตั้งทุก rate
        for combo in page.findChildren(QComboBox):
            fit_combo(combo)
        return page

    def _apply_strategy_to_rows(self, _index: int = 0) -> None:
        key = self._strategy.currentData()
        for row in self._rows:
            row["method"].setCurrentIndex(max(0, row["method"].findData(key)))
        self._refresh_settings()

    @staticmethod
    def _row_strategy(row: dict):
        return STRATEGIES.get(row["method"].currentData())

    def _last_step(self) -> StepConfig:
        return self._read_step(self._rows[-1]) if self._rows else StepConfig()

    def _add_row(self, step: StepConfig) -> None:
        row = {
            "index": label("", "stepIndex"),
            "rate": number_box(0.1, 2000, step.target_flow, 1, " ml/h"),
            "method": QComboBox(),
            "duration": number_box(0.5, 1440, step.duration_min, 1, " min"),
            "cycles": int_box(1, 10000, step.cycle_count),
            "window": QComboBox(),
            "remove": QPushButton("✕"),
            "info": wrap(label("", "hint")),
            "window_s": step.window_s,
            # สัดส่วนที่กำหนดในแผนเดิม (แก้แผน) — แถวใหม่ = ใช้ค่าที่จำไว้ของรุ่น
            "fractions": (step.regression_fraction, step.half_fraction) if step.regression_fraction > 0 else None,
        }
        row["index"].setAlignment(Qt.AlignmentFlag.AlignCenter)
        fit_combo(row["method"])
        fit_combo(row["window"])
        for key, text in STRATEGIES.choices():
            row["method"].addItem(tr(text), key)
        method = step.strategy or self._strategy.currentData()
        row["method"].setCurrentIndex(max(0, row["method"].findData(method)))
        row["method"].setToolTip(tr("Capture method for this rate"))
        row["method"].currentIndexChanged.connect(lambda: self._refresh_settings())
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
        for key in ROW_KEYS:
            self._grid.removeWidget(row[key])
            row[key].setParent(None)
            row[key].deleteLater()
        self._layout_rows()

    def _layout_rows(self) -> None:
        for number, row in enumerate(self._rows, start=1):
            row["index"].setText(str(number))
            for column, key in enumerate(ROW_KEYS):
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
        row_strategies = [self._row_strategy(row) for row in self._rows] or [strategy]
        can_count = any("count" in item.end_modes for item in row_strategies)
        any_cycles = any(item.uses_cycles for item in row_strategies)
        if not can_count:
            self._end_mode.setCurrentIndex(self._end_mode.findData(EndMode.TIME.value))
        self._end_mode.setEnabled(can_count)
        by_count = self._end_mode.currentData() == EndMode.COUNT.value
        self._delay.setEnabled(self._start_mode.currentData() == StartMode.DELAY.value)
        self._window_source.setEnabled(any_cycles)
        known = self._profile()
        self._recalibrate_button.setEnabled(any_cycles and bool(known and known.runs))
        for row, item in zip(self._rows, row_strategies):
            row_count = by_count and "count" in item.end_modes
            row["duration"].setEnabled(not row_count)
            row["cycles"].setEnabled(row_count)
            row["window"].setEnabled(item.uses_window)
            row["remove"].setEnabled(len(self._rows) > 1)

        hints = [tr(next(text for mode, _, text in START_MODES if mode.value == self._start_mode.currentData()))]
        if len({row["method"].currentData() for row in self._rows}) > 1:
            hints.append(tr("Each rate uses its own capture method; the method above sets every rate at once."))
        if any_cycles:
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
        self._refresh_windows()

    # ------------------------------------------------ หน้าต่างราย rate (ข้อ ก)
    def _rate_windows(self, steps=None, stroke_ml: float | None = None):
        """RateWindow ของทุกแถว (ค่าเดียวกับที่ controller จะใช้)"""
        job = self._read_job()
        if steps is None:
            steps = [self._read_step(row) for row in self._rows]
        overrides = {st.target_flow: (st.regression_fraction, st.half_fraction) for st in steps if st.regression_fraction > 0}
        return plan_windows(self._repository, self._settings.engine, job, [st.target_flow for st in steps],
                            self._sample_period, overrides, stroke_ml)

    def _refresh_windows(self, _strategy=None) -> None:
        cycle_rows = [row for row in self._rows if self._row_strategy(row).uses_cycles]
        self._windows_header.setVisible(bool(cycle_rows))
        for row in self._rows:
            row["info"].setVisible(row in cycle_rows)
        if not cycle_rows:
            return
        items = self._rate_windows([self._read_step(row) for row in cycle_rows])
        for row, item in zip(cycle_rows, items):
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
            strategy=row["method"].currentData() or "",
        )

    # ============================================================ นำทาง
    def _go(self, index: int) -> None:
        index = max(PAGE_JOB, min(PAGE_SETTINGS, index))
        self._pages.setCurrentIndex(index)
        mode_title = next(tr(title) for mode, title, _ in MODES if mode is self._mode)
        titles = [
            (tr("Device and job details"), tr("Who and what is being tested")),
            (tr("Accessories and parts"), tr("Tick what came with the device and what was replaced")),
            (tr("Choose the test mode"), tr("Click a mode to continue")),
            (tr("Checklist"), tr("Service type and the result of each check item, for the report")),
            (tr("Measured values"), tr("Values measured by hand for the report")),
            (tr("{mode} settings", mode=mode_title), tr("Flow rates and how they are measured")),
        ]
        step = tr("Step {n} of {total}", n=index + 1, total=STEP_COUNT)
        self._title.setText(f"{step} · {titles[index][0]}")
        self._subtitle.setText(titles[index][1])
        self._back.setVisible(index > PAGE_JOB)
        self._next.setVisible(index != PAGE_MODE)
        self._next.setText(tr("Create test") if index == PAGE_SETTINGS else tr("Next"))
        if index == PAGE_CHECK:
            self._load_checklists(self._accessories.values(), self._parts.values())
            QTimer.singleShot(0, self, self._offer_warranty_claims)     # ให้หน้า 2 ขึ้นก่อน แล้วจึงถามเรื่องเคลม
        if index == PAGE_REPORT:
            self._show_previous_checks()        # S/N อาจเปลี่ยนโดยรุ่นเดิม
            self._apply_auto_service()          # โหมด/อะไหล่อาจเปลี่ยน — ไม่ทับที่ติ๊กเอง
        if index == PAGE_VALUES:
            self._fill_occlusion_limits()
            self._extras.set_occlusion_visible(self._mode is RunMode.CALIBRATION)
        if index == PAGE_SETTINGS:
            self._refresh_settings()

    def _on_next(self) -> None:
        index = self._pages.currentIndex()
        if index == PAGE_JOB and not (self._check_accessory_standard() and self._check_site_province()):
            return
        if index == PAGE_CHECK and not self._confirm_empty_lists():
            return
        if index < PAGE_SETTINGS:
            self._go(index + 1)
            return
        window_source = self._window_source.currentData()
        steps = [self._read_step(row) for row in self._rows]
        cycle_at = [i for i, step in enumerate(steps) if STRATEGIES.get(step.strategy).uses_cycles]
        if cycle_at and window_source != "recalibrate":
            decision = self._check_calibration([steps[i] for i in cycle_at], window_source)
            if decision is None:
                return
            _key, window_source, checked = decision
            for index, step in zip(cycle_at, checked):      # rate ที่จับรอบปั๊มกลับที่เดิม (เรียงใหม่เฉพาะกลุ่มนี้)
                steps[index] = step
        keys = {step.strategy for step in steps}
        strategy_key = keys.pop() if len(keys) == 1 else self._strategy.currentData()
        can_count = any("count" in STRATEGIES.get(step.strategy).end_modes for step in steps)
        self.plan = TestPlan(
            job=self._read_job(), run_mode=self._mode,
            strategy=strategy_key,
            end_mode=EndMode(self._end_mode.currentData()) if can_count else EndMode.TIME,
            start_mode=StartMode(self._start_mode.currentData()),
            start_delay_s=self._delay.value(),
            tolerance_pct=self._tolerance.value(),
            window_source=window_source,
            steps=steps,
        )
        self._remember_checklists()
        self._remember_autofill(self.plan.job)
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
            return "pump_cycle", window_source, steps
        dialog = self._prompt_calibration(job, items, known_volume, stroke,
                                          recompute=None if known_volume else lambda ml: self._rate_windows(steps, ml))
        if dialog is None or dialog.action is None:
            return None
        strategy_key = "pump_cycle"
        if dialog.action == "calibrate":
            # วัดคาบก่อนทุก rate แล้วปรับหน้าต่างจากผลที่เก็บ (ค่าที่ปรับได้ = "สอบเทียบแล้ว") — rate สูงก่อนถ้าเลือก
            if getattr(dialog, "reorder", None) is not None and dialog.reorder.isChecked():
                steps = sorted(steps, key=lambda st: st.target_flow, reverse=True)
            return strategy_key, "measure" if profile and profile.runs else "profile", steps
        if dialog.action == "time":
            steps = [dataclasses.replace(st, window_s=dialog.time_windows.get(st.target_flow, st.window_s),
                                         strategy="time_interval") for st in steps]
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
