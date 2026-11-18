"""ทดสอบใบรายงานฝั่งหน้าจอแบบ offscreen: ฐานข้อมูล v6 (job_reports), ข้อมูลใบรายงาน, หน้าต่างตัวอย่าง (QPdfView),
บันทึก PDF / พิมพ์ (เครื่องพิมพ์ = ไฟล์ PDF), หน้าประวัติติ๊กเลือก, exporter "pdf",
และทั้งเส้นทางหลังทดสอบเสร็จ (ตราชั่งจำลอง 2 rate -> เก็บผล -> ถามออกใบ -> บันทึก PDF)

ใช้ Repository ชั่วคราวเท่านั้น (ไม่แตะ data/) · AppSettings.save ถูกปิด
รัน:  python -m unittest tests.test_report_ui -v
"""
import csv
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton

from config.settings import AppSettings
from services import session_store
from services.report import demo, layout, service

app = QApplication.instance() or QApplication([])


def no_settings_save(test: unittest.TestCase) -> None:
    """ห้ามทับ data/settings.json ระหว่างเทสต์ — ปิดเฉพาะในเทสต์นี้ (ปิดทั้งโมดูลจะทำให้เทสต์ roundtrip ของไฟล์อื่นพัง)"""
    original = AppSettings.save
    AppSettings.save = lambda self, path=None: None
    test.addCleanup(setattr, AppSettings, "save", original)


def store_demo(repo, root: Path) -> dict[str, str]:
    """เขียนผลตัวอย่าง (services/report/demo) ลงฐานข้อมูลชั่วคราว — คืน ref เดิม -> id ในฐานข้อมูล"""
    sessions, intervals = demo.sample_sessions()
    mapping = {}
    for session in sessions:
        folder = root / "sessions" / f"demo_{session['ref']}"
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / "intervals.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "chain", "t_s", "duration_s", "flow_ml_h", "error_pct", "flow_raw_ml_h",
                             "error_raw_pct", "volume_ml"])
            for iv in intervals[session["ref"]]:
                writer.writerow([iv["index"], "AB"[iv["chain"]], iv["t"], iv["duration_s"], iv["flow"], iv["error_pct"],
                                 iv["flow"], iv["error_pct"], iv["flow"] * iv["duration_s"] / 3600])
        config = session["config"]
        payload = {k: v for k, v in session.items() if k != "ref"}
        cursor = repo._db.execute(
            "INSERT INTO sessions (started_at, mode, job_id, step_index, step_count, pump_type, target_flow, verdict,"
            " end_reason, folder, summary_json, job_no) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (session["started_at"], config["run_mode"], config["job_id"], config["step_index"], config["step_count"],
             config["job"]["pump_type"], config["target_flow"], session["verdict"], session["end_reason"], str(folder),
             json.dumps(payload, ensure_ascii=False), config["job"]["job_no"]))
        mapping[session["ref"]] = str(cursor.lastrowid)
    repo._db.commit()
    return mapping


def wait_until(condition, timeout=30.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.02)
    return False


def click_later(text: str, delay=150, timeout=30.0):
    """รอจนหน้าต่าง modal ที่มีปุ่มข้อความนี้เปิดขึ้น แล้วกด (ข้ามหน้าต่างอื่น เช่น แถบความคืบหน้า)"""
    deadline = time.time() + timeout

    def press():
        widget = QApplication.activeModalWidget()
        if widget is not None:
            for button in widget.findChildren(QPushButton):
                if button.text().replace("&", "") == text and button.isVisible():
                    button.click()
                    return
        if time.time() < deadline:
            QTimer.singleShot(50, press)
    QTimer.singleShot(delay, press)


class _TmpRepo(unittest.TestCase):
    def setUp(self):
        no_settings_save(self)
        self.tmp = Path(tempfile.mkdtemp(prefix="deltam-report-ui-"))
        self.repo = session_store.Repository(self.tmp / "t.db", self.tmp / "sessions")
        self._previous = session_store._repository          # ห้ามเรียก get_repository() — จะเปิด data/ จริง
        session_store.set_repository(self.repo)
        self.refs = store_demo(self.repo, self.tmp)
        self.settings = AppSettings()
        self.settings.report.folder = str(self.tmp / "out")
        self.settings.report.language = "th"

    def tearDown(self):
        session_store.set_repository(self._previous)
        self.repo._db.close()
        shutil.rmtree(self.tmp, ignore_errors=True)


class RepositoryTest(_TmpRepo):
    def test_v6_job_reports_and_report_reads(self):
        self.assertEqual(self.repo._db.execute("PRAGMA user_version").fetchone()[0], 6)
        self.assertEqual(len(self.repo.job_sessions("J-CAL-INF")), 3)
        self.assertEqual(len(self.repo.intervals(self.refs["4"])), 58)
        self.assertIsNone(self.repo.report_info("J-CAL-INF"))
        self.repo.set_report_info("J-CAL-INF", {"leak_ua": 42})
        self.assertEqual(self.repo.report_info("J-CAL-INF"), {"leak_ua": 42})

    def test_jobs_for_expands_one_rate_to_whole_job(self):
        one = [s for s in self.repo.list() if s["ref"] == self.refs["4"]]       # ติ๊ก 50 ml/h อย่างเดียว
        jobs = service.jobs_for(self.repo, one, self.settings)
        self.assertEqual(len(jobs), 1)
        self.assertEqual([r.set_rate for r in jobs[0].rates], [10.0, 50.0, 200.0])
        self.assertEqual(jobs[0].options.balance_serial, self.settings.balance.serial_no)


class ReportInfoDialogTest(_TmpRepo):
    def test_edit_and_save(self):
        from ui.dialogs.report_info import ReportInfoDialog
        job = service.job_for_plan(self.repo, "J-CAL-SYR", self.settings)
        dialog = ReportInfoDialog(None, job)
        dialog.leak.setValue(350)
        dialog.occl_runs[0].setValue(55)
        dialog.checks.clear()
        dialog.checks.pass_all()
        info = dialog.result_info()
        self.assertEqual(info.leak_ua, 350)
        self.assertEqual(info.occl_runs[0], 55)
        self.assertEqual(len(info.checks), 17)                # syringe 8 + 6 + 3 ข้อ
        service.save_info(self.repo, job, info)
        again = service.job_for_plan(self.repo, "J-CAL-SYR", self.settings)
        self.assertEqual(again.info.leak_ua, 350)
        self.assertFalse(again.overall_pass())               # กระแสรั่วเกิน 300 µA
        dialog.close()


class PreviewAndOutputTest(_TmpRepo):
    def _actions(self):
        from ui.dialogs.report_preview import ReportActions
        return ReportActions(None, self.settings, self.repo)

    def test_preview_renders_switches_language_and_saves(self):
        from ui.dialogs.report_preview import ReportPreviewDialog
        jobs = service.jobs_for(self.repo, self.repo.list(), self.settings)
        actions = self._actions()
        dialog = ReportPreviewDialog(None, jobs, "th", actions)
        dialog.show()
        self.assertTrue(wait_until(lambda: dialog.data is not None))
        total = sum(layout.page_count(j) for j in jobs)
        self.assertEqual(dialog.document.pageCount(), total)
        first = dialog.data
        dialog.lang_box.setCurrentIndex(dialog.lang_box.findData("en"))
        self.assertTrue(wait_until(lambda: dialog.data is not None and dialog.data != first))
        dialog.job_box.setCurrentIndex(2)                    # กระโดดไปงานที่ 3 ไม่ล้ม
        self.settings.report.merge_files = True
        target = self.tmp / "out" / "combined.pdf"
        from PySide6.QtWidgets import QFileDialog
        original = QFileDialog.getSaveFileName
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(target), "PDF (*.pdf)"))
        try:
            click_later("OK")                                # กล่อง "บันทึกแล้ว"
            dialog._save()
        finally:
            QFileDialog.getSaveFileName = original
        self.assertTrue(target.read_bytes().startswith(b"%PDF"))
        dialog.close()

    def test_save_without_preview_one_file_per_job_and_replace_prompt(self):
        jobs = service.jobs_for(self.repo, self.repo.list(), self.settings)
        actions = self._actions()
        click_later("OK")
        self.assertTrue(actions.save(jobs, "th", ask_location=False))
        names = sorted(p.name for p in (self.tmp / "out").iterdir())
        self.assertEqual(names, ["MCI-0142_Calibration_TH.pdf", "MCI-0142_Inspection_TH.pdf",
                                 "MCS-0388_Calibration_TH.pdf", "MCS-0388_Inspection_TH.pdf"])
        click_later("Keep both")                             # มีไฟล์ชื่อเดิมแล้ว -> เก็บทั้งคู่
        QTimer.singleShot(2500, lambda: click_later("OK", 0))
        self.assertTrue(actions.save(jobs[:1], "th", ask_location=False))
        stem = Path(jobs[0].file_name("th")).stem
        self.assertTrue((self.tmp / "out" / f"{stem} (2).pdf").is_file())

    def test_print_in_background_to_pdf_printer(self):
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtPrintSupport import QPrinter
        from services.report import printing
        out = self.tmp / "printed.pdf"

        def fake_printer(parent, ask, pages=0, title=""):
            printer = printing.new_printer()
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(str(out))
            return printer
        original = printing.printer_for
        printing.printer_for = fake_printer
        try:
            job = service.job_for_plan(self.repo, "J-CAL-INF", self.settings)
            actions = self._actions()
            self.assertTrue(actions.print([job], "th"))
            self.assertTrue(wait_until(lambda: not actions._print_jobs, 60))
        finally:
            printing.printer_for = original
        doc = QPdfDocument()
        doc.load(str(out))
        self.assertEqual(doc.pageCount(), 3)

    def test_pdf_exporter_registered(self):
        from services.exporters import EXPORTERS
        self.assertIn("pdf", [key for key, _ in EXPORTERS.choices()])
        target = self.tmp / "export.pdf"
        EXPORTERS.get("pdf")(self.repo, self.settings, "en").export(self.repo.list(), target)
        self.assertTrue(target.read_bytes().startswith(b"%PDF"))


class HistoryTickTest(_TmpRepo):
    def test_tick_one_rate_ticks_the_job_and_saves(self):
        from PySide6.QtCore import Qt
        from ui.pages.history import HistoryPage
        page = HistoryPage(self.settings)
        refs = [s["ref"] for s in page._visible]
        row = refs.index(self.refs["4"])                     # 50 ml/h ของ Calibration infusion
        page.table.item(row, 0).setCheckState(Qt.CheckState.Checked)
        self.assertEqual(sorted(s["ref"] for s in page.checked_sessions()),
                         sorted(self.refs[k] for k in ("3", "4", "5")))
        self.assertTrue(page.btn_pdf.isEnabled())
        page.search.setText("MCS")                           # กรองแล้วรายการที่ติ๊กยังอยู่
        self.assertEqual(len(page.checked_sessions()), 3)
        page.search.setText("")
        page.select_all.click()
        self.assertEqual(len(page.checked_sessions()), 8)
        self.settings.report.preview_from_history = False
        click_later("Make the report anyway", 150)           # มีคำเตือนข้อมูลที่ยังไม่กรอก (ไฟฟ้า/การอุดตัน)
        QTimer.singleShot(3000, lambda: click_later("OK", 0))
        page._make_report("save")
        self.assertEqual(len(list((self.tmp / "out").glob("*.pdf"))), 4)
        page.close()


class AfterTestFlowTest(unittest.TestCase):
    """ทั้งเส้นทาง: แผน Calibration 2 rate กับตราชั่งจำลอง -> เก็บผลทุกขั้น -> ถามออกใบ -> บันทึก PDF (ไม่ดูตัวอย่าง)"""

    def test_calibration_run_then_save_report(self):
        from core.models import JobInfo, PumpType, RunMode, StepConfig, TestPlan
        from services.session_controller import SessionController
        from ui.dialogs.report_preview import offer_after_test
        no_settings_save(self)
        tmp = Path(tempfile.mkdtemp(prefix="deltam-report-run-"))
        repo = session_store.Repository(tmp / "t.db", tmp / "sessions")
        previous = session_store._repository
        session_store.set_repository(repo)
        try:
            settings = AppSettings()
            settings.source = "simulator"
            settings.simulator.speed = 300
            settings.report.folder = str(tmp / "out")
            settings.report.preview_after_test = False
            controller = SessionController(settings)
            controller.ask_profile_decision = lambda check: "skip"
            controller.review_requested.connect(lambda summary: QTimer.singleShot(0, controller.keep_result))
            finished = []
            controller.session_finished.connect(lambda summary, kept: finished.append(summary))
            job = JobInfo(pump_type=PumpType.SYRINGE, job_no="MCS-9001", site="รพ.ทดสอบ", brand="Terumo", model="TE-331",
                          serial_no="S1", operator="ผู้ทดสอบ")
            plan = TestPlan(job=job, run_mode=RunMode.CALIBRATION, strategy="time_interval", tolerance_pct=10.0,
                            steps=[StepConfig(target_flow=5.0, duration_min=2.0, window_s=20.0),
                                   StepConfig(target_flow=20.0, duration_min=2.0, window_s=20.0)])
            controller.set_plan(plan)
            for step in range(2):
                self.assertTrue(controller.start_step())
                self.assertTrue(wait_until(lambda n=step + 1: len(finished) >= n, 120), "step did not finish")
            self.assertFalse(controller.has_next_step)
            job_id = controller.plan.job_id
            report = service.job_for_plan(repo, job_id, settings)
            self.assertEqual([r.set_rate for r in report.rates], [5.0, 20.0])
            self.assertEqual(report.pump, "syringe")
            click_later("Save PDF", 150)                       # คำถามหลังทดสอบ
            QTimer.singleShot(1500, lambda: click_later("Make the report anyway", 0))   # คำเตือนข้อมูลที่ยังไม่กรอก
            QTimer.singleShot(4000, lambda: click_later("OK", 0))                     # กล่อง "บันทึกแล้ว"
            parent = QDialog()
            self.assertEqual(offer_after_test(parent, settings, repo, job_id), "save")
            self.assertTrue((tmp / "out" / "MCS-9001_Calibration_TH.pdf").is_file()
                            or (tmp / "out" / "MCS-9001_Calibration_EN.pdf").is_file())
            controller.shutdown()
        finally:
            session_store.set_repository(previous)
            repo._db.close()
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
