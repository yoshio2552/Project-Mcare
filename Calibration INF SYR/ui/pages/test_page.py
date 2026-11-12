"""หน้าทดสอบ (Test): แผนทดสอบ + ผลแบบ real-time (การ์ดสรุป กราฟ log)

หน้านี้แค่ "ประกอบชิ้นส่วน" และกระจายผลลัพธ์จาก SessionController ไปยังการ์ด/กราฟ
- เพิ่ม/สลับกราฟ: แก้ PLOT_GRID
- เพิ่มตัวเลขบนการ์ด: แก้ _build_cards และ _update_cards
- ข้อความบอกสถานะแต่ละช่วง: แก้ _update_banner
- แถบติดตามขั้น/ช่วง (ProcessTracker): แก้ _STAGE_PHASES
"""
from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QApplication, QDialog, QGridLayout, QHBoxLayout, QMessageBox, QVBoxLayout, QWidget,
)

from config.i18n import tr
from config.settings import AppSettings
from core.models import (
    EngineResult, SessionConfig, SessionState, SessionSummary, Stage, Verdict,
)
from core.strategies import STRATEGIES
from services.logging_setup import LogBridge
from services.session_controller import SessionController
from ui.dialogs.result_review import ResultReviewDialog
from ui.dialogs.test_wizard import TestWizard
from ui.plots import CumulativePlot, IntervalPlot, PlotModule, SlopePlot, WeightPlot
from ui.plots.cell import PlotCell
from ui.theme import Color
from ui.widgets.common import StatusPill, fmt, fmt_clock, label
from ui.widgets.log_panel import LogPanel
from ui.widgets.plan_panel import MODE_TITLES, BalanceCard, PlanPanel
from ui.widgets.process_tracker import ProcessTracker
from ui.widgets.stat_card import StatCard

# (คลาสกราฟ, แถว, คอลัมน์) — จัดผังกราฟที่นี่
PLOT_GRID = [
    (CumulativePlot, 0, 0), (IntervalPlot, 0, 1),
    (SlopePlot, 1, 0), (WeightPlot, 1, 1),
]

# ช่วงของการวัดที่แสดงบนแถบติดตาม
_STAGE_PHASES = {
    Stage.PRERUN: "Pre-run", Stage.WARMUP: "Prepare", Stage.SEARCHING: "First cycle", Stage.MEASURING: "Measure",
}
SELF_CHECK_PHASES = ["Connect", "Self-check", "Result"]

_STATE_PILLS = {
    SessionState.IDLE: ("READY", "neutral"),
    SessionState.RUNNING: ("RUNNING", "accent"),
    SessionState.STOPPING: ("STOPPING…", "warning"),
    SessionState.COMPLETED: ("COMPLETED", "success"),
    SessionState.STOPPED: ("STOPPED", "warning"),
    SessionState.ERROR: ("ERROR", "danger"),
}


class TestPage(QWidget):
    def __init__(self, settings: AppSettings, controller: SessionController, log_bridge: LogBridge):
        super().__init__()
        self.setObjectName("page")
        self._settings = settings
        self._controller = controller
        self._config: SessionConfig | None = None
        self._stage: Stage | None = None
        self._self_check_s = 0.0            # > 0 ระหว่างทำ self-check

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        # ------------------------------------------------ คอลัมน์ซ้าย
        left_widget = QWidget()
        left_widget.setFixedWidth(310)
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(14)
        self.plan_panel = PlanPanel(settings)
        self.balance = BalanceCard()
        self.log_panel = LogPanel()
        left.addWidget(self.plan_panel)
        left.addWidget(self.balance)
        left.addWidget(self.log_panel, 1)
        root.addWidget(left_widget)

        # ------------------------------------------------ คอลัมน์ขวา
        right = QVBoxLayout()
        right.setSpacing(10)
        root.addLayout(right, 1)

        # หัวเพจบรรทัดเดียว: ชื่อ · รายละเอียดการทดสอบ · เวลา · สถานะ (เตี้ย เพื่อเหลือที่ให้กราฟ)
        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(label(tr("Test"), "pageTitle"))
        self.subtitle = label(tr("Create a test on the left, then press Start"), "pageSubtitle")
        header.addWidget(self.subtitle, 1)
        self.clock = label("00:00:00", "clock")
        self.pill = StatusPill()
        header.addWidget(self.clock)
        header.addWidget(self.pill)
        right.addLayout(header)

        # แถบติดตามขั้น/ช่วง + ข้อความสถานะและปุ่มลัด (แทนแถบข้อความเดิม)
        self.tracker = ProcessTracker()
        self.progress = self.tracker.progress
        self.banner = self.tracker
        right.addWidget(self.tracker)
        right.addLayout(self._build_cards())
        right.addWidget(self._build_plots(), 1)

        # ------------------------------------------------ เชื่อมต่อ
        self.plan_panel.new_requested.connect(self.open_wizard)
        self.plan_panel.start_requested.connect(controller.start_step)
        self.plan_panel.stop_requested.connect(self._on_stop_requested)
        self.plan_panel.window_changed.connect(self._on_window_changed)
        self.balance.self_check_requested.connect(self._on_self_check_requested)
        self.banner.action_clicked.connect(self._on_banner_action)
        controller.plan_changed.connect(self._refresh_plan)
        controller.session_started.connect(self._on_session_started)
        controller.results_ready.connect(self._on_results)
        controller.state_changed.connect(self._on_state_changed)
        controller.review_requested.connect(self._on_review_requested)
        controller.session_finished.connect(self._on_session_finished)
        controller.self_check_started.connect(self._on_self_check_started)
        controller.self_check_finished.connect(self._on_self_check_finished)
        controller.balance_status.connect(self.balance.set_status)
        controller.live_reading.connect(self.balance.set_reading)
        log_bridge.message.connect(self.log_panel.append)
        self._on_state_changed(controller.state)

    # ------------------------------------------------------------ สร้าง UI
    def _build_cards(self) -> QHBoxLayout:
        self.card_error = StatCard(tr("Flow error"), unit="%", metrics=[
            ("flow", tr("Mean flow")), ("sd", "2 SD"),
        ])
        self.card_live = StatCard(tr("Live average"), unit="ml/h", metrics=[
            ("a", tr("Chain A"), Color.SERIES_A), ("b", tr("Chain B"), Color.SERIES_B), ("last", tr("Last interval")),
        ])
        self.card_timing = StatCard(tr("Cycle timing"), unit="s", metrics=[
            ("last", tr("Last cycle")), ("sd", "2 SD"),
        ])
        self.card_result = StatCard(tr("Result"), metrics=[
            ("target", tr("Target")), ("tolerance", tr("Tolerance")), ("count", tr("Intervals")),
        ])
        row = QHBoxLayout()
        row.setSpacing(10)
        self._cards = (self.card_error, self.card_live, self.card_timing, self.card_result)
        for card in self._cards:
            row.addWidget(card, 1)
        return row

    def _build_plots(self) -> QWidget:
        """1 กราฟ = 1 ช่อง (PlotCell): หัวกราฟแบบ Qt (ชื่อเส้นกดซ่อนได้ + ปุ่มรูปแบบ) + กราฟ"""
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        self.plots: list[PlotModule] = []
        for cls, row, col in PLOT_GRID:
            cell = PlotCell(cls, self._settings.ui)
            cell.module.on_option_changed = self._save_settings
            grid.addWidget(cell, row, col)
            self.plots.append(cell.module)
        for index in range(2):
            grid.setRowStretch(index, 1)
            grid.setColumnStretch(index, 1)
        return container

    def _save_settings(self) -> None:
        """ตัวเลือกข้างกราฟถูกจำไว้ใน settings.json ทันที"""
        try:
            self._settings.save()
        except OSError:
            pass

    # ------------------------------------------------------------- แผนทดสอบ
    def open_wizard(self) -> None:
        c = self._controller
        if c.is_running or c.awaiting_review:
            return
        wizard = TestWizard(self, c.repository, self._settings, c.plan)
        if wizard.exec() == QDialog.DialogCode.Accepted and wizard.plan is not None:
            c.set_plan(wizard.plan)
            self._config = None
            self.tracker.start(self.tracker.TEST_PHASES, running=False)
            self._refresh_plan()
            self.banner.show_message(
                tr("Test created. Set the pump to {rate:g} ml/h, start it, then press Start.",
                   rate=wizard.plan.steps[0].target_flow), "accent")

    @Slot()
    def _refresh_plan(self) -> None:
        c = self._controller
        self.plan_panel.refresh(c)
        self.balance.set_baseline(c.repository.latest_self_check(), busy=c.is_running or c.awaiting_review)
        # ยังไม่เริ่มขั้นใดหลังสร้างแผน: แถบติดตามบอกขั้นที่จะเริ่ม
        if self._config is None and not c.is_running and not c.awaiting_review:
            if c.plan is None:
                self.tracker.set_plan_step(None, None)
            elif c.has_next_step:
                step = c.plan.steps[c.step_index]
                self.tracker.set_plan_step(c.step_index, len(c.plan.steps), f"{step.target_flow:g} ml/h")

    def _on_stop_requested(self) -> None:
        if self._settings.ui.confirm_stop:
            answer = QMessageBox.question(
                self, tr("Stop the test?"),
                tr("The test is not finished. Stop it now?"),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._controller.stop()

    # ---------------------------------------------------------------- การทดสอบ
    @Slot(object)
    def _on_session_started(self, config: SessionConfig) -> None:
        self._config = config
        self._stage = None
        self._self_check_s = 0.0
        uses_cycles = STRATEGIES.get(config.strategy).uses_cycles
        method = tr(dict(STRATEGIES.choices())[config.strategy])
        parts = [tr(MODE_TITLES[config.run_mode.value]),
                 tr("Step {i}/{n}", i=config.step_index + 1, n=config.step_count),
                 f"{config.target_flow:g} ml/h", method, config.job.device_label]
        self.subtitle.setText("  ·  ".join(part for part in parts if part))
        self.card_timing.setVisible(uses_cycles)
        chains = self._settings.engine.cycle_chains if uses_cycles else 1
        for plot in self.plots:
            plot.set_chains(chains)
        self.card_live.set_metric_visible("b", chains == 2)
        self.tracker.set_plan_step(config.step_index, config.step_count, f"{config.target_flow:g} ml/h")
        self.tracker.start(self.tracker.TEST_PHASES)
        self.balance.set_in_test()
        self._reset_measurement_view()
        self.banner.show_message(tr("Connecting to the balance…"))

    def _reset_measurement_view(self) -> None:
        """ล้างการ์ด/กราฟ — ใช้ตอนเริ่ม session และตอนเปลี่ยนจาก pre-run เป็นวัดจริง"""
        config = self._config
        self.clock.setText("00:00:00")
        self.progress.setValue(0)
        for card in self._cards:
            card.reset()
        if config.target_flow > 0:
            self.card_result.set("target", fmt(config.target_flow, 1, " ml/h"))
            self.card_result.set("tolerance", fmt(config.tolerance_pct, 1, " %", prefix="± "))
            self.card_result.set("count", "0")
        for plot in self.plots:
            plot.begin_session(config)

    @Slot(list)
    def _on_results(self, results: list[EngineResult]) -> None:
        last = results[-1]
        self.balance.set_reading(last.weight)
        self.clock.setText(fmt_clock(last.t))
        self.progress.setValue(int(last.progress * 1000))
        if self._self_check_s > 0:                      # self-check: ดูแค่น้ำหนัก
            self.tracker.set_phase("Self-check")
            self.plots[-1].feed(results)
            remaining = max(0.0, self._self_check_s - last.t)
            self.banner.show_message(
                tr("Self-check — pump stopped, do not touch the beaker · {time} left", time=fmt_clock(remaining)[3:]),
                "warning", tr("Cancel"))
            return

        # ถ้าในชุดนี้มีจุดเริ่มวัดจริง: ล้างจอ แล้ววาดเฉพาะส่วนของการวัดจริง
        start = next((i for i, r in enumerate(results) if r.measurement_started), None)
        if start is not None:
            self._reset_measurement_view()
            results = results[start:]
        for plot in self.plots:
            plot.feed(results)
        self._update_cards(results)
        self._update_banner(last)

    def _on_banner_action(self) -> None:
        if self._self_check_s > 0:
            self._controller.stop()
        else:
            self._controller.begin_measurement()

    def _update_banner(self, result: EngineResult) -> None:
        stage, button = result.stage, tr("Start measuring now")
        if stage in _STAGE_PHASES:
            self.tracker.set_phase(_STAGE_PHASES[stage])
        if stage is Stage.PRERUN and result.prerun is not None:
            status = result.prerun
            if status.countdown_s is not None:
                text = tr("Pre-run — measurement starts in {time}", time=fmt_clock(status.countdown_s)[3:])
            elif status.waiting_user:
                text = tr("Pre-run — watch the graphs, then press Start measuring when the pump is ready")
            elif status.tuning and status.variation_pct is None and self._config.start_mode.value == "immediate":
                text = tr("Pre-run")
            else:
                text = tr("Pre-run — waiting for stable flow (variation {v} / limit {limit} %)",
                          v=fmt(status.variation_pct, 1, " %"), limit=fmt(status.limit_pct, 1))
            if status.tuning:
                text += "   ·   " + tr("measuring the pump cycle period…")
            elif status.period_s is not None:
                text += "   ·   " + tr("pump cycle {p:.1f} s", p=status.period_s)
            self.banner.show_message(text, "warning", button)
        elif stage is Stage.WARMUP:
            self.banner.show_message(tr("Preparing — filling the calculation window (about {s:.0f} s left)",
                                        s=result.eta_s or 0.0), "info")
        elif stage is Stage.SEARCHING:
            self.banner.show_message(tr("Waiting for the first complete pump cycle…"), "info")
        elif self._stage is not Stage.MEASURING:
            self.banner.clear_message()
        self._stage = stage

    def _update_cards(self, results: list[EngineResult]) -> None:
        cumulative = next((r.cumulative for r in reversed(results) if r.cumulative), None)
        stats = next((r.stats for r in reversed(results) if r.stats), None)
        interval = next((r.interval for r in reversed(results) if r.interval), None)
        tolerance = self._config.tolerance_pct

        if cumulative is not None and cumulative.best_flow is not None:
            self.card_live.set_hero(fmt(cumulative.best_flow, 3))
            self.card_live.set("a", fmt(cumulative.err_a, 2, " %", signed=True))
            self.card_live.set("b", fmt(cumulative.err_b, 2, " %", signed=True))

        if stats is not None and interval is not None:
            # ค่าที่ใช้ตัดสิน = ค่าเฉลี่ยของช่วงวัดที่ครบสมบูรณ์
            within = abs(stats.mean_error_pct) <= tolerance
            tone = "success" if within else "danger"
            self.card_error.set_hero(fmt(stats.mean_error_pct, 2, signed=True), tone)
            self.card_error.set("flow", fmt(stats.mean_flow, 3, " ml/h"))
            self.card_error.set("sd", fmt(stats.sd2_pct, 3, " %", prefix="± "))
            self.card_live.set("last", fmt(interval.flow, 3, " ml/h"))
            self.card_timing.set_hero(fmt(stats.mean_duration_s, 2))
            self.card_timing.set("last", fmt(interval.duration_s, 2, " s"))
            self.card_timing.set("sd", fmt(stats.sd2_duration_s, 2, " s", prefix="± "))
            self.card_result.set_hero(tr("IN TOLERANCE") if within else tr("OUT OF TOL."), tone)
            self.card_result.set("count", str(stats.count))

    @Slot(object)
    def _on_state_changed(self, state: SessionState) -> None:
        text, tone = _STATE_PILLS[state]
        self.pill.set(tr(text), tone)
        self._refresh_plan()

    # ------------------------------------------------------- เก็บ / ไม่เก็บ
    @Slot(object)
    def _on_review_requested(self, summary: SessionSummary) -> None:
        """จบ 1 ขั้น: แสดงผลแล้วถามว่าเก็บหรือไม่"""
        if summary.end_reason == "completed":
            self.progress.setValue(1000)
            if self._settings.ui.sound_on_finish:
                QApplication.beep()
        self._show_verdict(summary)
        self.tracker.set_phase("Review")
        self.banner.show_message(tr("Finished — choose whether to keep this result."), "accent")
        dialog = ResultReviewDialog(self, summary)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._controller.keep_result()
        else:
            self._controller.discard_result()

    def _show_verdict(self, summary: SessionSummary) -> None:
        if summary.verdict is Verdict.NONE:
            self.card_result.set_hero(tr("NO RESULT"), "muted")
            return
        passed = summary.verdict is Verdict.PASS
        text = summary.verdict.value if summary.end_reason == "completed" else f"{summary.verdict.value} ({tr('partial')})"
        self.card_result.set_hero(text, "success" if passed else "danger")

    @Slot(object, bool)
    def _on_session_finished(self, summary: SessionSummary, kept: bool) -> None:
        c = self._controller
        self._show_step_outcome(summary, kept)
        if summary.end_reason == "error":
            self.banner.show_message(tr("The test ended with an error — see the activity log."), "danger")
        elif not kept:
            self.banner.show_message(tr("Result not kept. Press Start to run this step again."), "warning")
        elif summary.end_reason != "completed":
            self.banner.show_message(tr("Incomplete result saved. Press Start to run this step again."), "warning")
        elif c.has_next_step:
            self.banner.show_message(
                tr("Step {i}/{n} saved. Set the pump to {rate:g} ml/h, then press Start.",
                   i=c.step_index, n=len(c.plan.steps), rate=c.plan.steps[c.step_index].target_flow), "accent")
        else:
            self.banner.show_message(tr("All steps are finished. Results are saved in History."), "success")

    def _show_step_outcome(self, summary: SessionSummary, kept: bool) -> None:
        """แถบติดตาม: จบขั้นแล้ว — บอกผลด้วยสี"""
        config = summary.config
        text = tr("Step {i}/{n}", i=config.step_index + 1, n=config.step_count) + "  ·  "
        if summary.end_reason == "error":
            self.tracker.finish(text + tr("ended with an error"), "danger")
        elif not kept:
            self.tracker.finish(text + tr("result not kept"), "warning")
        elif summary.end_reason != "completed":
            self.tracker.finish(text + tr("incomplete result saved"), "warning")
        else:
            verdict = f"  ·  {summary.verdict.value}" if summary.verdict is not Verdict.NONE else ""
            self.tracker.finish(text + tr("saved") + verdict,
                                "danger" if summary.verdict is Verdict.FAIL else "success")

    # ----------------------------------------------------------- self-check
    def _on_self_check_requested(self) -> None:
        minutes = self._settings.selfcheck.duration_min
        answer = QMessageBox.question(
            self, tr("Self-check"),
            tr("Self-check measures how much the weight changes by itself (evaporation and balance drift).\n\n"
               "1. Set up the beaker exactly as for a test, with liquid in it.\n"
               "2. Stop the pump.\n"
               "3. Do not touch the bench for {min:g} minutes.\n\n"
               "If it passes, the measured rate is used to correct every test for the rest of today.\n\nStart now?",
               min=minutes),
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._controller.start_self_check()

    @Slot(float)
    def _on_self_check_started(self, duration_s: float) -> None:
        self._self_check_s = duration_s
        self._config = SessionConfig(target_flow=0.0, strategy="time_total")
        self.subtitle.setText(tr("Self-check"))
        self.tracker.set_caption(tr("Self-check"), tr("{m:g} min · pump stopped", m=duration_s / 60))
        self.tracker.start(SELF_CHECK_PHASES)
        self.balance.set_in_test()
        self._reset_measurement_view()

    @Slot(object)
    def _on_self_check_finished(self, result) -> None:
        self._self_check_s = 0.0
        self._config = None
        if result is None:
            self.tracker.finish(tr("Self-check was cancelled."), "warning")
            self.banner.show_message(tr("Self-check was cancelled."), "warning")
            return
        numbers = tr("Baseline {rate:+.1f} ± {se:.1f} mg/h · balance noise {sd:.2f} mg",
                     rate=result.rate_g_per_h * 1000.0, se=result.se_g_per_h * 1000.0, sd=result.noise_sd_g * 1000.0)
        self.tracker.set_phase("Result")
        self.tracker.finish(tr("Self-check passed") if result.passed else tr("Self-check did not pass"),
                            "success" if result.passed else "danger")
        if result.passed:
            self.banner.show_message(tr("Self-check passed — it will be applied to today's tests.") + "   " + numbers, "success")
        else:
            reasons = " · ".join(tr(reason) for reason in result.reasons)
            self.banner.show_message(tr("Self-check did not pass and will not be used.") + "   " + reasons + "   " + numbers, "danger")

    @Slot(int)
    def _on_window_changed(self, seconds: int) -> None:
        self._settings.ui.rolling_window_s = seconds
        for plot in self.plots:
            plot.set_window(seconds)
