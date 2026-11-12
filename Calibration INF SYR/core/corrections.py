"""ค่าแก้ของการวัดแบบชั่งน้ำหนัก และ self-check

ค่าแก้แต่ละตัวเป็นฟังก์ชัน/คลาสแยกชิ้น — วันหน้าเพิ่มแรงลอยตัวของอากาศ หรือความไม่แน่นอน
ของตราชั่ง ก็เพิ่มที่ไฟล์นี้ แล้วให้ SessionController ใส่ลงค่าตั้งของการทดสอบ

flow ที่แก้แล้ว = (อัตราน้ำหนักที่วัดได้ − อัตราพื้นฐาน) / ความหนาแน่น
    อัตราพื้นฐาน (baseline) มาจาก self-check: วางบีกเกอร์ในสภาพเดียวกับตอนทดสอบ ปั๊มหยุด
    แล้ววัดว่าน้ำหนักเปลี่ยนเองเท่าไรต่อชั่วโมง (การระเหย + การไหลของค่าตราชั่ง รวมกัน)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from config.settings import SelfCheckSettings
from core.models import EngineResult, Sample


def water_density(temperature_c: float) -> float:
    """ความหนาแน่นของน้ำบริสุทธิ์ (g/ml) ตามอุณหภูมิ — สูตร Tanaka et al. (2001) ใช้ได้ 0–40 °C"""
    t = temperature_c
    a1, a2, a3, a4, a5 = -3.983035, 301.797, 522528.9, 69.34881, 999.974950
    return a5 * (1.0 - (t + a1) ** 2 * (t + a2) / (a3 * (t + a4))) / 1000.0


def choose_density(temperature_c: float | None, fallback: float) -> tuple[float, str]:
    """(ความหนาแน่น, ที่มา) — ใช้อุณหภูมิจากฟอร์มถ้ากรอกและอยู่ในช่วงที่สูตรใช้ได้"""
    if temperature_c is not None and 0.0 <= temperature_c <= 40.0:
        return water_density(temperature_c), "temperature"
    return fallback, "settings"


# ------------------------------------------------------------------ self-check
@dataclass
class SelfCheckResult:
    measured_at: str = ""
    duration_s: float = 0.0
    sample_count: int = 0
    rate_g_per_h: float = 0.0           # อัตราพื้นฐาน (ลบ = น้ำหนักหาย เช่นการระเหย)
    se_g_per_h: float = 0.0             # ความคลาดเคลื่อนมาตรฐานของอัตรา
    noise_sd_g: float = 0.0             # การกระจายของค่าตราชั่งรอบเส้นแนวโน้ม
    halves_diff_g_per_h: float = 0.0    # |อัตราครึ่งแรก − ครึ่งหลัง| (เฉลี่ยจากช่วงย่อย)
    halves_z: float = 0.0               # ความต่างข้างบน ÷ ความไม่แน่นอนของความต่าง (ยิ่งมาก ยิ่งไม่นิ่งจริง)
    passed: bool = False
    reasons: list = field(default_factory=list)     # เหตุผลที่ไม่ผ่าน (ข้อความอังกฤษ ผ่าน tr ตอนแสดง)

    @property
    def date(self) -> str:
        return self.measured_at[:10]


def _rate(t: np.ndarray, w: np.ndarray) -> tuple[float, float, float]:
    """(ความชัน g/s, SE ของความชัน, SD ของส่วนเหลือ) จากเส้นตรง least-squares"""
    n = len(t)
    slope, intercept = np.polyfit(t, w, 1)
    residual = w - (slope * t + intercept)
    sd = float(np.sqrt(np.sum(residual ** 2) / max(1, n - 2)))
    spread = float(np.sum((t - t.mean()) ** 2))
    return float(slope), (sd / math.sqrt(spread) if spread > 0 else 0.0), sd


def _block_rates(t: np.ndarray, w: np.ndarray, count: int, min_points: int = 6) -> np.ndarray:
    """แบ่งเวลาเป็น count ช่วงเท่ากัน คืนอัตรา (g/s) ของแต่ละช่วง — ลดจำนวนช่วงถ้าจุดต่อช่วงน้อยเกิน"""
    count = max(4, int(count))
    while count >= 4:
        edges = np.linspace(t[0], t[-1], count + 1)
        index = np.searchsorted(t, edges)
        parts = [(index[i], index[i + 1]) for i in range(count)]
        if all(b - a >= min_points for a, b in parts):
            return np.array([np.polyfit(t[a:b], w[a:b], 1)[0] for a, b in parts])
        count -= 2
    return np.array([])


def analyse_baseline(samples: list[tuple[float, float]], criteria: SelfCheckSettings,
                     skip_s: float = 2.0) -> SelfCheckResult:
    """วิเคราะห์ข้อมูล self-check (ปั๊มหยุด) -> อัตราพื้นฐาน + ผ่าน/ไม่ผ่าน"""
    result = SelfCheckResult(measured_at=datetime.now().isoformat(timespec="seconds"))
    data = np.asarray([(t, w) for t, w in samples if t >= skip_s], dtype=float)
    if len(data) < 20:
        result.reasons.append("Not enough data")
        return result
    t, w = data[:, 0], data[:, 1]
    result.duration_s = float(t[-1] - t[0])
    result.sample_count = len(t)

    slope, se, sd = _rate(t, w)
    result.rate_g_per_h, result.noise_sd_g = slope * 3600.0, sd

    # อัตรารายช่วงย่อย (block) — ใช้วัด "ความไม่แน่นอนจริง" ของอัตรา
    # ค่าตราชั่งจริงไหลขึ้นลงช้าๆ ต่อเนื่อง (จุดติดกันสัมพันธ์กัน ~0.999) SE จากสูตรเส้นตรงปกติจึงเล็กเกินจริงมาก
    # การแบ่งเป็นช่วงแล้วดูการกระจายของอัตราแต่ละช่วง จับการไหลช้าๆ นี้ได้ตรงกว่า
    blocks = _block_rates(t, w, criteria.blocks)
    if len(blocks) >= 4:
        half = len(blocks) // 2
        first, second = blocks[:half], blocks[half:]
        result.halves_diff_g_per_h = abs(float(np.mean(first) - np.mean(second))) * 3600.0
        se_diff = math.sqrt(np.var(first, ddof=1) / len(first) + np.var(second, ddof=1) / len(second)) * 3600.0
        result.halves_z = result.halves_diff_g_per_h / se_diff if se_diff > 0 else (0.0 if result.halves_diff_g_per_h == 0 else math.inf)
        result.se_g_per_h = max(se * 3600.0, float(np.std(blocks, ddof=1)) / math.sqrt(len(blocks)) * 3600.0)
    else:                                       # ข้อมูลน้อยเกินจะแบ่งช่วง: ใช้แบบเดิม
        middle = len(t) // 2
        result.halves_diff_g_per_h = abs(_rate(t[:middle], w[:middle])[0] - _rate(t[middle:], w[middle:])[0]) * 3600.0
        result.halves_z = math.inf
        result.se_g_per_h = se * 3600.0

    if samples[-1][0] - samples[0][0] < criteria.duration_min * 60.0 * 0.98:
        result.reasons.append("Stopped before the set duration")
    # ไม่นิ่ง = ครึ่งแรก/หลังต่างกันเกินค่าที่ยอมรับเสมอ และ เกินกว่าที่ noise ของตราชั่งจะอธิบายได้ (z)
    if (result.halves_diff_g_per_h * 1000.0 > criteria.max_halves_diff_mg_h
            and result.halves_z > criteria.max_halves_z):
        result.reasons.append("Rate changed between the first and second half (not settled)")
    if abs(result.rate_g_per_h) * 1000.0 > criteria.max_abs_rate_mg_h:
        result.reasons.append("Rate is too large to be evaporation or drift")
    result.passed = not result.reasons
    return result


class BaselineEngine:
    """engine ของ self-check: แค่เก็บข้อมูลตามเวลาที่ตั้ง (ใช้ร่วมกับ AcquisitionWorker ได้)"""

    def __init__(self, criteria: SelfCheckSettings):
        self.criteria = criteria
        self.duration_s = criteria.duration_min * 60.0
        self.samples: list[tuple[float, float]] = []
        self._t0: float | None = None

    def request_start(self) -> None:    # ให้มี interface เดียวกับ FlowEngine
        pass

    def process(self, sample: Sample) -> EngineResult:
        if self._t0 is None:
            self._t0 = sample.t
        t = sample.t - self._t0
        self.samples.append((t, sample.weight))
        progress = min(1.0, t / self.duration_s) if self.duration_s > 0 else 1.0
        return EngineResult(t=t, weight=sample.weight, progress=progress, finished=t >= self.duration_s)

    def result(self) -> SelfCheckResult:
        return analyse_baseline(self.samples, self.criteria)
