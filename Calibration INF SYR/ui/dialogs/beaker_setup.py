"""หน้าต่างตั้งบีกเกอร์ (ผู้ใช้ 2026-11-20): ตอนเปิดโปรแกรม/เชื่อมตราชั่งได้ครั้งแรก หรือกดเองจากการ์ดตราชั่ง/popup เตือน

    ขั้น 1  ยกบีกเกอร์ออก แล้วกด RE-ZERO ที่ตราชั่ง      — รอน้ำหนัก ≈ 0 g นิ่ง 1.5 s แล้วไปขั้นถัดไปเอง
    ขั้น 2  วางบีกเกอร์ (เปล่าหรือมีน้ำแล้วก็ได้)          — ความจุ (ค่าเริ่มต้น 150 ml) + บีกเกอร์เปล่า (68 g)
            น้ำตอนนี้ = น้ำหนัก − บีกเกอร์เปล่า · ปุ่ม "บีกเกอร์เปล่าอยู่" = ใช้น้ำหนักที่อ่านได้เป็นน้ำหนักบีกเกอร์
    ตกลง -> BeakerGuard.set_beaker(...) · ติ๊ก "จำเป็นค่าเริ่มต้น" = บันทึกลง settings.safety

น้ำหนักสดมาจาก SessionController.live_reading (ตราชั่งตอนว่าง) — ไม่ต้องเปิดพอร์ตเอง
"""
from __future__ import annotations

import time

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from config.i18n import tr
from core.beaker import EMPTY_PAN_G, Beaker
from ui.theme import Color
from ui.widgets.beaker_meter import BeakerMeter
from ui.widgets.common import label

ZERO_HOLD_S = 1.5
PLACE_MIN_G = 5.0


def _step_chip(number: int, text: str) -> QLabel:
    chip = QLabel(f"{number}   {text}")
    chip.setProperty("stepChip", True)
    return chip


class BeakerSetupDialog(QDialog):
    def __init__(self, parent: QWidget | None, guard, controller=None, reason: str = "manual"):
        super().__init__(parent)
        self.guard, self.controller = guard, controller
        s = guard.settings.safety
        self.setWindowTitle(tr("Beaker setup"))
        self.setModal(False)
        self.setMinimumWidth(620)
        self._zero_since: float | None = None
        self._weight: float | None = guard.weight

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(14)
        root.addWidget(label(tr("Beaker setup"), "pageTitle"))
        intro = {"start": tr("Before testing: zero the balance and tell DeltaM about the beaker, so it can warn you "
                             "before the water overflows."),
                 "removed": tr("The beaker was taken off. Zero the balance, then put the beaker back.")}
        note = label(intro.get(reason, tr("Zero the balance and set the beaker so DeltaM can warn before it "
                                           "overflows.")), "pageSubtitle")
        note.setWordWrap(True)
        root.addWidget(note)

        chips = QHBoxLayout()
        self.chip1, self.chip2 = _step_chip(1, tr("Empty pan · RE-ZERO")), _step_chip(2, tr("Place the beaker"))
        chips.addWidget(self.chip1)
        chips.addWidget(self.chip2)
        chips.addStretch(1)
        root.addLayout(chips)

        # น้ำหนักสด (ใหญ่ ชัด)
        live = QFrame()
        live.setProperty("card", True)
        live_row = QHBoxLayout(live)
        live_row.setContentsMargins(18, 12, 18, 12)
        self.meter = BeakerMeter(QSize(54, 68))
        live_row.addWidget(self.meter)
        live_box = QVBoxLayout()
        self.weight_label = label("—", "weight")
        self.weight_state = label("", "hint")
        live_box.addWidget(label(tr("Balance reading"), "fieldLabel"))
        live_box.addWidget(self.weight_label)
        live_box.addWidget(self.weight_state)
        live_row.addLayout(live_box, 1)
        root.addWidget(live)

        self.pages = QStackedWidget()
        root.addWidget(self.pages)

        # ---- ขั้น 1
        page1 = QWidget()
        box1 = QVBoxLayout(page1)
        box1.setContentsMargins(0, 0, 0, 0)
        steps = label("1.  " + tr("Take the beaker and everything else off the pan.") + "\n"
                      + "2.  " + tr("Press RE-ZERO on the balance and wait until it shows 0.000 g."), "")
        steps.setStyleSheet("font-size: 15px; line-height: 150%;")
        steps.setWordWrap(True)
        box1.addWidget(steps)
        self.zero_status = label("", "hint")
        box1.addWidget(self.zero_status)
        self.pages.addWidget(page1)

        # ---- ขั้น 2
        page2 = QWidget()
        grid = QGridLayout(page2)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        info = label(tr("Put the beaker on the pan — empty or already holding water."), "")
        info.setStyleSheet("font-size: 15px;")
        info.setWordWrap(True)
        grid.addWidget(info, 0, 0, 1, 4)
        self.capacity = QDoubleSpinBox()
        self.capacity.setRange(5, 5000)
        self.capacity.setDecimals(0)
        self.capacity.setSuffix(" ml")
        self.capacity.setValue(s.beaker_capacity_ml)
        self.empty = QDoubleSpinBox()
        self.empty.setRange(0, 5000)
        self.empty.setDecimals(1)
        self.empty.setSuffix(" g")
        self.empty.setValue(s.beaker_mass_g)
        grid.addWidget(label(tr("Beaker capacity"), "fieldLabel"), 1, 0)
        grid.addWidget(self.capacity, 1, 1)
        grid.addWidget(label(tr("Empty beaker weight"), "fieldLabel"), 1, 2)
        grid.addWidget(self.empty, 1, 3)
        self.btn_empty_now = QPushButton(tr("The beaker on the pan is empty — use this reading"))
        self.btn_empty_now.setProperty("variant", "ghost")
        grid.addWidget(self.btn_empty_now, 2, 2, 1, 2)
        self.result = label("", "metricValue")
        self.result.setWordWrap(True)
        grid.addWidget(self.result, 3, 0, 1, 4)
        self.remember = QCheckBox(tr("Remember capacity and empty weight as the defaults"))
        grid.addWidget(self.remember, 4, 0, 1, 4)
        self.pages.addWidget(page2)

        buttons = QHBoxLayout()
        self.btn_skip = QPushButton(tr("Skip for now"))
        self.btn_skip.setToolTip(tr("No overflow warnings until the beaker is set (Balance card → Beaker…)"))
        self.btn_back = QPushButton(tr("Back"))
        self.btn_next = QPushButton(tr("Already zeroed — next"))
        self.btn_done = QPushButton(tr("Start watching the beaker"))
        self.btn_done.setProperty("variant", "primary")
        buttons.addWidget(self.btn_skip)
        buttons.addStretch(1)
        for button in (self.btn_back, self.btn_next, self.btn_done):
            buttons.addWidget(button)
        root.addLayout(buttons)

        self.btn_skip.clicked.connect(self.reject)
        self.btn_back.clicked.connect(lambda: self._go(0))
        self.btn_next.clicked.connect(lambda: self._go(1))
        self.btn_done.clicked.connect(self._finish)
        self.btn_empty_now.clicked.connect(self._use_reading_as_empty)
        self.capacity.valueChanged.connect(self._refresh)
        self.empty.valueChanged.connect(self._refresh)
        if controller is not None:
            controller.live_reading.connect(self._on_reading)
            controller.balance_status.connect(self._on_status)
        self._go(0)
        self._refresh()

    # ------------------------------------------------------------ น้ำหนักสด
    def _on_status(self, connected: bool, text: str) -> None:
        if not connected:
            self.weight_label.setText("—")
            self.weight_state.setText(tr("Balance not connected") + (f" — {text}" if text and text != "no data" else ""))

    def _on_reading(self, weight: float, stable=None) -> None:
        self._weight = float(weight)
        self.weight_label.setText(f"{weight:.3f} g")
        self.weight_state.setText("" if stable is None else tr("stable") if stable else tr("unstable"))
        if self.pages.currentIndex() == 0:
            if abs(weight) <= EMPTY_PAN_G * 0.4 and stable is not False:
                self._zero_since = self._zero_since or time.monotonic()
                held = time.monotonic() - self._zero_since
                self.zero_status.setText("✓ " + tr("Zero OK"))
                self.zero_status.setStyleSheet(f"color: {Color.SUCCESS}; font-weight: 600;")
                if held >= ZERO_HOLD_S:
                    self._go(1)
            else:
                self._zero_since = None
                self.zero_status.setText(tr("Waiting for 0.000 g…"))
                self.zero_status.setStyleSheet(f"color: {Color.TEXT_MUTED};")
        self._refresh()

    def set_reading(self, weight: float, stable=None) -> None:
        """สำหรับเทสต์/เรียกตรง"""
        self._on_reading(weight, stable)

    # ------------------------------------------------------------ ขั้น
    def _go(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for chip, active in ((self.chip1, index == 0), (self.chip2, index == 1)):
            chip.setStyleSheet(
                f"padding: 6px 12px; border-radius: 13px; font-weight: 600;"
                f"background: {Color.ACCENT if active else Color.SURFACE_ALT};"
                f"color: {Color.ON_ACCENT if active else Color.TEXT_MUTED};")
        self.btn_back.setVisible(index == 1)
        self.btn_next.setVisible(index == 0)
        self.btn_done.setVisible(index == 1)
        self._refresh()

    def _use_reading_as_empty(self) -> None:
        if self._weight is not None and self._weight > PLACE_MIN_G:
            self.empty.setValue(self._weight)

    def _beaker(self) -> Beaker:
        return Beaker(capacity_ml=self.capacity.value(), empty_g=self.empty.value(), known=True)

    def _refresh(self) -> None:
        beaker = self._beaker()
        weight = self._weight
        placed = weight is not None and weight > PLACE_MIN_G
        if self.pages.currentIndex() == 1:
            self.btn_empty_now.setEnabled(placed)
            self.btn_done.setEnabled(placed)
            if not placed:
                self.result.setText(tr("Waiting for the beaker on the pan…"))
                self.result.setStyleSheet(f"color: {Color.TEXT_MUTED};")
                self.meter.set_level(None)
                return
            if weight < beaker.empty_g - 1.0:
                self.result.setText(tr("The reading is lighter than the empty beaker weight — check the empty "
                                       "weight (or press the button above if the beaker is empty)."))
                self.result.setStyleSheet(f"color: {Color.WARNING};")
            else:
                s = self.guard.settings.safety
                fill = beaker.fill_pct(weight)
                color = Color.DANGER if fill >= s.alarm_pct else Color.WARNING if fill >= s.warn_pct else Color.TEXT
                self.result.setText(tr("Water now {ml:.1f} ml · room for {free:.1f} ml ({pct:.0f} % full)",
                                       ml=beaker.water_ml(weight), free=beaker.free_ml(weight), pct=fill))
                self.result.setStyleSheet(f"color: {color};")
            s = self.guard.settings.safety
            self.meter.set_level(beaker.fill_pct(weight), s.warn_pct, s.alarm_pct)
        else:
            self.meter.set_level(None)

    def _finish(self) -> None:
        beaker = self._beaker()
        if self.remember.isChecked():
            s = self.guard.settings.safety
            s.beaker_capacity_ml, s.beaker_mass_g = beaker.capacity_ml, beaker.empty_g
            try:
                self.guard.settings.save()
            except OSError:
                pass
        if self._weight is not None:
            self.guard.on_weight(self._weight)
        self.guard.set_beaker(beaker.capacity_ml, beaker.empty_g)
        self.accept()

    def done(self, result: int) -> None:
        if self.controller is not None:
            for signal, slot in ((self.controller.live_reading, self._on_reading),
                                 (self.controller.balance_status, self._on_status)):
                try:
                    signal.disconnect(slot)
                except (RuntimeError, TypeError):
                    pass
        super().done(result)
