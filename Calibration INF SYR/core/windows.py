"""ขนาดหน้าต่างของวิธีจับรอบปั๊ม — จุดเดียวที่แปลง "คาบ x สัดส่วน" เป็นจำนวนจุด (ใช้ทั้ง engine, controller, tuning, UI)

    N regression = round(คาบ x r / ช่วงเวลาต่อจุด)     ขั้นต่ำ MIN_REGRESSION_POINTS
    n̄ (peak)    = round(คาบ x h / ช่วงเวลาต่อจุด)     ขั้นต่ำ MIN_HALF_POINTS
    จุดต่อรอบ    = คาบ / ช่วงเวลาต่อจุด

ขั้นต่ำมาจากข้อมูลจริง (session id 11: TE-112 + ME 20 drops, 200 ml/h, ตราชั่ง 5 Hz = 10.6 จุดต่อรอบ):
    regression 5–10 จุด / n̄ 3–5 จุด จับคาบได้ถูก (เวลาต่อรอบ / คาบ = 0.99)
    4 / 2 เริ่มแกว่ง (CV เวลาต่อรอบ 0.12 จาก 0.05) · 3 / 2 จับผิด (0.85 เท่าของคาบ)
เดิมโค้ดถอยไปใช้ค่าในหน้าตั้งค่า (250/250) เงียบๆ เมื่อได้ < 5 จุด และขั้นต่ำ 10 จุดตายตัว — ยกเลิกแล้ว

ช่วงที่ใช้ได้ของสัดส่วน (ข้อ ง):
    แนะนำ 0.3–0.5 x คาบ: ข้อมูลจริง TE-171 < 0.3 จับ "ครึ่งรอบ", > 0.5 ข้ามรอบ — นอกช่วงนี้ = เตือน
    ยอมรับได้ 0.1–0.75 x คาบ: นอกช่วงนี้ = ไม่ให้บันทึก/เริ่ม
    ค่าที่ปรับจากข้อมูลจริง (tuned) ผ่านการให้คะแนนเทียบคาบมาแล้ว จึงไม่เตือนเรื่องช่วงแนะนำ
จุดต่อรอบ (ข้อเสนอจากข้อมูลจุดเดียว — ยังไม่ยืนยันกับปั๊มรุ่นอื่น):
    < WARN_POINTS_PER_CYCLE (12)   จับ peak ได้ แต่ผลรายรอบแกว่งมาก -> เตือน + เสนอจับตามเวลา
    < MIN_POINTS_PER_CYCLE (8)     ไม่ให้เริ่มแบบจับรอบปั๊ม -> จับตามเวลา หรือเพิ่มความถี่ตราชั่ง
"""
from __future__ import annotations

import math
from dataclasses import dataclass

MIN_REGRESSION_POINTS = 5
MIN_HALF_POINTS = 3
WARN_POINTS_PER_CYCLE = 12.0
MIN_POINTS_PER_CYCLE = 8.0
RECOMMENDED_FRACTION = (0.3, 0.5)
ALLOWED_FRACTION = (0.1, 0.75)
TIME_WINDOW_MIN_S = 30.0        # ช่วงของวิธีจับตามเวลาที่เสนอแทน: จำนวนเต็มเท่าของคาบ อย่างน้อยเท่านี้


@dataclass(frozen=True, slots=True)
class CycleWindows:
    regression: int                 # จุด
    half: int                       # n̄ (จุด)
    points_per_cycle: float
    regression_fraction: float      # ที่ขอ
    half_fraction: float
    clamped: bool                   # ชนขั้นต่ำ (ค่าจริงเป็นสัดส่วนของคาบมากกว่าที่ขอ)

    @property
    def level(self) -> str:
        """ok | low (เตือน) | too_low (ไม่ให้เริ่มแบบจับรอบปั๊ม)"""
        if self.points_per_cycle < MIN_POINTS_PER_CYCLE:
            return "too_low"
        if self.points_per_cycle < WARN_POINTS_PER_CYCLE:
            return "low"
        return "ok"

    @property
    def effective_fractions(self) -> tuple[float, float]:
        """สัดส่วนของคาบที่ใช้จริงหลังปัดเป็นจุด/ชนขั้นต่ำ"""
        ppc = max(self.points_per_cycle, 1e-9)
        return self.regression / ppc, self.half / ppc


def cycle_windows(period_s: float | None, sample_period_s: float | None, regression_fraction: float,
                  half_fraction: float | None = None) -> CycleWindows | None:
    """จำนวนจุดของหน้าต่างจากคาบ — None เมื่อไม่รู้คาบหรือช่วงเวลาต่อจุด (ไม่มีการเดาค่าตายตัว)"""
    if half_fraction is None or half_fraction <= 0:
        half_fraction = regression_fraction
    if not period_s or not sample_period_s or period_s <= 0 or sample_period_s <= 0:
        return None
    ppc = period_s / sample_period_s
    regression_raw, half_raw = round(ppc * regression_fraction), round(ppc * half_fraction)
    regression = max(MIN_REGRESSION_POINTS, regression_raw)
    half = max(MIN_HALF_POINTS, half_raw)
    return CycleWindows(regression, half, ppc, regression_fraction, half_fraction,
                        clamped=regression != regression_raw or half != half_raw)


def fraction_problems(regression_fraction: float, half_fraction: float, tuned: bool = False) -> list[tuple[str, str]]:
    """ตรวจสัดส่วนของคาบ [(ระดับ "error" | "warning", ข้อความอังกฤษสำหรับ tr())]"""
    problems = []
    low, high = ALLOWED_FRACTION
    for name, value in (("Regression", regression_fraction), ("n̄", half_fraction)):
        if not low <= value <= high:
            problems.append(("error", f"{name} must be between {low:g} and {high:g} × cycle"))
        elif not tuned and not RECOMMENDED_FRACTION[0] <= value <= RECOMMENDED_FRACTION[1]:
            problems.append(("warning", f"{name} outside {RECOMMENDED_FRACTION[0]:g}–{RECOMMENDED_FRACTION[1]:g} × cycle "
                                        f"(below catches half cycles, above skips cycles)"))
    return problems


def fractions_from_points(regression: int, half: int, period_s: float, sample_period_s: float) -> tuple[float, float]:
    """แปลงจำนวนจุดที่ผู้ใช้กรอกกลับเป็นสัดส่วนของคาบ (เก็บเป็นสัดส่วน ใช้ได้ทั้งตราชั่ง 5 และ 10 Hz)"""
    ppc = period_s / sample_period_s
    return round(regression / ppc, 4), round(half / ppc, 4)


def time_window_for(period_s: float, minimum_s: float = TIME_WINDOW_MIN_S) -> float:
    """ช่วงของวิธีจับตามเวลาที่เป็นจำนวนเต็มเท่าของคาบ และยาวอย่างน้อย minimum_s

    (ข้อมูลจริง: 200 ml/h TE-112 ช่วง 14 x คาบ ได้ ±2SD 2.4 % เทียบจับ peak รายรอบ ±7–8 %)
    """
    if period_s <= 0:
        return minimum_s
    return round(period_s * max(1, math.ceil(minimum_s / period_s)), 2)
