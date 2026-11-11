"""ตัวส่งออกรายงาน (exporter) — จุดต่อยอดสำหรับใบรายงาน PDF / ใบรับรองในอนาคต

เพิ่มรูปแบบใหม่:
    @EXPORTERS.register("pdf", label="PDF report (.pdf)")
    class PdfExporter(Exporter): ...
แล้วมันจะโผล่ในปุ่ม Export ของหน้า History เอง
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from core.registry import Registry


class Exporter(ABC):
    extension = ""          # เช่น "xlsx"

    @abstractmethod
    def export(self, sessions: list[dict], path: Path) -> None:
        """เขียนรายการ session (summary dict แบบเดียวกับ SessionRepository.list) ลงไฟล์"""


EXPORTERS: Registry[Exporter] = Registry("exporter")

# (หัวคอลัมน์, ฟังก์ชันดึงค่า) ของตารางสรุป
_COLUMNS = [
    ("Date", lambda s: s.get("started_at", "")),
    ("Job ID", lambda s: s["config"].get("job_id", "")),
    ("Step", lambda s: f'{s["config"].get("step_index", 0) + 1}/{s["config"].get("step_count", 1)}'),
    ("Mode", lambda s: s["config"].get("run_mode", "")),
    ("Pump type", lambda s: s["config"]["job"].get("pump_type", "")),
    ("Brand", lambda s: s["config"]["job"].get("brand", "")),
    ("Model", lambda s: s["config"]["job"].get("model", "")),
    ("Serial no.", lambda s: s["config"]["job"].get("serial_no", "")),
    ("Asset ID", lambda s: s["config"]["job"].get("asset_id", "")),
    ("Department", lambda s: s["config"]["job"].get("department", "")),
    ("Syringe / IV set", lambda s: s["config"]["job"].get("accessory", "")),
    ("Operator", lambda s: s["config"]["job"].get("operator", "")),
    ("Balance ID", lambda s: s["config"]["job"].get("balance_id", "")),
    ("Temperature (°C)", lambda s: s["config"]["job"].get("temperature_c")),
    ("Humidity (%RH)", lambda s: s["config"]["job"].get("humidity_pct")),
    ("Method", lambda s: s["config"].get("strategy", "")),
    ("Target (ml/h)", lambda s: s["config"].get("target_flow")),
    ("Mean flow (ml/h)", lambda s: s.get("mean_flow")),
    ("Error (%)", lambda s: s.get("error_pct")),
    ("CI 95% (±%)", lambda s: s.get("ci95_pct")),
    ("2 SD (±%)", lambda s: s.get("sd2_pct")),
    ("Tolerance (±%)", lambda s: s["config"].get("tolerance_pct")),
    ("Intervals", lambda s: s.get("interval_count")),
    ("Duration (s)", lambda s: s.get("duration_s")),
    ("Status", lambda s: s.get("end_reason", "")),
    ("Result", lambda s: s.get("verdict", "")),
    ("Accessories", lambda s: ", ".join(s["config"]["job"].get("accessories") or [])),
    ("Parts replaced", lambda s: ", ".join(s["config"]["job"].get("parts_replaced") or [])),
    ("Density (g/ml)", lambda s: s.get("density_g_per_ml")),
    ("Density source", lambda s: s.get("density_source", "")),
    ("Self-check baseline (g/h)", lambda s: s.get("baseline_g_per_h")),
    ("Window source", lambda s: s.get("window_source", "")),
    ("Notes", lambda s: s["config"]["job"].get("notes", "")),
]


@EXPORTERS.register("xlsx", label="Excel (.xlsx)")
class XlsxExporter(Exporter):
    extension = "xlsx"

    def export(self, sessions: list[dict], path: Path) -> None:
        from openpyxl import Workbook
        from openpyxl.styles import Font

        book = Workbook()
        sheet = book.active
        sheet.title = "Sessions"
        sheet.append([name for name, _ in _COLUMNS])
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for session in sessions:
            row = []
            for _, getter in _COLUMNS:
                try:
                    row.append(getter(session))
                except (KeyError, TypeError):
                    row.append(None)
            sheet.append(row)
        for column in sheet.columns:
            width = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column)
            sheet.column_dimensions[column[0].column_letter].width = min(40, width + 2)
        sheet.freeze_panes = "A2"
        book.save(path)
