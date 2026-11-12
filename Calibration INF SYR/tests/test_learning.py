"""ทดสอบ: ค่าเริ่มต้นของรุ่นที่ยังไม่มีข้อมูล (ก), ปรับหน้าต่างจากข้อมูลย้อนหลัง (ข),
บีบอัด + ลายนิ้วมือ SHA-256 (ค) และตัวเลือกชนิดเครื่องใน wizard

รัน:  python -m unittest discover -s tests -v
"""
import gzip
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import EngineSettings, SimulatorSettings
from core.engine import FlowEngine
from core.models import JobInfo, Sample, SessionConfig, StartMode
from core.tuning import Dataset, TrialResult, TuningResult, tune
from hardware.replay import load_samples
from hardware.simulator import SimulatedBalance
from services.session_store import Repository


def _pump_samples(rate=50.0, period=14.0, minutes=4.0, hz=5.0, seed=2):
    sim = SimulatedBalance(SimulatorSettings(sample_rate_hz=hz, cycle_period_s=period, ripple_pct=30.0,
                                             noise_g=0.0003), rate, seed=seed)
    return [(i / hz, sim.weight_at(i / hz)) for i in range(int(minutes * 60 * hz))]


class _RepoCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.repo = Repository(root / "t.db", root / "sessions")

    def tearDown(self):
        self.repo.close()
        self._tmp.cleanup()

    def _save_run(self, rate=50.0, brand="ACME", model="P1", iv_set="SET", minutes=4.0, period=14.0):
        """รันการทดสอบจับรอบปั๊มจากข้อมูลจำลอง แล้วเก็บผล เหมือนผู้ใช้กด "เก็บ" """
        from services.recorder import RawRecorder
        job = JobInfo(brand=brand, model=model, accessory=iv_set)
        config = SessionConfig(job=job, target_flow=rate, strategy="pump_cycle", duration_min=minutes - 0.5)
        dt = 0.2
        points = round(period * 0.4 / dt)
        engine = FlowEngine(config, EngineSettings(regression_window=max(10, points), cycle_half_window=max(5, points)))
        folder = self.repo.new_session_folder(engine.started_at, "infusion", rate)
        recorder = RawRecorder(folder)
        for t, w in _pump_samples(rate, period, minutes):
            result = engine.process(Sample(t, w))
            recorder.write(False, result.t, result.weight)
        recorder.close()
        return self.repo.save(engine.summary("completed"), engine.intervals, folder), folder


class ModelDefaultTest(_RepoCase):
    def test_default_is_used_until_measured(self):
        self.assertEqual(self.repo.expected_period_info("ACME", "P1", "SET", 50.0), (None, ""))
        self.assertTrue(self.repo.set_model_default("ACME", "P1", "SET", 0.2))
        period, source = self.repo.expected_period_info("acme ", "p1", "set", 50.0)
        self.assertEqual(source, "model_default")
        self.assertAlmostEqual(period, 0.2 * 3600 / 50.0)
        self.assertTrue(self.repo.get_profile("ACME", "P1", "SET").provisional)
        # การวัดจริงครั้งแรกแทนที่ค่าเริ่มต้น
        profile, status = self.repo.add_observation("ACME", "P1", "SET", 50.0, 13.0, 50.0)
        self.assertEqual(status, "merged")
        self.assertAlmostEqual(profile.stroke_volume_ml, 50.0 * 13.0 / 3600.0)
        self.assertEqual(self.repo.expected_period_info("ACME", "P1", "SET", 50.0)[1], "rate")
        # ไม่ทับโปรไฟล์ที่วัดจริงแล้ว
        self.assertFalse(self.repo.set_model_default("ACME", "P1", "SET", 0.5))
        self.assertFalse(self.repo.set_model_default("", "", "SET", 0.5))     # ไม่มีชื่อรุ่น = จำไม่ได้

    def test_engine_falls_back_to_default_volume(self):
        """หาคาบไม่ได้ (เส้นตรงไม่มีรอบ) -> เดาจากปริมาตรต่อรอบเริ่มต้น แทนค่ากำหนดเองที่ไม่สนใจ rate"""
        config = SessionConfig(target_flow=50.0, strategy="pump_cycle", start_mode=StartMode.IMMEDIATE)
        settings = EngineSettings(window_mode="auto", auto_tune_timeout_s=30.0, default_stroke_volume_ml=0.16)
        engine = FlowEngine(config, settings)
        t = 0.0
        while engine.in_prerun and t < 60:
            engine.process(Sample(t, 50.0 * t / 3600.0))
            t += 0.2
        self.assertEqual(engine.window_source, "default")
        expected = round(0.16 * 3600 / 50.0 * settings.auto_window_fraction / 0.2)
        self.assertEqual(engine.settings.regression_window, max(10, expected))


class TuningTest(_RepoCase):
    def test_tune_finds_consistent_fraction(self):
        data = [Dataset(_pump_samples(), 14.0 * 50.0 / 50.0 / (1 + 0.015))]   # sim มี error +1.5 %
        result = tune(data, 50.0, current_fraction=0.4)
        self.assertIsNotNone(result.best)
        self.assertTrue(math.isfinite(result.best.score))
        self.assertIsNotNone(result.current_score)
        self.assertAlmostEqual(result.best.period_ratio, 1.0, delta=0.05)
        self.assertIn(result.recommended_fraction(), [t.fraction for t in result.trials])

    def test_keeps_current_unless_clearly_better(self):
        def trial(f, score):
            return TrialResult(f, 10, 5, 10, 0.0, 0.0, 1.0, score)
        result = TuningResult(rate=50.0, sessions=1, period_s=14.0, current_fraction=0.4, current_score=0.100)
        result.best = trial(0.35, 0.095)                # ดีขึ้น 5 % -> คงค่าเดิม
        self.assertEqual(result.recommended_fraction(), 0.4)
        result.best = trial(0.35, 0.080)                # ดีขึ้น 20 % -> เปลี่ยน
        self.assertEqual(result.recommended_fraction(), 0.35)
        result.best = None
        self.assertIsNone(result.recommended_fraction())

    def test_stored_sessions_feed_tuning(self):
        self._save_run(rate=50.0)
        self._save_run(rate=200.0, period=3.5, minutes=2.0)
        datasets = self.repo.tuning_datasets("acme", "P1", "set")
        self.assertEqual(sorted(datasets), [50.0, 200.0])
        result = tune(datasets[50.0], 50.0, 0.4)
        self.repo.save_tuning("ACME", "P1", "SET", result)
        fraction, tuned = self.repo.window_fraction("ACME", "P1", "SET", 50.0, 0.4)
        self.assertTrue(tuned)
        self.assertEqual(fraction, result.recommended_fraction())
        # rate ที่ยังไม่เคยปรับ: ใช้ค่ากลางของรุ่นนี้
        self.assertEqual(self.repo.window_fraction("ACME", "P1", "SET", 10.0, 0.4), (fraction, True))
        self.assertEqual(self.repo.window_fraction("OTHER", "X", "", 50.0, 0.4), (0.4, False))


class IntegrityTest(_RepoCase):
    def test_compressed_and_fingerprinted(self):
        ref, folder = self._save_run(minutes=2.0)
        self.assertFalse((folder / "raw.csv").exists())
        self.assertTrue((folder / "raw.csv.gz").is_file())
        checks = dict(self.repo.verify(ref))
        self.assertEqual(set(checks), {"raw.csv.gz", "intervals.csv", "summary.json"})
        self.assertTrue(all(status == "ok" for status in checks.values()))
        detail = self.repo.load(ref)
        self.assertEqual(len(detail.samples), 2 * 60 * 5)                # ไม่เสียข้อมูลแม้แต่จุดเดียว
        self.assertEqual(load_samples(folder / "raw.csv.gz"), detail.samples)
        with gzip.open(folder / "raw.csv.gz", "rt", encoding="utf-8") as f:
            self.assertEqual(f.readline().strip(), "t_s,weight_g")

        # แก้ไฟล์ภายหลัง -> ตรวจเจอ · ลบไฟล์ -> ตรวจเจอ
        with open(folder / "intervals.csv", "a", encoding="utf-8") as f:
            f.write("99,A,1,1,1,1,1,1\n")
        (folder / "summary.json").unlink()
        checks = dict(self.repo.verify(ref))
        self.assertEqual((checks["intervals.csv"], checks["summary.json"], checks["raw.csv.gz"]),
                         ("changed", "missing", "ok"))
        self.repo.delete(ref)
        self.assertEqual(self.repo.verify(ref), [])


class PumpTypeSelectorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_combo_like_api_and_colors(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from ui.widgets.pump_type import PumpTypeSelector
        selector = PumpTypeSelector()
        seen = []
        selector.changed.connect(seen.append)
        self.assertEqual(selector.currentData(), "infusion")
        QTest.mouseClick(selector._cards[1], Qt.MouseButton.LeftButton)
        self.assertEqual((selector.currentData(), seen), ("syringe", ["syringe"]))
        self.assertTrue(selector._cards[1].property("selected"))
        self.assertFalse(selector._cards[0].property("selected"))
        selector.setCurrentIndex(selector.findData("infusion"))
        self.assertEqual(seen, ["syringe", "infusion"])

    def test_changing_type_resets_measurement_defaults(self):
        from config.settings import AppSettings
        from core.models import RunMode
        from ui.dialogs.test_wizard import TestWizard
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository(Path(tmp) / "t.db", Path(tmp) / "s")
            wizard = TestWizard(None, repo, AppSettings())
            wizard._choose_mode(RunMode.CALIBRATION)
            self.assertEqual(wizard._strategy.currentData(), "pump_cycle")
            self.assertEqual([r["rate"].value() for r in wizard._rows], [10.0, 50.0, 200.0])
            wizard._pump_type.setCurrentIndex(wizard._pump_type.findData("syringe"))   # แก้ชนิดที่เลือกผิด
            wizard._choose_mode(RunMode.CALIBRATION)
            self.assertEqual(wizard._strategy.currentData(), "time_interval")
            self.assertEqual([r["rate"].value() for r in wizard._rows], [10.0, 50.0, 100.0])
            self.assertEqual(wizard._badge.property("pump"), "syringe")
            # รุ่นใหม่ + เลือก "rate สูงก่อน" -> แผนเรียง 200 → 50 → 10
            wizard._pump_type.setCurrentIndex(0)
            wizard._job_edits["brand"].setText("ACME")
            wizard._choose_mode(RunMode.CALIBRATION)
            wizard._ask_unknown_pump = lambda: "reorder"
            wizard._on_next()
            self.assertEqual([s.target_flow for s in wizard.plan.steps], [200.0, 50.0, 10.0])
            self.assertEqual(wizard.plan.window_source, "profile")
            # เลือก "ค่าเริ่มต้นของรุ่น" -> บันทึกเป็นค่าแทนไปก่อน
            wizard._ask_unknown_pump = lambda: (setattr(wizard, "_default_stroke_ml", 0.21), "default")[1]
            wizard._on_next()
            self.assertTrue(repo.get_profile("ACME", "", "").provisional)
            repo.close()

    def test_new_pump_dialog_offers_reorder(self):
        from ui.dialogs.new_pump import NewPumpDialog
        dialog = NewPumpDialog(None, "ACME P1", [10.0, 50.0, 200.0], 0.16, can_remember=True)
        self.assertTrue(dialog._options["reorder"].isChecked())
        dialog._accept()
        self.assertEqual(dialog.choice, "reorder")
        dialog = NewPumpDialog(None, "", [200.0, 50.0], 0.16, can_remember=False)
        self.assertFalse(dialog._options["reorder"].isEnabled())
        self.assertFalse(dialog._options["default"].isEnabled())
        self.assertTrue(dialog._options["profile"].isChecked())


if __name__ == "__main__":
    unittest.main()
