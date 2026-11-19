"""วิธี pump_cycle: แบ่งช่วงวัดตามรอบของ finger pump (peak-to-peak)

จับรอบคู่ (cycle_chains = 2, ค่าเริ่มต้น): สาย A = peak -> peak (TOP) · สาย B = valley -> valley (DOWN)
จบการทดสอบเมื่อทั้งสองสายครบเวลา หรือครบจำนวนรอบที่ตั้ง
จับรอบเดียว (cycle_chains = 1): ใช้เฉพาะสาย A — รอบของอีกชนิดถูกข้าม ไม่เป็นช่วงวัด
เหมาะกับ infusion pump ที่ flow แกว่งเป็นรอบ

ตัวจับจุดกลับตัว: ล็อกคาบ (core/phase_lock.py) — engine ส่งคาบที่เชื่อถือได้มาทาง set_period()
สายผูกกับชนิดจุดตายตัว: สาย A = peak (TOP) เสมอ (ผู้ใช้ 2026-11-19: "peak แรกเป็นจุด start" · เดิมสาย A = ชนิดที่เจอก่อน
ซึ่งอาจเป็น valley) · origin_t = เวลาของ peak แรกของสาย A — เวลา 0 ของช่วงวัด กราฟ และใบรายงาน
"""
from __future__ import annotations

from core.cycle_analyzer import DOWN, TOP
from core.phase_lock import PhaseLockedAnalyzer
from core.models import Cumulative, EndMode, EngineResult, ExtremumPoint
from core.strategies.base import STRATEGIES, FlowStrategy


CHAIN_OF_KIND = {TOP: 0, DOWN: 1}       # สาย A = peak -> peak · สาย B = valley -> valley


@STRATEGIES.register("pump_cycle", label="Pump cycle (peak-to-peak)")
class PumpCycleStrategy(FlowStrategy):
    uses_cycles = True
    end_modes = ("time", "count")

    def __init__(self, config, settings):
        super().__init__(config, settings)
        self._analyzer = PhaseLockedAnalyzer(n_bar=settings.cycle_half_window)
        self._anchors: dict[int, tuple[float, float]] = {}   # สาย -> (t, weight) จุดเริ่มของสาย
        self._chains = 1 if getattr(settings, "cycle_chains", 2) == 1 else 2
        self._chain_done = [False, False]
        self._chain_cycles = [0, 0]

    def set_period(self, period_s: float | None, trusted: bool = False) -> None:
        """คาบรอบปั๊มที่เชื่อถือได้ (วัดก่อนเริ่ม / โปรไฟล์ที่วัดจริง) — เรียกก่อนป้อนข้อมูล · None = ให้หาเอง
        trusted = วัดจากปั๊มตัวนี้ในช่วงก่อนวัดของการทดสอบนี้เอง (ล็อกทันที)"""
        self._analyzer = PhaseLockedAnalyzer(n_bar=self.settings.cycle_half_window, period_s=period_s,
                                             trusted=trusted)

    @property
    def origin_t(self) -> float | None:
        """เวลา (นับจากเริ่มวัด) ของจุดเริ่มสาย A = peak แรกที่ใช้เป็นเวลา 0"""
        return self._anchors[0][0] if 0 in self._anchors else None

    @property
    def lock_period_s(self) -> float | None:
        return self._analyzer.period_s

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
        chain = CHAIN_OF_KIND[end.kind]
        if chain >= self._chains:           # จับรอบเดียว: รอบของสาย B (valley) ไม่นับ
            return
        self._anchors.setdefault(chain, (start.t, start.weight))
        since_anchor = max(0.0, end.t - self._anchors[chain][0])
        self._chain_cycles[chain] += 1
        if self.config.end_mode is EndMode.COUNT:
            done = self._chain_cycles[chain] >= self.config.cycle_count
        else:       # ครบเวลาแล้วยังไม่ตัด จนกว่ารอบปั๊มรอบนี้จะจบจริง (เราอยู่ที่ปลายรอบพอดี)
            done = since_anchor >= self.config.duration_s
        if done:
            self._chain_done[chain] = True

        # เวลาของช่วงวัด = นับจาก peak แรกของสาย A (เวลา 0 ร่วมกันทุกสาย — เดิมสาย B นับจากจุดเริ่มของสาย B เอง)
        origin = self._anchors.get(0, self._anchors[chain])[0]     # สาย B ครบก่อนสาย A: นับจากจุดเริ่มของตัวเองไปก่อน
        result.interval = self._make_interval(
            chain=chain, t=max(0.0, end.t - origin),
            duration=max(0.0, end.t - start.t),
            delta_weight=end.weight - start.weight,
            start=(start.t, start.weight), end=(end.t, end.weight),
        )

    def _cumulative(self, t: float, weight: float) -> Cumulative | None:
        if 0 not in self._anchors:
            return None
        flow = lambda chain: (self._flow(weight - self._anchors[chain][1], t - self._anchors[chain][0]) or None) \
            if chain in self._anchors else None     # noqa: E731
        flow_a, flow_b = flow(0), flow(1)
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
        slowest = min(t - t0 for t0, _ in self._anchors.values())
        return max(0.0, min(1.0, slowest / self.config.duration_s))
