"""โปรไฟล์ปั๊ม: สิ่งที่โปรแกรม "จำ" เกี่ยวกับปั๊มแต่ละ ยี่ห้อ + รุ่น + ชนิดเครื่อง + ชุดสาย/syringe

สมมติฐาน: ปั๊มแบบ finger ส่งของเหลวต่อ 1 รอบเกือบคงที่ (ปริมาตรต่อรอบ, stroke volume)
    ปริมาตรต่อรอบ (ml) = flow (ml/h) x คาบรอบปั๊ม (s) / 3600
ถ้าจริง รู้ค่าเดียวก็คำนวณคาบรอบปั๊มได้ทุก rate:
    คาบ (s) = ปริมาตรต่อรอบ x 3600 / rate
แล้วตั้งหน้าต่างคำนวณ = คาบ x สัดส่วน ได้ทันทีโดยไม่ต้องวัดก่อนเริ่ม

ทุกการทดสอบแบบจับรอบปั๊มที่เก็บผล จะเพิ่ม "ข้อสังเกต" 1 รายการ (rate, คาบที่วัดได้)
ค่าที่ต่างจากโปรไฟล์เดิมมากจะไม่ถูกรวม เพื่อกันผลที่จับรอบพลาดมาทำให้โปรไฟล์เสีย
(สมมติฐานนี้ยังต้องยืนยันกับเครื่องจริงหลาย rate)
"""
from __future__ import annotations

from dataclasses import dataclass

MAX_DEVIATION = 0.25    # ข้อสังเกตที่ต่างจากโปรไฟล์เกิน 25 % จะไม่ถูกรวม
# หมายเหตุจากข้อมูลจริง TE-171 (2026-11-12): หน้าต่างที่เล็กกว่า ~0.3 x คาบ จับได้ "ครึ่งรอบ" (ปั๊มมี 2 จังหวะต่อรอบ)
# และใหญ่กว่า 0.5 x คาบ ข้ามรอบ — ช่วงที่ใช้ได้แคบ ค่าเริ่มต้นของรุ่นจึงควรใกล้ค่าจริง (ไม่มีค่ากลางที่ปลอดภัยทุกรุ่น)


def _norm(text) -> str:
    return " ".join(str(text or "").lower().split())


def profile_key(brand: str, model: str, iv_set: str) -> tuple[str, str, str]:
    """กุญแจ ยี่ห้อ + รุ่น + ชุดสาย (ไม่สนตัวพิมพ์เล็กใหญ่และช่องว่าง) — ใช้กับรายการตรวจเครื่องของรุ่น"""
    return _norm(brand), _norm(model), _norm(iv_set)


def pump_key(brand: str, model: str, iv_set: str, pump_type: str = "infusion") -> tuple[str, str, str, str]:
    """กุญแจของสิ่งที่โปรแกรมเรียนรู้ (โปรไฟล์, หน้าต่างที่ปรับแล้ว, เกณฑ์ช่วงก่อนวัด):
    (ยี่ห้อ, รุ่น, ชนิดเครื่อง infusion|syringe, ชุดสาย/syringe) — รุ่นเดียวกันแต่คนละชนิด/คนละชุดสาย = คนละรายการ"""
    return _norm(brand), _norm(model), _norm(pump_type) or "infusion", _norm(iv_set)


def stroke_volume_ml(flow_ml_h: float, period_s: float) -> float:
    return flow_ml_h * period_s / 3600.0


@dataclass
class PumpProfile:
    brand: str = ""
    model: str = ""
    pump_type: str = "infusion"
    iv_set: str = ""
    stroke_volume_ml: float = 0.0
    runs: int = 0
    updated_at: str = ""
    calibrated_at: str = ""     # Calibration รอบปั๊มครั้งล่าสุด — ข้อมูลก่อนเวลานี้ไม่ถูกใช้เรียนรู้ (แต่ยังเก็บไว้สอบย้อนหลัง)

    def period_s(self, rate_ml_h: float) -> float:
        """คาบรอบปั๊มที่คาดไว้ ณ rate ที่กำหนด"""
        return self.stroke_volume_ml * 3600.0 / rate_ml_h if rate_ml_h > 0 else 0.0

    def window_points(self, rate_ml_h: float, sample_period_s: float, fraction: float) -> int:
        """ขนาดหน้าต่าง (จำนวนจุด) สำหรับ rate นี้"""
        if sample_period_s <= 0:
            return 0
        return round(self.period_s(rate_ml_h) * fraction / sample_period_s)

    @property
    def provisional(self) -> bool:
        """ค่าเริ่มต้นที่ผู้ใช้กำหนดให้รุ่นนี้ "ใช้แทนไปก่อน" (ยังไม่เคยวัดจริง) — การวัดครั้งแรกจะแทนที่"""
        return self.runs == 0 and self.stroke_volume_ml > 0

    def accepts(self, observed_ml: float) -> bool:
        """ข้อสังเกตใหม่สอดคล้องกับโปรไฟล์เดิมไหม"""
        if self.runs == 0 or self.stroke_volume_ml <= 0:
            return observed_ml > 0
        return abs(observed_ml - self.stroke_volume_ml) <= MAX_DEVIATION * self.stroke_volume_ml

    def merge(self, observed_ml: float) -> None:
        """รวมข้อสังเกตใหม่แบบค่าเฉลี่ยสะสม"""
        self.stroke_volume_ml = (self.stroke_volume_ml * self.runs + observed_ml) / (self.runs + 1)
        self.runs += 1
