"""ทดสอบ: ถามผู้ใช้เมื่อรอบปั๊มต่างจากข้อมูลเดิม, Calibration รอบปั๊มใหม่ (แทนที่ข้อมูลเดิม), ตาราง intervals

รัน:  python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from config.settings import AppSettings
from services.session_store import Repository

app = QApplication.instance() or QApplication([])
KEY = ("ACME", "P1", "SET")


class _Repo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Repository(Path(self._tmp.name) / "t.db", Path(self._tmp.name) / "s")

    def tearDown(self):
        self.repo.close()
        self._tmp.cleanup()


class DecisionTest(_Repo):
    def test_out_of_range_needs_a_decision(self):
        self.repo.add_observation(*KEY, 50.0, 14.0, 50.0)
        self.assertEqual(self.repo.check_observation(*KEY, 50.0, 14.5, 50.0).status, "ok")
        check = self.repo.check_observation(*KEY, 50.0, 20.0, 50.0)
        self.assertEqual((check.status, check.kind, check.streak), ("out_of_range", "rate", 0))
        self.assertAlmostEqual(check.deviation_pct, (20 - 14) / 14 * 100)
        # ไม่เก็บ -> บันทึกไว้แต่ไม่ใช้ · ครั้งต่อไปนับเป็นครั้งที่ 2 ติดกัน
        self.assertEqual(self.repo.add_observation(*KEY, 50.0, 20.0, 50.0, decision="skip")[1], "declined")
        self.assertEqual(self.repo.expected_period(*KEY, 50.0), 14.0)
        self.assertEqual(self.repo.check_observation(*KEY, 50.0, 20.5, 50.0).streak, 1)
        # เก็บรวม -> ใช้เฉลี่ยกับของเดิม
        self.repo.add_observation(*KEY, 50.0, 20.0, 50.0, decision="add")
        self.assertAlmostEqual(self.repo.expected_period(*KEY, 50.0), 17.0)
        # ค่าตรงเกณฑ์ตัดต่อเนื่อง (streak กลับเป็น 0)
        self.repo.add_observation(*KEY, 50.0, 17.0, 50.0)
        self.assertEqual(self.repo.check_observation(*KEY, 50.0, 30.0, 50.0).streak, 0)

    def test_volume_check_when_rate_is_new(self):
        self.repo.add_observation(*KEY, 50.0, 14.4, 50.0)              # 0.2 ml ต่อรอบ
        check = self.repo.check_observation(*KEY, 10.0, 108.0, 10.0)   # 0.3 ml ต่อรอบ
        self.assertEqual((check.status, check.kind), ("out_of_range", "volume"))
        self.assertAlmostEqual(check.expected_period_s, 72.0)


class RecalibrateTest(_Repo):
    def test_replaces_learning_but_keeps_history(self):
        self.repo.add_observation(*KEY, 50.0, 14.0, 50.0)
        self.repo.add_observation(*KEY, 50.0, 14.2, 50.0)
        self.assertTrue(self.repo.recalibrate(*KEY, since="2999-01-01T00:00:00"))
        self.assertEqual(self.repo.expected_period_info(*KEY, 50.0), (None, ""))     # ข้อมูลเก่าไม่ถูกใช้แล้ว
        self.assertEqual(self.repo.check_observation(*KEY, 50.0, 21.0, 50.0).status, "new")
        self.repo._db.execute("UPDATE profiles SET calibrated_at = '2000-01-01'")   # ให้ค่าใหม่อยู่หลังเวลา calibration
        self.repo.recalibrate(*KEY, since="2000-01-01T00:00:00")
        profile, status = self.repo.add_observation(*KEY, 50.0, 21.0, 50.0, decision="calibration")
        self.assertEqual((status, profile.runs), ("merged", 1))
        self.assertAlmostEqual(profile.stroke_volume_ml, 50.0 * 21.0 / 3600.0)
        count = self.repo._db.execute("SELECT count(*) FROM profile_observations").fetchone()[0]
        self.assertEqual(count, 3)                                                     # ของเก่ายังอยู่ครบ


class ControllerLearningTest(_Repo):
    """SessionController._learn_profile: ถามผู้ใช้ / Calibration ใหม่ในแผน"""

    def _controller(self):
        from services import session_store
        session_store.set_repository(self.repo)
        from services.session_controller import SessionController
        settings = AppSettings()
        settings.source = "simulator"
        return SessionController(settings)

    @staticmethod
    def _fake(period, job_id="J1", source="profile", rate=50.0):
        from types import SimpleNamespace
        from core.models import JobInfo, SessionConfig, SessionSummary
        config = SessionConfig(job=JobInfo(brand=KEY[0], model=KEY[1], accessory=KEY[2]), target_flow=rate,
                               window_source=source, job_id=job_id)
        from datetime import datetime
        summary = SessionSummary(config=config, started_at=datetime.now().isoformat(timespec="microseconds"))
        stats = SimpleNamespace(count=10, mean_duration_s=period, mean_flow=rate)
        engine = SimpleNamespace(strategy_uses_cycles=True, stats=stats)
        return summary, engine

    def test_asks_and_follows_the_answer(self):
        c = self._controller()
        c._learn_profile(*self._fake(14.0), ref="1")
        asked = []
        c.ask_profile_decision = lambda check: asked.append(check) or "skip"
        c._learn_profile(*self._fake(20.0), ref="2")
        self.assertEqual(len(asked), 1)
        self.assertEqual(self.repo.expected_period(*KEY, 50.0), 14.0)              # ไม่เก็บ
        c.ask_profile_decision = lambda check: "recalibrate"
        c._learn_profile(*self._fake(21.0), ref="3")
        self.assertAlmostEqual(self.repo.expected_period(*KEY, 50.0), 21.0)        # เริ่มใหม่จากค่านี้
        c.ask_profile_decision = None                                                # ไม่มีใครตอบ = ไม่เก็บ
        c._learn_profile(*self._fake(14.1), ref="4")
        c._learn_profile(*self._fake(30.0), ref="5")
        self.assertAlmostEqual(self.repo.expected_period(*KEY, 50.0), 21.0)

    def test_recalibration_plan_replaces_on_first_kept_step(self):
        c = self._controller()
        c._learn_profile(*self._fake(14.0, job_id="OLD"), ref="1")
        c.ask_profile_decision = lambda check: self.fail("must not ask during calibration")
        c._learn_profile(*self._fake(30.0, job_id="CAL", source="recalibrate"), ref="2")
        self.assertIn("CAL", c._recalibrated)
        self.assertAlmostEqual(self.repo.get_profile(*KEY).stroke_volume_ml, 50.0 * 30.0 / 3600.0)
        # ขั้นถัดไปของแผนเดียวกัน = เรียนรู้ต่อจากค่าใหม่ (rate อื่น ปริมาตรต่อรอบใกล้กัน)
        c._learn_profile(*self._fake(150.0, job_id="CAL", source="recalibrate", rate=10.0), ref="3")
        self.assertEqual(self.repo.get_profile(*KEY).runs, 2)


class WizardCalibrationTest(_Repo):
    def test_button_sets_recalibrate_and_orders_high_to_low(self):
        from core.models import RunMode
        from ui.dialogs import recalibrate
        from ui.dialogs.test_wizard import TestWizard
        self.repo.add_observation(*KEY, 50.0, 14.0, 50.0)
        wizard = TestWizard(None, self.repo, AppSettings())
        for name, value in zip(("brand", "model", "accessory"), KEY):
            wizard._job_edits[name].setText(value)
        wizard._choose_mode(RunMode.CALIBRATION)
        self.assertTrue(wizard._recalibrate_button.isEnabled())
        recalibrate.RecalibrateDialog.exec = lambda self: 1
        self.assertTrue(wizard._ask_recalibrate())
        self.assertEqual(wizard._window_source.currentData(), "recalibrate")
        self.assertEqual([r["rate"].value() for r in wizard._rows], [200.0, 50.0, 10.0])
        wizard._on_next()
        self.assertEqual(wizard.plan.window_source, "recalibrate")

    def test_deviation_dialog_buttons(self):
        from services.session_store import ObservationCheck
        from ui.dialogs.profile_deviation import ProfileDeviationDialog
        check = ObservationCheck(rate=50, period_s=20, observed_ml=0.28, status="out_of_range", kind="rate",
                                 expected_period_s=14, expected_ml=0.19, deviation_pct=43, runs=3, streak=0)
        dialog = ProfileDeviationDialog(None, "ACME P1", check)
        self.assertFalse(dialog.btn_recalibrate.isVisibleTo(dialog))           # ครั้งแรก: ยังไม่เสนอ Calibration
        dialog.btn_add.click()
        self.assertEqual(dialog.choice, "add")
        check.streak = 1
        dialog = ProfileDeviationDialog(None, "ACME P1", check)
        self.assertTrue(dialog.btn_recalibrate.isVisibleTo(dialog))            # ต่างติดกัน 2 ครั้ง: เสนอ
        dialog.reject()
        self.assertEqual(dialog.choice, "skip")


if __name__ == "__main__":
    unittest.main()
