"""กราฟ flow เฉลี่ยสะสม (สาย A, B และค่าเฉลี่ยรวม) เทียบกับ target และแถบเกณฑ์ยอมรับ

กดชื่อเส้นบนหัวกราฟเพื่อซ่อน/แสดง (เฉพาะจอนี้) · จับรอบเดียว: มีแค่สาย A (ค่ารวม = สาย A)
"""
from ui.plots.base import PlotModule, RingBuffer
from ui.theme import Color

_SERIES = ((Color.SERIES_A, "Chain A", "●", "a"), (Color.SERIES_B, "Chain B", "●", "b"),
           (Color.SERIES_ALL, "Overall", "●", "all"))


class CumulativePlot(PlotModule):
    title = "Cumulative average flow"
    y_label = "Flow (ml/h)"
    legend = _SERIES

    def setup(self):
        self._buffer = RingBuffer(4, self.ui.max_points)
        self._add_target_band()
        self._curves = {
            "a": self._line(Color.SERIES_A, "Chain A", width=1.5),
            "b": self._line(Color.SERIES_B, "Chain B", width=1.5),
            "all": self._line(Color.SERIES_ALL, "Overall", width=2.5),
        }

    def begin_session(self, config):
        self._set_target(config)
        self.set_header(self.title, _SERIES if self.chains == 2 else _SERIES[:1])
        super().begin_session(config)

    def consume(self, result):
        c = result.cumulative
        if c is None or c.t <= 0:
            return False
        self._buffer.append(c.t, c.flow_a, c.flow_b, c.flow_all)
        return True

    def redraw(self):
        x = self._buffer.column(0)
        paired = self.chains == 2
        for column, key in enumerate(("a", "b", "all"), start=1):
            curve = self._curves[key]
            visible = self.series_visible(key) and (paired or key == "a")
            curve.setVisible(visible)
            if visible:
                curve.setData(x, self._buffer.column(column))
        self._roll_x(x[-1] if len(x) else 0.0)
        # แกน Y ยึดตามค่าล่าสุด (ค่าช่วงแรกที่ยังแกว่งแรงจะไม่ดึงสเกลจนอ่านไม่ออก)
        self._fit_y([self._buffer.column(i)[-1] for i in (1, 2, 3)] if len(x) else ())

    def reset(self):
        self._buffer.clear()
