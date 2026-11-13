"""FlowEngine: หัวใจการคำนวณ (Python ล้วน ไม่ผูกกับ Qt หรือ hardware)

1 session มี 2 ช่วง:
    pre-run   (ถ้าตั้งไว้) ข้อมูลใช้ดูความพร้อม/ปรับหน้าต่างคำนวณ ไม่ถูกนำไปคิดผล
    วัดจริง    เริ่มนับใหม่ทั้งหมด:  warm-up -> slope -> strategy -> สถิติ -> สรุปผล
สร้าง engine ใหม่ทุก session และรับค่าตั้งเป็น "สำเนา" ของการทดสอบนั้น
(การแก้หน้าตั้งค่าระหว่างรันจึงไม่มีผลกับการทดสอบที่กำลังเดิน)

หน่วยความจำ: engine ไม่เก็บข้อมูลดิบทุกจุด (RawRecorder เขียนลงดิสก์ระหว่างรันแล้ว) เก็บเฉพาะ
จำนวนจุด/เวลาแรก-สุดท้าย สถิติแบบสะสม (RunningStats) และรายการช่วงวัด (ต้องใช้บันทึก intervals.csv)
— รันหลายชั่วโมงหน่วยความจำโตตามจำนวนช่วงวัดเท่านั้น (~100 ไบต์ต่อช่วง)
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
from core.capture_check import check_cycle_capture
from core.stats import RunningStats, percent_error, regression_slope
from core.strategies import STRATEGIES
from core.windows import cycle_windows

FALLBACK_STROKE_VOLUME_ML = 0.16    # ใช้เดาคาบเมื่อหาไม่ได้และหน้าตั้งค่าตั้งปริมาตรต่อรอบเริ่มต้นเป็น 0


class _Span:
    """จำนวนจุด + (t, w) แรก/สุดท้าย ของช่วงหนึ่ง — แทนการเก็บทุกจุดไว้ใน list"""
    __slots__ = ("count", "first", "last")

    def __init__(self):
        self.count = 0
        self.first: tuple[float, float] | None = None
        self.last: tuple[float, float] | None = None

    def add(self, t: float, weight: float) -> None:
        self.count += 1
        if self.first is None:
            self.first = (t, weight)
        self.last = (t, weight)

    @property
    def elapsed(self) -> float:
        return self.last[0] - self.first[0] if self.first else 0.0

    @property
    def sample_period(self) -> float:
        """ช่วงเวลาต่อจุดเฉลี่ย (0 = ยังไม่รู้)"""
        return self.elapsed / (self.count - 1) if self.count > 1 else 0.0

    def __bool__(self) -> bool:
        return self.count > 0


class _SlopeWindow:
    """flow ขณะนั้นจาก linear regression แบบหน้าต่างเลื่อน"""
    MIN_POINTS = 10     # ค่าแรกออกเมื่อมีจุดครบเท่านี้ (หรือเต็มหน้าต่าง ถ้าหน้าต่างเล็กกว่า)
    ABSOLUTE_MIN = 3    # regression ต้องมีอย่างน้อย 3 จุด

    def __init__(self, size: int, ml_per_g: float, baseline_g_per_h: float, limit: float):
        size = max(self.ABSOLUTE_MIN, size)
        # เดิม 10 จุดตายตัว: หน้าต่าง < 10 จุด (rate สูง + ตราชั่ง 5 Hz) ส่ง slope = None เข้าตัวจับ peak แล้ว crash
        self.min_points = min(size, self.MIN_POINTS)
        self._points: deque[tuple[float, float]] = deque(maxlen=size)
        self._ml_per_g = ml_per_g
        self._baseline = baseline_g_per_h
        self._limit = limit
        self.count = 0

    def push(self, t: float, weight: float) -> float | None:
        self._points.append((t, weight))
        self.count += 1
        if self.count < self.min_points:
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
        self.points_per_cycle: float | None = None
        self.windows_logged = False             # controller เขียน log ขนาดหน้าต่างแล้วหรือยัง

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

        # ข้อมูลที่เก็บไว้สำหรับสรุปผล (ข้อมูลดิบถูกเขียนลงไฟล์ระหว่างรันโดย RawRecorder — ไม่เก็บใน RAM)
        self.prerun_span = _Span()
        self.span = _Span()
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
        self.prerun_span.add(t, sample.weight)
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
        """จบช่วงก่อนวัด: ตั้งหน้าต่างจากคาบ "เสมอ" (ไม่ถอยไปค่าตายตัวแม้ได้จุดน้อย — core/windows.py)"""
        if not self._tune:
            return
        period = self._prerun.period
        if period is not None:
            self.pump_period_s = period
            self.window_source = "measured"
        elif self.settings.expected_period_s > 0:
            # หาคาบไม่ได้แต่รู้คาบจากโปรไฟล์ของรุ่นนี้
            period = self.settings.expected_period_s
            self.window_source = "profile"
            self.notes.append("Pump cycle period not found before measuring; the model's known cycle was used")
        else:
            # หาคาบไม่ได้: เดาจากปริมาตรต่อรอบเริ่มต้น (ตามสัดส่วน rate) — ดีกว่าค่าเดียวที่ไม่สนใจ rate
            stroke = self.settings.default_stroke_volume_ml or FALLBACK_STROKE_VOLUME_ML
            period = stroke * 3600.0 / self.config.target_flow
            self.window_source = "default"
            self.notes.append("Pump cycle period not found; window sizes were estimated from the default volume per cycle")
        windows = cycle_windows(period, self.prerun_span.sample_period, self.settings.auto_window_fraction,
                                self.settings.half_fraction)
        if windows is not None:
            self.settings.regression_window = windows.regression
            self.settings.cycle_half_window = windows.half
            self.points_per_cycle = windows.points_per_cycle
            if windows.level != "ok":
                self.notes.append(f"Only {windows.points_per_cycle:.1f} balance points per pump cycle - "
                                  "peak detection is coarse; consider time-based capture or a faster balance output")

    def _begin_measurement(self) -> None:
        self._measuring = True
        self._t0: float | None = None
        self._slope = self._new_slope_window()
        self._flows = RunningStats()
        self._flows_raw = RunningStats()
        self._durations = RunningStats()
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
        self.span.add(t, weight)
        result = EngineResult(t=t, weight=weight, stage=Stage.WARMUP,
                              measurement_started=self._first_measure_sample)
        self._first_measure_sample = False

        window = max(_SlopeWindow.ABSOLUTE_MIN, self.settings.regression_window)
        if t < self.settings.warmup_s:
            result.eta_s = self.settings.warmup_s - t
            return result
        result.slope_flow = self._slope.push(t, weight)
        # วิธีจับรอบปั๊มต้องรอให้หน้าต่าง regression เต็มก่อน (วิธีจับตามเวลาไม่ต้องรอ)
        if self._needs_slope and self._slope.count < window:
            dt = self.span.sample_period or 0.1
            result.eta_s = (window - self._slope.count) * dt
            return result

        self.strategy.update(t, weight, result.slope_flow, result)

        if result.interval is not None:
            self.intervals.append(result.interval)
            self._flows.add(result.interval.flow)
            self._flows_raw.add(result.interval.flow_raw)
            self._durations.add(result.interval.duration_s)
            self.stats = result.stats = self._compute_stats()
        if result.cumulative is not None:
            self.cumulative = result.cumulative
        result.stage = Stage.MEASURING if self.cumulative is not None else Stage.SEARCHING
        self.finished = result.finished
        return result

    def _compute_stats(self) -> IntervalStats:
        """สถิติของ "ทุก" ช่วงวัดตั้งแต่เริ่มการทดสอบ (สะสม O(1) ต่อช่วง — ไม่คำนวณใหม่จากทุกค่า)"""
        target = self.config.target_flow
        flows, durations = self._flows, self._durations
        return IntervalStats(
            count=len(self.intervals),
            mean_flow=flows.mean,
            mean_error_pct=percent_error(flows.mean, target),
            ci95_pct=flows.confidence() / target * 100.0,
            sd2_pct=flows.expanded() / target * 100.0,
            mean_duration_s=durations.mean,
            ci95_duration_s=durations.confidence(),
            sd2_duration_s=durations.expanded(),
            mean_flow_raw=self._flows_raw.mean,
            mean_error_raw_pct=percent_error(self._flows_raw.mean, target),
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

    def capture_check(self):
        """ผลตรวจความสมเหตุสมผลของการจับรอบ (None = ไม่ได้จับรอบปั๊ม)"""
        if not self.strategy_uses_cycles:
            return None
        # คาบอ้างอิงจากโปรไฟล์ใช้ได้เมื่อมาจากการวัดจริง (ค่าแทนไปก่อนของรุ่นอาจเป็นค่าที่ผู้ใช้เดา)
        reliable = self.settings.expected_period_source in ("rate", "profile", "")
        expected = self.settings.expected_period_s if reliable else 0.0
        return check_cycle_capture(len(self.intervals), self.stats.mean_duration_s if self.stats else None,
                                   expected or None, self.pump_period_s)

    def verdict(self) -> Verdict:
        check = self.capture_check()
        if check is not None and check.invalid:
            return Verdict.INVALID
        error = self.current_error()
        if error is None:
            return Verdict.NONE
        return Verdict.PASS if abs(error) <= self.config.tolerance_pct else Verdict.FAIL

    def summary(self, end_reason: str, source: str = "") -> SessionSummary:
        summary = SessionSummary(
            config=self.config,
            started_at=self.started_at.isoformat(timespec="seconds"),
            end_reason=end_reason,
            duration_s=self.span.last[0] if self.span else 0.0,
            prerun_s=self.prerun_span.last[0] if self.prerun_span else 0.0,
            sample_count=self.span.count,
            interval_count=len(self.intervals),
            error_pct=self.current_error(),
            verdict=self.verdict(),
            source=source,
            regression_window=self.settings.regression_window,
            cycle_half_window=self.settings.cycle_half_window,
            pump_period_s=self.pump_period_s,
            sample_period_s=self.span.sample_period or self.prerun_span.sample_period or None,
            mean_duration_s=self.stats.mean_duration_s if self.stats else None,
            sd2_duration_s=self.stats.sd2_duration_s if self.stats else None,
            volume_per_interval_ml=(self.stats.mean_flow * self.stats.mean_duration_s / 3600.0) if self.stats else None,
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
        if self.strategy_uses_cycles:
            period = self.pump_period_s or self.settings.expected_period_s or None
            dt = summary.sample_period_s
            summary.points_per_cycle = self.points_per_cycle or (period / dt if period and dt else None)
            check = self.capture_check()
            summary.capture_check = check.to_dict()
            if check.invalid:
                summary.notes.append(check.message().format(**check.message_values()))
        if end_reason != "completed":
            summary.notes.append("Test did not run to completion; the verdict is provisional")
        return summary

    @property
    def strategy_uses_cycles(self) -> bool:
        return bool(getattr(STRATEGIES.get(self.config.strategy), "uses_cycles", False))
