"""วิธี pump_cycle: แบ่งช่วงวัดตามรอบของ finger pump (peak-to-peak)

จับรอบคู่ (cycle_chains = 2, ค่าเริ่มต้น): 2 สายสลับกัน สาย A ยึดจุดกลับตัวชนิดแรกที่เจอ (เช่น TOP->TOP)
สาย B ยึดอีกชนิด (DOWN->DOWN) จบการทดสอบเมื่อทั้งสองสายครบเวลา หรือครบจำนวนรอบที่ตั้ง
จับรอบเดียว (cycle_chains = 1): ใช้เฉพาะสาย A — รอบของอีกชนิดถูกข้าม ไม่เป็นช่วงวัด
เหมาะกับ infusion pump ที่ flow แกว่งเป็นรอบ
"""
from __future__ import annotations

from core.cycle_analyzer import CycleAnalyzer
from core.models import Cumulative, EndMode, EngineResult, ExtremumPoint
from core.strategies.base import STRATEGIES, FlowStrategy


@STRATEGIES.register("pump_cycle", label="Pump cycle (peak-to-peak)")
class PumpCycleStrategy(FlowStrategy):
    uses_cycles = True
    end_modes = ("time", "count")

    def __init__(self, config, settings):
        super().__init__(config, settings)
        self._analyzer = CycleAnalyzer(n_bar=settings.cycle_half_window)
        self._anchors: list[tuple[float, float]] = []   # (t, weight) จุดเริ่มของสาย A, B
        self._chains = 1 if getattr(settings, "cycle_chains", 2) == 1 else 2
        self._chain_done = [False, False]
        self._chain_cycles = [0, 0]
        self._next_chain = 0

    def update(self, t, weight, slope_flow, result: EngineResult) -> None:
        event = self._analyzer.update(t, weight, slope_flow)
        if event is not None:
            point = event.point
            result.extremum = ExtremumPoint(point.t, point.slope, point.kind)
            if event.cycle is not None:
                self._on_cycle(event.cycle, result)

        result.cumulative = self._cumulative(t, weight)
        result.progress = self._progress(t)
        result.finished = all(self._chain_done[:self._chains])

    def _on_cycle(self, cycle, result: EngineResult) -> None:
        start, end = cycle.start, cycle.end
        chain = self._next_chain
        self._next_chain ^= 1
        if chain >= self._chains:           # จับรอบเดียว: รอบของสาย B ไม่นับ
            return
        if len(self._anchors) < self._chains:
            self._anchors.append((start.t, start.weight))
        since_anchor = max(0.0, end.t - self._anchors[chain][0])
        self._chain_cycles[chain] += 1
        if self.config.end_mode is EndMode.COUNT:
            done = self._chain_cycles[chain] >= self.config.cycle_count
        else:       # ครบเวลาแล้วยังไม่ตัด จนกว่ารอบปั๊มรอบนี้จะจบจริง (เราอยู่ที่ปลายรอบพอดี)
            done = since_anchor >= self.config.duration_s
        if done:
            self._chain_done[chain] = True

        result.interval = self._make_interval(
            chain=chain, t=since_anchor,
            duration=max(0.0, end.t - start.t),
            delta_weight=end.weight - start.weight,
        )

    def _cumulative(self, t: float, weight: float) -> Cumulative | None:
        if not self._anchors:
            return None
        flows = [self._flow(weight - w0, t - t0) for t0, w0 in self._anchors]
        flow_a = flows[0] or None
        flow_b = (flows[1] or None) if len(flows) > 1 else None
        flow_all = (flow_a + flow_b) / 2.0 if flow_a and flow_b else None
        err = lambda flow: None if flow is None else self._error(flow)
        return Cumulative(
            t=max(0.0, t - self._anchors[0][0]),
            flow_a=flow_a, flow_b=flow_b, flow_all=flow_all,
            err_a=err(flow_a), err_b=err(flow_b), err_all=err(flow_all),
        )

    def _progress(self, t: float) -> float:
        if self.config.end_mode is EndMode.COUNT:
            return min(1.0, min(self._chain_cycles[:self._chains]) / max(1, self.config.cycle_count))
        if len(self._anchors) < self._chains or self.config.duration_s <= 0:
            return 0.0
        slowest = min(t - t0 for t0, _ in self._anchors)
        return max(0.0, min(1.0, slowest / self.config.duration_s))
