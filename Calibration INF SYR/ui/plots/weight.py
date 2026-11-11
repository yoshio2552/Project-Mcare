"""กราฟน้ำหนักดิบจากตราชั่ง (ดูความต่อเนื่องของสัญญาณตลอด session)"""
from ui.plots.base import DecimatingBuffer, PlotModule
from ui.theme import Color


class WeightPlot(PlotModule):
    title = "Balance weight"
    y_label = "Weight (g)"

    def setup(self):
        self._buffer = DecimatingBuffer(2, min(self.ui.max_points, 20000))
        self._curve = self._line(Color.SERIES_WEIGHT)

    def consume(self, result):
        self._buffer.append(result.t, result.weight)
        return True

    def redraw(self):
        self._curve.setData(self._buffer.column(0), self._buffer.column(1))

    def reset(self):
        self._buffer.clear()
