"""ตัวส่งออกรายงาน (exporter) — จุดต่อยอดสำหรับใบรายงาน PDF / ใบรับรองในอนาคต

เพิ่มรูปแบบใหม่:
    @EXPORTERS.register("key", label="ชื่อที่แสดง (.ext)")
    class MyExporter(Exporter): ...
แล้วมันจะโผล่ในปุ่ม Export ของหน้า History เอง
"pdf" = ใบรายงานแบบ Main Fable-1 ของทุกงานในรายการ รวมเป็นไฟล์เดียว (services/report) — ต้องมี QApplication
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from core.models import measured_seconds
from core.registry import Registry
from services.session_store import raw_result, volume_factor


def _verdict(summary: dict) -> str:
    from core.capture_check import effective_verdict      # ผลเก่าที่จับรอบผิด = INVALID
    return effective_verdict(summary)


class Exporter(ABC):
    extension = ""          # เช่น "xlsx"

    @abstractmethod
    def export(self, sessions: list[dict], path: Path) -> None:
        """เขียนรายการ session (summary dict แบบเดียวกับ SessionRepository.list) ลงไฟล์"""


EXPORTERS: Registry[Exporter] = Registry("exporter")

# (หัวคอลัมน์, ฟังก์ชันดึงค่า) ของตารางสรุป
_COLUMNS = [
    ("Date", lambda s: s.get("started_at", "")),
    ("Job no.", lambda s: s["config"]["job"].get("job_no", "")),
    ("Job ID", lambda s: s["config"].get("job_id", "")),
    ("Step", lambda s: f'{s["config"].get("step_index", 0) + 1}/{s["config"].get("step_count", 1)}'),
    ("Mode", lambda s: s["config"].get("run_mode", "")),
    ("Pump type", lambda s: s["config"]["job"].get("pump_type", "")),
    ("Brand", lambda s: s["config"]["job"].get("brand", "")),
    ("Model", lambda s: s["config"]["job"].get("model", "")),
    ("Serial no.", lambda s: s["config"]["job"].get("serial_no", "")),
    ("Asset ID", lambda s: s["config"]["job"].get("asset_id", "")),
    ("Hospital / site", lambda s: s["config"]["job"].get("site", "")),
    ("Province", lambda s: s["config"]["job"].get("province", "")),
    ("Department", lambda s: s["config"]["job"].get("department", "")),
    ("Syringe / IV set", lambda s: s["config"]["job"].get("accessory", "")),
    ("Syringe / IV set brand", lambda s: s["config"]["job"].get("accessory_brand", "")),
    ("IV set vs. hospital standard", lambda s: s["config"]["job"].get("accessory_usage", "")),
    ("Operator", lambda s: s["config"]["job"].get("operator", "")),
    ("Balance ID", lambda s: s["config"]["job"].get("balance_id", "")),
    ("Temperature (°C)", lambda s: s["config"]["job"].get("temperature_c")),
    ("Humidity (%RH)", lambda s: s["config"]["job"].get("humidity_pct")),
    ("Air temperature (°C)", lambda s: s["config"]["job"].get("air_temp_c")),
    ("Air pressure (hPa)", lambda s: s["config"]["job"].get("pressure_hpa")),
    ("Method", lambda s: s["config"].get("strategy", "")),
    ("Target (ml/h)", lambda s: s["config"].get("target_flow")),
    ("Mean flow (ml/h)", lambda s: s.get("mean_flow")),
    ("Error (%)", lambda s: s.get("error_pct")),
    ("Uncorrected flow (ml/h)", lambda s: raw_result(s)[0]),
    ("Uncorrected error (%)", lambda s: raw_result(s)[1]),
    ("2 SD (±%)", lambda s: s.get("sd2_pct")),
    ("Tolerance (±%)", lambda s: s["config"].get("tolerance_pct")),
    ("Intervals", lambda s: s.get("interval_count")),
    ("Measuring time (s)", lambda s: measured_seconds(s)),             # peak แรก -> ปลายรอบสุดท้าย (= ใบ)
    ("Total run time (s)", lambda s: s.get("duration_s")),             # ตั้งแต่เริ่มวัด รวมช่วงรอ peak แรก
    ("Measured mass (g)", lambda s: s.get("total_mass_g")),
    ("Mean of cycle flows (ml/h)", lambda s: s.get("mean_flow_cycles")),
    ("U k=2 (%)", lambda s: s.get("uncertainty_pct")),
    ("Status", lambda s: s.get("end_reason", "")),
    ("Result", lambda s: _verdict(s)),
    ("Accessories", lambda s: ", ".join(s["config"]["job"].get("accessories") or [])),
    ("Parts replaced", lambda s: ", ".join(s["config"]["job"].get("parts_replaced") or [])),
    ("Parts under warranty", lambda s: ", ".join(s["config"]["job"].get("parts_warranty") or [])),
    ("Density (g/ml)", lambda s: s.get("density_g_per_ml")),
    ("Density source", lambda s: s.get("density_source", "")),
    ("Air temp. used (°C)", lambda s: (s.get("correction") or {}).get("air_temp_c")),
    ("Humidity used (%RH)", lambda s: (s.get("correction") or {}).get("humidity_pct")),
    ("Pressure used (hPa)", lambda s: (s.get("correction") or {}).get("pressure_hpa")),
    ("Air density (kg/m³)", lambda s: (s.get("correction") or {})["air_density_g_per_ml"] * 1000.0),
    ("Z factor (ml/g)", lambda s: volume_factor(s)),
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


@EXPORTERS.register("pdf", label="PDF report (.pdf)")
class PdfExporter(Exporter):
    """ใบรายงานของทุกงานในรายการ (ทุก rate ของงานเดียวกัน = ใบเดียว) ต่อกันเป็น PDF ไฟล์เดียว · Quick Test ข้าม"""
    extension = "pdf"

    def __init__(self, repository=None, settings=None, lang: str | None = None):
        self.repository, self.settings, self.lang = repository, settings, lang

    def export(self, sessions: list[dict], path: Path) -> None:
        from config.settings import AppSettings
        from services.report import layout, render, service
        from services.session_store import get_repository
        repository = self.repository or get_repository()
        settings = self.settings or AppSettings.load()
        jobs = [job for job in service.jobs_for(repository, sessions, settings) if job.rates]
        if not jobs:
            raise ValueError("no Calibration / Inspection job with a usable flow result")
        lang = self.lang or service.language(settings)
        render.save_pdf(render.render_pdf_sync(layout.html_document(jobs, lang)), Path(path))
