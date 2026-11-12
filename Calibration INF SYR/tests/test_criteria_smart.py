"""ทดสอบ: กุญแจ ยี่ห้อ + รุ่น + ชนิดเครื่อง + ชุดสาย (รวม migration ฐานข้อมูลเก่า), เกณฑ์ช่วงก่อนวัดแยกกลุ่ม,
และช่องกรอกที่เสนอค่า (ghost text) ของ wizard

รัน:  python -m unittest discover -s tests -v
"""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import AppSettings, EngineSettings, PrerunSettings, prerun_group
from core.models import JobInfo, PumpType, SessionConfig, StartMode
from core.prerun import PreRun
from hardware.simulator import SimulatedBalance
from config.settings import SimulatorSettings
from services.job_suggestions import JobSuggester
from services.session_store import Repository


class _Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class PumpKeyTest(_Tmp):
    def test_type_and_set_are_separate(self):
        repo = Repository(self.root / "t.db", self.root / "s")
        repo.add_observation("ACME", "X1", "SET A", 50.0, 14.0, 50.0, pump_type="infusion")
        self.assertIsNotNone(repo.get_profile("acme", "x1", "set a", "infusion"))
        self.assertIsNone(repo.get_profile("ACME", "X1", "SET A", "syringe"))       # คนละชนิด
        self.assertIsNone(repo.get_profile("ACME", "X1", "SET B", "infusion"))      # คนละชุดสาย
        repo.save_prerun_criteria("ACME", "X1", "SET A", "syringe", "syringe_time", {"blocks": 6})
        self.assertEqual(repo.prerun_criteria("acme", "x1", "set a", "syringe", "syringe_time"), {"blocks": 6})
        self.assertIsNone(repo.prerun_criteria("ACME", "X1", "SET A", "infusion", "syringe_time"))
        repo.save_prerun_criteria("ACME", "X1", "SET A", "syringe", "syringe_time", None)
        self.assertIsNone(repo.prerun_criteria("ACME", "X1", "SET A", "syringe", "syringe_time"))
        repo.close()

    def test_migrates_v1_database_without_losing_data(self):
        path = self.root / "old.db"
        db = sqlite3.connect(path)
        db.executescript("""
            CREATE TABLE sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL, mode TEXT NOT NULL,
              job_id TEXT, step_index INTEGER, step_count INTEGER, pump_type TEXT, brand TEXT, model TEXT, iv_set TEXT,
              serial_no TEXT, asset_id TEXT, department TEXT, operator TEXT, target_flow REAL, mean_flow REAL,
              error_pct REAL, verdict TEXT, end_reason TEXT, folder TEXT, summary_json TEXT NOT NULL);
            CREATE TABLE profiles (brand TEXT, model TEXT, iv_set TEXT, stroke_volume_ml REAL, runs INTEGER,
              updated_at TEXT, PRIMARY KEY (brand, model, iv_set));
            CREATE TABLE profile_observations (id INTEGER PRIMARY KEY AUTOINCREMENT, brand TEXT, model TEXT, iv_set TEXT,
              rate_ml_h REAL, period_s REAL, mean_flow REAL, stroke_volume_ml REAL, accepted INTEGER, session_id INTEGER,
              created_at TEXT);
            PRAGMA user_version = 1;
        """)
        db.execute("INSERT INTO sessions (id, started_at, mode, pump_type, brand, model, iv_set, summary_json)"
                   " VALUES (1, '2026-11-01', 'inspection', 'syringe', 'ACME', 'S9', '50 ml', '{}')")
        db.execute("INSERT INTO profiles VALUES ('acme', 's9', '50 ml', 0.3, 2, 'x')")
        db.execute("INSERT INTO profiles VALUES ('acme', 'p1', '', 0.2, 1, 'x')")
        db.execute("INSERT INTO profile_observations (brand, model, iv_set, rate_ml_h, period_s, mean_flow,"
                   " stroke_volume_ml, accepted, session_id) VALUES ('acme', 's9', '50 ml', 50, 21.6, 50, 0.3, 1, 1)")
        db.commit()
        db.close()

        repo = Repository(path, self.root / "s")
        self.assertTrue((self.root / "old.v1-backup.db").is_file())                  # สำรองก่อนเปลี่ยน
        self.assertEqual(repo.get_profile("ACME", "S9", "50 ml", "syringe").runs, 2)  # ชนิดจากผลทดสอบ
        self.assertAlmostEqual(repo.get_profile("ACME", "P1", "", "infusion").stroke_volume_ml, 0.2)
        self.assertEqual(repo.expected_period_info("ACME", "S9", "50 ml", 50.0, "syringe"), (21.6, "rate"))
        self.assertEqual(repo._db.execute("PRAGMA user_version").fetchone()[0], 2)
        repo.close()
        Repository(path, self.root / "s").close()                                    # เปิดซ้ำได้ ไม่ย้ายซ้ำ


def _prerun(rate, group, period=None, hz=2.0, minutes=60.0, sim_period=None, ripple=20.0, max_wait_min=None):
    criteria = PrerunSettings().group(group)
    if max_wait_min is not None:
        criteria.max_wait_min = max_wait_min
    s = EngineSettings(stability_pct=criteria.stability_pct, stability_blocks=criteria.blocks,
                       stability_window_s=criteria.block_s, stability_block_mode=criteria.block_mode,
                       stability_block_cycles=criteria.block_cycles, stability_min_block_mg=criteria.min_block_mg,
                       stability_align_cycle=criteria.align_to_cycle, stability_max_wait_s=criteria.max_wait_min * 60,
                       expected_period_s=period or 0.0)
    pr = PreRun(SessionConfig(target_flow=rate, start_mode=StartMode.AUTO), s, tune_windows=False)
    sim = SimulatedBalance(SimulatorSettings(cycle_period_s=sim_period or period or 60.0, ripple_pct=ripple,
                                             noise_g=0.0), rate, seed=1)
    t = 0.0
    while t < minutes * 60 and not pr.ready:
        pr.update(t, round(sim.weight_at(t), 3))          # ตราชั่ง 1 mg
        t += 1.0 / hz
    return pr, t


class PrerunCriteriaTest(unittest.TestCase):
    def test_groups(self):
        self.assertEqual(prerun_group("infusion", True), "infusion_cycle")
        self.assertEqual(prerun_group("infusion", False), "infusion_time")
        self.assertEqual(prerun_group("syringe", False), "syringe_time")
        self.assertEqual(prerun_group("syringe", True), "infusion_cycle")     # syringe จับรอบไม่ได้: ใช้เกณฑ์จับรอบ

    def test_low_rate_cycle_is_no_longer_stuck(self):
        """2 ml/h คาบ 337 s: 3 ช่วง = 1011 s > เพดานข้อมูลเดิม 900 s (เดิมไม่มีวันนิ่ง)"""
        pr, t = _prerun(2.0, "infusion_cycle", period=337.0, max_wait_min=0)       # ไม่จำกัดเวลารอ
        self.assertTrue(pr.ready)
        self.assertFalse(pr.unconfirmed)
        self.assertAlmostEqual(pr.block_s, 337.0, delta=337 * 0.05)          # คาบที่วัดได้ก่อนเริ่มมาก่อนโปรไฟล์
        self.assertGreater(t, 3 * pr.block_s)                                 # เกิน 900 s ได้แล้ว
        self.assertGreater(t, 900.0)
        # ค่าเริ่มต้น (รอนานสุด 15 นาที) น้อยกว่าข้อมูลที่ต้องใช้ -> เริ่มวัดโดยบันทึกว่ายังไม่ยืนยัน
        pr, t = _prerun(2.0, "infusion_cycle", period=337.0)
        self.assertTrue(pr.unconfirmed)
        self.assertAlmostEqual(t, 900.5, delta=1.0)

    def test_block_length_rules(self):
        pr, _ = _prerun(1.0, "syringe_time", minutes=0.01, ripple=0.0)
        self.assertAlmostEqual(pr.block_length(), 72.0)          # 20 mg ที่ 1 ml/h = 72 s (ยืดจาก 30 s)
        pr, _ = _prerun(100.0, "syringe_time", minutes=0.01, ripple=0.0)
        self.assertAlmostEqual(pr.block_length(), 30.0)
        pr, _ = _prerun(200.0, "infusion_time", period=3.5, minutes=0.01)
        self.assertAlmostEqual(pr.block_length(), 17.5)          # 15 s ปัดขึ้นเป็น 5 คาบ

    def test_max_wait_starts_anyway_and_flags_it(self):
        s = EngineSettings(stability_pct=0.01, stability_blocks=3, stability_window_s=10.0,
                           stability_max_wait_s=120.0)
        pr = PreRun(SessionConfig(target_flow=50.0, start_mode=StartMode.AUTO), s, tune_windows=False)
        sim = SimulatedBalance(SimulatorSettings(cycle_period_s=37.0, ripple_pct=60.0, noise_g=0.0), 50.0)
        t = 0.0
        while not pr.ready and t < 600:
            status = pr.update(t, round(sim.weight_at(t), 3))
            t += 0.5
        self.assertTrue(pr.unconfirmed)
        self.assertAlmostEqual(t, 120.5, delta=1.0)
        self.assertEqual(status.max_wait_s, 120.0)


class SuggesterTest(unittest.TestCase):
    HISTORY = [
        {"started_at": "2026-11-12T10:00", "pump_type": "infusion", "brand": "TERUMO", "model": "TE-171",
         "accessory": "TI*PU200L", "serial_no": "A100", "asset_id": "K-1", "department": "ICU", "operator": "Somchai",
         "temperature_c": 24.5},
        {"started_at": "2026-11-11T10:00", "pump_type": "syringe", "brand": "Terumo", "model": "TE-331",
         "accessory": "50 ml", "serial_no": "S9", "asset_id": "K-9", "department": "ER", "operator": "Somchai",
         "temperature_c": 22.0},
        {"started_at": "2026-11-10T10:00", "pump_type": "infusion", "brand": "B. Braun", "model": "Infusomat",
         "accessory": "Space line", "serial_no": "B5", "department": "ICU", "operator": "Nok"},
    ]

    def setUp(self):
        self.s = JobSuggester(self.HISTORY, today="2026-11-12")

    def test_context_and_case(self):
        self.assertEqual(self.s.suggest("brand", {"pump_type": "syringe"}), ["Terumo"])
        self.assertEqual(self.s.suggest("brand", {"pump_type": "infusion"}, "ter"), ["TERUMO"])   # สะกดตามที่บันทึก
        self.assertEqual(self.s.suggest("model", {"pump_type": "infusion", "brand": "terumo"}), ["TE-171"])
        self.assertEqual(self.s.suggest("accessory", {"pump_type": "infusion", "brand": "B. Braun",
                                                      "model": "Infusomat"}), ["Space line"])
        self.assertEqual(self.s.suggest("operator", {}), ["Somchai", "Nok"])                    # ใช้บ่อยก่อน
        self.assertEqual(self.s.suggest("notes", {}), [])

    def test_known_serial_suggests_that_device(self):
        job = {"pump_type": "syringe", "serial_no": "s9"}
        self.assertEqual(self.s.suggest("model", job)[0], "TE-331")
        self.assertEqual(self.s.suggest("department", job)[0], "ER")
        self.assertEqual(self.s.suggest("asset_id", job)[0], "K-9")

    def test_environment_only_from_today(self):
        self.assertEqual(self.s.suggest("temperature_c", {}), ["24.5"])
        self.assertEqual(JobSuggester(self.HISTORY, today="2026-11-20").suggest("temperature_c", {}), [])


class SmartEditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _form(self):
        from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget
        from ui.widgets.smart_edit import SmartLineEdit
        window = QWidget()
        layout = QVBoxLayout(window)
        edit = SmartLineEdit(lambda typed: [v for v in ("TERUMO", "Terumo Plus", "B. Braun")
                                            if v.lower().startswith(typed.lower())])
        after = QLineEdit()
        layout.addWidget(edit)
        layout.addWidget(after)
        window.show()
        edit.setFocus()
        self.app.processEvents()
        return window, edit, after

    def test_tab_accepts_and_moves_on(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        window, edit, after = self._form()
        self.assertEqual(edit.text(), "")                     # ไม่กรอกให้เอง
        self.assertEqual(edit.ghost, "TERUMO")
        QTest.keyClicks(edit, "te")
        edit._completer.popup().hide()
        self.assertEqual(edit.ghost, "RUMO")
        QTest.keyClick(edit, Qt.Key.Key_Tab)
        self.app.processEvents()
        self.assertEqual(edit.text(), "TERUMO")
        self.assertTrue(after.hasFocus())
        window.close()

    def test_enter_accepts_esc_ignores(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        window, edit, _ = self._form()
        QTest.keyClick(edit, Qt.Key.Key_Escape)
        self.assertEqual(edit.ghost, "")
        QTest.keyClick(edit, Qt.Key.Key_Tab)                 # ไม่เอา -> Tab ปกติ ช่องยังว่าง
        self.assertEqual(edit.text(), "")
        edit.setFocus()
        self.app.processEvents()
        QTest.keyClicks(edit, "b")
        edit._completer.popup().hide()
        QTest.keyClick(edit, Qt.Key.Key_Return)
        self.assertEqual(edit.text(), "B. Braun")
        self.assertTrue(edit.hasFocus())
        window.close()

    def test_wizard_uses_history(self):
        from ui.dialogs.test_wizard import TestWizard
        from ui.widgets.smart_edit import SmartLineEdit
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository(Path(tmp) / "t.db", Path(tmp) / "s")
            repo.job_history = lambda limit=2000: SuggesterTest.HISTORY
            wizard = TestWizard(None, repo, AppSettings())
            self.assertIsInstance(wizard._job_edits["brand"], SmartLineEdit)
            self.assertNotIsInstance(wizard._job_edits["notes"], SmartLineEdit)       # หมายเหตุไม่แนะนำ
            wizard._pump_type.setCurrentIndex(wizard._pump_type.findData("syringe"))
            self.assertEqual(wizard._suggest("brand", ""), ["Terumo"])
            wizard._job_edits["serial_no"].setText("A100")
            self.assertEqual(wizard._suggest("model", "")[0], "TE-171")
            self.assertEqual(wizard._job_edits["model"].text(), "")                    # ยังไม่ได้กรอก
            repo.close()


if __name__ == "__main__":
    unittest.main()
