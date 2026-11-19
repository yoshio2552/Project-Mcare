"""หน้าต่าง "ความซ้ำของการวัด (2SD)" — ตั้งค่า → ความไม่แน่นอน (core/repeatability.py)

    ┌ ตาราง: ยี่ห้อ รุ่น · ชนิด · ชุดสาย · rate · 2SD % · 2SD ml/h · จำนวนชุด · สถานะ (มีค่าแล้ว / ยังไม่มี) ┐
    │  ยังไม่มี = เคยทดสอบรุ่น/ชุดสาย/rate นี้แล้ว แต่ยังไม่มีค่า -> กด "สอบเทียบ" ได้เลย                    │
    └ ชุดของแถวที่เลือก: วันที่ · ที่มา (วัด N ครั้ง / กรอกเอง) · ผลแต่ละครั้ง · 2SD ของชุด · ลบชุดได้             ┘
ค่าที่ใช้ = ค่าเฉลี่ยของ 2SD ทุกชุด · สอบเทียบซ้ำ = ชุดใหม่ (ชุดเดิมไม่ถูกลบ) · ลบชุด = ไม่นับในค่าเฉลี่ย (แถวยังอยู่ในฐานข้อมูล)
สอบเทียบ: สร้างแผน RunMode.REPEATABILITY (rate เดียว N ครั้ง) แล้วส่งไปหน้าทดสอบ (start_requested) — จบครบทุกครั้ง
SessionController._save_repeat_study บันทึกชุดให้เอง
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from config.i18n import tr
from core.models import EndMode, JobInfo, PumpType, RunMode, StartMode, StepConfig, TestPlan
from core.repeatability import UNITS, Study, from_input
from core.strategies import STRATEGIES
from ui.theme import Color
from ui.widgets.common import label, number_box

PUMPS = (("infusion", "Infusion pump"), ("syringe", "Syringe pump"))
CAPTURE = ("pump_cycle", "time_interval")


def _item(text, align_right=False):
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if align_right:
        item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
    return item


class _Combo(QFormLayout):
    """ช่อง ยี่ห้อ / รุ่น / ชนิด / ชุดสาย / rate (ใช้ร่วมกันในหน้าต่างกรอกค่าและสอบเทียบ)"""

    def __init__(self, row: dict | None):
        super().__init__()
        row = row or {}
        self.brand, self.model, self.iv_set = QLineEdit(row.get("brand", "")), QLineEdit(row.get("model", "")), \
            QLineEdit(row.get("iv_set", ""))
        self.pump = QComboBox()
        for key, text in PUMPS:
            self.pump.addItem(tr(text), key)
        self.pump.setCurrentIndex(max(0, self.pump.findData(row.get("pump_type", "infusion"))))
        self.rate = number_box(0.01, 2000, float(row.get("rate") or 50.0), 2, " ml/h")
        for text, widget in (("Brand", self.brand), ("Model", self.model), ("Pump type", self.pump),
                             ("IV set / syringe", self.iv_set), ("Rate", self.rate)):
            self.addRow(label(tr(text), "fieldLabel"), widget)

    def values(self) -> dict:
        return {"brand": self.brand.text().strip(), "model": self.model.text().strip(), "pump_type": self.pump.currentData(),
                "iv_set": self.iv_set.text().strip(), "rate": self.rate.value()}


class EntryDialog(QDialog):
    """กรอก 2SD เอง (จากงานวิจัยของผู้ใช้) — เป็น % ของ rate หรือ ± ml/h ที่ rate นั้น"""

    def __init__(self, parent, row: dict | None):
        super().__init__(parent)
        self.setWindowTitle(tr("Enter 2SD"))
        layout = QVBoxLayout(self)
        self.combo = _Combo(row)
        self.value = number_box(0, 1000, 0.0, 4)
        self.unit = QComboBox()
        for unit in UNITS:
            self.unit.addItem(unit, unit)
        value_row = QHBoxLayout()
        value_row.addWidget(self.value, 1)
        value_row.addWidget(self.unit)
        self.combo.addRow(label(tr("2SD"), "fieldLabel"), value_row)
        self.note = QLineEdit()
        self.note.setPlaceholderText(tr("Where the value comes from (study, date…)"))
        self.combo.addRow(label(tr("Note"), "fieldLabel"), self.note)
        self.preview = label("", "hint")
        layout.addLayout(self.combo)
        layout.addWidget(self.preview)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for signal in (self.value.valueChanged, self.unit.currentIndexChanged, self.combo.rate.valueChanged):
            signal.connect(self._update_preview)
        self._update_preview()

    def _update_preview(self, *_):
        try:
            pct, mlh = from_input(self.value.value(), self.unit.currentData(), self.combo.rate.value())
        except ValueError:
            self.preview.setText("")
            return
        self.preview.setText(tr("= 2SD {pct:.4f} % = ± {mlh:.4f} ml/h at {rate:g} ml/h", pct=pct, mlh=mlh,
                                rate=self.combo.rate.value()))

    def _accept(self):
        values = self.combo.values()
        if not values["model"]:
            QMessageBox.warning(self, tr("Enter 2SD"), tr("Enter the model."))
            return
        self.result_values = values
        pct, mlh = from_input(self.value.value(), self.unit.currentData(), values["rate"])
        self.study = Study(kind="manual", rate=values["rate"], sd2_pct=pct, sd2_ml_h=mlh, input_value=self.value.value(),
                           input_unit=self.unit.currentData(), note=self.note.text().strip())
        self.accept()


class StudyDialog(QDialog):
    """สอบเทียบความซ้ำ: rate เดียว N ครั้ง วิธีจับรอบปั๊มหรือแบ่งช่วงเวลา (ผลแต่ละครั้ง = ปริมาตรรวม ÷ เวลารวม)"""

    def __init__(self, parent, row: dict | None, runs: int):
        super().__init__(parent)
        self.setWindowTitle(tr("Repeatability study"))
        layout = QVBoxLayout(self)
        intro = label(tr("The same rate is measured {n} times. Each run gives one measured flow "
                         "(total volume ÷ total time); 2SD of the runs is saved as a new set.", n=runs), "hint")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.combo = _Combo(row)
        self.capture = QComboBox()
        names = dict(STRATEGIES.choices())
        for key in CAPTURE:
            self.capture.addItem(tr(names.get(key, key)), key)
        self.capture.setCurrentIndex(0 if (row or {}).get("pump_type", "infusion") == "infusion" else 1)
        self.minutes = number_box(0.5, 600, 5.0, 1, " min")
        self.window = number_box(5, 3600, 30.0, 0, " s")
        self.runs = number_box(2, 10, float(runs), 0)
        self.temperature = QLineEdit()
        self.temperature.setPlaceholderText(tr("Water temperature °C (recommended)"))
        self.serial = QLineEdit()
        for text, widget in (("Capture method", self.capture), ("Time per run", self.minutes),
                             ("Interval length (time method)", self.window), ("Runs", self.runs),
                             ("Water temperature", self.temperature), ("Serial no.", self.serial)):
            self.combo.addRow(label(tr(text), "fieldLabel"), widget)
        layout.addLayout(self.combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Go to the Test page"))
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.capture.currentIndexChanged.connect(lambda *_: self.window.setEnabled(self.capture.currentData() != "pump_cycle"))
        self.window.setEnabled(self.capture.currentData() != "pump_cycle")

    def _accept(self):
        values = self.combo.values()
        if not values["model"]:
            QMessageBox.warning(self, tr("Repeatability study"), tr("Enter the model."))
            return
        try:
            temperature = float(self.temperature.text().replace(",", ".")) if self.temperature.text().strip() else None
        except ValueError:
            QMessageBox.warning(self, tr("Repeatability study"), tr("Water temperature must be a number."))
            return
        job = JobInfo(pump_type=PumpType(values["pump_type"]), brand=values["brand"], model=values["model"],
                      accessory=values["iv_set"], serial_no=self.serial.text().strip(), temperature_c=temperature)
        step = StepConfig(target_flow=values["rate"], duration_min=self.minutes.value(), window_s=self.window.value())
        self.plan = TestPlan(job=job, run_mode=RunMode.REPEATABILITY, strategy=self.capture.currentData(),
                             end_mode=EndMode.TIME, start_mode=StartMode.IMMEDIATE, tolerance_pct=5.0,
                             steps=[StepConfig(**vars(step)) for _ in range(int(self.runs.value()))])
        self.accept()


class RepeatabilityDialog(QDialog):
    start_requested = Signal(object)        # TestPlan ของการสอบเทียบความซ้ำ -> หน้าทดสอบ

    COLUMNS = ("Brand / model", "Type", "IV set / syringe", "Rate (ml/h)", "2SD (%)", "2SD (± ml/h)", "Sets", "Status")

    def __init__(self, parent, repository, settings):
        super().__init__(parent)
        self.setWindowTitle(tr("Measurement repeatability (2SD)"))
        self.resize(1080, 720)
        self._repository, self._settings = repository, settings
        self._rows: list[dict] = []
        layout = QVBoxLayout(self)
        intro = label(tr("2SD of repeated runs for each model, pump type, IV set and rate — used in the uncertainty budget "
                         "(u = 2SD ÷ 2). The value used is the mean of all sets. Rows marked \"Not yet\" were tested before "
                         "but have no 2SD: select one and press Measure."), "hint")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Search model, IV set, rate…"))
        self.only_missing = QComboBox()
        for key, text in (("all", "All"), ("missing", "Not yet"), ("done", "Has 2SD")):
            self.only_missing.addItem(tr(text), key)
        top.addWidget(self.search, 1)
        top.addWidget(self.only_missing)
        layout.addLayout(top)
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([tr(c) for c in self.COLUMNS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 3)
        actions = QHBoxLayout()
        self.btn_measure = QPushButton(tr("Measure ({n} runs)…", n=settings.uncertainty.repeat_runs))
        self.btn_measure.setProperty("variant", "primary")
        self.btn_enter = QPushButton(tr("Enter 2SD…"))
        self.btn_new = QPushButton(tr("New model / rate…"))
        actions.addWidget(self.btn_measure)
        actions.addWidget(self.btn_enter)
        actions.addWidget(self.btn_new)
        actions.addStretch()
        layout.addLayout(actions)
        self.detail_title = label("", "cardTitle")
        layout.addWidget(self.detail_title)
        self.sets = QTableWidget(0, 7)
        self.sets.setHorizontalHeaderLabels([tr(c) for c in ("Set", "Date", "Source", "Runs (ml/h)", "2SD (%)",
                                                              "2SD (± ml/h)", "Note")])
        self.sets.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sets.verticalHeader().setVisible(False)
        self.sets.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.sets.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.sets, 2)
        bottom = QHBoxLayout()
        self.btn_remove = QPushButton(tr("Remove selected set"))
        self.btn_remove.setProperty("variant", "danger")
        close = QPushButton(tr("Close"))
        bottom.addWidget(self.btn_remove)
        bottom.addStretch()
        bottom.addWidget(close)
        layout.addLayout(bottom)

        self.search.textChanged.connect(self._fill)
        self.only_missing.currentIndexChanged.connect(self._fill)
        self.table.itemSelectionChanged.connect(self._show_sets)
        self.btn_measure.clicked.connect(lambda: self._measure(self._selected()))
        self.btn_enter.clicked.connect(lambda: self._enter(self._selected()))
        self.btn_new.clicked.connect(lambda: self._enter(None))
        self.btn_remove.clicked.connect(self._remove)
        close.clicked.connect(self.accept)
        self.reload()

    # ---------------------------------------------------------------- ข้อมูล
    def reload(self, keep: dict | None = None) -> None:
        self._all = self._repository.repeat_overview()
        self._fill(keep=keep)

    def _visible(self) -> list[dict]:
        text = self.search.text().strip().lower()
        mode = self.only_missing.currentData()
        out = []
        for row in self._all:
            if mode != "all" and row["status"] != mode:
                continue
            hay = " ".join(str(row.get(k, "")) for k in ("brand", "model", "iv_set", "pump_type")) + f" {row['rate']:g}"
            if text and text not in hay.lower():
                continue
            out.append(row)
        return out

    def _fill(self, *_args, keep: dict | None = None) -> None:
        self._rows = self._visible()
        self.table.setRowCount(len(self._rows))
        for i, row in enumerate(self._rows):
            done = row["status"] == "done"
            cells = [" ".join(p for p in (row["brand"], row["model"]) if p), tr(dict(PUMPS)[row["pump_type"]]) if
                     row["pump_type"] in dict(PUMPS) else row["pump_type"], row["iv_set"] or "—", f"{row['rate']:g}",
                     f"{row['sd2_pct']:.4f}" if done else "—", f"{row['sd2_ml_h']:.4f}" if done else "—",
                     str(row["studies"]), tr("Has 2SD") if done else tr("Not yet")]
            for c, text in enumerate(cells):
                item = _item(text, align_right=c in (3, 4, 5, 6))
                if c == 7:
                    item.setForeground(QColor(Color.SUCCESS if done else Color.WARNING))
                self.table.setItem(i, c, item)
        index = 0
        if keep:
            index = next((i for i, r in enumerate(self._rows) if self._same(r, keep)), 0)
        if self._rows:
            self.table.selectRow(index)
        self._show_sets()

    @staticmethod
    def _same(a: dict, b: dict) -> bool:
        norm = lambda r: (r["brand"].lower(), r["model"].lower(), r["pump_type"], r["iv_set"].lower())   # noqa: E731
        return norm(a) == norm(b) and abs(a["rate"] - b["rate"]) <= max(a["rate"], b["rate"]) * 0.02

    def _selected(self) -> dict | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        return self._rows[rows[0].row()] if rows and rows[0].row() < len(self._rows) else None

    def _show_sets(self) -> None:
        row = self._selected()
        self._studies = []
        if row is not None:
            self._studies = self._repository.repeat_studies(row["brand"], row["model"], row["pump_type"], row["iv_set"],
                                                            row["rate"])
        if row is None:
            self.detail_title.setText("")
        elif self._studies:
            self.detail_title.setText(tr("{name} · {iv} · {rate:g} ml/h — value used = mean of {n} set(s): "
                                         "2SD {pct:.4f} % (± {mlh:.4f} ml/h)",
                                         name=" ".join(p for p in (row["brand"], row["model"]) if p), iv=row["iv_set"] or "—",
                                         rate=row["rate"], n=len(self._studies), pct=row["sd2_pct"], mlh=row["sd2_ml_h"]))
        else:
            self.detail_title.setText(tr("{name} · {iv} · {rate:g} ml/h — no 2SD yet (the uncertainty budget uses the "
                                         "default in Settings)", name=" ".join(p for p in (row["brand"], row["model"]) if p),
                                         iv=row["iv_set"] or "—", rate=row["rate"]))
        self.sets.setRowCount(len(self._studies))
        for i, s in enumerate(self._studies):
            if s.kind == "measured":
                source = tr("Measured {n} runs · {method}", n=len(s.runs), method=tr(dict(STRATEGIES.choices()).get(s.strategy, s.strategy)))
                runs = "  ·  ".join(f"#{r.get('ref', '')} {float(r.get('mean_flow') or 0):.4f}" for r in s.runs)
            else:
                source = tr("Entered ({value:g} {unit})", value=s.input_value, unit=s.input_unit)
                runs = "—"
            cells = [f"#{s.id}", s.created_at.replace("T", " "), source, runs, f"{s.sd2_pct:.4f}", f"{s.sd2_ml_h:.4f}", s.note]
            for c, text in enumerate(cells):
                self.sets.setItem(i, c, _item(text, align_right=c in (4, 5)))
        self.btn_measure.setEnabled(True)
        self.btn_enter.setEnabled(row is not None)
        self.btn_remove.setEnabled(bool(self._studies))

    # ---------------------------------------------------------------- การกระทำ
    def _enter(self, row: dict | None) -> None:
        dialog = EntryDialog(self, row)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        v = dialog.result_values
        self._repository.add_repeat_study(v["brand"], v["model"], v["pump_type"], v["iv_set"], v["rate"], dialog.study)
        self.reload(keep=v)

    def _measure(self, row: dict | None) -> None:
        dialog = StudyDialog(self, row, self._settings.uncertainty.repeat_runs)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.start_requested.emit(dialog.plan)
        self.accept()

    def _remove(self) -> None:
        rows = self.sets.selectionModel().selectedRows() if self.sets.selectionModel() else []
        if not rows:
            QMessageBox.information(self, tr("Remove selected set"), tr("Select a set in the lower table first."))
            return
        study = self._studies[rows[0].row()]
        answer = QMessageBox.question(
            self, tr("Remove selected set"),
            tr("Remove set #{id} (2SD {pct:.4f} %) from the mean? It stays in the database for audit.",
               id=study.id, pct=study.sd2_pct))
        if answer != QMessageBox.StandardButton.Yes:
            return
        keep = self._selected()
        self._repository.delete_repeat_study(study.id)
        self.reload(keep=keep)
