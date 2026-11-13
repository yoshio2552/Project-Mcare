"""ทดสอบหน้าต่างของ UI แบบไม่มีจอ (offscreen) — กดปุ่มจริงผ่าน QTest

รัน:  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from core.models import SessionConfig, SessionSummary, Verdict

app = QApplication.instance() or QApplication([])

from ui.dialogs.result_review import ResultReviewDialog   # noqa: E402


def _summary(end_reason="completed") -> SessionSummary:
    return SessionSummary(config=SessionConfig(target_flow=50.0), end_reason=end_reason,
                          error_pct=1.2, mean_flow=50.6, sd2_pct=1.0, verdict=Verdict.PASS, interval_count=10)


def _run(dialog, button) -> int:
    """เปิด dialog แบบ modal แล้วกดปุ่ม — คืนผลของ exec()"""
    QTimer.singleShot(50, lambda: QTest.mouseClick(button, Qt.MouseButton.LeftButton))
    QTimer.singleShot(2000, dialog.done if False else (lambda: dialog.done(99)))   # กันค้างถ้าปุ่มไม่ทำงาน
    return dialog.exec()


class ResultReviewTest(unittest.TestCase):
    def test_discard_button_rejects(self):
        for end_reason in ("completed", "stopped"):
            dialog = ResultReviewDialog(None, _summary(end_reason))
            self.assertEqual(_run(dialog, dialog.btn_discard), QDialog.DialogCode.Rejected, end_reason)

    def test_keep_button_accepts(self):
        dialog = ResultReviewDialog(None, _summary())
        self.assertEqual(_run(dialog, dialog.btn_keep), QDialog.DialogCode.Accepted)

    def test_escape_does_not_discard(self):
        dialog = ResultReviewDialog(None, _summary())
        QTimer.singleShot(50, lambda: QTest.keyClick(dialog, Qt.Key.Key_Escape))
        QTimer.singleShot(400, lambda: dialog.done(99))
        self.assertEqual(dialog.exec(), 99)      # Esc ไม่ปิด = ไม่ลบข้อมูลโดยไม่ตั้งใจ


class IntervalPlotTest(unittest.TestCase):
    def _cell(self):
        from config.settings import UiSettings
        from ui.plots import IntervalPlot
        from ui.plots.cell import PlotCell
        self.saved = 0
        cell = PlotCell(IntervalPlot, UiSettings())
        cell.module.on_option_changed = lambda: setattr(self, "saved", self.saved + 1)
        cell.module.begin_session(SessionConfig(target_flow=50.0))
        return cell

    @staticmethod
    def _feed(plot, flows):
        from core.models import EngineResult, Interval
        plot.feed([EngineResult(t=10.0 * (i + 1), weight=0.0, interval=Interval(i, i % 2, 10.0 * (i + 1), 10.0, f, 0.0))
                   for i, f in enumerate(flows)])

    def test_moving_average_is_running_mean_from_start(self):
        cell = self._cell()
        self._feed(cell.module, [48.0, 52.0, 50.0, 54.0])
        x, y = cell.module._moving_curve.getData()
        self.assertEqual(list(y), [48.0, 50.0, 50.0, 51.0])          # เฉลี่ยตั้งแต่ช่วงแรกถึงช่วงนั้น
        self.assertEqual(list(x), [10.0, 20.0, 30.0, 40.0])
        self.assertIsNone(cell.module._moving_curve.opts["symbol"])     # เส้นต่อเนื่อง ไม่มีจุด (ผู้ใช้ขอ 2026-11-13)

    def test_header_chip_toggles_and_style_buttons(self):
        from PySide6.QtWidgets import QPushButton
        cell = self._cell()
        ui = cell.module.ui
        chips = {b.text().split("  ", 1)[1]: b for b in cell.header.findChildren(QPushButton)
                 if b.property("variant") == "legendChip" and b.isVisibleTo(cell.header) is not None}
        moving = next(b for t, b in chips.items() if "Moving" in t)
        QTest.mouseClick(moving, Qt.MouseButton.LeftButton)
        self.assertFalse(ui.interval_moving_avg)
        self.assertEqual(self.saved, 1)
        points = next(b for b in cell.header.findChildren(QPushButton)
                      if b.property("variant") == "segmentSmall" and not b.isChecked() and b.parent() is not None)
        QTest.mouseClick(points, Qt.MouseButton.LeftButton)
        self.assertEqual(ui.interval_style, "points")
        self.assertEqual(self.saved, 2)


if __name__ == "__main__":
    unittest.main()
