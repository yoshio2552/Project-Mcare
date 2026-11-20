"""แผงรายละเอียดด้านขวาของหน้าประวัติ (ผู้ใช้ 2026-11-20: "เช็คประกัน, set IV, remark จากขั้นที่ 1 ได้ ไม่รก")

เลือกแถว -> เห็นสรุปทันทีโดยไม่ต้องเปิดหน้าต่าง: ผล + ตัวเลขหลัก · งาน · เครื่อง · ชุดสาย · อะไหล่/ประกัน · หมายเหตุ · Google Sheet
ปุ่ม: เปิดหน้าผล (ResultWorkspace) · เล่นซ้ำ · ใบรายงาน
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget

from config.i18n import tr
from core.capture_check import effective_verdict
from ui.icons import Glyph, glyph_icon
from ui.theme import Color
from ui.widgets.common import fmt, label

_VERDICT = {"PASS": "SUCCESS", "FAIL": "DANGER", "INVALID": "WARNING"}


def _text(value) -> str:
    return "—" if value in (None, "", []) else str(value)


class HistoryInspector(QFrame):
    open_requested = Signal()
    replay_requested = Signal()
    report_requested = Signal()
    sheet_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setProperty("card", True)
        self.setMinimumWidth(300)
        self.setMaximumWidth(460)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content = QWidget()
        self._box = QVBoxLayout(self._content)
        self._box.setContentsMargins(16, 14, 16, 14)
        self._box.setSpacing(10)
        scroll.setWidget(self._content)
        outer.addWidget(scroll, 1)
        buttons = QHBoxLayout()
        buttons.setContentsMargins(12, 6, 12, 12)
        self.btn_open = QPushButton("  " + tr("Open"))
        self.btn_open.setProperty("variant", "primary")
        self.btn_open.setIcon(glyph_icon(Glyph.OPEN, Color.ON_ACCENT, size=14))
        self.btn_replay = QPushButton("  " + tr("Replay"))
        self.btn_replay.setIcon(glyph_icon(Glyph.PLAY, Color.TEXT, size=14))
        self.btn_report = QPushButton(tr("Report"))
        for button in (self.btn_open, self.btn_replay, self.btn_report):
            buttons.addWidget(button)
        outer.addLayout(buttons)
        self.btn_sheet = QPushButton(tr("Edit in Google Sheet…"))
        self.btn_sheet.setProperty("variant", "ghost")
        self.btn_sheet.clicked.connect(self.sheet_requested)
        sheet_row = QHBoxLayout()
        sheet_row.setContentsMargins(12, 0, 12, 10)
        sheet_row.addWidget(self.btn_sheet)
        outer.addLayout(sheet_row)
        self.btn_sheet.hide()
        self.btn_open.clicked.connect(self.open_requested)
        self.btn_replay.clicked.connect(self.replay_requested)
        self.btn_report.clicked.connect(self.report_requested)
        self.show_entry(None)

    def _clear(self) -> None:
        while self._box.count():
            item = self._box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout() is not None:
                self._drop_layout(item.layout())

    def _drop_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().setParent(None)
                item.widget().deleteLater()
            elif item.layout() is not None:
                self._drop_layout(item.layout())

    def _section(self, title: str, rows: list[tuple[str, str]], colors: dict | None = None) -> None:
        self._box.addWidget(label(title.upper(), "sectionTitle"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(3)
        grid.setColumnStretch(1, 1)
        for index, (name, value) in enumerate(rows):
            name_label = label(name, "metricName")
            name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            value_label = label(value, "metricValue")
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            if colors and name in colors:
                value_label.setStyleSheet(f"color: {colors[name]};")
            grid.addWidget(name_label, index, 0)
            grid.addWidget(value_label, index, 1)
        self._box.addLayout(grid)

    def show_entry(self, entry, sheet_rows=None, reportable: bool = False, sheet_editable: bool = False) -> None:
        """entry = (kind, session, members) ของแถวในหน้าประวัติ (None = ยังไม่เลือก)"""
        self._clear()
        self.btn_sheet.setVisible(entry is not None and sheet_editable)
        for button in (self.btn_open, self.btn_replay):
            button.setEnabled(entry is not None)
        self.btn_report.setEnabled(entry is not None and reportable)
        if entry is None:
            hint = label(tr("Select a result to see its details here.\nDouble-click to open it."), "hint")
            hint.setWordWrap(True)
            self._box.addWidget(hint)
            self._box.addStretch(1)
            return
        kind, session, members = entry
        config = session.get("config") or {}
        job = config.get("job") or {}
        verdict = effective_verdict(session)
        if kind == "job":
            verdicts = [effective_verdict(m) for m in members]
            verdict = "FAIL" if "FAIL" in verdicts else "INVALID" if "INVALID" in verdicts else \
                "PASS" if verdicts and all(v == "PASS" for v in verdicts) else "N/A"
        device = " ".join(p for p in (job.get("brand"), job.get("model")) if p) or "—"
        title = label(device, "pageTitle")
        title.setWordWrap(True)
        self._box.addWidget(title)
        head = QHBoxLayout()
        color = getattr(Color, _VERDICT.get(verdict, "TEXT_MUTED"))
        pill = label(f" {tr(verdict) if verdict == 'INVALID' else verdict} ", "")
        pill.setStyleSheet(f"color: {color}; border: 1.5px solid {color}; border-radius: 10px; font-weight: 800;"
                           f" padding: 2px 10px;")
        head.addWidget(pill)
        if kind == "job":
            rates = " · ".join(f'{float((m.get("config") or {}).get("target_flow") or 0):g}' for m in members)
            head.addWidget(label(f"{rates} ml/h", "hint"), 1)
        else:
            head.addWidget(label(f'{float(config.get("target_flow") or 0):g} ml/h  ·  '
                                 f'{fmt(session.get("error_pct"), 2, " %", signed=True)}', "metricValue"), 1)
        self._box.addLayout(head)

        if kind == "job":
            rows = []
            for m in sorted(members, key=lambda m: float((m.get("config") or {}).get("target_flow") or 0)):
                rate = float((m.get("config") or {}).get("target_flow") or 0)
                rows.append((f"{rate:g} ml/h", f'{effective_verdict(m)}  ·  {fmt(m.get("error_pct"), 2, " %", signed=True)}'
                             f'  ·  {fmt(m.get("mean_flow"), 3, " ml/h")}'))
            self._section(tr("Rates"), rows)
        iv = " ".join(p for p in (job.get("accessory_brand") or "", job.get("accessory") or "") if p)
        usage = {"standard": tr("hospital standard"), "temporary": tr("temporary"),
                 "new_standard": tr("new hospital standard"), "first": tr("first time — set as standard")}
        self._section(tr("Job"), [
            (tr("Job no."), _text(job.get("job_no"))),
            (tr("Hospital / site"), _text(" · ".join(p for p in (job.get("site") or "", job.get("province") or "") if p))),
            (tr("Department"), _text(job.get("department"))),
            (tr("Operator"), _text(job.get("operator"))),
        ])
        self._section(tr("Device"), [
            (tr("Serial no."), _text(job.get("serial_no"))),
            (tr("Asset ID"), _text(job.get("asset_id"))),
            (tr("IV set / syringe"), _text(iv) + (f"  ({usage[job['accessory_usage']]})"
                                                  if job.get("accessory_usage") in usage else "")),
            (tr("Accessories"), ", ".join(job.get("accessories") or []) or "—"),
        ])
        parts = list(job.get("parts_replaced") or [])
        claims = set(job.get("parts_warranty") or [])
        part_rows = [(p, tr("warranty claim") if p in claims else tr("replaced")) for p in parts] or \
            [(tr("Parts"), tr("No parts replaced"))]
        self._section(tr("Parts and warranty"), part_rows,
                      {p: Color.SUCCESS for p in claims} | {p: Color.TEXT for p in parts if p not in claims})
        self._box.addWidget(label(tr("Remark").upper(), "sectionTitle"))
        remark = label(_text(job.get("notes")), "metricValue")
        remark.setWordWrap(True)
        remark.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._box.addWidget(remark)
        for source_name, values in (sheet_rows or [])[:2]:
            self._section(tr("Google Sheet") + " · " + source_name,
                          [(str(k), str(v)) for k, v in list(values.items())[:14] if str(v).strip()])
        self._box.addStretch(1)
