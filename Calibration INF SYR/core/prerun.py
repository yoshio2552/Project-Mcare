"""ช่วงก่อนวัด (pre-run): ตัดสินว่า "พร้อมเริ่มวัดจริงหรือยัง" และประเมินคาบรอบปั๊ม

มี 2 โมเดลคณิตศาสตร์:

PeriodEstimator — หาคาบรอบปั๊มจาก autocorrelation
    นำน้ำหนักมาลบเส้นแนวโน้มตรง (เหลือแต่ส่วนที่แกว่งตามรอบปั๊ม) แล้วหา autocorrelation
    คาบ = ระยะเลื่อน (lag) ที่สัญญาณกลับมาซ้อนทับตัวเองได้ดีที่สุดครั้งแรก
    ยอมรับเมื่อ (1) มีข้อมูลยาวอย่างน้อย 3 คาบ (2) ค่าสหสัมพันธ์สูงพอ
    (3) ประเมิน 2 ครั้งติดกันได้ค่าใกล้กัน — ถ้าไม่ผ่านถือว่า "หาคาบไม่ได้" (เช่น syringe pump)

flow_variation — วัดความนิ่งของ flow
    แบ่งข้อมูลล่าสุดเป็นช่วงยาวเท่ากันหลายช่วงติดกัน คิด flow เฉลี่ยของแต่ละช่วง
    ความแกว่ง = (มากสุด - น้อยสุด) / ค่าเฉลี่ย x 100

ความยาว 1 ช่วงเทียบ (block_length) — เกณฑ์มาจากกลุ่ม ชนิดเครื่อง x วิธีจับ (config.settings.PrerunCriteria)
    cycle  = คาบรอบปั๊ม x จำนวนคาบ (คาบจากการวัดก่อนเริ่ม หรือจากโปรไฟล์) — การแกว่งตามรอบหักล้างกันพอดี
    time   = วินาทีที่ตั้ง ยืดจนน้ำหนักต่อช่วงถึง min_block_mg (rate ต่ำ) และปัดเป็นจำนวนเต็มเท่าของคาบถ้าตั้งไว้
รอนานสุด max_wait: ครบแล้วเริ่มวัดเลย และบันทึกว่า "ยังไม่ยืนยันว่า flow นิ่ง" (สอบย้อนหลังได้)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from config.settings import EngineSettings
from core.models import PreRunStatus, SessionConfig, StartMode

MAX_BUFFER_S = 900.0    # เก็บข้อมูล pre-run ล่าสุดอย่างน้อยเท่านี้ (ขยายเองถ้าช่วงเทียบยาวกว่า — เดิมเป็นเพดานตายตัว
                        # ทำให้ rate ต่ำกว่า ~4 ml/h ไม่มีวัน "นิ่ง")


class PeriodEstimator:
    def __init__(self, min_data_s: float = 30.0, check_every_s: float = 5.0,
                 min_periods: float = 3.0, min_correlation: float = 0.5, agreement: float = 0.05):
        self.min_data_s = min_data_s
        self.check_every_s = check_every_s
        self.min_periods = min_periods
        self.min_correlation = min_correlation
        self.agreement = agreement
        self.period: float | None = None        # คาบที่ยืนยันแล้ว (s)
        self._previous: float | None = None
        self._next_check = min_data_s

    def update(self, t: np.ndarray, w: np.ndarray) -> float | None:
        """ป้อนข้อมูลทั้งหมดที่มี (เรียกบ่อยได้ ตัวมันเองจะคำนวณเป็นระยะ)"""
        if self.period is not None or len(t) < 20:
            return self.period
        span = t[-1] - t[0]
        if span < self._next_check:
            return None
        self._next_check = span + self.check_every_s

        estimate = self.estimate(t, w)
        if estimate is not None and self._previous is not None \
                and abs(estimate - self._previous) <= self.agreement * estimate:
            self.period = (estimate + self._previous) / 2.0
        self._previous = estimate
        return self.period

    def estimate(self, t: np.ndarray, w: np.ndarray) -> float | None:
        """ประเมินคาบ 1 ครั้งจากข้อมูลชุดนี้ (None = ยังไม่ชัดพอ)"""
        n = len(t)
        dt = float(np.median(np.diff(t)))
        if n < 20 or dt <= 0:
            return None
        residual = w - np.polyval(np.polyfit(t, w, 1), t)
        residual = residual - residual.mean()
        energy = float(np.dot(residual, residual))
        if energy <= 0:
            return None
        # การแกว่งต้องใหญ่กว่าความละเอียดของตราชั่งชัดเจน ไม่งั้นจะโดนลวดลายจากการปัดเศษหลอก
        # ความละเอียด = ผลต่างอันดับสองที่เล็กที่สุดที่ไม่ใช่ 0 (เดิมใช้ผลต่างอันดับหนึ่ง ซึ่งที่ rate สูงเป็น
        # "flow ต่อจุด" ไม่ใช่ความละเอียด เช่น 200 ml/h ที่ 5 Hz ≈ 11 mg ต่อจุด -> ปฏิเสธการแกว่งจริงทั้งหมด)
        steps = np.abs(np.diff(w, 2))
        steps = steps[steps > 1e-9]
        if len(steps) and residual.std() < 3.0 * float(steps.min()):
            return None

        spectrum = np.fft.rfft(residual, 2 * n)
        acf = np.fft.irfft(spectrum * np.conj(spectrum))[:n] / energy

        max_lag = int(n / self.min_periods)
        below_zero = np.flatnonzero(acf[:max_lag] < 0)
        if len(below_zero) == 0:
            return None
        start = int(below_zero[0])
        if max_lag - start < 3:
            return None
        lag = start + int(np.argmax(acf[start:max_lag]))
        if lag >= max_lag - 1:                       # ยอดยังอยู่ที่ขอบ = ข้อมูลยังไม่ยาวพอ
            return None
        # acf ข้างบนถูกถ่วงให้เล็กลงตาม lag (ดีสำหรับเลือก "ยอดแรก" แต่ทำให้ตำแหน่งยอดเพี้ยนต่ำ)
        # จึงหาตำแหน่งยอดจริงอีกครั้งจากค่าที่ชดเชยแล้ว ในบริเวณรอบๆ ยอดเดิม
        unbiased = acf[:max_lag] * n / (n - np.arange(max_lag))
        low, high = max(1, int(lag * 0.9)), min(max_lag - 1, int(lag * 1.1) + 2)
        lag = low + int(np.argmax(unbiased[low:high]))
        if lag >= max_lag - 1 or unbiased[lag] < self.min_correlation:
            return None

        # ปรับตำแหน่งยอดให้ละเอียดกว่า 1 sample ด้วยพาราโบลา
        left, mid, right = unbiased[lag - 1], unbiased[lag], unbiased[lag + 1]
        curvature = left - 2 * mid + right
        shift = 0.5 * (left - right) / curvature if curvature != 0 else 0.0
        return (lag + shift) * dt


def block_length(mode: str, cycles: int, block_s: float, min_block_mg: float, align: bool,
                 rate_ml_h: float, period_s: float | None) -> float:
    """ความยาว 1 ช่วงเทียบความนิ่ง (วินาที) — ใช้ทั้งตอนวัดจริงและตอนประมาณเวลารอในหน้าสร้างการทดสอบ"""
    if mode == "cycle" and period_s:
        return period_s * max(1, cycles)
    block = block_s
    rate_g_per_s = rate_ml_h / 3600.0
    if min_block_mg > 0 and rate_g_per_s > 0:
        block = max(block, min_block_mg / 1000.0 / rate_g_per_s)
    if align and period_s:
        block = math.ceil(block / period_s - 1e-9) * period_s
    return block


def flow_variation(t: np.ndarray, w: np.ndarray, block_s: float, blocks: int) -> float | None:
    """ความแกว่งของ flow (%) จาก `blocks` ช่วงล่าสุด ช่วงละ block_s วินาที"""
    if len(t) < 2 or blocks < 2 or t[-1] - t[0] < block_s * blocks:
        return None
    edges = t[-1] - block_s * np.arange(blocks, -1, -1)
    flows = np.diff(np.interp(edges, t, w)) / block_s
    mean = float(flows.mean())
    if mean <= 0:
        return None
    return float((flows.max() - flows.min()) / mean * 100.0)


@dataclass(frozen=True, slots=True)
class Stability:
    variation_pct: float    # (มากสุด − น้อยสุด) / ค่าเฉลี่ย ของ flow รายช่วง
    trend_pct: float        # |ค่าเฉลี่ยครึ่งหลัง − ครึ่งแรก| / ค่าเฉลี่ย
    limit_pct: float        # เกณฑ์ที่ใช้จริง
    stable: bool


def flow_stability(t: np.ndarray, w: np.ndarray, block_s: float, blocks: int,
                   base_limit_pct: float) -> Stability | None:
    """ตรวจ flow นิ่งแบบคำนึงถึงความละเอียดตราชั่งและแนวโน้ม

    1) ความแกว่ง V เหมือน flow_variation
    2) เกณฑ์ = เกณฑ์พื้นฐาน + ส่วนที่มาจากการปัดเศษของตราชั่งล้วนๆ
           ส่วนปัดเศษ = 2 x ความละเอียด / (น้ำหนักที่เพิ่มใน 1 ช่วง) x 100
       (rate ต่ำ น้ำหนักต่อช่วงน้อย การปัดเศษอย่างเดียวก็ทำให้ดูแกว่งได้ จึงต้องเผื่อให้)
    3) แนวโน้ม: ค่าเฉลี่ยของครึ่งหลังต้องไม่ต่างจากครึ่งแรกเกินหนึ่งในสามของเกณฑ์
       (กัน flow ที่ไหลขึ้น/ลงช้าๆ แต่แต่ละช่วงยังดูใกล้กัน)
    """
    if len(t) < 2 or blocks < 2 or t[-1] - t[0] < block_s * blocks:
        return None
    edges = t[-1] - block_s * np.arange(blocks, -1, -1)
    increments = np.diff(np.interp(edges, t, w))
    mean = float(increments.mean())
    if mean <= 0:
        return None
    variation = float((increments.max() - increments.min()) / mean * 100.0)
    half = blocks // 2
    trend = float(abs(increments[-half:].mean() - increments[:half].mean()) / mean * 100.0)

    steps = np.abs(np.diff(w))
    steps = steps[steps > 0]
    resolution = float(steps.min()) if len(steps) else 0.0
    limit = base_limit_pct + 2.0 * resolution / mean * 100.0
    return Stability(variation, trend, limit, variation <= limit and trend <= limit / 3.0)


class PreRun:
    """ตัวคุมช่วงก่อนวัด: ป้อนข้อมูลทีละจุด แล้วถาม .ready"""

    def __init__(self, config: SessionConfig, settings: EngineSettings, tune_windows: bool):
        self._config = config
        self._settings = settings
        self._tune = tune_windows                       # ต้องหาคาบรอบปั๊มก่อนเริ่มวัดไหม
        self._estimator = PeriodEstimator() if tune_windows or config.start_mode is StartMode.AUTO else None
        self._t: list[float] = []
        self._w: list[float] = []
        self._next_analysis = 0.0
        self._stability: Stability | None = None
        self.forced = False                             # ผู้ใช้กด "เริ่มวัดเดี๋ยวนี้"
        self.ready = False
        self.timed_out = False                          # หาคาบไม่ได้ภายในเวลาที่กำหนด
        self.unconfirmed = False                        # เริ่มวัดเพราะครบเวลารอนานสุด (flow ยังไม่ยืนยันว่านิ่ง)
        self.stable_at: float | None = None             # เวลาที่ flow นิ่งครั้งแรก
        self.block_s: float | None = None               # ความยาวช่วงเทียบที่ใช้ล่าสุด

    @property
    def known_period(self) -> float | None:
        """คาบที่วัดได้ก่อนเริ่ม หรือคาบจากโปรไฟล์ (ถ้ามี)"""
        return self.period or (self._settings.expected_period_s or None)

    def block_length(self) -> float:
        """ความยาว 1 ช่วงเทียบความนิ่ง (วินาที) ตามเกณฑ์ของกลุ่มนี้"""
        s = self._settings
        return block_length(s.stability_block_mode, s.stability_block_cycles, s.stability_window_s,
                            s.stability_min_block_mg, s.stability_align_cycle, self._config.target_flow,
                            self.known_period)

    @property
    def period(self) -> float | None:
        return self._estimator.period if self._estimator else None

    def update(self, t: float, weight: float) -> PreRunStatus:
        self._t.append(t)
        self._w.append(weight)
        if t >= self._next_analysis:                    # วิเคราะห์วินาทีละครั้งพอ
            self._next_analysis = t + 1.0
            self._analyse(t)

        mode = self._config.start_mode
        tuning = self._tune and self.period is None and not self.timed_out
        if mode is StartMode.IMMEDIATE:
            start_ok = True
        elif mode is StartMode.DELAY:
            start_ok = t >= self._config.start_delay_s
        elif mode is StartMode.AUTO:
            start_ok = self._stability is not None and self._stability.stable
            if start_ok and self.stable_at is None:
                self.stable_at = t
            max_wait = self._settings.stability_max_wait_s
            if not start_ok and max_wait > 0 and t >= max_wait:
                start_ok = self.unconfirmed = True
        else:
            start_ok = False
        self.ready = self.forced or (start_ok and not tuning)
        if self.ready and not start_ok:
            self.unconfirmed = mode is StartMode.AUTO       # ผู้ใช้กดเริ่มเองก่อนนิ่ง

        return PreRunStatus(
            elapsed_s=t,
            countdown_s=max(0.0, self._config.start_delay_s - t) if mode is StartMode.DELAY else None,
            variation_pct=self._stability.variation_pct if self._stability else None,
            limit_pct=self._stability.limit_pct if self._stability else None,
            period_s=self.period,
            tuning=tuning,
            waiting_user=mode is StartMode.MANUAL,
            block_s=self.block_s,
            max_wait_s=self._settings.stability_max_wait_s if mode is StartMode.AUTO else None,
        )

    def _analyse(self, now: float) -> None:
        block = self.block_length()
        keep = max(MAX_BUFFER_S, block * self._settings.stability_blocks * 1.2 + 60.0)
        while self._t and now - self._t[0] > keep:
            del self._t[:100], self._w[:100]
        t, w = np.asarray(self._t), np.asarray(self._w)
        if self._estimator is not None:
            self._estimator.update(t, w)
        if self._tune and self.period is None and now >= self._settings.auto_tune_timeout_s:
            self.timed_out = True
        if self._config.start_mode is StartMode.AUTO:
            self.block_s = block
            self._stability = flow_stability(t, w, block, self._settings.stability_blocks,
                                             self._settings.stability_pct)
