"""ทดสอบค่าแก้แปลงน้ำหนักเป็นปริมาตรตาม ISO 4787 (ปัจจัย Z) และการเก็บค่าดิบไว้สอบย้อนหลัง

รัน:  python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import EngineSettings
from core.corrections import air_density, gravimetric_correction, water_density, z_factor
from core.engine import FlowEngine
from core.models import JobInfo, Sample, SessionConfig
from services.session_store import Repository, raw_result, volume_factor


class StandardFormulaTest(unittest.TestCase):
    def test_air_density_oiml(self):
        # OIML R111-1 E.3-1 ที่ 20 °C, 50 %RH, 1013.25 hPa = 1.1993 kg/m³
        self.assertAlmostEqual(air_density(20.0, 50.0, 1013.25) * 1000.0, 1.1993, places=4)
        # ความชื้นมากขึ้น = อากาศเบาลง, ความดันมากขึ้น = หนักขึ้น
        self.assertLess(air_density(25.0, 90.0, 1013.25), air_density(25.0, 10.0, 1013.25))
        self.assertGreater(air_density(25.0, 50.0, 1020.0), air_density(25.0, 50.0, 1000.0))

    def test_z_factor_matches_iso_4787_table(self):
        # ตาราง Z ของ ISO 4787 / ISO 8655-6 ที่ 1013 hPa: 20 °C = 1.0029, 25 °C = 1.0040 ml/g
        for t, expected in ((20.0, 1.0029), (25.0, 1.0040)):
            z = z_factor(water_density(t), air_density(t, 50.0, 1013.25), 8.0)
            self.assertAlmostEqual(z, expected, places=4, msg=t)
        # แรงลอยตัวทำให้ Z มากกว่า 1/ρw ราว 0.1 %
        rho = water_density(20.0)
        self.assertAlmostEqual(z_factor(rho, air_density(20.0, 50.0, 1013.25)) * rho, 1.00106, places=4)

    def test_sources_and_fallbacks(self):
        settings = EngineSettings()
        c = gravimetric_correction(JobInfo(temperature_c=25.0), settings)
        self.assertEqual((c.water_density_source, c.air_temp_source, c.humidity_source, c.pressure_source),
                         ("temperature", "liquid", "settings", "settings"))
        self.assertEqual(c.air_temp_c, 25.0)
        c = gravimetric_correction(JobInfo(temperature_c=22.0, air_temp_c=24.0, humidity_pct=60.0,
                                           pressure_hpa=1008.0), settings)
        self.assertEqual((c.air_temp_source, c.humidity_source, c.pressure_source), ("form", "form", "form"))
        self.assertAlmostEqual(c.ml_per_g, z_factor(water_density(22.0), air_density(24.0, 60.0, 1008.0)), places=12)
        self.assertEqual(c.warnings, [])
        # ค่าผิดช่วง -> ใช้ค่าตั้ง + บันทึกคำเตือน
        c = gravimetric_correction(JobInfo(temperature_c=22.0, humidity_pct=150.0, pressure_hpa=101.3), settings)
        self.assertEqual((c.humidity_source, c.pressure_source), ("settings", "settings"))
        self.assertEqual(len(c.warnings), 2)
        # ไม่กรอกอุณหภูมิ: ความหนาแน่นจากค่าตั้ง + เตือน
        c = gravimetric_correction(JobInfo(), settings)
        self.assertEqual((c.water_density_g_per_ml, c.air_temp_c), (settings.density_g_per_ml, 20.0))
        self.assertTrue(c.warnings)
        # ปิดการแก้แรงลอยตัว = 1/ρw แบบเดิม
        settings.air_buoyancy = False
        c = gravimetric_correction(JobInfo(temperature_c=20.0), settings)
        self.assertAlmostEqual(c.ml_per_g, 1.0 / water_density(20.0), places=12)
        self.assertEqual(c.air_density_g_per_ml, 0.0)

    def test_net_flow(self):
        c = gravimetric_correction(JobInfo(temperature_c=20.0), EngineSettings(), baseline_g_per_h=-0.2)
        self.assertAlmostEqual(c.net_flow(9.8), 10.0 * c.ml_per_g, places=12)


def _run_engine(z: float, baseline: float, rate_g_h: float = 50.0):
    """time_interval 10 s, น้ำหนักขึ้นเป็นเส้นตรง -> flow ดิบ = rate_g_h ทุกช่วง"""
    config = SessionConfig(target_flow=50.0, strategy="time_interval", duration_min=1.0, window_s=10.0)
    settings = EngineSettings(warmup_s=0.0, ml_per_g=z, baseline_g_per_h=baseline)
    engine = FlowEngine(config, settings, correction={"ml_per_g": z})
    t = 0.0
    while not engine.finished and t < 120:
        engine.process(Sample(t, 100.0 + rate_g_h * t / 3600.0))
        t += 0.1
    return engine


class EngineRawFlowTest(unittest.TestCase):
    def test_net_and_raw_are_both_kept(self):
        z, baseline = 1.00285, -0.2
        engine = _run_engine(z, baseline)
        self.assertGreaterEqual(len(engine.intervals), 5)
        for iv in engine.intervals:
            self.assertAlmostEqual(iv.flow_raw, 50.0, places=3)
            self.assertAlmostEqual(iv.flow, (iv.flow_raw - baseline) * z, places=6)
        summary = engine.summary("completed")
        self.assertAlmostEqual(summary.mean_flow_raw, 50.0, places=3)
        self.assertAlmostEqual(summary.error_raw_pct, 0.0, places=2)
        self.assertAlmostEqual(summary.mean_flow, (50.0 + 0.2) * z, places=3)
        self.assertEqual(summary.ml_per_g, z)
        self.assertEqual(summary.correction, {"ml_per_g": z})
        # สูตรสอบย้อนหลังให้ผลเดียวกับที่ engine คำนวณ
        self.assertAlmostEqual((summary.mean_flow_raw - baseline) * z, summary.mean_flow, places=6)

    def test_default_factor_is_inverse_density(self):
        settings = EngineSettings(density_g_per_ml=0.998)
        self.assertAlmostEqual(settings.volume_factor, 1 / 0.998)


class AuditStorageTest(unittest.TestCase):
    def test_saved_intervals_keep_raw_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Repository(Path(tmp) / "t.db", Path(tmp) / "sessions")
            engine = _run_engine(1.003, 0.0)
            summary = engine.summary("completed")
            folder = repo.new_session_folder(engine.started_at, "infusion", 50.0)
            ref = repo.save(summary, engine.intervals, folder)
            detail = repo.load(ref)
            self.assertTrue(detail.intervals)
            for row, iv in zip(detail.intervals, engine.intervals):
                self.assertFalse(row["raw_derived"])
                self.assertAlmostEqual(row["flow_raw"], iv.flow_raw, places=3)
            flow, error, derived = raw_result(detail.summary)
            self.assertFalse(derived)
            self.assertAlmostEqual(flow, summary.mean_flow_raw)
            repo.close()

    def test_old_results_are_derived(self):
        """ผลรุ่นก่อน (ไม่มี mean_flow_raw / ml_per_g): ย้อนสูตร ดิบ = สุทธิ × ρ + B"""
        old = {"config": {"target_flow": 10.0}, "mean_flow": 9.5, "density_g_per_ml": 0.998,
               "baseline_g_per_h": -0.1, "error_pct": -5.0}
        self.assertAlmostEqual(volume_factor(old), 1 / 0.998)
        flow, error, derived = raw_result(old)
        self.assertTrue(derived)
        self.assertAlmostEqual(flow, 9.5 * 0.998 - 0.1)
        self.assertAlmostEqual(error, (flow - 10.0) / 10.0 * 100.0)

    def test_audit_rows_verify_formula(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from ui.dialogs.session_detail import correction_rows
        c = gravimetric_correction(JobInfo(temperature_c=24.0, humidity_pct=55.0), EngineSettings())
        engine = _run_engine(c.ml_per_g, 0.0)
        from dataclasses import asdict
        summary = json.loads(json.dumps(asdict(engine.summary("completed")), default=str))
        summary["correction"] = asdict(c)
        rows = dict(correction_rows(summary))
        check = next(v for k, v in rows.items() if "×" in k)
        self.assertTrue(check.endswith("✓"), check)


if __name__ == "__main__":
    unittest.main()
