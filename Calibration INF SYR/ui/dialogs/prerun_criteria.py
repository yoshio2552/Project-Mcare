"""PrerunCriteriaDialog: ตั้งเกณฑ์ "flow นิ่ง" ของโหมดเริ่มวัดอัตโนมัติ เฉพาะ ยี่ห้อ + รุ่น + ชนิดเครื่อง + ชุดสาย/syringe

ค่าเริ่มต้นของแต่ละกลุ่ม (Infusion จับรอบปั๊ม / Infusion จับตามเวลา / Syringe จับตามเวลา) อยู่ในหน้าตั้งค่า
หน้าต่างนี้ใช้เมื่อรุ่นใดต้องการค่าต่างไป เช่น syringe รุ่นที่กระบอกใช้เวลานานกว่าจะส่ง flow คงที่
ผลลัพธ์: .action = "save" (ค่าใน .values) | "reset" (ลบค่าเฉพาะรุ่น กลับไปใช้ค่าเริ่มต้น) | None
"""
from __future__ import annotations

import dataclasses

from PySide6.QtWidgets import QComboBox, QDialog, QFormLayout, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from config.i18n import tr
from config.settings import PrerunCriteria
from ui.widgets.common import Card, int_box, label, number_box

BLOCK_MODES = [("cycle", "Pump cycles (needs the pump cycle)"), ("time", "Seconds")]


class PrerunCriteriaDialog(QDialog):
    def __init__(self, parent: QWidget | None, device: str, group_name: str, criteria: PrerunCriteria,
                 specific: bool):
        super().__init__(parent)
        self.setWindowTitle(tr("Stable-flow criteria"))
        self.setModal(True)
        self.setMinimumWidth(520)
        self.action: str | None = None
        self.values: dict = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)
        root.addWidget(label(tr("Stable-flow criteria for this model"), "pageTitle"))
        info = label(tr("{device} · {group}", device=device, group=group_name) + "\n"
                     + (tr("Currently: values set for this model") if specific
                        else tr("Currently: defaults from Settings")), "pageSubtitle")
        info.setWordWrap(True)
        root.addWidget(info)

        card = Card()
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)
        self._mode = QComboBox()
        for key, text in BLOCK_MODES:
            self._mode.addItem(tr(text), key)
        self._mode.setCurrentIndex(max(0, self._mode.findData(criteria.block_mode)))
        self._pct = number_box(0.1, 50, criteria.stability_pct, 1, " %")
        self._cycles = int_box(1, 20, criteria.block_cycles)
        self._block_s = number_box(2, 3600, criteria.block_s, 0, " s")
        self._min_mg = number_box(0, 5000, criteria.min_block_mg, 0, " mg")
        self._align = QComboBox()
        for value, text in ((True, "On"), (False, "Off")):
            self._align.addItem(tr(text), value)
        self._align.setCurrentIndex(0 if criteria.align_to_cycle else 1)
        self._blocks = int_box(2, 20, criteria.blocks)
        self._wait = number_box(0, 240, criteria.max_wait_min, 0, " min")
        rows = [
            ("Allowed flow variation", self._pct),
            ("Block length unit", self._mode),
            ("Cycles per block", self._cycles),
            ("Block length", self._block_s),
            ("Lengthen each block to at least", self._min_mg),
            ("Round up to whole pump cycles", self._align),
            ("Blocks compared", self._blocks),
            ("Start anyway after", self._wait),
        ]
        for text, widget in rows:
            form.addRow(label(tr(text), "fieldLabel"), widget)
        card.body.addLayout(form)
        hint = label(tr("“Start anyway” begins measuring after this time even if the flow is not stable yet, and the "
                        "result records that stability was not confirmed. 0 = wait until stable."), "hint")
        hint.setWordWrap(True)
        card.body.addWidget(hint)
        root.addWidget(card)

        buttons = QHBoxLayout()
        reset = QPushButton(tr("Use defaults"))
        reset.setEnabled(specific)
        cancel = QPushButton(tr("Cancel"))
        save = QPushButton(tr("Save for this model"))
        save.setProperty("variant", "primary")
        buttons.addWidget(reset)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)
        reset.clicked.connect(lambda: self._finish("reset"))
        cancel.clicked.connect(self.reject)
        save.clicked.connect(lambda: self._finish("save"))
        self._mode.currentIndexChanged.connect(self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        cycle = self._mode.currentData() == "cycle"
        self._cycles.setEnabled(cycle)
        self._align.setEnabled(not cycle)

    def criteria(self) -> PrerunCriteria:
        return PrerunCriteria(
            stability_pct=self._pct.value(), block_mode=self._mode.currentData(), block_cycles=self._cycles.value(),
            block_s=self._block_s.value(), min_block_mg=self._min_mg.value(), align_to_cycle=bool(self._align.currentData()),
            blocks=self._blocks.value(), max_wait_min=self._wait.value())

    def _finish(self, action: str) -> None:
        self.action = action
        self.values = dataclasses.asdict(self.criteria()) if action == "save" else {}
        self.accept()
