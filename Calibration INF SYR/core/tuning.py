"""ปรับขนาดหน้าต่างจับรอบปั๊ม (สัดส่วน หน้าต่าง/คาบ) จากข้อมูลดิบที่เก็บไว้ — "calibration" ของตัวจับ peak

หลักการ: เล่นข้อมูลดิบ (raw.csv) ของการทดสอบที่เก็บไว้ ผ่าน FlowEngine ตัวจริงซ้ำหลายรอบ
แต่ละรอบใช้สัดส่วนต่างกัน (เช่น 0.15 … 0.45 x คาบ) แล้วให้คะแนนว่าจับรอบได้ "สม่ำเสมอ" แค่ไหน

    คะแนน = CV(เวลาต่อรอบ) + CV(flow ต่อรอบ) + |เวลาต่อรอบเฉลี่ย / คาบ − 1|        (ยิ่งน้อยยิ่งดี)

    CV(เวลาต่อรอบ)   ปั๊มเดิน rate คงที่ ทุกรอบควรยาวเท่ากัน — จับ peak ปลอม/พลาด จะทำให้แกว่ง
    CV(flow ต่อรอบ)  ผลรายรอบควรใกล้กัน
    เทอมคาบ         เวลาต่อรอบต้องเท่ากับคาบจริง — กันการจับ "ครึ่งรอบ" ที่สม่ำเสมอ
                   (ข้อมูลจริง TE-171: หน้าต่าง < 0.3 x คาบ จับได้ครึ่งรอบ เพราะปั๊มมี 2 จังหวะต่อรอบ)

คาบอ้างอิง (ไม่ขึ้นกับสัดส่วนที่กำลังลอง): โปรไฟล์ปั๊ม ตรวจไขว้กับ autocorrelation ของข้อมูลทั้งไฟล์
    ถ้า autocorrelation ได้ ~2 เท่าของโปรไฟล์ = โปรไฟล์น่าจะเรียนรู้ครึ่งรอบมา ใช้ autocorrelation แทน
    ไม่มีโปรไฟล์: autocorrelation → ค่ากลางของรอบที่เก็บไว้
ผลเก็บต่อ ยี่ห้อ + รุ่น + ชุดสาย + rate (ตาราง window_tuning) และใช้ตอนเริ่มการทดสอบครั้งต่อไป
ไม่มี Qt — เรียกได้จาก thread ใดก็ได้ (ส่ง should_stop เพื่อยกเลิกกลางคัน)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from config.settings import EngineSettings
from core.models import EndMode, Sample, SessionConfig, StartMode

FRACTIONS = (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45)
MIN_INTERVALS = 4           # น้อยกว่านี้ให้คะแนนไม่ได้
MIN_GAIN = 0.10             # เปลี่ยนจากค่าปัจจุบันเมื่อคะแนนดีขึ้นอย่างน้อย 10 % (กันการไล่ตาม noise ของข้อมูลชุดเดียว)


@dataclass
class Dataset:
    """ข้อมูลดิบ 1 การทดสอบ + คาบอ้างอิง"""
    samples: list[tuple[float, float]]
    period_s: float
    ref: str = ""


@dataclass
class TrialResult:
    fraction: float
    regression_window: int
    half_window: int
    intervals: int
    cv_duration: float
    cv_flow: float
    period_ratio: float         # เวลาต่อรอบเฉลี่ย / คาบอ้างอิง
    score: float


@dataclass
class TuningResult:
    rate: float
    sessions: int
    period_s: float
    trials: list[TrialResult] = field(default_factory=list)     # คะแนนเฉลี่ยทุก dataset ต่อสัดส่วน
    best: TrialResult | None = None
    current_fraction: float = 0.4
    current_score: float | None = None

    def recommended_fraction(self) -> float | None:
        """สัดส่วนที่ควรใช้: ค่าที่ดีที่สุด ถ้าดีกว่าค่าปัจจุบันชัดเจน ไม่งั้นคงค่าปัจจุบัน (None = ไม่มีค่าไหนจับรอบได้)"""
        if self.best is None:
            return None
        current = self.current_score
        if current is None or not math.isfinite(current) or self.best.score <= current * (1.0 - MIN_GAIN):
            return self.best.fraction
        return self.current_fraction


def window_points(period_s: float, sample_period_s: float, fraction: float) -> tuple[int, int]:
    """(หน้าต่าง regression, n_bar) — ขั้นต่ำเหมือน engine (10 และ 5 จุด)"""
    points = round(period_s * fraction / sample_period_s) if sample_period_s > 0 else 0
    return max(10, points), max(5, points)


def sample_period(samples: list[tuple[float, float]]) -> float:
    t = np.asarray([s[0] for s in samples])
    return float(np.median(np.diff(t))) if len(t) > 1 else 0.0


def evaluate(dataset: Dataset, rate: float, fraction: float, chains: int = 2,
             should_stop: Callable[[], bool] | None = None) -> TrialResult:
    """เล่นข้อมูล 1 ชุดด้วยสัดส่วนนี้ แล้วให้คะแนน"""
    from core.engine import FlowEngine          # import ตรงนี้ กัน import วน

    dt = sample_period(dataset.samples)
    regression, half = window_points(dataset.period_s, dt, fraction)
    span = dataset.samples[-1][0] - dataset.samples[0][0] if dataset.samples else 0.0
    config = SessionConfig(target_flow=rate, strategy="pump_cycle", end_mode=EndMode.TIME,
                           start_mode=StartMode.IMMEDIATE, duration_min=span / 60.0 + 60.0)
    settings = EngineSettings(regression_window=regression, cycle_half_window=half, window_mode="manual",
                              cycle_chains=chains, ml_per_g=1.0)
    engine = FlowEngine(config, settings)
    for index, (t, w) in enumerate(dataset.samples):
        if should_stop is not None and index % 2000 == 0 and should_stop():
            raise InterruptedError
        engine.process(Sample(t, w))
    durations = np.array([iv.duration_s for iv in engine.intervals])
    flows = np.array([iv.flow for iv in engine.intervals])
    if len(durations) < MIN_INTERVALS or durations.mean() <= 0 or flows.mean() <= 0:
        return TrialResult(fraction, regression, half, len(durations), math.inf, math.inf, 0.0, math.inf)
    cv_duration = float(durations.std(ddof=1) / durations.mean())
    cv_flow = float(flows.std(ddof=1) / flows.mean())
    ratio = float(durations.mean() / dataset.period_s)
    score = cv_duration + cv_flow + abs(ratio - 1.0)
    return TrialResult(fraction, regression, half, len(durations), cv_duration, cv_flow, ratio, score)


def tune(datasets: list[Dataset], rate: float, current_fraction: float = 0.4, chains: int = 2,
         fractions: tuple[float, ...] = FRACTIONS, should_stop: Callable[[], bool] | None = None,
         progress: Callable[[float], None] | None = None) -> TuningResult:
    """ลองทุกสัดส่วนกับทุกชุดข้อมูล คะแนนรวม = ค่าเฉลี่ยของทุกชุด (ชุดไหนจับไม่ได้ = ไม่ผ่านสัดส่วนนั้น)"""
    candidates = sorted(set(fractions) | {round(current_fraction, 2)})
    result = TuningResult(rate=rate, sessions=len(datasets), current_fraction=current_fraction,
                          period_s=float(np.median([d.period_s for d in datasets])) if datasets else 0.0)
    total, done = len(candidates) * len(datasets), 0
    for fraction in candidates:
        trials = []
        for dataset in datasets:
            trials.append(evaluate(dataset, rate, fraction, chains, should_stop))
            done += 1
            if progress is not None:
                progress(done / total)
        score = float(np.mean([t.score for t in trials])) if trials else math.inf
        first = trials[0] if trials else TrialResult(fraction, 0, 0, 0, math.inf, math.inf, 0.0, math.inf)
        combined = TrialResult(
            fraction, first.regression_window, first.half_window, sum(t.intervals for t in trials),
            float(np.mean([t.cv_duration for t in trials])), float(np.mean([t.cv_flow for t in trials])),
            float(np.mean([t.period_ratio for t in trials])), score)
        result.trials.append(combined)
        if math.isclose(fraction, current_fraction, abs_tol=0.005):
            result.current_score = score
    finite = [t for t in result.trials if math.isfinite(t.score)]
    if finite:
        result.best = min(finite, key=lambda t: t.score)
    return result


def reference_period(samples: list[tuple[float, float]], profile_period: float | None,
                     interval_durations: list[float]) -> float | None:
    """คาบอ้างอิงที่ไม่ขึ้นกับสัดส่วนที่กำลังลอง"""
    from core.prerun import PeriodEstimator
    estimate = None
    if len(samples) > 20:
        t, w = np.asarray([s[0] for s in samples]), np.asarray([s[1] for s in samples])
        estimate = PeriodEstimator().estimate(t, w)
    if profile_period and profile_period > 0:
        if estimate and 1.8 <= estimate / profile_period <= 2.2:
            return estimate
        return profile_period
    if estimate:
        return estimate
    return float(np.median(interval_durations)) if interval_durations else None
