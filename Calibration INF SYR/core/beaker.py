"""ความปลอดภัยของบีกเกอร์รับน้ำ (ผู้ใช้ 2026-11-20) — คำนวณล้วน ไม่มี Qt

ตราชั่งอ่านได้ = น้ำหนักบีกเกอร์เปล่า + น้ำ (หลังกด RE-ZERO ตอนไม่มีอะไรบนจาน)
    น้ำ (ml) ≈ (น้ำหนัก − บีกเกอร์เปล่า) ÷ 0.998 g/ml (ใช้เตือนเท่านั้น ไม่ใช้คำนวณผล — ความแม่นระดับ 0.5 % พอ)
    เต็ม (%) = น้ำ ÷ ความจุบีกเกอร์ × 100

ระดับ:
    ok      ต่ำกว่าเกณฑ์เตือน
    warn    ≥ warn_pct  ใกล้เต็ม — เสียงเตือน + popup (การทดสอบเดินต่อได้)
    alarm   ≥ alarm_pct จะล้น — เสียงดังซ้ำ + popup ใหญ่จนกว่าผู้ใช้กดรับทราบ (การทดสอบยังเดินต่อได้)
ก่อนเริ่ม rate: คาดปริมาตรเมื่อจบ = น้ำตอนนี้ + rate × (เวลาทดสอบ + เวลาเผื่อ) — เกิน alarm_pct = ถามก่อนเริ่ม
หลังจบ rate แต่ปั๊มยังเดิน (น้ำหนักยังขึ้น): เตือนนุ่มเป็นจังหวะ "หยุดปั๊มได้แล้ว" (PumpRunningDetector)
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

WATER_G_PER_ML = 0.998          # น้ำที่ ~21 °C — พอสำหรับการเตือน
EMPTY_PAN_G = 0.05              # น้ำหนักต่ำกว่านี้ = จานว่าง (ยกบีกเกอร์ออก / หลัง RE-ZERO)
REMOVED_FRACTION = 0.5          # น้ำหนักต่ำกว่าครึ่งของบีกเกอร์เปล่า = ยกบีกเกอร์ออกแล้ว


@dataclass
class Beaker:
    capacity_ml: float = 150.0
    empty_g: float = 68.0           # บีกเกอร์เปล่า (ชั่งได้ตอนตั้งค่า หรือค่าที่ตั้งไว้)
    known: bool = False             # ผ่านขั้นตั้งค่า (RE-ZERO + วางบีกเกอร์) แล้วหรือยัง

    def water_ml(self, weight_g: float) -> float:
        return max(0.0, (weight_g - self.empty_g) / WATER_G_PER_ML)

    def fill_pct(self, weight_g: float) -> float:
        return self.water_ml(weight_g) / self.capacity_ml * 100.0 if self.capacity_ml > 0 else 0.0

    def free_ml(self, weight_g: float) -> float:
        return max(0.0, self.capacity_ml - self.water_ml(weight_g))

    def removed(self, weight_g: float) -> bool:
        """ยกบีกเกอร์ออกจากจาน (น้ำหนักต่ำกว่าครึ่งของบีกเกอร์เปล่า)"""
        return weight_g < max(EMPTY_PAN_G, self.empty_g * REMOVED_FRACTION)


def level(fill_pct: float, warn_pct: float, alarm_pct: float) -> str:
    if fill_pct >= alarm_pct:
        return "alarm"
    if fill_pct >= warn_pct:
        return "warn"
    return "ok"


@dataclass
class Prediction:
    now_ml: float
    added_ml: float
    end_ml: float
    end_pct: float
    level: str              # ระดับเมื่อจบ rate นี้ (ok / warn / alarm)


def predict(beaker: Beaker, weight_g: float, rate_ml_h: float, minutes: float, allowance_min: float,
            warn_pct: float, alarm_pct: float) -> Prediction:
    """น้ำเมื่อจบ rate นี้ = น้ำตอนนี้ + rate × (เวลาทดสอบ + เวลาเผื่อ ช่วงก่อนวัด/คนมาหยุดปั๊ม)"""
    now = beaker.water_ml(weight_g)
    added = max(0.0, rate_ml_h) * max(0.0, minutes + allowance_min) / 60.0
    end = now + added
    pct = end / beaker.capacity_ml * 100.0 if beaker.capacity_ml > 0 else 0.0
    return Prediction(now, added, end, pct, level(pct, warn_pct, alarm_pct))


def minutes_to(beaker: Beaker, weight_g: float, rate_ml_h: float, target_pct: float) -> float | None:
    """เวลาที่เหลือ (นาที) ก่อนน้ำถึง target_pct ที่ rate นี้ — None = rate ≤ 0"""
    if rate_ml_h <= 0:
        return None
    left = beaker.capacity_ml * target_pct / 100.0 - beaker.water_ml(weight_g)
    return max(0.0, left / rate_ml_h * 60.0)


class PumpRunningDetector:
    """ปั๊มยังเดินไหม จากน้ำหนักล่าสุด (หลังจบการทดสอบ — ใช้เตือน "หยุดปั๊มได้แล้ว")

    เดิน  = น้ำหนักเพิ่มขึ้นเกิน rise_g ภายใน window_s ล่าสุด
    หยุด  = ช่วง window_s ล่าสุดเพิ่มน้อยกว่า rise_g (การระเหยลดน้ำหนัก ไม่ถือว่าเดิน)
    ยังไม่รู้ = ข้อมูลยังไม่ครบ window_s
    """

    def __init__(self, window_s: float = 20.0, rise_g: float = 0.02):
        self.window_s = window_s
        self.rise_g = rise_g
        self._points: deque[tuple[float, float]] = deque()

    def reset(self) -> None:
        self._points.clear()

    def add(self, t: float, weight_g: float) -> None:
        self._points.append((t, weight_g))
        while self._points and t - self._points[0][0] > self.window_s * 1.5:
            self._points.popleft()

    def running(self) -> bool | None:
        if len(self._points) < 3:
            return None
        t_last, w_last = self._points[-1]
        old = [(t, w) for t, w in self._points if t_last - t >= self.window_s]
        if not old:
            return None
        return w_last - old[-1][1] > self.rise_g

    def rate_ml_h(self) -> float | None:
        """อัตราการเพิ่มของน้ำ (ml/h) ในหน้าต่างล่าสุด — ใช้ประมาณเวลาที่เหลือก่อนล้น"""
        if len(self._points) < 3:
            return None
        (t0, w0), (t1, w1) = self._points[0], self._points[-1]
        if t1 - t0 < 5.0:
            return None
        return (w1 - w0) / WATER_G_PER_ML / (t1 - t0) * 3600.0
