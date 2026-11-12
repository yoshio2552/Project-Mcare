"""ทดสอบตัวเลือก "จับรอบคู่ / จับรอบเดียว" (EngineSettings.cycle_chains) ของวิธี pump_cycle

รัน:  python -m unittest discover -s tests -v
"""
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import AppSettings, EngineSettings, SimulatorSettings
from core.models import EndMode, SessionConfig, Verdict
from test_core import run_simulation


class CycleChainsTest(unittest.TestCase):
    def setUp(self):
        self.sim = SimulatorSettings(error_pct=2.0, noise_g=0.0)

    def test_paired_is_default(self):
        self.assertEqual(EngineSettings().cycle_chains, 2)

    def test_single_chain_uses_only_chain_a(self):
        config = SessionConfig(target_flow=50.0, duration_min=5.0, tolerance_pct=5.0)
        paired = run_simulation(config, self.sim, EngineSettings())
        single = run_simulation(config, self.sim, EngineSettings(cycle_chains=1))
        self.assertTrue(single.finished)
        self.assertEqual({iv.chain for iv in single.intervals}, {0})
        # ได้ราวครึ่งหนึ่งของแบบคู่ (สาย A อย่างเดียว) และผลเท่ากัน
        self.assertAlmostEqual(len(single.intervals), len(paired.intervals) / 2, delta=1)
        self.assertAlmostEqual(single.stats.mean_error_pct, 2.0, delta=0.3)
        self.assertAlmostEqual(single.stats.mean_duration_s, 60.0, delta=1.0)
        self.assertIs(single.verdict(), Verdict.PASS)
        # ค่าสะสม: ไม่มีสาย B และค่ารวม = สาย A
        self.assertIsNone(single.cumulative.flow_b)
        self.assertEqual(single.cumulative.best_flow, single.cumulative.flow_a)
        self.assertEqual(single.summary("completed").engine_settings["cycle_chains"], 1)

    def test_single_chain_count_mode(self):
        config = SessionConfig(target_flow=50.0, end_mode=EndMode.COUNT, cycle_count=4, duration_min=999)
        engine = run_simulation(config, self.sim, EngineSettings(cycle_chains=1))
        self.assertTrue(engine.finished)
        self.assertEqual(len(engine.intervals), 4)

    def test_single_chain_finishes_on_time_with_progress(self):
        config = SessionConfig(target_flow=200.0, duration_min=2.0)
        progress = []
        engine = run_simulation(replace(config), SimulatorSettings(error_pct=0.0, noise_g=0.0, cycle_period_s=10),
                                EngineSettings(cycle_chains=1),
                                on_result=lambda e, r: progress.append(r.progress))
        self.assertTrue(engine.finished)
        self.assertEqual(progress[-1], 1.0)
        self.assertGreater(max(progress[:-1]), 0.5)          # คืบหน้าจริงระหว่างทาง (ไม่ค้างที่ 0)

    def test_setting_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            s = AppSettings()
            s.engine.cycle_chains = 1
            s.ui.interval_style = "points"
            s.ui.interval_moving_avg = False
            s.ui.interval_overall_mean = True
            s.save(path)
            loaded = AppSettings.load(path)
            self.assertEqual(loaded.engine.cycle_chains, 1)
            self.assertEqual((loaded.ui.interval_style, loaded.ui.interval_moving_avg, loaded.ui.interval_overall_mean),
                             ("points", False, True))
        self.assertEqual((AppSettings().ui.interval_style, AppSettings().ui.interval_moving_avg,
                          AppSettings().ui.interval_overall_mean), ("step", True, False))


if __name__ == "__main__":
    unittest.main()
