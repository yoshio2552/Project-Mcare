"""TestWizard: สร้างแผนทดสอบ 4 ขั้น
    1) ข้อมูลงาน/เครื่อง — พิมพ์ค้นเครื่องที่เคยทดสอบแล้วดึงข้อมูลมาเติมได้
    2) ตรวจเครื่อง — อุปกรณ์ที่มากับเครื่อง, อะไหล่ที่เปลี่ยน (เลือกจากรายการกลางในหน้าตั้งค่า)
    3) เลือกโหมด: Calibration / Inspection / Quick Test
    4) ตั้งค่าการวัดของโหมดนั้น (rate, วิธีจับ, เงื่อนไขจบ, วิธีเริ่มวัด, ขนาดหน้าต่าง)
ผลลัพธ์คือ TestPlan (อ่านจาก .plan หลัง dialog ปิดแบบ accept)

เพิ่มช่องกรอกข้อมูลงาน: เพิ่ม field ใน core.models.JobInfo แล้วเพิ่ม 1 บรรทัดใน JOB_FIELDS
ทุกช่อง (ยกเว้นหมายเหตุ) เสนอค่าจากงานที่เคยบันทึกเป็นตัวอักษรจาง — กด Tab/Enter เพื่อรับ (services.job_suggestions)
"""
from __future__ import annotations

import copy

from PySide6.QtCore import QStringListModel, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QCompleter, QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from config.constants import (
    DEFAULT_STRATEGY, DEFAULT_TOLERANCE_PCT, MODE_DEFAULTS, RATE_PRESETS, WINDOW_CHOICES_S,
)
from config.i18n import tr
from config.settings import AppSettings
from core.models import EndMode, JobInfo, PumpType, RunMode, StartMode, StepConfig, TestPlan
from core.strategies import STRATEGIES
from config.settings import prerun_group
from ui.dialogs.new_pump import NewPumpDialog
from ui.dialogs.prerun_criteria import PrerunCriteriaDialog
from ui.theme import Color
from ui.widgets.common import Card, divider, int_box, label, number_box
from services.job_suggestions import NO_SUGGESTIONS, JobSuggester
from ui.widgets.pump_type import PumpBadge, PumpBar, PumpTypeSelector
from ui.widgets.smart_edit import SmartLineEdit

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
    ("temperature_c", "Liquid temperature (°C)", "Water density for g → ml", 1),
    ("humidity_pct", "Humidity (%RH)", "Air buoyancy — blank = Settings", 1),
    ("air_temp_c", "Air temperature (°C)", "Blank = liquid temperature", 1),
    ("pressure_hpa", "Air pressure (hPa)", "Blank = Settings", 1),
    ("notes", "Notes", "", 1),
]
_NUMERIC_FIELDS = {"temperature_c", "humidity_pct", "air_temp_c", "pressure_hpa"}
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
    """รายการติ๊กเลือกของ "รุ่นนี้" — คลิกที่ไหนของแถวก็ได้, เพิ่มรายการเองได้, จำไว้ใช้กับรุ่นเดิมครั้งหน้า

    รายการที่รุ่นนี้เคยใช้จะขึ้นก่อน (ใช้บ่อยสุดอยู่บน มีดาวนำหน้า) ตามด้วยรายการกลางจากหน้าตั้งค่า
    คลิกขวาที่รายการของรุ่นเพื่อลบออกจากรุ่นนี้
    """
    forget_requested = Signal(str)

    def __init__(self, title: str):
        super().__init__(title)
        self._count = label("", "hint")
        self.header.addWidget(self._count)
        self._source = label("", "hint")
        self._source.setWordWrap(True)
        self.body.addWidget(self._source)

        self.list = QListWidget()
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.body.addWidget(self.list, 1)

        tools = QHBoxLayout()
        select_all = QPushButton(tr("Select all"))
        clear = QPushButton(tr("Clear"))
        for button in (select_all, clear):
            button.setProperty("variant", "ghost")
            tools.addWidget(button)
        tools.addStretch()
        self.body.addLayout(tools)

        row = QHBoxLayout()
        self._edit = QLineEdit()
        add = QPushButton(tr("Add"))
        row.addWidget(self._edit, 1)
        row.addWidget(add)
        self.body.addLayout(row)

        self._custom: list[str] = []        # รายการที่ผู้ใช้เพิ่มเองในครั้งนี้
        self._model_items: set[str] = set()
        add.clicked.connect(self._add_custom)
        self._edit.returnPressed.connect(self._add_custom)
        self.list.itemClicked.connect(self._toggle)          # คลิกทั้งแถว = ติ๊ก/เอาออก
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        select_all.clicked.connect(lambda: self._set_all(True))
        clear.clicked.connect(lambda: self._set_all(False))

    def set_items(self, device: str, model_items: list[tuple[str, int]], catalog: list[str], checked: list[str]) -> None:
        """เติมรายการ: ของรุ่นนี้ก่อน (ใช้บ่อยสุดอยู่บน) แล้วตามด้วยรายการกลาง"""
        self.list.clear()
        self._model_items = {name for name, _ in model_items}
        uses = dict(model_items)
        for name in dict.fromkeys([*uses, *catalog, *self._custom, *checked]):
            self._add(name, name in checked, uses.get(name))
        self._edit.setPlaceholderText(tr("Add an item for {device}…", device=device) if device else tr("Add another item…"))
        if not device:
            self._source.setText(tr("Enter brand and model in step 1 to keep a list for each model."))
        elif model_items:
            self._source.setText(tr("★ = used with {device} before ({n} items). Right-click a ★ item to remove it from this model.",
                                    device=device, n=len(model_items)))
        else:
            self._source.setText(tr("First time for {device} — what you tick or add is remembered for this model.", device=device))
        self._refresh()

    def _add(self, name: str, checked: bool, uses: int | None = None) -> None:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, name)
        item.setData(Qt.ItemDataRole.UserRole + 1, uses)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)   # ไม่ให้กล่องรับคลิกเอง (กันติ๊กซ้อน)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        if uses is not None:
            item.setToolTip(tr("Ticked {n} times for this model", n=uses))
        self.list.addItem(item)
        self._paint(item)

    def _paint(self, item: QListWidgetItem) -> None:
        """รายการที่ติ๊ก: ตัวหนาสีเด่น · รายการของรุ่น: มีดาวและจำนวนครั้ง"""
        name, uses = item.data(Qt.ItemDataRole.UserRole), item.data(Qt.ItemDataRole.UserRole + 1)
        checked = item.checkState() == Qt.CheckState.Checked
        item.setText(f"★  {name}   ·  {uses}×" if uses else f"★  {name}" if uses is not None else name)
        font = item.font()
        font.setBold(checked)
        item.setFont(font)
        item.setForeground(QColor(Color.ACCENT if checked else Color.TEXT))

    def _toggle(self, item: QListWidgetItem) -> None:
        checked = item.checkState() == Qt.CheckState.Checked
        item.setCheckState(Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked)
        self._paint(item)
        self.list.clearSelection()
        self._refresh()

    def _set_all(self, checked: bool) -> None:
        for index in range(self.list.count()):
            item = self.list.item(index)
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self._paint(item)
        self._refresh()

    def _refresh(self) -> None:
        self._count.setText(tr("{n} of {total} ticked", n=len(self.values()), total=self.list.count()))

    def _add_custom(self) -> None:
        text = self._edit.text().strip()
        self._edit.clear()
        if not text:
            return
        existing = next((self.list.item(i) for i in range(self.list.count())
                         if self.list.item(i).data(Qt.ItemDataRole.UserRole).lower() == text.lower()), None)
        if existing is None:
            self._custom.append(text)
            self._add(text, True)
            self.list.scrollToBottom()
        elif existing.checkState() != Qt.CheckState.Checked:
            self._toggle(existing)
        self._refresh()

    def _on_context_menu(self, position) -> None:
        item = self.list.itemAt(position)
        if item is None or item.data(Qt.ItemDataRole.UserRole) not in self._model_items:
            return
        menu = QMenu(self)
        remove = menu.addAction(tr("Remove from this model"))
        if menu.exec(self.list.mapToGlobal(position)) is remove:
            name = item.data(Qt.ItemDataRole.UserRole)
            self._model_items.discard(name)
            self.list.takeItem(self.list.row(item))
            self.forget_requested.emit(name)
            self._refresh()

    def values(self) -> list[str]:
        items = (self.list.item(i) for i in range(self.list.count()))
        return [i.data(Qt.ItemDataRole.UserRole) for i in items if i.checkState() == Qt.CheckState.Checked]

    def custom_items(self) -> list[str]:
        return list(self._custom)


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
        self._load_checklists(self._initial.job.accessories, self._initial.job.parts_replaced, force=True)
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

        # ชนิดเครื่อง: การ์ดใหญ่สองใบ สีต่างกัน (เลือกผิดเห็นทันที) — อยู่บนสุดของฟอร์ม
        self._pump_type = PumpTypeSelector()
        self._pump_type.changed.connect(self._on_pump_type)
        card.body.addWidget(label(tr("Pump type"), "fieldLabel"))
        card.body.addWidget(self._pump_type)
        card.body.addWidget(divider())
        columns = [self._form(), self._form()]
        self._job_edits: dict[str, QLineEdit] = {}
        for name, text, placeholder, column in JOB_FIELDS:
            edit = QLineEdit() if name in NO_SUGGESTIONS else \
                SmartLineEdit(lambda typed, field=name: self._suggest(field, typed))
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
        layout.addWidget(label(tr("Faint text is a suggestion from earlier tests — press Tab or Enter to accept it, "
                                  "↓ for more, Esc to ignore. Nothing is filled in until you accept."), "hint"))
        layout.addStretch()
        return page

    def _suggest(self, field: str, typed: str) -> list[str]:
        """คำแนะนำของช่อง field ตามบริบทของช่องอื่นที่กรอกแล้ว"""
        job = {name: edit.text().strip() for name, edit in self._job_edits.items()}
        job["pump_type"] = self._pump_type.currentData()
        return self._suggester.suggest(field, job, typed)

    def _on_pump_type(self, key: str) -> None:
        """เปลี่ยนชนิดเครื่อง: สีแถบ/ป้ายเปลี่ยนตาม และค่าเริ่มต้นของการวัด (rate, วิธีจับ) ต้องตั้งใหม่"""
        self._bar.set_pump(key)
        self._badge.set_pump(key)
        self._rows_pump = None

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
        self._accessories = _Checklist(tr("Accessories received with the device"))
        self._parts = _Checklist(tr("Parts replaced"))
        self._accessories.forget_requested.connect(lambda item: self._forget("accessory", item))
        self._parts.forget_requested.connect(lambda item: self._forget("part", item))
        row.addWidget(self._accessories, 1)
        row.addWidget(self._parts, 1)
        self._checklist_device: tuple | None = None     # รุ่นที่รายการบนจอเป็นของมัน
        return page

    def _device_key(self) -> tuple[str, str]:
        return self._job_edits["brand"].text().strip(), self._job_edits["model"].text().strip()

    def _load_checklists(self, accessories: list[str], parts: list[str], force: bool = False) -> None:
        """เติมรายการตรวจเครื่องของรุ่นที่กรอกอยู่ (เรียกเมื่อเข้าหน้านี้ หรือเมื่อรุ่นเปลี่ยน)"""
        brand, model = self._device_key()
        if not force and self._checklist_device == (brand.lower(), model.lower()):
            return
        self._checklist_device = (brand.lower(), model.lower())
        device = " ".join(part for part in (brand, model) if part)
        catalog = self._settings.catalog
        self._accessories.set_items(device, self._repository.model_items(brand, model, "accessory"),
                                    catalog.accessories, accessories)
        self._parts.set_items(device, self._repository.model_items(brand, model, "part"), catalog.parts, parts)

    def _forget(self, kind: str, item: str) -> None:
        brand, model = self._device_key()
        self._repository.forget_item(brand, model, kind, item)

    def _remember_checklists(self) -> None:
        """สร้างการทดสอบแล้ว: จำสิ่งที่ติ๊ก/เพิ่ม ไว้กับรุ่นนี้ (ยิ่งใช้ รายการของรุ่นยิ่งครบ)"""
        brand, model = self._device_key()
        self._repository.remember_items(brand, model, "accessory", self._accessories.custom_items(), self._accessories.values())
        self._repository.remember_items(brand, model, "part", self._parts.custom_items(), self._parts.values())

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
        right.addRow(label(tr("Window sizes"), "fieldLabel"), self._window_source)
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
        row["rate"].valueChanged.connect(lambda: self._refresh_criteria())     # เวลาที่ต้องใช้ตรวจนิ่งขึ้นกับ rate
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
            elif source == "profile":
                hints.append(tr("No profile for this pump yet — the pump cycle will be measured before each rate and saved as its profile."))
        self._hint.setText("  ".join(hints))
        self._refresh_criteria(strategy)

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
        if index == PAGE_CHECK:
            self._load_checklists(self._accessories.values(), self._parts.values())
        if index == PAGE_SETTINGS:
            self._refresh_settings()

    def _on_next(self) -> None:
        index = self._pages.currentIndex()
        if index < PAGE_SETTINGS:
            self._go(index + 1)
            return
        window_source = self._window_source.currentData()
        strategy = STRATEGIES.get(self._strategy.currentData())
        steps = [self._read_step(row) for row in self._rows]
        if strategy.uses_cycles and window_source == "profile" and not self._profile():
            choice = self._ask_unknown_pump()
            if choice is None:
                return
            if choice == "reorder":         # rate สูงก่อน: rate แรกเรียนรู้ปริมาตรต่อรอบได้ไว
                steps.sort(key=lambda step: step.target_flow, reverse=True)
                choice = "profile"
            elif choice == "default":       # ค่าแทนไปก่อนของรุ่นนี้ (การวัดจริงครั้งแรกจะแทนที่)
                job = self._read_job()
                self._repository.set_model_default(job.brand, job.model, job.accessory, self._default_stroke_ml,
                                                   job.pump_type.value)
                choice = "profile"
            window_source = choice
        self.plan = TestPlan(
            job=self._read_job(), run_mode=self._mode,
            strategy=self._strategy.currentData(),
            end_mode=EndMode(self._end_mode.currentData()),
            start_mode=StartMode(self._start_mode.currentData()),
            start_delay_s=self._delay.value(),
            tolerance_pct=self._tolerance.value(),
            window_source=window_source,
            steps=steps,
        )
        self._remember_checklists()
        self.accept()

    def _ask_unknown_pump(self) -> str | None:
        """ปั๊มรุ่นที่ยังไม่มีข้อมูลรอบปั๊ม: เตือนก่อน แล้วให้เลือก (ดู ui/dialogs/new_pump.py)

        คืน "reorder" | "profile" | "default" | "manual" หรือ None (กลับไปแก้)
        "default" -> ปริมาตรต่อรอบที่เลือกอยู่ใน self._default_stroke_ml
        """
        job = self._read_job()
        device = " ".join(part for part in (job.brand, job.model, job.accessory) if part)
        dialog = NewPumpDialog(self, device, [self._read_step(row).target_flow for row in self._rows],
                               self._settings.engine.default_stroke_volume_ml or 0.16,
                               can_remember=bool(job.brand or job.model))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        self._default_stroke_ml = dialog.default_ml
        return dialog.choice
