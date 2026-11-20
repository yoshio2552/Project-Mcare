"""ResultWorkspace: หน้าต่างดูผลย้อนหลังแบบมืออาชีพ (ผู้ใช้ 2026-11-20 — แทนหน้ารายละเอียดเดิมที่ "งง ไม่ละเอียด")

    ┌ [INFUSION] Terumo TE-171 · S/N 1709…                                   [ PASS ] ┐
    │ Calibration · งาน MCI-0142 · รพ.ขอนแก่น · 20 พ.ย. 2569 14:20                     │
    │ rate:  [10 ml/h ✓] [50 ml/h ✓] [200 ml/h ✗]       (งาน Calibration หลาย rate)       │
    ├ ภาพรวม │ กราฟ · เล่นซ้ำ │ เอกสาร │ งานและเครื่อง │ ข้อมูลการวัด │ คุณภาพและสอบย้อน ┤
    │ …                                                                                  │
    └ เปิดโฟลเดอร์ข้อมูล            ส่งออกการเล่นซ้ำ ▾   พิมพ์   บันทึก PDF   ปิด ┘
แท็บ "กราฟ · เล่นซ้ำ" = กราฟ 4 ช่องแบบหน้าทดสอบ สร้างจากไฟล์ของผล (services/replay_session.py) เล่นซ้ำ/เลื่อนได้
แท็บ "เอกสาร" = ใบรายงาน PDF ของงาน ณ ตอนนี้ (สร้างจากผลที่บันทึก) ซูม 67 %
ส่งออก: HTML เคลื่อนไหว (เปิดได้ทุกเบราว์เซอร์) · วิดีโอ MP4
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QMenu, QMessageBox,
    QPlainTextEdit, QProgressDialog, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QTabWidget, QToolButton,
    QVBoxLayout, QWidget,
)

from config.i18n import tr
from config.settings import AppSettings, UiSettings
from core.models import EngineResult, Interval, IntervalStats, SessionConfig, measured_seconds
from core.strategies import STRATEGIES
from services.session_store import get_repository, raw_result
from ui.icons import Glyph, glyph_icon
from ui.theme import Color
from ui.widgets.common import Card, fmt, fmt_duration, label
from ui.widgets.pump_type import PumpBadge

TABS = ("Overview", "Graphs · replay", "Document", "Job and device", "Measurement data", "Quality and audit")
_VERDICT = {"PASS": "SUCCESS", "FAIL": "DANGER", "INVALID": "WARNING"}


def _text(value) -> str:
    return "—" if value in (None, "", []) else str(value)


def _date(iso: str) -> str:
    from datetime import datetime
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d  %H:%M")
    except (TypeError, ValueError):
        return _text(iso)


def _section(title: str, rows: list[tuple[str, str]], wide_values: bool = True) -> Card:
    """การ์ด ชื่อ : ค่า (ค่ายาวตัดบรรทัด เลือกคัดลอกได้)"""
    card = Card(title)
    grid = QGridLayout()
    grid.setHorizontalSpacing(14)
    grid.setVerticalSpacing(5)
    grid.setColumnStretch(1, 1)
    for index, (name, value) in enumerate(rows):
        name_label = label(name, "metricName")
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        value_label = label(value, "metricValue")
        value_label.setWordWrap(wide_values)
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        grid.addWidget(name_label, index, 0)
        grid.addWidget(value_label, index, 1)
    card.body.addLayout(grid)
    return card


def _scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setWidget(widget)
    return area


class _Kpi(QFrame):
    def __init__(self, title: str, value: str, unit: str = "", note: str = "", color: str | None = None):
        super().__init__()
        self.setProperty("card", True)
        box = QVBoxLayout(self)
        box.setContentsMargins(14, 10, 14, 10)
        box.setSpacing(2)
        box.addWidget(label(title.upper(), "sectionTitle"))
        row = QHBoxLayout()
        row.setSpacing(4)
        value_label = label(value, "heroCompact")
        if color:
            value_label.setStyleSheet(f"color: {color};")
        row.addWidget(value_label)
        row.addWidget(label(unit, "heroUnit"), alignment=Qt.AlignmentFlag.AlignBottom)
        row.addStretch()
        box.addLayout(row)
        if note:
            box.addWidget(label(note, "hint"))


class _KpiRow(QWidget):
    """การ์ดตัวเลขหลัก 6 ใบ: จอกว้าง = แถวเดียว · จอแคบ = 2 แถว (ไม่ถูกตัด)"""

    def __init__(self):
        super().__init__()
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(10)
        self._items: list[QWidget] = []
        self._columns = 0

    def addWidget(self, widget: QWidget, _stretch: int = 0) -> None:
        self._items.append(widget)
        self._arrange(6)

    def _arrange(self, columns: int) -> None:
        if columns == self._columns and all(self._grid.indexOf(w) >= 0 for w in self._items):
            return
        self._columns = columns
        for widget in self._items:
            self._grid.removeWidget(widget)
        for index, widget in enumerate(self._items):
            self._grid.addWidget(widget, index // columns, index % columns)
        for column in range(6):
            self._grid.setColumnStretch(column, 1 if column < columns else 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._arrange(6 if event.size().width() >= 1100 else 3)


class ResultWorkspace(QDialog):
    def __init__(self, parent: QWidget | None, sessions: list[dict], repository=None, settings=None, on_report=None,
                 detail=None, start_ref: str | None = None):
        """sessions = ผลของงานเดียวกัน (Calibration หลาย rate) หรือผลเดียว · on_report(action) = "save" | "print" """
        super().__init__(parent)
        self.repository = repository or get_repository()
        self.settings = settings
        self.on_report = on_report
        self.members = sorted(sessions, key=lambda s: (float((s.get("config") or {}).get("target_flow") or 0),
                                                       s.get("started_at", "")))
        self._details: dict[str, object] = {}
        if detail is not None:
            self._details[str(detail.summary.get("ref", ""))] = detail
        self._replay = None
        self._replay_ref = None
        self._document_ref = None
        self.setWindowTitle(tr("Test result"))
        self.resize(1380, 880)
        from ui.dialogs.report_preview import fit_to_screen
        fit_to_screen(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 14)
        root.setSpacing(10)
        # ---- หัว: ชนิดเครื่อง ชื่อเครื่อง ผล
        head = QHBoxLayout()
        head.setSpacing(12)
        self.badge = PumpBadge()
        head.addWidget(self.badge, alignment=Qt.AlignmentFlag.AlignTop)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title = label("", "pageTitle")
        self.subtitle = label("", "pageSubtitle")
        self.subtitle.setWordWrap(True)
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        head.addLayout(titles, 1)
        self.verdict = QLabel("")
        self.verdict.setAlignment(Qt.AlignmentFlag.AlignCenter)
        head.addWidget(self.verdict, alignment=Qt.AlignmentFlag.AlignTop)
        root.addLayout(head)

        # ---- ตัวเลือก rate (งานหลาย rate)
        self.rate_bar = QHBoxLayout()
        self.rate_bar.setSpacing(0)
        self._rate_buttons: list[QPushButton] = []
        if len(self.members) > 1:
            self.rate_bar.addWidget(label(tr("Rate"), "fieldLabel"))
            self.rate_bar.addSpacing(10)
            for index, member in enumerate(self.members):
                button = QPushButton(self._rate_text(member))
                button.setProperty("variant", "segmentSmall")
                button.setProperty("position", "first" if index == 0 else "last" if index == len(self.members) - 1
                                   else "mid")
                button.setCheckable(True)
                button.setMinimumHeight(28)
                button.clicked.connect(lambda _=False, i=index: self.show_member(i))
                self._rate_buttons.append(button)
                self.rate_bar.addWidget(button)
            self.rate_bar.addStretch(1)
            root.addLayout(self.rate_bar)

        self.banner = label("", "pageSubtitle")
        self.banner.setWordWrap(True)
        self.banner.hide()
        root.addWidget(self.banner)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setProperty("tabsStyle", "settings")
        root.addWidget(self.tabs, 1)

        # ---- ปุ่มล่าง
        buttons = QHBoxLayout()
        self.btn_folder = QPushButton("  " + tr("Open data folder"))
        self.btn_folder.setIcon(glyph_icon(Glyph.FOLDER, Color.TEXT, size=14))
        buttons.addWidget(self.btn_folder)
        buttons.addStretch(1)
        self.btn_export = QToolButton()
        self.btn_export.setText("  " + tr("Export replay"))
        self.btn_export.setIcon(glyph_icon(Glyph.SHARE, Color.TEXT, size=14))
        self.btn_export.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_export.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.btn_export)
        menu.addAction(tr("Motion HTML (opens in any browser)…"), self.export_html)
        menu.addAction(tr("MP4 video…"), self.export_video)
        self.btn_export.setMenu(menu)
        buttons.addWidget(self.btn_export)
        self.btn_print = self.btn_pdf = None
        if on_report is not None and any((m.get("config") or {}).get("run_mode") in ("calibration", "inspection")
                                         for m in self.members):
            self.btn_print = QPushButton(tr("Print"))
            self.btn_pdf = QPushButton(tr("Save PDF"))
            self.btn_print.clicked.connect(lambda: self.on_report("print"))
            self.btn_pdf.clicked.connect(lambda: self.on_report("save"))
            buttons.addWidget(self.btn_print)
            buttons.addWidget(self.btn_pdf)
        close = QPushButton(tr("Close"))
        close.setProperty("variant", "primary")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        root.addLayout(buttons)
        self.btn_folder.clicked.connect(self._open_folder)
        self.tabs.currentChanged.connect(self._on_tab)

        start = 0
        if start_ref is not None:
            start = next((i for i, m in enumerate(self.members) if str(m.get("ref")) == str(start_ref)), 0)
        elif detail is not None:
            start = next((i for i, m in enumerate(self.members)
                          if str(m.get("ref")) == str(detail.summary.get("ref"))), 0)
        self.show_member(start)

    # ------------------------------------------------------------ ข้อมูล
    @staticmethod
    def _rate_text(member: dict) -> str:
        from core.capture_check import effective_verdict
        verdict = effective_verdict(member)
        mark = {"PASS": "✓", "FAIL": "✗", "INVALID": "⚠"}.get(verdict, "")
        return f"  {float((member.get('config') or {}).get('target_flow') or 0):g} ml/h  {mark}  "

    def _settings_now(self):
        return self.settings if self.settings is not None else AppSettings.load()

    def _detail(self, member: dict):
        ref = str(member.get("ref", ""))
        if ref not in self._details:
            self._details[ref] = self.repository.load(ref)
        return self._details[ref]

    def show_member(self, index: int) -> None:
        index = max(0, min(index, len(self.members) - 1))
        for i, button in enumerate(self._rate_buttons):
            button.setChecked(i == index)
        member = self.members[index]
        try:
            self.detail = self._detail(member)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, tr("Test result"), tr("Could not open this result: {error}", error=exc))
            return
        self.summary = self.detail.summary
        if self._replay is not None:
            self._replay.stop()
        self._replay = None
        self._replay_ref = self._document_ref = None
        keep = self.tabs.currentIndex()
        self.tabs.blockSignals(True)
        while self.tabs.count():
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            widget.deleteLater()
        self._fill_header()
        self.tabs.addTab(_scroll(self._overview()), tr(TABS[0]))
        self._replay_holder = QWidget()
        QVBoxLayout(self._replay_holder).setContentsMargins(0, 8, 0, 0)
        self.tabs.addTab(self._replay_holder, tr(TABS[1]))
        self._document_holder = QWidget()
        QVBoxLayout(self._document_holder).setContentsMargins(0, 8, 0, 0)
        self.tabs.addTab(self._document_holder, tr(TABS[2]))
        self.tabs.addTab(_scroll(self._job_tab()), tr(TABS[3]))
        self.tabs.addTab(self._data_tab(), tr(TABS[4]))
        self.tabs.addTab(_scroll(self._quality_tab()), tr(TABS[5]))
        self.tabs.blockSignals(False)
        self.tabs.setCurrentIndex(max(0, keep))
        self._on_tab(self.tabs.currentIndex())

    def _fill_header(self) -> None:
        from core.capture_check import check_summary, effective_verdict
        summary, config = self.summary, self.summary.get("config") or {}
        job = config.get("job") or {}
        pump = job.get("pump_type") or "infusion"
        self.badge.set_pump(pump)
        device = " ".join(str(p) for p in (job.get("brand"), job.get("model")) if p) or \
            (tr("Syringe pump") if pump == "syringe" else tr("Infusion pump"))
        serial = f"  ·  S/N {job['serial_no']}" if job.get("serial_no") else ""
        self.title.setText(f"{device}{serial}  ·  {float(config.get('target_flow') or 0):g} ml/h")
        method = tr(dict(STRATEGIES.choices()).get(config.get("strategy"), _text(config.get("strategy"))))
        parts = [tr(str(config.get("run_mode", "")).replace("_", " ").capitalize()), method,
                 (tr("Job") + " " + job["job_no"]) if job.get("job_no") else "",
                 " · ".join(p for p in (job.get("site") or "", job.get("province") or "") if p),
                 _date(summary.get("started_at", ""))]
        self.subtitle.setText("   ·   ".join(p for p in parts if p))
        verdict = effective_verdict(summary)
        color = getattr(Color, _VERDICT.get(verdict, "TEXT_MUTED"))
        self.verdict.setText(f"  {tr(verdict) if verdict == 'INVALID' else verdict}  ")
        self.verdict.setStyleSheet(f"color: {color}; border: 2px solid {color}; border-radius: 16px; "
                                   f"font-size: 20px; font-weight: 800; padding: 4px 14px;")
        capture = check_summary(summary)
        if capture is not None and capture.invalid:
            text = "⚠ " + tr(capture.message(), **capture.message_values())
            self.banner.setText(text)
            self.banner.setStyleSheet(f"color: {Color.WARNING}; border: 1px solid {Color.WARNING}; "
                                      f"border-radius: 8px; padding: 8px;")
            self.banner.show()
        else:
            self.banner.hide()

    # ------------------------------------------------------------ แท็บ: ภาพรวม
    def _overview(self) -> QWidget:
        from ui.plots import IntervalPlot
        from ui.plots.cell import PlotCell
        summary, config = self.summary, self.summary.get("config") or {}
        job = config.get("job") or {}
        tol = float(config.get("tolerance_pct") or 0)
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 10, 6, 6)
        box.setSpacing(12)
        kpis = _KpiRow()
        error = summary.get("error_pct")
        ok = error is not None and abs(error) <= tol
        budget = summary.get("uncertainty") or {}
        kpis.addWidget(_Kpi(tr("Measured flow"), fmt(summary.get("mean_flow"), 3), "ml/h",
                            tr("Set rate {rate:g} ml/h", rate=float(config.get("target_flow") or 0))))
        kpis.addWidget(_Kpi(tr("Flow error (net)"), fmt(error, 2, signed=True), "%",
                            tr("Tolerance ± {tol:g} %", tol=tol), Color.SUCCESS if ok else Color.DANGER), 1)
        kpis.addWidget(_Kpi("2 SD", fmt(summary.get("sd2_pct"), 3, prefix="± "), "%", tr("Spread of the intervals")), 1)
        kpis.addWidget(_Kpi(tr("Uncertainty U"), fmt(budget.get("U_ml_h"), 4, prefix="± ") if budget else "—", "ml/h",
                            fmt(budget.get("U_pct"), 3, " %", prefix="± ") if budget else tr("Not calculated")), 1)
        kpis.addWidget(_Kpi(tr("Intervals"), _text(summary.get("interval_count")), "",
                            tr("{n} balance points", n=summary.get("sample_count") or 0)), 1)
        kpis.addWidget(_Kpi(tr("Measuring time"), fmt_duration(measured_seconds(summary)), "",
                            tr("Total run {t}", t=fmt_duration(summary.get("duration_s", 0)))), 1)
        box.addWidget(kpis)

        body = QHBoxLayout()
        body.setSpacing(12)
        # กราฟรายช่วง (เต็มการทดสอบ)
        ui = UiSettings(max_points=6000)
        try:
            saved = self._settings_now().ui
            for name in ("interval_style", "interval_moving_avg", "interval_overall_mean", "interval_uncorrected"):
                setattr(ui, name, getattr(saved, name))
        except Exception:
            pass
        cell = PlotCell(IntervalPlot, ui)
        plot = cell.module
        plot.range_mode = "full"
        chains = 2 if any(row["chain"] == 1 for row in self.detail.intervals) else 1
        plot.set_chains(chains)
        plot.begin_session(SessionConfig(target_flow=max(1e-6, float(config.get("target_flow", 1.0) or 1.0)),
                                         tolerance_pct=tol or 5.0))
        plot.full_min_s = 0.0
        mean = summary.get("mean_flow")
        stats = IntervalStats(len(self.detail.intervals), mean, 0, 0, 0, 0, 0, 0) if mean is not None else None
        plot.feed([EngineResult(t=row["t"], weight=0.0, stats=stats, interval=Interval(
            row["index"], row["chain"], row["t"], row["duration_s"], row["flow"], row["error_pct"],
            row["flow_raw"], row["error_raw_pct"])) for row in self.detail.intervals])
        cell.setMinimumHeight(360)
        body.addWidget(cell, 3)

        side = QVBoxLayout()
        side.setSpacing(12)
        side.setContentsMargins(0, 0, 0, 0)
        iv = " ".join(p for p in (job.get("accessory_brand") or "", job.get("accessory") or "") if p)
        side.addWidget(_section(tr("At a glance"), [
            (tr("Job no."), _text(job.get("job_no"))),
            (tr("Hospital / site"), _text(" · ".join(p for p in (job.get("site") or "", job.get("province") or "") if p))),
            (tr("Department"), _text(job.get("department"))),
            (tr("IV set / syringe"), _text(iv)),
            (tr("Parts / warranty"), self._parts_text(job)),
            (tr("Operator"), _text(job.get("operator"))),
            (tr("Remark"), _text(job.get("notes"))),
        ]))
        side.addStretch(1)
        body.addLayout(side, 2)
        box.addLayout(body, 1)
        return page

    @staticmethod
    def _parts_text(job: dict) -> str:
        parts = list(job.get("parts_replaced") or [])
        claims = set(job.get("parts_warranty") or [])
        if not parts:
            return tr("No parts replaced")
        return ", ".join(p + (f" ({tr('warranty claim')})" if p in claims else "") for p in parts)

    # ------------------------------------------------------------ แท็บ: กราฟ · เล่นซ้ำ (สร้างเมื่อเปิดแท็บ)
    def _on_tab(self, index: int) -> None:
        ref = str(self.summary.get("ref", ""))
        if index == 1 and self._replay_ref != ref:
            self._build_replay()
        elif index == 2 and self._document_ref != ref:
            self._build_document()
        if index != 1 and self._replay is not None:
            self._replay.pause()

    def replay_data(self):
        from services.replay_session import build
        return build(self.detail)

    def _build_replay(self) -> None:
        from ui.widgets.replay_view import ReplayView
        layout = self._replay_holder.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            data = self.replay_data()
        finally:
            QApplication.restoreOverrideCursor()
        if not data.results:
            layout.addWidget(label(tr("No raw data saved for this result — nothing to replay."), "pageSubtitle"))
        else:
            try:
                saved = self._settings_now().ui
            except Exception:
                saved = None
            self._replay = ReplayView(data, saved)
            note = label(tr("Rebuilt from the saved raw data and intervals — the numbers match the saved result. "
                            "Press Play to watch the test as it ran."), "hint")
            note.setWordWrap(True)
            layout.addWidget(note)
            layout.addWidget(self._replay, 1)
        self._replay_ref = str(self.summary.get("ref", ""))

    # ------------------------------------------------------------ แท็บ: เอกสาร
    def _build_document(self) -> None:
        layout = self._document_holder.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._document_ref = str(self.summary.get("ref", ""))
        from services.report import service as report_service
        if not report_service.reportable(self.summary):
            layout.addWidget(label(tr("Quick Test has no report"), "pageSubtitle"))
            layout.addStretch(1)
            return
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtPdfWidgets import QPdfView
        from services.report import layout as report_layout
        from services.report.render import shared_renderer
        settings = self._settings_now()
        try:
            jobs = report_service.jobs_for(self.repository, [self.summary], settings)
        except Exception as exc:
            layout.addWidget(label(tr("Could not build the PDF: {error}", error=exc), "pageSubtitle"))
            return
        status = label(tr("Building the report…"), "hint")
        layout.addWidget(status)
        self._pdf = QPdfDocument(self._document_holder)
        view = QPdfView(self._document_holder)
        view.setDocument(self._pdf)
        view.setPageMode(QPdfView.PageMode.MultiPage)
        zoom = int(getattr(settings.report, "preview_zoom_pct", 67) or 0)
        if zoom > 0:
            view.setZoomMode(QPdfView.ZoomMode.Custom)
            view.setZoomFactor(zoom / 100.0)
        else:
            view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        view.setPageSpacing(14)
        layout.addWidget(view, 1)
        holder_ref = self._document_ref

        def done(data, error, _checks) -> None:
            from PySide6.QtCore import QBuffer, QByteArray, QIODevice
            if holder_ref != self._document_ref:
                return
            if data is None:
                status.setText(tr("Could not build the PDF: {error}", error=error))
                return
            self._pdf_buffer = QBuffer(self._document_holder)
            self._pdf_buffer.setData(QByteArray(data))
            self._pdf_buffer.open(QIODevice.OpenModeFlag.ReadOnly)
            self._pdf.load(self._pdf_buffer)
            status.setText(tr("Report of this job made from the saved results · {pages} pages",
                              pages=self._pdf.pageCount()))

        lang = report_service.language(settings)
        shared_renderer().render(report_layout.html_document(jobs, lang), done)

    # ------------------------------------------------------------ แท็บ: งานและเครื่อง
    def _job_tab(self) -> QWidget:
        from services.report import checklist as report_checklist
        from ui.dialogs.session_detail import USAGE_TEXT
        summary, config = self.summary, self.summary.get("config") or {}
        job = config.get("job") or {}
        page = QWidget()
        columns = QHBoxLayout(page)
        columns.setContentsMargins(0, 10, 6, 6)
        columns.setSpacing(12)
        left, right = QVBoxLayout(), QVBoxLayout()
        for column in (left, right):
            column.setSpacing(12)
        pump = tr("Syringe pump") if job.get("pump_type") == "syringe" else tr("Infusion pump")
        left.addWidget(_section(tr("Job"), [
            (tr("Job no."), _text(job.get("job_no"))),
            (tr("Hospital / site"), _text(job.get("site"))),
            (tr("Province"), _text(job.get("province"))),
            (tr("Department"), _text(job.get("department"))),
            (tr("Operator"), _text(job.get("operator"))),
            (tr("Contact person"), _text(" · ".join(p for p in (job.get("contact"), job.get("contact_phone")) if p))),
            (tr("Date"), _date(summary.get("started_at", ""))),
            (tr("Job ID"), f'{_text(config.get("job_id"))}  ({config.get("step_index", 0) + 1}/'
                           f'{config.get("step_count", 1)})'),
        ]))
        left.addWidget(_section(tr("Device"), [
            (tr("Pump type"), pump),
            (tr("Brand"), _text(job.get("brand"))),
            (tr("Model"), _text(job.get("model"))),
            (tr("Serial no."), _text(job.get("serial_no"))),
            (tr("Asset ID"), _text(job.get("asset_id"))),
            (tr("Accessories"), ", ".join(job.get("accessories") or []) or "—"),
        ]))
        usage = job.get("accessory_usage")
        left.addWidget(_section(tr("IV set / syringe"), [
            (tr("Brand"), _text(job.get("accessory_brand"))),
            (tr("Model"), _text(job.get("accessory"))),
            (tr("Against the hospital standard"), tr(USAGE_TEXT[usage]) if usage in USAGE_TEXT else "—"),
            (tr("Evaporation trap"), {"yes": tr("Used"), "no": tr("Not used")}.get(job.get("evaporation_trap"), "—")),
        ]))
        left.addStretch(1)

        right.addWidget(self._warranty_card(job))
        version = int(job.get("checks_version") or 0)
        pump_key = str(job.get("pump_type") or "infusion")
        full = report_checklist.expand(pump_key, job.get("checks") or {}, version)
        lang = "th" if tr("Pass") != "Pass" else "en"
        checks_text = report_checklist.describe(pump_key, full, lang) if (version or full) else tr("Not recorded")
        right.addWidget(_section(tr("Checklist results for the report"), [(tr("Result"), checks_text)]))
        remark = Card(tr("Remark"))
        notes = QPlainTextEdit(str(job.get("notes") or ""))
        notes.setReadOnly(True)
        notes.setPlaceholderText(tr("No remark"))
        notes.setMaximumHeight(110)
        remark.body.addWidget(notes)
        right.addWidget(remark)
        right.addWidget(_section(tr("Environment"), [
            (tr("Liquid temperature"), fmt(job.get("temperature_c"), 1, " °C")),
            (tr("Air temperature"), fmt(job.get("air_temp_c"), 1, " °C")),
            (tr("Humidity"), fmt(job.get("humidity_pct"), 1, " %RH")),
            (tr("Air pressure"), fmt(job.get("pressure_hpa"), 1, " hPa")),
            (tr("Balance ID"), _text(job.get("balance_id"))),
        ]))
        sheet = self._sheet_card(job)
        if sheet is not None:
            right.addWidget(sheet)
        right.addStretch(1)
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)
        return page

    def _warranty_card(self, job: dict) -> Card:
        """อะไหล่ที่เปลี่ยนในงานนี้ + สถานะประกันของเครื่อง ณ วันนี้ (จากประวัติทั้งหมดของเครื่อง)"""
        from core.models import JobInfo, PumpType
        from core.warranty import summarize
        card = Card(tr("Parts and warranty"))
        claims = set(job.get("parts_warranty") or [])
        parts = list(job.get("parts_replaced") or [])
        lines = [f"• {p}" + (f"  —  {tr('warranty claim')}" if p in claims else "") for p in parts]
        card.body.addWidget(label("\n".join(lines) if lines else tr("No parts replaced in this job"), "metricValue"))
        try:
            info = JobInfo(pump_type=PumpType(job.get("pump_type") or "infusion"), brand=job.get("brand") or "",
                           model=job.get("model") or "", serial_no=job.get("serial_no") or "",
                           asset_id=job.get("asset_id") or "")
            settings = self._settings_now()
            history = summarize(self.repository.part_history(info), months=settings.warranty.months,
                                grace_months=settings.warranty.grace_months)
        except Exception:
            history = []
        if history:
            card.body.addWidget(label(tr("Warranty of this device today"), "fieldLabel"))
            table = QTableWidget(len(history), 5)
            table.setHorizontalHeaderLabels([tr("Part"), tr("Warranty from"), tr("Until"), tr("Claims"), tr("Status")])
            colors = {"active": Color.SUCCESS, "late": Color.WARNING, "expired": Color.TEXT_MUTED}
            names = {"active": tr("Under warranty"), "late": tr("Late claim period"), "expired": tr("Expired")}
            for row, item in enumerate(history):
                values = [item.part, item.first_at, item.status.until.isoformat(), str(item.claims),
                          names.get(item.status.state, item.status.state)]
                for col, value in enumerate(values):
                    cell = QTableWidgetItem(value)
                    if col == 4:
                        from PySide6.QtGui import QColor
                        cell.setForeground(QColor(colors.get(item.status.state, Color.TEXT)))
                    table.setItem(row, col, cell)
            table.verticalHeader().hide()
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.setMaximumHeight(40 + 30 * len(history))
            card.body.addWidget(table)
        return card

    def _sheet_card(self, job: dict) -> Card | None:
        """ข้อมูลของงานนี้ใน Google Sheet (ถ้าตั้งค่าไว้และดึงมาแล้ว)"""
        try:
            from services import sheets
            rows = sheets.store().rows_for(job)
        except Exception:
            return None
        if not rows:
            return None
        card = Card(tr("Google Sheet"))
        for source_name, values in rows[:3]:
            card.body.addWidget(label(source_name, "fieldLabel"))
            grid = QGridLayout()
            grid.setHorizontalSpacing(12)
            for index, (name, value) in enumerate(list(values.items())[:30]):
                grid.addWidget(label(str(name), "metricName"), index, 0)
                value_label = label(str(value), "metricValue")
                value_label.setWordWrap(True)
                grid.addWidget(value_label, index, 1)
            card.body.addLayout(grid)
        return card

    # ------------------------------------------------------------ แท็บ: ข้อมูลการวัด
    def _data_tab(self) -> QWidget:
        from services.replay_session import read_intervals
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 10, 0, 0)
        rows = read_intervals(Path(self.summary.get("folder") or "")) or self.detail.intervals
        box.addWidget(label(tr("{n} intervals · times from the first peak (s) · volume from the balance weight",
                               n=len(rows)), "hint"))
        headers = [tr("#"), tr("Chain"), tr("Start (s)"), tr("End (s)"), tr("Duration (s)"), tr("Δm (g)"),
                   tr("Volume (ml)"), tr("Flow (ml/h)"), tr("Error (%)"), tr("Uncorrected (ml/h)")]
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        origin = float(self.summary.get("origin_s") or 0.0)
        tol = float((self.summary.get("config") or {}).get("tolerance_pct") or 0)
        for r, row in enumerate(rows):
            start = row.get("t_start")
            end = row.get("t_end")
            dm = (row["w_end"] - row["w_start"]) if row.get("w_end") is not None and row.get("w_start") is not None \
                else None
            values = [str(row["index"] + 1), "AB"[row["chain"]],
                      fmt(start - origin if start is not None else row["t"] - row["duration_s"], 2),
                      fmt(end - origin if end is not None else row["t"], 2), fmt(row["duration_s"], 3), fmt(dm, 4),
                      fmt(row.get("volume_ml"), 4), fmt(row["flow"], 4), fmt(row["error_pct"], 2, signed=True),
                      fmt(row.get("flow_raw"), 4)]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 8 and tol and abs(row["error_pct"]) > tol:
                    from PySide6.QtGui import QColor
                    item.setForeground(QColor(Color.DANGER))
                table.setItem(r, c, item)
        table.verticalHeader().hide()
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        box.addWidget(table, 1)
        return page

    # ------------------------------------------------------------ แท็บ: คุณภาพและสอบย้อน
    def _quality_tab(self) -> QWidget:
        from core.capture_check import check_summary
        from services.window_plan import FIT_TEXT
        from ui.dialogs.session_detail import correction_rows, integrity_text, uncertainty_rows
        summary = self.summary
        page = QWidget()
        columns = QHBoxLayout(page)
        columns.setContentsMargins(0, 10, 6, 6)
        columns.setSpacing(12)
        left, right = QVBoxLayout(), QVBoxLayout()
        left.setSpacing(12)
        right.setSpacing(12)
        raw_flow, raw_error, _ = raw_result(summary)
        left.addWidget(_section(tr("Result"), [
            (tr("Mean flow"), fmt(summary.get("mean_flow"), 4, " ml/h")),
            (tr("Flow error (net)"), fmt(summary.get("error_pct"), 3, " %", signed=True)),
            (tr("Uncorrected"), f'{fmt(raw_flow, 4, " ml/h")}  ({fmt(raw_error, 3, " %", signed=True)})'),
            ("2 SD", fmt(summary.get("sd2_pct"), 3, " %", prefix="± ")),
            (tr("Intervals"), _text(summary.get("interval_count"))),
            (tr("Measuring time"), fmt_duration(measured_seconds(summary))),
            (tr("Status"), tr(str(summary.get("end_reason", "")).capitalize())),
        ]))
        capture = check_summary(summary)
        if capture is not None:
            engine = summary.get("engine_settings") or {}
            left.addWidget(_section(tr("Pump-cycle capture"), [
                (tr("Pump cycle"), fmt(summary.get("pump_period_s") or engine.get("expected_period_s") or None, 2, " s")),
                (tr("Time per cycle"), fmt(summary.get("mean_duration_s"), 2, " s")),
                (tr("Regression window"), f'{_text(summary.get("regression_window"))} {tr("pts")}'),
                (tr("n̄ (peak left/right)"), f'{_text(summary.get("cycle_half_window"))} {tr("pts")}'),
                (tr("Points per cycle"), fmt(summary.get("points_per_cycle"), 1)),
                (tr("Window values"), tr(FIT_TEXT.get(engine.get("window_fit", ""), engine.get("window_fit", "—") or "—"))),
                (tr("Capture check"), tr({"ok": "OK", "too_few": "Not enough cycles",
                                          "period_mismatch": "Does not match the cycle",
                                          "irregular": "Some cycles split or merged",
                                          "consistent": "Cycles agree (no reference cycle)",
                                          "unverified": "Not checked (cycle unknown)"}.get(capture.status, capture.status))),
            ]))
        if summary.get("uncertainty"):
            left.addWidget(_section(tr("Uncertainty budget"), uncertainty_rows(summary)))
        left.addStretch(1)
        try:
            checks = self.repository.verify(summary.get("ref", ""))
        except Exception:
            checks = []
        right.addWidget(_section(tr("g → ml correction (audit)"),
                                 [*correction_rows(summary), (tr("Data integrity"), integrity_text(checks))]))
        audit = Card(tr("Re-check from raw data"))
        self.audit_result = label(tr("Recalculates every number from raw.csv and compares it with the saved result."),
                                  "hint")
        self.audit_result.setWordWrap(True)
        button = QPushButton(tr("Re-check every number from raw data"))
        button.clicked.connect(self._run_audit)
        audit.body.addWidget(self.audit_result)
        audit.body.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        right.addWidget(audit)
        right.addStretch(1)
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)
        return page

    def _run_audit(self) -> None:
        from services.audit import audit_folder
        try:
            audit = audit_folder(Path(self.summary.get("folder") or ""), self.summary)
        except Exception as exc:
            self.audit_result.setText(str(exc))
            self.audit_result.setStyleSheet(f"color: {Color.DANGER};")
            return
        head = tr("All {n} checks match the raw data ({k} intervals).", n=len(audit.checks), k=audit.intervals) \
            if audit.ok else tr("Some checks do not match the raw data — see below.")
        lines = [("✓ " if c.ok else "✗ ") + tr(c.name) + (f"  —  {c.detail}" if c.detail else "") for c in audit.checks]
        self.audit_result.setText(head + "\n" + "\n".join(lines))
        self.audit_result.setStyleSheet(f"color: {Color.SUCCESS if audit.ok else Color.WARNING};")

    # ------------------------------------------------------------ ส่งออกการเล่นซ้ำ
    def _export_name(self, extension: str) -> str:
        config = self.summary.get("config") or {}
        job = config.get("job") or {}
        stem = "_".join(p for p in (job.get("job_no"), job.get("model"), f"{float(config.get('target_flow') or 0):g}mlh")
                        if p) or "DeltaM_replay"
        stem = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in stem)
        return str(Path.home() / "Documents" / f"{stem}_replay.{extension}")

    def _meta(self) -> dict:
        from core.capture_check import effective_verdict
        config = self.summary.get("config") or {}
        job = config.get("job") or {}
        verdict = effective_verdict(self.summary)
        rows = [(tr("Job no."), _text(job.get("job_no"))), (tr("Hospital / site"), _text(job.get("site"))),
                (tr("Serial no."), _text(job.get("serial_no"))), (tr("IV set / syringe"),
                 _text(" ".join(p for p in (job.get("accessory_brand") or "", job.get("accessory") or "") if p))),
                (tr("Operator"), _text(job.get("operator"))), (tr("Date"), _date(self.summary.get("started_at", ""))),
                (tr("Measured flow"), fmt(self.summary.get("mean_flow"), 3, " ml/h")),
                (tr("Flow error (net)"), fmt(self.summary.get("error_pct"), 2, " %", signed=True)
                 + "  (± " + f"{float(config.get('tolerance_pct') or 0):g} %)")]
        sha = ""
        try:
            sha = (self.repository.file_hash(self.summary.get("ref"), "raw.csv.gz") or "")[:16]
        except Exception:
            pass
        return {"title": self.title.text(), "subtitle": self.subtitle.text(), "verdict": verdict, "rows": rows,
                "footer": tr("Result {ref}", ref=self.summary.get("ref", "")) + (f" · SHA-256 {sha}…" if sha else "")}

    def export_html(self, path: str | None = None) -> str | None:
        from services.replay_export import build_html
        data = self.replay_data()
        if not data.results:
            QMessageBox.information(self, tr("Export replay"), tr("No raw data saved for this result — nothing to replay."))
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, tr("Export replay"), self._export_name("html"), "HTML (*.html)")
            if not path:
                return None
        labels = {"tile_time": tr("Time since the first peak"), "tile_flow": tr("Flow now"),
                  "tile_mean": tr("Measured flow"), "tile_error": tr("Flow error (net)"), "tile_count": tr("Intervals"),
                  "tile_weight": tr("Balance weight"), "cumulative": tr("Cumulative average flow"),
                  "intervals": tr("Interval flow"), "slope": tr("Instantaneous flow and pump cycles"),
                  "weight": tr("Balance weight"), "chain_a": tr("Chain A"), "chain_b": tr("Chain B"),
                  "overall": tr("Overall"), "moving": tr("Moving average"), "slope_line": tr("Flow now"),
                  "peak": tr("Peak"), "weight_line": tr("Weight (g)"), "full": tr("Full"), "auto": tr("Auto"),
                  "zoom": tr("Zoom"), "play": tr("Play"), "pause": tr("Pause")}
        lang = "th" if tr("Play") != "Play" else "en"
        Path(path).write_text(build_html(data, self._meta(), labels, lang), encoding="utf-8")
        if self.isVisible():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        return path

    def export_video(self, path: str | None = None, speed: float | None = None, size: QSize | None = None) -> str | None:
        from ui.widgets.replay_view import ReplayView
        data = self.replay_data()
        if not data.results:
            QMessageBox.information(self, tr("Export replay"), tr("No raw data saved for this result — nothing to replay."))
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, tr("Export replay"), self._export_name("mp4"), "MP4 (*.mp4)")
            if not path:
                return None
        if speed is None:       # วิดีโอยาวไม่เกิน ~2 นาที (ทดสอบยาว = เร่งมากขึ้น)
            speed = next((s for s in (5, 10, 20, 30, 60, 120, 240, 480) if data.duration / s <= 120), 600)
        view = ReplayView(data, self._settings_now().ui, header=self.title.text() + "   ·   " + self._meta()["verdict"])
        view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        view.show()
        progress = QProgressDialog(tr("Making the video ({speed:g}× speed)…", speed=speed), tr("Cancel"), 0, 1000, self)
        progress.setWindowTitle(tr("Export replay"))
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        ok, message = view.export_video(path, speed=speed, size=size or QSize(1600, 900),
                                        progress=lambda f: (progress.setValue(int(f * 1000)), QApplication.processEvents()),
                                        should_stop=progress.wasCanceled)
        progress.close()
        view.close()
        view.deleteLater()
        if not ok:
            QMessageBox.warning(self, tr("Export replay"), tr("The video was not made: {error}", error=message))
            return None
        if self.isVisible():
            QMessageBox.information(self, tr("Export replay"), tr("Saved {path}\n{info}", path=path, info=message))
        return path

    def _open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.summary.get("folder") or "")))

    def closeEvent(self, event) -> None:
        if self._replay is not None:
            self._replay.stop()
        super().closeEvent(event)

    def done(self, result: int) -> None:
        if self._replay is not None:
            self._replay.stop()
        super().done(result)
