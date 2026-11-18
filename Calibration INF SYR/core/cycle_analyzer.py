"""ตัวจับรอบการทำงานของ finger pump จากจุด peak/valley ของ slope (Zigzag)

หลักการ: เก็บหน้าต่างกว้าง 2*n_bar+1 จุด ถ้าจุดกึ่งกลางเป็นค่าสูงสุด/ต่ำสุดของ
หน้าต่าง = จุดกลับตัว "ผู้สมัคร" (TOP/DOWN) แล้วบังคับให้ TOP กับ DOWN สลับกันเสมอ
1 รอบ (cycle) = TOP->TOP หรือ DOWN->DOWN ที่อยู่ติดกัน

กันการจับ "คลื่นเล็ก" ในรอบเดียวกัน (ปั๊มหลายรุ่นมียอดรองระหว่างยอดหลัก) 2 ชั้น:
  1) รอยืนยัน: ผู้สมัครยังไม่ถูกรายงานจนกว่าจะเจอจุดกลับตัวชนิดตรงข้าม — ระหว่างรอ ถ้าเจอชนิดเดิม
     ที่ดีกว่า (TOP สูงกว่า / DOWN ลึกกว่า) จะแทนผู้สมัครเดิม
     เดิม: รายงานยอดแรกทันที พอยอดจริงตามมาก็แก้ไม่ได้แล้ว -> ได้รอบสั้นผิดปกติ 1 รอบ + น้ำหนักช่วงนั้นหาย
     (ข้อมูลจริง LM730 50 ml/h 2026-11-17: n_bar 0.36 x คาบ ได้รอบ 5.5 s ปนกับรอบจริง 14.1 s)
  2) เกณฑ์แอมพลิจูด: จุดชนิดตรงข้ามต้องห่างจากผู้สมัครอย่างน้อย MIN_SWING_FRACTION ของช่วงแกว่งเต็ม
     (สูงสุด − ต่ำสุดของ slope ใน SWING_WINDOWS หน้าต่างล่าสุด) ไม่งั้นถือเป็นคลื่นเล็ก ข้ามไป
ผลข้างเคียงที่ตั้งใจ: จุดกลับตัวถูกรายงานช้าลงราวครึ่งรอบ (เวลา/น้ำหนักของจุดไม่เปลี่ยน)
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


MIN_SWING_FRACTION = 0.5    # ข้อมูลจริง 8 รุ่น/ชุดสาย: ยอดรองแกว่งไม่เกิน ~0.3 ของช่วงเต็ม ยอดหลัก ~1.0
SWING_WINDOWS = 3           # ช่วงแกว่งเต็มดูจากกี่หน้าต่างล่าสุด (>= 1 คาบ แม้ n_bar = 0.2 x คาบ)


class CycleAnalyzer:
    def __init__(self, n_bar: int = 50, min_swing_fraction: float = MIN_SWING_FRACTION):
        self.n_bar = n_bar
        self.window_size = 2 * n_bar + 1
        self.min_swing_fraction = min_swing_fraction
        self._time: deque[float] = deque(maxlen=self.window_size)
        self._weight: deque[float] = deque(maxlen=self.window_size)
        self._slope: deque[float] = deque(maxlen=self.window_size)
        self._recent: deque[float] = deque(maxlen=self.window_size * SWING_WINDOWS)
        self._last = {TOP: None, DOWN: None}     # จุดกลับตัวที่ "ยืนยันแล้ว" ล่าสุดของแต่ละชนิด
        self._pending: Extremum | None = None    # ผู้สมัครที่รอจุดชนิดตรงข้ามมายืนยัน
        self._last_time: float | None = None

    def update(self, t: float, weight: float, slope: float) -> CycleEvent | None:
        """ป้อนข้อมูลทีละจุด คืน CycleEvent เมื่อ "ยืนยัน" จุดกลับตัวได้ (ช้ากว่าเวลาของจุดราวครึ่งรอบ)"""
        self._time.append(t)
        self._weight.append(weight)
        self._slope.append(slope)
        self._recent.append(slope)
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
        pending = self._pending
        if pending is None:
            self._pending = point
            return None

        if kind == pending.kind:
            # ชนิดเดิมซ้ำก่อนเจอชนิดตรงข้าม: เก็บตัวที่ดีกว่า (TOP สูงกว่า, DOWN ลึกกว่า) เป็นผู้สมัคร
            better = point.slope > pending.slope if kind == TOP else point.slope < pending.slope
            if better:
                self._pending = point
            return None

        swing = max(self._recent) - min(self._recent)
        if abs(point.slope - pending.slope) < self.min_swing_fraction * swing:
            return None                          # คลื่นเล็กในรอบเดียวกัน — ไม่ใช่จุดกลับตัวของรอบปั๊ม

        # เจอชนิดตรงข้ามที่แกว่งมากพอ -> ผู้สมัครเดิมได้รับการยืนยัน
        previous_same_kind = self._last[pending.kind]
        cycle = Cycle(start=previous_same_kind, end=pending) if previous_same_kind is not None else None
        self._last[pending.kind] = pending
        self._pending = point
        return CycleEvent(point=pending, cycle=cycle)
