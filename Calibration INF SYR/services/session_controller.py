"""SessionController: ผู้คุมการทดสอบทั้งหมด

UI คุยกับตัวนี้ตัวเดียว: ส่งแผนทดสอบ (TestPlan) สั่ง start/stop แล้วฟัง signal
— ไม่ต้องรู้จัก thread, engine, hardware, ฐานข้อมูล

วงจรของ 1 ขั้นทดสอบ
    start_step() → กำลังวัด → จบ → review_requested (ถามผู้ใช้)
        keep_result()     บันทึกลงฐานข้อมูล ถ้าครบเวลาจะเลื่อนไปขั้นถัดไป
        discard_result()  ลบข้อมูลทิ้ง ขั้นเดิมยังอยู่ → กดเริ่มคือทำซ้ำ
ค่าคำนวณของแต่ละขั้นถูก "คัดลอก" ตอนเริ่ม (ปัจจัย Z จากอุณหภูมิ/ความชื้น/ความดัน, ค่าแก้จาก self-check,
ขนาดหน้าต่างจากโปรไฟล์ปั๊ม) การแก้หน้าตั้งค่าระหว่างรันจึงไม่มีผล
"""
from __future__ import annotations

import dataclasses
import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from config.i18n import tr
from config.settings import AppSettings, EngineSettings, PrerunCriteria, prerun_group
from core.corrections import BaselineEngine, GravimetricCorrection, SelfCheckResult, gravimetric_correction
from core.engine import FlowEngine
from core.models import SessionConfig, SessionState, SessionSummary, TestPlan
from core.profiles import PumpProfile
from core.strategies import STRATEGIES
from hardware import SOURCES
from services.acquisition import AcquisitionWorker
from services.monitor import BalanceMonitor
from services.recorder import RawRecorder
from services.session_store import get_repository
from services.tuner import WindowTuner

log = logging.getLogger("deltam.session")

_END_STATES = {
    "completed": SessionState.COMPLETED,
    "stopped": SessionState.STOPPED,
    "error": SessionState.ERROR,
}


# ที่มาของหน้าต่างราย rate บนจอ
WINDOW_FITS = {"tuned": "tuned for this rate", "interpolated": "between tuned rates", "default": "Settings"}

# ชื่อกลุ่มเกณฑ์ช่วงก่อนวัดบนจอ
PRERUN_GROUP_NAMES = {
    "infusion_cycle": "Infusion · pump-cycle capture",
    "infusion_time": "Infusion · time-based capture",
    "syringe_time": "Syringe · time-based capture",
}


def tuning_text(result) -> str:
    """สรุปผลการปรับหน้าต่าง 1 rate (ใช้ใน log และหน้าประวัติ)"""
    fractions = result.recommended()
    if fractions is None:
        return tr("{rate:g} ml/h: no window size found the pump cycles reliably ({n} tests)",
                  rate=result.rate, n=result.sessions)
    points = result.points(fractions)
    current = result.current_score
    return tr("{rate:g} ml/h: regression {r:.2f} × cycle ({rp} pts), n̄ {h:.2f} × cycle ({hp} pts) · "
              "score {s:.3f} (before {cs}) · {n} tests",
              rate=result.rate, r=fractions[0], h=fractions[1], rp=points[0], hp=points[1], s=result.best.score,
              cs=f"{current:.3f}" if current is not None and current == current and current != float("inf") else "—",
              n=result.sessions)


class SessionController(QObject):
    state_changed = Signal(object)          # SessionState
    plan_changed = Signal()                 # แผน หรือความคืบหน้าของแผนเปลี่ยน
    session_started = Signal(object)        # SessionConfig ของขั้นที่เริ่ม
    results_ready = Signal(list)            # list[EngineResult] (รวมเป็นชุดตามรอบวาดจอ)
    review_requested = Signal(object)       # SessionSummary — รอผู้ใช้ตัดสินว่าเก็บหรือไม่
    session_finished = Signal(object, bool) # SessionSummary, เก็บผลไหม (หลังผู้ใช้ตัดสินแล้ว)
    self_check_started = Signal(float)      # ระยะเวลา (s)
    self_check_finished = Signal(object)    # SelfCheckResult (None = ถูกยกเลิก/ผิดพลาด)
    balance_status = Signal(bool, str)      # สถานะตราชั่งตอนว่าง
    live_reading = Signal(float, object)    # น้ำหนักสดตอนว่าง, ธงนิ่ง

    def __init__(self, settings: AppSettings, parent: QObject | None = None):
        super().__init__(parent)
        self.settings = settings
        self.repository = get_repository()
        self.state = SessionState.IDLE
        self.plan: TestPlan | None = None
        self.step_index = 0                             # ขั้นถัดไปที่จะรัน
        self.step_results: list[SessionSummary] = []    # ผลของขั้นที่เก็บแล้ว
        self.pending_summary: SessionSummary | None = None   # ผลที่รอผู้ใช้ตัดสิน
        self.sample_period_s: float | None = None       # ช่วงเวลาต่อจุดของตราชั่ง (วัดตอนว่าง)
        self._engine = None
        self._folder: Path | None = None
        self._worker: AcquisitionWorker | None = None
        self._thread: QThread | None = None
        self._monitor: BalanceMonitor | None = None
        self._monitor_thread: QThread | None = None
        self._pending: list = []
        self._flush_timer = QTimer(self)
        self._flush_timer.timeout.connect(self._flush)
        self.tuner = WindowTuner(self.repository, self)        # ปรับหน้าต่างจากข้อมูลย้อนหลัง (thread แยก)
        self.tuner.finished.connect(self._on_tuned)
        # หน้าจอตั้งให้: ถามผู้ใช้เมื่อรอบปั๊มต่างจากข้อมูลเดิมเกินเกณฑ์ -> "add" | "skip" | "recalibrate"
        # (ไม่ได้ตั้ง = ไม่เก็บค่าที่ต่างเกินเกณฑ์)
        self.ask_profile_decision = None
        self._recalibrated: set[str] = set()     # job_id ของแผน "Calibration ใหม่" ที่ล้างข้อมูลเดิมไปแล้ว

    # ------------------------------------------------------------- สถานะ
    @property
    def is_running(self) -> bool:
        return self.state in (SessionState.RUNNING, SessionState.STOPPING)

    @property
    def awaiting_review(self) -> bool:
        return self.pending_summary is not None

    @property
    def has_next_step(self) -> bool:
        return self.plan is not None and self.step_index < len(self.plan.steps)

    @property
    def can_start(self) -> bool:
        return self.has_next_step and not self.is_running and not self.awaiting_review

    def baseline_today(self) -> SelfCheckResult | None:
        """self-check ที่ผ่านของวันนี้ (ถ้ามี จะถูกใช้เป็นค่าแก้อัตโนมัติ)"""
        result = self.repository.latest_self_check()
        return result if result is not None and result.passed else None

    def correction_for(self, plan: TestPlan | None = None) -> GravimetricCorrection | None:
        """ค่าแก้ g -> ml ที่การทดสอบตามแผนนี้จะใช้ (ISO 4787 Z + self-check ของวันนี้)"""
        plan = plan or self.plan
        if plan is None:
            return None
        baseline = self.baseline_today()
        return gravimetric_correction(plan.job, self.settings.engine,
                                      baseline.rate_g_per_h if baseline else 0.0,
                                      baseline.measured_at if baseline else "")

    def prerun_criteria_for(self, job, strategy: str) -> tuple[PrerunCriteria, str, bool]:
        """(เกณฑ์ช่วงก่อนวัด, กลุ่ม, เป็นค่าเฉพาะรุ่นไหม) — รุ่น + ชนิด + ชุดสาย ที่ตั้งไว้ก่อน ไม่งั้นค่าเริ่มต้นของกลุ่ม"""
        group = prerun_group(job.pump_type.value, STRATEGIES.get(strategy).uses_cycles)
        criteria = dataclasses.replace(self.settings.prerun.group(group))
        override = self.repository.prerun_criteria(job.brand, job.model, job.accessory, job.pump_type.value, group)
        if override:
            for name, value in override.items():
                if hasattr(criteria, name):
                    setattr(criteria, name, type(getattr(criteria, name))(value))
        return criteria, group, bool(override)

    def profile_for(self, plan: TestPlan | None = None) -> PumpProfile | None:
        plan = plan or self.plan
        if plan is None:
            return None
        return self.repository.get_profile(plan.job.brand, plan.job.model, plan.job.accessory, plan.job.pump_type.value)

    # ---------------------------------------------------------------- plan
    def set_plan(self, plan: TestPlan) -> None:
        if self.is_running or self.awaiting_review:
            return
        plan.job_id = datetime.now().strftime("J%Y%m%d-%H%M%S")
        self.plan = plan
        self.step_index = 0
        self.step_results = []
        self.plan_changed.emit()

    def adopt(self, other: "SessionController") -> None:
        """รับแผนและความคืบหน้าต่อจาก controller ตัวเก่า (ใช้ตอนสร้างหน้าต่างใหม่)"""
        self.plan, self.step_index, self.step_results = other.plan, other.step_index, list(other.step_results)
        self.sample_period_s = other.sample_period_s
        self.plan_changed.emit()

    def start_step(self) -> bool:
        """เริ่มขั้นถัดไปของแผน"""
        if not self.can_start:
            return False
        return self._start_test(self.plan.session_config(self.step_index))

    def stop(self) -> None:
        if self.state is SessionState.RUNNING and self._worker is not None:
            self._set_state(SessionState.STOPPING)
            self._worker.request_stop()

    def begin_measurement(self) -> None:
        """ข้ามช่วง pre-run แล้วเริ่มวัดจริงเดี๋ยวนี้"""
        if self._engine is not None and self.is_running:
            self._engine.request_start()

    def shutdown(self) -> None:
        """เรียกตอนปิดโปรแกรม: หยุดทุกอย่าง — การทดสอบที่ยังไม่จบ/ยังไม่ได้ตัดสินจะไม่ถูกเก็บ"""
        self.stop_monitor()
        self.tuner.cancel()
        if self._worker is not None:
            self._worker.request_stop()
            self._worker.done.wait(3.0)
            self._finalize("stopped", closing=True)
        if self.awaiting_review:
            self.discard_result(closing=True)

    # ------------------------------------------------------- เก็บ / ไม่เก็บ
    def keep_result(self) -> None:
        summary, engine, folder = self.pending_summary, self._engine, self._folder
        if summary is None:
            return
        self.pending_summary = None
        try:
            ref = self.repository.save(summary, engine.intervals, folder)
            log.info(tr("Result saved"))
        except Exception as exc:
            log.error(tr("Could not save the result: {error}", error=exc))
            ref = ""
        if summary.end_reason == "completed":
            self.step_results.append(summary)
            self.step_index += 1
            self._learn_profile(summary, engine, ref)
            self._tune_windows(summary, engine)
        self._after_review(summary, kept=True)

    def discard_result(self, closing: bool = False) -> None:
        summary = self.pending_summary
        if summary is None:
            return
        self.pending_summary = None
        if self._folder is not None:
            self.repository.discard_folder(self._folder)
        if not closing:
            log.info(tr("Result discarded — press Start to run this step again"))
            self._after_review(summary, kept=False)

    def _after_review(self, summary: SessionSummary, kept: bool) -> None:
        self._engine = self._folder = None
        self.plan_changed.emit()
        self.session_finished.emit(summary, kept)

    def _learn_profile(self, summary: SessionSummary, engine: FlowEngine, ref: str) -> None:
        """การทดสอบแบบจับรอบปั๊มที่เก็บผล = ข้อสังเกตใหม่ 1 รายการของโปรไฟล์ปั๊ม

        ต่างจากข้อมูลเดิมเกินเกณฑ์ (25 %) -> ถามผู้ใช้ (ask_profile_decision): เก็บรวม / ไม่เก็บ / Calibration ใหม่
        แผนแบบ "Calibration รอบปั๊มใหม่": ขั้นแรกที่เก็บผลครบ = ล้างข้อมูลเดิมของรุ่นนี้ แล้วเริ่มจากค่านี้
        """
        if not engine.strategy_uses_cycles or engine.stats is None or engine.stats.count < 4:
            return
        job, config = summary.config.job, summary.config
        args = (job.brand, job.model, job.accessory)
        rate, period, flow = config.target_flow, engine.stats.mean_duration_s, engine.stats.mean_flow
        decision = "auto"
        if config.window_source == "recalibrate" and config.job_id not in self._recalibrated:
            decision = "calibration"
        else:
            check = self.repository.check_observation(*args, rate, period, flow, job.pump_type.value)
            if check.status == "out_of_range":
                choice = self.ask_profile_decision(check) if self.ask_profile_decision else "skip"
                decision = "calibration" if choice == "recalibrate" else choice
        if decision == "calibration":
            if not self.repository.recalibrate(*args, job.pump_type.value, since=summary.started_at):
                return
            self._recalibrated.add(config.job_id)
            log.info(tr("Pump cycle calibration: earlier data of this model is no longer used (kept for audit)"))
        profile, status = self.repository.add_observation(*args, rate, period, flow, ref, job.pump_type.value, decision)
        if status == "merged":
            log.info(tr("Pump profile updated: {ml:.3f} ml per cycle ({n} runs)",
                        ml=profile.stroke_volume_ml, n=profile.runs))
        elif status == "rate_only":
            log.info(tr("Pump cycle at {rate:g} ml/h ({p:.1f} s) does not fit the profile's volume per cycle — "
                        "remembered for this rate only", rate=summary.config.target_flow,
                        p=engine.stats.mean_duration_s))
        elif status in ("rejected", "declined"):
            log.warning(tr("Pump cycle ({p:.1f} s) differs from earlier runs at this rate and was not remembered",
                           p=engine.stats.mean_duration_s))

    def _tune_windows(self, summary: SessionSummary, engine: FlowEngine) -> None:
        """เก็บผลจับรอบปั๊มแล้ว: ปรับสัดส่วนหน้าต่าง/คาบ ของ rate นี้จากข้อมูลย้อนหลัง (เบื้องหลัง)"""
        job = summary.config.job
        if not engine.strategy_uses_cycles or not (job.brand or job.model):
            return
        defaults = (self.settings.engine.auto_window_fraction, self.settings.engine.half_fraction)
        if self.tuner.start(job.brand, job.model, job.accessory, summary.config.target_flow,
                            engine.settings.cycle_chains, defaults, job.pump_type.value):
            log.info(tr("Tuning the peak-detection window from stored tests in the background…"))

    @Slot(object, object)
    def _on_tuned(self, key, results) -> None:
        brand, model, iv_set, pump_type = key
        for result in results:
            self.repository.save_tuning(brand, model, iv_set, result, pump_type)
            log.info(tuning_text(result))

    # ----------------------------------------------------------- self-check
    def start_self_check(self) -> bool:
        if self.is_running or self.awaiting_review:
            return False
        engine = BaselineEngine(dataclasses.replace(self.settings.selfcheck))
        log.info(tr("Self-check started ({min:g} min) — pump stopped, do not touch the beaker",
                    min=engine.criteria.duration_min))
        if not self._launch(engine, SessionConfig(target_flow=0.0), recorder=None):
            return False
        self.self_check_started.emit(engine.duration_s)
        return True

    # ------------------------------------------------------- balance monitor
    def start_monitor(self) -> None:
        if self._monitor is not None or self.is_running:
            return
        try:
            source = SOURCES.create(self.settings.source, self.settings, SessionConfig(target_flow=0.0))
        except Exception as exc:
            self.balance_status.emit(False, str(exc))
            return
        self._monitor = BalanceMonitor(source)
        self._monitor_thread = QThread(self)
        self._monitor.moveToThread(self._monitor_thread)
        self._monitor_thread.started.connect(self._monitor.run)
        self._monitor.status.connect(self.balance_status)
        self._monitor.reading.connect(self.live_reading)
        self._monitor.sample_period.connect(self._on_sample_period)
        self._monitor_thread.start()

    def stop_monitor(self) -> None:
        if self._monitor is None:
            return
        monitor, thread = self._monitor, self._monitor_thread
        self._monitor = self._monitor_thread = None
        monitor.status.disconnect(self.balance_status)
        monitor.reading.disconnect(self.live_reading)
        monitor.sample_period.disconnect(self._on_sample_period)
        monitor.request_stop()
        monitor.done.wait(3.0)
        thread.quit()
        thread.wait(3000)

    def restart_monitor(self) -> None:
        """เรียกหลังเปลี่ยนค่าตั้งการเชื่อมต่อ"""
        if not self.is_running:
            self.stop_monitor()
            self.sample_period_s = None
            self.start_monitor()

    @Slot(float)
    def _on_sample_period(self, seconds: float) -> None:
        self.sample_period_s = seconds

    # ------------------------------------------------------------- internals
    def _prepare_settings(self, config: SessionConfig) -> tuple[EngineSettings, str, str, GravimetricCorrection]:
        """ค่าคำนวณของขั้นนี้ (สำเนา) + ที่มาของความหนาแน่น + ที่มาของขนาดหน้าต่าง + ค่าแก้ g -> ml"""
        engine = dataclasses.replace(self.settings.engine)
        baseline = self.baseline_today()
        correction = gravimetric_correction(config.job, engine, baseline.rate_g_per_h if baseline else 0.0,
                                            baseline.measured_at if baseline else "")
        engine.density_g_per_ml = correction.water_density_g_per_ml
        engine.ml_per_g = correction.ml_per_g
        engine.baseline_g_per_h = correction.baseline_g_per_h
        density_source = correction.water_density_source
        if density_source == "temperature":
            log.info(tr("Density {rho:.4f} g/ml from {temp:g} °C", rho=engine.density_g_per_ml,
                        temp=config.job.temperature_c))
        if correction.air_buoyancy:
            log.info(tr("Air density {rho:.4f} kg/m³ ({t:g} °C, {rh:g} %RH, {p:g} hPa) · Z = {z:.5f} ml/g",
                        rho=correction.air_density_g_per_ml * 1000.0, t=correction.air_temp_c,
                        rh=correction.humidity_pct, p=correction.pressure_hpa, z=correction.ml_per_g))
        for warning in correction.warnings:
            log.warning(tr(warning))
        if baseline:
            log.info(tr("Using today's self-check: baseline {rate:+.1f} mg/h", rate=baseline.rate_g_per_h * 1000.0))

        # เกณฑ์ "flow นิ่ง" ของกลุ่ม ชนิดเครื่อง x วิธีจับ (หรือค่าเฉพาะรุ่น) + คาบที่รู้ล่วงหน้า
        criteria, group, specific = self.prerun_criteria_for(config.job, config.strategy)
        engine.stability_pct, engine.stability_blocks = criteria.stability_pct, criteria.blocks
        engine.stability_window_s, engine.stability_block_mode = criteria.block_s, criteria.block_mode
        engine.stability_block_cycles, engine.stability_min_block_mg = criteria.block_cycles, criteria.min_block_mg
        engine.stability_align_cycle, engine.stability_max_wait_s = criteria.align_to_cycle, criteria.max_wait_min * 60.0
        engine.stability_source = ("model:" if specific else "settings:") + group
        job = config.job
        engine.expected_period_s = self.repository.expected_period(
            job.brand, job.model, job.accessory, config.target_flow, job.pump_type.value) or 0.0
        if config.start_mode.value == "auto":
            log.info(tr("Stable-flow criteria: {group} ({source})", group=tr(PRERUN_GROUP_NAMES[group]),
                        source=tr("this model") if specific else tr("defaults")))

        engine.window_mode, window_source = "manual", "manual"
        if STRATEGIES.get(config.strategy).uses_cycles and config.window_source != "manual":
            job, points, half, period, source = config.job, 0, 0, None, ""
            # หน้าต่างของ rate นี้ (แยก regression / n_bar และแยกราย rate): ปรับจากข้อมูลย้อนหลังของรุ่นนี้ ถ้ามี
            r, h, fit = self.repository.window_fractions(job.brand, job.model, job.accessory, config.target_flow,
                                                         (engine.auto_window_fraction, engine.half_fraction),
                                                         job.pump_type.value)
            engine.auto_window_fraction, engine.auto_half_fraction = r, h
            engine.window_fit = fit
            if fit != "default":
                log.info(tr("Windows for {rate:g} ml/h ({fit}): regression {r:.2f} × cycle, n̄ {h:.2f} × cycle",
                            rate=config.target_flow, fit=tr(WINDOW_FITS[fit]), r=r, h=h))
            # แผน "Calibration ใหม่": ขั้นแรกวัดคาบก่อนเริ่ม (ไม่ใช้ข้อมูลเดิม) — ล้างแล้วจึงใช้ค่าที่เรียนรู้ใหม่
            use_profile = config.window_source == "profile" or (
                config.window_source == "recalibrate" and config.job_id in self._recalibrated)
            if use_profile and self.sample_period_s:
                period, source = self.repository.expected_period_info(job.brand, job.model, job.accessory,
                                                                      config.target_flow, job.pump_type.value)
                if period:
                    points = round(period * r / self.sample_period_s)
                    half = round(period * h / self.sample_period_s)
            if points >= 5:
                engine.regression_window, engine.cycle_half_window = max(10, points), max(5, half)
                window_source = "model_default" if source == "model_default" else "profile"
                if source == "model_default":
                    log.info(tr("Window sizes from this model's default volume per cycle (not measured yet): "
                                "{n} points (cycle about {p:.1f} s)", n=points, p=period))
                else:
                    log.info(tr("Window sizes {rate:g} ml/h: regression {n} pts, n̄ {h} pts (cycle about {p:.1f} s)",
                                rate=config.target_flow, n=engine.regression_window, h=engine.cycle_half_window,
                                p=period))
            else:
                engine.window_mode, window_source = "auto", "measured"
        return engine, density_source, window_source, correction

    def _start_test(self, config: SessionConfig) -> bool:
        try:
            engine_settings, density_source, window_source, correction = self._prepare_settings(config)
            engine = FlowEngine(config, engine_settings, density_source, window_source,
                                correction=dataclasses.asdict(correction))
            folder = self.repository.new_session_folder(engine.started_at, config.job.pump_type.value, config.target_flow)
        except Exception as exc:
            log.error(tr("Cannot start the test: {error}", error=exc))
            self._set_state(SessionState.ERROR)
            return False
        log.info(tr("Step {i}/{n} started: target {rate:g} ml/h, tolerance ±{tol:g}%",
                    i=config.step_index + 1, n=config.step_count,
                    rate=config.target_flow, tol=config.tolerance_pct))
        self._folder = folder
        if not self._launch(engine, config, RawRecorder(folder)):
            self.repository.discard_folder(folder)
            self._folder = None
            return False
        self.session_started.emit(config)
        return True

    def _launch(self, engine, config: SessionConfig, recorder: RawRecorder | None) -> bool:
        self.stop_monitor()                             # ปล่อยพอร์ตให้การทดสอบจริง
        self.tuner.cancel()                             # ไม่แย่งเวลาประมวลผลกับการอ่านตราชั่ง
        try:
            source = SOURCES.create(self.settings.source, self.settings, config)
        except Exception as exc:
            log.error(tr("Cannot start the test: {error}", error=exc))
            self._set_state(SessionState.ERROR)
            self.start_monitor()
            return False
        self._engine = engine
        self._pending.clear()
        self._worker = AcquisitionWorker(source, engine, recorder)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.result.connect(self._on_result)
        self._worker.finished.connect(self._on_worker_finished)
        self._set_state(SessionState.RUNNING)
        self._flush_timer.start(self.settings.ui.refresh_ms)
        self._thread.start()
        return True

    @Slot(object)
    def _on_result(self, result) -> None:
        self._pending.append(result)

    @Slot()
    def _flush(self) -> None:
        if self._pending:
            batch, self._pending = self._pending, []
            self.results_ready.emit(batch)

    @Slot(str)
    def _on_worker_finished(self, reason: str) -> None:
        self._finalize(reason)

    def _finalize(self, reason: str, closing: bool = False) -> None:
        if self._worker is None:        # จบไปแล้ว (กันเรียกซ้ำ)
            return
        thread, engine = self._thread, self._engine
        self._worker = self._thread = None
        self._flush_timer.stop()
        thread.quit()
        thread.wait(3000)
        self._flush()
        self._set_state(_END_STATES.get(reason, SessionState.ERROR))

        if isinstance(engine, BaselineEngine):
            self._finish_self_check(engine, reason)
        else:
            self._finish_test(engine, reason, closing)
        if not closing:
            self.start_monitor()

    def _finish_self_check(self, engine: BaselineEngine, reason: str) -> None:
        self._engine = None
        result = None
        if reason == "completed" and len(engine.samples) >= 20:     # ถูกยกเลิกกลางคัน = ไม่บันทึก
            result = engine.result()
            self.repository.add_self_check(result)
            log.info(tr("Self-check {verdict}: baseline {rate:+.1f} ± {se:.1f} mg/h, noise {sd:.2f} mg",
                        verdict=tr("passed") if result.passed else tr("did not pass"),
                        rate=result.rate_g_per_h * 1000.0, se=result.se_g_per_h * 1000.0,
                        sd=result.noise_sd_g * 1000.0))
        self.plan_changed.emit()
        self.self_check_finished.emit(result)

    def _finish_test(self, engine: FlowEngine, reason: str, closing: bool) -> None:
        summary = engine.summary(reason, source=self.settings.source)
        if reason == "completed":
            log.info(tr("Step finished: {verdict} (error {error:+.2f}%)",
                        verdict=summary.verdict.value, error=summary.error_pct or 0.0))
        elif reason == "stopped":
            log.info(tr("Test stopped by user"))

        has_data = bool(engine.samples)
        if closing or not has_data:     # ไม่มีอะไรให้ตัดสิน: ลบทิ้งเลย
            if self._folder is not None:
                self.repository.discard_folder(self._folder)
            self._engine = self._folder = None
            self.plan_changed.emit()
            if not closing:
                self.session_finished.emit(summary, False)
            return
        self.pending_summary = summary
        self.plan_changed.emit()
        self.review_requested.emit(summary)

    def _set_state(self, state: SessionState) -> None:
        self.state = state
        self.state_changed.emit(state)
