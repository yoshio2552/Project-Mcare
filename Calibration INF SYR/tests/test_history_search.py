"""ทดสอบการค้นหา/คัดกรองหน้าประวัติ (ผู้ใช้ 2026-11-19): ค้นเร็วช่องเดียว + คัดกรองขั้นสูง + ล้างที่เลือก

รัน:  python -m unittest tests.test_history_search -v
"""
import os
import sys
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from services import history_search as hs
from tests.test_report_ui import _TmpRepo

app = QApplication.instance() or QApplication([])


def _session(**job):
    base = dict(pump_type="infusion", site="โรงพยาบาลขอนแก่น", province="ขอนแก่น", brand="Terumo", model="TE-171",
                accessory_brand="Terumo", accessory="20 หยดต่อ ml", operator="สมชาย ใจดี", serial_no="17110582",
                job_no="MCI-0142", checks={"visual.door_lock": "fail"})
    base.update(job)
    return {"ref": "1", "started_at": "2026-11-18T10:00:00", "verdict": "PASS", "end_reason": "completed",
            "config": {"run_mode": "inspection", "job_id": "J1", "target_flow": 50.0, "job": base}}


class QuickSearchTest(unittest.TestCase):
    def test_words_and_aliases(self):
        s = _session()
        for text in ("te-171 สมชาย", "inf", "อินฟิวชั่น", "MCI", "2569", "18/11/2569", "18/11/2026", "2026-11", "พ.ย.",
                     "50", "ผ่าน", "pass", "ขอนแก่น", "20 หยด", "ตรวจสภาพ"):
            self.assertTrue(hs.quick_match(s, text), text)
        for text in ("syr", "ไม่ผ่าน", "fail", "2568", "สอบเทียบ", "door_lock"):
            self.assertFalse(hs.quick_match(s, text), text)      # "fail" ในผลตรวจรายข้อไม่นับ

    def test_field_prefix(self):
        s = _session()
        self.assertTrue(hs.quick_match(s, "ผู้ทำ:สมชาย"))
        self.assertFalse(hs.quick_match(s, "ผู้ทำ:สมหญิง"))
        self.assertTrue(hs.quick_match(s, "ปี:2569 rate:50"))
        self.assertTrue(hs.quick_match(s, "year:2026"))           # ค.ศ. ก็ได้
        self.assertFalse(hs.quick_match(s, "rate:5"))             # rate เทียบตรงค่า
        self.assertTrue(hs.quick_match(s, "ชุดสาย:terumo type:inf"))
        self.assertTrue(hs.quick_match(s, "ผล:ผ่าน"))
        self.assertTrue(hs.quick_match(s, "unknown:word") is False)   # ไม่ใช่ชื่อช่อง = ค้นเป็นคำทั่วไป

    def test_advanced_filter(self):
        records = [hs.record(_session()), hs.record(_session(pump_type="syringe", brand="Nipro", model="SP-500",
                                                             site="รพ.อุดร"))]
        records[1]["date"], records[1]["year"] = date(2025, 3, 1), 2568
        self.assertEqual(hs.distinct(records, "brand"), ["Nipro", "Terumo"])
        self.assertEqual(hs.distinct(records, "model", {"brand": "nipro"}), ["SP-500"])
        self.assertEqual(hs.years(records), [2569, 2568])
        self.assertEqual([r["brand"] for r in records if hs.AdvancedFilter(pump="syringe").matches(r)], ["Nipro"])
        self.assertEqual(len([r for r in records if hs.AdvancedFilter(site="ขอนแก่น").matches(r)]), 1)
        f = hs.AdvancedFilter(date_from=date(2026, 1, 1), date_to=date(2026, 12, 31))
        self.assertEqual([r["brand"] for r in records if f.matches(r)], ["Terumo"])
        self.assertEqual(hs.AdvancedFilter(operator="สมชาย", year=2569).active(), ["operator", "year"])


class HistoryFilterUiTest(_TmpRepo):
    def test_panel_filters_chips_and_clear_ticks(self):
        from PySide6.QtCore import Qt
        from ui.pages.history import HistoryPage
        page = HistoryPage(self.settings)
        total = page.table.rowCount()
        page.btn_advanced.setChecked(True)
        self.assertTrue(page.advanced.isVisibleTo(page))
        page.advanced.pump.setCurrentIndex(page.advanced.pump.findData("syringe"))
        page._apply_filter()                                      # (ปกติรอ 180 ms หลังเปลี่ยน)
        self.assertLess(page.table.rowCount(), total)
        self.assertTrue(all(hs.record(s)["pump"] == "syringe" for s in page._visible))
        self.assertEqual([name for name, _ in page.advanced.chips()], ["pump"])
        self.assertIn("1", page.btn_advanced.text())
        page.chips.removed.emit("pump")                           # กด × ที่ป้าย
        page._apply_filter()
        self.assertEqual(page.table.rowCount(), total)
        # ปี = ตั้งช่วงวันที่ให้เอง
        year = page.advanced.year.itemData(1)
        page.advanced.year.setCurrentIndex(1)
        self.assertEqual(page.advanced.value().date_from, date(year - 543, 1, 1))
        page.advanced.clear()
        self.assertEqual(page.advanced.chips(), [])
        # ล้างที่เลือก
        page.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        self.assertTrue(page._checked)
        self.assertTrue(page.btn_clear_ticks.isVisibleTo(page))
        page.btn_clear_ticks.click()
        self.assertEqual(page._checked, {})
        page.close()

    def test_date_popup_opens_at_today_and_table_fill_is_fast(self):
        import time
        from PySide6.QtCore import QDate, QEvent
        from ui.pages.history import HistoryPage
        page = HistoryPage(self.settings)
        calendar = page.advanced.date_from.calendarWidget()
        QApplication.sendEvent(calendar, QEvent(QEvent.Type.Show))
        today = QDate.currentDate()
        self.assertEqual((calendar.yearShown(), calendar.monthShown()), (today.year(), today.month()))
        page.show()
        start = time.perf_counter()
        page._apply_filter()
        self.assertLess(time.perf_counter() - start, 0.5)     # เดิม 2 วินาที (คอลัมน์คำนวณความกว้างทุกช่อง)
        page.close()

    def test_quick_search_box(self):
        from ui.pages.history import HistoryPage
        page = HistoryPage(self.settings)
        page.search.setText("syr")
        page._apply_filter()                                      # (ปกติรอหยุดพิมพ์ 180 ms)
        self.assertTrue(page._visible)
        self.assertTrue(all(hs.record(s)["pump"] == "syringe" for s in page._visible))
        page.close()


if __name__ == "__main__":
    unittest.main()
