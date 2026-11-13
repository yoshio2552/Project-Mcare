"""ทดสอบชั้น core + hardware (ไม่ต้องมี Qt / เครื่องจริง)

รัน:  python -m unittest discover -s tests -v
"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import AppSettings, EngineSettings, SimulatorSettings
from core import stats
from core.cycle_analyzer import DOWN, TOP, CycleAnalyzer
from core.engine import FlowEngine
import numpy as np

from core.models import EndMode, JobInfo, PumpType, Sample, SessionConfig, Stage, StartMode, Verdict
from core.prerun import PeriodEstimator, flow_variation
from core.strategies import STRATEGIES
from hardware import SOURCES
from hardware.parsers import parse_line
from hardware.simulator import SimulatedBalance


def run_simulation(config: SessionConfig, sim: SimulatorSettings, engine_settings: EngineSettings,
                   max_samples: int = 200_000, on_result=None) -> FlowEngine:
    """ป้อนข้อมูลจำลองเข้า engine ตรงๆ (ไม่รอเวลา) จนจบการทดสอบ"""
    source = SimulatedBalance(sim, config.target_flow, engine_settings.density_g_per_ml, seed=1)
    engine = FlowEngine(config, engine_settings)
    dt = 1.0 / sim.sample_rate_hz
    for i in range(max_samples):
        t = i * dt
        result = engine.process(Sample(t, round(source.weight_at(t), 4)))
        if on_result:
            on_result(engine, result)
        if result.finished:
            break
    return engine


class StatsTest(unittest.TestCase):
    def test_t_score(self):
        self.assertAlmostEqual(stats.t_score(2), 12.706, places=2)
        self.assertAlmostEqual(stats.t_score(30), 2.045, places=2)
        self.assertAlmostEqual(stats.t_score(1000), 1.962, places=2)
        self.assertEqual(stats.t_score(1), 0.0)

    def test_confidence_interval(self):
        mean, margin = stats.confidence_interval([10.0, 12.0, 14.0])
        self.assertAlmostEqual(mean, 12.0)
        self.assertAlmostEqual(margin, 4.303 * 2.0 / math.sqrt(3), places=2)
        self.assertEqual(stats.confidence_interval([5.0]), (5.0, 0.0))

    def test_regression_slope(self):
        points = [(100.0 + i * 0.1, 3.0 + 0.5 * i * 0.1) for i in range(50)]
        self.assertAlmostEqual(stats.regression_slope(points), 0.5, places=6)
        self.assertEqual(stats.regression_slope(points[:2]), 0.0)

    def test_percent_error_and_flow(self):
        self.assertAlmostEqual(stats.percent_error(51.0, 50.0), 2.0)
        self.assertEqual(stats.percent_error(1.0, 0.0), 0.0)
        self.assertAlmostEqual(stats.flow_ml_per_h(1.0, 72.0), 50.0)
        self.assertEqual(stats.flow_ml_per_h(-1.0, 10.0), 0.0)


class ParseWeightTest(unittest.TestCase):
    def test_parse(self):
        reading = parse_line("ST,+00012.345  g\r\n")
        self.assertEqual((reading.weight, reading.stable), (12.345, True))
        self.assertEqual(parse_line("US,-00000.021  g").stable, False)
        self.assertAlmostEqual(parse_line("US,-00000.021  g").weight, -0.021)
        self.assertAlmostEqual(parse_line("ST,+0123.4 mg").weight, 0.1234)
        self.assertIsNone(parse_line("OL,+99999.999  g"))          # เกินพิกัด
        self.assertIsNone(parse_line("QT,+00000012 PC"))           # โหมดนับชิ้น ไม่ใช่น้ำหนัก
        self.assertEqual(parse_line("  - 0.0021 g").weight, -0.0021)   # รูปแบบทั่วไป
        self.assertIsNone(parse_line("no number"))
        self.assertIsNone(parse_line(""))


class CycleAnalyzerTest(unittest.TestCase):
    def test_alternating_extrema_and_cycles(self):
        analyzer = CycleAnalyzer(n_bar=5)
        kinds, cycles = [], []
        for i in range(400):
            t = i * 0.1
            event = analyzer.update(t, weight=t, slope=math.sin(2 * math.pi * t / 4.0))
            if event:
                kinds.append(event.point.kind)
                if event.cycle:
                    cycles.append(event.cycle)
        self.assertGreater(len(kinds), 10)
        for a, b in zip(kinds, kinds[1:]):
            self.assertNotEqual(a, b)                       # TOP/DOWN ต้องสลับกันเสมอ
        for cycle in cycles:
            self.assertEqual(cycle.start.kind, cycle.end.kind)
            self.assertAlmostEqual(cycle.end.t - cycle.start.t, 4.0, delta=0.11)
        self.assertEqual({c.pattern for c in cycles}, {"TOP-DOWN-TOP", "DOWN-TOP-DOWN"})
        self.assertIn(kinds[0], (TOP, DOWN))

    def test_flat_signal_has_no_extrema(self):
        analyzer = CycleAnalyzer(n_bar=5)
        self.assertTrue(all(analyzer.update(i, i, 1.0) is None for i in range(100)))


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.sim = SimulatorSettings(error_pct=2.0, noise_g=0.0)
        self.engine_settings = EngineSettings()

    def test_pump_cycle_measures_simulated_error(self):
        config = SessionConfig(target_flow=50.0, duration_min=5.0, tolerance_pct=5.0)
        engine = run_simulation(config, self.sim, self.engine_settings)
        self.assertTrue(engine.finished)
        self.assertGreaterEqual(len(engine.intervals), 8)
        self.assertEqual({iv.chain for iv in engine.intervals}, {0, 1})
        self.assertAlmostEqual(engine.stats.mean_error_pct, 2.0, delta=0.3)
        self.assertAlmostEqual(engine.stats.mean_duration_s, 60.0, delta=1.0)
        # ค่าที่ใช้ตัดสิน = ค่าเฉลี่ยของรอบที่ครบสมบูรณ์ (ไม่ใช่ค่าสะสมที่แกว่งตามจังหวะปั๊ม)
        self.assertEqual(engine.current_error(), engine.stats.mean_error_pct)
        self.assertIs(engine.verdict(), Verdict.PASS)
        self.assertEqual(engine.summary("completed").interval_count, len(engine.intervals))

    def test_fixed_window_and_fail_verdict(self):
        config = SessionConfig(job=JobInfo(pump_type=PumpType.SYRINGE), strategy="time_interval",
                               target_flow=10.0, duration_min=5.0, window_s=30.0, tolerance_pct=1.0)
        sim = SimulatorSettings(error_pct=2.0, ripple_pct=0.0, noise_g=0.0)
        engine = run_simulation(config, sim, self.engine_settings)
        self.assertTrue(engine.finished)
        self.assertEqual(len(engine.intervals), 10)         # 5 นาที / 30 วินาที
        self.assertAlmostEqual(engine.current_error(), 2.0, delta=0.2)
        self.assertIs(engine.verdict(), Verdict.FAIL)

    def test_time_total_gives_single_interval(self):
        config = SessionConfig(strategy="time_total", target_flow=10.0, duration_min=2.0)
        engine = run_simulation(config, SimulatorSettings(error_pct=-1.0, ripple_pct=0.0, noise_g=0.0), self.engine_settings)
        self.assertEqual(len(engine.intervals), 1)
        self.assertAlmostEqual(engine.current_error(), -1.0, delta=0.1)

    def test_cycle_count_end_mode(self):
        config = SessionConfig(target_flow=50.0, end_mode=EndMode.COUNT, cycle_count=3, duration_min=999)
        engine = run_simulation(config, self.sim, self.engine_settings)
        self.assertTrue(engine.finished)
        self.assertEqual([sum(iv.chain == c for iv in engine.intervals) for c in (0, 1)], [3, 3])

    def test_delay_start_discards_prerun_data(self):
        config = SessionConfig(strategy="time_total", target_flow=10.0, duration_min=1.0,
                               start_mode=StartMode.DELAY, start_delay_s=20.0)
        stages = []
        engine = run_simulation(config, SimulatorSettings(ripple_pct=0.0, noise_g=0.0), self.engine_settings,
                                on_result=lambda e, r: stages.append(r.stage))
        self.assertTrue(engine.finished)
        self.assertAlmostEqual(engine.prerun_span.last[0], 20.0, delta=0.11)
        self.assertEqual(engine.span.first[0], 0.0)                # การวัดจริงเริ่มนับเวลาใหม่
        self.assertEqual(stages[0], Stage.PRERUN)
        self.assertEqual(stages[-1], Stage.MEASURING)

    def test_manual_start_waits_for_request(self):
        config = SessionConfig(strategy="time_total", target_flow=10.0, duration_min=1.0, start_mode=StartMode.MANUAL)
        def press_start(engine, result):
            if result.stage is Stage.PRERUN and result.t >= 45.0:
                engine.request_start()
        engine = run_simulation(config, SimulatorSettings(ripple_pct=0.0, noise_g=0.0), self.engine_settings,
                                on_result=press_start)
        self.assertTrue(engine.finished)
        self.assertAlmostEqual(engine.prerun_span.last[0], 45.1, delta=0.11)

    def test_auto_start_waits_for_stable_flow(self):
        config = SessionConfig(strategy="time_total", target_flow=10.0, duration_min=1.0, start_mode=StartMode.AUTO)
        engine = run_simulation(config, SimulatorSettings(ripple_pct=0.0, noise_g=0.0), self.engine_settings)
        self.assertTrue(engine.finished)
        self.assertGreaterEqual(engine.prerun_span.last[0], 60.0)   # ต้องมีข้อมูลครบ 4 ช่วง x 15 s ก่อน
        self.assertLess(engine.prerun_span.last[0], 70.0)

    def test_auto_window_tunes_to_pump_period(self):
        """ปั๊มรอบสั้น (20 s): ค่า manual 250 จุดจับรอบไม่ได้ แต่โหมด auto ปรับหน้าต่างให้เอง"""
        sim = SimulatorSettings(error_pct=2.0, cycle_period_s=20.0, noise_g=0.0)
        config = SessionConfig(target_flow=200.0, duration_min=3.0)
        settings = EngineSettings(window_mode="auto")
        engine = run_simulation(config, sim, settings)
        self.assertTrue(engine.finished)
        self.assertAlmostEqual(engine.pump_period_s, 20.0, delta=0.5)
        self.assertAlmostEqual(engine.settings.regression_window, 80, delta=2)   # 20 s x 0.4 / 0.1 s
        self.assertEqual(settings.regression_window, 250)             # ค่าตั้งของผู้ใช้ไม่ถูกแก้
        self.assertAlmostEqual(engine.stats.mean_duration_s, 20.0, delta=0.5)
        self.assertAlmostEqual(engine.current_error(), 2.0, delta=0.3)

    def test_rejects_bad_target(self):
        with self.assertRaises(ValueError):
            FlowEngine(SessionConfig(target_flow=0.0), self.engine_settings)


class PreRunMathTest(unittest.TestCase):
    def _signal(self, period, seconds, ripple=0.15, noise=0.0002):
        rng = np.random.default_rng(0)
        t = np.arange(0, seconds, 0.1)
        omega = 2 * np.pi / period
        w = 0.0139 * (t + ripple / omega * (1 - np.cos(omega * t))) + rng.normal(0, noise, len(t))
        return t, w

    def test_period_estimate(self):
        for period in (12.0, 60.0):
            t, w = self._signal(period, period * 4)
            self.assertAlmostEqual(PeriodEstimator().estimate(t, w), period, delta=period * 0.03)

    def test_no_period_for_steady_flow(self):
        t, w = self._signal(60.0, 240.0, ripple=0.0)
        self.assertIsNone(PeriodEstimator().estimate(t, w))

    def test_flow_variation(self):
        t, w = self._signal(60.0, 300.0, noise=0.0)
        self.assertGreater(flow_variation(t, w, 15.0, 4), 10.0)       # ช่วงสั้นกว่าคาบ -> เห็นการแกว่ง
        self.assertLess(flow_variation(t, w, 60.0, 4), 0.5)           # ช่วง = 1 คาบ -> หักล้างกัน
        self.assertIsNone(flow_variation(t[:100], w[:100], 15.0, 4))


class RegistryAndSettingsTest(unittest.TestCase):
    def test_registries(self):
        self.assertIn("pump_cycle", STRATEGIES)
        self.assertIn("time_interval", STRATEGIES)
        self.assertIn("time_total", STRATEGIES)
        self.assertEqual({k for k, _ in SOURCES.choices()}, {"serial", "simulator", "replay"})
        with self.assertRaises(KeyError):
            STRATEGIES.create("unknown")

    def test_settings_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            settings = AppSettings()
            settings.source = "simulator"
            settings.serial.port = "COM9"
            settings.engine.density_g_per_ml = 1.0
            settings.save(path)
            loaded = AppSettings.load(path)
            self.assertEqual(loaded.source, "simulator")
            self.assertEqual(loaded.serial.port, "COM9")
            self.assertEqual(loaded.engine.density_g_per_ml, 1.0)
            path.write_text('{"serial": {"baudrate": "bad", "unknown": 1}}', encoding="utf-8")
            self.assertEqual(AppSettings.load(path).serial.baudrate, 9600)


if __name__ == "__main__":
    unittest.main()
