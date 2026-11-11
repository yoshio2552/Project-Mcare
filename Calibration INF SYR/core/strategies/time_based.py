"""วิธีจับตามเวลา (ไม่พึ่งการจับรอบปั๊ม — เหมาะกับ syringe pump ที่ flow เรียบ)

time_interval : แบ่งเวลาทดสอบเป็นช่วงยาวเท่ากัน (เช่น ทุก 30 วินาที) ได้สถิติรายช่วง
time_total    : วัดรวดเดียวทั้งช่วงเวลาทดสอบ ได้ค่าเดียว
"""
from __future__ import annotations

from core.models import Cumulative, EngineResult
from core.strategies.base import STRATEGIES, FlowStrategy


@STRATEGIES.register("time_interval", label="Time, split into intervals")
class TimeIntervalStrategy(FlowStrategy):
    uses_window = True

    def __init__(self, config, settings):
        super().__init__(config, settings)
        self._anchor: tuple[float, float] | None = None        # จุดเริ่มการทดสอบ
        self._window_start: tuple[float, float] | None = None  # จุดเริ่มของช่วงปัจจุบัน
        self._window_s = self._window_length()
        self._target_count = max(1, round(config.duration_s / self._window_s))

    def _window_length(self) -> float:
        return max(1.0, min(self.config.window_s, self.config.duration_s))

    def update(self, t, weight, slope_flow, result: EngineResult) -> None:
        if self._anchor is None:
            self._anchor = self._window_start = (t, weight)
            return

        t0, w0 = self._anchor
        elapsed = t - t0
        ws_t, ws_w = self._window_start
        if t - ws_t >= self._window_s - 1e-9:
            result.interval = self._make_interval(
                chain=0, t=elapsed, duration=t - ws_t, delta_weight=weight - ws_w,
            )
            self._window_start = (t, weight)

        flow = self._flow(weight - w0, elapsed) or None
        result.cumulative = Cumulative(
            t=elapsed, flow_a=flow, err_a=None if flow is None else self._error(flow),
        )
        result.progress = min(1.0, elapsed / (self._window_s * self._target_count))
        result.finished = self._interval_count >= self._target_count


@STRATEGIES.register("time_total", label="Time, single measurement")
class TimeTotalStrategy(TimeIntervalStrategy):
    uses_window = False

    def _window_length(self) -> float:
        return max(1.0, self.config.duration_s)
