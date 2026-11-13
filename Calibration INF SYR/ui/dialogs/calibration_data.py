"""CalibrationDataDialog: ตั้งค่า -> ข้อมูลสอบเทียบรอบปั๊ม — ดู/แก้ regression และ n̄ ราย rate ของแต่ละ
ยี่ห้อ + รุ่น + ชนิด + ชุดสาย (Set IV)

ซ้าย: ทุกรุ่นที่มีข้อมูลรอบปั๊ม (โปรไฟล์) หรือหน้าต่างที่บันทึกไว้
ขวา: ทุก rate ที่มีค่า — คาบ · regression · n̄ · จุดต่อรอบ · ที่มา (✓ สอบเทียบแล้ว / แก้เอง / ค่าเริ่มต้นที่บันทึกไว้)
    แก้ตัวเลขแล้ว "บันทึก" = เก็บเป็นค่าที่แก้เอง (manual) ทับค่าเดิม (ค่าเดิมเก็บไว้ใน result_json)
    ค่าที่แก้เองยังถือว่า "ยังไม่ได้สอบเทียบ" (ตอนสร้างการทดสอบยังเตือน) และการปรับอัตโนมัติหลังเก็บผลไม่ทับ —
    ทับได้เฉพาะเมื่อสั่ง Calibration / วัดคาบก่อนทุก rate
    เพิ่ม rate ใหม่ / ลบ rate ได้ (ลบ = กลับไปใช้ค่าเริ่มต้นของ rate นั้น)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from config.i18n import tr
from config.settings import EngineSettings
from core.models import JobInfo, PumpType
from services.window_plan import rate_window
from ui.widgets.common import label, number_box
from ui.widgets.window_table import WindowTable


def model_title(model: dict) -> str:
    pump = tr("Syringe") if model["pump_type"] == "syringe" else tr("Infusion")
    device = " ".join(p for p in (model["brand"], model["model"]) if p) or tr("(no name)")
    iv_set = model["iv_set"] or tr("no IV set")
    return f"{pump} · {device} · {iv_set}"


class CalibrationDataDialog(QDialog):
    def __init__(self, parent: QWidget | None, repository, engine: EngineSettings, sample_period_s: float | None):
        super().__init__(parent)
        self.setWindowTitle(tr("Pump-cycle calibration data"))
        self.setModal(True)
        self.resize(1100, 560)
        self._repository, self._engine, self._dt = repository, engine, sample_period_s
        self._models: list[dict] = []
        self._extra_rates: list[float] = []
        self._dirty = False

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)
        root.addWidget(label(tr("Pump-cycle calibration data"), "pageTitle"))
        intro = label(tr("Regression and n̄ windows of every rate, per brand + model + pump type + IV set. Values are "
                         "stored as a fraction of the pump cycle, so the number of points follows the real cycle and "
                         "balance speed. Edited values are kept as \"set by hand\": they are not replaced by automatic "
                         "tuning, and tests still ask for calibration until the model is calibrated."), "pageSubtitle")
        intro.setWordWrap(True)
        root.addWidget(intro)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._list = QListWidget()
        self._list.setMinimumWidth(380)
        splitter.addWidget(self._list)
        right = QWidget()
        box = QVBoxLayout(right)
        box.setContentsMargins(8, 0, 0, 0)
        self._info = label("", "hint")
        self._info.setWordWrap(True)
        box.addWidget(self._info)
        self.table = WindowTable(editable=True)
        self.table.changed.connect(lambda: self._set_dirty(True))
        box.addWidget(self.table, 1)
        tools = QHBoxLayout()
        tools.addWidget(label(tr("Add rate"), "fieldLabel"))
        self._new_rate = number_box(0.1, 2000, 100, 1, " ml/h")
        add = QPushButton(tr("Add"))
        self._delete = QPushButton(tr("Delete rate"))
        self._delete.setProperty("variant", "danger")
        tools.addWidget(self._new_rate)
        tools.addWidget(add)
        tools.addStretch()
        tools.addWidget(self._delete)
        box.addLayout(tools)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        if not sample_period_s:
            root.addWidget(label(tr("The balance speed is not known yet — windows are shown as a fraction of the pump "
                                    "cycle. Connect the balance to see and edit points."), "hint"))
        buttons = QHBoxLayout()
        self.status = label("", "hint")
        close = QPushButton(tr("Close"))
        self.btn_save = QPushButton(tr("Save changes"))
        self.btn_save.setProperty("variant", "primary")
        buttons.addWidget(self.status, 1)
        buttons.addWidget(close)
        buttons.addWidget(self.btn_save)
        root.addLayout(buttons)

        self._list.currentRowChanged.connect(self._show_model)
        add.clicked.connect(self._add_rate)
        self._delete.clicked.connect(self._delete_rate)
        self.btn_save.clicked.connect(self._save)
        close.clicked.connect(self.reject)
        self.reload()

    # ------------------------------------------------------------------ data
    def reload(self) -> None:
        current = self._list.currentRow()
        self._models = self._repository.calibration_models()
        self._list.clear()
        for model in self._models:
            mark = f"  ✓ {model['tuned']}/{model['rates']}" if model["rates"] else ""
            item = QListWidgetItem(model_title(model) + mark)
            self._list.addItem(item)
        if self._models:
            self._list.setCurrentRow(max(0, min(current, len(self._models) - 1)))
        else:
            self._info.setText(tr("No pump-cycle data yet. It is created by pump-cycle tests, or saved from the "
                                  "calibration prompt when a test is created."))
            self.table.set_rows([], self._dt)
        self._set_dirty(False)

    def _job(self, model: dict) -> JobInfo:
        return JobInfo(brand=model["brand"], model=model["model"], accessory=model["iv_set"],
                       pump_type=PumpType(model["pump_type"] if model["pump_type"] in ("infusion", "syringe") else "infusion"))

    def _model(self) -> dict | None:
        row = self._list.currentRow()
        return self._models[row] if 0 <= row < len(self._models) else None

    def _show_model(self, _row: int = -1) -> None:
        model = self._model()
        if model is None:
            return
        self._extra_rates = []
        lines = []
        if model["runs"]:
            lines.append(tr("Volume per cycle {ml:.3f} ml from {n} runs", ml=model["stroke_volume_ml"], n=model["runs"]))
        elif model["stroke_volume_ml"]:
            lines.append(tr("Model default: {ml:.3f} ml per cycle (not measured yet)", ml=model["stroke_volume_ml"]))
        if model["calibrated_at"]:
            lines.append(tr("Last calibration {date}", date=model["calibrated_at"][:19].replace("T", " ")))
        self._info.setText("  ·  ".join(lines))
        self._fill()

    def _fill(self) -> None:
        model = self._model()
        job = self._job(model)
        rows = self._repository.tuned_windows(job.brand, job.model, job.accessory, job.pump_type.value)
        rates = sorted({round(r["rate_ml_h"], 3) for r in rows} | set(self._extra_rates))
        items = [rate_window(self._repository, self._engine, job, rate, self._dt) for rate in rates]
        self.table.set_rows(items, self._dt)
        self._set_dirty(bool(self._extra_rates))

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self.btn_save.setEnabled(dirty)
        self.status.setText(tr("Not saved yet") if dirty else "")

    # --------------------------------------------------------------- actions
    def _add_rate(self) -> None:
        if self._model() is None:
            return
        if self.table.edited_rates():
            QMessageBox.information(self, tr("Add rate"), tr("Save or discard the changes first."))
            return
        rate = round(self._new_rate.value(), 3)
        if rate not in [i.rate for i in self.table.items()]:
            self._extra_rates.append(rate)
            self._fill()

    def _delete_rate(self) -> None:
        model, rate = self._model(), self.table.selected_rate()
        if model is None or rate is None:
            return
        answer = QMessageBox.question(self, tr("Delete rate"),
                                      tr("Delete the windows of {rate:g} ml/h for {device}? That rate goes back to "
                                         "the default values.", rate=rate, device=model_title(model)))
        if answer != QMessageBox.StandardButton.Yes:
            return
        job = self._job(model)
        self._repository.delete_window(job.brand, job.model, job.accessory, job.pump_type.value, rate)
        if rate in self._extra_rates:
            self._extra_rates.remove(rate)
        self.reload()

    def _save(self) -> None:
        model = self._model()
        if model is None:
            return
        job = self._job(model)
        changed = set(self.table.edited_rates()) | set(self._extra_rates)
        items = {i.rate: i for i in self.table.items()}
        blocked = [rate for rate in changed if items[rate].blocking]
        if blocked:
            QMessageBox.warning(self, tr("Pump-cycle calibration data"),
                                tr("Values at {rates} ml/h are outside the usable range and were not saved.",
                                   rates=", ".join(f"{r:g}" for r in sorted(blocked))))
        saved = 0
        for rate in sorted(changed - set(blocked)):
            item = items[rate]
            if self._repository.save_window(job.brand, job.model, job.accessory, job.pump_type.value, rate,
                                            item.regression_fraction, item.half_fraction, "manual",
                                            item.period_s, self._dt):
                saved += 1
        self._extra_rates = []
        self.reload()
        self.status.setText(tr("Saved {n} rates", n=saved))
