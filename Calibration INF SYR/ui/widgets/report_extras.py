"""ค่าที่วัด/ตรวจด้วยมือสำหรับใบรายงาน: สัญญาณเตือนการอุดตัน (3 ครั้ง) · ความปลอดภัยทางไฟฟ้า · ตรวจขั้นสุดท้าย

ใช้ทั้งใน wizard ขั้นที่ 2 (กรอกตั้งแต่ต้น — ผู้ใช้ 2026-11-18) และหน้าข้อมูลใบรายงาน (แก้ภายหลัง)
ค่าเป็น dict ชื่อเดียวกับ services.report.model.ReportInfo (occl_*, supply_v, leak_ua, whole_checked, label_attached)
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLineEdit, QWidget

from config.i18n import tr
from services.report.model import occl_stats
from ui.widgets.common import label

# หน่วยความดันของการอุดตัน — kgf/cm² (ผู้ใช้ 2026-11-20: เครื่องบางรุ่นแสดง kg/cm² · 1 kgf/cm² = 98.0665 kPa)
OCCL_UNITS = ("kPa", "mmHg", "psi", "bar", "kgf/cm²")
FIELDS = ("occl_level", "occl_unit", "occl_runs", "occl_low", "occl_high", "supply_v", "leak_ua",
          "whole_checked", "label_attached", "battery_rate", "battery_min")
LIMIT_FIELDS = ("occl_level", "occl_unit", "occl_low", "occl_high")


def defaults_from(report_settings, pump: str = "infusion") -> dict:
    """ค่าตั้งต้นของขั้นค่าที่วัด (wizard ขั้น 5) จากหน้าตั้งค่า (ตัวเลข 0 = ว่าง)
    การอุดตันแยก Infusion / Syringe ตามชนิดเครื่องที่เลือกในขั้น 1 (ผู้ใช้ 2026-11-20)"""
    r = report_settings
    number_or_none = lambda v: float(v) if v else None      # noqa: E731
    ticks = bool(getattr(r, "default_final_ticks", True))
    occl = r.occlusion_defaults(pump) if hasattr(r, "occlusion_defaults") else dict(
        level=getattr(r, "default_occl_level", ""), unit=getattr(r, "default_occl_unit", "kPa"),
        low=getattr(r, "default_occl_low", 0), high=getattr(r, "default_occl_high", 0))
    return dict(occl_level=occl["level"] or "", occl_unit=occl["unit"] or "kPa",
                occl_low=number_or_none(occl["low"]), occl_high=number_or_none(occl["high"]),
                supply_v=number_or_none(getattr(r, "default_supply_v", 0)),
                battery_min=number_or_none(getattr(r, "default_battery_min", 0)),
                whole_checked=ticks, label_attached=ticks)


class _Spin(QDoubleSpinBox):
    """ไม่รับล้อเมาส์จนกว่าจะคลิกเข้าช่อง — เลื่อนหน้า wizard แล้วเคอร์เซอร์ผ่านช่อง ค่าไม่เปลี่ยนเอง
    (ผู้ใช้ 2026-11-19: ครั้งที่ 1 กลายเป็น 0.00 เอง แล้วผลขึ้น "ไม่ผ่าน")"""

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()                      # ส่งต่อให้หน้าเลื่อนตามปกติ


def number(maximum: float, decimals: int = 0, suffix: str = "") -> QDoubleSpinBox:
    """ช่องตัวเลขที่ว่างได้ (ค่าต่ำสุด = ว่าง แสดงเป็น —)"""
    box = _Spin()
    box.setRange(-1, maximum)
    box.setDecimals(decimals)
    box.setSpecialValueText("—")
    box.setSuffix(suffix)
    box.setValue(-1)
    box.setMinimumWidth(90)
    return box


def get(box: QDoubleSpinBox) -> float | None:
    return None if box.value() < 0 else round(box.value(), box.decimals())


def reading(box: QDoubleSpinBox) -> float | None:
    """ค่าความดันที่วัดได้: 0 หรือว่าง = ยังไม่ได้วัด (สัญญาณเตือนการอุดตันที่ 0 เป็นไปไม่ได้)"""
    value = get(box)
    return value if value is not None and value > 0 else None


def put(box: QDoubleSpinBox, value) -> None:
    box.setValue(-1 if value is None or value == "" else float(value))


class ReportExtras(QWidget):
    changed = Signal()

    def __init__(self, leak_limit_ua: float = 300.0, ticks_default: bool = True):
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        row = 0
        self._occl_widgets: list[QWidget] = []      # ซ่อนทั้งกลุ่มเมื่อไม่ใช่ Calibration (set_occlusion_visible)
        self._occl_visible = True
        # ---- สัญญาณเตือนการอุดตัน
        title = label(tr("Occlusion alarm"), "cardTitle")
        self._occl_widgets.append(title)
        grid.addWidget(title, row, 0, 1, 8)
        row += 1
        self.occl_level = QLineEdit()
        self.occl_level.setPlaceholderText(tr("e.g. M"))
        self.occl_level.setMaximumWidth(80)
        self.occl_unit = QComboBox()
        for unit in OCCL_UNITS:
            self.occl_unit.addItem(unit, unit)
        self.occl_runs = [number(10000, 2) for _ in range(3)]
        self.occl_low, self.occl_high = number(10000, 2), number(10000, 2)
        level_caption = label(tr("Level set"), "fieldLabel")
        grid.addWidget(level_caption, row, 0)
        grid.addWidget(self.occl_level, row, 1)
        grid.addWidget(self.occl_unit, row, 2)
        self._occl_widgets += [level_caption, self.occl_level, self.occl_unit]
        runs = QHBoxLayout()
        runs.setContentsMargins(0, 0, 0, 0)
        for index, box in enumerate(self.occl_runs, 1):
            runs.addWidget(label(tr("Run {n}", n=index), "fieldLabel"))
            runs.addWidget(box)
        holder = QWidget()
        holder.setLayout(runs)
        grid.addWidget(holder, row, 3, 1, 5)
        self._occl_widgets.append(holder)
        row += 1
        limit_caption = label(tr("Manufacturer's limit"), "fieldLabel")
        self._occl_widgets.append(limit_caption)
        grid.addWidget(limit_caption, row, 0)
        limits = QHBoxLayout()
        limits.setContentsMargins(0, 0, 0, 0)
        limits.addWidget(self.occl_low)
        limits.addWidget(label("–", "fieldLabel"))
        limits.addWidget(self.occl_high)
        limits.addStretch(1)
        holder = QWidget()
        holder.setLayout(limits)
        grid.addWidget(holder, row, 1, 1, 3)
        self.occl_result = label("", "hint")
        grid.addWidget(self.occl_result, row, 4, 1, 4)
        self._occl_widgets += [holder, self.occl_result]
        row += 1
        # ---- ความปลอดภัยทางไฟฟ้า
        grid.addWidget(label(tr("Electrical safety"), "cardTitle"), row, 0, 1, 8)
        row += 1
        self.supply, self.leak = number(1000, 0, " V"), number(100000, 0, " µA")
        grid.addWidget(label(tr("Supply voltage"), "fieldLabel"), row, 0)
        grid.addWidget(self.supply, row, 1, 1, 2)
        grid.addWidget(label(tr("Equipment leakage current"), "fieldLabel"), row, 3)
        grid.addWidget(self.leak, row, 4)
        self.leak_note = label(tr("Limit {v:g} µA", v=leak_limit_ua), "hint")
        grid.addWidget(self.leak_note, row, 5, 1, 3)
        row += 1
        # ---- แบตเตอรี่: ไม่ใช่การทดสอบ — ยืนยันว่าใช้งานด้วยแบตเตอรี่ได้มากกว่า N นาที (ผู้ใช้ 2026-11-20)
        # ใบเขียน "ใช้งานด้วยแบตเตอรี่ได้มากกว่า 30 นาที" · ค่าตั้งต้นในหน้าตั้งค่า · อัตราทดสอบเดิม (งานเก่า) เก็บไว้ไม่แสดง
        grid.addWidget(label(tr("Battery operation"), "cardTitle"), row, 0, 1, 8)
        row += 1
        self.battery_min = number(10000, 0, " " + tr("min"))
        self._battery_rate = None
        grid.addWidget(label(tr("Runs on battery for more than"), "fieldLabel"), row, 0)
        grid.addWidget(self.battery_min, row, 1, 1, 2)
        grid.addWidget(label(tr("Not a test — the report states the unit can run on battery for longer than this"),
                             "hint"), row, 3, 1, 5)
        row += 1
        # ---- ตรวจขั้นสุดท้าย (ตั้งต้นติ๊ก — เหมือนรายการตรวจที่ตั้งต้นผ่าน)
        self.whole = QCheckBox(tr("Whole unit checked"))
        self.label_box = QCheckBox(tr("Inspection label attached"))
        self.whole.setChecked(ticks_default)
        self.label_box.setChecked(ticks_default)
        ticks = QHBoxLayout()
        ticks.setContentsMargins(0, 4, 0, 0)
        ticks.addWidget(self.whole)
        ticks.addSpacing(20)
        ticks.addWidget(self.label_box)
        ticks.addStretch(1)
        holder = QWidget()
        holder.setLayout(ticks)
        grid.addWidget(holder, row, 0, 1, 8)
        grid.setColumnStretch(7, 1)

        for box in (*self.occl_runs, self.occl_low, self.occl_high):
            box.valueChanged.connect(self._update_result)
        self.occl_unit.currentIndexChanged.connect(self._update_result)
        self._update_result()

    # ---------------------------------------------------------------- ค่า
    def set_occlusion_visible(self, visible: bool) -> None:
        """การอุดตันวัดเฉพาะงาน Calibration (ใบ Inspection เขียน "ทำงานปกติ" ไม่ใส่ค่า — ผู้ใช้ 2026-11-19)
        ซ่อนแล้ว values() ไม่ส่งค่าที่วัด (ระดับ/หน่วย/เกณฑ์ของรุ่นยังส่ง — ใช้เติมงานหน้าของรุ่นเดียวกัน)"""
        self._occl_visible = visible
        for widget in self._occl_widgets:
            widget.setVisible(visible)

    def set_values(self, data: dict) -> None:
        self.occl_level.setText(str(data.get("occl_level") or ""))
        self.occl_unit.setCurrentIndex(max(0, self.occl_unit.findData(data.get("occl_unit") or "kPa")))
        runs = list(data.get("occl_runs") or [])[:3]
        for box, value in zip(self.occl_runs, runs + [None] * (3 - len(runs))):
            put(box, value)
        put(self.occl_low, data.get("occl_low"))
        put(self.occl_high, data.get("occl_high"))
        put(self.supply, data.get("supply_v"))
        put(self.leak, data.get("leak_ua"))
        self._battery_rate = data.get("battery_rate")     # งานเก่า — คงค่าไว้ (ไม่แสดง)
        put(self.battery_min, data.get("battery_min"))
        if "whole_checked" in data:
            self.whole.setChecked(bool(data.get("whole_checked")))
        if "label_attached" in data:
            self.label_box.setChecked(bool(data.get("label_attached")))
        self._update_result()

    def set_limits(self, data: dict, defaults: dict | None = None) -> None:
        """เติมเกณฑ์ผู้ผลิต/ระดับ/หน่วยจากงานก่อนของรุ่นเดียวกัน — เฉพาะช่องที่ยังว่าง หรือยังเป็นค่าตั้งต้นจากหน้าตั้งค่า
        (ค่าของรุ่นแม่นกว่าค่าตั้งต้นรวม — ผู้ใช้ 2026-11-19)"""
        current = self.values()
        if defaults and data.get("occl_low") is not None and all(current.get(k) == defaults.get(k) for k in LIMIT_FIELDS):
            self.occl_level.setText(str(data.get("occl_level") or ""))
            self.occl_unit.setCurrentIndex(max(0, self.occl_unit.findData(data.get("occl_unit") or "kPa")))
            put(self.occl_low, data.get("occl_low"))
            put(self.occl_high, data.get("occl_high"))
            return
        if not self.occl_level.text().strip() and data.get("occl_level"):
            self.occl_level.setText(str(data["occl_level"]))
        if get(self.occl_low) is None and get(self.occl_high) is None and data.get("occl_low") is not None:
            self.occl_unit.setCurrentIndex(max(0, self.occl_unit.findData(data.get("occl_unit") or "kPa")))
            put(self.occl_low, data.get("occl_low"))
            put(self.occl_high, data.get("occl_high"))

    def apply_defaults(self, new: dict, old: dict) -> None:
        """ชนิดเครื่องเปลี่ยน: ค่าการอุดตัน (ระดับ/หน่วย/เกณฑ์) ที่ยังเป็นค่าตั้งต้นของชนิดเดิม -> ค่าตั้งต้นของชนิดใหม่
        (ที่ผู้ใช้แก้เอง หรือเติมจากรุ่นแล้ว ไม่ทับ)"""
        current = self.values()
        if all(current.get(k) == old.get(k) for k in LIMIT_FIELDS):
            self.occl_level.setText(str(new.get("occl_level") or ""))
            self.occl_unit.setCurrentIndex(max(0, self.occl_unit.findData(new.get("occl_unit") or "kPa")))
            put(self.occl_low, new.get("occl_low"))
            put(self.occl_high, new.get("occl_high"))
            self._update_result()

    def values(self) -> dict:
        runs = [reading(box) for box in self.occl_runs] if self._occl_visible else [None, None, None]
        return dict(occl_level=self.occl_level.text().strip(), occl_unit=self.occl_unit.currentData(),
                    occl_runs=runs, occl_low=get(self.occl_low),
                    occl_high=get(self.occl_high), supply_v=get(self.supply), leak_ua=get(self.leak),
                    whole_checked=self.whole.isChecked(), label_attached=self.label_box.isChecked(),
                    battery_rate=self._battery_rate, battery_min=get(self.battery_min))

    def _update_result(self, *_args) -> None:
        values = [reading(box) for box in self.occl_runs]
        stats = occl_stats(values)
        if stats is None:
            self.occl_result.setText("")
            self.changed.emit()
            return
        mean, sd2, digits = stats
        text = tr("Mean {mean} ± {sd2} (2SD) {unit}", mean=f"{mean:.{digits}f}", sd2=f"{sd2:.{digits}f}",
                  unit=self.occl_unit.currentData())
        count = sum(v is not None for v in values)
        if count < len(values):                 # ยังวัดไม่ครบ — บอกไว้ ไม่ให้ดูเหมือนผลสุดท้าย
            text += "  ·  " + tr("{n} of {total} runs", n=count, total=len(values))
        low, high = get(self.occl_low), get(self.occl_high)
        if low is not None and high is not None:
            text += "  ·  " + (tr("Pass") if low <= mean <= high else tr("Fail"))
        self.occl_result.setText(text)
        self.changed.emit()
