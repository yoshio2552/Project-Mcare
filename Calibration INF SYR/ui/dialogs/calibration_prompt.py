"""CalibrationPromptDialog: ก่อนสร้างการทดสอบแบบจับรอบปั๊ม (Calibration / Inspection / Quick Test)

ขึ้นเมื่อ ยี่ห้อ + รุ่น + ชนิด + ชุดสาย นี้ยังไม่ได้สอบเทียบรอบปั๊ม (regression / n̄) ที่ rate ใดใน แผน
หรือมี rate ที่จุดต่อรอบน้อย / ค่านอกช่วงที่ใช้ได้ — ไม่ขึ้นเลยเมื่อวิธีวัดไม่ได้ใช้รอบปั๊ม (จับตามเวลา, syringe ค่าเริ่มต้น)

หน้า 1 (เตือน)  สอบเทียบเลย (แนะนำ — rate สูงก่อน)  |  ข้าม  |  เปลี่ยนเป็นจับตามเวลา (ถ้าจุดต่อรอบน้อย)
หน้า 2 (ข้าม)   ตาราง regression / n̄ ราย rate ที่จะใช้ (ค่าเริ่มต้น หรือค่าที่บันทึกไว้ก่อน) แก้ได้
                ใช้ครั้งนี้  |  บันทึกให้รุ่นนี้แล้วใช้ — บันทึกเป็น "ยังไม่ได้สอบเทียบ" ครั้งหน้ายังเตือนอยู่
                แต่ถ้าข้ามอีกจะใช้ค่าที่บันทึกไว้นี้
ผลลัพธ์: action = "calibrate" | "use" | "time" · values {rate: (r, h)} · save · reorder · stroke_ml
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from config.i18n import tr
from core.windows import time_window_for
from ui.theme import Color
from ui.widgets.common import label, number_box
from ui.widgets.window_table import WindowTable


class CalibrationPromptDialog(QDialog):
    def __init__(self, parent: QWidget | None, device: str, items: list, sample_period_s: float | None,
                 sample_source: str, can_remember: bool, can_calibrate: bool, stroke_ml: float | None = None,
                 recompute=None):
        """recompute(stroke_ml) -> items ใหม่ (รุ่นที่ยังไม่รู้ปริมาตรต่อรอบ: แก้ปริมาตรแล้วคาบ/จุดเปลี่ยนตาม)"""
        super().__init__(parent)
        self.setWindowTitle(tr("Pump-cycle calibration"))
        self.setModal(True)
        self.setMinimumWidth(820)
        self.action: str | None = None
        self.values: dict[float, tuple[float, float]] = {}
        self.save = False
        self.stroke_ml = stroke_ml
        self.time_windows: dict[float, float] = {}
        self._items, self._dt, self._recompute = items, sample_period_s, recompute
        uncalibrated = [i for i in items if not i.calibrated]
        coarse = [i for i in items if i.level in ("low", "too_low")]

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        self._pages = QStackedWidget()
        root.addWidget(self._pages)

        # ------------------------------------------------------------ หน้า 1
        warn = QWidget()
        box = QVBoxLayout(warn)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(10)
        title = tr("{device} is not calibrated for pump-cycle capture", device=device or tr("This pump")) if uncalibrated \
            else tr("Check before starting")
        box.addWidget(label(title, "pageTitle"))
        lines = []
        if uncalibrated:
            lines.append(tr("Not calibrated at {rates} ml/h. Each rate needs its own regression and n̄ window — "
                            "calibrating measures the pump cycle and tunes them from the result.",
                            rates=", ".join(f"{i.rate:g}" for i in uncalibrated)))
        if coarse:
            lines.append(tr("At {rates} ml/h the balance gives few points per pump cycle, so peak detection is coarse. "
                            "Time-based capture over whole cycles is more precise there; a faster balance output "
                            "(9600 baud or stream mode, set on the balance) also helps.",
                            rates=", ".join(f"{i.rate:g}" for i in coarse)))
        if not sample_period_s:
            lines.append(tr("The balance has not been read yet, so the number of points is not known."))
        elif sample_source != "measured":
            lines.append(tr("Points are estimated with {dt:.2f} s per balance reading ({src}).",
                            dt=sample_period_s, src=tr(sample_source)))
        intro = label("\n\n".join(lines), "pageSubtitle")
        intro.setWordWrap(True)
        box.addWidget(intro)
        overview = WindowTable(editable=False)
        overview.set_rows(items, sample_period_s)
        self._overview = overview
        box.addWidget(overview)
        self.reorder = QCheckBox(tr("Calibrate from the highest rate to the lowest (recommended: the high rate learns "
                                    "the cycle within seconds)"))
        rates = [i.rate for i in items]
        self.reorder.setChecked(len(rates) > 1 and rates != sorted(rates, reverse=True))
        self.reorder.setEnabled(len(rates) > 1 and rates != sorted(rates, reverse=True))
        self.reorder.setVisible(bool(uncalibrated))
        box.addWidget(self.reorder)
        buttons = QHBoxLayout()
        back = QPushButton(tr("Back to settings"))
        buttons.addWidget(back)
        buttons.addStretch()
        self.btn_time = QPushButton(tr("Switch to time-based capture"))
        self.btn_time.setToolTip(tr("Intervals of whole pump cycles (at least 30 s) instead of peak detection"))
        self.btn_time.setVisible(bool(coarse))
        buttons.addWidget(self.btn_time)
        self.btn_skip = QPushButton(tr("Skip calibration…") if uncalibrated else tr("Review windows…"))
        buttons.addWidget(self.btn_skip)
        self.btn_calibrate = QPushButton(tr("Calibrate now (recommended)") if uncalibrated else tr("Continue"))
        self.btn_calibrate.setProperty("variant", "primary")
        self.btn_calibrate.setEnabled(not any(i.blocking for i in items) or bool(uncalibrated))
        buttons.addWidget(self.btn_calibrate)
        box.addLayout(buttons)
        self._pages.addWidget(warn)
        self._uncalibrated = bool(uncalibrated)

        # ------------------------------------------------------------ หน้า 2
        edit = QWidget()
        box = QVBoxLayout(edit)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(10)
        box.addWidget(label(tr("Windows used without calibration"), "pageTitle"))
        hint = label(tr("These are the defaults for each rate (or what you saved for this model before). Change them if "
                        "you know better values. Saved values are marked \"not calibrated\": you will still be asked "
                        "to calibrate next time, and skipping again uses them."), "pageSubtitle")
        hint.setWordWrap(True)
        box.addWidget(hint)
        if recompute is not None:
            row = QHBoxLayout()
            row.addWidget(label(tr("Volume per cycle (this model has not been measured)"), "fieldLabel"))
            self._stroke = number_box(0.01, 5.0, stroke_ml or 0.16, 3, " ml")
            self._stroke.valueChanged.connect(self._on_stroke)
            row.addWidget(self._stroke)
            row.addStretch()
            box.addLayout(row)
        self.table = WindowTable(editable=True)
        self.table.set_rows(items, sample_period_s)

        self.table.changed.connect(self._refresh_buttons)
        box.addWidget(self.table)
        self._block_note = label("", "hint")
        self._block_note.setStyleSheet(f"color: {Color.DANGER};")
        self._block_note.setWordWrap(True)
        box.addWidget(self._block_note)
        buttons = QHBoxLayout()
        back2 = QPushButton(tr("Back"))
        buttons.addWidget(back2)
        buttons.addStretch()
        self.btn_use = QPushButton(tr("Use for this test only"))
        self.btn_save = QPushButton(tr("Save for this model and use"))
        self.btn_save.setProperty("variant", "primary")
        self.btn_save.setEnabled(can_remember)
        if not can_remember:
            self.btn_save.setToolTip(tr("Enter brand and model in step 1 to keep values for this model."))
        buttons.addWidget(self.btn_use)
        buttons.addWidget(self.btn_save)
        box.addLayout(buttons)
        self._pages.addWidget(edit)
        self._can_remember = can_remember

        back.clicked.connect(self.reject)
        back2.clicked.connect(lambda: self._pages.setCurrentIndex(0))
        self.btn_skip.clicked.connect(lambda: self._pages.setCurrentIndex(1))
        self.btn_calibrate.clicked.connect(self._calibrate)
        self.btn_time.clicked.connect(self._time_based)
        self.btn_use.clicked.connect(lambda: self._use(save=False))
        self.btn_save.clicked.connect(lambda: self._use(save=True))
        self._refresh_buttons()

    def showEvent(self, event) -> None:
        # ความสูงตารางคิดได้เมื่อรู้ความกว้างจริง (ข้อความสถานะตัดบรรทัด)
        super().showEvent(event)
        self._overview.fit_height()
        self.table.fit_height()

    # ----------------------------------------------------------------- actions
    def _on_stroke(self, value: float) -> None:
        self.stroke_ml = value
        self._items = self._recompute(value)
        self.table.set_rows(self._items, self._dt)
        self.table.fit_height()
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        blocking = [i for i in self.table.items() if i.blocking]
        self.btn_use.setEnabled(not blocking)
        self.btn_save.setEnabled(not blocking and self._can_remember)
        self._block_note.setText(tr("Cannot use peak detection at {rates} ml/h with these values — fix them or switch "
                                    "to time-based capture.", rates=", ".join(f"{i.rate:g}" for i in blocking))
                                 if blocking else "")

    def _calibrate(self) -> None:
        self.action = "calibrate" if self._uncalibrated else "use"
        self.values = {i.rate: (i.regression_fraction, i.half_fraction) for i in self._items}
        self.accept()

    def _use(self, save: bool) -> None:
        self.action, self.save = "use", save
        self.values = self.table.values()
        self.accept()

    def _time_based(self) -> None:
        self.action = "time"
        self.time_windows = {i.rate: time_window_for(i.period_s) for i in self._items if i.period_s}
        self.accept()
