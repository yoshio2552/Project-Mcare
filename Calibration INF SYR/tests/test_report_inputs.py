"""ทดสอบรอบ 2026-11-18 เย็น: ค่าที่กรอกตั้งแต่ wizard (การอุดตัน ไฟฟ้า ติ๊กขั้นสุดท้าย), การอุดตันเฉลี่ย ± 2SD,
ประเภทงานคิดเอง, วิธีจับแยกราย rate, รูปแบบตัวเลขในใบ (Error% 2 ตำแหน่ง · ปริมาตร 3 ตำแหน่ง · เวลา นาที:วินาที.xx)

รัน:  python -m unittest tests.test_report_inputs -v
"""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from core.models import EndMode, JobInfo, RunMode, StepConfig, TestPlan
from services.report import demo, layout, style
from services.report.model import occl_stats
from tests.test_report_ui import _TmpRepo

app = QApplication.instance() or QApplication([])


class NumbersTest(unittest.TestCase):
    def test_occlusion_mean_and_2sd(self):
        mean, sd2, digits = occl_stats([0.7, 0.7, 0.7])
        self.assertEqual((f"{mean:.{digits}f}", f"{sd2:.{digits}f}"), ("0.70", "0.00"))   # เดิมปัดเป็น "1"
        mean, sd2, digits = occl_stats([68, 71, 69])
        self.assertEqual((f"{mean:.{digits}f}", f"{sd2:.{digits}f}"), ("69.3", "3.1"))
        self.assertIsNone(occl_stats([None, None, None]))
        self.assertEqual(occl_stats([5, None, None])[1], 0.0)

    def test_time_format(self):
        self.assertEqual(layout.mmss(840), "14:00.00")
        self.assertEqual(layout.mmss(14.2), "00:14.20")
        self.assertEqual(layout.mmss(4500.456), "75:00.46")
        self.assertEqual(layout.mmss(59.999), "01:00.00")
        self.assertEqual(layout.mmss(None), "—")
        self.assertEqual(layout.ml(1.23456), "1.235 ml")

    def test_report_uses_new_formats(self):
        job = demo.jobs()[2]                                  # Calibration infusion 3 rate
        page = layout.Doc(job, "th").calibration_summary(2, 3)
        self.assertIn("Error%", page)
        self.assertNotIn("คลาดเคลื่อน", page)
        r = job.rates[0]
        self.assertIn(f"{abs(r.error):.2f}", page)            # ทศนิยม 2 ตำแหน่ง
        self.assertIn(layout.mmss(r.minutes * 60), page)
        self.assertIn("เฉลี่ย ± 2SD", page)
        self.assertIn("69.3 ± 3.1", page)
        rows = dict(layout.Doc(job, "th").detail_rows(r))
        self.assertRegex(rows["ปริมาตรรวม"], r"^\d+\.\d{3} ml$")
        self.assertRegex(rows["เวลารวม"], r"^\d{2}:\d{2}\.\d{2}$")

    def test_service_type_is_automatic(self):
        jobs = demo.jobs()
        cal = jobs[2]
        self.assertEqual(cal.service_types(), {"calib", "repair"} if cal.job.get("parts_replaced") else {"calib"})
        cal.job["parts_replaced"] = []
        self.assertEqual(cal.service_types(), {"calib"})
        insp = jobs[0]
        insp.job["parts_replaced"] = ["ฟิวส์"]
        self.assertEqual(insp.service_types(), {"pm", "repair"})
        insp.job["parts_replaced"] = []
        self.assertEqual(insp.service_types(), {"pm"})
        self.assertNotIn(("Service type", {}), insp.missing())

    def test_occlusion_entered_for_inspection_sets_the_item(self):
        insp = demo.jobs()[0]
        insp.info.occl_runs, insp.info.occl_low, insp.info.occl_high = [30, 31, 29], 40, 100
        self.assertEqual(insp.check_status("performance.occlusion"), "fail")
        self.assertFalse(insp.overall_pass())
        self.assertIn("30.0 ± 2.0 kPa", layout.Doc(insp, "th").inspection_page(1, 2))

    def test_font_is_sarabun(self):
        css = style.stylesheet()
        self.assertIn("font-family: 'Sarabun'", css)          # ผู้ใช้ขอกลับมาใช้ฟอนต์/สีแบบเดิม
        self.assertNotIn("Plex", css)


class PlanPerRateMethodTest(unittest.TestCase):
    def test_step_strategy_overrides_plan(self):
        plan = TestPlan(job=JobInfo(), run_mode=RunMode.CALIBRATION, strategy="pump_cycle", end_mode=EndMode.COUNT,
                        steps=[StepConfig(target_flow=10, strategy="time_interval"), StepConfig(target_flow=50)])
        self.assertTrue(plan.mixed)
        self.assertEqual(plan.strategies(), ["time_interval", "pump_cycle"])
        first, second = plan.session_config(0), plan.session_config(1)
        self.assertEqual((first.strategy, first.end_mode), ("time_interval", EndMode.TIME))   # นับรอบไม่ได้ -> ตามเวลา
        self.assertEqual((second.strategy, second.end_mode), ("pump_cycle", EndMode.COUNT))
        self.assertTrue(plan.uses_cycles())
        self.assertFalse(plan.uses_cycles(0))

    def test_old_plans_without_step_strategy(self):
        plan = TestPlan(strategy="time_interval", steps=[StepConfig(), StepConfig()])
        self.assertFalse(plan.mixed)
        self.assertEqual(plan.session_config(1).strategy, "time_interval")


class WizardInputsTest(_TmpRepo):
    def _wizard(self):
        from ui.dialogs.test_wizard import TestWizard
        return TestWizard(None, self.repo, self.settings)

    def test_extras_default_and_job_report(self):
        wizard = self._wizard()
        report = wizard._read_job().report
        self.assertTrue(report["whole_checked"] and report["label_attached"])     # ตั้งต้นติ๊ก
        wizard._extras.occl_runs[0].setValue(0.7)
        wizard._extras.leak.setValue(40)
        report = wizard._read_job().report
        self.assertEqual(report["occl_runs"], [0.7, None, None])
        self.assertEqual(report["leak_ua"], 40)
        self.assertFalse(hasattr(wizard, "_service"))          # ประเภทงานไม่ต้องเลือกแล้ว
        wizard.close()

    def test_per_rate_method_in_plan(self):
        from ui.dialogs.test_wizard import PAGE_SETTINGS
        wizard = self._wizard()
        wizard._mode = RunMode.CALIBRATION
        wizard._apply_mode_defaults()
        wizard._strategy.setCurrentIndex(wizard._strategy.findData("pump_cycle"))
        wizard._apply_strategy_to_rows()
        self.assertEqual({row["method"].currentData() for row in wizard._rows}, {"pump_cycle"})
        first = wizard._rows[0]["method"]
        first.setCurrentIndex(first.findData("time_interval"))
        self.assertTrue(wizard._rows[0]["window"].isEnabled())        # ความยาวช่วงของแบ่งช่วงเวลา
        self.assertFalse(wizard._rows[0]["info"].isVisibleTo(wizard))   # ไม่มีหน้าต่าง peak
        checked = []
        wizard._check_calibration = lambda steps, source: (checked.extend(steps), ("pump_cycle", source, steps))[1]
        wizard._remember_checklists = lambda: None
        wizard._pages.setCurrentIndex(PAGE_SETTINGS)
        wizard._on_next()
        plan = wizard.plan
        self.assertTrue(plan.mixed)
        self.assertEqual(plan.strategies()[0], "time_interval")
        self.assertEqual(set(plan.strategies()[1:]), {"pump_cycle"})
        self.assertEqual(len(checked), len(plan.steps) - 1)          # ตรวจสอบเทียบเฉพาะ rate ที่จับรอบปั๊ม
        wizard.close()

    def test_wizard_values_reach_the_job_record(self):
        from datetime import datetime
        from core.models import SessionConfig, SessionSummary
        from services.report import service
        job = JobInfo(brand="Terumo", model="TE-171", serial_no="X1",
                      report=dict(occl_level="M", occl_unit="kPa", occl_runs=[68, 71, 69], occl_low=40, occl_high=100,
                                  supply_v=224, leak_ua=38, whole_checked=True, label_attached=True))
        config = SessionConfig(job=job, job_id="J-NEW", run_mode=RunMode.INSPECTION)
        folder = self.tmp / "sessions" / "new"
        folder.mkdir(parents=True, exist_ok=True)
        self.repo.save(SessionSummary(config=config, started_at=datetime.now().isoformat(timespec="seconds")), [], folder)
        stored, report = self.repo.job_record("J-NEW")
        self.assertNotIn("report", stored)                    # ค่าของใบอยู่ใน report_json ไม่ซ้ำใน job_json
        self.assertEqual(report["occl_runs"], [68, 71, 69])
        self.assertEqual(self.repo.last_model_report("terumo", "te-171")["occl_high"], 100)
        info = service.job_for_plan(self.repo, "J-NEW", self.settings).info
        self.assertTrue(info.whole_checked)
        self.assertEqual(info.leak_ua, 38)


if __name__ == "__main__":
    unittest.main()
