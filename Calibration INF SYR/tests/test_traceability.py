"""ค่าที่ใช้ตัดสิน = ค่าสะสม, สอบย้อนจากข้อมูลดิบ, เวลาวัด, งบความไม่แน่นอน (2026-11-19)"""
import csv
import gzip
import os
import shutil
import tempfile
import unittest
from dataclasses import asdict, fields
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from config.settings import AppSettings, EngineSettings, SimulatorSettings, UncertaintySettings
from core.engine import FlowEngine
from core.models import EndMode, JobInfo, PumpType, Sample, SessionConfig, StartMode, measured_seconds
from core.uncertainty import budget, k_factor, warn_beyond_tolerance
from hardware.simulator import SimulatedBalance
from services import session_store
from services.audit import audit_folder


def run_engine(minutes=4.0, period=8.0, rate=50.0, chains=1, strategy="pump_cycle", wobble=0.0):
    sim = SimulatedBalance(SimulatorSettings(sample_rate_hz=5.0, cycle_period_s=period, ripple_pct=30.0,
                                             noise_g=0.0002), rate, seed=3)
    config = SessionConfig(target_flow=rate, strategy=strategy, end_mode=EndMode.TIME, start_mode=StartMode.IMMEDIATE,
                           duration_min=minutes, window_s=30.0, job=JobInfo(pump_type=PumpType.INFUSION, brand="ACME",
                                                                            model="P1", serial_no="S1"))
    settings = EngineSettings(regression_window=12, cycle_half_window=12, window_mode="manual", cycle_chains=chains,
                              ml_per_g=1.003, expected_period_s=period, expected_period_source="rate")
    engine = FlowEngine(config, settings)
    samples = []
    for i in range(int((minutes + 2) * 60 * 5)):
        t = i / 5.0 + (0.03 * ((i * 7919) % 11 - 5) / 5 if wobble else 0.0)     # เวลาไม่สม่ำเสมอเล็กน้อย
        result = engine.process(Sample(t, round(sim.weight_at(t), 4)))
        samples.append((result.t, result.weight))       # แบบ RawRecorder: เวลานับจากเริ่มวัด
        if result.finished:
            break
    return engine, samples


class MeasuredValueTest(unittest.TestCase):
    def test_measured_equals_cumulative_from_first_peak(self):
        # ผู้ใช้: ค่าสะสมจากจุดเริ่มของ peak แรกถึงจุดสุดท้าย ต้องเท่ากับค่าที่ได้ — ตอนนี้ตรงทุกหลัก
        engine, _ = run_engine(wobble=True)
        summary = engine.summary("completed")
        a = [iv for iv in engine.intervals if iv.chain == 0]
        first, last = a[0], a[-1]
        cumulative = ((last.end_w - first.start_w) / (last.end_t - first.start_t) * 3600.0) * 1.003
        self.assertAlmostEqual(summary.mean_flow, cumulative, places=9)
        self.assertAlmostEqual(summary.total_mass_g, last.end_w - first.start_w, places=9)
        self.assertAlmostEqual(summary.measured_s, last.end_t - first.start_t, places=6)
        # ค่าเฉลี่ยธรรมดาของ flow รายช่วงเก็บไว้เทียบ (ต่างกันเมื่อช่วงยาวไม่เท่ากัน)
        self.assertIsNotNone(summary.mean_flow_cycles)

    def test_measured_seconds_helper(self):
        self.assertEqual(measured_seconds({"measured_s": 305.9, "duration_s": 322.4}), 305.9)
        self.assertEqual(measured_seconds({"duration_s": 322.4}), 322.4)        # ผลเก่า


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="deltam-audit-"))
        self.repo = session_store.Repository(self.tmp / "t.db", self.tmp / "sessions")

    def tearDown(self):
        self.repo._db.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _saved(self, strategy="pump_cycle"):
        engine, samples = run_engine(strategy=strategy, wobble=True)
        summary = engine.summary("completed")
        folder = self.tmp / f"run_{strategy}"
        folder.mkdir()
        with open(folder / "raw.csv", "w", encoding="utf-8") as f:
            f.write("t_s,weight_g\n" + "".join(f"{t:.4f},{w:.4f}\n" for t, w in samples))
        ref = self.repo.save(summary, engine.intervals, folder)
        detail = self.repo.load(ref)
        return folder, detail.summary, ref

    def test_fresh_result_passes_every_check_exactly(self):
        for strategy in ("pump_cycle", "time_interval"):
            folder, summary, ref = self._saved(strategy)
            audit = audit_folder(folder, summary)
            self.assertTrue(audit.exact, strategy)
            self.assertTrue(audit.ok, [(c.name, c.detail) for c in audit.checks if not c.ok])
            with open(folder / "intervals.csv", encoding="utf-8") as f:
                self.assertIn("t_start_s", next(csv.reader(f)))
            self.assertEqual(len(self.repo.file_hash(ref, "raw.csv.gz")), 64)

    def test_tampered_raw_data_is_caught(self):
        folder, summary, _ = self._saved()
        boundary = list(csv.DictReader(open(folder / "intervals.csv", encoding="utf-8")))[2]["t_start_s"]
        raw = folder / "raw.csv.gz"
        with gzip.open(raw, "rt", encoding="utf-8") as f:
            lines = f.read().splitlines()
        index = next(i for i, line in enumerate(lines) if line.startswith(boundary + ","))
        t, w = lines[index].split(",")
        lines[index] = f"{t},{float(w) + 0.005:.4f}"        # แก้น้ำหนักที่จุดต้นช่วง 5 mg
        with gzip.open(raw, "wt", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        audit = audit_folder(folder, summary)
        self.assertFalse(audit.ok)
        failed = {c.name for c in audit.checks if not c.ok}
        self.assertIn("Interval weights match raw data", failed)


    def test_earlier_results_for_repeatability(self):
        for _ in range(3):
            self._saved_counter = getattr(self, "_saved_counter", 0) + 1
            engine, samples = run_engine()
            folder = self.tmp / f"rep{self._saved_counter}"
            folder.mkdir()
            (folder / "raw.csv").write_text("t_s,weight_g\n", encoding="utf-8")
            self.repo.save(engine.summary("completed"), engine.intervals, folder)
        job = JobInfo(pump_type=PumpType.INFUSION, brand="ACME", model="P1", serial_no="S1")
        values, source = self.repo.earlier_errors(job, 50.0)
        self.assertEqual((len(values), source), (3, "same device"))
        values, source = self.repo.earlier_errors(JobInfo(brand="ACME", model="P1", serial_no="OTHER"), 50.0)
        self.assertEqual((len(values), source), (3, "same model"))
        self.assertEqual(self.repo.earlier_errors(job, 200.0)[0], [])          # rate อื่นไม่นับ


class UncertaintyTest(unittest.TestCase):
    def summary(self):
        engine, _ = run_engine()
        return asdict(engine.summary("completed"))

    def test_budget_components_and_expansion(self):
        s = self.summary()
        b = budget(s, UncertaintySettings(), history=[])
        names = [c["name"] for c in b["components"]]
        for name in ("Balance calibration", "Balance resolution", "Timestamps", "Water temperature → density",
                     "Evaporation / self-check", "Repeatability (earlier runs)"):
            self.assertIn(name, names)
        self.assertNotIn("2SD", " ".join(names))                    # ผู้ใช้: 2SD ของช่วงวัดไม่เข้าสมการ
        u_c = sum(c["u_rel_pct"] ** 2 for c in b["components"]) ** 0.5
        self.assertAlmostEqual(b["u_c_pct"], u_c, places=9)
        self.assertAlmostEqual(b["U_pct"], round(b["k"] * u_c, 3), places=6)
        self.assertAlmostEqual(b["k"], 2.0, places=2)                # Type B ทั้งหมด -> ν = ∞
        self.assertTrue(b["simulated"])
        self.assertEqual(b["settings"]["balance_u_g"], 0.0015)      # ค่าตั้งที่ใช้บันทึกไปกับผล (สอบย้อน)

    def test_repeatability_from_earlier_runs_sets_degrees_of_freedom(self):
        s = self.summary()
        b = budget(s, UncertaintySettings(), history=[-1.0, 0.5, 1.5])
        rep = next(c for c in b["components"] if c["name"].startswith("Repeatability"))
        self.assertAlmostEqual(rep["u_rel_pct"], 1.2583, places=3)
        self.assertEqual(rep["nu"], 2.0)
        self.assertGreater(b["k"], 2.1)                             # ν_eff ต่ำ -> k มากกว่า 2
        self.assertAlmostEqual(k_factor(1e9), 2.0)

    def test_warning_only_when_pass_but_beyond_with_u(self):
        self.assertTrue(warn_beyond_tolerance(4.5, 0.8, 5.0))
        self.assertFalse(warn_beyond_tolerance(3.0, 0.8, 5.0))
        self.assertFalse(warn_beyond_tolerance(5.5, 0.8, 5.0))     # ไม่ผ่านอยู่แล้ว
        self.assertFalse(warn_beyond_tolerance(4.5, None, 5.0))

    def test_settings_page_has_every_field(self):
        from ui.pages.settings import GROUPS
        listed = {f.name for title, items in GROUPS if title == "Uncertainty" for f in items}
        self.assertEqual(listed, {f.name for f in fields(UncertaintySettings)})
        self.assertIsInstance(AppSettings().uncertainty, UncertaintySettings)


if __name__ == "__main__":
    unittest.main()
