"""กราฟ flow ขณะนั้น (regression slope) พร้อมจุด peak/valley ที่ใช้จับรอบปั๊ม

ข้อมูลเก็บแบบ SeriesStore (รันหลายชั่วโมง: โหมดเต็มยังเห็นตั้งแต่ต้น ซูมยังละเอียดทุกจุด)
"""
import numpy as np
import pyqtgraph as pg

from core.strategies import STRATEGIES
from ui.plots.base import PlotModule, RingBuffer, SeriesStore
from ui.theme import Color

MIN_SPAN_FLOW_FRACTION = 0.1    # แกน Y แคบสุด = 10 % ของ target
MAX_MARKERS = 1500              # จุด peak/valley ที่วาดได้มากสุดในหนึ่งมุมมอง


class SlopePlot(PlotModule):
    title = "Instantaneous flow & pump cycle"
    y_label = "Flow (ml/h)"
    legend = ((Color.DANGER, "Peak", "▼", "peaks"), (Color.SUCCESS, "Valley", "▲", "peaks"))

    def setup(self):
        self._store = SeriesStore(2, self.ui.max_points)
        # จุดกลับตัว: พอสำหรับช่วง recent ทั้งหมด (5 Hz, ~11 จุดต่อรอบ -> ~3,600 จุดต่อ 2.2 ชม.)
        self._tops = RingBuffer(2, 10000)
        self._downs = RingBuffer(2, 10000)
        self._curve = self._line(Color.SERIES_SLOPE, "Slope")
        outline = pg.mkPen(Color.SURFACE, width=1)
        self._top_points = pg.ScatterPlotItem(size=9, symbol="t", pen=outline, brush=pg.mkBrush(Color.DANGER), name="Peak")
        self._down_points = pg.ScatterPlotItem(size=9, symbol="t1", pen=outline, brush=pg.mkBrush(Color.SUCCESS), name="Valley")
        self.plot.addItem(self._top_points)
        self.plot.addItem(self._down_points)
        self._target = 1.0

    def begin_session(self, config):
        # วิธีจับตามเวลา: ยังแสดง slope ให้เห็นรูปแบบการไหล แต่ไม่มีจุด peak/valley
        uses_cycles = config.strategy in STRATEGIES and STRATEGIES.get(config.strategy).uses_cycles
        self.set_header(self.title if uses_cycles else "Instantaneous flow", self.legend if uses_cycles else ())
        self._target = max(config.target_flow, 1.0)
        super().begin_session(config)

    def consume(self, result):
        changed = False
        if result.slope_flow is not None:
            self._store.append(result.t, result.slope_flow)
            changed = True
        if result.extremum is not None:
            target = self._tops if result.extremum.kind == "TOP" else self._downs
            target.append(result.extremum.t, result.extremum.flow)
            changed = True
        return changed

    @staticmethod
    def _points_after(buffer: RingBuffer, left: float | None):
        x, y = buffer.column(0), buffer.column(1)
        if left is None or not len(x):
            return x, y
        start = int(np.searchsorted(x, left))
        return x[start:], y[start:]

    def redraw(self):
        last = self._store.last(0)
        if last is None:
            self._curve.setData([], [])
            self._top_points.setData([], [])
            self._down_points.setData([], [])
            return
        left_edge = self.visible_left(last)
        x, y = self._store.view(left_edge)
        self._curve.setData(x, y)
        show = self.series_visible("peaks")        # กดชื่อ Peak/Valley บนหัวกราฟเพื่อซ่อนจุดกลับตัว
        self._top_points.setVisible(show)
        self._down_points.setVisible(show)
        tops, downs = self._points_after(self._tops, left_edge), self._points_after(self._downs, left_edge)
        if len(tops[0]) + len(downs[0]) > MAX_MARKERS:
            # มุมมองยาวหลายชั่วโมง: จุดกลับตัวหลายพันจุดทับกันจนอ่านไม่ออก และวาดช้า -> ไม่วาด (ซูมเข้าจะเห็น)
            tops = downs = ([], [])
        self._top_points.setData(*tops)
        self._down_points.setData(*downs)
        left, right = self._roll_x(last)
        # แกน Y ตามข้อมูลในช่วงที่เห็น (เปลี่ยนโหมด/เริ่มรอบใหม่ก็ยังเห็นรูปแบบรอบปั๊มชัด)
        self._fit_y_visible(x, y, left, right, MIN_SPAN_FLOW_FRACTION * self._target)

    def reset(self):
        self._store.clear()
        self._tops.clear()
        self._downs.clear()
