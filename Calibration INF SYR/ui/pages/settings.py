"""หน้า Settings: แก้ค่าตั้งของระบบ (หน้าจอ, ตราชั่ง, การคำนวณ, self-check, รายการตรวจเครื่อง)

ฟอร์มสร้างจากตาราง GROUPS — เพิ่มค่าตั้งใหม่ = เพิ่ม field ใน config/settings.py
แล้วเพิ่ม 1 บรรทัดในตารางนี้ ไม่ต้องเขียน widget เอง
ค่าที่บันทึกมีผลกับการทดสอบ "ครั้งถัดไป" (การทดสอบที่กำลังเดินใช้สำเนาค่าตอนเริ่ม)
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractSpinBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLineEdit,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from config.i18n import LANGUAGES, tr
from config.settings import AppSettings
from hardware import SOURCES
from hardware.parsers import format_choices
from hardware.serial_balance import Detection, detect_settings, list_ports
from ui.icons import Glyph, glyph_icon
from ui.theme import Color
from ui.widgets.common import Card, PageHeader, label


@dataclass
class Field:
    section: str            # ชื่อ attribute ของ AppSettings ("" = ระดับบนสุด)
    name: str               # ชื่อ field
    text: str               # ป้ายบนจอ
    minimum: float = 0
    maximum: float = 1e6
    decimals: int = 0       # ใช้กับ float
    suffix: str = ""
    choices: object = None  # list ของ (ค่า, ข้อความ) หรือ callable ที่คืน list -> ใช้ combo box
    editable: bool = False
    hint: str = ""
    translate: bool = True  # แปลข้อความของตัวเลือกใน combo ไหม
    kind: str = ""          # "" = ตามชนิดของค่า, "text" = ข้อความ, "lines" = รายการ (บรรทัดละ 1 รายการ)


_ON_OFF = [(True, "On"), (False, "Off")]
DATA_SOURCE = "Data source"

GROUPS: list[tuple[str, list[Field]]] = [
    ("Interface", [
        Field("ui", "language", "Language", choices=lambda: list(LANGUAGES.items()), translate=False),
        Field("ui", "sound_on_finish", "Sound when a test finishes", choices=_ON_OFF),
        Field("ui", "confirm_stop", "Confirm before stopping", choices=_ON_OFF),
    ]),
    (DATA_SOURCE, [
        Field("", "source", "Source", choices=lambda: SOURCES.choices(),
              hint="Simulator lets you try the program without a balance connected"),
        Field("serial", "port", "Port", choices=lambda: [(p, p) for p in list_ports()], editable=True, translate=False),
        Field("serial", "baudrate", "Baud rate", translate=False,
              choices=[(b, str(b)) for b in (1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200)]),
        Field("serial", "bytesize", "Data bits", choices=[(7, "7"), (8, "8")], translate=False),
        Field("serial", "parity", "Parity", choices=[("N", "None"), ("E", "Even"), ("O", "Odd")]),
        Field("serial", "stopbits", "Stop bits", choices=[(1, "1"), (2, "2")], translate=False),
        Field("serial", "mode", "Balance output", choices=[
            ("auto", "Auto detect"), ("stream", "Stream (balance sends by itself)"), ("poll", "Ask for each value"),
        ], hint="Auto listens first; if the balance is silent it asks for values instead"),
        Field("serial", "poll_interval_s", "Ask every", 0.02, 5, 2, " s"),
        Field("serial", "response_timeout_s", "Wait for a full answer up to", 0.1, 10, 2, " s",
              hint="Lines that are still incomplete after this are discarded (GF-300 answers in about 0.2 s)"),
        Field("serial", "line_format", "Line format", choices=format_choices,
              hint="Strict A&D only accepts complete lines; the looser formats can misread a cut-off line"),
        Field("replay", "path", "Replay file", kind="text", hint="A raw.csv or capture file recorded earlier (time, weight)"),
        Field("replay", "speed", "Replay speed", 0.1, 500, 1, " x"),
    ]),
    ("Calculation", [
        Field("engine", "density_g_per_ml", "Liquid density", 0.5, 2.0, 4, " g/ml",
              hint="Used only when no liquid temperature is entered in the test form"),
        Field("engine", "air_buoyancy", "Air buoyancy correction (ISO 4787)", choices=_ON_OFF,
              hint="g → ml with the Z factor: water density from liquid temperature, air density from "
                   "air temperature, humidity and pressure (about +0.1 %)"),
        Field("engine", "default_humidity_pct", "Humidity if not entered", 0, 100, 0, " %RH"),
        Field("engine", "default_pressure_hpa", "Air pressure if not entered", 500, 1200, 2, " hPa"),
        Field("engine", "reference_density_g_per_ml", "Density of the balance's reference weights", 1, 25, 2, " g/ml",
              hint="Stainless steel calibration weights = 8.0 g/ml (OIML R111)"),
        Field("engine", "warmup_s", "Warm-up", 0, 600, 1, " s"),
        Field("engine", "regression_window", "Regression window", 3, 5000, suffix=" pts",
              hint="Manual window sizes — used when a test is set to manual, or the pump cycle cannot be found"),
        Field("engine", "cycle_half_window", "Cycle half-window (n_bar)", 1, 5000, suffix=" pts"),
        Field("engine", "auto_window_fraction", "Window / pump cycle", 0.1, 0.49, 2,
              hint="Size of both windows as a fraction of the pump cycle (profile or measured)"),
        Field("engine", "cycle_chains", "Pump-cycle capture", choices=[
            (2, "Paired cycles (peak→peak and valley→valley)"), (1, "Single cycle (one reference point)"),
        ], hint="Paired runs two chains of intervals side by side; single keeps only chain A"),
        Field("engine", "auto_tune_timeout_s", "Stop looking for the cycle after", 30, 3600, 0, " s"),
    ]),
    ("Automatic start (stable flow)", [
        Field("engine", "stability_pct", "Allowed flow variation", 0.1, 50, 1, " %",
              hint="An allowance for the balance resolution is added automatically at low rates"),
        Field("engine", "stability_window_s", "Block length", 2, 600, 1, " s"),
        Field("engine", "stability_blocks", "Blocks compared", 2, 20),
    ]),
    ("Self-check", [
        Field("selfcheck", "duration_min", "Duration", 1, 240, 0, " min"),
        Field("selfcheck", "max_halves_z", "Change must exceed balance noise by", 1, 10, 1, " ×",
              hint="Not settled = the two halves differ by more than this many times their uncertainty (from 10 blocks)"),
        Field("selfcheck", "max_halves_diff_mg_h", "Always accept a change between halves up to", 1, 1000, 0, " mg/h",
              hint="Smaller differences than this never count as unsettled — they are too small to matter"),
        Field("selfcheck", "max_abs_rate_mg_h", "Largest believable rate", 10, 10000, 0, " mg/h"),
    ]),
    ("Device check lists", [
        Field("catalog", "accessories", "Accessories", kind="lines", hint="One item per line"),
        Field("catalog", "parts", "Replaceable parts", kind="lines"),
    ]),
    ("Simulator", [
        Field("simulator", "speed", "Time speed-up", 0.1, 500, 1, " x"),
        Field("simulator", "error_pct", "Pump error", -50, 50, 2, " %"),
        Field("simulator", "ripple_pct", "Flow ripple", 0, 95, 1, " %"),
        Field("simulator", "cycle_period_s", "Cycle period", 1, 3600, 1, " s"),
        Field("simulator", "evaporation_mg_h", "Evaporation", 0, 5000, 0, " mg/h"),
    ]),
]


# กลุ่มที่อยู่คอลัมน์ซ้าย (ที่เหลืออยู่ขวา)
LEFT_COLUMN = {"Interface", "Calculation", "Self-check", "Simulator"}


class _DetectWorker(QObject):
    progress = Signal(str)
    done = Signal(object)       # Detection | None | Exception

    def __init__(self, serial_settings):
        super().__init__()
        self._settings = serial_settings
        self.cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            self.done.emit(detect_settings(self._settings, progress=self.progress.emit,
                                           should_stop=lambda: self.cancelled))
        except Exception as exc:
            self.done.emit(exc)


class SettingsPage(QWidget):
    saved = Signal()

    def __init__(self, settings: AppSettings, pause_balance=None, resume_balance=None):
        """pause_balance / resume_balance: ฟังก์ชันปล่อย/คืนพอร์ตตราชั่งระหว่างค้นหาอัตโนมัติ"""
        super().__init__()
        self.setObjectName("page")
        self._settings = settings
        self._pause_balance, self._resume_balance = pause_balance, resume_balance
        self._editors: list[tuple[Field, QWidget]] = []
        self._cards: dict[str, Card] = {}
        self._detect_thread: QThread | None = None
        self._detect_worker: _DetectWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        header = PageHeader(tr("Settings"), tr("Saved values apply from the next test"))
        self.status = label("", "hint")
        reset = QPushButton(tr("Reset to defaults"))
        save = QPushButton("  " + tr("Save"))
        save.setProperty("variant", "primary")
        save.setIcon(glyph_icon(Glyph.SAVE, Color.ON_ACCENT, size=14))
        save.setStyleSheet("padding: 7px 18px; font-size: 13px;")
        for widget in (self.status, reset, save):
            header.actions.addWidget(widget)
        layout.addWidget(header)

        columns = [QVBoxLayout(), QVBoxLayout()]
        for title, group_fields in GROUPS:
            columns[0 if title in LEFT_COLUMN else 1].addWidget(self._build_group(title, group_fields))
        self._add_detect_row()
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(14)
        for column in columns:
            column.setSpacing(14)
            column.addStretch()
            content_layout.addLayout(column, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        save.clicked.connect(self._save)
        reset.clicked.connect(self._reset)
        self.load()

    # ------------------------------------------------------------ สร้าง UI
    def _build_group(self, title: str, group_fields: list[Field]) -> Card:
        card = Card(tr(title))
        self._cards[title] = card
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for f in group_fields:
            editor = self._build_editor(f)
            self._editors.append((f, editor))
            row = editor
            if f.editable and callable(f.choices):      # combo ที่รายการเปลี่ยนได้ -> มีปุ่ม refresh
                row = QWidget()
                box = QHBoxLayout(row)
                box.setContentsMargins(0, 0, 0, 0)
                box.setSpacing(6)
                refresh = QPushButton()
                refresh.setIcon(glyph_icon(Glyph.REFRESH, Color.TEXT, size=14))
                refresh.setToolTip(tr("Scan for ports"))
                refresh.clicked.connect(lambda _=False, fd=f, ed=editor: self._fill_combo(fd, ed, ed.currentText()))
                box.addWidget(editor, 1)
                box.addWidget(refresh)
            form.addRow(label(tr(f.text), "fieldLabel"), row)
            if f.hint:
                hint = label(tr(f.hint), "hint")
                hint.setWordWrap(True)
                form.addRow("", hint)
        card.body.addLayout(form)
        card.body.addStretch()
        return card

    def _build_editor(self, f: Field) -> QWidget:
        if f.choices is not None:
            combo = QComboBox()
            combo.setEditable(f.editable)
            return combo
        if f.kind == "text":
            return QLineEdit()
        if f.kind == "lines":
            editor = QPlainTextEdit()
            editor.setFixedHeight(128)
            return editor
        current = getattr(self._target(f), f.name)
        box = QDoubleSpinBox() if isinstance(current, float) else QSpinBox()
        if isinstance(box, QDoubleSpinBox):
            box.setDecimals(f.decimals)
            box.setRange(f.minimum, f.maximum)
        else:
            box.setRange(int(f.minimum), int(f.maximum))
        box.setSuffix(f.suffix)
        box.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return box

    def _fill_combo(self, f: Field, combo: QComboBox, value) -> None:
        choices = f.choices() if callable(f.choices) else f.choices
        combo.clear()
        for data, text in choices:
            combo.addItem(tr(text) if f.translate else text, data)
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
        elif f.editable:
            combo.setEditText(str(value))

    def _target(self, f: Field):
        return getattr(self._settings, f.section) if f.section else self._settings

    # ---------------------------------------------------------- load / save
    def _set_editor(self, f: Field, editor: QWidget, value) -> None:
        if isinstance(editor, QComboBox):
            self._fill_combo(f, editor, value)
        elif isinstance(editor, QLineEdit):
            editor.setText(str(value))
        elif isinstance(editor, QPlainTextEdit):
            editor.setPlainText("\n".join(value))
        else:
            editor.setValue(value)

    def _read_editor(self, f: Field, editor: QWidget):
        if isinstance(editor, QComboBox):
            return editor.currentText().strip() if f.editable else editor.currentData()
        if isinstance(editor, QLineEdit):
            return editor.text().strip()
        if isinstance(editor, QPlainTextEdit):
            return [line.strip() for line in editor.toPlainText().splitlines() if line.strip()]
        return editor.value()

    def load(self) -> None:
        for f, editor in self._editors:
            self._set_editor(f, editor, getattr(self._target(f), f.name))

    def _save(self) -> None:
        for f, editor in self._editors:
            setattr(self._target(f), f.name, self._read_editor(f, editor))
        try:
            self._settings.save()
            self.status.setText(tr("Saved ✓"))
        except OSError as exc:
            self.status.setText(tr("Could not save: {error}", error=exc))
        self.saved.emit()

    def _reset(self) -> None:
        self._settings.reset()
        self.load()
        self.status.setText(tr("Defaults restored (not saved yet)"))

    # ------------------------------------------------------ ค้นหาตราชั่งอัตโนมัติ
    def _add_detect_row(self) -> None:
        card = self._cards[DATA_SOURCE]
        row = QHBoxLayout()
        self.btn_detect = QPushButton(tr("Find the balance automatically"))
        self.btn_detect.setToolTip(tr("Tries the ports and the usual port settings until the balance answers"))
        self.detect_status = label("", "hint")
        self.detect_status.setWordWrap(True)
        row.addWidget(self.btn_detect)
        row.addWidget(self.detect_status, 1)
        card.body.insertLayout(card.body.count() - 1, row)
        self.btn_detect.clicked.connect(self._toggle_detect)

    def _editor(self, section: str, name: str) -> tuple[Field, QWidget]:
        return next((f, e) for f, e in self._editors if f.section == section and f.name == name)

    def _toggle_detect(self) -> None:
        if self._detect_worker is not None:             # กดอีกครั้ง = ยกเลิก
            self._detect_worker.cancelled = True
            return
        current = dataclasses.replace(self._settings.serial)
        for name in ("port", "baudrate", "bytesize", "parity", "stopbits"):   # เริ่มจากค่าที่เห็นบนจอ
            setattr(current, name, self._read_editor(*self._editor("serial", name)))
        if self._pause_balance:
            self._pause_balance()
        self.btn_detect.setText(tr("Cancel"))
        self._detect_worker = _DetectWorker(current)
        self._detect_thread = QThread(self)
        self._detect_worker.moveToThread(self._detect_thread)
        self._detect_thread.started.connect(self._detect_worker.run)
        self._detect_worker.progress.connect(lambda text: self.detect_status.setText(tr("Trying {what}…", what=text)))
        self._detect_worker.done.connect(self._on_detect_done)
        self._detect_thread.start()

    @Slot(object)
    def _on_detect_done(self, result) -> None:
        self._detect_thread.quit()
        self._detect_thread.wait(3000)
        self._detect_thread = self._detect_worker = None
        self.btn_detect.setText(tr("Find the balance automatically"))
        if isinstance(result, Detection):
            for name in ("port", "baudrate", "bytesize", "parity", "stopbits", "mode"):
                self._set_editor(*self._editor("serial", name), getattr(result, name))
            self._set_editor(*self._editor("", "source"), "serial")
            self.detect_status.setText(tr(
                "Found: {port} · {baud} {bits}{parity}{stop} · {mode} · about {rate:.0f} values/s — "
                "press Save to use it.   Sample: {line}",
                port=result.port, baud=result.baudrate, bits=result.bytesize, parity=result.parity,
                stop=result.stopbits, mode=result.mode, rate=result.rate_hz, line=result.sample_line))
        elif isinstance(result, Exception):
            self.detect_status.setText(tr("Search failed: {error}", error=result))
        else:
            self.detect_status.setText(tr("No balance answered. Check the cable, power and the balance's output setting."))
        if self._resume_balance:
            self._resume_balance()
