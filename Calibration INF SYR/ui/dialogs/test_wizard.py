"""TestWizard: สร้างแผนทดสอบ 4 ขั้น
    1) ข้อมูลงาน/เครื่อง — พิมพ์ค้นเครื่องที่เคยทดสอบแล้วดึงข้อมูลมาเติมได้
    2) ตรวจเครื่อง — อุปกรณ์ที่มากับเครื่อง, อะไหล่ที่เปลี่ยน (เลือกจากรายการกลางในหน้าตั้งค่า)
    3) เลือกโหมด: Calibration / Inspection / Quick Test
    4) ตั้งค่าการวัดของโหมดนั้น (rate, วิธีจับ, เงื่อนไขจบ, วิธีเริ่มวัด, ขนาดหน้าต่าง)
ผลลัพธ์คือ TestPlan (อ่านจาก .plan หลัง dialog ปิดแบบ accept)

เพิ่มช่องกรอกข้อมูลงาน: เพิ่ม field ใน core.models.JobInfo แล้วเพิ่ม 1 บรรทัดใน JOB_FIELDS
"""
from __future__ import annotations

import copy

from PySide6.QtCore import QStringListModel, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QCompleter, QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from config.constants import (
    DEFAULT_STRATEGY, DEFAULT_TOLERANCE_PCT, MODE_DEFAULTS, RATE_PRESETS, WINDOW_CHOICES_S,
)
from config.i18n import tr
from config.settings import AppSettings
from core.models import EndMode, JobInfo, PumpType, RunMode, StartMode, StepConfig, TestPlan
from core.strategies import STRATEGIES
from ui.widgets.common import Card, divider, int_box, label, number_box

# (ชื่อ field ใน JobInfo, ป้าย, ข้อความตัวอย่าง, คอลัมน์)  — ช่องข้อความทั่วไป
JOB_FIELDS = [
    ("brand", "Brand", "", 0),
    ("model", "Model", "", 0),
    ("serial_no", "Serial no.", "", 0),
    ("asset_id", "Asset ID", "", 0),
    ("department", "Department", "", 0),
    ("accessory", "Syringe / IV set", "Brand and type — part of the pump profile", 1),
    ("operator", "Operator", "", 1),
    ("balance_id", "Balance ID", "Reference balance used", 1),
    ("temperature_c", "Liquid temperature (°C)", "Used to convert g to ml", 1),
    ("humidity_pct", "Humidity (%RH)", "", 1),
    ("notes", "Notes", "", 1),
]
_NUMERIC_FIELDS = {"temperature_c", "humidity_pct"}
_DEVICE_FIELDS = ("brand", "model", "serial_no", "asset_id", "department", "accessory")

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
WINDOW_SOURCES = [
    ("profile", "From the pump profile"),
    ("measure", "Measure the pump cycle before each rate"),
    ("manual", "Manual (values in Settings)"),
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


class _Checklist(Card):
    """รายการติ๊กเลือก + เพิ่มรายการเองได้"""

    def __init__(self, title: str, options: list[str], checked: list[str]):
        super().__init__(title)
        self.list = QListWidget()
        self.body.addWidget(self.list, 1)
        for text in list(dict.fromkeys([*options, *checked])):
            self._add(text, text in checked)
        row = QHBoxLayout()
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(tr("Add another item…"))
        add = QPushButton(tr("Add"))
        row.addWidget(self._edit, 1)
        row.addWidget(add)
        self.body.addLayout(row)
        add.clicked.connect(self._add_custom)
        self._edit.returnPressed.connect(self._add_custom)

    def _add(self, text: str, checked: bool) -> None:
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.list.addItem(item)

    def _add_custom(self) -> None:
        text = self._edit.text().strip()
        if text and text not in self.values(all_items=True):
            self._add(text, True)
        self._edit.clear()

    def values(self, all_items: bool = False) -> list[str]:
        items = (self.list.item(i) for i in range(self.list.count()))
        return [i.text() for i in items if all_items or i.checkState() == Qt.CheckState.Checked]


class TestWizard(QDialog):
    def __init__(self, parent: QWidget, repository, settings: AppSettings, initial: TestPlan | None = None):
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

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)
        self._title = label("", "pageTitle")
        self._subtitle = label("", "pageSubtitle")
        root.addWidget(self._title)
        root.addWidget(self._subtitle)

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
        self._go(PAGE_JOB)

    # ================================================================ หน้า 1
    def _build_job_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        card = Card()
        self._search = DeviceSearch(self._repository)
        self._search.picked.connect(self._on_recall)
        recall = QHBoxLayout()
        recall.addWidget(label(tr("Recall"), "fieldLabel"))
        recall.addWidget(self._search, 1)
        card.body.addLayout(recall)
        card.body.addWidget(divider())

        self._pump_type = QComboBox()
        self._pump_type.addItem(tr("Infusion pump"), PumpType.INFUSION.value)
        self._pump_type.addItem(tr("Syringe pump"), PumpType.SYRINGE.value)
        columns = [self._form(), self._form()]
        columns[0].addRow(label(tr("Pump type"), "fieldLabel"), self._pump_type)
        self._job_edits: dict[str, QLineEdit] = {}
        for name, text, placeholder, column in JOB_FIELDS:
            edit = QLineEdit()
            edit.setPlaceholderText(tr(placeholder) if placeholder else "")
            self._job_edits[name] = edit
            columns[column].addRow(label(tr(text), "fieldLabel"), edit)
        grid = QHBoxLayout()
        grid.setSpacing(28)
        grid.addLayout(columns[0], 1)
        grid.addLayout(columns[1], 1)
        card.body.addLayout(grid)
        layout.addWidget(card)
        layout.addWidget(label(tr("All fields are optional, but they are saved with the result and used for traceability."), "hint"))
        layout.addStretch()
        return page

    @staticmethod
    def _form() -> QFormLayout:
        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(9)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        return form

    def _on_recall(self, device: dict) -> None:
        """เติมข้อมูลตัวเครื่องจากรายการที่เลือก (ไม่ทับข้อมูลของงานครั้งนี้ เช่น ผู้ทดสอบ อุณหภูมิ)"""
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
        job.accessories = self._accessories.values()
        job.parts_replaced = self._parts.values()
        return job

    # ================================================================ หน้า 2
    def _build_check_page(self) -> QWidget:
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        catalog, job = self._settings.catalog, self._initial.job
        self._accessories = _Checklist(tr("Accessories received with the device"), catalog.accessories, job.accessories)
        self._parts = _Checklist(tr("Parts replaced"), catalog.parts, job.parts_replaced)
        row.addWidget(self._accessories, 1)
        row.addWidget(self._parts, 1)
        return page

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
        keep = self._mode is mode and bool(self._rows)     # กลับมาโหมดเดิม -> คงค่าที่ตั้งไว้
        self._mode = mode
        if not keep:
            self._apply_mode_defaults()
        self._go(PAGE_SETTINGS)

    def _apply_mode_defaults(self) -> None:
        pump = self._pump_type.currentData()
        plan = self._initial
        if plan.run_mode is self._mode and plan.job_id:      # แก้ไขแผนเดิมของโหมดเดิม -> ใช้ค่าเดิม
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
        right.addRow(label(tr("Window sizes"), "fieldLabel"), self._window_source)
        columns = QHBoxLayout()
        columns.setSpacing(28)
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)
        method.body.addLayout(columns)
        self._hint = label("", "hint")
        self._hint.setWordWrap(True)
        method.body.addWidget(self._hint)
        layout.addWidget(method)

        # ---- รายการ rate
        rates = Card(tr("Flow rates"))
        self._add_button = QPushButton(tr("+ Add rate"))
        self._add_button.setProperty("variant", "ghost")
        rates.header.addWidget(self._add_button)
        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(10)
        self._grid.setVerticalSpacing(8)
        for column, text in enumerate(("", "Target rate", "Duration", "Pump cycles", "Interval length", "")):
            self._grid.addWidget(label(tr(text) if text else "", "fieldLabel"), 0, column)
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
            "window_s": step.window_s,
        }
        row["index"].setAlignment(Qt.AlignmentFlag.AlignCenter)
        row["remove"].setProperty("variant", "ghost")
        row["remove"].setToolTip(tr("Remove this rate"))
        row["remove"].clicked.connect(lambda: (self._remove_row(row), self._refresh_settings()))
        row["duration"].valueChanged.connect(lambda: self._fill_windows(row))
        row["window"].activated.connect(lambda: row.__setitem__("window_s", row["window"].currentData()))
        self._rows.append(row)
        self._fill_windows(row)
        self._layout_rows()

    def _remove_row(self, row: dict) -> None:
        self._rows.remove(row)
        for key in ("index", "rate", "duration", "cycles", "window", "remove"):
            self._grid.removeWidget(row[key])
            row[key].setParent(None)
            row[key].deleteLater()
        self._layout_rows()

    def _layout_rows(self) -> None:
        for number, row in enumerate(self._rows, start=1):
            row["index"].setText(str(number))
            for column, key in enumerate(("index", "rate", "duration", "cycles", "window", "remove")):
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
        return self._repository.get_profile(job.brand, job.model, job.accessory)

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
            elif source == "profile":
                hints.append(tr("No profile for this pump yet — the pump cycle will be measured before each rate and saved as its profile."))
        self._hint.setText("  ".join(hints))

    def _read_step(self, row: dict) -> StepConfig:
        return StepConfig(
            target_flow=row["rate"].value(), duration_min=row["duration"].value(),
            cycle_count=row["cycles"].value(), window_s=float(row["window"].currentData() or 30.0),
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
        if index == PAGE_SETTINGS:
            self._refresh_settings()

    def _on_next(self) -> None:
        index = self._pages.currentIndex()
        if index < PAGE_SETTINGS:
            self._go(index + 1)
            return
        window_source = self._window_source.currentData()
        strategy = STRATEGIES.get(self._strategy.currentData())
        if strategy.uses_cycles and window_source == "profile" and not self._profile():
            window_source = self._ask_unknown_pump()
            if window_source is None:
                return
        self.plan = TestPlan(
            job=self._read_job(), run_mode=self._mode,
            strategy=self._strategy.currentData(),
            end_mode=EndMode(self._end_mode.currentData()),
            start_mode=StartMode(self._start_mode.currentData()),
            start_delay_s=self._delay.value(),
            tolerance_pct=self._tolerance.value(),
            window_source=window_source,
            steps=[self._read_step(row) for row in self._rows],
        )
        self.accept()

    def _ask_unknown_pump(self) -> str | None:
        """ปั๊มรุ่นที่ยังไม่เคยเจอ: ถามว่าจะให้เรียนรู้รอบปั๊ม หรือใช้ค่ากำหนดเอง"""
        job = self._read_job()
        box = QMessageBox(self)
        box.setWindowTitle(tr("New pump model"))
        box.setText(tr("There is no pump profile for this brand, model and IV set yet."))
        details = tr("The program can measure the pump cycle before each rate (this adds a short wait of about "
                     "three pump cycles) and remember it, so later tests of this pump start without that wait.")
        if not (job.brand or job.model):
            details += "\n\n" + tr("Brand and model are empty, so the result cannot be remembered for next time.")
        box.setInformativeText(details)
        learn = box.addButton(tr("Measure and learn"), QMessageBox.ButtonRole.AcceptRole)
        manual = box.addButton(tr("Use manual sizes"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(tr("Cancel"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is learn:
            return "profile"        # ยังไม่มีโปรไฟล์ = วัดก่อนเริ่ม; พอมีแล้วขั้นถัดไปจะใช้โปรไฟล์เอง
        if box.clickedButton() is manual:
            return "manual"
        return None
