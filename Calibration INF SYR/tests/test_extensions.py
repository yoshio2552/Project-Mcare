"""ทดสอบส่วนต่อขยาย: ตราชั่ง stream/poll + auto detect, ค่าแก้, self-check, โปรไฟล์, ฐานข้อมูล, replay

รัน:  python -m unittest discover -s tests -v
"""
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from config.settings import AppSettings, EngineSettings, ReplaySettings, SelfCheckSettings, SerialSettings, SimulatorSettings
from core.corrections import BaselineEngine, analyse_baseline, choose_density, water_density
from core.engine import FlowEngine
from core.models import JobInfo, Sample, SessionConfig
from core.prerun import flow_stability
from core.profiles import PumpProfile, profile_key, stroke_volume_ml
from core.stats import flow_ml_per_h
from hardware.replay import ReplayBalance
from hardware.serial_balance import SerialBalance, detect_settings
from hardware.simulator import SimulatedBalance
from services.session_store import Repository


class FakeSerial:
    """พอร์ตจำลอง: mode = 'stream' ส่งเอง, 'poll' ตอบเมื่อถูกถาม, 'silent' เงียบ"""

    def __init__(self, mode: str, line: bytes = b"ST,+00012.345  g\r\n"):
        self.mode, self.line = mode, line
        self.pending = 0
        self.written = []
        self.closed = False

    def readline(self) -> bytes:
        time.sleep(0.002)
        if self.mode == "stream":
            return self.line
        if self.mode == "poll" and self.pending:
            self.pending -= 1
            return self.line
        return b""

    def write(self, data: bytes) -> None:
        self.written.append(data)
        self.pending += 1

    def reset_input_buffer(self) -> None:
        self.pending = 0

    def close(self) -> None:
        self.closed = True


class SerialBalanceTest(unittest.TestCase):
    def test_auto_picks_stream(self):
        port = FakeSerial("stream")
        balance = SerialBalance(SerialSettings(mode="auto"), factory=lambda s: port)
        balance.open()
        self.assertEqual(balance.mode, "stream")
        sample = balance.read()
        self.assertEqual((sample.weight, sample.stable), (12.345, True))
        self.assertEqual(port.written, [])                  # โหมด stream ต้องไม่ส่งคำสั่งใดๆ
        balance.close()

    def test_auto_picks_poll_and_paces_requests(self):
        port = FakeSerial("poll", b"US,+00001.000  g\r\n")
        balance = SerialBalance(SerialSettings(mode="auto", poll_interval_s=0.02), factory=lambda s: port)
        balance.open()
        self.assertEqual(balance.mode, "poll")
        port.written.clear()
        samples = []
        deadline = time.perf_counter() + 0.25
        while time.perf_counter() < deadline:
            sample = balance.read()
            if sample:
                samples.append(sample)
        self.assertEqual(set(port.written), {b"Q\r\n"})
        self.assertGreaterEqual(len(samples), 6)
        self.assertLessEqual(len(samples), 14)              # ~0.25 s / 0.02 s ไม่ยิงรัว
        self.assertFalse(samples[0].stable)
        self.assertGreater(balance.last_latency_s, 0)
        balance.close()

    def test_silent_balance_raises_and_closes(self):
        port = FakeSerial("silent")
        balance = SerialBalance(SerialSettings(mode="auto"), factory=lambda s: port)
        with self.assertRaises(IOError):
            balance.open()
        self.assertTrue(port.closed)

    def test_detect_settings_finds_working_combination(self):
        tried = []

        def factory(settings):
            tried.append((settings.port, settings.baudrate, settings.parity))
            if settings.port == "COM1":
                raise OSError("busy")
            return FakeSerial("poll" if (settings.baudrate, settings.parity) == (2400, "E") else "silent")

        found = detect_settings(SerialSettings(port="COM1"), ports=["COM1", "COM7"], factory=factory)
        self.assertEqual((found.port, found.baudrate, found.bytesize, found.parity, found.mode),
                         ("COM7", 2400, 7, "E", "poll"))
        self.assertEqual(found.sample_line, "ST,+00012.345  g")
        self.assertGreater(found.rate_hz, 0)
        self.assertEqual(tried[0][0], "COM1")               # ลองพอร์ตที่ตั้งไว้ก่อน
        self.assertIsNone(detect_settings(SerialSettings(port="COM7"), ports=[], factory=lambda s: FakeSerial("silent")))


class CorrectionsTest(unittest.TestCase):
    def test_water_density(self):
        self.assertAlmostEqual(water_density(20.0), 0.99821, places=5)
        self.assertAlmostEqual(water_density(25.0), 0.99705, places=5)
        self.assertEqual(choose_density(None, 0.9982), (0.9982, "settings"))
        self.assertEqual(choose_density(95.0, 0.9982), (0.9982, "settings"))    # นอกช่วงของสูตร
        density, source = choose_density(25.0, 0.9982)
        self.assertEqual(source, "temperature")
        self.assertAlmostEqual(density, 0.99705, places=5)

    def test_baseline_is_removed_from_flow(self):
        # ปั๊มส่ง 10 g/h แต่ระเหย 0.5 g/h -> ตราชั่งเห็น 9.5 g/h ; หัก baseline (-0.5) แล้วต้องได้ 10
        self.assertAlmostEqual(flow_ml_per_h(9.5, 3600.0, 1.0, baseline_g_per_h=-0.5), 10.0)
        self.assertAlmostEqual(flow_ml_per_h(9.5, 3600.0, 1.0), 9.5)

    def test_engine_applies_evaporation_baseline(self):
        sim = SimulatorSettings(error_pct=0.0, ripple_pct=0.0, noise_g=0.0, evaporation_mg_h=200.0)
        config = SessionConfig(strategy="time_total", target_flow=10.0, duration_min=5.0)
        errors = {}
        for name, baseline in (("raw", 0.0), ("corrected", -0.2)):
            settings = EngineSettings(density_g_per_ml=1.0, baseline_g_per_h=baseline)
            source = SimulatedBalance(sim, 10.0, 1.0)
            engine = FlowEngine(config, settings)
            for i in range(10_000):
                if engine.process(Sample(i * 0.1, source.weight_at(i * 0.1))).finished:
                    break
            errors[name] = engine.current_error()
        self.assertAlmostEqual(errors["raw"], -2.0, delta=0.05)         # ระเหย 0.2 g/h จาก 10 g/h
        self.assertAlmostEqual(errors["corrected"], 0.0, delta=0.05)

    def test_engine_copies_settings(self):
        settings = EngineSettings()
        engine = FlowEngine(SessionConfig(target_flow=10.0), settings)
        settings.density_g_per_ml = 5.0                                  # แก้หน้าตั้งค่าระหว่างรัน
        self.assertEqual(engine.settings.density_g_per_ml, 0.9982)
        self.assertEqual(engine.summary("stopped").engine_settings["density_g_per_ml"], 0.9982)

    def test_stats_use_every_interval(self):
        config = SessionConfig(strategy="time_interval", target_flow=50.0, duration_min=50.0, window_s=10.0)
        source = SimulatedBalance(SimulatorSettings(ripple_pct=0.0, noise_g=0.0), 50.0, 0.9982)
        engine = FlowEngine(config, EngineSettings())
        for i in range(40_000):
            if engine.process(Sample(i * 0.1, source.weight_at(i * 0.1))).finished:
                break
        self.assertEqual(engine.stats.count, 300)
        self.assertEqual(len(engine._flows), 300)                        # ไม่ตัดเหลือ 200 อีกแล้ว


class SelfCheckTest(unittest.TestCase):
    def _samples(self, rate_mg_h, minutes=10, noise=0.0002, bend=0.0):
        rng = np.random.default_rng(3)
        t = np.arange(0, minutes * 60 + 0.1, 0.1)
        w = 150.0 + rate_mg_h / 1000 / 3600 * t + bend * (t / t[-1]) ** 2 + rng.normal(0, noise, len(t))
        return list(zip(t.tolist(), np.round(w, 4).tolist()))

    def test_evaporation_rate_is_measured(self):
        result = analyse_baseline(self._samples(-40.0), SelfCheckSettings())
        self.assertTrue(result.passed, result.reasons)
        self.assertAlmostEqual(result.rate_g_per_h * 1000, -40.0, delta=3.0)
        self.assertAlmostEqual(result.noise_sd_g, 0.0002, delta=0.0001)
        self.assertLess(result.se_g_per_h * 1000, 2.0)

    def test_fails_when_not_settled_or_too_short_or_leaking(self):
        criteria = SelfCheckSettings()
        self.assertFalse(analyse_baseline(self._samples(-40.0, bend=0.05), criteria).passed)
        self.assertFalse(analyse_baseline(self._samples(-40.0, minutes=3), criteria).passed)
        self.assertFalse(analyse_baseline(self._samples(5000.0), criteria).passed)
        self.assertFalse(analyse_baseline([], criteria).passed)

    def _real_like(self, rate_mg_h, change_mg_h=0.0, seed=5):
        """เหมือนตราชั่งจริง: ค่าไหลขึ้นลงช้าๆ (random walk ที่ถูกดึงกลับ) + ปัดเศษ 1 mg, 10 นาที 5 Hz"""
        rng = np.random.default_rng(seed)
        t = np.arange(0, 600.1, 0.2)
        wander = np.zeros(len(t))
        for i in range(1, len(t)):
            wander[i] = 0.995 * wander[i - 1] + rng.normal(0, 0.0004)
        rate = rate_mg_h + change_mg_h * (t > 300)                 # อัตราเปลี่ยนกลางทาง
        w = 150.0 + np.cumsum(rate / 1000 / 3600 * 0.2) + wander
        return list(zip(t.tolist(), np.round(w, 3).tolist()))

    def test_real_like_steady_evaporation_passes(self):
        """ค่าไหลช้าๆ + ปัดเศษ 1 mg ทำให้ครึ่งแรก/หลังต่างกันเกิน 30 mg/h ได้เองโดยไม่ได้เปลี่ยนจริง — ต้องผ่าน"""
        criteria = SelfCheckSettings()
        passed = 0
        for seed in range(8):
            result = analyse_baseline(self._real_like(-200.0, seed=seed), criteria)
            passed += result.passed
            self.assertAlmostEqual(result.rate_g_per_h * 1000, -200.0, delta=60.0)
        self.assertGreaterEqual(passed, 7)
        # เกณฑ์เดิม (ตัวเลขตายตัว 30 mg/h) จะไม่ผ่านแทบทุกครั้ง
        old = [analyse_baseline(self._real_like(-200.0, seed=s), criteria).halves_diff_g_per_h * 1000 > 30 for s in range(8)]
        self.assertGreaterEqual(sum(old), 4)

    def test_real_like_changing_rate_fails(self):
        """แบบที่เห็นจริงเมื่อเช้า: ครึ่งแรกน้ำหนักลด ครึ่งหลังน้ำหนักเพิ่ม (มีน้ำไหลเข้า) — ต้องไม่ผ่าน"""
        result = analyse_baseline(self._real_like(-650.0, change_mg_h=980.0), SelfCheckSettings(max_abs_rate_mg_h=5000))
        self.assertFalse(result.passed)
        self.assertGreater(result.halves_z, 3.0)
        self.assertIn("Rate changed between the first and second half (not settled)", result.reasons)

    def test_baseline_engine_runs_for_duration(self):
        engine = BaselineEngine(SelfCheckSettings(duration_min=1.0))
        finished = [engine.process(Sample(100 + i * 0.1, 150.0)).finished for i in range(700)]
        self.assertEqual(finished.index(True), 600)
        self.assertAlmostEqual(engine.result().rate_g_per_h, 0.0, places=6)


class StabilityTest(unittest.TestCase):
    def test_low_rate_quantisation_is_allowed_for(self):
        # 10 ml/h บนตราชั่งละเอียด 1 mg: ช่วง 15 s เพิ่มแค่ ~41 mg การปัดเศษทำให้ดูแกว่งเกิน 2 %
        t = np.arange(0, 120, 0.1)
        w = np.round(10 * 0.9982 / 3600 * t, 3)
        stability = flow_stability(t, w, 15.0, 4, base_limit_pct=2.0)
        self.assertGreater(stability.limit_pct, 4.0)
        self.assertTrue(stability.stable)

    def test_slow_drift_is_rejected(self):
        t = np.arange(0, 120, 0.1)
        w = 0.0139 * (t + 0.0009 * t ** 2)                    # flow ไหลขึ้นเรื่อยๆ
        stability = flow_stability(t, w, 15.0, 4, base_limit_pct=10.0)
        self.assertLess(stability.variation_pct, 10.0)        # แต่ละช่วงยังดูใกล้กัน...
        self.assertFalse(stability.stable)                    # ...แต่แนวโน้มชัด จึงไม่ถือว่านิ่ง


class ProfileTest(unittest.TestCase):
    def test_profile_math(self):
        self.assertEqual(profile_key(" Terumo ", "TE-112", "  Set  A"), ("terumo", "te-112", "set a"))
        self.assertAlmostEqual(stroke_volume_ml(50.0, 60.0), 0.8333, places=4)
        profile = PumpProfile(stroke_volume_ml=0.8333, runs=1)
        self.assertAlmostEqual(profile.period_s(200.0), 15.0, places=2)
        self.assertEqual(profile.window_points(200.0, 0.1, 0.4), 60)
        self.assertTrue(profile.accepts(0.9))
        self.assertFalse(profile.accepts(1.7))                # รอบที่จับพลาดเป็น 2 เท่า ต้องไม่ถูกรวม


class RepositoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = Repository(root / "test.db", root / "sessions")

    def tearDown(self):
        self.repo.close()
        self.tmp.cleanup()

    def _run(self, job: JobInfo, mode="inspection", target=50.0):
        from core.models import RunMode
        config = SessionConfig(job=job, run_mode=RunMode(mode), strategy="time_interval",
                               target_flow=target, duration_min=1.0, window_s=30.0, job_id="J1")
        source = SimulatedBalance(SimulatorSettings(ripple_pct=0.0, noise_g=0.0), target, 0.9982)
        engine = FlowEngine(config, EngineSettings())
        for i in range(2000):
            if engine.process(Sample(i * 0.1, source.weight_at(i * 0.1))).finished:
                break
        folder = self.repo.new_session_folder(datetime.now(), job.pump_type.value, target)
        (folder / "raw.csv").write_text("t_s,weight_g\n0.0,0.0\n0.1,0.0014\n", encoding="utf-8")
        return self.repo.save(engine.summary("completed"), engine.intervals, folder), folder

    def test_save_list_load_delete(self):
        ref, folder = self._run(JobInfo(brand="Terumo", model="TE-112", serial_no="20481", accessories=["Battery"]))
        self._run(JobInfo(brand="B.Braun", model="Space", serial_no="777"), mode="calibration")
        self.assertEqual(len(self.repo.list()), 2)
        self.assertEqual(len(self.repo.list("calibration")), 1)
        self.assertEqual(self.repo.list("quick_test"), [])
        detail = self.repo.load(ref)
        self.assertEqual(detail.summary["config"]["job"]["accessories"], ["Battery"])
        self.assertEqual(len(detail.intervals), 2)
        self.assertEqual(len(detail.samples), 2)
        self.repo.delete(ref)
        self.assertFalse(folder.exists())
        self.assertEqual(len(self.repo.list()), 1)

    def test_search_devices_by_scope(self):
        self._run(JobInfo(brand="Terumo", model="TE-112", serial_no="20481", asset_id="BME-0457"))
        self._run(JobInfo(brand="Terumo", model="TE-112", serial_no="20481", asset_id="BME-0457"))
        self._run(JobInfo(brand="B.Braun", model="Space", serial_no="777", asset_id="BME-0900"))
        self.assertEqual(len(self.repo.search_devices("")), 2)                   # ไม่ซ้ำเครื่อง
        self.assertEqual([d["model"] for d in self.repo.search_devices("terumo 204")], ["TE-112"])
        self.assertEqual([d["serial_no"] for d in self.repo.search_devices("777", "serial")], ["777"])
        self.assertEqual(self.repo.search_devices("777", "code"), [])
        self.assertEqual(len(self.repo.search_devices("bme-09", "code")), 1)
        self.assertEqual(len(self.repo.search_devices("j1", "job")), 2)
        self.assertEqual(self.repo.search_devices("")[0]["last_verdict"], "PASS")

    def test_profile_learning(self):
        self.assertIsNone(self.repo.get_profile("Terumo", "TE-112", "Set A"))
        self.assertIsNone(self.repo.expected_period("Terumo", "TE-112", "Set A", 50.0))
        self.assertEqual(self.repo.add_observation("Terumo", "TE-112", "Set A", 50.0, 60.0, 50.0)[1], "merged")
        profile, status = self.repo.add_observation("terumo ", "te-112", "set a", 200.0, 15.3, 200.0)
        self.assertEqual((profile.runs, status), (2, "merged"))
        self.assertAlmostEqual(profile.stroke_volume_ml, (0.8333 + 0.85) / 2, places=3)
        # rate ที่ไม่เคยวัด: คำนวณจากปริมาตรต่อรอบ ; rate ที่เคยวัด: ใช้ค่าที่วัดจริง
        self.assertAlmostEqual(self.repo.expected_period("Terumo", "TE-112", "Set A", 100.0), 0.8417 * 36, delta=0.1)
        self.assertAlmostEqual(self.repo.expected_period("Terumo", "TE-112", "Set A", 200.0), 15.3)
        # จับรอบพลาดเป็น 2 เท่าที่ rate เดิม -> ไม่นำไปใช้
        profile, status = self.repo.add_observation("Terumo", "TE-112", "Set A", 50.0, 120.0, 50.0)
        self.assertEqual((profile.runs, status), (2, "rejected"))
        self.assertAlmostEqual(self.repo.expected_period("Terumo", "TE-112", "Set A", 50.0), 60.0)
        # rate ใหม่ที่ไม่เป็นไปตามปริมาตรต่อรอบคงที่ -> จำไว้เฉพาะ rate นั้น ไม่ทำให้โปรไฟล์เพี้ยน
        profile, status = self.repo.add_observation("Terumo", "TE-112", "Set A", 10.0, 90.0, 10.0)
        self.assertEqual((profile.runs, status), (2, "rate_only"))
        self.assertAlmostEqual(self.repo.expected_period("Terumo", "TE-112", "Set A", 10.0), 90.0)
        self.assertIsNone(self.repo.get_profile("Terumo", "TE-112", "Set B"))    # ชุดสายต่างกัน = คนละโปรไฟล์
        self.assertEqual(self.repo.add_observation("", "", "", 50.0, 60.0, 50.0), (None, ""))

    def test_model_items_are_kept_per_model(self):
        self.assertEqual(self.repo.model_items("Terumo", "TE-112", "part"), [])
        self.repo.remember_items("Terumo", "TE-112", "part", listed=["Tubing guide"], checked=["Battery"])
        self.repo.remember_items(" terumo", "te-112 ", "part", listed=[], checked=["Battery", "Tubing guide"])
        self.assertEqual(self.repo.model_items("Terumo", "TE-112", "part"), [("Battery", 2), ("Tubing guide", 1)])
        self.assertEqual(self.repo.model_items("Terumo", "TE-112", "accessory"), [])    # แยกชนิด
        self.assertEqual(self.repo.model_items("B.Braun", "Space", "part"), [])         # แยกรุ่น
        self.repo.forget_item("Terumo", "TE-112", "part", "Battery")
        self.assertEqual(self.repo.model_items("Terumo", "TE-112", "part"), [("Tubing guide", 1)])
        self.repo.remember_items("", "", "part", listed=["X"], checked=["X"])           # ไม่มีชื่อรุ่น = ไม่จำ
        self.assertEqual(self.repo.model_items("", "", "part"), [])

    def test_self_check_is_valid_for_the_day(self):
        from core.corrections import SelfCheckResult
        self.assertIsNone(self.repo.latest_self_check())
        today = datetime.now().isoformat(timespec="seconds")
        self.repo.add_self_check(SelfCheckResult(measured_at="2020-01-01T10:00:00", passed=True, rate_g_per_h=-0.03))
        self.assertIsNone(self.repo.latest_self_check())
        self.repo.add_self_check(SelfCheckResult(measured_at=today, passed=True, rate_g_per_h=-0.04))
        self.assertAlmostEqual(self.repo.latest_self_check().rate_g_per_h, -0.04)


class ReplayAndSettingsTest(unittest.TestCase):
    def test_replay_feeds_recorded_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "raw.csv"
            path.write_text("t_s,weight_g\n5.0,1.0\n5.1,1.1\nbad,row\n5.2,1.2\n", encoding="utf-8")
            source = ReplayBalance(ReplaySettings(path=str(path), speed=1000))
            source.open()
            got = []
            while len(got) < 3:
                sample = source.read()
                if sample:
                    got.append((sample.t, sample.weight))
            self.assertEqual(got, [(5.0, 1.0), (5.1, 1.1), (5.2, 1.2)])
            with self.assertRaises(IOError):
                ReplayBalance(ReplaySettings(path="")).open()

    def test_settings_lists_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            settings = AppSettings()
            settings.catalog.parts = ["แบตเตอรี่", "Door"]
            settings.serial.mode = "poll"
            settings.save(path)
            loaded = AppSettings.load(path)
            self.assertEqual(loaded.catalog.parts, ["แบตเตอรี่", "Door"])
            self.assertEqual(loaded.serial.mode, "poll")


if __name__ == "__main__":
    unittest.main()
