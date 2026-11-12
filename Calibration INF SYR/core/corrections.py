"""ค่าแก้ของการวัดแบบชั่งน้ำหนัก และ self-check

ค่าแก้แต่ละตัวเป็นฟังก์ชัน/คลาสแยกชิ้น — วันหน้าเพิ่มงบความไม่แน่นอน ก็เพิ่มที่ไฟล์นี้
แล้วให้ SessionController ใส่ลงค่าตั้งของการทดสอบ

flow สุทธิ = (อัตราน้ำหนักที่วัดได้ − อัตราพื้นฐาน) × Z                       [ml/h]
    Z (ml/g) = 1 / (ρw − ρa) × (1 − ρa / ρb)                                ISO 4787:2021 / ISO 8655-6
        ρw ความหนาแน่นน้ำ จากอุณหภูมิของเหลว (Tanaka et al. 2001, CIPM)
        ρa ความหนาแน่นอากาศ จากอุณหภูมิอากาศ + ความชื้น + ความดัน (OIML R111-1 E.3)
        ρb ความหนาแน่นตุ้มน้ำหนักที่ใช้สอบเทียบตราชั่ง (8.0 g/ml)
    อัตราพื้นฐาน (baseline) มาจาก self-check: วางบีกเกอร์ในสภาพเดียวกับตอนทดสอบ ปั๊มหยุด
    แล้ววัดว่าน้ำหนักเปลี่ยนเองเท่าไรต่อชั่วโมง (การระเหย + การไหลของค่าตราชั่ง รวมกัน)
flow ที่ยังไม่แก้ (เก็บคู่กันไว้สอบย้อนหลัง) = อัตราน้ำหนักที่วัดได้ โดยถือ 1 g = 1 ml
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from config.settings import EngineSettings, SelfCheckSettings
from core.models import EngineResult, JobInfo, Sample

STANDARD = "ISO 4787:2021 Z factor; water density Tanaka et al. (2001); air density OIML R111-1 (E.3)"
# ช่วงที่สูตรความหนาแน่นอากาศของ OIML รับรองความถูกต้อง (นอกช่วงยังคำนวณได้ แต่บันทึกคำเตือน)
AIR_FORMULA_RANGE = {"t": (10.0, 30.0), "p": (900.0, 1100.0), "rh": (0.0, 80.0)}


def water_density(temperature_c: float) -> float:
    """ความหนาแน่นของน้ำบริสุทธิ์ (g/ml) ตามอุณหภูมิ — สูตร Tanaka et al. (2001) ใช้ได้ 0–40 °C"""
    t = temperature_c
    a1, a2, a3, a4, a5 = -3.983035, 301.797, 522528.9, 69.34881, 999.974950
    return a5 * (1.0 - (t + a1) ** 2 * (t + a2) / (a3 * (t + a4))) / 1000.0


def air_density(temperature_c: float, humidity_pct: float, pressure_hpa: float) -> float:
    """ความหนาแน่นของอากาศ (g/ml) — สูตรประมาณของ OIML R111-1:2004 (E.3-1) ที่ ISO 4787 / ISO 8655-6 ใช้

    ρa [kg/m³] = (0.34848 p − 0.009 hr exp(0.061 t)) / (273.15 + t)     p = hPa, hr = %, t = °C
    ความไม่แน่นอนสัมพัทธ์ ~2×10⁻⁴ เมื่อ 900–1100 hPa, 10–30 °C, hr < 80 %
    """
    t, hr, p = temperature_c, humidity_pct, pressure_hpa
    return (0.34848 * p - 0.009 * hr * math.exp(0.061 * t)) / (273.15 + t) / 1000.0


def z_factor(water_g_per_ml: float, air_g_per_ml: float, reference_g_per_ml: float = 8.0) -> float:
    """ปัจจัย Z ของ ISO 4787 (ml/g): ปริมาตร = ค่าที่ตราชั่งอ่านได้ × Z (รวมค่าแก้แรงลอยตัวของอากาศแล้ว)"""
    return 1.0 / (water_g_per_ml - air_g_per_ml) * (1.0 - air_g_per_ml / reference_g_per_ml)


def choose_density(temperature_c: float | None, fallback: float) -> tuple[float, str]:
    """(ความหนาแน่น, ที่มา) — ใช้อุณหภูมิจากฟอร์มถ้ากรอกและอยู่ในช่วงที่สูตรใช้ได้"""
    if temperature_c is not None and 0.0 <= temperature_c <= 40.0:
        return water_density(temperature_c), "temperature"
    return fallback, "settings"


@dataclass
class GravimetricCorrection:
    """ค่าแก้แปลงน้ำหนักเป็นปริมาตรของ 1 การทดสอบ — เก็บทั้ง "ค่าที่ใช้" และ "ที่มา" ไว้สอบย้อนหลัง

    ที่มา (source): form = กรอกในฟอร์ม · settings = ค่าในหน้าตั้งค่า · liquid = ใช้อุณหภูมิของเหลวแทน
    """
    liquid_temp_c: float | None = None
    air_temp_c: float = 20.0
    air_temp_source: str = "settings"
    humidity_pct: float = 50.0
    humidity_source: str = "settings"
    pressure_hpa: float = 1013.25
    pressure_source: str = "settings"
    water_density_g_per_ml: float = 0.9982
    water_density_source: str = "settings"      # temperature | settings
    air_buoyancy: bool = True
    air_density_g_per_ml: float = 0.0           # 0 เมื่อปิดการแก้แรงลอยตัว
    reference_density_g_per_ml: float = 8.0
    ml_per_g: float = 1.0                       # Z
    baseline_g_per_h: float = 0.0               # self-check ที่หัก (0 = ไม่ได้หัก)
    baseline_measured_at: str = ""
    standard: str = STANDARD
    warnings: list = field(default_factory=list)    # ข้อความอังกฤษ ผ่าน tr ตอนแสดง

    def net_flow(self, raw_ml_per_h: float) -> float:
        """flow สุทธิ จาก flow ที่ยังไม่แก้ (ตัวเลข g/h = ml/h เมื่อถือ 1 g = 1 ml)"""
        return (raw_ml_per_h - self.baseline_g_per_h) * self.ml_per_g


def gravimetric_correction(job: JobInfo, settings: EngineSettings,
                           baseline_g_per_h: float = 0.0, baseline_measured_at: str = "") -> GravimetricCorrection:
    """ประกอบค่าแก้ของการทดสอบจากข้อมูลในฟอร์ม + ค่าตั้ง (ค่าที่ไม่ได้กรอกใช้ค่าตั้ง และบันทึกที่มาไว้)"""
    c = GravimetricCorrection(liquid_temp_c=job.temperature_c, air_buoyancy=settings.air_buoyancy,
                              reference_density_g_per_ml=settings.reference_density_g_per_ml,
                              baseline_g_per_h=baseline_g_per_h, baseline_measured_at=baseline_measured_at)
    c.water_density_g_per_ml, c.water_density_source = choose_density(job.temperature_c, settings.density_g_per_ml)
    if job.temperature_c is not None and c.water_density_source == "settings":
        c.warnings.append("Liquid temperature is outside 0–40 °C; the density in Settings was used")
    elif job.temperature_c is None:
        c.warnings.append("No liquid temperature entered; the density in Settings was used")

    if job.air_temp_c is not None:
        c.air_temp_c, c.air_temp_source = job.air_temp_c, "form"
    elif c.water_density_source == "temperature":
        c.air_temp_c, c.air_temp_source = job.temperature_c, "liquid"
    else:
        c.air_temp_c, c.air_temp_source = 20.0, "settings"
    if job.humidity_pct is not None and 0.0 <= job.humidity_pct <= 100.0:
        c.humidity_pct, c.humidity_source = job.humidity_pct, "form"
    else:
        if job.humidity_pct is not None:
            c.warnings.append("Humidity must be 0–100 %RH; the value in Settings was used")
        c.humidity_pct, c.humidity_source = settings.default_humidity_pct, "settings"
    if job.pressure_hpa is not None and 500.0 <= job.pressure_hpa <= 1200.0:
        c.pressure_hpa, c.pressure_source = job.pressure_hpa, "form"
    else:
        if job.pressure_hpa is not None:
            c.warnings.append("Air pressure must be 500–1200 hPa; the value in Settings was used")
        c.pressure_hpa, c.pressure_source = settings.default_pressure_hpa, "settings"

    if c.air_buoyancy:
        c.air_density_g_per_ml = air_density(c.air_temp_c, c.humidity_pct, c.pressure_hpa)
        (t_lo, t_hi), (p_lo, p_hi), (h_lo, h_hi) = (AIR_FORMULA_RANGE[k] for k in ("t", "p", "rh"))
        if not (t_lo <= c.air_temp_c <= t_hi and p_lo <= c.pressure_hpa <= p_hi and h_lo <= c.humidity_pct <= h_hi):
            c.warnings.append("Air conditions are outside the range of the air-density formula (10–30 °C, "
                              "900–1100 hPa, below 80 %RH); the effect on the result is still very small")
        c.ml_per_g = z_factor(c.water_density_g_per_ml, c.air_density_g_per_ml, c.reference_density_g_per_ml)
    else:
        c.ml_per_g = 1.0 / c.water_density_g_per_ml
    return c


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
