"""FlowEngine: หัวใจการคำนวณ (Python ล้วน ไม่ผูกกับ Qt หรือ hardware)

1 session มี 2 ช่วง:
    pre-run   (ถ้าตั้งไว้) ข้อมูลใช้ดูความพร้อม/ปรับหน้าต่างคำนวณ ไม่ถูกนำไปคิดผล
    วัดจริง    เริ่มนับใหม่ทั้งหมด:  warm-up -> slope -> strategy -> สถิติ -> สรุปผล
สร้าง engine ใหม่ทุก session และรับค่าตั้งเป็น "สำเนา" ของการทดสอบนั้น
(การแก้หน้าตั้งค่าระหว่างรันจึงไม่มีผลกับการทดสอบที่กำลังเดิน)
"""
from __future__ import annotations

import dataclasses
from collections import deque
from datetime import datetime

from config.settings import EngineSettings
from core.models import (
    Cumulative, EngineResult, Interval, IntervalStats, Sample,
    SessionConfig, SessionSummary, Stage, StartMode, Verdict,
)
from core.prerun import PreRun
from core.stats import confidence_interval, expanded_std, percent_error, regression_slope
from core.strategies import STRATEGIES


class _SlopeWindow:
    """flow ขณะนั้นจาก linear regression แบบหน้าต่างเลื่อน"""
    MIN_POINTS = 10     # น้อยกว่านี้ค่ายังไม่มีความหมาย

    def __init__(self, size: int, ml_per_g: float, baseline_g_per_h: float, limit: float):
        self._points: deque[tuple[float, float]] = deque(maxlen=size)
        self._ml_per_g = ml_per_g
        self._baseline = baseline_g_per_h
        self._limit = limit
        self.count = 0

    def push(self, t: float, weight: float) -> float | None:
        self._points.append((t, weight))
        self.count += 1
        if self.count < self.MIN_POINTS:
            return None
        grams_per_h = regression_slope(self._points) * 3600.0 - self._baseline
        return min(grams_per_h * self._ml_per_g, self._limit)


class FlowEngine:
    def __init__(self, config: SessionConfig, settings: EngineSettings,
                 density_source: str = "settings", window_source: str = "manual",
                 correction: dict | None = None):
        if config.target_flow <= 0:
            raise ValueError("Target rate must be greater than 0")
        self.config = config
        self.settings = dataclasses.replace(settings)     # สำเนาของการทดสอบนี้
        self.density_source = density_source
        self.window_source = window_source
        self.correction = dict(correction or {})          # ที่มาของปัจจัย Z (บันทึกไปกับผล)
        self.started_at = datetime.now()
        self.pump_period_s: float | None = None
        self.notes: list[str] = []
        self.stability_confirmed: bool | None = None
        self.stable_after_s: float | None = None

        strategy_class = STRATEGIES.get(config.strategy)
        tune = self.settings.window_mode == "auto" and getattr(strategy_class, "uses_cycles", False)
        self._prerun: PreRun | None = None
        if tune or config.start_mode is not StartMode.IMMEDIATE:
            self._prerun = PreRun(config, self.settings, tune_windows=tune)
        self._tune = tune
        self._prerun_t0: float | None = None
        self._preview = self._new_slope_window()
        self._start_requested = False       # ตั้งจาก thread อื่นได้ (bool เดียว)
        self._measuring = self._prerun is None
        self._first_measure_sample = self._prerun is not None

        # ข้อมูลที่เก็บไว้สำหรับสรุปผล (ข้อมูลดิบถูกเขียนลงไฟล์ระหว่างรันโดย RawRecorder)
        self.prerun_samples: list[tuple[float, float]] = []
        self.samples: list[tuple[float, float]] = []
        self.intervals: list[Interval] = []
        self.stats: IntervalStats | None = None
        self.cumulative: Cumulative | None = None
        self.finished = False
        if self._measuring:
            self._begin_measurement()

    # ------------------------------------------------------------ commands
    def request_start(self) -> None:
        """ผู้ใช้สั่งเริ่มวัดจริงเดี๋ยวนี้ (ข้าม pre-run ที่เหลือ)"""
        self._start_requested = True

    @property
    def in_prerun(self) -> bool:
        return not self._measuring

    # --------------------------------------------------------------- main
    def process(self, sample: Sample) -> EngineResult:
        if not self._measuring:
            return self._process_prerun(sample)
        return self._process_measurement(sample)

    def _process_prerun(self, sample: Sample) -> EngineResult:
        if self._prerun_t0 is None:
            self._prerun_t0 = sample.t
        t = sample.t - self._prerun_t0
        self.prerun_samples.append((t, sample.weight))
        if self._start_requested:
            self._prerun.forced = True
        status = self._prerun.update(t, sample.weight)
        result = EngineResult(t=t, weight=sample.weight, stage=Stage.PRERUN, prerun=status)
        if t >= self.settings.warmup_s:
            result.slope_flow = self._preview.push(t, sample.weight)
        if self._prerun.ready:
            self._apply_tuning()
            if self.config.start_mode is StartMode.AUTO:
                self.stability_confirmed = not self._prerun.unconfirmed
                self.stable_after_s = self._prerun.stable_at
                if self._prerun.unconfirmed:
                    self.notes.append("Measurement started before the flow was confirmed stable "
                                      "(maximum wait reached or started by hand)")
            self._begin_measurement()       # sample ถัดไปคือจุดเริ่มของการวัดจริง
        return result

    def _apply_tuning(self) -> None:
        if not self._tune:
            return
        period, fraction = self._prerun.period, self.settings.auto_window_fraction
        if period is None and self.settings.default_stroke_volume_ml > 0:
            # หาคาบไม่ได้: เดาจากปริมาตรต่อรอบเริ่มต้น (ตามสัดส่วน rate) ดีกว่าค่ากำหนดเองที่ไม่สนใจ rate
            period = self.settings.default_stroke_volume_ml * 3600.0 / self.config.target_flow
            self.window_source = "default"
            self.notes.append("Pump cycle period not found; window sizes were estimated from the default volume per cycle")
        elif period is None:
            self.window_source = "manual"
            self.notes.append("Pump cycle period not found; manual window sizes were used")
            return
        else:
            self.pump_period_s = period
            self.window_source = "measured"
        samples = self.prerun_samples
        dt = (samples[-1][0] - samples[0][0]) / max(1, len(samples) - 1)
        points = round(period * fraction / dt) if dt > 0 else 0
        if points >= 5:
            self.settings.regression_window = max(10, points)
            self.settings.cycle_half_window = max(5, points)

    def _begin_measurement(self) -> None:
        self._measuring = True
        self._t0: float | None = None
        self._slope = self._new_slope_window()
        self._flows: list[float] = []
        self._flows_raw: list[float] = []
        self._durations: list[float] = []
        self.strategy = STRATEGIES.create(self.config.strategy, self.config, self.settings)
        self._needs_slope = self.strategy.uses_cycles

    def _new_slope_window(self) -> _SlopeWindow:
        return _SlopeWindow(
            self.settings.regression_window, self.settings.volume_factor,
            self.settings.baseline_g_per_h,
            self.config.target_flow * self.settings.slope_clamp_factor,
        )

    def _process_measurement(self, sample: Sample) -> EngineResult:
        if self._t0 is None:
            self._t0 = sample.t
        t, weight = sample.t - self._t0, sample.weight
        self.samples.append((t, weight))
        result = EngineResult(t=t, weight=weight, stage=Stage.WARMUP,
                              measurement_started=self._first_measure_sample)
        self._first_measure_sample = False

        window = self.settings.regression_window
        if t < self.settings.warmup_s:
            result.eta_s = self.settings.warmup_s - t
            return result
        result.slope_flow = self._slope.push(t, weight)
        # วิธีจับรอบปั๊มต้องรอให้หน้าต่าง regression เต็มก่อน (วิธีจับตามเวลาไม่ต้องรอ)
        if self._needs_slope and self._slope.count < window:
            dt = t / max(1, len(self.samples) - 1) if len(self.samples) > 1 else 0.1
            result.eta_s = (window - self._slope.count) * dt
            return result

        self.strategy.update(t, weight, result.slope_flow, result)

        if result.interval is not None:
            self.intervals.append(result.interval)
            self._flows.append(result.interval.flow)
            self._flows_raw.append(result.interval.flow_raw)
            self._durations.append(result.interval.duration_s)
            self.stats = result.stats = self._compute_stats()
        if result.cumulative is not None:
            self.cumulative = result.cumulative
        result.stage = Stage.MEASURING if self.cumulative is not None else Stage.SEARCHING
        self.finished = result.finished
        return result

    def _compute_stats(self) -> IntervalStats:
        """สถิติของ "ทุก" ช่วงวัดตั้งแต่เริ่มการทดสอบ"""
        target = self.config.target_flow
        mean_flow, ci_flow = confidence_interval(self._flows)
        mean_dur, ci_dur = confidence_interval(self._durations)
        return IntervalStats(
            count=len(self.intervals),
            mean_flow=mean_flow,
            mean_error_pct=percent_error(mean_flow, target),
            ci95_pct=ci_flow / target * 100.0,
            sd2_pct=expanded_std(self._flows) / target * 100.0,
            mean_duration_s=mean_dur,
            ci95_duration_s=ci_dur,
            sd2_duration_s=expanded_std(self._durations),
            mean_flow_raw=sum(self._flows_raw) / len(self._flows_raw),
            mean_error_raw_pct=percent_error(sum(self._flows_raw) / len(self._flows_raw), target),
        )

    # ------------------------------------------------------------ summary
    def current_error(self) -> float | None:
        """error ที่ใช้ตัดสิน: ค่าเฉลี่ยของช่วงวัดที่ "ครบสมบูรณ์" เท่านั้น

        (ค่าสะสมแบบ real-time แกว่งตามจังหวะของรอบปั๊ม จึงใช้เป็นตัวสำรองเฉพาะ
        เมื่อยังไม่มีช่วงวัดที่ครบเลย)
        """
        if self.stats is not None:
            return self.stats.mean_error_pct
        if self.cumulative is not None:
            return self.cumulative.best_error
        return None

    def verdict(self) -> Verdict:
        error = self.current_error()
        if error is None:
            return Verdict.NONE
        return Verdict.PASS if abs(error) <= self.config.tolerance_pct else Verdict.FAIL

    def summary(self, end_reason: str, source: str = "") -> SessionSummary:
        summary = SessionSummary(
            config=self.config,
            started_at=self.started_at.isoformat(timespec="seconds"),
            end_reason=end_reason,
            duration_s=self.samples[-1][0] if self.samples else 0.0,
            prerun_s=self.prerun_samples[-1][0] if self.prerun_samples else 0.0,
            sample_count=len(self.samples),
            interval_count=len(self.intervals),
            error_pct=self.current_error(),
            verdict=self.verdict(),
            source=source,
            regression_window=self.settings.regression_window,
            cycle_half_window=self.settings.cycle_half_window,
            pump_period_s=self.pump_period_s,
            window_source=self.window_source if self.strategy_uses_cycles else "",
            stability_confirmed=self.stability_confirmed,
            stable_after_s=self.stable_after_s,
            density_g_per_ml=self.settings.density_g_per_ml,
            density_source=self.density_source,
            baseline_g_per_h=self.settings.baseline_g_per_h,
            ml_per_g=self.settings.volume_factor,
            correction=dict(self.correction),
            engine_settings=dataclasses.asdict(self.settings),
            notes=list(self.notes),
        )
        if self.stats is not None:
            summary.mean_flow = self.stats.mean_flow
            summary.ci95_pct = self.stats.ci95_pct
            summary.sd2_pct = self.stats.sd2_pct
            summary.mean_flow_raw = self.stats.mean_flow_raw
        elif self.cumulative is not None:
            summary.mean_flow = self.cumulative.best_flow
            if summary.mean_flow is not None:       # ย้อนสูตร: ดิบ = สุทธิ / Z + baseline
                summary.mean_flow_raw = summary.mean_flow / self.settings.volume_factor + self.settings.baseline_g_per_h
        if summary.mean_flow_raw is not None:
            summary.error_raw_pct = percent_error(summary.mean_flow_raw, self.config.target_flow)
        if end_reason != "completed":
            summary.notes.append("Test did not run to completion; the verdict is provisional")
        return summary

    @property
    def strategy_uses_cycles(self) -> bool:
        return bool(getattr(STRATEGIES.get(self.config.strategy), "uses_cycles", False))
