"""ตัวจับรอบการทำงานของ finger pump จากจุด peak/valley ของ slope (Zigzag)

หลักการ: เก็บหน้าต่างกว้าง 2*n_bar+1 จุด ถ้าจุดกึ่งกลางเป็นค่าสูงสุด/ต่ำสุดของ
หน้าต่าง = เจอ TOP/DOWN แล้วบังคับให้ TOP กับ DOWN สลับกันเสมอ
1 รอบ (cycle) = TOP->TOP หรือ DOWN->DOWN ที่อยู่ติดกัน
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

TOP = "TOP"
DOWN = "DOWN"


@dataclass(frozen=True, slots=True)
class Extremum:
    t: float
    weight: float
    slope: float
    kind: str


@dataclass(frozen=True, slots=True)
class Cycle:
    start: Extremum
    end: Extremum

    @property
    def pattern(self) -> str:
        return "TOP-DOWN-TOP" if self.end.kind == TOP else "DOWN-TOP-DOWN"


@dataclass(frozen=True, slots=True)
class CycleEvent:
    point: Extremum
    cycle: Cycle | None = None


class CycleAnalyzer:
    def __init__(self, n_bar: int = 50):
        self.n_bar = n_bar
        self.window_size = 2 * n_bar + 1
        self._time: deque[float] = deque(maxlen=self.window_size)
        self._weight: deque[float] = deque(maxlen=self.window_size)
        self._slope: deque[float] = deque(maxlen=self.window_size)
        self._last = {TOP: None, DOWN: None}     # extremum ล่าสุดของแต่ละชนิด
        self._last_kind: str | None = None
        self._last_time: float | None = None

    def update(self, t: float, weight: float, slope: float) -> CycleEvent | None:
        """ป้อนข้อมูลทีละจุด คืน CycleEvent เมื่อยืนยันจุดกลับตัวใหม่ได้"""
        self._time.append(t)
        self._weight.append(weight)
        self._slope.append(slope)
        if len(self._slope) < self.window_size:
            return None

        center = self._slope[self.n_bar]
        highest, lowest = max(self._slope), min(self._slope)
        if highest == lowest:                    # เส้นราบทั้งหน้าต่าง ไม่มีจุดกลับตัว
            return None
        if center != highest and center != lowest:
            return None

        center_time = self._time[self.n_bar]
        if center_time == self._last_time:
            return None
        self._last_time = center_time

        kind = TOP if center == highest else DOWN
        point = Extremum(center_time, self._weight[self.n_bar], center, kind)

        if kind == self._last_kind:
            # ชนิดซ้ำกับจุดก่อนหน้า: ไม่รายงาน แต่อาจเลื่อนจุดอ้างอิงไปยังจุดที่ดีกว่า
            # เทียบด้วย slope: TOP เก็บยอดที่สูงกว่า, DOWN เก็บก้นที่ลึกกว่า
            previous = self._last[kind]
            if previous is not None:
                better = point.slope > previous.slope if kind == TOP else point.slope < previous.slope
                if better:
                    self._last[kind] = point
            return None

        previous_same_kind = self._last[kind]
        cycle = None
        if self._last_kind is not None and previous_same_kind is not None:
            cycle = Cycle(start=previous_same_kind, end=point)
        self._last[kind] = point
        self._last_kind = kind
        return CycleEvent(point=point, cycle=cycle)
