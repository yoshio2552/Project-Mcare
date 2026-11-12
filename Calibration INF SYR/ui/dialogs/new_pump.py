"""NewPumpDialog: เตือนก่อนสร้างการทดสอบ เมื่อปั๊มรุ่นนี้ (ยี่ห้อ + รุ่น + ชุดสาย) ยังไม่มีข้อมูลรอบปั๊ม

ทำไมต้องเตือน: วิธีจับรอบปั๊มต้องรู้ "คาบรอบปั๊ม" ก่อนตั้งหน้าต่างจับ peak
    ปั๊มส่งปริมาตรต่อรอบเกือบคงที่ คาบจึงยาวขึ้นเมื่อ rate ต่ำ (คาบ = ปริมาตรต่อรอบ x 3600 / rate)
    การวัดคาบต้องเห็นอย่างน้อย ~3 รอบ: 200 ml/h ใช้ไม่กี่วินาที แต่ 10 ml/h ใช้หลายนาที
ตัวเลือก
    reorder  เรียง rate จากสูงไปต่ำ — rate แรกเรียนรู้ปริมาตรต่อรอบได้ไว แล้ว rate ต่ำใช้ค่าที่ทำนายได้ทันที (แนะนำ)
    profile  วัดคาบก่อนแต่ละ rate ตามลำดับเดิม (rate ต่ำรอนาน)
    default  ใช้ปริมาตรต่อรอบที่กำหนดเอง "แทนไปก่อน" สำหรับรุ่นนี้ — การวัดจริงครั้งแรกจะแทนที่ค่านี้
    manual   ใช้ขนาดหน้าต่างกำหนดเองในหน้าตั้งค่า (ไม่สนใจ rate)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QFrame, QHBoxLayout, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from config.i18n import tr
from ui.widgets.common import Card, label, number_box

MEASURE_CYCLES = 3.5        # รอบที่ต้องเห็นก่อนยืนยันคาบได้ (โดยประมาณ — ใช้บอกเวลารอ)


def _wait_text(seconds: float) -> str:
    return tr("{s:.0f} s", s=seconds) if seconds < 90 else tr("{m:.0f} min", m=seconds / 60.0)


class NewPumpDialog(QDialog):
    def __init__(self, parent: QWidget | None, device: str, rates: list[float],
                 default_ml: float, can_remember: bool):
        super().__init__(parent)
        self.setWindowTitle(tr("New pump model"))
        self.setModal(True)
        self.setFixedWidth(600)
        self.choice: str | None = None
        self.default_ml = default_ml

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        root.addWidget(label(tr("No pump-cycle data for this model yet"), "pageTitle"))
        intro = label(tr("{device} has not been measured before. Peak detection needs the pump cycle period, "
                         "and the period gets longer as the rate gets lower, so measuring it first takes "
                         "about three pump cycles:", device=device or tr("This pump")), "pageSubtitle")
        intro.setWordWrap(True)
        root.addWidget(intro)

        # เวลารอโดยประมาณของแต่ละ rate (เดาจากปริมาตรต่อรอบเริ่มต้น)
        waits = Card()
        row = QHBoxLayout()
        row.setSpacing(18)
        for rate in sorted(set(rates), reverse=True):
            period = default_ml * 3600.0 / rate if rate > 0 and default_ml > 0 else 0.0
            box = QVBoxLayout()
            box.setSpacing(0)
            box.addWidget(label(f"{rate:g} ml/h", "metricName"))
            box.addWidget(label("≈ " + _wait_text(period * MEASURE_CYCLES), "metricValue"))
            row.addLayout(box)
        row.addStretch()
        waits.body.addLayout(row)
        root.addWidget(waits)

        descending = sorted(rates, reverse=True)
        can_reorder = len(rates) > 1 and rates != descending
        high_first = len(rates) > 1 and not can_reorder
        self._group = QButtonGroup(self)
        self._options: dict[str, QRadioButton] = {}
        options = [
            ("reorder", tr("Run the highest rate first (recommended)"),
             tr("Order becomes {order} ml/h. The first rate learns the volume per cycle within seconds; "
                "the lower rates then start without waiting.", order=" → ".join(f"{r:g}" for r in descending)),
             can_reorder),
            ("profile", tr("Measure the cycle before each rate, in this order") if not high_first
             else tr("Measure the cycle at the first rate (already highest first)"),
             tr("Nothing changes in the plan; low rates wait longer before measuring starts."), True),
            ("default", tr("Use a default for this model for now"),
             tr("Peak detection starts at once using the volume per cycle below. The first real measurement "
                "of this model replaces it.") if can_remember
             else tr("Enter brand and model in step 1 to keep a default for this model."), can_remember),
            ("manual", tr("Use manual window sizes (Settings)"),
             tr("Same window size at every rate — only suitable if you know it fits."), True),
        ]
        for key, title, detail, enabled in options:
            radio = QRadioButton(title)
            radio.setEnabled(enabled)
            self._group.addButton(radio)
            self._options[key] = radio
            frame = QFrame()
            frame.setProperty("optionCard", True)
            box = QVBoxLayout(frame)
            box.setContentsMargins(12, 8, 12, 8)
            box.setSpacing(2)
            box.addWidget(radio)
            text = label(detail, "hint")
            text.setWordWrap(True)
            text.setContentsMargins(26, 0, 0, 0)
            text.setEnabled(enabled)
            box.addWidget(text)
            if key == "default":
                line = QHBoxLayout()
                line.setContentsMargins(26, 4, 0, 0)
                line.addWidget(label(tr("Volume per cycle"), "fieldLabel"))
                self._volume = number_box(0.01, 5.0, default_ml, 3, " ml")
                self._volume.setEnabled(enabled)
                line.addWidget(self._volume)
                line.addStretch()
                box.addLayout(line)
            root.addWidget(frame)
        (self._options["reorder"] if can_reorder else self._options["profile"]).setChecked(True)

        buttons = QHBoxLayout()
        cancel = QPushButton(tr("Back to settings"))
        ok = QPushButton(tr("Create test"))
        ok.setProperty("variant", "primary")
        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(ok)
        root.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self._accept)
        ok.setDefault(True)

    def showEvent(self, event) -> None:
        # ข้อความหลายบรรทัด: ความสูงต้องคิดจากความกว้างจริง ไม่งั้นข้อความถูกบีบทับกัน
        self.layout().activate()
        self.setMinimumHeight(self.layout().totalHeightForWidth(self.width()))
        super().showEvent(event)

    def _accept(self) -> None:
        self.choice = next(key for key, radio in self._options.items() if radio.isChecked())
        self.default_ml = self._volume.value()
        self.accept()
