"""ResultReviewDialog: ถามหลังจบ 1 ขั้นว่า "เก็บผลนี้ไหม"

เก็บ      → บันทึกลงฐานข้อมูล (ถ้าทดสอบครบจะเลื่อนไปขั้นถัดไป)
ไม่เก็บ   → ลบข้อมูลทิ้งจริง ขั้นเดิมยังอยู่ กดเริ่มคือทำซ้ำ
"""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from config.i18n import tr
from core.models import SessionSummary, Verdict
from ui.theme import Color
from ui.widgets.common import Card, fmt, fmt_clock, label


class ResultReviewDialog(QDialog):
    def __init__(self, parent: QWidget, summary: SessionSummary):
        super().__init__(parent)
        config = summary.config
        completed = summary.end_reason == "completed"
        self.setWindowTitle(tr("Keep this result?"))
        self.setModal(True)
        self.setMinimumWidth(460)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)
        root.addWidget(label(tr("Step {i}/{n} · {rate:g} ml/h", i=config.step_index + 1,
                                n=config.step_count, rate=config.target_flow), "pageTitle"))
        if not completed:
            note = label(tr("This test was stopped before it finished. If kept, it is saved as incomplete "
                            "and the step still has to be run again."), "pageSubtitle")
            note.setWordWrap(True)
            root.addWidget(note)

        card = Card()
        verdict = summary.verdict
        text = verdict.value if completed or verdict is Verdict.NONE else f"{verdict.value} ({tr('partial')})"
        hero = label(text, "hero")
        hero.setStyleSheet(f"color: {Color.SUCCESS if verdict is Verdict.PASS else Color.DANGER if verdict is Verdict.FAIL else Color.TEXT_MUTED};")
        card.body.addWidget(hero)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(1, 1)
        rows = [
            (tr("Flow error (net)"), fmt(summary.error_pct, 2, " %", signed=True)),
            (tr("Mean flow"), fmt(summary.mean_flow, 3, " ml/h")),
            (tr("Uncorrected (1 g = 1 ml)"), f'{fmt(summary.mean_flow_raw, 3, " ml/h")}   '
                                            f'({fmt(summary.error_raw_pct, 2, " %", signed=True)})'),
            (tr("Correction factor Z"), fmt(summary.ml_per_g or None, 5, " ml/g")),
            ("2 SD", fmt(summary.sd2_pct, 3, " %", prefix="± ")),
            (tr("Tolerance"), fmt(config.tolerance_pct, 1, " %", prefix="± ")),
            (tr("Intervals"), str(summary.interval_count)),
            (tr("Duration"), fmt_clock(summary.duration_s)),
        ]
        for index, (name, value) in enumerate(rows):
            grid.addWidget(label(name, "metricName"), index, 0)
            grid.addWidget(label(value, "metricValue"), index, 1)
        card.body.addLayout(grid)
        root.addWidget(card)

        hint = label(tr("Discard deletes this data permanently. Pressing Start afterwards repeats this step."), "hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        buttons = QHBoxLayout()
        self.btn_discard = QPushButton(tr("Discard"))
        self.btn_discard.setProperty("variant", "danger")
        self.btn_keep = QPushButton(tr("Keep result"))
        self.btn_keep.setProperty("variant", "primary")
        buttons.addWidget(self.btn_discard)
        buttons.addStretch()
        buttons.addWidget(self.btn_keep)
        root.addLayout(buttons)
        self.btn_keep.clicked.connect(self.accept)
        self.btn_discard.clicked.connect(self._discard)
        (self.btn_keep if completed else self.btn_discard).setDefault(True)

    def _discard(self) -> None:
        """ปุ่ม "ไม่เก็บ" เท่านั้นที่ปิดแบบ Rejected (= ลบข้อมูล)"""
        QDialog.reject(self)

    def reject(self) -> None:
        # ปิดหน้าต่างด้วย Esc/กากบาท = ยังไม่ได้เลือก ไม่ถือว่า "ไม่เก็บ" (กันลบข้อมูลโดยไม่ตั้งใจ)
        # (เดิมเช็ค self.sender() ซึ่งใน PySide6 ไม่ใช่ปุ่ม จึงกดปุ่มไม่เก็บไม่ได้เลย)
        pass
