"""หน้าต่างจับรอบปั๊ม "ราย rate" ของ ยี่ห้อ + รุ่น + ชนิด + ชุดสาย — ใช้ร่วมกันทั้ง wizard, แผงแผนทดสอบ, controller
และหน้าข้อมูลสอบเทียบในตั้งค่า (ทุกที่เห็นค่าเดียวกัน ไม่มี "ค่าเดียวทุก rate")

ต่อ 1 rate:
    คาบ        rate        เคยวัดที่ rate นี้ (ค่าเฉลี่ยที่ยอมรับ)
               profile     จากปริมาตรต่อรอบของโปรไฟล์
               model_default  ค่าแทนไปก่อนของรุ่นที่ผู้ใช้กำหนด
               estimate    เดาจากปริมาตรต่อรอบเริ่มต้นในหน้าตั้งค่า (ยังไม่รู้จักรุ่นนี้)
    สัดส่วน    tuned (สอบเทียบแล้ว) | manual | uncalibrated | interpolated | default | plan (กำหนดในแผนนี้)
    จำนวนจุด   core.windows.cycle_windows(คาบ, ช่วงเวลาต่อจุด, r, h)
ไม่มี Qt
"""
from __future__ import annotations

from dataclasses import dataclass, field

from config.settings import AppSettings, EngineSettings
from core.windows import CycleWindows, cycle_windows, fraction_problems

FALLBACK_STROKE_VOLUME_ML = 0.16
RELIABLE_PERIODS = ("rate", "profile")      # คาบที่มาจากการวัดจริง (ใช้ตรวจผลหลังจบได้)

# ที่มาของสัดส่วน -> ข้อความบนจอ (อังกฤษ สำหรับ tr())
FIT_TEXT = {
    "tuned": "✓ Calibrated",
    "manual": "Set by hand · not calibrated",
    "uncalibrated": "⚠ Saved default · not calibrated",
    "interpolated": "From neighbouring calibrated rates",
    "default": "⚠ Not calibrated (default)",
    "plan": "Set for this test",
}
PERIOD_TEXT = {"rate": "measured", "profile": "from volume per cycle", "model_default": "model default",
               "estimate": "estimated"}


@dataclass
class RateWindow:
    rate: float
    period_s: float | None
    period_source: str
    regression_fraction: float
    half_fraction: float
    fit: str
    windows: CycleWindows | None = None
    problems: list[tuple[str, str]] = field(default_factory=list)

    @property
    def calibrated(self) -> bool:
        return self.fit == "tuned"

    @property
    def level(self) -> str:
        """ok | low | too_low | unknown (ไม่รู้ช่วงเวลาต่อจุด)"""
        return self.windows.level if self.windows else "unknown"

    @property
    def blocking(self) -> bool:
        """เริ่มแบบจับรอบปั๊มไม่ได้: จุดต่อรอบน้อยเกิน หรือสัดส่วนนอกช่วงที่ยอมรับ"""
        return self.level == "too_low" or any(kind == "error" for kind, _ in self.problems)

    @property
    def warnings(self) -> bool:
        return not self.calibrated or self.level in ("low", "too_low") or bool(self.problems)


def sample_period_estimate(settings: AppSettings, measured: float | None, repository=None) -> tuple[float | None, str]:
    """(ช่วงเวลาต่อจุดของตราชั่ง, ที่มา) — วัดจริงตอนว่าง > ตราชั่งจำลอง > ผลล่าสุดที่บันทึกไว้"""
    if measured and measured > 0:
        return measured, "measured"
    if settings.source == "simulator" and settings.simulator.sample_rate_hz > 0:
        return 1.0 / settings.simulator.sample_rate_hz, "simulator"
    if repository is not None:
        latest = repository.latest_sample_period()
        if latest:
            return latest, "last_test"
    return None, ""


def rate_window(repository, engine: EngineSettings, job, rate: float, sample_period_s: float | None,
                override: tuple[float, float] | None = None, stroke_ml: float | None = None,
                use_known_period: bool = True) -> RateWindow:
    """หน้าต่างที่ rate นี้จะใช้ (override = สัดส่วนที่กำหนดในแผน)"""
    brand, model, iv_set, pump_type = job.brand, job.model, job.accessory, job.pump_type.value
    period, period_source = (None, "")
    if use_known_period:
        period, period_source = repository.expected_period_info(brand, model, iv_set, rate, pump_type)
    if not period and rate > 0:
        stroke = stroke_ml or engine.default_stroke_volume_ml or FALLBACK_STROKE_VOLUME_ML
        period, period_source = stroke * 3600.0 / rate, "estimate"
    if override and override[0] > 0:
        r, h, fit = override[0], override[1] or override[0], "plan"
    else:
        r, h, fit = repository.window_fractions(brand, model, iv_set, rate,
                                                (engine.auto_window_fraction, engine.half_fraction), pump_type)
    windows = cycle_windows(period, sample_period_s, r, h)
    return RateWindow(rate, period, period_source, r, h, fit, windows, fraction_problems(r, h, tuned=fit == "tuned"))


def plan_windows(repository, engine: EngineSettings, job, rates: list[float], sample_period_s: float | None,
                 overrides: dict[float, tuple[float, float]] | None = None,
                 stroke_ml: float | None = None) -> list[RateWindow]:
    overrides = overrides or {}
    return [rate_window(repository, engine, job, rate, sample_period_s, overrides.get(rate), stroke_ml) for rate in rates]


def window_summary(item: RateWindow) -> str:
    """ข้อความสั้น 1 บรรทัด (ภาษาอังกฤษ — ผู้เรียกแปลแต่ละส่วนเอง ดู ui) สำหรับ log"""
    period = f"{item.period_s:.2f} s" if item.period_s else "—"
    if item.windows:
        return (f"{item.rate:g} ml/h: cycle {period} ({item.period_source}), regression {item.windows.regression} pts, "
                f"n̄ {item.windows.half} pts, {item.windows.points_per_cycle:.1f} pts/cycle, {item.fit}")
    return f"{item.rate:g} ml/h: cycle {period} ({item.period_source}), r {item.regression_fraction:.2f} × cycle, " \
           f"n̄ {item.half_fraction:.2f} × cycle, {item.fit}"
