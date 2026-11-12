"""SessionDetailDialog: เปิดดูผลการทดสอบย้อนหลัง 1 session (ข้อมูล + กราฟ)

ใช้โมดูลกราฟชุดเดียวกับ Dashboard โดยป้อนข้อมูลที่อ่านจากคลังผล
"""
from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from config.i18n import tr
from config.settings import AppSettings, UiSettings
from core.models import EngineResult, Interval, IntervalStats, SessionConfig
from core.strategies import STRATEGIES
from services.session_store import SessionDetail
from ui.plots import IntervalPlot, WeightPlot
from ui.plots.cell import PlotCell
from ui.theme import Color
from ui.widgets.common import Card, fmt, fmt_clock, label

MAX_PLOT_POINTS = 6000


def _text(value) -> str:
    return "—" if value in (None, "") else str(value)


class SessionDetailDialog(QDialog):
    def __init__(self, parent: QWidget, detail: SessionDetail):
        super().__init__(parent)
        summary = detail.summary
        config = summary.get("config", {})
        job = config.get("job", {})
        self._ref = summary.get("folder", "")
        self.setWindowTitle(tr("Test result"))
        self.resize(1180, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        verdict = str(summary.get("verdict", ""))
        title = QHBoxLayout()
        pump = tr("Syringe pump") if job.get("pump_type") == "syringe" else tr("Infusion pump")
        device = " ".join(str(part) for part in (job.get("brand"), job.get("model")) if part) or pump
        method = tr(dict(STRATEGIES.choices()).get(config.get("strategy"), _text(config.get("strategy"))))
        title.addWidget(label(f'{device}  ·  {config.get("target_flow", 0):g} ml/h', "pageTitle"))
        title.addStretch()
        verdict_label = label(verdict, "hero")
        verdict_label.setStyleSheet(f"color: {Color.SUCCESS if verdict == 'PASS' else Color.DANGER if verdict == 'FAIL' else Color.TEXT_MUTED};")
        title.addWidget(verdict_label)
        root.addLayout(title)

        body = QHBoxLayout()
        body.setSpacing(14)
        root.addLayout(body, 1)

        # ---- ข้อมูล
        info = QVBoxLayout()
        info.setSpacing(12)
        info.addWidget(self._section(tr("Result"), [
            (tr("Mean flow"), fmt(summary.get("mean_flow"), 3, " ml/h")),
            (tr("Flow error"), fmt(summary.get("error_pct"), 2, " %", signed=True)),
            ("2 SD", fmt(summary.get("sd2_pct"), 3, " %", prefix="± ")),
            (tr("Tolerance"), fmt(config.get("tolerance_pct"), 1, " %", prefix="± ")),
            (tr("Intervals"), _text(summary.get("interval_count"))),
            (tr("Duration"), fmt_clock(summary.get("duration_s", 0))),
            (tr("Status"), tr(str(summary.get("end_reason", "")).capitalize())),
        ]))
        info.addWidget(self._section(tr("Device"), [
            (tr("Pump type"), pump),
            (tr("Serial no."), _text(job.get("serial_no"))),
            (tr("Asset ID"), _text(job.get("asset_id"))),
            (tr("Department"), _text(job.get("department"))),
            (tr("Syringe / IV set"), _text(job.get("accessory"))),
            (tr("Accessories"), ", ".join(job.get("accessories") or []) or "—"),
            (tr("Parts replaced"), ", ".join(job.get("parts_replaced") or []) or "—"),
        ]))
        info.addWidget(self._section(tr("Test"), [
            (tr("Date"), _text(summary.get("started_at")).replace("T", "  ")),
            (tr("Job ID"), f'{_text(config.get("job_id"))}  ({config.get("step_index", 0) + 1}/{config.get("step_count", 1)})'),
            (tr("Method"), method),
            (tr("Operator"), _text(job.get("operator"))),
            (tr("Balance ID"), _text(job.get("balance_id"))),
            (tr("Temperature (°C)"), _text(job.get("temperature_c"))),
            (tr("Humidity (%RH)"), _text(job.get("humidity_pct"))),
            (tr("Notes"), _text(job.get("notes"))),
        ]))
        info.addStretch()
        info_widget = QWidget()
        info_widget.setLayout(info)
        info.setContentsMargins(0, 0, 0, 0)
        info_widget.setFixedWidth(340)
        body.addWidget(info_widget)

        # ---- กราฟ (ช่องเดียวกับหน้าทดสอบ: กดชื่อเส้นบนหัวกราฟเพื่อซ่อน/แสดง, สลับขั้นบันได/จุดได้)
        ui = UiSettings(max_points=MAX_PLOT_POINTS)
        try:            # เริ่มด้วยรูปแบบที่ผู้ใช้เลือกไว้บนหน้าทดสอบ (เปลี่ยนในหน้าต่างนี้ไม่บันทึกกลับ)
            saved = AppSettings.load().ui
            ui.interval_style = saved.interval_style
            ui.interval_moving_avg = saved.interval_moving_avg
            ui.interval_overall_mean = saved.interval_overall_mean
        except Exception:
            pass
        plot_config = SessionConfig(target_flow=float(config.get("target_flow", 1.0)),
                                    tolerance_pct=float(config.get("tolerance_pct", 5.0)))
        interval_cell = PlotCell(IntervalPlot, ui)
        weight_cell = PlotCell(WeightPlot, ui)
        interval_plot, weight_plot = interval_cell.module, weight_cell.module
        chains = 2 if any(row["chain"] == 1 for row in detail.intervals) else 1
        for plot in (interval_plot, weight_plot):
            plot.set_chains(chains)
            plot.begin_session(plot_config)

        mean = summary.get("mean_flow")
        stats = IntervalStats(len(detail.intervals), mean, 0, 0, 0, 0, 0, 0) if mean is not None else None
        interval_plot.feed([
            EngineResult(t=row["t"], weight=0.0, stats=stats, interval=Interval(
                row["index"], row["chain"], row["t"], row["duration_s"], row["flow"], row["error_pct"]))
            for row in detail.intervals
        ])
        step = max(1, len(detail.samples) // MAX_PLOT_POINTS)
        weight_plot.feed([EngineResult(t=t, weight=w) for t, w in detail.samples[::step]])
        charts = QVBoxLayout()
        charts.setSpacing(10)
        charts.addWidget(interval_cell, 3)
        charts.addWidget(weight_cell, 2)
        body.addLayout(charts, 1)

        # ---- ปุ่ม
        buttons = QHBoxLayout()
        open_folder = QPushButton(tr("Open data folder"))
        close = QPushButton(tr("Close"))
        buttons.addWidget(open_folder)
        buttons.addStretch()
        buttons.addWidget(close)
        root.addLayout(buttons)
        open_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._ref)))
        close.clicked.connect(self.accept)

    @staticmethod
    def _section(title: str, rows: list[tuple[str, str]]) -> Card:
        card = Card(title)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(1, 1)
        for index, (name, value) in enumerate(rows):
            value_label = label(value, "metricValue")
            value_label.setWordWrap(True)
            grid.addWidget(label(name, "metricName"), index, 0)
            grid.addWidget(value_label, index, 1)
        card.body.addLayout(grid)
        return card
