"""กราฟ flow ของแต่ละช่วงวัด (จุดต่อ 1 รอบปั๊ม/ช่วงเวลา) แยกสีตามสาย + เส้นค่าเฉลี่ย"""
import pyqtgraph as pg
from PySide6.QtCore import Qt

from ui.plots.base import PlotModule, RingBuffer
from ui.theme import Color


class IntervalPlot(PlotModule):
    title = "Interval flow"
    y_label = "Flow (ml/h)"
    x_label = "Time since chain start (s)"
    legend = ((Color.SERIES_A, "Chain A"), (Color.SERIES_B, "Chain B"), (Color.SERIES_MEAN, "Mean", "- -"))

    def setup(self):
        self._chains = [RingBuffer(2, self.ui.max_points), RingBuffer(2, self.ui.max_points)]
        self._add_target_band()
        self._curves = [
            self._line(color, name, width=1.5, symbol="o", symbolSize=7,
                       symbolBrush=color, symbolPen=pg.mkPen(Color.SURFACE, width=1))
            for color, name in ((Color.SERIES_A, "Chain A"), (Color.SERIES_B, "Chain B"))
        ]
        self._mean_line = pg.InfiniteLine(angle=0, pen=pg.mkPen(Color.SERIES_MEAN, width=1.5, style=Qt.PenStyle.DashLine))
        self.plot.addItem(self._mean_line)
        self._mean_line.hide()
        self._mean = None
        self._max_t = 0.0

    def begin_session(self, config):
        self._set_target(config)
        super().begin_session(config)

    def consume(self, result):
        interval = result.interval
        if interval is None:
            return False
        self._chains[interval.chain].append(interval.t, interval.flow)
        self._max_t = max(self._max_t, interval.t)
        if result.stats is not None:
            self._mean = result.stats.mean_flow
        return True

    def redraw(self):
        for curve, chain in zip(self._curves, self._chains):
            curve.setData(chain.column(0), chain.column(1))
        self._mean_line.setVisible(self._mean is not None)
        if self._mean is not None:
            self._mean_line.setValue(self._mean)
        self._fit_y([v for chain in self._chains for v in chain.column(1)])
        # แกนเวลาขยายเป็นขั้นละ 1 นาที
        self.plot.setXRange(0, (int(self._max_t / 60) + 1) * 60, padding=0.02)

    def reset(self):
        for chain in self._chains:
            chain.clear()
        self._mean = None
        self._max_t = 0.0
