"""กราฟ flow เฉลี่ยสะสม (สาย A, B และค่าเฉลี่ยรวม) เทียบกับ target และแถบเกณฑ์ยอมรับ

กดชื่อเส้นบนหัวกราฟเพื่อซ่อน/แสดง (เฉพาะจอนี้) · จับรอบเดียว: มีแค่สาย A (ค่ารวม = สาย A)
"""
from ui.plots.base import PlotModule, SeriesStore
from ui.theme import Color

_SERIES = ((Color.SERIES_A, "Chain A", "●", "a"), (Color.SERIES_B, "Chain B", "●", "b"),
           (Color.SERIES_ALL, "Overall", "●", "all"))


class CumulativePlot(PlotModule):
    title = "Cumulative average flow"
    y_label = "Flow (ml/h)"
    legend = _SERIES

    def setup(self):
        self._store = SeriesStore(4, self.ui.max_points)    # รันนาน: โหมดเต็มเห็นตั้งแต่ต้น ซูมละเอียดทุกจุด
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
        self._store.append(c.t, c.flow_a, c.flow_b, c.flow_all)
        return True

    def redraw(self):
        last = self._store.last(0)
        columns = self._store.view(self.visible_left(last)) if last is not None else [[]] * 4
        paired = self.chains == 2
        for column, key in enumerate(("a", "b", "all"), start=1):
            curve = self._curves[key]
            visible = self.series_visible(key) and (paired or key == "a")
            curve.setVisible(visible)
            if visible:
                curve.setData(columns[0], columns[column])
        self._roll_x(last or 0.0)
        # แกน Y ยึดตามค่าล่าสุด (ค่าช่วงแรกที่ยังแกว่งแรงจะไม่ดึงสเกลจนอ่านไม่ออก)
        self._fit_y([self._store.last(i) for i in (1, 2, 3)] if last is not None else ())

    def reset(self):
        self._store.clear()
