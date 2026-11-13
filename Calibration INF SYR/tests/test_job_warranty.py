"""ทดสอบงานรอบ 2026-11-13: เลขงาน MCI/MCS, ประกันอะไหล่, ฐานข้อมูล v5, ชุดสายมาตรฐานของโรงพยาบาล,
เติมยี่ห้อ/ชนิดจากรุ่น, ขั้นตรวจเครื่องแบบใหม่ และมุมมองกราฟ Full / Auto / Zoom

รัน:  python -m unittest discover -s tests -v
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from config.settings import AppSettings, UiSettings
from core import warranty
from core.models import JobInfo, PumpType, TestPlan, job_no_for_pump, pump_from_job_no
from core.warranty import PartRecord
from services.job_suggestions import JobSuggester
from services.session_store import SCHEMA_VERSION, Repository

app = QApplication.instance() or QApplication([])


class _Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.repo = Repository(self.root / "t.db", self.root / "s")

    def tearDown(self):
        self.repo.close()
        self._tmp.cleanup()


class JobNumberTest(unittest.TestCase):
    def test_prefix_and_pump(self):
        self.assertEqual(pump_from_job_no("MCI-0012"), "infusion")
        self.assertEqual(pump_from_job_no("mcs123"), "syringe")
        self.assertIsNone(pump_from_job_no("J-1"))
        self.assertEqual(job_no_for_pump("", "syringe"), "MCS")
        self.assertEqual(job_no_for_pump("MCI-0012", "syringe"), "MCS-0012")     # เปลี่ยนเฉพาะคำนำหน้า
        self.assertEqual(job_no_for_pump("OTHER-1", "infusion"), "OTHER-1")      # เลขรูปแบบอื่น ไม่แตะ


class WarrantyTest(unittest.TestCase):
    def test_status_and_month_end(self):
        self.assertEqual(warranty.add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        s = warranty.status("2025-11-13", "2026-11-13")
        self.assertEqual((s.state, s.days_left), ("active", 0))                  # วันสุดท้ายยังอยู่ในประกัน
        self.assertEqual(warranty.status("2025-11-13", "2026-11-14").state, "late")
        self.assertEqual(warranty.status("2025-11-13", "2026-12-13").state, "late")
        self.assertEqual(warranty.status("2025-11-13", "2026-12-14").state, "expired")
        self.assertEqual(warranty.status("2025-11-13", "2027-01-01", months=24).state, "active")

    def test_start_never_restarts_while_covered(self):
        history = [PartRecord("Battery", "2026-01-10", "2026-01-10")]
        today = "2026-06-01"
        self.assertEqual(warranty.start_for([], "Battery", today), today)                        # ครั้งแรก
        self.assertEqual(warranty.start_for(history, "battery", today, claimed=True), "2026-01-10")
        self.assertEqual(warranty.start_for(history, "Battery", today, claimed=False), "2026-01-10")
        self.assertEqual(warranty.start_for(history, "Keypad", today), today)                    # นับใครนับมัน
        late = "2027-01-20"
        self.assertEqual(warranty.start_for(history, "Battery", late, claimed=True), "2026-01-10")
        self.assertEqual(warranty.start_for(history, "Battery", late, claimed=False), late)      # ซื้อชิ้นใหม่
        self.assertEqual(warranty.start_for(history, "Battery", "2027-06-01", claimed=False), "2027-06-01")

    def test_summary_keeps_claims_on_original_start(self):
        records = [PartRecord("Battery", "2026-01-10", "2026-01-10"),
                   PartRecord("battery", "2026-05-01", "2026-01-10", claimed=True),
                   PartRecord("Display", "2024-01-01", "2024-01-01")]
        rows = warranty.summarize(records, "2026-06-01")
        self.assertEqual([r.part for r in rows], ["battery", "Display"])
        self.assertEqual((rows[0].first_at, rows[0].times, rows[0].claims), ("2026-01-10", 2, 1))
        self.assertEqual(rows[1].status.state, "expired")


class RepositoryV5Test(_Tmp):
    def _job(self, **kw):
        base = dict(pump_type=PumpType.INFUSION, brand="Terumo", model="TE-112", serial_no="S1", site="รพ.A")
        base.update(kw)
        return JobInfo(**base)

    def test_parts_history_and_warranty_start(self):
        self.repo.record_parts("J1", self._job(parts_replaced=["Battery", "Keypad"]), today="2026-01-10")
        self.repo.record_parts("J2", self._job(parts_replaced=["Battery"], parts_warranty=["Battery"]), today="2026-04-01")
        history = self.repo.part_history(self._job())
        self.assertEqual([(r.part, r.replaced_at, r.warranty_start, r.claimed) for r in history],
                         [("Battery", "2026-01-10", "2026-01-10", False), ("Keypad", "2026-01-10", "2026-01-10", False),
                          ("Battery", "2026-04-01", "2026-01-10", True)])
        self.assertEqual(self.repo.part_history(self._job(serial_no="S2")), [])            # คนละเครื่อง
        self.assertEqual(self.repo.part_history(self._job(brand="")), history)              # ไม่กรอกยี่ห้อก็ยังหาเจอ
        self.repo.record_parts("J2", self._job(parts_replaced=[]), today="2026-04-01")       # แทนที่ของ job เดิม
        self.assertEqual(len(self.repo.part_history(self._job())), 2)
        self.repo.delete_parts("J1")
        self.assertEqual(self.repo.part_history(self._job()), [])

    def test_site_standard(self):
        self.assertIsNone(self.repo.site_standard("รพ.A", "Terumo", "TE-112", "infusion"))
        self.repo.set_site_standard("รพ.A", "Terumo", "TE-112", "infusion", "TS-PN200", "Terumo")
        self.assertEqual(self.repo.site_standard("รพ.a ", "", "te-112", "infusion")["iv_set"], "TS-PN200")
        self.assertIsNone(self.repo.site_standard("รพ.A", "Terumo", "TE-112", "syringe"))
        self.assertIsNone(self.repo.site_standard("รพ.B", "Terumo", "TE-112", "infusion"))

    def test_migrates_v4_sessions(self):
        path = self.root / "v4.db"
        db = sqlite3.connect(path)
        db.executescript("""
            CREATE TABLE sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL, mode TEXT NOT NULL,
              job_id TEXT, step_index INTEGER, step_count INTEGER, pump_type TEXT, brand TEXT, model TEXT, iv_set TEXT,
              serial_no TEXT, asset_id TEXT, department TEXT, operator TEXT, target_flow REAL, mean_flow REAL,
              error_pct REAL, verdict TEXT, end_reason TEXT, folder TEXT, summary_json TEXT NOT NULL);
            CREATE TABLE profiles (brand TEXT, model TEXT, pump_type TEXT, iv_set TEXT, stroke_volume_ml REAL,
              runs INTEGER, updated_at TEXT, calibrated_at TEXT DEFAULT '', PRIMARY KEY (brand, model, pump_type, iv_set));
            PRAGMA user_version = 4;
        """)
        db.execute("INSERT INTO sessions (started_at, mode, summary_json) VALUES ('2026-11-01', 'inspection', '{}')")
        db.commit()
        db.close()
        repo = Repository(path, self.root / "s2")
        self.assertTrue((self.root / "v4.v4-backup.db").is_file())
        self.assertTrue({"job_no", "site", "province", "iv_set_brand", "iv_set_usage"} <= repo._columns("sessions"))
        self.assertEqual(repo._db.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
        self.assertEqual(repo._db.execute("SELECT count(*) FROM sessions").fetchone()[0], 1)
        repo.close()


class SuggesterTest(unittest.TestCase):
    def test_model_infers_brand_and_type(self):
        history = [
            {"pump_type": "syringe", "brand": "Terumo", "model": "TE-331", "accessory": "BD 50 ml", "accessory_brand": "BD"},
            {"pump_type": "infusion", "brand": "Terumo", "model": "TE-112", "accessory": "TS-PN200", "accessory_brand": "Terumo",
             "site": "รพ.A", "province": "ขอนแก่น"},
        ]
        s = JobSuggester(history)
        self.assertEqual(s.infer_device("te-331"), {"brand": "Terumo", "pump_type": "syringe"})
        self.assertEqual(s.infer_device("unknown"), {"brand": "", "pump_type": ""})
        self.assertEqual(s.infer_accessory_brand("bd 50 ML"), "BD")
        self.assertEqual(s.suggest("province", {"site": "รพ.A"}), ["ขอนแก่น"])
        self.assertEqual(s.suggest("job_no", {}), [])                     # เลขงานไม่เสนอ


class WizardTest(_Tmp):
    def _wizard(self, settings=None):
        from ui.dialogs.test_wizard import TestWizard
        return TestWizard(None, self.repo, settings or AppSettings())

    def test_job_prefix_follows_pump_type_both_ways(self):
        w = self._wizard()
        edit = w._job_edits["job_no"]
        self.assertEqual(edit.text(), "MCI")
        w._pump_type.setCurrentIndex(w._pump_type.findData("syringe"))
        self.assertEqual(edit.text(), "MCS")
        edit.setText("MCI-77")
        w._on_job_no_edited("MCI-77")
        self.assertEqual(w._pump_type.currentData(), "infusion")
        self.assertEqual(w._read_job().job_no, "MCI-77")
        edit.setText("MCI")
        self.assertEqual(w._read_job().job_no, "")                         # มีแต่คำนำหน้า = ยังไม่ได้กรอก
        self.assertEqual(w._job_labels["accessory"].text(), "IV set")
        w.close()

    def test_model_autofill_waits_for_confirmation(self):
        w = self._wizard()
        w._suggester = JobSuggester([{"pump_type": "syringe", "brand": "Terumo", "model": "TE-331"}])
        w._job_edits["model"].setText("TE-331")
        w._on_model_changed()
        self.assertEqual(w._job_edits["brand"].text(), "")                 # ยังไม่กรอกให้
        self.assertEqual(w._job_edits["brand"].preview, "Terumo")          # แสดงจาง
        self.assertEqual(w._pump_type.suggested(), "syringe")
        self.assertEqual(w._pump_type.currentData(), "infusion")
        w._on_model_confirmed()                                           # Tab / Enter
        self.assertEqual(w._job_edits["brand"].text(), "Terumo")
        self.assertEqual(w._pump_type.currentData(), "syringe")
        self.assertEqual(w._job_labels["accessory"].text(), "Syringe used")
        self.assertIsNone(w._pump_type.suggested())
        w.close()

    def test_checklists_reset_and_plan_carries_warranty(self):
        from core.models import RunMode
        from ui.dialogs.test_wizard import PAGE_CHECK, TestWizard
        initial = TestPlan(job=JobInfo(brand="ACME", model="P1", accessories=["Battery"], parts_replaced=["Keypad"]),
                           job_id="J-old")
        w = TestWizard(None, self.repo, AppSettings(), initial)
        self.assertEqual((w._accessories.values(), w._parts.values()), ([], []))     # เริ่มว่างทุกครั้ง
        w._parts.search.setText("key")
        w._parts.search.refresh()
        w._parts.search._commit()                                            # Enter = ติ๊ก แล้วล้างช่อง
        self.assertEqual(w._parts.values(), ["Keypad"])
        self.assertEqual(w._parts.search.text(), "")
        w._parts.tick("Battery", warranty=True)
        w._pages.setCurrentIndex(PAGE_CHECK)
        asked = []
        TestWizardEmpty = type(w)
        w._confirm_empty_lists = lambda: asked.append(True) or False         # อุปกรณ์ที่ติดมาว่าง -> ถาม
        w._on_next()
        self.assertEqual((asked, w._pages.currentIndex()), ([True], PAGE_CHECK))
        w._accessories.tick("Power cord")
        del w._confirm_empty_lists
        self.assertTrue(TestWizardEmpty._confirm_empty_lists(w))            # ครบแล้ว ไม่ถาม
        w._choose_mode(RunMode.INSPECTION)
        w._strategy.setCurrentIndex(w._strategy.findData("time_interval"))
        w._on_next()
        job = w.plan.job
        self.assertEqual(sorted(job.parts_replaced), ["Battery", "Keypad"])
        self.assertEqual(job.parts_warranty, ["Battery"])
        self.assertEqual(job.balance_id, "GF300  S/N 14654769")
        w.close()

    def test_accessory_standard_prompt(self):
        w = self._wizard()
        e = w._job_edits
        for name, value in (("site", "รพ.A"), ("brand", "Terumo"), ("model", "TE-112"), ("accessory", "TS-PN200")):
            e[name].setText(value)
        self.assertTrue(w._check_accessory_standard())
        self.assertEqual(w._accessory_usage, "first")
        self.repo.set_site_standard("รพ.A", "Terumo", "TE-112", "infusion", "TS-PN200", "Terumo")
        self.assertTrue(w._check_accessory_standard())
        self.assertEqual(w._accessory_usage, "standard")
        e["accessory"].setText("Other set")
        answers = iter([None, "temporary"])
        w._ask_accessory_change = lambda *a: next(answers)
        self.assertFalse(w._check_accessory_standard())                  # กลับไปแก้
        self.assertTrue(w._check_accessory_standard())
        self.assertEqual(w._accessory_usage, "temporary")
        w._ask_accessory_change = lambda *a: self.fail("asked twice for the same values")
        self.assertTrue(w._check_accessory_standard())
        e["accessory"].setText("")
        w._refresh_standard()
        self.assertEqual(e["accessory"].preview, "TS-PN200")              # เสนอชุดสายมาตรฐาน (จาง)
        w.close()


class ControllerPartsTest(_Tmp):
    def test_parts_recorded_at_plan_creation_and_replaced_plan_cleared(self):
        from services import session_store
        from services.session_controller import SessionController
        previous = session_store._repository                 # ห้ามเรียก get_repository() — จะเปิด data/ จริง
        session_store.set_repository(self.repo)
        self.addCleanup(session_store.set_repository, previous)
        settings = AppSettings()
        settings.source = "simulator"
        controller = SessionController(settings)
        job = JobInfo(brand="ACME", model="P1", serial_no="S9", parts_replaced=["Battery"])
        controller.set_plan(TestPlan(job=job))
        self.assertEqual([r.part for r in self.repo.part_history(job)], ["Battery"])
        controller.set_plan(TestPlan(job=JobInfo(brand="ACME", model="P1", serial_no="S9", parts_replaced=["Keypad"])))
        self.assertEqual([r.part for r in self.repo.part_history(job)], ["Keypad"])     # แผนแรกยังไม่เริ่ม -> ลบ


class GraphRangeTest(unittest.TestCase):
    def test_modes(self):
        import pyqtgraph as pg
        from ui.plots.weight import WeightPlot
        ui = UiSettings()
        widget = pg.PlotWidget()                                           # ต้องถือไว้ ไม่งั้นถูกเก็บกวาด
        plot = WeightPlot(widget.getPlotItem(), ui)
        ui.graph_range = "auto"
        self.assertEqual(plot.view_width_s(), ui.rolling_window_s)         # ยังไม่รู้คาบ
        plot.period_s = 20.0
        self.assertEqual(plot.view_width_s(), 120.0)                       # 6 รอบ
        ui.graph_range = "zoom"
        self.assertEqual(plot.view_width_s(), 60.0)
        ui.graph_range = "full"
        self.assertIsNone(plot.view_width_s())
        self.assertEqual(plot._visible_x(500.0), (0.0, 500.0))
        plot.range_mode = "zoom"                                           # หน้าประวัติ/โมดูลกำหนดเอง
        self.assertEqual(plot._visible_x(500.0), (440.0, 500.0))


if __name__ == "__main__":
    unittest.main()
