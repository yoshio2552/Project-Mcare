"""หน้า History: ผลทดสอบที่บันทึกไว้ แยกแท็บตามโหมด — ค้นหา กรอง เปิดดู ลบ ส่งออกไฟล์ · ติ๊กเลือกแล้วออกใบรายงาน PDF / พิมพ์

ช่องติ๊ก (คอลัมน์แรก): ติ๊ก rate ใดของงานก็ได้ = ทั้งงาน (ทุก rate ของงานเดียวกันออกเป็นใบเดียว) · Quick Test ไม่มีใบ
รายการที่ติ๊กไว้ยังอยู่เมื่อค้นหา/กรอง/เปลี่ยนแท็บ (ป้ายบอกจำนวน)

- เพิ่มคอลัมน์: เพิ่ม 1 บรรทัดใน COLUMNS
- เพิ่มรูปแบบไฟล์ส่งออก: ลงทะเบียน exporter ใหม่ใน services/exporters.py
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox,
    QProgressDialog, QPushButton, QTabBar, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from config.constants import SESSIONS_DIR
from config.i18n import tr
from services.exporters import EXPORTERS
from services.session_controller import tuning_text
from core.capture_check import check_summary, effective_verdict
from services.report import service as report_service
from services.report.model import job_key as report_job_key
from services.session_store import get_repository, raw_result
from ui.dialogs.session_detail import SessionDetailDialog
from ui.icons import Glyph, glyph_icon
from ui.theme import Color
from ui.widgets.common import PageHeader, fmt, fmt_clock, label

# แท็บ = โหมดการทดสอบ (None = ทั้งหมด)
MODE_TABS = [(None, "All"), ("calibration", "Calibration"), ("inspection", "Inspection"), ("quick_test", "Quick Test")]


def _job(session: dict) -> dict:
    return session["config"].get("job") or {}


def _title(text: str) -> str:
    return text.replace("_", " ").capitalize()


# (หัวคอลัมน์, ฟังก์ชันดึงข้อความจาก summary dict, ชิดขวาไหม)
COLUMNS = [
    ("Date", lambda s: _date(s.get("started_at", "")), False),
    ("Result", lambda s: effective_verdict(s), False),     # ผลเก่าที่จับรอบผิด = INVALID (ตรวจย้อนหลัง)
    ("Mode", lambda s: _title(s["config"].get("run_mode", "")), False),
    ("Step", lambda s: f'{s["config"].get("step_index", 0) + 1}/{s["config"].get("step_count", 1)}', False),
    ("Device", lambda s: " ".join(p for p in (_job(s).get("brand"), _job(s).get("model")) if p) or "—", False),
    ("Serial no.", lambda s: _job(s).get("serial_no") or "—", False),
    ("Operator", lambda s: _job(s).get("operator") or "—", False),
    ("Target (ml/h)", lambda s: fmt(s["config"].get("target_flow"), 1), True),
    ("Mean flow (ml/h)", lambda s: fmt(s.get("mean_flow"), 3), True),
    ("Error (%)", lambda s: fmt(s.get("error_pct"), 2, signed=True), True),
    ("Uncorrected (%)", lambda s: fmt(raw_result(s)[1], 2, signed=True), True),
    ("2 SD (±%)", lambda s: fmt(s.get("sd2_pct"), 3), True),
    ("Duration", lambda s: fmt_clock(s.get("duration_s", 0)), True),
    ("Status", lambda s: tr(_title(s.get("end_reason", ""))), False),
]
_VERDICT_COLORS = {"PASS": "SUCCESS", "FAIL": "DANGER", "INVALID": "WARNING"}    # ชื่อสีใน Color (ตามธีม)


def _grouped(session: dict) -> bool:
    """Calibration ที่มี job_id = 1 แถวต่องาน (ผู้ใช้ขอ 2026-11-18) — Inspection / Quick Test แถวละผลเหมือนเดิม"""
    config = session.get("config") or {}
    return config.get("run_mode") == "calibration" and bool(config.get("job_id"))


def _job_texts(members: list[dict], expanded: bool) -> dict:
    """ข้อความของแถวงาน Calibration: rate ทั้งหมด · ผลรวม (ผลล่าสุดของแต่ละ rate) · คลาดเคลื่อนที่มากสุด"""
    latest: dict[float, dict] = {}
    for member in sorted(members, key=lambda m: m.get("started_at", "")):
        latest[float(member["config"].get("target_flow") or 0)] = member
    verdicts = [effective_verdict(m) for m in latest.values()]
    steps = max(int(m["config"].get("step_count") or 1) for m in members)
    done = sum(1 for m in latest.values() if m.get("end_reason") == "completed" and effective_verdict(m) in ("PASS", "FAIL"))
    if "FAIL" in verdicts:
        result = "FAIL"
    elif "INVALID" in verdicts:
        result = "INVALID"
    elif verdicts and all(v == "PASS" for v in verdicts):
        result = "PASS"
    else:
        result = "N/A"
    errors = [m.get("error_pct") for m in latest.values() if m.get("error_pct") is not None]
    worst = max(errors, key=abs) if errors else None
    sd2 = [m.get("sd2_pct") for m in latest.values() if m.get("sd2_pct") is not None]
    first = min(members, key=lambda m: m.get("started_at", ""))
    job = _job(first)
    return {
        "Date": ("▾  " if expanded else "▸  ") + _date(first.get("started_at", "")),
        "Result": result,
        "Mode": _title("calibration"),
        "Step": f"{done}/{steps}",
        "Device": " ".join(p for p in (job.get("brand"), job.get("model")) if p) or "—",
        "Serial no.": job.get("serial_no") or "—",
        "Operator": job.get("operator") or "—",
        "Target (ml/h)": " · ".join(f"{rate:g}" for rate in sorted(latest)),
        "Mean flow (ml/h)": tr("{n} rates", n=len(latest)),
        "Error (%)": fmt(worst, 2, signed=True) if worst is not None else "—",
        "Uncorrected (%)": "—",
        "2 SD (±%)": fmt(max(sd2), 3) if sd2 else "—",
        "Duration": fmt_clock(sum(float(m.get("duration_s") or 0) for m in members)),
        "Status": tr("Completed") if done == steps else tr("{done} of {total} rates", done=done, total=steps),
    }


def _date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d  %H:%M")
    except ValueError:
        return iso


class HistoryPage(QWidget):
    def __init__(self, settings=None):
        super().__init__()
        self.setObjectName("page")
        self._settings = settings            # AppSettings ของโปรแกรม (None = อ่านจากไฟล์ตอนใช้)
        self._repository = get_repository()
        self._sessions: list[dict] = []      # ของแท็บปัจจุบัน
        self._visible: list[dict] = []       # หลังกรอง (ตรงกับแถวในตาราง)
        self._checked: dict[str, dict] = {}  # ref -> session ที่ติ๊กไว้ (ข้ามแท็บ/ตัวกรอง)
        self._rows: list[tuple] = []         # แถวของตาราง (ดู _build_rows)
        self._expanded: set[str] = set()     # งาน Calibration ที่กางดูราย rate
        self._report_actions = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header = PageHeader(tr("History"), tr("Saved test results — double-click a row to open it"))
        refresh = QPushButton("  " + tr("Refresh"))
        refresh.setIcon(glyph_icon(Glyph.REFRESH, Color.TEXT, size=14))
        export = QPushButton("  " + tr("Export"))
        export.setIcon(glyph_icon(Glyph.SAVE, Color.TEXT, size=14))
        open_folder = QPushButton("  " + tr("Open data folder"))
        open_folder.setIcon(glyph_icon(Glyph.FOLDER, Color.TEXT, size=14))
        self.btn_tune = QPushButton(tr("Tune peak window"))
        self.btn_tune.setToolTip(tr("Replay the stored tests of the selected pump model and find the window size "
                                    "that captures its pump cycles most consistently"))
        self.busy = lambda: False           # หน้าต่างหลักตั้งให้: กำลังทดสอบอยู่ไหม
        self.btn_delete = QPushButton(tr("Delete"))
        self.btn_delete.setProperty("variant", "danger")
        self.btn_delete.setStyleSheet("padding: 7px 14px; font-size: 13px;")
        # ใบรายงานของรายการที่ติ๊ก
        self.btn_pdf = QPushButton("  " + tr("Save PDF"))
        self.btn_pdf.setIcon(glyph_icon(Glyph.SAVE, Color.TEXT, size=14))
        self.btn_print = QPushButton(tr("Print"))
        for button in (self.btn_pdf, self.btn_print):
            button.setToolTip(tr("Make the report of the ticked jobs (all rates of a job go on one report)"))
            button.setEnabled(False)
        for button in (refresh, self.btn_pdf, self.btn_print, export, open_folder, self.btn_tune, self.btn_delete):
            header.actions.addWidget(button)
        layout.addWidget(header)

        self.tabs = QTabBar()
        self.tabs.setDrawBase(False)
        self.tabs.setExpanding(False)
        for _, text in MODE_TABS:
            self.tabs.addTab(tr(text))
        layout.addWidget(self.tabs)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Search device, serial no., operator, date…"))
        self.search.setClearButtonEnabled(True)
        self.result_filter = QComboBox()
        for text, value in ((tr("All results"), ""), ("PASS", "PASS"), ("FAIL", "FAIL"), ("INVALID", "INVALID")):
            self.result_filter.addItem(text, value)
        self.count = label("", "hint")
        self.select_all = QCheckBox(tr("Tick all shown"))
        self.selected = label("", "hint")
        filters.addWidget(self.search, 1)
        filters.addWidget(self.result_filter)
        filters.addWidget(self.count)
        filters.addSpacing(12)
        filters.addWidget(self.select_all)
        filters.addWidget(self.selected)
        layout.addLayout(filters)

        self.table = QTableWidget(0, len(COLUMNS) + 1)     # คอลัมน์ 0 = ช่องติ๊ก
        self.table.setHorizontalHeaderLabels([""] + [tr(name) for name, _, _ in COLUMNS])
        for col, (_, _, right) in enumerate(COLUMNS, 1):
            align = Qt.AlignmentFlag.AlignRight if right else Qt.AlignmentFlag.AlignLeft
            self.table.horizontalHeaderItem(col).setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
        self.table.verticalHeader().hide()
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setHighlightSections(False)
        layout.addWidget(self.table, 1)

        self.empty = label(tr("No results to show"), "hint")
        layout.addWidget(self.empty, alignment=Qt.AlignmentFlag.AlignHCenter)

        refresh.clicked.connect(self.reload)
        export.clicked.connect(self._export)
        open_folder.clicked.connect(self._open_folder)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.tabs.currentChanged.connect(self.reload)
        self.search.textChanged.connect(self._apply_filter)
        self.result_filter.currentIndexChanged.connect(self._apply_filter)
        self.table.cellDoubleClicked.connect(lambda row, _: self._open_detail(row))
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.btn_tune.clicked.connect(self._tune_selected)
        self.table.itemChanged.connect(self._on_item_changed)
        self.select_all.clicked.connect(self._on_select_all)
        self.btn_pdf.clicked.connect(lambda: self._make_report("save"))
        self.btn_print.clicked.connect(lambda: self._make_report("print"))
        self.reload()

    # ------------------------------------------------------------- ข้อมูล
    def reload(self, *_) -> None:
        self._sessions = self._repository.list(MODE_TABS[max(0, self.tabs.currentIndex())][0])
        self._apply_filter()

    def _apply_filter(self, *_) -> None:
        words = self.search.text().lower().split()
        verdict = self.result_filter.currentData()

        def matches(session: dict) -> bool:
            if verdict and effective_verdict(session) != verdict:
                return False
            if not words:
                return True
            job = session.get("config", {}).get("job") or {}
            haystack = " ".join(str(v) for v in (*job.values(), session.get("started_at", ""),
                                                 session.get("config", {}).get("job_id", ""))).lower()
            return all(word in haystack for word in words)

        self._visible = [s for s in self._sessions if matches(s)]
        self._build_rows()
        self._fill_table()

    # แถวของตาราง: ("single", ผล, [ผล]) · ("job", ผลตัวแทน, [ทุก rate]) = Calibration 1 แถวต่องาน · ("rate", ผล, [ทุก rate]) = แถวย่อยเมื่อกางออก
    def _build_rows(self) -> None:
        groups: dict[str, list[dict]] = {}
        for session in self._visible:
            if _grouped(session):
                groups.setdefault(report_job_key(session), []).append(session)
        rows, seen = [], set()
        for session in self._visible:
            if not _grouped(session):
                rows.append(("single", session, [session]))
                continue
            key = report_job_key(session)
            if key in seen:
                continue
            seen.add(key)
            members = sorted(groups[key], key=lambda m: (m["config"].get("step_index", 0), m.get("started_at", "")))
            rows.append(("job", members[-1], members))
            if key in self._expanded:
                rows += [("rate", member, members) for member in members]
        self._rows = rows

    def _row(self, row: int):
        return self._rows[row] if 0 <= row < len(self._rows) else None

    def _fill_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._rows))
        for row, (kind, session, members) in enumerate(self._rows):
            tick = QTableWidgetItem()
            if report_service.reportable(session):
                tick.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                on = all(m["ref"] in self._checked for m in members) if kind == "job" else session["ref"] in self._checked
                tick.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
            else:
                tick.setFlags(Qt.ItemFlag.ItemIsEnabled)
                tick.setToolTip(tr("Quick Test has no report"))
            self.table.setItem(row, 0, tick)
            texts = _job_texts(members, report_job_key(session) in self._expanded) if kind == "job" else None
            for col, (name, getter, right) in enumerate(COLUMNS, 1):
                if texts is not None:
                    text = texts.get(name, "—")
                else:
                    try:
                        text = getter(session)
                    except (KeyError, TypeError, ValueError):
                        text = "—"
                    if kind == "rate" and name == "Date":
                        text = "      └  " + text
                item = QTableWidgetItem(text)
                align = Qt.AlignmentFlag.AlignRight if right else Qt.AlignmentFlag.AlignLeft
                item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if name == "Result" and text in _VERDICT_COLORS:
                    item.setForeground(QColor(getattr(Color, _VERDICT_COLORS[text])))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                if kind == "job":
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    if name == "Date":
                        item.setToolTip(tr("Click to show or hide each rate"))
                elif kind == "rate" and name != "Result":
                    item.setForeground(QColor(Color.TEXT_MUTED))       # แถวย่อยราย rate สีจางกว่าแถวงาน
                self.table.setItem(row, col, item)
        self.table.blockSignals(False)
        self._update_ticks()
        self.table.clearSelection()
        self.table.setCurrentCell(-1, -1)
        self.btn_delete.setEnabled(False)
        self.btn_tune.setEnabled(False)
        self.empty.setVisible(not self._rows)
        self.count.setText(tr("{shown} of {total}", shown=len(self._visible), total=len(self._sessions)))

    def _toggle_job(self, row: int) -> None:
        entry = self._row(row)
        if entry is None or entry[0] != "job":
            return
        key = report_job_key(entry[1])
        self._expanded.symmetric_difference_update({key})
        self._build_rows()
        self._fill_table()

    def _on_cell_clicked(self, row: int, column: int) -> None:
        entry = self._row(row)
        if entry is not None and entry[0] == "job" and column == 1:
            self._toggle_job(row)

    # ------------------------------------------------------------- คำสั่ง
    def _open_detail(self, row: int) -> None:
        entry = self._row(row)
        if entry is None:
            return
        if entry[0] == "job":                    # แถวงาน: ดับเบิลคลิก = กาง/หุบ
            self._toggle_job(row)
            return
        session = entry[1]
        try:
            detail = self._repository.load(session["ref"])
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, tr("History"), tr("Could not open this result: {error}", error=exc))
            return
        SessionDetailDialog(self, detail, on_report=lambda action: self._report_for([session], action)).exec()

    def _on_selection(self) -> None:
        entry = self._row(self.table.currentRow())
        self.btn_delete.setEnabled(entry is not None)
        session = entry[1] if entry else None
        job = (session or {}).get("config", {}).get("job") or {}
        self.btn_tune.setEnabled(bool(session) and session["config"].get("strategy") == "pump_cycle"
                                 and bool(job.get("brand") or job.get("model")))

    def _tune_selected(self) -> None:
        """ปรับขนาดหน้าต่างจับรอบปั๊มของรุ่นที่เลือก จากทุกการทดสอบที่เก็บไว้ (ทุก rate)"""
        from config.settings import AppSettings
        from core.tuning import tune
        entry = self._row(self.table.currentRow())
        if entry is None:
            return
        if self.busy():
            QMessageBox.information(self, tr("Tune peak window"), tr("Wait until the running test has finished."))
            return
        job = entry[1]["config"]["job"]
        brand, model, iv_set = job.get("brand", ""), job.get("model", ""), job.get("accessory", "")
        pump_type = job.get("pump_type") or "infusion"
        device = " ".join(p for p in (brand, model, iv_set) if p)
        datasets = self._repository.tuning_datasets(brand, model, iv_set, pump_type=pump_type)
        if not datasets:
            QMessageBox.information(self, tr("Tune peak window"),
                                    tr("No completed pump-cycle tests with raw data for {device}.", device=device))
            return
        engine = AppSettings.load().engine
        progress = QProgressDialog(tr("Replaying stored tests of {device}…", device=device), tr("Cancel"), 0, 1000, self)
        progress.setWindowTitle(tr("Tune peak window"))
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        lines, total = [], len(datasets)
        try:
            for done, (rate, data) in enumerate(sorted(datasets.items())):
                def step(fraction, d=done):
                    progress.setValue(int((d + fraction) / total * 1000))
                    QApplication.processEvents()
                current = self._repository.window_fractions(
                    brand, model, iv_set, rate, (engine.auto_window_fraction, engine.half_fraction), pump_type)[:2]
                result = tune(data, rate, current, engine.cycle_chains,
                              should_stop=progress.wasCanceled, progress=step)
                self._repository.save_tuning(brand, model, iv_set, result, pump_type)
                lines.append(tuning_text(result))
        except InterruptedError:
            return
        finally:
            progress.close()
        QMessageBox.information(self, tr("Tune peak window"),
                                tr("{device} — used from the next test:", device=device) + "\n\n" + "\n".join(lines))

    def _delete_selected(self) -> None:
        entry = self._row(self.table.currentRow())
        if entry is None:
            return
        kind, session, members = entry
        if kind == "job":                         # แถวงาน Calibration = ลบทุก rate ของงาน (ลบจริง ไม่มีถังพัก)
            rates = " · ".join(f'{m["config"].get("target_flow", 0):g}' for m in members)
            question = tr("Delete the whole calibration job ({n} results: {rates} ml/h) and its data permanently?",
                          n=len(members), rates=rates)
            targets = members
        else:
            question = tr("Delete this result and its data permanently?\n{date} · {rate:g} ml/h",
                          date=_date(session.get("started_at", "")), rate=session["config"].get("target_flow", 0))
            targets = [session]
        if QMessageBox.question(self, tr("Delete result"), question) == QMessageBox.StandardButton.Yes:
            for target in targets:
                self._repository.delete(target["ref"])
                self._checked.pop(target["ref"], None)
            self.reload()

    # ------------------------------------------------------------- ใบรายงาน (ติ๊กเลือก)
    def _job_members(self, session: dict) -> list[dict]:
        """ทุกผลของงานเดียวกันที่อยู่ในรายการของแท็บนี้ (Calibration หลาย rate = ใบเดียว)"""
        key = report_job_key(session)
        return [s for s in self._sessions if report_job_key(s) == key and report_service.reportable(s)] or [session]

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        entry = self._row(item.row())
        if item.column() != 0 or entry is None:
            return
        session = entry[1]
        on = item.checkState() == Qt.CheckState.Checked
        for member in self._job_members(session):
            if on:
                self._checked[member["ref"]] = member
            else:
                self._checked.pop(member["ref"], None)
        self._sync_ticks()

    def _on_select_all(self) -> None:
        on = self.select_all.isChecked()
        for session in self._visible:
            if not report_service.reportable(session):
                continue
            for member in self._job_members(session):
                if on:
                    self._checked[member["ref"]] = member
                else:
                    self._checked.pop(member["ref"], None)
        self._sync_ticks()

    def _sync_ticks(self) -> None:
        self.table.blockSignals(True)
        for row, (kind, session, members) in enumerate(self._rows):
            item = self.table.item(row, 0)
            if item is not None and report_service.reportable(session):
                on = all(m["ref"] in self._checked for m in members) if kind == "job" else session["ref"] in self._checked
                item.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
        self.table.blockSignals(False)
        self._update_ticks()

    def _update_ticks(self) -> None:
        jobs = {report_job_key(s) for s in self._checked.values()}
        shown = [s for s in self._visible if report_service.reportable(s)]
        self.select_all.blockSignals(True)
        self.select_all.setChecked(bool(shown) and all(s["ref"] in self._checked for s in shown))
        self.select_all.blockSignals(False)
        self.selected.setText(tr("{n} ticked · {jobs} report(s)", n=len(self._checked), jobs=len(jobs))
                              if self._checked else "")
        for button in (self.btn_pdf, self.btn_print):
            button.setEnabled(bool(self._checked))

    def checked_sessions(self) -> list[dict]:
        return list(self._checked.values())

    def _settings_now(self):
        if self._settings is None:
            from config.settings import AppSettings
            return AppSettings.load()
        return self._settings

    def _make_report(self, action: str) -> None:
        """บันทึก PDF / พิมพ์ ใบของงานที่ติ๊ก (ทุก rate ของงานเดียวกันเป็นใบเดียว)"""
        self._report_for(self.checked_sessions(), action)

    def _report_for(self, sessions: list[dict], action: str) -> None:
        from ui.dialogs.report_preview import ReportActions
        if not sessions:
            return
        settings = self._settings_now()
        jobs = report_service.jobs_for(self._repository, sessions, settings)
        self._report_actions = ReportActions(self, settings, self._repository)
        self._report_actions.output(jobs, action, preview=settings.report.preview_from_history)

    def _export(self) -> None:
        if not self._visible:
            QMessageBox.information(self, tr("Export"), tr("No results to show"))
            return
        choices = EXPORTERS.choices()
        filters = ";;".join(f"{text} (*.{EXPORTERS.get(key).extension})" for key, text in choices)
        default = str(Path.home() / f"DeltaM_{datetime.now():%Y%m%d_%H%M}.{EXPORTERS.get(choices[0][0]).extension}")
        path, chosen = QFileDialog.getSaveFileName(self, tr("Export"), default, filters)
        if not path:
            return
        key = next((k for k, text in choices if chosen.startswith(text)), choices[0][0])
        try:
            EXPORTERS.create(key).export(self._visible, Path(path))
        except Exception as exc:
            QMessageBox.warning(self, tr("Export"), tr("Export failed: {error}", error=exc))
            return
        QMessageBox.information(self, tr("Export"), tr("Exported {n} results to\n{path}", n=len(self._visible), path=path))

    @staticmethod
    def _open_folder() -> None:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(SESSIONS_DIR)))
