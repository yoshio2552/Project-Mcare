"""ทดสอบ: หน้าต่างจับรอบปั๊มราย rate (จ), ตรวจผลหลังจบ (ฉ), ข้อมูลสอบเทียบแยกที่มา (ข, ค), ตัวกันพลาด (ง)
และการใช้หน่วยความจำ/เวลาเมื่อรันนาน

รัน:  python -m unittest discover -s tests -v
"""
import os
import sqlite3
import sys
import tempfile
import time
import tracemalloc
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import EngineSettings, SimulatorSettings
from core.capture_check import check_cycle_capture, check_summary, effective_verdict
from core.engine import FlowEngine
from core.models import EndMode, JobInfo, Sample, SessionConfig, StartMode, Verdict
from core.stats import RunningStats, confidence_interval, expanded_std
from core.windows import cycle_windows, fraction_problems, fractions_from_points, time_window_for
from hardware.simulator import SimulatedBalance
from services.session_store import Repository
from services.window_plan import plan_windows


def _samples(rate=200.0, period=2.13, minutes=3.0, hz=5.0, seed=4):
    sim = SimulatedBalance(SimulatorSettings(sample_rate_hz=hz, cycle_period_s=period, ripple_pct=30.0,
                                             noise_g=0.0003), rate, seed=seed)
    return [(i / hz, sim.weight_at(i / hz)) for i in range(int(minutes * 60 * hz))]


def _run(samples, config, settings):
    engine = FlowEngine(config, settings)
    for t, w in samples:
        if engine.process(Sample(t, w)).finished:
            break
    return engine


class CycleWindowsTest(unittest.TestCase):
    def test_short_cycle_uses_minimum_not_settings(self):
        # session id 11: คาบ 2.13 s ที่ 5 Hz = 10.6 จุดต่อรอบ -> 0.4 x = 4 จุด -> ขั้นต่ำ 5 / 3 (เดิมถอยไป 250/250)
        w = cycle_windows(2.13, 0.2, 0.4, 0.4)
        self.assertEqual((w.regression, w.half), (5, 4))
        self.assertTrue(w.clamped)
        self.assertAlmostEqual(w.points_per_cycle, 10.65, places=2)
        self.assertEqual(w.level, "low")
        self.assertEqual(cycle_windows(71.0, 0.2, 0.4).level, "ok")
        self.assertEqual(cycle_windows(1.2, 0.2, 0.4).level, "too_low")
        self.assertIsNone(cycle_windows(None, 0.2, 0.4))
        self.assertIsNone(cycle_windows(2.0, None, 0.4))

    def test_guards_and_conversions(self):
        self.assertEqual(fraction_problems(0.4, 0.35), [])
        self.assertEqual([k for k, _ in fraction_problems(0.2, 0.4)], ["warning"])
        self.assertEqual(fraction_problems(0.2, 0.4, tuned=True), [])            # ค่าที่ปรับจากข้อมูลจริงไม่เตือน
        self.assertEqual([k for k, _ in fraction_problems(0.9, 0.4)], ["error"])
        self.assertEqual(fractions_from_points(6, 3, 2.0, 0.2), (0.6, 0.3))
        self.assertAlmostEqual(time_window_for(2.13), 31.95)                     # 15 x คาบ >= 30 s
        self.assertAlmostEqual(time_window_for(71.0), 71.0)


class EngineShortCycleTest(unittest.TestCase):
    def test_small_windows_do_not_crash_and_capture_the_cycle(self):
        # เดิม: หน้าต่าง regression < 10 จุด -> slope = None เข้าตัวจับ peak -> TypeError
        config = SessionConfig(target_flow=200.0, strategy="pump_cycle", duration_min=2.0)
        engine = _run(_samples(), config, EngineSettings(regression_window=6, cycle_half_window=3, ml_per_g=1.0))
        self.assertGreater(engine.stats.count, 40)
        self.assertAlmostEqual(engine.stats.mean_duration_s, 2.13, delta=0.15)

    def test_measured_cycle_sets_windows_even_with_few_points(self):
        config = SessionConfig(target_flow=200.0, strategy="pump_cycle", duration_min=1.5, start_mode=StartMode.IMMEDIATE)
        settings = EngineSettings(window_mode="auto", ml_per_g=1.0)        # regression_window ในหน้าตั้งค่า = 250
        engine = _run(_samples(minutes=4.0), config, settings)
        self.assertEqual(engine.window_source, "measured")
        self.assertLess(engine.settings.regression_window, 20)
        self.assertAlmostEqual(engine.points_per_cycle, 10.65, delta=1.0)
        summary = engine.summary("completed")
        self.assertEqual(summary.capture_check["status"], "ok")
        self.assertIn(summary.verdict, (Verdict.PASS, Verdict.FAIL))
        self.assertAlmostEqual(summary.points_per_cycle, 10.65, delta=1.0)


class CaptureCheckTest(unittest.TestCase):
    def test_wrong_windows_make_the_result_invalid(self):
        # ตั้งแบบ session id 11 (250/250 จุด กับคาบ 2.13 s) -> จับ "รอบ" ยาวผิดคาบ = INVALID ไม่ใช่ PASS
        config = SessionConfig(target_flow=200.0, strategy="pump_cycle", duration_min=3.0)
        settings = EngineSettings(regression_window=250, cycle_half_window=250, ml_per_g=1.0,
                                  expected_period_s=2.13, expected_period_source="profile")
        engine = _run(_samples(minutes=4.0), config, settings)
        summary = engine.summary("completed")
        self.assertIs(summary.verdict, Verdict.INVALID)
        self.assertIn(summary.capture_check["status"], ("too_few", "period_mismatch"))

    def test_rules(self):
        self.assertEqual(check_cycle_capture(3, 2.1, 2.1, None).status, "too_few")
        self.assertEqual(check_cycle_capture(10, 90.3, None, 2.13).status, "period_mismatch")
        self.assertEqual(check_cycle_capture(10, 2.2, 2.13, 5.0).status, "ok")          # คาบโปรไฟล์มาก่อน
        self.assertEqual(check_cycle_capture(10, 2.2, None, None).status, "unverified")
        self.assertFalse(check_cycle_capture(10, 2.2, None, None).invalid)

    def test_old_result_is_checked_afterwards(self):
        # รูปแบบ summary ของผลเก่า (ก่อนมีการตรวจ) เช่น session id 11 ที่บันทึก PASS ไว้
        old = {"verdict": "PASS", "config": {"strategy": "pump_cycle"}, "interval_count": 1,
               "mean_duration_s": 90.3, "pump_period_s": 2.13, "engine_settings": {"expected_period_s": 2.22}}
        check = check_summary(old)
        self.assertTrue(check.invalid and check.retrospective)
        self.assertEqual(effective_verdict(old), "INVALID")
        self.assertEqual(effective_verdict({"verdict": "PASS", "config": {"strategy": "time_interval"}}), "PASS")


class RunningStatsTest(unittest.TestCase):
    def test_matches_numpy(self):
        values = list(np.random.default_rng(1).normal(50, 3, 500))
        stats = RunningStats()
        for v in values:
            stats.add(v)
        mean, ci = confidence_interval(values)
        self.assertAlmostEqual(stats.mean, mean, places=9)
        self.assertAlmostEqual(stats.expanded(), expanded_std(values), places=9)
        self.assertAlmostEqual(stats.confidence(), ci, places=9)


class CalibrationDataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repository(Path(self.tmp.name) / "t.db", Path(self.tmp.name) / "s")

    def tearDown(self):
        self.repo.close()
        self.tmp.cleanup()

    def _tuned(self, rate, r=0.3, h=0.25):
        from core.tuning import TrialResult, TuningResult
        best = TrialResult(r, h, 0, 0, 10, 0.01, 0.01, 1.0, 0.02)
        return TuningResult(rate=rate, sessions=1, period_s=2.0, sample_period_s=0.2, best=best, current=(r, h))

    def test_sources_never_overwrite_better_data(self):
        args = ("ACME", "P1", "SET", "infusion")
        self.assertTrue(self.repo.save_tuning("ACME", "P1", "SET", self._tuned(200.0)))
        self.assertFalse(self.repo.save_window(*args, 200.0, 0.45, 0.45, "uncalibrated"))   # ไม่ทับค่าสอบเทียบแล้ว
        self.assertTrue(self.repo.save_window(*args, 50.0, 0.42, 0.38, "uncalibrated", 14.0, 0.2))
        self.assertEqual(self.repo.window_fractions("ACME", "P1", "SET", 50.0, (0.4, 0.4)), (0.42, 0.38, "uncalibrated"))
        self.assertTrue(self.repo.save_window(*args, 200.0, 0.35, 0.3, "manual"))           # ผู้ใช้แก้เองทับได้
        self.assertEqual(self.repo.window_fractions("ACME", "P1", "SET", 200.0, (0.4, 0.4))[2], "manual")
        self.assertFalse(self.repo.save_tuning("ACME", "P1", "SET", self._tuned(200.0)))    # ปรับอัตโนมัติไม่ทับค่าแก้เอง
        self.assertTrue(self.repo.save_tuning("ACME", "P1", "SET", self._tuned(200.0), replace_manual=True))
        self.assertTrue(self.repo.save_tuning("ACME", "P1", "SET", self._tuned(50.0)))       # ข้อมูลจริงแทนค่าเริ่มต้น
        self.assertEqual(self.repo.window_fractions("ACME", "P1", "SET", 50.0, (0.4, 0.4))[2], "tuned")
        # rate ที่ไม่มีค่า: เทียบจาก rate ที่สอบเทียบแล้วสองข้าง
        self.assertEqual(self.repo.window_fractions("ACME", "P1", "SET", 100.0, (0.4, 0.4))[2], "interpolated")
        models = self.repo.calibration_models()
        self.assertEqual((models[0]["rates"], models[0]["tuned"]), (2, 2))
        self.assertTrue(self.repo.delete_window(*args, 50.0))
        self.assertEqual(self.repo.window_fractions("ACME", "P1", "SET", 50.0, (0.4, 0.4))[2], "default")

    def test_every_rate_gets_its_own_window(self):
        self.repo.set_model_default("ACME", "P1", "SET", 0.124)
        job = JobInfo(brand="ACME", model="P1", accessory="SET")
        items = plan_windows(self.repo, EngineSettings(), job, [10.0, 50.0, 200.0], 0.2)
        self.assertEqual(len({i.windows.regression for i in items}), 3)            # ไม่ใช่ค่าเดียวทุก rate
        self.assertEqual([i.level for i in items], ["ok", "ok", "low"])
        self.assertTrue(all(i.period_source == "model_default" and not i.calibrated for i in items))

    def test_migration_from_v3_adds_source(self):
        path = Path(self.tmp.name) / "old.db"
        db = sqlite3.connect(path)
        db.executescript("""
            CREATE TABLE profiles (brand TEXT, model TEXT, pump_type TEXT, iv_set TEXT, stroke_volume_ml REAL,
                runs INTEGER, updated_at TEXT, calibrated_at TEXT DEFAULT '', PRIMARY KEY (brand, model, pump_type, iv_set));
            CREATE TABLE window_tuning (brand TEXT, model TEXT, pump_type TEXT, iv_set TEXT, rate_ml_h REAL,
                regression_fraction REAL, half_fraction REAL, regression_points INTEGER, half_points INTEGER,
                sample_period_s REAL, score REAL, default_score REAL, sessions INTEGER, period_s REAL,
                result_json TEXT, updated_at TEXT, PRIMARY KEY (brand, model, pump_type, iv_set, rate_ml_h));
            INSERT INTO window_tuning (brand, model, pump_type, iv_set, rate_ml_h, regression_fraction, half_fraction)
                VALUES ('acme', 'p1', 'infusion', '', 50, 0.3, 0.3);
            PRAGMA user_version = 3;
        """)
        db.commit()
        db.close()
        repo = Repository(path, Path(self.tmp.name) / "s2")
        self.assertEqual(repo.window_fractions("ACME", "P1", "", 50.0, (0.4, 0.4)), (0.3, 0.3, "tuned"))
        self.assertTrue((Path(self.tmp.name) / "old.v3-backup.db").is_file())
        repo.close()


class LongRunTest(unittest.TestCase):
    def test_memory_and_time_stay_flat(self):
        """จำลอง 4 ชั่วโมงที่ 10 Hz (144,000 จุด) แบบจับตามเวลา: engine ต้องไม่เก็บข้อมูลดิบทุกจุดใน RAM"""
        hz, rate = 10.0, 100.0
        config = SessionConfig(target_flow=rate, strategy="time_interval", duration_min=4 * 60.0, window_s=10.0,
                               end_mode=EndMode.TIME)
        engine = FlowEngine(config, EngineSettings(ml_per_g=1.0))
        step = rate / 3600.0 / hz
        tracemalloc.start()
        start = time.perf_counter()
        for i in range(int(4 * 3600 * hz)):
            engine.process(Sample(i / hz, 100.0 + i * step))
            if i == 36000:
                first_hour, _ = tracemalloc.get_traced_memory()
        elapsed = time.perf_counter() - start
        current, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertEqual(engine.span.count, int(4 * 3600 * hz))
        self.assertGreater(engine.stats.count, 1400)
        # หลังชั่วโมงแรก โตเฉพาะรายการช่วงวัด (~1,440 ช่วง) — ไม่ใช่ 144,000 จุด
        self.assertLess(current - first_hour, 3_000_000)
        self.assertLess(elapsed / engine.span.count, 0.0005)          # < 0.5 ms ต่อจุด (ตราชั่งให้ 1 จุดทุก 100 ms)


if __name__ == "__main__":
    unittest.main()
