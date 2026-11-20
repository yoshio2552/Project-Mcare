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
        # รูปแบบใหม่ (ผู้ใช้ 2026-11-20): หน่วยกำกับชัด ไม่สับสน ชม:นาที กับ นาที:วินาที
        self.assertEqual(layout.duration(840), "14 min 0.00 s")
        self.assertEqual(layout.duration(14.2), "14.20 s")
        self.assertEqual(layout.duration(4500.456), "1 h 15 min 0.46 s")
        self.assertEqual(layout.duration(59.999), "1 min 0.00 s")
        self.assertEqual(layout.duration(None), "—")
        self.assertEqual(layout.seconds(72.7), "72.70 s")

    def test_report_uses_new_formats(self):
        job = demo.jobs()[2]                                  # Calibration infusion 3 rate
        page = layout.Doc(job, "th").calibration_summary(2, 3)
        self.assertIn("Error%", page)
        self.assertNotIn("คลาดเคลื่อน", page)
        r = job.rates[0]
        self.assertIn(f"{abs(r.error):.2f}", page)            # ทศนิยม 2 ตำแหน่ง
        self.assertIn(layout.duration(r.minutes * 60), page)      # "14 min 0.00 s" (2026-11-20 แทน 14:00.00)
        self.assertNotIn("นาที:วินาที", page)
        self.assertIn("เฉลี่ย ± 2SD", page)
        self.assertIn("69.3 ± 3.1", page)
        rows = dict(layout.Doc(job, "th").detail_rows(r))
        self.assertRegex(rows["ปริมาตรรวม"], r"^\d+\.\d{3} ml$")
        self.assertRegex(rows["เวลาที่วัด"], r'^(\d+ h )?(\d+ min )?\d+\.\d{2} s( <i class="setv">· ตั้ง [\d.]+ (นาที|รอบ)</i>)?$')
        self.assertRegex(rows["เวลาต่อช่วงเฉลี่ย" if r.method != "cycle" else "เวลาต่อรอบเฉลี่ย"], r"^\d+\.\d{2}( ± \d+\.\d{2})? s$")

    def test_service_type_is_automatic(self):
        # ผู้ใช้ 2026-11-20: บำรุงรักษาเสมอ (รวม Calibration) · Calibration -> สอบเทียบ ด้วย · อะไหล่ -> ซ่อม ด้วย
        jobs = demo.jobs()
        cal = jobs[2]
        expected = {"pm", "calib", "repair"} if cal.job.get("parts_replaced") else {"pm", "calib"}
        self.assertEqual(cal.service_types(), expected)
        cal.job["parts_replaced"] = []
        self.assertEqual(cal.service_types(), {"pm", "calib"})
        insp = jobs[0]
        insp.job["parts_replaced"] = ["ฟิวส์"]
        self.assertEqual(insp.service_types(), {"pm", "repair"})
        insp.job["parts_replaced"] = []
        self.assertEqual(insp.service_types(), {"pm"})
        self.assertNotIn(("Service type", {}), insp.missing())
        insp.job["service_kinds"] = ["repair"]              # ติ๊กเองใน wizard ขั้น 4 -> ใช้ตามที่ติ๊ก
        self.assertEqual(insp.service_types(), {"repair"})
        insp.job["service_kinds"] = ["bogus"]               # ค่าแปลก -> กลับไปคิดเอง
        self.assertEqual(insp.service_types(), {"pm"})

    def test_occlusion_entered_for_inspection_sets_the_item(self):
        insp = demo.jobs()[0]
        insp.info.occl_runs, insp.info.occl_low, insp.info.occl_high = [30, 31, 29], 40, 100
        self.assertEqual(insp.check_status("performance.occlusion"), "fail")
        self.assertFalse(insp.overall_pass())
        self.assertNotIn("30.0 ± 2.0 kPa", layout.Doc(insp, "th").inspection_page(1, 2))   # ไม่ใส่ค่าที่วัดในใบ Inspection

    def test_fonts_of_the_sample(self):
        css = style.stylesheet()                            # ใบตัวอย่างของผู้ใช้ 2026-11-19: Plex Sans Thai + Plex Mono
        self.assertIn("font-family: 'IBM Plex Sans Thai'", css)
        self.assertIn("font-family: 'IBM Plex Mono'", css)
        self.assertNotIn("Looped", css)                     # ตัวที่ผู้ใช้ไม่เอา (2026-11-18)

    def test_inspection_page_one_like_the_sample(self):
        insp = demo.jobs()[0]
        page = layout.Doc(insp, "th").inspection_page(1, 2)
        for text in ('<span class="no">01</span>', '<span class="no">06</span>', "ตรวจขั้นสุดท้าย", "FINAL INSPECTION",
                     "DEVICE INSPECTED", "เครื่องให้สารละลาย", 'class="vfig"', "Error% +0.84 · ดูหน้า 2",
                     "ใช้งานได้มากกว่า 120 นาที", "DeltaM 0.3.0"):
            self.assertIn(text, page, text)
        self.assertNotIn("จัดทำโดย", page)                   # ผู้ใช้ 2026-11-20: เอาคำนี้ออกจากท้ายกระดาษ
        self.assertNotIn("ข้อมูลดิบ", page)
        self.assertNotIn("<svg", page)                      # ไม่มีแถบมาตรวัดหน้า 1 แล้ว
        self.assertNotIn("วันที่ ....", page)               # ลายเซ็นไม่มีวันที่
        self.assertNotIn("69.3 ± 3.1", page)               # Inspection: การอุดตันไม่ใส่ค่าที่วัด
        self.assertIn("เตือนเมื่อมีการอุดตัน", page)         # ผู้ใช้ 2026-11-19 (เดิม "ทำงานปกติ")
        # กล่องผล: คำไม่ซ้ำ — แถว rate "อยู่ในเกณฑ์" · ขวา "สรุปผล" + ผ่าน
        self.assertIn('class="pass">อยู่ในเกณฑ์', page)
        self.assertIn('<span class="vl">สรุปผล</span>', page)
        cal_page = layout.Doc(demo.jobs()[2], "th").inspection_page(1, 3, cal=True)
        self.assertNotIn('class="vfig"', cal_page)          # Calibration: ตารางผลอยู่หน้า 2 แทน
        self.assertIn("10 · 50 · 200 ml/h · ดูหน้า 2", cal_page)
        self.assertNotIn("Error% สูงสุด", cal_page)
        self.assertIn("วัด 3 ครั้ง เฉลี่ย 69.3 ± 3.1 kPa", cal_page)
        self.assertIn("INSPECTION REPORT", cal_page)

    def test_measurement_page_shows_iv_set_volume_and_standard(self):
        insp = demo.jobs()[0]
        doc = layout.Doc(insp, "th")
        page = doc.measurement_page(insp.rates[0], 2, 2)
        self.assertIn("ชุดให้สารละลาย", page)
        self.assertIn(doc.consumable(), page)
        self.assertNotIn("สัญญาณเตือนการอุดตัน", page)      # Inspection ไม่ได้วัดการอุดตันในหน้านี้ (ผู้ใช้ 2026-11-19)
        self.assertIn("การคิดปริมาตรจากน้ำหนัก", page)
        self.assertIn("เครื่องมือมาตรฐานและสภาวะขณะวัด", page)
        later = doc.measurement_page(insp.rates[0], 3, 3, first=False)
        self.assertNotIn("การคิดปริมาตรจากน้ำหนัก", later)  # หลาย rate: 04–05 เฉพาะหน้าผลวัดแรก

    def test_slim_gauge_keeps_colours(self):
        from services.report.charts import PUMP, gauge
        svg = gauge("infusion", -0.2, 0.6, 5, 330, slim=True)
        self.assertIn(PUMP["infusion"]["tint"], svg)           # พื้นแถบเกณฑ์
        self.assertIn('fill-opacity="0.35"', svg)              # แถบ ± U
        self.assertNotIn("<text x", svg.split("%")[0][:0] + "")   # (ป้ายมีแค่ −5/0/+5)
        self.assertNotIn("−0.20", svg)

    def test_flow_line_is_black(self):
        from services.report.charts import INK, flow_chart
        from services.report.text import Words
        series = [(i * 0.25, (i + 1) * 0.25, 50 + (i % 3)) for i in range(20)]
        svg = flow_chart(Words("th"), "infusion", series, 50, 51, 5, 698, 236)
        self.assertIn(f'stroke="{INK}" stroke-width="1.2"', svg)
        self.assertIn("ช่วงเกณฑ์ยอมรับ", svg)
        self.assertIn("เวลา (นาที)", svg)                       # ชื่อแกนกลางแกนใต้ป้าย (2026-11-20)


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

    def test_six_steps_mode_before_checklist(self):
        # ผู้ใช้ 2026-11-19: เลือกโหมด (ขั้น 3) ก่อนกรอกผลตรวจ (ขั้น 4) · 2026-11-20: ค่าที่วัดแยกเป็นขั้น 5 ตั้งค่า = ขั้น 6
        from ui.dialogs.test_wizard import PAGE_CHECK, PAGE_MODE, PAGE_REPORT, PAGE_SETTINGS, PAGE_VALUES, TestWizard
        wizard = TestWizard(None, self.repo, self.settings)
        self.assertEqual(wizard._pages.count(), 6)
        self.assertEqual((PAGE_CHECK, PAGE_MODE, PAGE_REPORT, PAGE_VALUES, PAGE_SETTINGS), (1, 2, 3, 4, 5))
        report_page = wizard._pages.widget(PAGE_REPORT).widget()
        self.assertTrue(report_page.isAncestorOf(wizard._checks))
        self.assertFalse(report_page.isAncestorOf(wizard._extras))
        self.assertTrue(wizard._pages.widget(PAGE_VALUES).widget().isAncestorOf(wizard._extras))
        self.assertFalse(wizard._pages.widget(PAGE_CHECK).widget().isAncestorOf(wizard._checks))
        wizard._go(PAGE_MODE)
        self.assertIn("3", wizard._title.text())
        self.assertIn("6", wizard._title.text())
        wizard._choose_mode(RunMode.CALIBRATION)               # กดการ์ดโหมด -> ไปขั้นผลตรวจ (ไม่ข้ามไปตั้งค่า)
        self.assertEqual(wizard._pages.currentIndex(), PAGE_REPORT)
        self.assertIn("4", wizard._title.text())
        wizard._on_next()
        self.assertEqual(wizard._pages.currentIndex(), PAGE_VALUES)
        self.assertIn("5", wizard._title.text())
        wizard._on_next()
        self.assertEqual(wizard._pages.currentIndex(), PAGE_SETTINGS)
        wizard.close()

    def test_service_type_ticks_in_step_four(self):
        # ผู้ใช้ 2026-11-20: ติ๊กประเภทงานแก้ได้ในขั้น 4 · ตั้งต้นตามโหมด + อะไหล่ (บำรุงรักษาเสมอ)
        from ui.dialogs.test_wizard import PAGE_REPORT, TestWizard
        wizard = TestWizard(None, self.repo, self.settings)
        wizard._choose_mode(RunMode.CALIBRATION)
        self.assertEqual(set(wizard._service_values()), {"pm", "calib"})
        self.assertEqual(wizard._read_job().service_kinds, [])          # ตรงกับที่คิดเอง -> ไม่เก็บ
        wizard._service_boxes["pm"].setChecked(False)
        self.assertEqual(wizard._read_job().service_kinds, ["calib"])   # แก้เอง -> เก็บ
        wizard._go(PAGE_REPORT - 1)
        wizard._choose_mode(RunMode.INSPECTION)                          # เปลี่ยนโหมด -> ไม่ทับที่ติ๊กเอง
        self.assertEqual(wizard._service_values(), ["calib"])
        wizard._apply_auto_service(force=True)                           # ปุ่ม "ตั้งให้อัตโนมัติ"
        self.assertEqual(wizard._service_values(), ["pm"])
        self.assertEqual(wizard._read_job().service_kinds, [])
        wizard.close()

    def test_occlusion_only_for_calibration(self):
        from ui.dialogs.test_wizard import PAGE_REPORT, TestWizard
        wizard = TestWizard(None, self.repo, self.settings)
        wizard.show()
        extras = wizard._extras
        extras.occl_runs[0].setValue(0.8)
        wizard._choose_mode(RunMode.INSPECTION)
        self.assertEqual(wizard._pages.currentIndex(), PAGE_REPORT)
        wizard._on_next()                                       # ขั้น 5 ค่าที่วัด (2026-11-20)
        self.assertEqual(wizard._pages.currentIndex(), PAGE_REPORT + 1)
        self.assertFalse(extras.occl_runs[0].isVisible())
        self.assertFalse(extras.occl_result.isVisible())
        self.assertEqual(wizard._read_job().report["occl_runs"], [None, None, None])   # ใบ Inspection ไม่ใส่ค่าที่วัด
        self.assertTrue(extras.supply.isVisible())                                   # ส่วนอื่นเหมือนเดิม
        wizard._go(PAGE_REPORT - 1)
        wizard._choose_mode(RunMode.CALIBRATION)
        wizard._on_next()
        self.assertTrue(extras.occl_runs[0].isVisible())
        self.assertEqual(wizard._read_job().report["occl_runs"], [0.8, None, None])
        wizard.close()

    def test_occlusion_zero_is_blank_and_wheel_needs_focus(self):
        # ภาพผู้ใช้: ครั้งที่ 1 เป็น 0.00 (ล้อเมาส์ตอนเลื่อนหน้า) แล้วผลขึ้น "ไม่ผ่าน"
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication
        from ui.widgets.report_extras import ReportExtras
        extras = ReportExtras()
        extras.occl_low.setValue(0.5)
        extras.occl_high.setValue(1.3)
        extras.occl_runs[0].setValue(0.0)
        self.assertEqual(extras.occl_result.text(), "")
        self.assertEqual(extras.values()["occl_runs"], [None, None, None])
        extras.occl_runs[0].setValue(0.9)
        self.assertIn("1", extras.occl_result.text())                # วัดแล้ว 1 จาก 3 ครั้ง
        box = extras.occl_runs[1]
        before = box.value()
        event = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, 120), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(box, event)
        self.assertEqual(box.value(), before)                         # ไม่ได้คลิกเข้าช่อง = ล้อไม่เปลี่ยนค่า

    def test_step_three_defaults_from_settings(self):
        from ui.dialogs.test_wizard import TestWizard
        r = self.settings.report
        r.default_occl_inf_level, r.default_occl_inf_unit, r.default_occl_inf_low, r.default_occl_inf_high = "M", "kPa", 0.5, 1.3
        r.default_occl_syr_level, r.default_occl_syr_unit, r.default_occl_syr_low, r.default_occl_syr_high = "L", "kgf/cm²", 0.3, 0.9
        r.default_supply_v, r.default_final_ticks, r.default_battery_min = 220, False, 45
        wizard = TestWizard(None, self.repo, self.settings)
        values = wizard._read_job().report
        self.assertEqual((values["occl_level"], values["occl_low"], values["occl_high"]), ("M", 0.5, 1.3))
        self.assertEqual((values["supply_v"], values["battery_min"]), (220, 45))
        # เปลี่ยนเป็น Syringe -> ค่าตั้งต้นของ Syringe (แยกชนิด — ผู้ใช้ 2026-11-20) · กลับ Infusion -> ค่าเดิม
        wizard._pump_type.setCurrentIndex(wizard._pump_type.findData("syringe"))
        values = wizard._read_job().report
        self.assertEqual((values["occl_level"], values["occl_unit"], values["occl_low"]), ("L", "kgf/cm²", 0.3))
        wizard._pump_type.setCurrentIndex(wizard._pump_type.findData("infusion"))
        self.assertEqual(wizard._read_job().report["occl_level"], "M")
        self.assertFalse(values["whole_checked"])
        self.assertEqual(values["occl_runs"], [None, None, None])     # ค่าที่วัดจริงไม่มีค่าตั้งต้น
        self.assertIsNone(values["leak_ua"])
        # เกณฑ์ที่เคยบันทึกของรุ่นเดียวกันทับค่าตั้งต้น (ยังไม่ได้แก้เอง)
        wizard._extras.set_limits({"occl_level": "H", "occl_unit": "mmHg", "occl_low": 300, "occl_high": 900},
                                  wizard._extras_defaults)
        values = wizard._read_job().report
        self.assertEqual((values["occl_level"], values["occl_unit"], values["occl_low"]), ("H", "mmHg", 300))
        wizard.close()

    def test_step_five_fits_a_normal_window(self):
        from ui.dialogs.test_wizard import PAGE_SETTINGS, TestWizard
        wizard = TestWizard(None, self.repo, self.settings)
        wizard._mode = RunMode.CALIBRATION
        wizard._apply_mode_defaults()
        wizard._go(PAGE_SETTINGS)
        self.assertLess(wizard._pages.widget(PAGE_SETTINGS).widget().minimumSizeHint().width(), 900)
        wizard.close()

    def test_extras_default_and_job_report(self):
        wizard = self._wizard()
        report = wizard._read_job().report
        self.assertTrue(report["whole_checked"] and report["label_attached"])     # ตั้งต้นติ๊ก
        wizard._extras.occl_runs[0].setValue(0.7)
        wizard._extras.leak.setValue(40)
        report = wizard._read_job().report
        self.assertEqual(report["occl_runs"], [0.7, None, None])
        self.assertEqual(report["leak_ua"], 40)
        self.assertFalse(hasattr(wizard, "_service"))          # ไม่มีช่องเลือกแบบเดิม (ใช้ติ๊ก _service_boxes ในขั้น 4)
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
