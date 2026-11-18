"""ทดสอบใบรายงาน PDF (แบบ Main Fable-1): รวมผลเป็นใบ, เลือกผลราย rate, หน้า HTML, สร้าง PDF ด้วย QtWebEngine
(offscreen), ตรวจล้นกระดาษกับข้อมูลยาวสุด, บันทึกทับไฟล์ที่เปิดค้าง

รัน:  python -m unittest tests.test_report -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from services.report import checklist, demo, layout
from services.report.model import ReportInfo, ReportOptions, collect, group_jobs
from services.report.text import Words

app = QApplication.instance() or QApplication([])


def _jobs(long=False):
    return demo.jobs(long=long)


class ModelTest(unittest.TestCase):
    def test_groups_by_job_and_skips_quick_test(self):
        sessions, _ = demo.sample_sessions()
        quick = dict(sessions[0], ref="99")
        quick["config"] = dict(sessions[0]["config"], run_mode="quick_test", job_id="Q")
        groups = group_jobs(sessions + [quick])
        self.assertEqual([len(g) for g in groups], [1, 1, 3, 3])

    def test_calibration_combines_rates_sorted(self):
        cal = _jobs()[2]
        self.assertEqual(cal.kind, "calibration")
        self.assertEqual([r.set_rate for r in cal.rates], [10.0, 50.0, 200.0])
        self.assertEqual(cal.rates[1].n, 58)
        self.assertEqual(cal.file_name("th"), "MCI-0142_Calibration_TH.pdf")
        self.assertEqual(cal.file_name("en"), "MCI-0142_Calibration_EN.pdf")
        self.assertTrue(cal.overall_pass())
        self.assertEqual(cal.warnings, [])

    def test_invalid_and_incomplete_rates_are_left_out_with_warning(self):
        sessions, intervals = demo.sample_sessions()
        group = [dict(s) for s in sessions if s["config"]["job_id"] == "J-CAL-INF"]
        group[0]["verdict"] = "INVALID"                 # 10 ml/h ใช้ไม่ได้
        group[2]["end_reason"] = "stopped"              # 200 ml/h หยุดกลางทาง
        job = collect(group, lambda ref: intervals.get(ref, []), None, ReportOptions())
        self.assertEqual([r.set_rate for r in job.rates], [50.0])
        texts = [text for text, _ in job.warnings]
        self.assertEqual(sum("no usable result" in t for t in texts), 2)
        self.assertTrue(any("planned rates" in t for t in texts))

    def test_latest_valid_run_used_when_a_retry_is_invalid(self):
        sessions, intervals = demo.sample_sessions()
        group = [dict(s) for s in sessions if s["config"]["job_id"] == "J-CAL-INF"]
        retry = dict(group[1], ref="77", started_at="2026-11-17T12:00:00", verdict="INVALID", mean_flow=60.0)
        job = collect(group + [retry], lambda ref: intervals.get(ref, []), None, ReportOptions())
        self.assertAlmostEqual(job.rates[1].measured, 50.42)
        self.assertTrue(any("earlier valid run" in t for t, _ in job.warnings))

    def test_pump_cycle_counts_chain_a_only(self):
        sessions, intervals = demo.sample_sessions()
        session = sessions[0]
        ivs = intervals["1"]
        doubled = ivs + [dict(iv, chain=1, index=iv["index"] + 1000) for iv in ivs]
        job = collect([session], lambda ref: doubled, None, ReportOptions())
        self.assertEqual(job.rates[0].n, len(ivs))
        self.assertEqual(len(job.rates[0].series), len(ivs))

    def test_info_row_overrides_job(self):
        info = ReportInfo.merged({"contact": "ก", "checks": {"visual.pole_clamp": "pass"}},
                                 {"contact": "ข", "leak_ua": 350, "occl_runs": [1, 2]})
        self.assertEqual(info.contact, "ข")
        self.assertEqual(info.checks, {"visual.pole_clamp": "pass"})
        self.assertEqual(info.occl_runs, [1, 2, None])
        self.assertEqual(info.safety_status(300), checklist.FAIL)

    def test_fail_items_make_overall_fail(self):
        job = _jobs()[0]
        self.assertTrue(job.overall_pass())
        job.info.checks = dict(job.info.checks, **{"visual.pole_clamp": checklist.FAIL})
        self.assertFalse(job.overall_pass())
        job = _jobs()[0]
        job.info.leak_ua = 301
        self.assertFalse(job.overall_pass())

    def test_missing_report_data_listed(self):
        sessions, intervals = demo.sample_sessions()
        group = [s for s in sessions if s["config"]["job_id"] == "J-CAL-SYR"]
        bare = [dict(s, config=dict(s["config"], job=dict(s["config"]["job"], checks={}))) for s in group]
        job = collect(bare, lambda ref: intervals.get(ref, []), None, ReportOptions())
        texts = [t for t, _ in job.missing()]
        self.assertTrue(any("checklist" in t for t in texts))
        self.assertTrue(any("leakage" in t for t in texts))
        self.assertTrue(any("Occlusion" in t for t in texts))

    def test_checklist_exceptions_and_version(self):
        full = {key: checklist.PASS for key in checklist.all_keys("infusion")}
        full["visual.door_lock"] = checklist.FAIL
        full.pop("performance.battery")                       # ยังไม่ตรวจ
        stored = checklist.compress("infusion", full)
        self.assertEqual(stored, {"visual.door_lock": "fail", "performance.battery": ""})
        back = checklist.expand("infusion", stored, 1)
        self.assertEqual(back["visual.door_lock"], "fail")
        self.assertEqual(back["visual.pole_clamp"], "pass")
        self.assertNotIn("performance.battery", back)
        self.assertEqual(checklist.expand("infusion", {}, 0), {})              # งานเก่า: ไม่เดาว่าผ่าน
        self.assertEqual(checklist.describe("infusion", checklist.expand("infusion", {}, 1), "th"), "ผ่านทุกข้อ")
        checklist.ADDED_IN[2] = {"visual.pole_clamp"}                           # จำลองรายการใหม่ในรุ่น 2
        try:
            self.assertNotIn("visual.pole_clamp", checklist.expand("infusion", {}, 1))
        finally:
            checklist.ADDED_IN.pop(2)

    def test_thai_date_is_buddhist_era(self):
        self.assertEqual(Words("th").date("2026-11-17T09:10:00"), "17 พ.ย. 2569")
        self.assertEqual(Words("en").date("2026-11-17T09:10:00"), "17 Nov 2026")


class LayoutTest(unittest.TestCase):
    def test_brand_not_repeated(self):
        self.assertEqual(layout.join_brand("TOP", "TOP-2300"), "TOP-2300")
        self.assertEqual(layout.join_brand("ME", "ME 20 Drops/ml"), "ME 20 Drops/ml")
        self.assertEqual(layout.join_brand("Terumo", "TE-171"), "Terumo TE-171")
        self.assertEqual(layout.join_brand("B", "Braun 50"), "B Braun 50")         # ไม่ตัดกลางคำ
        self.assertEqual(layout.join_brand("", "LF-600"), "LF-600")

    def test_flow_steps_are_joined_despite_rounding(self):
        """ช่วงต่อเนื่องที่เวลาปัดเศษ (ต่างกัน ~0.001 s) ต้องต่อเป็นเส้นเดียว · ช่องว่างจริง (ช่วงหาย) ยังเว้นไว้"""
        from services.report.charts import flow_chart
        from services.report.text import Words
        series = [(0.0, 0.9516, 9.0), (0.95162, 1.9101, 9.1), (1.91005, 2.8580, 10.0), (4.8, 5.75, 9.5)]
        svg = flow_chart(Words("th"), "infusion", series, 10.0, 9.5, 5.0, 698, 290)
        path = svg.split('<path d="', 1)[1].split('"', 1)[0]
        self.assertEqual(path.count("M"), 2)                 # ต่อ 3 ช่วงแรก + เริ่มใหม่หลังช่องว่างจริง

    def test_graph_options(self):
        from services.report.charts import MOVING, ORANGE, flow_chart
        from services.report.text import Words
        series = [(i * 0.25, (i + 1) * 0.25, 50 + (i % 3)) for i in range(20)]
        step = flow_chart(Words("th"), "infusion", series, 50, 51, 5, 698, 290)
        self.assertIn("<path", step)
        self.assertIn(ORANGE, step)
        self.assertNotIn(MOVING, step)
        points = flow_chart(Words("th"), "infusion", series, 50, 51, 5, 698, 290, style="points", show_mean=False, moving=True)
        self.assertIn("<polyline", points)
        self.assertIn("<circle", points)
        self.assertIn(MOVING, points)
        self.assertIn("ค่าเฉลี่ยสะสม", points)
        self.assertNotIn(ORANGE, points)
        job = _jobs()[0]
        job.options.chart_style, job.options.chart_moving = "points", True
        self.assertIn(MOVING, layout.html_document([job], "th"))

    def test_minute_axis_one_minute_when_room(self):
        from services.report.charts import _time_steps
        self.assertEqual(_time_steps(6.1, 638)[1], 1)        # หน้า 2 Inspection: ทุก 1 นาที
        self.assertEqual(_time_steps(14.7, 638)[1], 1)
        self.assertEqual(_time_steps(15.0, 312)[1], 2)       # กราฟเล็กหน้าเทคนิค: ป้ายห่างพอ ไม่ชน
        label = _time_steps(240.0, 312)[1]
        self.assertGreaterEqual(312 * label / 240.0, 34)     # รัน 4 ชม. ยังไม่ชน
        self.assertLessEqual(240.0 / label, 10)

    def test_page_counts(self):
        jobs = _jobs()
        self.assertEqual([len(layout.pages(j, "th")) for j in jobs], [2, 2, 3, 3])
        long = _jobs(long=True)
        self.assertEqual([len(layout.pages(j, "th")) for j in long], [2, 2, 4, 4])     # 6 rate -> หน้าเทคนิค 2 หน้า
        for job in jobs + long:
            self.assertEqual(layout.page_count(job), len(layout.pages(job, "en")))

    def test_user_text_is_escaped(self):
        job = _jobs()[0]
        job.job["site"] = "<b>รพ. & คลินิก</b>"
        html = layout.html_document([job], "th")
        self.assertIn("&lt;b&gt;รพ. &amp; คลินิก&lt;/b&gt;", html)
        self.assertNotIn("<b>รพ.", html)

    def test_syringe_calibration_uses_pink(self):
        cal_syr = _jobs()[3]
        html = layout.html_document([cal_syr], "th")
        self.assertIn('class="page a2 syringe tech"', html)
        self.assertIn("#B0306A", html)
        self.assertIn("ตัวยึดกระบอกฉีด", html)      # รายการตรวจของ syringe

    def test_no_uncertainty_shows_dash(self):
        job = _jobs(long=True)[2]
        html = layout.html_document([job], "th")
        self.assertIn("ความไม่แน่นอน U ยังไม่ได้ประเมินในรายงานนี้", html)

    def test_fonts_are_embedded_not_downloaded(self):
        html = layout.html_document(_jobs()[:1], "en")
        self.assertIn("font/ttf;base64", html)
        self.assertNotIn("fonts.googleapis.com", html)


class RenderTest(unittest.TestCase):
    """สร้าง PDF จริงด้วย QtWebEngine — ตรวจทุกหน้าว่าไม่ล้นกระดาษ ไม่มีตัวอักษรเล็กกว่า 12 px และใช้ฟอนต์ Sarabun ที่ฝังไว้"""

    def _render(self, jobs, lang):
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtPdf import QPdfDocument
        from services.report import render
        data, checks = render.check_layout_sync(layout.html_document(jobs, lang))
        self.assertIsNotNone(data)
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertEqual(render.layout_problems(checks), [], lang)
        self.assertTrue(all(item.get("sarabun") for item in checks))
        buffer = QBuffer()
        buffer.setData(QByteArray(data))
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        doc = QPdfDocument()
        doc.load(buffer)
        self.assertEqual(doc.pageCount(), sum(layout.page_count(j) for j in jobs))
        size = doc.pagePointSize(0)
        self.assertAlmostEqual(size.width(), 595.3, delta=1.0)      # A4
        self.assertAlmostEqual(size.height(), 841.9, delta=1.0)
        return checks

    def test_sample_fits_without_shrinking(self):
        for lang in ("th", "en"):
            checks = self._render(_jobs(), lang)
            self.assertTrue(all(item.get("fit") == 0 for item in checks), checks)

    def test_longest_data_fits(self):
        for lang in ("th", "en"):
            self._render(_jobs(long=True), lang)

    def test_save_over_open_file_reports_locked(self):
        from services.report.render import FileLockedError, save_pdf, unique_path
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "MCI-0001_Inspection_TH.pdf"
            save_pdf(b"%PDF-1.4 first", target)
            self.assertEqual(target.read_bytes(), b"%PDF-1.4 first")
            self.assertEqual(unique_path(target).name, "MCI-0001_Inspection_TH (2).pdf")
            with open(target, "rb"):                 # เปิดค้างแบบโปรแกรมอ่าน PDF -> แทนที่ไม่ได้
                with self.assertRaises(FileLockedError):
                    save_pdf(b"%PDF-1.4 second", target)
            self.assertEqual(target.read_bytes(), b"%PDF-1.4 first")     # ไฟล์เดิมไม่เสีย
            self.assertEqual([p.name for p in Path(tmp).iterdir()], [target.name])   # ไม่มีไฟล์ชั่วคราวค้าง


if __name__ == "__main__":
    unittest.main()
