"""รอบ 6.21 (2026-11-20): ความปลอดภัยบีกเกอร์ · เล่นซ้ำผลเก่า (+ HTML) · Google Sheet · slope รอครบหน้าต่าง ·
กราฟโหมดเต็มวาดไม่เกินจำนวนจุดที่กำหนด · บรรทัดที่ตราชั่งส่งมาแต่ถูกปฏิเสธเก็บตัวอย่างไว้"""
import io
import json
import os
import tempfile
import unittest
import urllib.request
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

from config.settings import AppSettings, EngineSettings
from core.beaker import Beaker, PumpRunningDetector, level, minutes_to, predict


class BeakerMathTest(unittest.TestCase):
    def test_water_fill_and_levels(self):
        beaker = Beaker(capacity_ml=150, empty_g=68, known=True)
        self.assertAlmostEqual(beaker.water_ml(68 + 99.8), 100.0, places=3)
        self.assertAlmostEqual(beaker.fill_pct(68 + 149.7), 100.0, places=2)
        self.assertTrue(beaker.removed(0.01))
        self.assertFalse(beaker.removed(70))
        self.assertEqual(level(50, 85, 95), "ok")
        self.assertEqual(level(90, 85, 95), "warn")
        self.assertEqual(level(96, 85, 95), "alarm")

    def test_prediction_includes_allowance(self):
        beaker = Beaker(150, 68, True)
        p = predict(beaker, 68 + 100 * 0.998, rate_ml_h=200, minutes=10, allowance_min=3, warn_pct=85, alarm_pct=95)
        self.assertAlmostEqual(p.added_ml, 200 * 13 / 60)
        self.assertEqual(p.level, "alarm")                       # 100 + 43 = 143 ml = 95.6 %
        self.assertAlmostEqual(minutes_to(beaker, 68, 60, 100), 150.0)

    def test_pump_running_detector(self):
        d = PumpRunningDetector(window_s=10, rise_g=0.02)
        for i in range(30):
            d.add(i, 100 + 0.01 * i)                             # 36 ml/h ไหลอยู่
        self.assertTrue(d.running())
        self.assertAlmostEqual(d.rate_ml_h(), 0.01 / 0.998 * 3600, delta=1)
        d.reset()
        for i in range(30):
            d.add(i, 100 - 0.0001 * i)                           # หยุด (ระเหยเล็กน้อย)
        self.assertFalse(d.running())


class BeakerGuardTest(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        from services.beaker_guard import BeakerGuard
        self.settings = AppSettings()
        self.guard = BeakerGuard(self.settings)
        self.alerts = []
        self.guard.alert_changed.connect(self.alerts.append)

    def feed(self, weight):
        self.guard._last_check = 0
        self.guard.on_weight(weight)

    def test_no_alarm_until_beaker_is_set(self):
        self.feed(68 + 149)
        self.assertIsNone(self.guard.current())

    def test_warn_alarm_ack_and_remove(self):
        g = self.guard
        g.set_beaker(150, 68)
        self.feed(68 + 50)
        self.assertIsNone(g.current())
        self.feed(68 + 133)
        self.assertEqual(g.current().kind, "warn")
        self.feed(68 + 146)
        self.assertEqual(g.current().kind, "overflow")
        g.acknowledge("overflow")
        self.feed(68 + 147)
        self.assertNotEqual(getattr(g.current(), "kind", None), "overflow")      # รับทราบแล้ว เงียบ
        self.feed(0.0)                                                           # ยกบีกเกอร์ออก
        self.assertEqual(g.current().kind, "zero")
        self.feed(68 + 10)                                                       # วางกลับ (เทน้ำแล้ว)
        self.assertIsNone(g.current())
        self.assertEqual(g.status().level, "ok")

    def test_start_check_predicts_overflow(self):
        g = self.guard
        g.set_beaker(150, 68)
        self.feed(68 + 120)
        self.assertIsNotNone(g.start_check(50, 30))              # 120 + 27.5 ml > 95 %
        self.assertIsNone(g.start_check(1, 10))
        self.settings.safety.check_before_start = False
        self.assertIsNone(g.start_check(50, 30))

    def test_disabled_does_nothing(self):
        self.settings.safety.enabled = False
        self.guard.set_beaker(150, 68)
        self.feed(68 + 149)
        self.assertIsNone(self.guard.current())


class SlopeWaitsForFullWindowTest(unittest.TestCase):
    def test_no_slope_before_window_is_full(self):
        from core.engine import FlowEngine
        from core.models import EndMode, Sample, SessionConfig, StartMode
        config = SessionConfig(target_flow=50.0, strategy="pump_cycle", end_mode=EndMode.TIME,
                               start_mode=StartMode.IMMEDIATE, duration_min=5)
        engine = FlowEngine(config, EngineSettings(regression_window=40, cycle_half_window=20, window_mode="manual",
                                                   warmup_s=0))
        slopes = [engine.process(Sample(i * 0.2, 100 + i * 0.2 * 50 / 3600)).slope_flow for i in range(60)]
        self.assertTrue(all(s is None for s in slopes[:39]))
        self.assertIsNotNone(slopes[39])


class FullViewPointsTest(unittest.TestCase):
    def test_full_view_is_capped(self):
        from ui.plots.base import FULL_VIEW_POINTS, SeriesStore
        store = SeriesStore(2, 40000)
        for i in range(20000):
            store.append(i * 0.2, float(i))
        x, _ = store.view(None)
        self.assertLessEqual(len(x), FULL_VIEW_POINTS)
        self.assertEqual(x[0], 0.0)                              # ยังเห็นตั้งแต่จุดแรก
        x, _ = store.view(20000 * 0.2 - 60)                      # ซูม 60 s ยังละเอียดทุกจุด
        self.assertGreaterEqual(len(x), 300)


class RejectedLinesTest(unittest.TestCase):
    def test_samples_kept(self):
        from hardware.serial_balance import Diagnostics
        d = Diagnostics()
        for raw in (b"EC,E01\r\n", b"EC,E01\r\n", b"+0144.804  g\r\n"):
            d.note_rejected(1.0, raw)
        self.assertEqual(d.rejected, 3)
        self.assertEqual(len(d.rejected_samples), 2)
        self.assertIn("EC,E01", d.rejected_samples[0])


def _write_session(folder: Path, chains: int = 1):
    """ผลจำลองแบบจับรอบ: raw.csv.gz + intervals.csv เหมือนที่โปรแกรมบันทึก"""
    import gzip
    folder.mkdir(parents=True, exist_ok=True)
    t = np.arange(0, 300, 0.2)
    rate_g_s = 50 / 3600
    w = 100 + rate_g_s * t + 0.004 * np.sin(2 * np.pi * t / 15)
    with gzip.open(folder / "raw.csv.gz", "wt") as f:
        f.write("t_s,weight_g\n")
        for a, b in zip(t, w):
            f.write(f"{a:.4f},{b:.4f}\n")
    origin = 5.0
    rows = ["index,chain,t_s,duration_s,flow_ml_h,error_pct,flow_raw_ml_h,error_raw_pct,volume_ml,"
            "t_start_s,t_end_s,w_start_g,w_end_g"]
    start, index = origin, 0
    while start + 15 <= 290:
        end = start + 15
        ws, we = np.interp(start, t, w), np.interp(end, t, w)
        flow = (we - ws) / 15 * 3600
        rows.append(f"{index},A,{end - origin:.4f},15,{flow:.4f},{(flow - 50) / 50 * 100:.4f},{flow:.4f},"
                    f"{(flow - 50) / 50 * 100:.4f},{flow * 15 / 3600:.5f},{start:.4f},{end:.4f},{ws:.4f},{we:.4f}")
        start, index = end, index + 1
    (folder / "intervals.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return index


class ReplayTest(unittest.TestCase):
    def test_replay_matches_saved_intervals_and_exports_html(self):
        from services.replay_export import build_html
        from services.replay_session import build, frame_values
        from services.session_store import SessionDetail
        tmp = Path(tempfile.mkdtemp())
        n = _write_session(tmp / "s1")
        summary = {"folder": str(tmp / "s1"), "origin_s": 5.0, "regression_window": 20, "ml_per_g": 1.0,
                   "config": {"target_flow": 50.0, "tolerance_pct": 5.0, "strategy": "pump_cycle"}}
        import gzip
        import csv
        with gzip.open(tmp / "s1" / "raw.csv.gz", "rt") as f:
            samples = [(float(a), float(b)) for a, b in list(csv.reader(f))[1:]]
        data = build(SessionDetail(summary=summary, samples=samples))
        intervals = [r for r in data.results if r.interval is not None]
        self.assertEqual(len(intervals), n)
        self.assertAlmostEqual(data.t_start, -5.0, places=3)                     # เวลา 0 = peak แรก
        self.assertEqual(len([r for r in data.results if r.extremum is not None]), n + 1)
        values = frame_values(data, len(data.results))
        self.assertAlmostEqual(values["mean"], 50.0, delta=0.5)
        self.assertEqual(values["count"], n)
        html = build_html(data, {"title": "T", "rows": [("a", "b")], "verdict": "PASS"}, {"play": "Play"})
        self.assertIn("<canvas", html)
        payload = html.split('type="application/json">')[1].split("</script>")[0]
        body = json.loads(payload)
        self.assertEqual(len(body["data"]["intervals"]), n)


class SheetsTest(unittest.TestCase):
    def setUp(self):
        from services import sheets
        self.sheets = sheets
        self.tmp = Path(tempfile.mkdtemp())
        sheets.set_store(sheets.SheetStore(self.tmp / "cache.json"))

    def tearDown(self):
        self.sheets.set_store(None)

    def test_csv_link_and_column_guess(self):
        s = self.sheets
        url = "https://docs.google.com/spreadsheets/d/ABC_123/edit#gid=77"
        self.assertEqual(s.csv_url(url), "https://docs.google.com/spreadsheets/d/ABC_123/export?format=csv&gid=77")
        guess = s.guess_columns(["เลขงาน", "โรงพยาบาล", "S/N", "รุ่น", "หมายเหตุ", "อื่นๆ"])
        self.assertEqual(guess, {"เลขงาน": "job_no", "โรงพยาบาล": "site", "S/N": "serial_no", "รุ่น": "model",
                                 "หมายเหตุ": "notes"})

    def test_fetch_lookup_and_write(self):
        s = self.sheets
        csv_text = "เลขงาน,โรงพยาบาล,S/N,รุ่น\nMCI26-871,รพ.สุโขทัย,2008010167,LF-630\n,,,\n"
        calls = []

        def opener(request, timeout):
            calls.append(request)
            if isinstance(request, urllib.request.Request) and request.data:
                return json.dumps({"ok": True, "row": 2}).encode()
            if "action=read" in request.full_url:
                return json.dumps({"ok": True, "headers": ["Job", "Status"],
                                   "rows": [["MCI26-871", "done"]]}).encode()
            return csv_text.encode("utf-8")

        settings = AppSettings()
        settings.sheets.sources = [{"id": "a", "name": "CSV", "kind": "csv", "url": "https://x/pub?output=csv"},
                                   {"id": "b", "name": "Script", "kind": "script", "url": "https://script/exec",
                                    "token": "t", "columns": {"Job": "job_no"}}]
        results = s.sync_all(settings, opener)
        self.assertEqual([r[0] for r in results], ["CSV", "Script"])
        store = s.store()
        found = store.lookup("job_no", " mci26-871 ")
        self.assertEqual(found["site"], "รพ.สุโขทัย")
        self.assertEqual(found["model"], "LF-630")
        rows = store.rows_for({"job_no": "MCI26-871"})
        self.assertEqual(len(rows), 2)                           # ทั้งสองแหล่ง
        source = store.source("b")
        self.assertEqual(s.write_row(source, "MCI26-871", {"Status": "sent", "New": "x"}, opener=opener), 2)
        body = json.loads(calls[-1].data.decode())
        self.assertEqual(body["key_column"], "Job")
        self.assertEqual(body["values"], {"Status": "sent", "New": "x"})
        store.update_cached(source, "Job", "MCI26-871", {"New": "x"})
        self.assertIn("New", store.state("b")["headers"])
        with self.assertRaises(IOError):
            s.write_row(store.source("a"), "MCI26-871", {"x": "1"}, opener=opener)    # CSV อ่านอย่างเดียว

    def test_html_page_instead_of_csv_is_reported(self):
        s = self.sheets
        source = s.SheetSource.from_dict({"kind": "csv", "url": "https://docs.google.com/spreadsheets/d/X/edit"})
        with self.assertRaises(IOError):
            s.fetch(source, opener=lambda r, t: b"<!doctype html><html>login</html>")


if __name__ == "__main__":
    unittest.main()


from tests.test_report_ui import _TmpRepo      # noqa: E402  ฐานข้อมูลชั่วคราว + ผลตัวอย่าง (ไม่แตะ data/ จริง)


class WorkspaceHistoryTest(_TmpRepo):
    def test_workspace_tabs_switch_rates_and_keep_report_buttons(self):
        from ui.dialogs.result_workspace import TABS, ResultWorkspace
        members = self.repo.job_sessions("J-CAL-INF")
        calls = []
        dialog = ResultWorkspace(None, members, self.repo, self.settings, on_report=calls.append)
        self.assertEqual(dialog.tabs.count(), len(TABS))
        self.assertEqual(len(dialog._rate_buttons), 3)
        for index in (0, 3, 4, 5):
            dialog.tabs.setCurrentIndex(index)
        dialog.show_member(2)
        self.assertTrue(dialog._rate_buttons[2].isChecked())
        dialog.btn_pdf.click()
        self.assertEqual(calls, ["save"])
        dialog.close()

    def test_history_columns_panel_and_open(self):
        from ui.pages.history import COLUMNS, DEFAULT_VISIBLE, HistoryPage
        page = HistoryPage(self.settings)
        names = [n for n, _, _ in COLUMNS]
        for name in names:
            self.assertEqual(page.table.isColumnHidden(names.index(name) + 1), name not in DEFAULT_VISIBLE, name)
        page._set_column("Operator", True)
        self.assertIn("Operator", self.settings.ui.history_columns)
        row = next(i for i, (k, _, _) in enumerate(page._rows) if k == "job")
        page.table.setCurrentCell(row, 2)
        self.assertTrue(page.inspector.btn_open.isEnabled())
        opened = []
        import ui.dialogs.result_workspace as ws
        original = ws.ResultWorkspace.exec
        ws.ResultWorkspace.exec = lambda self: opened.append(len(self.members)) or 0
        try:
            page._open_detail(row, force=True)                  # ดับเบิลคลิกแถวงาน = เปิดหน้าผลทุก rate
        finally:
            ws.ResultWorkspace.exec = original
        self.assertEqual(opened, [3])
        page.close()

    def test_report_info_tabs_save_remark_and_advanced(self):
        from services.report import service as report_service
        from ui.dialogs.report_info import ReportInfoDialog
        job = report_service.job_for_plan(self.repo, "J-CAL-SYR", self.settings)
        dialog = ReportInfoDialog(None, job)
        self.assertGreaterEqual(dialog.tabs.count(), 4)
        self.assertFalse(dialog.advanced.isVisibleTo(dialog))
        dialog.show_advanced.setChecked(True)
        self.assertTrue(dialog.advanced.isVisibleTo(dialog))
        dialog.notes.setPlainText("สายแพรหลวม")
        dialog.device_edits["accessory_brand"].setText("Terumo")
        dialog.accessories.setText("Pole clamp, Drop sensor")
        report_service.save_info(self.repo, job, dialog.result_info(), dialog.device_values())
        stored = self.repo.job_record("J-CAL-SYR")[0]
        self.assertEqual(stored["notes"], "สายแพรหลวม")
        self.assertEqual(stored["accessory_brand"], "Terumo")
        self.assertEqual(stored["accessories"], ["Pole clamp", "Drop sensor"])
        dialog.close()


class Round622Test(_TmpRepo):
    def test_history_pages_newest_first(self):
        from ui.pages.history import HistoryPage
        self.settings.ui.history_page_rows = 2
        page = HistoryPage(self.settings)
        self.assertEqual(len([r for r in page._rows if r[0] != "rate"]), 2)
        self.assertGreater(page._hidden, 0)
        self.assertTrue(page.btn_more.isVisibleTo(page))
        page._show_more(None)
        self.assertEqual(page._hidden, 0)
        page.search.setText("x")
        page._apply_filter()                                    # ค้นหาใหม่ = กลับไปหน้าแรก
        self.assertEqual(page._page, 2)
        page.close()

    def test_plot_header_does_not_force_a_wide_window(self):
        from config.settings import UiSettings
        from ui.plots import IntervalPlot
        from ui.plots.cell import PlotCell
        cell = PlotCell(IntervalPlot, UiSettings())
        self.assertLess(cell.minimumSizeHint().width(), 300)
        cell.resize(300, 200)
        cell.show()
        cell.header.resize(300, 26)
        cell.header._fit()
        self.assertTrue(cell.header._compact)                   # ชื่อเส้นย่อเหลือสัญลักษณ์

    def test_smooth_scroll_never_goes_back(self):
        from config.settings import UiSettings
        from core.models import EngineResult, SessionConfig
        from ui.plots import WeightPlot
        from ui.plots.cell import PlotCell
        ui = UiSettings(graph_range="zoom", graph_zoom_s=10)
        cell = PlotCell(WeightPlot, ui)                          # เก็บตัว cell ไว้ (ไม่งั้น Qt ลบกราฟทิ้ง)
        plot = cell.module
        plot.begin_session(SessionConfig(target_flow=10))
        plot.smooth = True
        plot.feed([EngineResult(t=i * 0.2, weight=1.0) for i in range(100)])        # ถึง 19.8 s
        right = plot.plot.viewRange()[0][1]
        self.assertTrue(plot.smooth_advance(0.1))
        self.assertGreater(plot.plot.viewRange()[0][1], right)
        ahead = plot.plot.viewRange()[0][1]
        plot.feed([EngineResult(t=19.9, weight=1.0)])            # จุดใหม่มาช้ากว่าที่เลื่อนไป: ไม่ถอยหลัง
        self.assertGreaterEqual(plot.plot.viewRange()[0][1], ahead - 1e-9)

    def test_review_reminder_and_idle_flow(self):
        from PySide6.QtWidgets import QDialog
        from services.beaker_guard import BeakerGuard
        from ui.widgets.attention import AttentionReminder
        dialog = QDialog()
        reminder = AttentionReminder(dialog, 30, "test")
        self.assertTrue(reminder._timer.isActive())
        reminder._tick()
        self.assertEqual(reminder.count, 1)
        dialog.done(0)
        self.assertFalse(reminder._timer.isActive())
        guard = BeakerGuard(self.settings)
        guard.set_beaker(150, 68)
        self.settings.safety.idle_flow_min = 0.0001
        import time as _time
        start = _time.monotonic()
        for i in range(40):                                     # น้ำไหลเรื่อยๆ ทั้งที่ไม่ได้ทดสอบ
            guard.detector.add(start - 40 + i, 100 + 0.01 * i)
        guard.weight = 100.4
        guard._idle_flow_since = start - 60
        guard._check_idle_flow()
        self.assertEqual(guard._active["remind"].title, guard._idle_title())

    def test_recall_fills_job_number(self):
        from ui.dialogs.test_wizard import TestWizard
        wizard = TestWizard(None, self.repo, self.settings)
        wizard._on_recall({"brand": "Terumo", "model": "TE-171", "serial_no": "S9", "job_no": "MCI26-871",
                           "pump_type": "infusion"})
        self.assertEqual(wizard._job_prefix.text(), "MCI")
        self.assertEqual(wizard._job_edits["job_no"].text(), "26-871")
        wizard._job_edits["job_no"].setText("999")
        wizard._on_recall({"model": "TE-171", "serial_no": "S9", "job_no": "MCI26-871"})
        self.assertEqual(wizard._job_edits["job_no"].text(), "999")              # ที่พิมพ์ไว้ไม่ทับ
        wizard.close()
