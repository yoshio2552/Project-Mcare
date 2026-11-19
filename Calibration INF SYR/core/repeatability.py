"""ความซ้ำของการวัด (2SD) ต่อ ยี่ห้อ+รุ่น · ชนิดเครื่อง · ชุดสาย · rate — ใช้ในงบความไม่แน่นอน (ไม่มี Qt)

ที่มาของค่า (ผู้ใช้ 2026-11-19 — ไม่คิดจากผลเก่าอัตโนมัติ):
    1) กรอกเอง — ค่า 2SD จากงานวิจัยของผู้ใช้ เป็น % ของ rate หรือ ± ml/h ที่ rate นั้น
    2) สอบเทียบความซ้ำ — โหมดพิเศษ วัด rate เดียวกัน N ครั้ง (ค่าตั้งต้น 3) ด้วยวิธีจับรอบปั๊มหรือแบ่งช่วงเวลา
       ผลแต่ละครั้ง = ค่าที่วัดได้ (ปริมาตรรวม ÷ เวลารวม) · 2SD = 2 × SD ตัวอย่าง (n − 1) ของผลทั้ง N ครั้ง
แต่ละครั้งที่กรอก/สอบเทียบ = 1 "ชุด" — สอบเทียบซ้ำไม่ลบชุดเดิม · ค่าที่ใช้ = ค่าเฉลี่ยของ 2SD ทุกชุดที่ยังใช้อยู่
ลบชุดได้ (ไม่หายจากฐานข้อมูล — ซ่อนพร้อมเวลาที่ลบ สอบย้อนได้) · ผลที่คิดงบไปแล้วเก็บภาพรวม ณ ตอนนั้นไว้ในผลเอง

ในงบความไม่แน่นอน: u = 2SD ÷ 2 (ml/h) แบบ Type B (ค่าที่ประเมินไว้ก่อน — GUM 4.3.1) ν = ∞
ไม่มีค่าของรุ่น/ชุดสาย/rate นั้น -> ใช้ค่าตั้งต้นในหน้าตั้งค่า (ค่าเริ่มต้น 0)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, stdev

UNITS = ("%", "ml/h")


@dataclass
class Study:
    """1 ชุด (สอบเทียบ N ครั้ง หรือกรอกเอง)"""
    id: int = 0
    kind: str = "manual"            # manual | measured
    rate: float = 0.0
    sd2_pct: float = 0.0            # 2SD เป็น % ของ rate
    sd2_ml_h: float = 0.0           # 2SD เป็น ml/h ที่ rate นั้น
    input_value: float = 0.0        # ค่าที่ผู้ใช้กรอก (manual) ตามหน่วยที่กรอก
    input_unit: str = "%"
    runs: list = field(default_factory=list)    # [{ref, mean_flow, error_pct, started_at}] (measured)
    strategy: str = ""
    duration_min: float = 0.0
    job_id: str = ""
    note: str = ""
    created_at: str = ""


def from_input(value: float, unit: str, rate: float) -> tuple[float, float]:
    """ค่าที่กรอก -> (2SD %, 2SD ml/h)"""
    if rate <= 0:
        raise ValueError("rate must be greater than 0")
    if value < 0:
        raise ValueError("2SD cannot be negative")
    if unit == "ml/h":
        return value / rate * 100.0, value
    return value, value / 100.0 * rate


def from_runs(flows: list[float], rate: float) -> tuple[float, float]:
    """ผลการวัดซ้ำ (ml/h) -> (2SD %, 2SD ml/h) — SD ตัวอย่าง n − 1 · เป็น % ของ rate ที่ตั้ง (เหมือน 2SD ที่อื่นในโปรแกรม)"""
    if len(flows) < 2:
        raise ValueError("at least 2 runs are needed")
    sd2 = 2.0 * stdev(flows)
    return sd2 / rate * 100.0, sd2


def combined(studies: list[Study], rate: float) -> tuple[float, float] | None:
    """ค่าที่ใช้ของรายการ: ค่าเฉลี่ยของ 2SD ทุกชุด (ผู้ใช้ 2026-11-19) -> (2SD %, 2SD ml/h ที่ rate นี้) · ไม่มีชุด = None"""
    if not studies:
        return None
    pct = mean(s.sd2_pct for s in studies)
    return pct, pct / 100.0 * rate
