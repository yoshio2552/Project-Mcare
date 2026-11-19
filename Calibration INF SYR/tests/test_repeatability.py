"""สอบเทียบความซ้ำ (RunMode.REPEATABILITY) ทั้งเส้นทาง + หน้าต่างตารางความซ้ำ (2026-11-19)"""
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog

from config.settings import AppSettings
from core.models import EndMode, JobInfo, PumpType, RunMode, StartMode, StepConfig, TestPlan
from core.repeatability import Study, from_runs
from services import session_store


def wait_until(condition, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


class _Repo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        AppSettings.save = lambda self, path=None: None
        self.tmp = Path(tempfile.mkdtemp(prefix="deltam-repeat-"))
        self.repo = session_store.Repository(self.tmp / "t.db", self.tmp / "sessions")
        self.previous = session_store._repository
        session_store.set_repository(self.repo)

    def tearDown(self):
        session_store.set_repository(self.previous)
        self.repo._db.close()
        shutil.rmtree(self.tmp, ignore_errors=True)


class StudyFlowTest(_Repo):
    def test_three_runs_make_one_set_with_traceable_runs(self):
        from services.session_controller import SessionController
        settings = AppSettings()
        settings.source = "simulator"
        settings.simulator.speed = 300
        controller = SessionController(settings)
        controller.ask_profile_decision = lambda check: "skip"
        controller.review_requested.connect(lambda summary: QTimer.singleShot(0, controller.keep_result))
        finished, saved = [], []
        controller.session_finished.connect(lambda summary, kept: finished.append(summary))
        controller.repeat_study_saved.connect(saved.append)
        job = JobInfo(pump_type=PumpType.SYRINGE, brand="Terumo", model="TE-331", accessory="50 ml")
        step = StepConfig(target_flow=20.0, duration_min=1.0, window_s=20.0)
        plan = TestPlan(job=job, run_mode=RunMode.REPEATABILITY, strategy="time_interval", end_mode=EndMode.TIME,
                        start_mode=StartMode.IMMEDIATE, steps=[StepConfig(**vars(step)) for _ in range(3)])
        controller.set_plan(plan)
        for run in range(3):
            self.assertTrue(controller.start_step())
            self.assertTrue(wait_until(lambda n=run + 1: len(finished) >= n, 90), "run did not finish")
        self.assertTrue(wait_until(lambda: bool(saved), 5))
        controller.shutdown()
        info = saved[0]
        self.assertEqual(len(info["runs"]), 3)
        pct, mlh = from_runs([s.mean_flow for s in finished], 20.0)
        self.assertAlmostEqual(info["sd2_pct"], pct, places=12)
        self.assertAlmostEqual(info["sd2_ml_h"], mlh, places=12)
        value = self.repo.repeat_value("Terumo", "TE-331", "syringe", "50 ml", 20.0)
        self.assertAlmostEqual(value["sd2_pct"], pct, places=12)
        study = self.repo.repeat_studies("Terumo", "TE-331", "syringe", "50 ml", 20.0)[0]
        self.assertEqual(study.kind, "measured")
        self.assertEqual(len(study.runs), 3)
        for run in study.runs:                                   # ทุกครั้งเปิดผลได้ (สอบย้อน)
            self.assertIsNotNone(self.repo.load(run["ref"]))
        modes = {s["config"]["run_mode"] for s in self.repo.list("repeatability")}
        self.assertEqual(modes, {"repeatability"})
        # สอบเทียบซ้ำ = ชุดใหม่ ค่าที่ใช้ = ค่าเฉลี่ย
        self.repo.add_repeat_study("Terumo", "TE-331", "syringe", "50 ml", 20.0,
                                   Study(kind="manual", rate=20.0, sd2_pct=pct + 2.0, sd2_ml_h=(pct + 2.0) / 5.0))
        self.assertAlmostEqual(self.repo.repeat_value("Terumo", "TE-331", "syringe", "50 ml", 20.0)["sd2_pct"], pct + 1.0)


class DialogTest(_Repo):
    def test_dialog_lists_enters_and_removes(self):
        from PySide6.QtWidgets import QMessageBox
        from ui.dialogs import repeatability as dialogs
        for owner, name in ((dialogs.EntryDialog, "exec"), (dialogs.StudyDialog, "exec"), (QMessageBox, "question")):
            self.addCleanup(setattr, owner, name, getattr(owner, name))     # คืนของเดิมหลังเทสต์
        self.repo.add_repeat_study("ACME", "P1", "infusion", "Set-A", 50.0,
                                   Study(kind="manual", rate=50.0, sd2_pct=0.8, sd2_ml_h=0.4, input_value=0.4, input_unit="ml/h"))
        dialog = dialogs.RepeatabilityDialog(None, self.repo, AppSettings())
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertEqual(dialog.table.item(0, 4).text(), "0.8000")
        self.assertEqual(dialog.sets.rowCount(), 1)

        def fill(entry):            # หน้าต่างกรอกค่า: 1.2 % ที่ rate เดียวกัน
            entry.value.setValue(1.2)
            entry._accept()
            return QDialog.DialogCode.Accepted
        dialogs.EntryDialog.exec = fill
        dialog._enter(dialog._selected())
        self.assertEqual(dialog.sets.rowCount(), 2)
        self.assertEqual(dialog.table.item(0, 4).text(), "1.0000")        # ค่าเฉลี่ยของ 2 ชุด
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
        dialog.sets.selectRow(1)
        dialog._remove()
        self.assertEqual(dialog.sets.rowCount(), 1)
        self.assertEqual(len(self.repo.repeat_studies("ACME", "P1", "infusion", "Set-A", 50.0, include_deleted=True)), 2)

        plans = []
        dialog.start_requested.connect(plans.append)

        def measure(study):
            study._accept()
            return QDialog.DialogCode.Accepted
        dialogs.StudyDialog.exec = measure
        dialog._measure(dialog._selected())
        plan = plans[0]
        self.assertIs(plan.run_mode, RunMode.REPEATABILITY)
        self.assertEqual(len(plan.steps), 3)
        self.assertEqual({s.target_flow for s in plan.steps}, {50.0})
        self.assertEqual((plan.job.brand, plan.job.model, plan.job.accessory), ("ACME", "P1", "Set-A"))
        dialog.close()


if __name__ == "__main__":
    unittest.main()
