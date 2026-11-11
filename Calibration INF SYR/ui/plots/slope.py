"""กราฟ flow ขณะนั้น (regression slope) พร้อมจุด peak/valley ที่ใช้จับรอบปั๊ม"""
import pyqtgraph as pg

from core.strategies import STRATEGIES
from ui.plots.base import PlotModule, RingBuffer
from ui.theme import Color


class SlopePlot(PlotModule):
    title = "Instantaneous flow & pump cycle"
    y_label = "Flow (ml/h)"
    legend = ((Color.DANGER, "Peak", "▼"), (Color.SUCCESS, "Valley", "▲"))

    def setup(self):
        self._buffer = RingBuffer(2, self.ui.max_points)
        self._tops = RingBuffer(2, 2000)
        self._downs = RingBuffer(2, 2000)
        self._curve = self._line(Color.SERIES_SLOPE, "Slope")
        outline = pg.mkPen(Color.SURFACE, width=1)
        self._top_points = pg.ScatterPlotItem(size=9, symbol="t", pen=outline, brush=pg.mkBrush(Color.DANGER), name="Peak")
        self._down_points = pg.ScatterPlotItem(size=9, symbol="t1", pen=outline, brush=pg.mkBrush(Color.SUCCESS), name="Valley")
        self.plot.addItem(self._top_points)
        self.plot.addItem(self._down_points)
        self.plot.setAutoVisible(y=True)

    def begin_session(self, config):
        # วิธีจับตามเวลา: ยังแสดง slope ให้เห็นรูปแบบการไหล แต่ไม่มีจุด peak/valley
        uses_cycles = config.strategy in STRATEGIES and STRATEGIES.get(config.strategy).uses_cycles
        self.set_header(self.title if uses_cycles else "Instantaneous flow", self.legend if uses_cycles else ())
        super().begin_session(config)

    def consume(self, result):
        changed = False
        if result.slope_flow is not None:
            self._buffer.append(result.t, result.slope_flow)
            changed = True
        if result.extremum is not None:
            target = self._tops if result.extremum.kind == "TOP" else self._downs
            target.append(result.extremum.t, result.extremum.flow)
            changed = True
        return changed

    def redraw(self):
        x = self._buffer.column(0)
        self._curve.setData(x, self._buffer.column(1))
        self._top_points.setData(self._tops.column(0), self._tops.column(1))
        self._down_points.setData(self._downs.column(0), self._downs.column(1))
        self._roll_x(x[-1] if len(x) else 0.0)

    def reset(self):
        self._buffer.clear()
        self._tops.clear()
        self._downs.clear()
