"""ทดสอบรอบ 2026-11-20: ปรับแต่งใบรายงานในหน้าตั้งค่า — ท้ายกระดาษ, ผู้ลงนาม/ช่องลายเซ็น (ภาพ PNG), U เป็น ml/h,
± U ที่มาตรวัด/กราฟ, ±2SD ของอัตราการไหล/การอุดตัน, ชุดหน้าของใบ Calibration, หน้าตั้งค่าแบบแท็บ

รัน:  python -m unittest tests.test_report_options -v
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication

from config.settings import AppSettings, _merge
from services.report import demo, layout, signatures
from services.report.service import options_from_settings
from services.report.signatures import Person, SignSlot
from tests.test_report_ui import _TmpRepo

app = QApplication.instance() or QApplication([])


def _cal(**options):
    job = demo.jobs()[2]                    # Calibration infusion 3 rate (มีงบความไม่แน่นอน)
    for name, value in options.items():
        setattr(job.options, name, value)
    return job


def _signature_png(path: Path, white: bool = True) -> None:
    img = QImage(400, 140, QImage.Format.Format_ARGB32)
    img.fill(QColor("white") if white else QColor(0, 0, 0, 0))
    painter = QPainter(img)
    painter.setPen(QPen(QColor("#102060"), 6))
    painter.drawLine(30, 110, 150, 30)
    painter.drawLine(150, 30, 330, 100)
    painter.end()
    img.save(str(path))


class FooterAndPagesTest(unittest.TestCase):
    def test_footer_has_no_label_words_and_can_hide_parts(self):
        job = _cal()
        doc = layout.Doc(job, "th")
        foot = doc.footer(2, 4)
        self.assertNotIn("จัดทำโดย", foot)
        self.assertNotIn("ข้อมูลดิบ", foot)
        self.assertIn("DeltaM 0.3.0", foot)
        self.assertIn("ftrace", foot)
        self.assertNotIn("Produced with", layout.Doc(job, "en").footer(2, 4))
        job.options.footer_version = False
        job.options.footer_trace = False
        foot = layout.Doc(job, "th").footer(2, 4)
        self.assertNotIn("DeltaM", foot)
        self.assertNotIn("ftrace", foot)

    def test_supply_voltage_reference(self):
        # ผู้ใช้ 2026-11-20: อ้างอิงแรงดันไฟ AC Supply 200-230VAC ใต้ค่าแรงดันที่จ่าย · ตั้งได้ / ว่าง = ไม่แสดง
        job = demo.jobs()[0]
        self.assertIn("อ้างอิง AC Supply 200-230VAC", layout.Doc(job, "th").safety_row())
        self.assertIn("ref. AC Supply 200-230VAC", layout.Doc(job, "en").safety_row())
        job.options.supply_ref = ""
        self.assertNotIn("AC Supply", layout.Doc(job, "th").safety_row())
        s = AppSettings()
        s.report.supply_ref = "AC 220 V ± 10 %"
        self.assertEqual(options_from_settings(s).supply_ref, "AC 220 V ± 10 %")

    def test_calibration_page_sets(self):
        for pages_set, expected in (("all", 4), ("no_uncertainty", 3), ("certificate", 2)):
            job = _cal(cal_pages=pages_set)
            built = layout.pages(job, "th")
            self.assertEqual(len(built), expected, pages_set)
            self.assertEqual(layout.page_count(job), expected)
            self.assertIn(f"หน้า 2 / {expected}", built[1][1])           # เลขหน้ารวมตามชุดหน้า
        self.assertTrue(layout.pages(_cal(cal_pages="all"), "en")[-1][0].endswith("uncertainty"))
        self.assertFalse(any(name.endswith("uncertainty") for name, _ in layout.pages(_cal(cal_pages="no_uncertainty"), "en")))
        inspection = demo.jobs()[0]
        inspection.options.cal_pages = "certificate"                     # ไม่มีผลกับใบ Inspection
        self.assertEqual(len(layout.pages(inspection, "th")), layout.page_count(inspection))


class UncertaintyAndSpreadTest(unittest.TestCase):
    def test_u_column_ml_h_percent_or_hidden(self):
        job = _cal()
        r = job.rates[1]
        page = layout.Doc(job, "th").calibration_summary(2, 4)
        self.assertIn("<th>U<i>ml/h</i></th>", page)
        self.assertIn(f"±{r.summary['uncertainty']['U_ml_h']:.4f}", page)          # ทศนิยม 4 ตำแหน่ง
        self.assertIn("หน่วย ml/h", page)
        job.options.u_column = "pct"
        page = layout.Doc(job, "th").calibration_summary(2, 4)
        self.assertIn("<th>U<i>%</i></th>", page)
        self.assertIn(f"±{r.u:.3f}", page)
        job.options.u_column = "hide"
        page = layout.Doc(job, "th").calibration_summary(2, 4)
        self.assertNotIn("<th>U<i>", page)
        self.assertNotIn("ความไม่แน่นอนขยาย", page)

    def test_u_graphics_switch(self):
        job = _cal()
        on = layout.Doc(job, "th").rate_block(job.rates[1])
        self.assertIn("Error% ± U", on)
        job.options.cal_u = False
        off = layout.Doc(job, "th").rate_block(job.rates[1])
        self.assertNotIn("Error% ± U", off)
        self.assertNotIn('fill-opacity="0.35"', off)                    # แถบ ± U ของมาตรวัด
        tech = layout.Doc(job, "th").calibration_technical(job.rates, 3, 4)
        self.assertNotIn("ค่าที่วัดได้ ± U", tech)                          # คำอธิบายกราฟ Error% ไม่มี ± U
        self.assertNotIn("รวม U แล้ว", tech)
        insp = demo.jobs()[0]
        insp.rates[0].u = 1.0
        self.assertIn('fill-opacity="0.35"', layout.Doc(insp, "th").measurement_page(insp.rates[0], 2, 2))
        insp.options.insp_u = False
        self.assertNotIn('fill-opacity="0.35"', layout.Doc(insp, "th").measurement_page(insp.rates[0], 2, 2))

    def test_flow_and_occlusion_2sd_switches(self):
        job = _cal()
        doc = layout.Doc(job, "th")
        self.assertIn("<th>±2SD<i>%</i></th>", doc.calibration_summary(2, 4))
        self.assertIn("การกระจาย ±2SD", dict(doc.detail_rows(job.rates[0])))
        self.assertIn("69.3 ± 3.1", doc.occlusion_table())
        job.options.cal_flow_2sd = False
        job.options.cal_occl_2sd = False
        doc = layout.Doc(job, "th")
        self.assertNotIn("±2SD", doc.calibration_summary(2, 4))
        self.assertNotIn("การกระจาย ±2SD", dict(doc.detail_rows(job.rates[0])))
        table = doc.occlusion_table()
        self.assertNotIn("± 3.1", table)
        self.assertIn("<b>69.3</b>", table)
        self.assertIn("วัด 3 ครั้ง เฉลี่ย 69.3 kPa", doc.inspection_page(1, 4, cal=True))
        insp = demo.jobs()[0]
        insp.options.insp_flow_2sd = False                                # ใบ Inspection แยกค่าตั้ง
        self.assertNotIn("การกระจาย ±2SD", dict(layout.Doc(insp, "th").detail_rows(insp.rates[0])))
        self.assertIn("การกระจาย ±2SD", dict(layout.Doc(demo.jobs()[0], "th").detail_rows(insp.rates[0])))


class SignatureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="deltam-sign-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_default_boxes_inspection(self):
        page = layout.Doc(demo.jobs()[0], "en").inspection_page(1, 2)
        for text in ("Inspected by", "PM Engineer", "Approved by", "Engineering Manager"):
            self.assertIn(text, page)
        self.assertNotIn("Received by", page)
        th = layout.Doc(demo.jobs()[0], "th").inspection_page(1, 2)
        for text in ("ผู้ตรวจสอบ", "วิศวกรบำรุงรักษา", "ผู้อนุมัติ", "ผู้จัดการฝ่ายวิศวกรรม"):
            self.assertIn(text, th)

    def test_resolve_operator_person_and_blank(self):
        png = self.tmp / "s.png"
        _signature_png(png)
        people = [Person(id="a1", name_th="โยชิโอะ คาวาชิมะ", name_en="Yoshio Kawashima", aliases="Yoshio", image=str(png))]
        slot = SignSlot("ผู้ตรวจสอบ", "Inspected by", "", "", "operator")
        self.assertEqual(signatures.resolve(slot, people, " yoshio ", "en"), ("Yoshio Kawashima", str(png)))
        self.assertEqual(signatures.resolve(slot, people, "Yoshio", "th")[0], "โยชิโอะ คาวาชิมะ")
        self.assertEqual(signatures.resolve(slot, people, "Somchai", "en"), ("Somchai", ""))   # ไม่ตรง: ชื่อที่พิมพ์ ไม่มีภาพ
        self.assertEqual(signatures.resolve(slot, people, "Yosh", "en"), ("Yosh", ""))         # ไม่เดาชื่อบางส่วน
        slot.who = "person:a1"
        self.assertEqual(signatures.resolve(slot, people, "", "en")[0], "Yoshio Kawashima")
        slot.who = "person:gone"
        self.assertEqual(signatures.resolve(slot, people, "", "en"), ("", ""))
        job = demo.jobs()[0]
        job.job["operator"] = "Yoshio"
        job.options.people = people
        page = layout.Doc(job, "en").inspection_page(1, 2)
        self.assertIn("data:image/png;base64,", page)
        self.assertIn("Yoshio Kawashima", page)
        self.assertIn('class="sg4 img"', page)                            # มีภาพ = ไม่มีเส้นใต้
        job.options.sign_insp[1].show = False
        self.assertIn('class="signs4 n1"', layout.Doc(job, "en").inspection_page(1, 2))

    def test_legacy_settings_migrate(self):
        s = AppSettings()
        s.report.reviewer, s.report.approver = "Siwakorn A.", "Abdulroman."
        s.report.signers = ["สมชาย ตั้งใจ | วิศวกร | C:/sig.png"]
        self.assertTrue(signatures.migrate(s.report))
        people = signatures.people_from(s.report.people)
        self.assertEqual({p.label() for p in people}, {"Siwakorn A.", "Abdulroman.", "สมชาย ตั้งใจ"})
        cal = signatures.slots_from(s.report.sign_calibration, "calibration")
        by_id = {p.id: p for p in people}
        self.assertEqual(by_id[cal[1].who.split(":")[1]].name_en, "Siwakorn A.")
        self.assertEqual(by_id[cal[2].who.split(":")[1]].name_en, "Abdulroman.")
        self.assertFalse(signatures.migrate(s.report))                   # ทำซ้ำ: ไม่เปลี่ยน ไม่สร้างคนซ้ำ
        self.assertEqual(len(signatures.people_from(s.report.people)), 3)
        self.assertEqual((s.report.reviewer, s.report.approver), ("Siwakorn A.", "Abdulroman."))   # ไม่ลบค่าเก่า
        options = options_from_settings(s)
        page = layout.Doc(_cal(people=options.people, sign_cal=options.sign_cal), "en").calibration_summary(2, 4)
        self.assertIn("Siwakorn A.", page)
        self.assertIn("Abdulroman.", page)

    def test_settings_json_keeps_dict_lists(self):
        s = AppSettings()
        s.report.people = [{"id": "x1", "name_en": "A B", "image": "signatures/x.png"}]
        s.report.sign_inspection = [{"role_en": "Inspected by", "who": "operator", "show": True}]
        from dataclasses import asdict
        loaded = AppSettings()
        _merge(loaded, asdict(s))
        self.assertEqual(loaded.report.people[0]["name_en"], "A B")
        self.assertEqual(loaded.report.sign_inspection[0]["who"], "operator")
        loaded = AppSettings()
        _merge(loaded, {"catalog": {"parts": ["Battery", 3]}})            # รายการข้อความเดิมยังแปลงเป็นข้อความ
        self.assertEqual(loaded.catalog.parts, ["Battery", "3"])

    def test_relative_image_resolves_under_data(self):
        self.assertEqual(signatures.image_file("signatures/a.png", self.tmp), str(self.tmp / "signatures" / "a.png"))
        self.assertEqual(signatures.image_file(str(self.tmp / "b.png")), str(self.tmp / "b.png"))
        self.assertEqual(signatures.image_file(""), "")

    def test_prepare_signature_white_background(self):
        from ui.widgets.signature_settings import prepare_signature
        png = self.tmp / "white.png"
        _signature_png(png, white=True)
        image, removed = prepare_signature(QImage(str(png)))
        self.assertTrue(removed)
        self.assertTrue(image.hasAlphaChannel())
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)               # มุมบนซ้าย (เดิมขาว) โปร่งใส
        self.assertLess(image.width(), 400)                                # ตัดขอบว่าง
        clear = self.tmp / "clear.png"
        _signature_png(clear, white=False)
        _image, removed = prepare_signature(QImage(str(clear)))
        self.assertFalse(removed)                                          # พื้นใสอยู่แล้ว ไม่แตะ
        empty = QImage(50, 50, QImage.Format.Format_RGB32)
        empty.fill(QColor("white"))
        self.assertIsNone(prepare_signature(empty)[0])


class SettingsPageTest(_TmpRepo):
    def test_tabs_hold_every_group_and_save_signers(self):
        from ui.pages.settings import GROUPS, REPORT_TABS, TABS, SettingsPage
        placed = [g for _, cols in TABS + REPORT_TABS for col in cols for g in col]
        self.assertEqual(sorted(placed), sorted(title for title, _ in GROUPS))
        import ui.widgets.signature_settings as sig
        original = sig.signature_dir
        sig.signature_dir = lambda: self.tmp / "signatures"           # ห้ามเขียน data/ จริง
        try:
            self.settings.report.approver = "Abdulroman."
            page = SettingsPage(self.settings)
            self.assertGreaterEqual(page.tabs.count(), 7)
            dialog = sig.PersonDialog(page, None)
            png = self.tmp / "in.png"
            _signature_png(png)
            self.assertTrue(dialog.load_image(str(png)))
            dialog.name_en.setText("Yoshio  Kawashima")
            dialog._accept()
            self.assertTrue(dialog.person.image.startswith("signatures/"))
            self.assertTrue((self.tmp / dialog.person.image).is_file())
            page.signatures.people.append(dialog.person)
            page.signatures._render_people()
            row = page.signatures.slots["calibration"].rows[0]["who"]
            row.setCurrentIndex(row.findData(f"person:{dialog.person.id}"))
            checkbox = next(e for f, e in page._editors if f.name == "cal_show_occl_2sd")
            checkbox.setChecked(False)
            page._save()
            report = self.settings.report
            self.assertFalse(report.cal_show_occl_2sd)
            self.assertIn("Yoshio Kawashima", [p["name_en"] for p in report.people])
            self.assertIn("Abdulroman.", [p["name_en"] for p in report.people])   # ย้ายจากค่าเก่า
            self.assertEqual(report.sign_calibration[0]["who"], f"person:{dialog.person.id}")
            options = options_from_settings(self.settings)
            self.assertFalse(options.cal_occl_2sd)
            self.assertEqual(options.sign_cal[0].who, f"person:{dialog.person.id}")
            page.close()
        finally:
            sig.signature_dir = original

    def test_report_info_service_kinds_saved(self):
        from services.report import service
        from ui.dialogs.report_info import ReportInfoDialog
        job = service.jobs_for(self.repo, self.repo.list(), self.settings)[0]
        dialog = ReportInfoDialog(None, job)
        self.assertEqual(dialog.device_values()["service_kinds"], [])          # ตรงกับที่คิดเอง
        for box in dialog.service_boxes.values():
            box.setChecked(False)
        dialog.service_boxes["repair"].setChecked(True)
        service.save_info(self.repo, job, dialog.result_info(), dialog.device_values())
        self.assertEqual(job.service_types(), {"repair"})
        again = service.reload(self.repo, job, self.settings)
        self.assertEqual(again.service_types(), {"repair"})
        dialog.close()


if __name__ == "__main__":
    unittest.main()
