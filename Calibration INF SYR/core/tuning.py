"""ปรับขนาดหน้าต่างจับรอบปั๊มจากข้อมูลดิบที่เก็บไว้ — "calibration" ของตัวจับ peak ราย rate

มี 2 หน้าต่าง ปรับแยกกัน (แต่ละ ยี่ห้อ + รุ่น + ชนิด + ชุดสาย + rate มีค่าของตัวเอง):
    N regression  = คาบ x r / ช่วงเวลาต่อจุด     หน้าต่างลากเส้นตรงหา flow ขณะนั้น (slope)
    n_bar (peak)  = คาบ x h / ช่วงเวลาต่อจุด     จุดซ้าย/ขวาที่ใช้ตัดสินว่าเป็น peak/valley
เก็บเป็น "สัดส่วนของคาบ" (r, h) เพราะใช้ได้ทั้งตราชั่ง 5 Hz และ 10 Hz — จำนวนจุดจริงบันทึกไว้ด้วย

หลักการ: เล่นข้อมูลดิบ (raw.csv) ของการทดสอบที่เก็บไว้ ผ่าน FlowEngine ตัวจริงซ้ำหลายรอบ แล้วให้คะแนน

    คะแนน = CV(เวลาต่อรอบ) + CV(flow ต่อรอบ) + |เวลาต่อรอบเฉลี่ย / คาบ − 1|        (ยิ่งน้อยยิ่งดี)

    CV(เวลาต่อรอบ)   ปั๊มเดิน rate คงที่ ทุกรอบควรยาวเท่ากัน — จับ peak ปลอม/พลาด จะทำให้แกว่ง
    CV(flow ต่อรอบ)  ผลรายรอบควรใกล้กัน
    เทอมคาบ         เวลาต่อรอบต้องเท่ากับคาบจริง — กันการจับ "ครึ่งรอบ" ที่สม่ำเสมอ
                   (ข้อมูลจริง TE-171: หน้าต่าง < 0.3 x คาบ จับได้ครึ่งรอบ เพราะปั๊มมี 2 จังหวะต่อรอบ)

การค้นหา (ทีละแกน — ประหยัดเวลากว่าลองทุกคู่ 7 x 7):
    1) r = h ทุกค่าใน FRACTIONS   2) คง r ที่ดีสุด ลอง h ทุกค่า   3) คง h ที่ดีสุด ลอง r ทุกค่า

คาบอ้างอิง (ไม่ขึ้นกับค่าที่กำลังลอง): โปรไฟล์ปั๊ม ตรวจไขว้กับ autocorrelation ของข้อมูลทั้งไฟล์
    ถ้า autocorrelation ได้ ~2 เท่าของโปรไฟล์ = โปรไฟล์น่าจะเรียนรู้ครึ่งรอบมา ใช้ autocorrelation แทน
    ไม่มีโปรไฟล์: autocorrelation → ค่ากลางของรอบที่เก็บไว้
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
    regression_fraction: float      # r
    half_fraction: float            # h
    regression_window: int          # จุด (ของ dataset แรก)
    half_window: int
    intervals: int
    cv_duration: float
    cv_flow: float
    period_ratio: float             # เวลาต่อรอบเฉลี่ย / คาบอ้างอิง
    score: float


@dataclass
class TuningResult:
    rate: float
    sessions: int
    period_s: float
    sample_period_s: float = 0.0
    trials: list[TrialResult] = field(default_factory=list)     # คะแนนเฉลี่ยทุก dataset ต่อคู่ (r, h)
    best: TrialResult | None = None
    current: tuple[float, float] = (0.4, 0.4)
    current_score: float | None = None

    def recommended(self) -> tuple[float, float] | None:
        """(r, h) ที่ควรใช้: คู่ที่ดีที่สุด ถ้าดีกว่าค่าปัจจุบันชัดเจน ไม่งั้นคงค่าปัจจุบัน (None = ไม่มีคู่ไหนจับรอบได้)"""
        if self.best is None:
            return None
        current = self.current_score
        if current is None or not math.isfinite(current) or self.best.score <= current * (1.0 - MIN_GAIN):
            return self.best.regression_fraction, self.best.half_fraction
        return self.current

    def points(self, fractions: tuple[float, float]) -> tuple[int, int]:
        return window_points(self.period_s, self.sample_period_s, *fractions)


def window_points(period_s: float, sample_period_s: float, regression_fraction: float,
                  half_fraction: float | None = None) -> tuple[int, int]:
    """(หน้าต่าง regression, n_bar) เป็นจำนวนจุด — ขั้นต่ำเหมือน engine (10 และ 5 จุด)"""
    if half_fraction is None:
        half_fraction = regression_fraction
    if sample_period_s <= 0:
        return 10, 5
    return (max(10, round(period_s * regression_fraction / sample_period_s)),
            max(5, round(period_s * half_fraction / sample_period_s)))


def sample_period(samples: list[tuple[float, float]]) -> float:
    t = np.asarray([s[0] for s in samples])
    return float(np.median(np.diff(t))) if len(t) > 1 else 0.0


def evaluate(dataset: Dataset, rate: float, regression_fraction: float, half_fraction: float | None = None,
             chains: int = 2, should_stop: Callable[[], bool] | None = None) -> TrialResult:
    """เล่นข้อมูล 1 ชุดด้วยคู่ (r, h) นี้ แล้วให้คะแนน"""
    from core.engine import FlowEngine          # import ตรงนี้ กัน import วน

    if half_fraction is None:
        half_fraction = regression_fraction
    dt = sample_period(dataset.samples)
    regression, half = window_points(dataset.period_s, dt, regression_fraction, half_fraction)
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
    failed = TrialResult(regression_fraction, half_fraction, regression, half, len(durations),
                         math.inf, math.inf, 0.0, math.inf)
    if len(durations) < MIN_INTERVALS or durations.mean() <= 0 or flows.mean() <= 0:
        return failed
    cv_duration = float(durations.std(ddof=1) / durations.mean())
    cv_flow = float(flows.std(ddof=1) / flows.mean())
    ratio = float(durations.mean() / dataset.period_s)
    score = cv_duration + cv_flow + abs(ratio - 1.0)
    return TrialResult(regression_fraction, half_fraction, regression, half, len(durations),
                       cv_duration, cv_flow, ratio, score)


def tune(datasets: list[Dataset], rate: float, current: tuple[float, float] | float = (0.4, 0.4), chains: int = 2,
         fractions: tuple[float, ...] = FRACTIONS, should_stop: Callable[[], bool] | None = None,
         progress: Callable[[float], None] | None = None) -> TuningResult:
    """หา (r, h) ที่ดีที่สุดของ rate นี้ — คะแนนรวม = ค่าเฉลี่ยของทุกชุดข้อมูล (ชุดไหนจับไม่ได้ = คู่นั้นไม่ผ่าน)"""
    if not isinstance(current, tuple):
        current = (float(current), float(current))
    current = (round(current[0], 2), round(current[1], 2))
    result = TuningResult(rate=rate, sessions=len(datasets), current=current,
                          period_s=float(np.median([d.period_s for d in datasets])) if datasets else 0.0,
                          sample_period_s=float(np.median([sample_period(d.samples) for d in datasets]))
                          if datasets else 0.0)
    cache: dict[tuple[float, float], TrialResult] = {}
    planned = (3 * len(fractions) + 1) * max(1, len(datasets))
    done = [0]

    def score(r: float, h: float) -> TrialResult:
        key = (round(r, 2), round(h, 2))
        if key not in cache:
            trials = []
            for dataset in datasets:
                trials.append(evaluate(dataset, rate, key[0], key[1], chains, should_stop))
                done[0] += 1
                if progress is not None:
                    progress(min(1.0, done[0] / planned))
            first = trials[0] if trials else None
            cache[key] = TrialResult(
                key[0], key[1], first.regression_window if first else 0, first.half_window if first else 0,
                sum(t.intervals for t in trials),
                float(np.mean([t.cv_duration for t in trials])) if trials else math.inf,
                float(np.mean([t.cv_flow for t in trials])) if trials else math.inf,
                float(np.mean([t.period_ratio for t in trials])) if trials else 0.0,
                float(np.mean([t.score for t in trials])) if trials else math.inf)
            result.trials.append(cache[key])
        return cache[key]

    def best_of(candidates: list[TrialResult]) -> TrialResult | None:
        finite = [t for t in candidates if math.isfinite(t.score)]
        return min(finite, key=lambda t: t.score) if finite else None

    result.current_score = score(*current).score
    diagonal = best_of([score(f, f) for f in fractions])                 # 1) r = h
    if diagonal is not None:
        r = diagonal.regression_fraction
        half = best_of([score(r, f) for f in fractions])                 # 2) ปรับ n_bar
        h = half.half_fraction if half else r
        best_of([score(f, h) for f in fractions])                         # 3) ปรับ regression
    result.best = best_of(result.trials)
    if progress is not None:
        progress(1.0)
    return result


def reference_period(samples: list[tuple[float, float]], profile_period: float | None,
                     interval_durations: list[float]) -> float | None:
    """คาบอ้างอิงที่ไม่ขึ้นกับค่าที่กำลังลอง"""
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
