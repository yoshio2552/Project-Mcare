"""กราฟ flow เฉลี่ยสะสม (สาย A, B และค่าเฉลี่ยรวม) เทียบกับ target และแถบเกณฑ์ยอมรับ"""
from ui.plots.base import PlotModule, RingBuffer
from ui.theme import Color


class CumulativePlot(PlotModule):
    title = "Cumulative average flow"
    y_label = "Flow (ml/h)"
    legend = ((Color.SERIES_A, "Chain A"), (Color.SERIES_B, "Chain B"), (Color.SERIES_ALL, "Overall"))

    def setup(self):
        self._buffer = RingBuffer(4, self.ui.max_points)
        self._add_target_band()
        self._curve_a = self._line(Color.SERIES_A, "Chain A", width=1.5)
        self._curve_b = self._line(Color.SERIES_B, "Chain B", width=1.5)
        self._curve_all = self._line(Color.SERIES_ALL, "Overall", width=2.5)

    def begin_session(self, config):
        self._set_target(config)
        super().begin_session(config)

    def consume(self, result):
        c = result.cumulative
        if c is None or c.t <= 0:
            return False
        self._buffer.append(c.t, c.flow_a, c.flow_b, c.flow_all)
        return True

    def redraw(self):
        x = self._buffer.column(0)
        self._curve_a.setData(x, self._buffer.column(1))
        self._curve_b.setData(x, self._buffer.column(2))
        self._curve_all.setData(x, self._buffer.column(3))
        self._roll_x(x[-1] if len(x) else 0.0)
        # แกน Y ยึดตามค่าล่าสุด (ค่าช่วงแรกที่ยังแกว่งแรงจะไม่ดึงสเกลจนอ่านไม่ออก)
        self._fit_y([self._buffer.column(i)[-1] for i in (1, 2, 3)] if len(x) else ())

    def reset(self):
        self._buffer.clear()
