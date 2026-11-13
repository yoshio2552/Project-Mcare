"""RecalibrateDialog: ปุ่ม "Calibration รอบปั๊ม" — เรียนรู้รอบปั๊มของรุ่นนี้ใหม่ แทนที่ข้อมูลเดิม

แสดงสิ่งที่โปรแกรมจำไว้ของ ยี่ห้อ + รุ่น + ชนิด + ชุดสาย (ปริมาตรต่อรอบ, หน้าต่างราย rate) แล้วยืนยัน
แผนที่ตั้งเป็น Calibration ใหม่:
    rate แรก: วัดคาบก่อนเริ่ม (ไม่ใช้ข้อมูลเดิม) — กดเก็บผลแล้ว ข้อมูลรอบปั๊ม/หน้าต่างเดิมของรุ่นนี้เลิกใช้
    rate ถัดไป: ใช้ค่าที่เพิ่งเรียนรู้ · หน้าต่างแต่ละ rate ปรับใหม่จากข้อมูลหลัง Calibration เท่านั้น
    ข้อมูลเก่าไม่ถูกลบ (สอบย้อนหลังได้)
แนะนำเรียง rate จากสูงไปต่ำ: rate สูงวัดคาบได้ในไม่กี่วินาที
"""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDialog, QGridLayout, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from config.i18n import tr
from ui.widgets.common import Card, label


class RecalibrateDialog(QDialog):
    def __init__(self, parent: QWidget | None, device: str, profile, tuned: list[dict], rates: list[float]):
        super().__init__(parent)
        self.setWindowTitle(tr("Pump cycle calibration"))
        self.setModal(True)
        self.setFixedWidth(580)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        root.addWidget(label(tr("Calibrate the pump cycle again"), "pageTitle"))
        intro = label(tr("{device}: the first rate measures the pump cycle before it starts. When that result is "
                         "kept, the earlier pump-cycle data and window sizes of this model are no longer used "
                         "(they stay stored for audit). Each rate then gets its own window sizes again.",
                         device=device), "pageSubtitle")
        intro.setWordWrap(True)
        root.addWidget(intro)

        card = Card(tr("What is stored now"))
        lines = []
        if profile is not None and profile.runs:
            lines.append(tr("Volume per cycle {ml:.3f} ml from {n} runs", ml=profile.stroke_volume_ml, n=profile.runs))
        if profile is not None and profile.calibrated_at:
            lines.append(tr("Last calibration {date}", date=profile.calibrated_at.replace("T", " ")))
        card.body.addWidget(label("\n".join(lines) or tr("Nothing yet"), "metricValue"))
        if tuned:
            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(3)
            from services.window_plan import FIT_TEXT
            for column, text in enumerate((tr("Rate"), tr("Regression window"), tr("n̄ (peak left/right)"), tr("Status"))):
                grid.addWidget(label(text, "metricName"), 0, column)
            for row, item in enumerate(tuned, start=1):
                grid.addWidget(label(f"{item['rate_ml_h']:g} ml/h", "metricValue"), row, 0)
                grid.addWidget(label(tr("{n} pts ({f:.2f} × cycle)", n=item["regression_points"] or "—",
                                        f=item["regression_fraction"]), "metricValue"), row, 1)
                grid.addWidget(label(tr("{n} pts ({f:.2f} × cycle)", n=item["half_points"] or "—",
                                        f=item["half_fraction"]), "metricValue"), row, 2)
                grid.addWidget(label(tr(FIT_TEXT.get(item.get("source") or "tuned", "")), "metricValue"), row, 3)
            card.body.addLayout(grid)
        root.addWidget(card)

        descending = sorted(rates, reverse=True)
        self.reorder = QCheckBox(tr("Run the rates from highest to lowest ({order} ml/h) — recommended",
                                    order=" → ".join(f"{r:g}" for r in descending)))
        self.reorder.setChecked(len(rates) > 1 and rates != descending)
        self.reorder.setEnabled(len(rates) > 1 and rates != descending)
        root.addWidget(self.reorder)

        buttons = QHBoxLayout()
        cancel = QPushButton(tr("Cancel"))
        ok = QPushButton(tr("Use calibration for this test"))
        ok.setProperty("variant", "primary")
        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(ok)
        root.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        ok.setDefault(True)
