"""การจับรอบปั๊มเมื่อรูปคลื่นมี "ยอดรอง" ในรอบเดียวกัน + ตัวปรับหน้าต่างเลือกกลางช่วง + แกนกราฟ/ธีม (2026-11-17)

ที่มา: LM730 50 ml/h (ข้อมูลจริง) — ยอดรองสูง ~0.6 ของยอดหลัก อยู่ก่อนยอดหลักถัดไป ~0.45 คาบ
n̄ = 0.36 x คาบ ที่ได้จากการสอบเทียบ จับยอดรองเป็น peak เป็นบางรอบ (รอบ 5.5 s ปนกับ 14.1 s)
"""
import math
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core.cycle_analyzer import CycleAnalyzer
from core.tuning import TrialResult, TuningResult

PERIOD, DT = 14.0, 0.2


def waveform(t: float, jitter: float = 0.0) -> float:
    """slope จำลองแบบ LM730: ยอดหลักแคบที่เฟส 0 + ยอดรองกว้างที่เฟส 0.55 + ก้นลึกหลังยอดหลัก"""
    phase = ((t + jitter) / PERIOD) % 1.0
    bump = lambda center, width, height: height * math.exp(-((min(abs(phase - center), 1 - abs(phase - center))) / width) ** 2)
    return 52.0 + bump(0.0, 0.05, 10.0) + bump(0.55, 0.10, 4.0) - bump(0.13, 0.05, 6.0)


def cycles(n_bar: int, seconds: float = 600.0, wobble: float = 0.0, **kwargs) -> list[float]:
    analyzer, durations = CycleAnalyzer(n_bar=n_bar, **kwargs), []
    for i in range(int(seconds / DT)):
        t = i * DT
        jitter = wobble * math.sin(2 * math.pi * t / 97.0)      # คาบขยับช้าๆ เหมือนปั๊มจริง
        event = analyzer.update(t, t, waveform(t, jitter))
        if event and event.cycle and event.cycle.end.kind == "TOP":
            durations.append(event.cycle.end.t - event.cycle.start.t)
    return durations


class MinorPeakTest(unittest.TestCase):
    def assert_full_cycles(self, durations):
        self.assertGreater(len(durations), 30)
        for d in durations:
            self.assertAlmostEqual(d, PERIOD, delta=PERIOD * 0.15)

    def test_edge_window_never_reports_minor_peak(self):
        # n̄ ติดขอบ (0.36 x คาบ = 25 จุด): เดิมยอดรองหลุดเป็น peak เมื่อคาบขยับ
        self.assert_full_cycles(cycles(n_bar=25, wobble=1.0))

    def test_small_window_is_rescued_by_swing_gate(self):
        # n̄ = 0.2 x คาบ: ยอดรอง + ก้นรองเป็นจุดกลับตัวเฉพาะที่ทั้งคู่ — เกณฑ์แอมพลิจูดต้องข้ามไป
        self.assert_full_cycles(cycles(n_bar=14))
        without_gate = cycles(n_bar=14, min_swing_fraction=0.0)
        self.assertTrue(any(d < PERIOD * 0.7 for d in without_gate))     # ยืนยันว่าเทสต์นี้ทดสอบเกณฑ์จริง

    def test_wide_window_still_works(self):
        self.assert_full_cycles(cycles(n_bar=42))                       # 0.6 x คาบ


class TunerPlateauTest(unittest.TestCase):
    def result(self, current, plateau, open_ends=(False, True), best=(0.25, 0.5)):
        trial = TrialResult(best[0], best[1], 18, 35, 30, 0.01, 0.01, 1.0, 0.022)
        return TuningResult(rate=50, sessions=1, period_s=14.0, sample_period_s=0.2, current=current,
                            current_score=0.022, best=trial, plateau=plateau, plateau_open=open_ends)

    def test_current_on_plateau_edge_moves_to_middle(self):
        # คะแนนเท่ากัน (ไม่ดีขึ้น 10 %) แต่ค่าปัจจุบันติดขอบล่างของช่วงที่ใช้ได้ -> ย้ายเข้ากลางช่วง
        self.assertEqual(self.result((0.25, 0.35), (0.35, 0.6)).recommended(), (0.25, 0.5))
        self.assertEqual(self.result((0.25, 0.30), (0.40, 0.6)).recommended(), (0.25, 0.5))

    def test_current_inside_plateau_is_kept(self):
        self.assertEqual(self.result((0.25, 0.45), (0.35, 0.6)).recommended(), (0.25, 0.45))
        # ปลายบนของช่วงชนขอบของค่าที่ลอง = ไม่รู้ว่าเป็นขอบจริง ไม่ถือว่าติดขอบ
        self.assertEqual(self.result((0.25, 0.60), (0.35, 0.6)).recommended(), (0.25, 0.60))


class TypicalPeriodTest(unittest.TestCase):
    def test_one_bad_cycle_does_not_move_the_learned_period(self):
        from core.profiles import typical_period
        durations = [14.1] * 21 + [5.5]                                 # ผลจริง 20261117_121157 (LM730 50 ml/h)
        self.assertAlmostEqual(sum(durations) / len(durations), 13.7, delta=0.1)     # ค่าเฉลี่ยถูกดึง
        self.assertAlmostEqual(typical_period(durations), 14.1)
        self.assertAlmostEqual(typical_period([9.0, 9.4]), 9.2)         # จำนวนคู่: เฉลี่ยสองค่ากลาง
        self.assertIsNone(typical_period([]))
        self.assertIsNone(typical_period([0.0, None]))


class GraphAxisAndThemeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def module(self, ui, config):
        import pyqtgraph as pg
        from ui.plots.cumulative import CumulativePlot
        self.widget = pg.PlotWidget()
        plot = CumulativePlot(self.widget.getPlotItem(), ui)
        plot.range_mode = "full"
        plot.begin_session(config)
        return plot

    def test_flow_y_fixed_and_full_time_axis(self):
        from config.settings import UiSettings
        from core.models import EndMode, SessionConfig
        ui = UiSettings()
        timed = self.module(ui, SessionConfig(target_flow=50.0, duration_min=10.0, end_mode=EndMode.TIME))
        low, high = timed.plot.viewRange()[1]
        self.assertAlmostEqual(low, 40.0, delta=0.01)                   # rate ± 20 %
        self.assertAlmostEqual(high, 60.0, delta=0.01)
        self.assertEqual(timed.full_min_s, 600.0)                       # จบตามเวลา: 0–เวลาที่ตั้ง
        self.assertEqual(timed._visible_x(12.0), (0.0, 600.0))
        self.assertEqual(timed._visible_x(700.0), (0.0, 700.0))
        counted = self.module(ui, SessionConfig(target_flow=50.0, end_mode=EndMode.COUNT, cycle_count=30))
        self.assertEqual(counted._visible_x(12.0), (0.0, 300.0))        # จบตามรอบ: ขั้นต่ำจากหน้าตั้งค่า
        # ค่าเฉลี่ยหลุดช่วงตรึง -> ขยายให้เห็น
        counted._fit_y((), anchors=(30.0,))
        self.assertLess(counted.plot.viewRange()[1][0], 30.0)
        ui.graph_flow_y_pct = 0.0                                       # 0 = ตามข้อมูลแบบเดิม
        free = self.module(ui, SessionConfig(target_flow=50.0))
        self.assertIsNone(free._y_fixed)

    def test_palette_switch_updates_colors_and_tables(self):
        from ui import theme
        dark_text = theme.PALETTES["dark"]["TEXT"]
        try:
            theme.use_palette("light")
            self.assertEqual(theme.Color.TEXT, theme.PALETTES["light"]["TEXT"])
            self.assertEqual(theme.TONES["neutral"], theme.Color.TEXT)
            self.assertEqual(theme.PUMP_COLORS["infusion"], theme.Color.INFUSION)
            self.assertEqual(theme.resolve("SERIES_A"), theme.PALETTES["light"]["SERIES_A"])
            self.assertEqual(set(theme.PALETTES["light"]), set(theme.PALETTES["dark"]))   # ทุกสีมีครบทั้งสองธีม
            self.assertIn(theme.Color.SURFACE, theme._stylesheet())
        finally:
            theme.use_palette("dark")
        self.assertEqual(theme.Color.TEXT, dark_text)
        self.assertEqual(theme.use_palette("no-such-theme"), "dark")


if __name__ == "__main__":
    unittest.main()
