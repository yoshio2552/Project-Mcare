"""ProfileDeviationDialog: รอบปั๊มครั้งนี้ต่างจากข้อมูลเดิมของรุ่น (ยี่ห้อ + รุ่น + ชนิด + ชุดสาย) เกินเกณฑ์

ถามหลังกด "เก็บผล" — ผลการทดสอบถูกบันทึกแล้วเสมอ คำถามนี้เกี่ยวกับ "การเรียนรู้รอบปั๊ม" อย่างเดียว
    เก็บรวมกับข้อมูลเดิม  -> นำค่านี้ไปเฉลี่ยรวม (add)
    ไม่เก็บ               -> บันทึกไว้สอบย้อนหลัง แต่ไม่ใช้เรียนรู้ (skip — ค่าเริ่มต้น, Esc)
    Calibration ใหม่      -> แสดงเมื่อต่างติดกันตั้งแต่ 2 ครั้ง: ล้างข้อมูลเดิมแล้วเริ่มจากค่านี้ (recalibrate)
"""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from config.i18n import tr
from core.profiles import MAX_DEVIATION
from ui.theme import Color
from ui.widgets.common import Card, label


class ProfileDeviationDialog(QDialog):
    def __init__(self, parent: QWidget | None, device: str, check):
        super().__init__(parent)
        self.setWindowTitle(tr("Pump cycle differs from earlier data"))
        self.setModal(True)
        self.setFixedWidth(560)
        self.choice = "skip"

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        root.addWidget(label(tr("Pump cycle differs from earlier data"), "pageTitle"))
        intro = label(tr("{device} at {rate:g} ml/h. The test result is saved either way — this only decides whether "
                         "the program learns from it.", device=device or tr("This pump"), rate=check.rate),
                      "pageSubtitle")
        intro.setWordWrap(True)
        root.addWidget(intro)

        card = Card()
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(6)
        earlier = tr("Earlier at this rate") if check.kind == "rate" else tr("Earlier ({n} runs, volume per cycle)",
                                                                              n=check.runs)
        rows = [
            (tr("This test"), f"{check.period_s:.2f} s", f"{check.observed_ml:.3f} ml"),
            (earlier, f"{check.expected_period_s:.2f} s", f"{check.expected_ml:.3f} ml"),
        ]
        grid.addWidget(label("", "metricName"), 0, 0)
        grid.addWidget(label(tr("Per cycle"), "metricName"), 0, 1)
        grid.addWidget(label(tr("Volume per cycle"), "metricName"), 0, 2)
        for index, (name, period, volume) in enumerate(rows, start=1):
            grid.addWidget(label(name, "metricName"), index, 0)
            grid.addWidget(label(period, "metricValue"), index, 1)
            grid.addWidget(label(volume, "metricValue"), index, 2)
        card.body.addLayout(grid)
        difference = label(tr("Difference {d:+.1f} % (limit ±{limit:g} %)", d=check.deviation_pct,
                              limit=MAX_DEVIATION * 100), "metricValue")
        difference.setStyleSheet(f"color: {Color.WARNING};")
        card.body.addWidget(difference)
        root.addWidget(card)

        causes = label(tr("Possible causes: cycles caught wrongly (check the live-flow graph), a different IV set lot "
                          "or a set not seated properly, or the pump was repaired or adjusted."), "hint")
        causes.setWordWrap(True)
        root.addWidget(causes)
        repeated = check.streak >= 1
        if repeated:
            warning = label(tr("This is the {n}th time in a row that it differs — the pump has probably really "
                               "changed. Calibrating again is recommended.", n=check.streak + 1), "hint")
            warning.setStyleSheet(f"color: {Color.WARNING};")
            warning.setWordWrap(True)
            root.addWidget(warning)

        buttons = QHBoxLayout()
        self.btn_skip = QPushButton(tr("Do not learn from it"))
        self.btn_add = QPushButton(tr("Add to earlier data"))
        self.btn_recalibrate = QPushButton(tr("Calibrate again (replace earlier data)"))
        self.btn_recalibrate.setVisible(repeated)
        (self.btn_recalibrate if repeated else self.btn_skip).setProperty("variant", "primary")
        buttons.addWidget(self.btn_skip)
        buttons.addStretch()
        buttons.addWidget(self.btn_add)
        buttons.addWidget(self.btn_recalibrate)
        root.addLayout(buttons)
        self.btn_skip.clicked.connect(lambda: self._finish("skip"))
        self.btn_add.clicked.connect(lambda: self._finish("add"))
        self.btn_recalibrate.clicked.connect(lambda: self._finish("recalibrate"))
        self.btn_skip.setDefault(True)

    def _finish(self, choice: str) -> None:
        self.choice = choice
        self.accept()

    def reject(self) -> None:           # Esc / กากบาท = ไม่เก็บ (ปลอดภัยที่สุด)
        self.choice = "skip"
        super().reject()
