"""กราฟ flow ของแต่ละช่วงวัด แยกสีตามสาย + เส้นค่าเฉลี่ย

รูปแบบการวาด (ปุ่มบนหัวกราฟ, จำไว้ใน UiSettings.interval_style):
    step    ขั้นบันได — แต่ละช่วงวัดเป็นเส้นแนวนอนยาวเท่าช่วงเวลาของมัน (แบบกราฟ IEC 60601-2-24)
    points  จุดต่อเส้น — 1 จุดต่อ 1 ช่วงวัด ที่เวลาปลายช่วง (แบบเดิม)
เส้นค่าเฉลี่ย (กดชื่อบนหัวกราฟเพื่อซ่อน/แสดง ได้ทั้งคู่หรืออย่างใดอย่างหนึ่ง):
    Moving avg     ค่าเฉลี่ยสะสม "ตั้งแต่ช่วงแรกถึงช่วงนั้น" (start → end) จุดต่อจุด — ค่าเริ่มต้น
                   จุดสุดท้ายเท่ากับค่าเฉลี่ยรวมพอดี จึงเห็นว่าค่าเฉลี่ยเข้าสู่ค่าสุดท้ายอย่างไร
    ค่าเฉลี่ยรวม    เส้นตรงแนวนอนของค่าเฉลี่ยทุกช่วงตั้งแต่เริ่ม (แบบเดิม)
    ยังไม่แก้       ค่าเฉลี่ยสะสมของ flow ที่ "ยังไม่แก้" (1 g = 1 ml ไม่หัก self-check) เส้นประสีจาง
                   เทียบกับค่าสุทธิ (เส้นทึบ) — เห็นว่าค่าแก้ Z + self-check ขยับผลไปเท่าไร
สาย A / สาย B กดซ่อนได้เช่นกัน (เฉพาะจอนี้ ไม่จำ)
"""
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt

from ui.plots.base import PlotModule, RingBuffer
from ui.theme import Color

_CHAINS = ((Color.SERIES_A, "Chain A", "●", "a"), (Color.SERIES_B, "Chain B", "●", "b"))
_MOVING = (Color.SERIES_MEAN, "Moving average", "━", "moving")
_MEAN = (Color.SERIES_OVERALL_MEAN, "Overall mean", "┄", "mean")     # คนละสีกับ Moving avg (ผู้ใช้ขอ 2026-11-13)
_RAW = (Color.TEXT_FAINT, "Uncorrected", "┈", "raw")
_SAVED = {"moving": "interval_moving_avg", "mean": "interval_overall_mean",
          "raw": "interval_uncorrected"}   # key -> ชื่อใน UiSettings


class IntervalPlot(PlotModule):
    title = "Interval flow"
    y_label = "Flow (ml/h)"
    x_label = "Time since chain start (s)"
    styles = (("step", "Steps"), ("points", "Points"))

    def setup(self):
        # ต่อสาย: t ปลายช่วง, flow, ระยะเวลาช่วง
        self._chains = [RingBuffer(3, self.ui.max_points), RingBuffer(3, self.ui.max_points)]
        self._moving = RingBuffer(3, self.ui.max_points)       # t, ค่าเฉลี่ยสะสม (สุทธิ), ค่าเฉลี่ยสะสม (ยังไม่แก้)
        self._sum, self._sum_raw, self._count = 0.0, 0.0, 0
        self._add_target_band()
        self._curves = [self._line(color, name, width=2.0) for color, name, *_ in _CHAINS]
        # Moving avg = เส้นทึบต่อเนื่อง ไม่มีจุด (ผู้ใช้ขอ 2026-11-13)
        self._moving_curve = self.plot.plot(pen=pg.mkPen(Color.SERIES_MEAN, width=2.2))
        self._moving_curve.setZValue(5)
        self._raw_curve = self.plot.plot(pen=pg.mkPen(Color.TEXT_FAINT, width=1.5, style=Qt.PenStyle.DashLine))
        self._raw_curve.setZValue(3)
        self._mean_line = pg.InfiniteLine(angle=0, pen=pg.mkPen(Color.SERIES_OVERALL_MEAN, width=1.8,
                                                                style=Qt.PenStyle.DashLine))
        self._mean_line.setZValue(4)
        self.plot.addItem(self._mean_line)
        self._mean_line.hide()
        self._mean = None
        self._max_t = 0.0
        self._apply_style()
        self._update_header()

    # ------------------------------------------------------------ ตัวเลือกบนหัวกราฟ
    def current_style(self) -> str:
        return self.ui.interval_style

    def set_style(self, key: str) -> None:
        self.ui.interval_style = key
        self._apply_style()
        self._option_changed()

    def series_visible(self, key: str) -> bool:
        if key in _SAVED:
            return bool(getattr(self.ui, _SAVED[key]))
        return super().series_visible(key)

    def set_series_visible(self, key: str, visible: bool) -> None:
        if key in _SAVED:
            setattr(self.ui, _SAVED[key], visible)
            self._option_changed()
        else:
            super().set_series_visible(key, visible)

    def _apply_style(self) -> None:
        points = self.ui.interval_style == "points"
        for curve, (color, *_) in zip(self._curves, _CHAINS):
            if points:
                curve.setPen(pg.mkPen(color, width=1.5))
                curve.setSymbol("o")
                curve.setSymbolSize(7)
                curve.setSymbolBrush(color)
                curve.setSymbolPen(pg.mkPen(Color.SURFACE, width=1))
            else:
                curve.setPen(pg.mkPen(color, width=2.0))
                curve.setSymbol(None)

    def _update_header(self) -> None:
        self.set_header(self.title, (*_CHAINS[:self.chains], _MOVING, _MEAN, _RAW))

    # ------------------------------------------------------------ ข้อมูล
    def begin_session(self, config):
        self._set_target(config)
        self._update_header()
        super().begin_session(config)

    def consume(self, result):
        interval = result.interval
        if interval is None:
            return False
        self._chains[interval.chain].append(interval.t, interval.flow, interval.duration_s)
        self._max_t = max(self._max_t, interval.t)
        # ค่าเฉลี่ยสะสมตั้งแต่ช่วงแรก (ทุกสายรวมกันตามลำดับที่จบ)
        self._sum += interval.flow
        self._sum_raw += interval.flow_raw
        self._count += 1
        self._moving.append(interval.t, self._sum / self._count, self._sum_raw / self._count)
        if result.stats is not None:
            self._mean = result.stats.mean_flow
        return True

    def redraw(self):
        step = self.ui.interval_style == "step"
        for key, curve, chain in zip(("a", "b"), self._curves, self._chains):
            end, flow = chain.column(0), chain.column(1)
            visible = self.series_visible(key) and len(end) > 0
            curve.setVisible(visible)
            if not visible:
                continue
            if step:
                start = end - chain.column(2)
                # แต่ละช่วง = เส้นแนวนอนจากต้นถึงปลายช่วง ต่อกันเป็นขั้นบันได
                curve.setData(np.column_stack((start, end)).ravel(), np.repeat(flow, 2))
            else:
                curve.setData(end, flow)
        moving_on = self.series_visible("moving") and len(self._moving) > 0
        self._moving_curve.setVisible(moving_on)
        if moving_on:
            self._moving_curve.setData(self._moving.column(0), self._moving.column(1))
        raw_on = self.series_visible("raw") and len(self._moving) > 0
        self._raw_curve.setVisible(raw_on)
        if raw_on:
            self._raw_curve.setData(self._moving.column(0), self._moving.column(2))
        mean_on = self.series_visible("mean") and self._mean is not None
        self._mean_line.setVisible(mean_on)
        if mean_on:
            self._mean_line.setValue(self._mean)
        shown = [v for chain in self._chains for v in chain.column(1)]
        if raw_on:
            shown.extend(self._moving.column(2))
        self._fit_y(shown)
        if self.current_range_mode() == "full":
            # แกนเวลาขยายเป็นขั้นละ 1 นาที
            self.plot.setXRange(0, (int(self._max_t / 60) + 1) * 60, padding=0.02)
        else:
            self._roll_x(self._max_t)

    def reset(self):
        for chain in self._chains:
            chain.clear()
        self._moving.clear()
        self._sum, self._sum_raw, self._count = 0.0, 0.0, 0
        self._mean = None
        self._max_t = 0.0
