"""ทดสอบรอบ 6.20 (2026-11-20): เติมข้อมูลงานทันที (ฐานข้อมูลสะสม) · เลขงานแยกคำนำหน้า · การระเหยระหว่างวัด
(แบบจำลอง + evaporation trap + งบความไม่แน่นอน) · วันครบกำหนดตราชั่ง · แบตเตอรี่/การอุดตันแยกชนิด · โหมดไทยกึ่งอังกฤษ
· กราฟ/เวลาในใบ · ผู้ติดต่อ "-"

รัน:  python -m unittest tests.test_autofill_evaporation -v
"""
import math
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from config.settings import AppSettings, EngineSettings, EvaporationSettings, ReportSettings, UncertaintySettings
from core import evaporation
from core.corrections import gravimetric_correction
from core.models import JobInfo, PumpType, TestPlan, join_job_no, pump_from_prefix, split_job_no
from services.autofill import Autofill
from services.job_suggestions import JobSuggester
from services.report import demo, layout
from services.report.text import Words
from tests.test_report_ui import _TmpRepo

app = QApplication.instance() or QApplication([])


class EvaporationModelTest(unittest.TestCase):
    def test_physical_constants(self):
        # CIPM-2007: psv(20 °C) = 2339.3 Pa · Marrero & Mason: D_AB(20 °C, 1 atm) ≈ 2.42e-5 m²/s
        self.assertAlmostEqual(evaporation.saturation_pressure(20.0), 2339.3, delta=1.0)
        self.assertAlmostEqual(evaporation.saturation_pressure(25.0), 3169.9, delta=1.5)
        self.assertAlmostEqual(evaporation.diffusion_coefficient(20.0, 101325.0), 2.42e-5, delta=0.03e-5)
        # Sh ต่อเนื่องพอที่รอยต่อช่วง (< 10 %)
        for ra in (200.0, 2.2e4, 8e6):
            low, high = evaporation.sherwood(ra * 0.999), evaporation.sherwood(ra * 1.001)
            self.assertLess(abs(high - low) / low, 0.10)

    def test_rate_is_plausible_and_behaves(self):
        open_dish = evaporation.estimate(50, 0, 22, 22, 50, 1013.25)
        mm_per_day = open_dish.rate_g_per_h * 24 / open_dish.area_mm2 * 1000     # g -> mm³ ÷ พื้นที่
        self.assertGreater(mm_per_day, 1.0)          # น้ำนิ่งในห้อง ~1–5 mm/วัน (ตรวจความสมเหตุสมผล)
        self.assertLess(mm_per_day, 6.0)
        deeper = evaporation.estimate(50, 40, 22, 22, 50, 1013.25)
        self.assertLess(deeper.rate_g_per_h, open_dish.rate_g_per_h)               # ผิวน้ำลึกจากปาก = ระเหยน้อยลง
        humid = evaporation.estimate(50, 20, 22, 22, 80, 1013.25)
        dry = evaporation.estimate(50, 20, 22, 22, 30, 1013.25)
        self.assertLess(humid.rate_g_per_h, dry.rate_g_per_h)
        self.assertEqual(evaporation.estimate(50, 20, 22, 22, 100, 1013.25).rate_g_per_h, 0.0)  # อิ่มตัว = ไม่ระเหย
        warm = evaporation.estimate(50, 20, 28, 28, 50, 1013.25)
        self.assertGreater(warm.rate_g_per_h, evaporation.estimate(50, 20, 22, 22, 50, 1013.25).rate_g_per_h)
        # ค่าที่ได้ = Δρv·A / (h/D + 1/h_m) ตรวจซ้ำด้วยมือ (สอบย้อนได้)
        e = evaporation.estimate(50, 20, 22, 22, 50, 1013.25)
        manual = e.delta_rho_v * e.area_mm2 * 1e-6 / (e.resistance_headspace + e.resistance_convection) * 3.6e6
        self.assertAlmostEqual(manual, e.rate_g_per_h, places=9)

    def test_decide_methods_and_level(self):
        s = EvaporationSettings()
        trap = evaporation.decide(s, True, -0.05, 22, 22, 50, 1013.25, 50, 600)
        self.assertEqual((trap.method, trap.baseline_g_per_h), ("trap", 0.0))
        self.assertGreater(trap.model_g_per_h, 0.0)                   # ยังคิดค่าไว้แสดงขีดฆ่าในใบ
        auto_sc = evaporation.decide(s, False, -0.05, 22, 22, 50, 1013.25)
        self.assertEqual((auto_sc.method, auto_sc.baseline_g_per_h), ("self_check", -0.05))
        auto = evaporation.decide(s, False, None, 22, 22, 50, 1013.25, 50, 600)
        self.assertEqual(auto.method, "model")
        self.assertAlmostEqual(auto.baseline_g_per_h, -auto.model_g_per_h)
        self.assertLess(auto.detail["headspace_end_mm"], auto.detail["headspace_start_mm"])   # น้ำสูงขึ้นระหว่างวัด
        s.method = "off"
        self.assertEqual(evaporation.decide(s, False, None, 22, 22, 50, 1013.25).baseline_g_per_h, 0.0)
        s.method, s.start_volume_ml = "model", 135.0
        self.assertIn("warning", evaporation.decide(s, False, None, 22, 22, 50, 1013.25, 50, 600).detail)  # ล้นภาชนะ

    def test_correction_and_uncertainty(self):
        from core import uncertainty
        engine, evap = EngineSettings(), EvaporationSettings()
        job = JobInfo(temperature_c=22.0, air_temp_c=22.0, humidity_pct=50.0, pressure_hpa=1013.25)
        corrected = gravimetric_correction(job, engine, evaporation=evap, rate_ml_h=10.0, duration_s=600)
        self.assertEqual(corrected.evaporation_method, "model")
        self.assertGreater(corrected.net_flow(10.0), gravimetric_correction(job, engine).net_flow(10.0))   # ชดเชยน้ำที่หาย
        job.evaporation_trap = "yes"
        trapped = gravimetric_correction(job, engine, evaporation=evap, rate_ml_h=10.0, duration_s=600)
        self.assertEqual((trapped.evaporation_method, trapped.baseline_g_per_h), ("trap", 0.0))
        job.evaporation_trap = ""
        evap.default_trap = True                                      # ค่าตั้งต้นในหน้าตั้งค่า (แผนเก่าไม่ได้ระบุ)
        self.assertEqual(gravimetric_correction(job, engine, evaporation=evap).evaporation_method, "trap")
        from dataclasses import asdict
        summary = dict(total_mass_g=1.7, total_time_s=600.0, mean_flow=10.2, ml_per_g=1.003)
        u = UncertaintySettings()
        model_budget = uncertainty.budget(dict(summary, correction=asdict(corrected)), u)
        trap_budget = uncertainty.budget(dict(summary, correction=asdict(trapped)), u)
        comp = lambda b: next(c for c in b["components"] if c["name"] == "Evaporation / self-check")  # noqa: E731
        self.assertGreater(comp(model_budget)["u_rel_pct"], comp(trap_budget)["u_rel_pct"])


class JobNumberTest(unittest.TestCase):
    def test_split_and_join(self):
        self.assertEqual(split_job_no("MCI26-2201"), ("MCI", "26-2201"))
        self.assertEqual(split_job_no("mcs-9"), ("mcs", "-9"))
        self.assertEqual(split_job_no("26-22"), ("", "26-22"))
        self.assertEqual(split_job_no("INF-7", {"infusion": "INF-"}), ("INF-", "7"))
        self.assertEqual(join_job_no("MCI", " 26-1 "), "MCI26-1")
        self.assertEqual(join_job_no("MCI", ""), "")
        self.assertEqual(pump_from_prefix("mcs"), "syringe")
        self.assertIsNone(pump_from_prefix("XYZ"))


class AutofillMemoryTest(_TmpRepo):
    def test_remember_and_lookup(self):
        book = Autofill(self.repo, JobSuggester([]))
        book.remember({"site": "รพ.ทดสอบ", "province": "ขอนแก่น", "model": "TE-171", "brand": "Terumo",
                       "pump_type": "infusion", "accessory": "TI*PU200L", "accessory_brand": "Terumo",
                       "serial_no": "S-1", "asset_id": "A-1", "department": "ICU"})
        self.assertEqual(book.province("  รพ.ทดสอบ "), "ขอนแก่น")
        self.assertEqual(book.model_info("te-171"), {"brand": "Terumo", "pump_type": "infusion"})
        self.assertEqual(book.accessory_brand("ti*pu200l", "infusion"), "Terumo")
        self.assertEqual(book.accessory_brand("ti*pu200l", "syringe"), "")      # คนละชนิดเครื่อง
        self.assertEqual(book.device("s-1")["department"], "ICU")
        self.assertEqual(book.device("", "a-1")["model"], "TE-171")
        # จังหวัดใหม่ "เฉพาะงานนี้" -> ไม่ทับของเดิม · "จำทับ" -> ค่าล่าสุด
        book.remember({"site": "รพ.ทดสอบ", "province": "มหาสารคาม", "model": "TE-171", "serial_no": "S-1"},
                      province_update=False)
        self.assertEqual(book.province("รพ.ทดสอบ"), "ขอนแก่น")
        self.assertEqual(book.device("S-1")["province"], "ขอนแก่น")
        book.remember({"site": "รพ.ทดสอบ", "province": "มหาสารคาม"})
        self.assertEqual(book.province("รพ.ทดสอบ"), "มหาสารคาม")
        book.remember({"site": "รพ.ขีด", "province": "-"})                     # "-" = ไม่มีข้อมูล ไม่จำ
        self.assertEqual(book.province("รพ.ขีด"), "")

    def test_history_fallback(self):
        history = [{"site": "รพ.เก่า", "province": "ลำปาง", "model": "LF-600", "brand": "LifeFlow",
                    "pump_type": "infusion", "serial_no": "OLD-1"}]
        book = Autofill(self.repo, JobSuggester(history))
        self.assertEqual(book.province("รพ.เก่า"), "ลำปาง")                   # ไม่มีในตาราง -> จากประวัติผล
        self.assertEqual(book.model_info("LF-600")["brand"], "LifeFlow")
        self.assertEqual(book.device("old-1")["site"], "รพ.เก่า")

    def test_wizard_fills_and_asks_before_overwriting_province(self):
        from ui.dialogs.test_wizard import TestWizard
        Autofill(self.repo, JobSuggester([])).remember(
            {"site": "รพ.A", "province": "ขอนแก่น", "model": "TE-331", "brand": "Terumo", "pump_type": "syringe",
             "serial_no": "SN-9", "department": "ER", "accessory": "BD 50 ml", "accessory_brand": "BD"})
        w = TestWizard(None, self.repo, self.settings)
        e = w._job_edits
        e["serial_no"].setText("SN-9")                                          # S/N -> ทุกช่องของเครื่อง
        self.assertEqual([e[n].text() for n in ("site", "province", "model", "brand", "department", "accessory")],
                         ["รพ.A", "ขอนแก่น", "TE-331", "Terumo", "ER", "BD 50 ml"])
        self.assertEqual(w._pump_type.currentData(), "syringe")
        self.assertEqual(w._job_prefix.text(), "MCS")
        e["province"].setText("อุดรธานี")
        asked = []
        w._ask_province_change = lambda site, old, new: asked.append((site, old, new)) or None
        self.assertFalse(w._check_site_province())                            # กลับไปแก้
        w._ask_province_change = lambda *a: asked.append(a) or False
        self.assertTrue(w._check_site_province())                             # เฉพาะงานนี้
        self.assertEqual(len(asked), 2)
        w._remember_autofill(w._read_job())
        self.assertEqual(Autofill(self.repo, JobSuggester([])).province("รพ.A"), "ขอนแก่น")
        w.close()

    def test_new_settings_load_and_upgrade(self):
        r = ReportSettings(default_occl_level="M", default_occl_unit="mmHg", default_occl_low=300, default_occl_high=900)
        r.upgrade()
        self.assertEqual(r.occlusion_defaults("syringe"), {"level": "M", "unit": "mmHg", "low": 300, "high": 900})
        self.assertEqual(r.occlusion_defaults("infusion")["level"], "M")
        self.assertEqual((r.default_occl_level, r.default_occl_low), ("", 0.0))

    def test_settings_page_new_groups(self):
        from ui.pages.settings import GROUPS, REPORT_TABS, TABS, SettingsPage
        from ui.widgets.date_field import DateField
        placed = [g for _, cols in TABS + REPORT_TABS for col in cols for g in col]
        self.assertEqual(sorted(placed), sorted(title for title, _ in GROUPS))
        page = SettingsPage(self.settings)
        editor = next(e for f, e in page._editors if f.name == "due_date")
        self.assertIsInstance(editor, DateField)
        editor.setText("2027-01-12")
        next(e for f, e in page._editors if f.name == "prefix_syringe").setText("SYR")
        page._save()
        self.assertEqual((self.settings.balance.due_date, self.settings.jobs.prefix_syringe), ("2027-01-12", "SYR"))
        editor.setText("")
        page._save()
        self.assertEqual(self.settings.balance.due_date, "")
        page.close()


class ReportTextTest(unittest.TestCase):
    def test_mix_language(self):
        insp = demo.jobs()[0]
        page = layout.Doc(insp, "mix").inspection_page(1, 2)
        self.assertIn("Inspection Report", page)                      # ชื่อใบ = ศัพท์เทคนิค
        self.assertIn("Visual inspection", page)
        self.assertNotIn("VISUAL INSPECTION", page)                    # หัวข้ออังกฤษแล้ว ไม่มีป้ายซ้ำ
        self.assertIn("Battery", page)                                 # ชื่อรายการตรวจ = อังกฤษ
        self.assertIn("ใช้งานได้มากกว่า 120 นาที", page)                    # รายละเอียด = ไทย
        self.assertIn("โรงพยาบาล", page)                                # ข้อมูลลูกค้า = ไทย
        self.assertIn("17 พ.ย. 2569", page)                             # วันที่ไทย
        self.assertIn("Inspected by", page)                            # บทบาทผู้ลงนาม = อังกฤษ
        self.assertIn(">Pass<", page)
        self.assertEqual(Words("mix").lang, "th")
        self.assertTrue(insp.file_name("mix").endswith("_TH-EN.pdf"))
        th = layout.Doc(insp, "th").inspection_page(1, 2)
        self.assertIn("ตรวจสภาพภายนอก", th)
        self.assertIn("VISUAL INSPECTION", th)
        en = layout.Doc(insp, "en").inspection_page(1, 2)
        self.assertNotIn("ตรวจสภาพภายนอก", en)

    def test_language_setting(self):
        from services.report.service import language
        settings = AppSettings()
        settings.report.language = "mix"
        self.assertEqual(language(settings), "mix")
        settings.report.language = "xx"
        self.assertEqual(language(settings), "th")

    def test_charts_labels(self):
        from services.report.charts import flow_chart, vgauge
        series = [(i * 0.25, (i + 1) * 0.25, 50 + (i % 3)) for i in range(4)]
        svg = flow_chart(Words("mix"), "infusion", series, 50, 51, 5, 328, 196)
        self.assertIn("Time (min)", svg)
        self.assertIn(">1</text>", svg)                                # ป้ายนาทีสุดท้ายไม่ถูกซ่อน
        self.assertNotIn("Error%", vgauge(Words("th"), "infusion", 1.0, 0.5, 5, 196))

    def test_contact_dash_balance_dates_and_evaporation(self):
        job = demo.jobs()[2]
        job.info.contact, job.info.contact_phone = "-", " - "
        job.options.balance_cal_date, job.options.balance_due_date = "2026-01-12", "2027-01-12"
        job.env.update(evap_method="trap", evap_model=0.034)
        page = layout.Doc(job, "th").calibration_summary(2, 3)
        self.assertIn("<dt>ผู้ติดต่อ</dt><dd>—</dd>", page)
        self.assertIn("<dt>สอบเทียบเมื่อ</dt><dd>12 ม.ค. 2569</dd>", page)
        self.assertIn("<dt>ครบกำหนดสอบเทียบ</dt><dd>12 ม.ค. 2570</dd>", page)
        self.assertIn("<s>0.034 g/h</s>", page)
        self.assertIn("evaporation trap", page)
        job.env.update(evap_method="model", evap_model=0.034)
        page = layout.Doc(job, "en").calibration_summary(2, 3)
        self.assertIn("0.034 g/h", page)
        self.assertIn("calculated · corrected", page)
        job.options.balance_cal_date = job.options.balance_due_date = ""
        self.assertNotIn("ครบกำหนดสอบเทียบ", layout.Doc(job, "th").calibration_summary(2, 3))


if __name__ == "__main__":
    unittest.main()
