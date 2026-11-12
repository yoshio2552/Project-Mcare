"""แผงซ้ายของหน้าทดสอบ: แผนทดสอบ (PlanPanel) + สถานะตราชั่ง (BalanceCard)

ทั้งสองตัวแค่แสดงผลและส่ง signal — ไม่รู้จัก engine
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from config.i18n import tr
from config.settings import AppSettings
from core.models import EndMode, SessionState, Verdict
from core.strategies import STRATEGIES
from ui.icons import Glyph, glyph_icon
from ui.theme import Color, set_tone
from ui.widgets.common import Card, StatusPill, divider, fmt, int_box, label

MODE_TITLES = {"calibration": "Calibration", "inspection": "Inspection", "quick_test": "Quick Test"}


class PlanPanel(Card):
    new_requested = Signal()
    start_requested = Signal()
    stop_requested = Signal()
    window_changed = Signal(int)

    def __init__(self, settings: AppSettings):
        super().__init__(tr("Test plan"))
        self.btn_new = QPushButton(tr("New test"))
        self.btn_new.setProperty("variant", "ghost")
        self.header.addWidget(self.btn_new)

        # ---- ตอนยังไม่มีแผน: ปุ่มใหญ่ชัดๆ ปุ่มเดียว
        self._empty = QWidget()
        empty = QVBoxLayout(self._empty)
        empty.setContentsMargins(0, 4, 0, 4)
        empty.setSpacing(10)
        self.btn_create = QPushButton("＋  " + tr("New test"))
        self.btn_create.setProperty("variant", "hero")
        hint = label(tr("Enter the device details, choose a mode, then set up the measurement."), "pageSubtitle")
        hint.setWordWrap(True)
        empty.addWidget(self.btn_create)
        empty.addWidget(hint)
        self.body.addWidget(self._empty)

        # ---- ตอนมีแผนแล้ว
        self._plan = QWidget()
        plan = QVBoxLayout(self._plan)
        plan.setContentsMargins(0, 0, 0, 0)
        plan.setSpacing(10)
        self._device = label("", "metricValue")
        self._device.setWordWrap(True)
        self._mode = label("", "pageSubtitle")
        self._mode.setWordWrap(True)
        self._info = label("", "hint")
        self._info.setWordWrap(True)
        plan.addWidget(self._device)
        plan.addWidget(self._mode)
        plan.addWidget(self._info)
        plan.addWidget(divider())
        self._steps = QVBoxLayout()
        self._steps.setSpacing(6)
        plan.addLayout(self._steps)
        plan.addWidget(divider())

        window_row = QHBoxLayout()
        self.window = int_box(30, 3600, settings.ui.rolling_window_s, " s", step=30)
        self.window.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        window_row.addWidget(label(tr("Graph window"), "fieldLabel"))
        window_row.addWidget(self.window, 1)
        plan.addLayout(window_row)

        self.btn_start = QPushButton()
        self.btn_start.setProperty("variant", "primary")
        self.btn_start.setIcon(glyph_icon(Glyph.PLAY, Color.ON_ACCENT, disabled_color=Color.TEXT_FAINT, size=16))
        self.btn_stop = QPushButton("  " + tr("Stop"))
        self.btn_stop.setProperty("variant", "danger")
        self.btn_stop.setIcon(glyph_icon(Glyph.STOP, Color.DANGER, disabled_color=Color.TEXT_FAINT, size=16))
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.btn_start, 2)
        buttons.addWidget(self.btn_stop, 1)
        plan.addLayout(buttons)
        self.body.addWidget(self._plan)

        for button in (self.btn_start, self.btn_stop, self.btn_new, self.btn_create):
            button.setIconSize(QSize(16, 16))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self.new_requested)
        self.btn_create.clicked.connect(self.new_requested)
        self.btn_start.clicked.connect(self.start_requested)
        self.btn_stop.clicked.connect(self.stop_requested)
        self.window.valueChanged.connect(self.window_changed)

    def refresh(self, controller) -> None:
        """วาดแผงใหม่ตามสถานะปัจจุบันของ controller"""
        plan, state = controller.plan, controller.state
        running = controller.is_running
        busy = running or controller.awaiting_review
        self._empty.setVisible(plan is None)
        self._plan.setVisible(plan is not None)
        self.btn_new.setVisible(plan is not None)
        self.btn_new.setEnabled(not busy)
        self.btn_create.setEnabled(not busy)
        if plan is None:
            return

        while self._steps.count():
            item = self._steps.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)      # หายจากจอทันที ไม่รอ event loop
                widget.deleteLater()

        strategy = STRATEGIES.get(plan.strategy)
        method = tr(dict(STRATEGIES.choices())[plan.strategy])
        pump = tr("Infusion pump") if plan.job.pump_type.value == "infusion" else tr("Syringe pump")
        self._device.setText(plan.job.device_label or pump)
        self._mode.setText(f"{tr(MODE_TITLES[plan.run_mode.value])}  ·  {pump}\n{method}  ·  ± {plan.tolerance_pct:g} %")
        self._info.setText("\n".join(self._info_lines(controller, strategy)))

        by_count = plan.end_mode is EndMode.COUNT and "count" in strategy.end_modes
        results, step_index = controller.step_results, controller.step_index
        for index, step in enumerate(plan.steps):
            length = f"{step.cycle_count} {tr('cycles')}" if by_count else f"{step.duration_min:g} min"
            if index < len(results):
                summary = results[index]
                tone = "success" if summary.verdict is Verdict.PASS else "danger"
                status = f"{summary.verdict.value}  {fmt(summary.error_pct, 2, ' %', signed=True)}"
            elif index == step_index and running:
                tone, status = "accent", tr("Running")
            elif index == step_index and controller.awaiting_review:
                tone, status = "accent", tr("Keep?")
            else:
                tone, status = "neutral", ""
            self._steps.addWidget(self._step_row(index + 1, f"{step.target_flow:g} ml/h  ·  {length}", status, tone))

        done = step_index >= len(plan.steps)
        if done:
            self.btn_start.setText("  " + tr("All steps done"))
        else:
            self.btn_start.setText("  " + tr("Start {i}/{n} · {rate:g} ml/h", i=step_index + 1,
                                             n=len(plan.steps), rate=plan.steps[step_index].target_flow))
        self.btn_start.setEnabled(controller.can_start)
        self.btn_stop.setEnabled(state is SessionState.RUNNING)

    @staticmethod
    def _info_lines(controller, strategy) -> list[str]:
        """บรรทัดบอกว่าการทดสอบนี้จะใช้ค่าแก้/โปรไฟล์อะไร"""
        plan, lines = controller.plan, []
        if strategy.uses_cycles:
            profile = controller.profile_for(plan)
            if plan.window_source == "manual":
                lines.append(tr("Window sizes: manual (Settings)"))
            elif plan.window_source == "profile" and profile and profile.runs:
                lines.append(tr("Pump profile: {ml:.3f} ml per cycle ({n} runs)",
                                ml=profile.stroke_volume_ml, n=profile.runs))
            else:
                lines.append(tr("Pump cycle is measured before each rate"))
        correction = controller.correction_for(plan)
        if correction is not None:
            if correction.water_density_source == "temperature":
                lines.append(tr("Density {rho:.5f} g/ml from {temp:g} °C", rho=correction.water_density_g_per_ml,
                                temp=correction.liquid_temp_c))
            else:
                lines.append(tr("Density {rho:.5f} g/ml from Settings (no liquid temperature)",
                                rho=correction.water_density_g_per_ml))
            if correction.air_buoyancy:
                lines.append(tr("g → ml: Z = {z:.5f} ml/g (ISO 4787, {t:g} °C · {rh:g} %RH · {p:g} hPa)",
                                z=correction.ml_per_g, t=correction.air_temp_c, rh=correction.humidity_pct,
                                p=correction.pressure_hpa))
            else:
                lines.append(tr("g → ml: 1/density = {z:.5f} ml/g (air buoyancy off)", z=correction.ml_per_g))
        baseline = controller.baseline_today()
        if baseline is not None:
            lines.append(tr("Self-check correction: {rate:+.1f} mg/h", rate=baseline.rate_g_per_h * 1000.0))
        return lines

    @staticmethod
    def _step_row(number: int, text: str, status: str, tone: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        badge = label(str(number), "stepIndex")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_tone(badge, tone)
        status_label = label(status, "metricValue")
        status_label.setStyleSheet(f"color: {dict(success=Color.SUCCESS, danger=Color.DANGER, accent=Color.ACCENT).get(tone, Color.TEXT_MUTED)};")
        layout.addWidget(badge)
        layout.addWidget(label(text))
        layout.addStretch()
        layout.addWidget(status_label)
        return row


class BalanceCard(Card):
    """น้ำหนักสดจากตราชั่ง + สถานะการเชื่อมต่อ + self-check"""
    self_check_requested = Signal()

    def __init__(self):
        super().__init__(tr("Balance"))
        self.pill = StatusPill(tr("CONNECTING…"), "neutral")
        self.header.addWidget(self.pill)
        self.body.setSpacing(4)

        weight_row = QHBoxLayout()
        self._weight = label("—", "weight")
        self._stable = label("", "hint")
        weight_row.addWidget(self._weight)
        weight_row.addWidget(self._stable, alignment=Qt.AlignmentFlag.AlignBottom)
        weight_row.addStretch()
        self.body.addLayout(weight_row)
        self._detail = label("", "hint")
        self._detail.setWordWrap(True)
        self.body.addWidget(self._detail)

        check_row = QHBoxLayout()
        self._baseline = label("", "hint")
        self._baseline.setWordWrap(True)
        self.btn_self_check = QPushButton(tr("Self-check"))
        self.btn_self_check.setToolTip(tr("Measure evaporation and balance drift with the pump stopped"))
        self.btn_self_check.setCursor(Qt.CursorShape.PointingHandCursor)
        check_row.addWidget(self._baseline, 1)
        check_row.addWidget(self.btn_self_check)
        self.body.addSpacing(4)
        self.body.addLayout(check_row)
        self.btn_self_check.clicked.connect(self.self_check_requested)

    @Slot(bool, str)
    def set_status(self, connected: bool, text: str) -> None:
        if connected:
            self.pill.set(tr("CONNECTED"), "success")
            self._detail.setText(text)
        else:
            self.pill.set(tr("NOT CONNECTED"), "danger")
            self._detail.setText(tr("No data from the balance") if text == "no data" else text)
            self._weight.setText("—")
            self._stable.setText("")

    @Slot(float, object)
    def set_reading(self, weight: float, stable=None) -> None:
        self._weight.setText(f"{weight:.4f} g")
        self._stable.setText("" if stable is None else tr("stable") if stable else tr("unstable"))

    def set_in_test(self) -> None:
        self.pill.set(tr("IN TEST"), "accent")

    def set_baseline(self, result, busy: bool) -> None:
        """result = SelfCheckResult ล่าสุดของวันนี้ (หรือ None)"""
        self.btn_self_check.setEnabled(not busy)
        if result is None:
            self._baseline.setText(tr("No self-check today"))
        elif result.passed:
            self._baseline.setText(tr("Self-check today: {rate:+.1f} mg/h", rate=result.rate_g_per_h * 1000.0))
        else:
            self._baseline.setText(tr("Self-check today did not pass"))
