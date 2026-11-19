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


    def test_repeatability_table_sets_mean_and_audit_trail(self):
        from core.repeatability import Study, from_input, from_runs
        # กรอกเอง: % และ ml/h ต้องได้ค่าเดียวกันที่ rate นั้น
        self.assertEqual(from_input(0.8, "%", 50.0), (0.8, 0.4))
        self.assertEqual(from_input(0.4, "ml/h", 50.0), (0.8, 0.4))
        pct, mlh = from_runs([49.0, 50.0, 51.0], 50.0)
        self.assertAlmostEqual(mlh, 2.0)                                   # 2 × SD(n−1) = 2 × 1
        self.assertAlmostEqual(pct, 4.0)
        a = self.repo.add_repeat_study("ACME", "P1", "infusion", "Set-A", 50.0,
                                       Study(kind="manual", rate=50.0, sd2_pct=0.8, sd2_ml_h=0.4, input_value=0.8))
        b = self.repo.add_repeat_study("acme ", "p1", "infusion", "set-a", 50.4,      # สะกดต่าง/rate ใกล้ = รายการเดียวกัน
                                       Study(kind="measured", rate=50.4, sd2_pct=1.2, sd2_ml_h=0.6,
                                             runs=[{"ref": "7", "mean_flow": 50.1}]))
        value = self.repo.repeat_value("ACME", "P1", "infusion", "Set-A", 50.0)
        self.assertAlmostEqual(value["sd2_pct"], 1.0)                      # ค่าเฉลี่ยของ 2 ชุด
        self.assertAlmostEqual(value["sd2_ml_h"], 0.5)
        self.assertEqual({x["id"] for x in value["studies"]}, {a, b})
        self.assertIsNone(self.repo.repeat_value("ACME", "P1", "infusion", "Set-B", 50.0))   # ชุดสายอื่น
        self.assertIsNone(self.repo.repeat_value("ACME", "P1", "syringe", "Set-A", 50.0))    # ชนิดอื่น
        self.assertIsNone(self.repo.repeat_value("ACME", "P1", "infusion", "Set-A", 200.0))  # rate อื่น
        self.repo.delete_repeat_study(a)                                   # ลบ = ไม่นับ แต่แถวยังอยู่ (สอบย้อน)
        self.assertAlmostEqual(self.repo.repeat_value("ACME", "P1", "infusion", "Set-A", 50.0)["sd2_pct"], 1.2)
        everything = self.repo.repeat_studies("ACME", "P1", "infusion", "Set-A", 50.0, include_deleted=True)
        self.assertEqual(len(everything), 2)
        self.assertTrue(next(x for x in everything if x.id == a).deleted_at)
        overview = self.repo.repeat_overview()
        self.assertEqual([(o["status"], o["studies"]) for o in overview], [("done", 1)])

    def test_overview_lists_tested_combinations_without_2sd(self):
        engine, _ = run_engine()
        folder = self.tmp / "ov"
        folder.mkdir()
        (folder / "raw.csv").write_text("t_s,weight_g\n", encoding="utf-8")
        self.repo.save(engine.summary("completed"), engine.intervals, folder)
        overview = self.repo.repeat_overview()
        self.assertEqual(len(overview), 1)
        self.assertEqual((overview[0]["model"], overview[0]["rate"], overview[0]["status"]), ("P1", 50.0, "missing"))


class UncertaintyTest(unittest.TestCase):
    def summary(self):
        engine, _ = run_engine()
        return asdict(engine.summary("completed"))

    def test_budget_components_and_expansion(self):
        s = self.summary()
        b = budget(s, UncertaintySettings(), None)
        names = [c["name"] for c in b["components"]]
        for name in ("Balance calibration", "Balance resolution", "Timestamps", "Water temperature → density",
                     "Evaporation / self-check", "Repeatability (2SD entered)"):
            self.assertIn(name, names)
        # ผู้ใช้: 2SD ของช่วงวัดในผลนี้ไม่เข้าสมการ — เปลี่ยน sd2_pct ของผลแล้วงบต้องเท่าเดิม
        s2 = dict(s, sd2_pct=(s.get("sd2_pct") or 0) + 50.0)
        self.assertEqual(budget(s2, UncertaintySettings(), None)["u_c_pct"], budget(s, UncertaintySettings(), None)["u_c_pct"])
        u_c = sum(c["u_rel_pct"] ** 2 for c in b["components"]) ** 0.5
        self.assertAlmostEqual(b["u_c_pct"], u_c, places=9)
        self.assertAlmostEqual(b["U_pct"], b["k"] * u_c, places=12)       # ไม่ปัดตอนเก็บ
        rep = next(c for c in b["components"] if c["name"].startswith("Repeatability"))
        self.assertEqual(rep["u_rel_pct"], 0.0)                            # ไม่มีค่า -> ค่าตั้งต้น 0 (ผู้ใช้)
        self.assertAlmostEqual(b["k"], 2.0, places=2)                # Type B ทั้งหมด -> ν = ∞
        self.assertTrue(b["simulated"])
        self.assertEqual(b["settings"]["balance_u_g"], 0.0015)      # ค่าตั้งที่ใช้บันทึกไปกับผล (สอบย้อน)

    def test_repeatability_entry_enters_budget_as_half_of_2sd(self):
        s = self.summary()
        repeat = {"sd2_pct": 1.0, "sd2_ml_h": 0.5, "rate": 50.0, "studies": [{"id": 4}, {"id": 9}]}
        b = budget(s, UncertaintySettings(), repeat)
        rep = next(c for c in b["components"] if c["name"].startswith("Repeatability"))
        self.assertAlmostEqual(rep["u_rel_pct"], 0.25 / s["mean_flow"] * 100.0, places=9)   # u = 2SD ÷ 2 (ml/h) ÷ Q
        self.assertIn("#4, #9", rep["source"])
        self.assertEqual(b["repeatability"], repeat)                       # ภาพรวมที่ใช้ เก็บไปกับผล
        self.assertAlmostEqual(b["k"], 2.0, places=2)                      # Type B, ν = ∞
        self.assertAlmostEqual(b["U_ml_h"], b["U_pct"] / 100.0 * s["mean_flow"], places=12)
        self.assertAlmostEqual(k_factor(1e9), 2.0)
        self.assertGreater(k_factor(2.0), 4.0)

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
