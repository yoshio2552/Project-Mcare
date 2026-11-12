"""หน้า History: ผลทดสอบที่บันทึกไว้ แยกแท็บตามโหมด — ค้นหา กรอง เปิดดู ลบ ส่งออกไฟล์

- เพิ่มคอลัมน์: เพิ่ม 1 บรรทัดใน COLUMNS
- เพิ่มรูปแบบไฟล์ส่งออก: ลงทะเบียน exporter ใหม่ใน services/exporters.py
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox,
    QPushButton, QTabBar, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from config.constants import SESSIONS_DIR
from config.i18n import tr
from services.exporters import EXPORTERS
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
    ("Result", lambda s: str(s.get("verdict", "")), False),
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
_VERDICT_COLORS = {"PASS": Color.SUCCESS, "FAIL": Color.DANGER}


def _date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d  %H:%M")
    except ValueError:
        return iso


class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self._repository = get_repository()
        self._sessions: list[dict] = []      # ของแท็บปัจจุบัน
        self._visible: list[dict] = []       # หลังกรอง (ตรงกับแถวในตาราง)

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
        self.btn_delete = QPushButton(tr("Delete"))
        self.btn_delete.setProperty("variant", "danger")
        self.btn_delete.setStyleSheet("padding: 7px 14px; font-size: 13px;")
        for button in (refresh, export, open_folder, self.btn_delete):
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
        for text, value in ((tr("All results"), ""), ("PASS", "PASS"), ("FAIL", "FAIL")):
            self.result_filter.addItem(text, value)
        self.count = label("", "hint")
        filters.addWidget(self.search, 1)
        filters.addWidget(self.result_filter)
        filters.addWidget(self.count)
        layout.addLayout(filters)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([tr(name) for name, _, _ in COLUMNS])
        for col, (_, _, right) in enumerate(COLUMNS):
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
        self.table.itemSelectionChanged.connect(lambda: self.btn_delete.setEnabled(self.table.currentRow() >= 0))
        self.reload()

    # ------------------------------------------------------------- ข้อมูล
    def reload(self, *_) -> None:
        self._sessions = self._repository.list(MODE_TABS[max(0, self.tabs.currentIndex())][0])
        self._apply_filter()

    def _apply_filter(self, *_) -> None:
        words = self.search.text().lower().split()
        verdict = self.result_filter.currentData()

        def matches(session: dict) -> bool:
            if verdict and str(session.get("verdict", "")) != verdict:
                return False
            if not words:
                return True
            job = session.get("config", {}).get("job") or {}
            haystack = " ".join(str(v) for v in (*job.values(), session.get("started_at", ""),
                                                 session.get("config", {}).get("job_id", ""))).lower()
            return all(word in haystack for word in words)

        self._visible = [s for s in self._sessions if matches(s)]
        self._fill_table()

    def _fill_table(self) -> None:
        self.table.setRowCount(len(self._visible))
        for row, session in enumerate(self._visible):
            for col, (name, getter, right) in enumerate(COLUMNS):
                try:
                    text = getter(session)
                except (KeyError, TypeError, ValueError):
                    text = "—"
                item = QTableWidgetItem(text)
                align = Qt.AlignmentFlag.AlignRight if right else Qt.AlignmentFlag.AlignLeft
                item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if name == "Result" and text in _VERDICT_COLORS:
                    item.setForeground(QColor(_VERDICT_COLORS[text]))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table.setItem(row, col, item)
        self.table.clearSelection()
        self.table.setCurrentCell(-1, -1)
        self.btn_delete.setEnabled(False)
        self.empty.setVisible(not self._visible)
        self.count.setText(tr("{shown} of {total}", shown=len(self._visible), total=len(self._sessions)))

    # ------------------------------------------------------------- คำสั่ง
    def _open_detail(self, row: int) -> None:
        try:
            detail = self._repository.load(self._visible[row]["ref"])
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, tr("History"), tr("Could not open this result: {error}", error=exc))
            return
        SessionDetailDialog(self, detail).exec()

    def _delete_selected(self) -> None:
        row = self.table.currentRow()
        if not 0 <= row < len(self._visible):
            return
        session = self._visible[row]
        answer = QMessageBox.question(
            self, tr("Delete result"),
            tr("Delete this result and its data permanently?\n{date} · {rate:g} ml/h",
               date=_date(session.get("started_at", "")), rate=session["config"].get("target_flow", 0)),
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._repository.delete(session["ref"])
            self.reload()

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
