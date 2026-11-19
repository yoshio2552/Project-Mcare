"""ตัวจับรอบปั๊มแบบ "ล็อกคาบ" (phase-locked) — ทนต่อปั๊มที่มีหลายจังหวะต่อรอบ ทุก rate

ปัญหาของตัวจับแบบหน้าต่าง (core/cycle_analyzer.py): ปั๊มหลายรุ่นมียอดรอง 1–3 ยอดในรอบเดียว (LM730, LF-730)
ถ้าหน้าต่าง n̄ แคบกว่าระยะถึงยอดหลักข้างเคียง ยอดรองจะถูกนับเป็นจุดกลับตัว -> รอบถูกแบ่งเป็นสองท่อน
(ข้อมูลจริง LF-730 50 ml/h 2026-11-19: รอบ 14.1 s ถูกแบ่งเป็น 8.2 + 5.7 s)

หลักการ: รู้คาบ P ที่แม่นแล้ว จุดกลับตัวถัดไปของชนิดเดียวกัน "ต้อง" อยู่ห่างจากจุดก่อนราว 1 คาบ
    0) ปรับคาบจากรูปคลื่นเอง: สหสัมพันธ์ (Pearson) ของ slope กับตัวมันเองที่เลื่อนไป L — รูปคลื่นทั้งรอบ
       (ทุกชั้นรวมกัน) ซ้อนทับตัวเองดีที่สุดที่ L = 1 คาบจริง ยอดรองทำให้ L = ครึ่งคาบซ้อนได้แค่บางส่วน
       · รู้คาบตั้งต้น (วัดก่อนเริ่ม / โปรไฟล์): ค้นใน 0.65–1.5 เท่า แก้คาบตั้งต้นที่คลาดได้ถึง ±30 %
       · ไม่รู้คาบ: ตัวจับแบบหน้าต่างเดิมให้คาบหยาบ (อาจได้ครึ่งคาบหรือสองเท่า) แล้วค้นใน 0.4–2.5 เท่า
       · เลือกยอดที่ lag สั้นสุดที่สูงเกือบเท่ายอดสูงสุด (≥ 0.9) — กันได้ 2–3 เท่าของคาบ (TE-112 ซ้อนที่ 3 คาบได้ดีพอๆ กัน)
       · ไม่รู้คาบแล้วได้ครึ่งคาบของยอดคู่: ยอดชนิดเดียวกันจะสลับสูง-ต่ำ -> ตรวจก่อนปล่อยช่วงวัด แล้วใช้ 2 เท่า
    1) จุดแรก (seed): ค่าสูงสุด (TOP) / ต่ำสุด (DOWN) ของ slope ในช่วง 1 คาบเต็ม (ยอดหลักของรอบ)
    2) จุดถัดไป: ยอดเฉพาะที่ในช่วง [0.6P, 1.5P] หลังจุดก่อน คะแนน = ความสูง − โทษที่ห่างจาก 1 คาบ
       ยอดรองอยู่ผิดจังหวะ (ห่างยอดหลักไม่ถึง 0.8P) จึงแพ้ยอดหลักที่ตรงจังหวะ แม้จะสูงเกือบเท่ากัน ไม่ว่ากี่ชั้น
    3) ไม่มียอดเฉพาะที่ (ข้อมูลเรียบ) -> ค่าสูงสุดใน [0.8P, 1.25P] ไต่ตามได้ถึง [0.6P, 1.5P]
    4) P ปรับตามค่ากลางของรอบล่าสุด (≤ 9 รอบ) จำกัดไว้ 0.7–1.4 เท่าของคาบที่ปรับแล้ว
ผลคือ: รอบสั้นกว่า 0.6P หรือยาวกว่า 1.5P เกิดไม่ได้ และทุกช่วงวัดเริ่ม-จบที่จังหวะเดียวกันของรอบปั๊ม

ระหว่างยังไม่ได้คาบที่ปรับแล้ว: ไม่มีจุด/ช่วงวัด (ไม่เดา) — ได้คาบแล้วจึงล็อกย้อนจากต้นข้อมูลทันที (ไม่เสียรอบช่วงต้น)
· คาบที่เพิ่งวัดก่อนเริ่ม (ข้อมูลปั๊มตัวนี้ ณ ตอนนี้): ล็อกทันที · คาบจากโปรไฟล์ (การทดสอบก่อน): รอข้อมูล REFINE_SPAN คาบ
  แล้วปรับก่อน (ชุดสาย/เครื่องอาจต่างจากเดิม) · ไม่รู้คาบ: ทางใดทางหนึ่งก่อน — ตัวจับแบบหน้าต่างได้ MIN_CYCLES_TO_LOCK รอบ
  แล้วปรับ / ค้นคาบตรงจากรูปคลื่นได้ค่าเดิม 2 ครั้งติด (หน้าต่าง n̄ ที่เดามากว้างเกินคาบจะหาจุดไม่ได้เลย)
จุดถูกรายงานหลังเกิดจริงราว 0.5P (เวลา/น้ำหนักของจุดไม่เปลี่ยน — ตัวจับเดิมก็ช้าราวครึ่งรอบ)
ทดสอบ: raw จริง 49 ไฟล์ (8 รุ่น 10–200 ml/h) + สัญญาณจำลองหลายชั้น (tests/test_phase_lock.py) — HISTORY 6.16
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import deque
from statistics import median

import numpy as np

from core.cycle_analyzer import DOWN, TOP, Cycle, CycleAnalyzer, CycleEvent, Extremum

LOCK_CORE = (0.8, 1.25)         # ช่วงที่หาจุดถัดไป (เท่าของคาบ)
LOCK_REACH = (0.6, 1.5)         # ไต่ตามยอดที่ติดขอบได้ไกลสุด
SEED_CORE = (0.25, 1.25)        # จุดแรก: 1 คาบเต็ม ไม่ชิดจุดเริ่ม (ช่วงต้นอาจกำลังลง/ขึ้นจากรอบก่อน)
SEED_REACH = (0.0, 1.5)
PERIOD_LIMITS = (0.7, 1.4)      # คาบที่ปรับเองตามรอบล่าสุด เทียบคาบที่ปรับจากรูปคลื่น
PERIOD_MEMORY = 9               # ค่ากลางของกี่รอบล่าสุด
REFINE_SPAN = 3.2               # รู้คาบตั้งต้น: รอข้อมูลกี่คาบก่อนปรับคาบ + ล็อก (ต้อง > 2 × REFINE_KNOWN[1])
REFINE_KNOWN = (0.65, 1.5)      # ช่วงค้นคาบเมื่อรู้คาบตั้งต้น (เท่า)
REFINE_ROUGH = (0.4, 3.2)       # ช่วงค้นคาบจากคาบหยาบของตัวจับแบบหน้าต่าง (หยาบอาจได้ 1/3–2 เท่าของคาบจริง)
MIN_CORRELATION = 0.3           # สหสัมพันธ์ต่ำกว่านี้ = รูปคลื่นไม่เป็นรอบพอจะเชื่อ
MIN_CYCLES_TO_LOCK = 3          # ไม่รู้คาบ: ต้องได้กี่รอบจากตัวจับแบบหน้าต่างก่อนปรับคาบ
BLIND_EVERY = 25                # ไม่รู้คาบ: ค้นคาบตรงจากรูปคลื่นทุกกี่จุด (ไม่พึ่งหน้าต่าง n̄ ที่อาจกว้าง/แคบเกิน)
BLIND_CORRELATION = 0.5         # ค้นตรงต้องซ้อนได้อย่างน้อยเท่านี้ และได้ค่าเดิม 2 ครั้งติด (±5 %)
MIN_REFINE_POINTS = 100         # ปรับคาบด้วยข้อมูลอย่างน้อยกี่จุด (rate สูง 10 จุดต่อรอบ: 3 คาบสั้นเกินจะเชื่อ)
VERIFY_POINTS = 6               # ไม่รู้คาบ: ถือช่วงวัดไว้จนได้จุดชนิดละเท่านี้ แล้วตรวจว่ายอด "สลับสูง-ต่ำ" ไหม
STRONG_FRACTION = 0.9           # ยอดสหสัมพันธ์ที่ "สูงเกือบเท่า" ยอดสูงสุด — เลือก lag สั้นสุดในกลุ่มนี้
DISTANCE_PENALTY = 0.5          # โทษต่อระยะห่างจาก 1 คาบ (เท่าของช่วงแกว่งต่อ 1 คาบ): ห่างครึ่งคาบ = −25 % ของช่วงแกว่ง
FIT_RANGE = (0.75, 1.33)        # รอบช่วงต้นที่ยาวนอกช่วงนี้ (เท่าของค่ากลางรอบถัดไป) ถูกทิ้งก่อนปล่อย
ALTERNATION_F = 12.0            # ค่า F (ระหว่างกลุ่มคู่/คี่ ÷ ภายในกลุ่ม) ที่ถือว่าสลับจริง = ได้ครึ่งคาบ -> ใช้ 2 เท่า
MAX_UNLOCKED_POINTS = 12000     # ข้อมูลที่เก็บไว้ระหว่างยังไม่ล็อก (~40 นาทีที่ 5 Hz)


class _Track:
    """ตัวติดตามจุดกลับตัว 1 ชนิด (TOP หรือ DOWN)"""
    __slots__ = ("kind", "sign", "last", "seed_from")

    def __init__(self, kind: str):
        self.kind = kind
        self.sign = 1.0 if kind == TOP else -1.0
        self.last: Extremum | None = None
        self.seed_from: float | None = None


class PhaseLockedAnalyzer:
    """ใช้แทน CycleAnalyzer ได้ (update คืน CycleEvent | None — เหตุการณ์ที่เกิดพร้อมกันทยอยออกทีละจุด)"""

    def __init__(self, n_bar: int = 50, period_s: float | None = None, trusted: bool = False):
        """period_s = คาบตั้งต้น · trusted = วัดจากข้อมูลชุดนี้เองก่อนเริ่ม (ล็อกทันที ไม่ต้องรอปรับ REFINE_SPAN คาบ)"""
        self._fallback = CycleAnalyzer(n_bar=n_bar)
        self.given_period_s = period_s if period_s and period_s > 0 else None
        self.trusted = bool(trusted and self.given_period_s)
        self.period_s: float | None = None          # คาบที่ใช้ล็อก (หลังปรับจากรูปคลื่น)
        self.locked_period_s: float | None = None   # คาบตอนเริ่มล็อก (ฐานของ PERIOD_LIMITS)
        self.correlation: float | None = None       # สหสัมพันธ์ที่คาบนั้น (บอกความน่าเชื่อ)
        self.mode = "search"
        self._t: list[float] = []
        self._w: list[float] = []
        self._s: list[float] = []
        self._tracks = {TOP: _Track(TOP), DOWN: _Track(DOWN)}
        self._durations: deque[float] = deque(maxlen=PERIOD_MEMORY)
        self._rough: dict[str, list[float]] = {}    # เวลาจุดของตัวจับแบบหน้าต่าง (หาคาบหยาบ)
        self._blind_previous: float | None = None
        self._queue: deque[CycleEvent] = deque()
        self._held: list[CycleEvent] | None = None  # ไม่รู้คาบ: ช่วงวัดชุดแรกที่ถือไว้รอตรวจ (None = ไม่ถือ/ปล่อยแล้ว)
        self._verify = False
        self._accepted = {TOP: 0, DOWN: 0}          # รอบที่ผ่านการตรวจรอบนำหน้าแล้ว ต่อชนิด
        self._doubled = False

    # ------------------------------------------------------------ สาธารณะ
    def update(self, t: float, weight: float, slope: float) -> CycleEvent | None:
        self._t.append(t)
        self._w.append(weight)
        self._s.append(slope)
        if self.mode == "search":
            self._search(t, weight, slope)
        if self.mode == "lock":
            while any([self._advance(track, t) for track in self._tracks.values()]):
                pass                            # ล็อกย้อนจากต้นข้อมูล: เดินจนทันเวลาปัจจุบัน
            self._trim()
        return self._queue.popleft() if self._queue else None

    # ------------------------------------------------------------ หาคาบก่อนล็อก
    def _search(self, t: float, weight: float, slope: float) -> None:
        if len(self._t) > MAX_UNLOCKED_POINTS:
            self._drop(len(self._t) - MAX_UNLOCKED_POINTS // 2)
        if self.trusted:                        # คาบที่เพิ่งวัดจากปั๊มตัวนี้ (ช่วงก่อนวัด) — ไม่ต้องรอ
            self._lock(self.given_period_s)
            return
        if self.given_period_s:
            if t - self._t[0] < REFINE_SPAN * self.given_period_s or len(self._t) < MIN_REFINE_POINTS:
                return
            period = self._refine(self.given_period_s, REFINE_KNOWN) or self.given_period_s
            self._lock(period)
            return
        if len(self._t) % BLIND_EVERY == 0:
            period = self._blind_scan()
            if period is not None:
                self._lock(period, verify=True)
                return
        event = self._fallback.update(t, weight, slope)
        if event is None:
            return
        times = self._rough.setdefault(event.point.kind, [])
        times.append(event.point.t)
        durations = [b - a for series in self._rough.values() for a, b in zip(series, series[1:])]
        if len(durations) < MIN_CYCLES_TO_LOCK:
            return
        period = self._refine(median(durations), REFINE_ROUGH)
        if period is not None:
            self._lock(period, verify=True)

    def _blind_scan(self) -> float | None:
        """ค้นคาบจากรูปคลื่นตรงๆ (ทางสำรอง ไม่พึ่งตัวจับแบบหน้าต่าง): ค่าสูงสุดของสหสัมพันธ์ ตั้งแต่จุดตัดศูนย์แรก
        ถึง 1/3 ของข้อมูล — ต้องดูได้ไกล 3 เท่าของค่าที่พบ และได้ค่าใกล้เดิม 2 ครั้งติดกัน (ช้ากว่าทางแรก แต่ไม่พลาด)"""
        times, values = np.asarray(self._t), np.asarray(self._s, dtype=float)
        n = len(values)
        if n < 60:
            return None
        dt = float(np.median(np.diff(times)))
        high = n // 3
        rho = _lag_correlation(values, high + 1)
        negative = np.flatnonzero(rho < 0)
        if dt <= 0 or not len(negative) or high - negative[0] < 3:
            return None
        inner = [k for k in range(int(negative[0]) + 1, high) if rho[k] >= rho[k - 1] and rho[k] > rho[k + 1]]
        best = _first_strong(rho, inner) if inner else high
        # ต้องดูได้ไกลอย่างน้อย 3 เท่าของค่าที่พบ: ไม่งั้นค่าที่พบอาจเป็นแค่ 1/2 หรือ 1/3 ของคาบจริง (ยอดรอง)
        if 3 * best > high or rho[best] < BLIND_CORRELATION:
            self._blind_previous = None
            return None
        period = best * dt
        previous, self._blind_previous = self._blind_previous, period
        if previous is None or abs(period - previous) > 0.05 * period:
            return None
        self.correlation = float(rho[best])
        return period

    def _lock(self, period: float, verify: bool = False) -> None:
        """เริ่มล็อกที่คาบนี้ ย้อนจากต้นข้อมูล — ถือช่วงวัดชุดแรกไว้ตรวจก่อนปล่อย (_release)
        verify = ตรวจยอดสลับด้วย (คาบที่หาเองโดยไม่มีคาบตั้งต้น — อาจได้ครึ่งคาบ)"""
        self.period_s = self.locked_period_s = period
        self.mode = "lock"
        self._durations.clear()
        self._held = [] if verify else None
        self._verify = verify
        self._accepted = {TOP: 0, DOWN: 0}
        for track in self._tracks.values():
            track.last, track.seed_from = None, self._t[0]

    def _emit(self, event: CycleEvent) -> None:
        if self._held is None:
            self._queue.append(self._screen_leading(event))
            return
        self._held.append(event)
        self._release()

    def _screen_leading(self, event: CycleEvent) -> CycleEvent:
        """รู้คาบแล้ว: รอบนำหน้าของแต่ละชนิดที่ยาวนอก FIT_RANGE × คาบ ไม่เป็นช่วงวัด (เหลือแค่จุด) — จุดเริ่มสายเลื่อนไป
        จุดถัดไปที่ตรงจังหวะ (จุดแรกอาจตกช่วงที่ปั๊มยังไม่นิ่ง) · ตรวจทันที ไม่ต้องถือไว้ (การ์ด/กราฟไม่ช้าลง)"""
        cycle = event.cycle
        if cycle is None or self._accepted[cycle.end.kind]:
            return event
        ratio = (cycle.end.t - cycle.start.t) / self.period_s
        if not FIT_RANGE[0] <= ratio <= FIT_RANGE[1]:
            return CycleEvent(point=event.point)
        self._accepted[cycle.end.kind] += 1
        return event

    def _release(self) -> None:
        """ไม่รู้คาบ: ปล่อยช่วงวัดชุดแรกเมื่อแต่ละชนิดมีจุดพอ:
        1) ไม่รู้คาบ: ยอดของจุดชนิดเดียวกันสลับสูง-ต่ำเป็นระบบ = ล็อกได้ครึ่งคาบ -> ล็อกใหม่ที่ 2 เท่า (ครั้งเดียว)
        2) รอบช่วงต้นที่ยาวต่างจากค่ากลางของรอบถัดไป (นอก FIT_RANGE) ถูกทิ้ง — จุดแรกอาจตกช่วงที่ปั๊มยังไม่นิ่ง
           (raw จริง LF-600 10 ml/h: รอบแรก 48.9 s จากคาบ 74 s) · ทิ้งเฉพาะรอบนำหน้าที่ติดกัน ไม่ทิ้งกลางสาย
           -> จุดเริ่มสาย (peak แรก = เวลา 0) จึงเป็นจุดแรกที่ตรงจังหวะ"""
        groups = {kind: [e for e in self._held if e.point.kind == kind] for kind in (TOP, DOWN)}
        if min(len(events) for events in groups.values()) < VERIFY_POINTS:
            return
        if not self._doubled and any(
                _alternation_f([e.point.slope for e in events]) > ALTERNATION_F for events in groups.values()):
            self._doubled = True
            self._lock(2.0 * self.period_s, verify=True)
            return
        keep = []
        for events in groups.values():
            cycles = [e for e in events if e.cycle is not None]
            later = [e.cycle.end.t - e.cycle.start.t for e in cycles[1:]]
            middle = median(later) if later else None
            drop = 0
            for event in cycles:
                length = event.cycle.end.t - event.cycle.start.t
                if middle and not FIT_RANGE[0] <= length / middle <= FIT_RANGE[1]:
                    drop += 1
                else:
                    break
            dropped = {id(e) for e in cycles[:drop]}
            keep += [e for e in events if id(e) not in dropped]
        self._held = None
        self._accepted = {kind: 1 for kind in (TOP, DOWN)}     # รอบนำหน้าตรวจแล้วข้างบน
        self._queue.extend(sorted(keep, key=lambda e: e.point.t))

    def _refine(self, guess: float, span: tuple[float, float]) -> float | None:
        """คาบที่รูปคลื่น slope ซ้อนทับตัวเองดีที่สุด ในช่วง span × guess — None = ไม่ชัดพอ/ข้อมูลยังไม่พอ

        ใช้เฉพาะยอดเฉพาะที่ภายในช่วง แล้วเลือก lag สั้นสุดที่สูง ≥ 0.9 ของยอดสูงสุด (_first_strong)
        ข้อยกเว้นที่ตั้งใจ: ยอดคู่ที่เหมือนกันเกือบทุกส่วน (ห่างครึ่งรอบพอดี) ซ้อนที่ครึ่งคาบได้ดีกว่า -> นับทุกจังหวะเป็นรอบ
        (ครึ่งคาบยาวเท่ากันทุกรอบ ค่าเฉลี่ย flow ไม่เอียง)"""
        times, values = np.asarray(self._t), np.asarray(self._s, dtype=float)
        n = len(values)
        if n < 16:
            return None
        dt = float(np.median(np.diff(times)))
        if dt <= 0:
            return None
        low = max(2, int(span[0] * guess / dt))
        high = int(span[1] * guess / dt) + 2
        if high > n // 2:                       # ยังดูไม่ครบช่วง: คาบจริงอาจอยู่ไกลกว่าที่ดูได้ — รอข้อมูลเพิ่ม
            return None
        rho = _lag_correlation(values, high + 1)
        # ยอดเฉพาะที่ภายในช่วงค้น (ค่าสูงสุดที่ติดขอบ = ยอดจริงอยู่นอกช่วง เช่นครึ่งคาบของยอดคู่ — ไม่ใช่คาบที่ค้น)
        inner = [k for k in range(low + 1, high) if rho[k] >= rho[k - 1] and rho[k] > rho[k + 1]]
        if not inner:
            return None
        best = _first_strong(rho, inner)
        if rho[best] < MIN_CORRELATION:
            return None
        self.correlation = float(rho[best])
        left, mid, right = rho[best - 1], rho[best], rho[best + 1]
        curvature = left - 2 * mid + right
        shift = 0.5 * (left - right) / curvature if curvature < 0 else 0.0
        return (best + shift) * dt

    # ------------------------------------------------------------ ล็อกคาบแล้ว
    def _advance(self, track: _Track, t: float) -> bool:
        """เดิน 1 ก้าว (จุดแรก หรือจุดถัดไป) ถ้าข้อมูลพอ — คืน True เมื่อได้จุดใหม่"""
        period = self.period_s
        if track.last is None:
            start = track.seed_from if track.seed_from is not None else self._t[0]
            if t < start + SEED_REACH[1] * period:
                return False
            point = self._pick(track, start, SEED_CORE, SEED_REACH)
            if point is None:
                track.seed_from = start + period
                return False
            track.last, track.seed_from = point, None
            self._emit(CycleEvent(point=point))
            return True
        if t < track.last.t + LOCK_REACH[1] * period:
            return False
        point = self._pick_next(track)
        if point is None:                       # ข้อมูลขาดช่วง: เริ่มหาจุดแรกใหม่ (ไม่สร้างรอบที่คร่อมช่องว่าง)
            track.last, track.seed_from = None, track.last.t + period
            return False
        cycle = Cycle(start=track.last, end=point)
        track.last = point
        self._learn(cycle.end.t - cycle.start.t)
        self._emit(CycleEvent(point=point, cycle=cycle))
        return True

    def _pick(self, track: _Track, origin: float, core: tuple[float, float],
              reach: tuple[float, float]) -> Extremum | None:
        """ค่าสูงสุด/ต่ำสุดใน core (เท่าของคาบนับจาก origin) — ติดขอบให้ไต่ตามได้ถึง reach"""
        period, times, values, sign = self.period_s, self._t, self._s, track.sign
        r0 = bisect_left(times, origin + reach[0] * period)
        r1 = bisect_right(times, origin + reach[1] * period)
        if core[0] > 0:
            r0 = max(r0, bisect_right(times, origin))
        c0 = max(r0, bisect_left(times, origin + core[0] * period))
        c1 = min(r1, bisect_right(times, origin + core[1] * period))
        if c1 - c0 < 1:
            return None
        best = max(range(c0, c1), key=lambda k: sign * values[k])
        if best == c0:
            while best - 1 >= r0 and sign * values[best - 1] > sign * values[best]:
                best -= 1
        if best == c1 - 1:
            while best + 1 < r1 and sign * values[best + 1] > sign * values[best]:
                best += 1
        return Extremum(times[best], self._w[best], values[best], track.kind)

    def _pick_next(self, track: _Track) -> Extremum | None:
        """จุดถัดไป: ยอดเฉพาะที่ (local max/min) ในช่วง [0.6P, 1.5P] หลังจุดก่อน ให้คะแนน = ความสูง − โทษที่ห่างจาก 1 คาบ
        (DISTANCE_PENALTY × ช่วงแกว่ง × |ระยะ/P − 1|) — ยอดรองที่สูงเกือบเท่ายอดหลักแต่อยู่ผิดจังหวะจึงแพ้ยอดที่ตรงจังหวะ
        ไม่มียอดเฉพาะที่เลย (ข้อมูลเรียบ) -> ค่าสูงสุดในช่วง [0.8P, 1.25P]"""
        period, times, values, sign = self.period_s, self._t, self._s, track.sign
        origin = track.last.t
        r0 = max(bisect_right(times, origin), bisect_left(times, origin + LOCK_REACH[0] * period))
        r1 = bisect_right(times, origin + LOCK_REACH[1] * period)
        if r1 - r0 < 3:
            return None
        window = values[max(0, bisect_left(times, origin - period)):r1]
        swing = (max(window) - min(window)) or 1e-12
        best, best_score = None, None
        for k in range(r0 + 1, r1 - 1):
            v = sign * values[k]
            if v < sign * values[k - 1] or v <= sign * values[k + 1]:
                continue                        # ไม่ใช่ยอดเฉพาะที่ (ยอดแบนนับจุดแรก)
            score = v - DISTANCE_PENALTY * swing * abs((times[k] - origin) / period - 1.0)
            if best_score is None or score > best_score:
                best, best_score = k, score
        if best is None:
            return self._pick(track, origin, LOCK_CORE, LOCK_REACH)
        return Extremum(times[best], self._w[best], values[best], track.kind)

    def _learn(self, duration: float) -> None:
        """ปรับคาบตามรอบล่าสุด (ค่ากลาง — รอบเพี้ยนรอบเดียวไม่ลากคาบ)"""
        self._durations.append(duration)
        if len(self._durations) < MIN_CYCLES_TO_LOCK:
            return
        low, high = (f * self.locked_period_s for f in PERIOD_LIMITS)
        self.period_s = min(high, max(low, median(self._durations)))

    # ------------------------------------------------------------ หน่วยความจำคงที่
    def _trim(self) -> None:
        """เก็บเฉพาะข้อมูลที่ยังอาจถูกค้น (ตั้งแต่จุดล่าสุดที่เก่าที่สุดของสองชนิด)"""
        if len(self._t) < 4096:
            return
        keep = []
        for track in self._tracks.values():
            ref = track.last.t if track.last is not None else track.seed_from
            if ref is None:
                return
            keep.append(ref)
        index = bisect_left(self._t, min(keep)) - 1
        if index > 2048:
            self._drop(index)

    def _drop(self, count: int) -> None:
        del self._t[:count], self._w[:count], self._s[:count]


def _first_strong(rho: np.ndarray, peaks: list[int]) -> int:
    """ยอดสหสัมพันธ์ที่ lag สั้นที่สุดที่สูงเกือบเท่ายอดสูงสุด (≥ STRONG_FRACTION) — คาบจริง ไม่ใช่ 2–3 เท่า
    (ข้อมูลจริง TE-112: ซ้อนที่ 3 คาบ 28 s ได้สูงพอๆ กับ 1 คาบ 9.5 s) · ได้ครึ่งคาบของยอดคู่ -> ตรวจยอดสลับแก้ให้"""
    top = max(peaks, key=lambda k: rho[k])
    if rho[top] <= 0:
        return top
    return min(k for k in peaks if rho[k] >= STRONG_FRACTION * rho[top])


def _alternation_f(values: list[float]) -> float:
    """ค่า F ของการแบ่งกลุ่มลำดับคู่/คี่ (ระหว่างกลุ่ม ÷ ภายในกลุ่ม) — สูง = ค่าสลับสูง-ต่ำเป็นระบบ"""
    v = np.asarray(values, dtype=float)
    even, odd = v[0::2], v[1::2]
    if len(even) < 2 or len(odd) < 2:
        return 0.0
    within = (((even - even.mean()) ** 2).sum() + ((odd - odd.mean()) ** 2).sum()) / (len(v) - 2)
    between = len(even) * (even.mean() - v.mean()) ** 2 + len(odd) * (odd.mean() - v.mean()) ** 2
    return float(between / within) if within > 0 else (float("inf") if between > 0 else 0.0)


def _lag_correlation(values: np.ndarray, max_lag: int) -> np.ndarray:
    """สหสัมพันธ์ Pearson ระหว่าง x[:n-L] กับ x[L:] สำหรับ L = 0..max_lag-1 (FFT + ผลรวมสะสม — O(n log n))"""
    x = values - values.mean()
    n = len(x)
    size = 1 << (2 * n - 1).bit_length()
    spectrum = np.fft.rfft(x, size)
    cross = np.fft.irfft(spectrum * np.conj(spectrum), size)[:max_lag]
    lags = np.arange(max_lag)
    m = n - lags
    c1 = np.concatenate(([0.0], np.cumsum(x)))
    c2 = np.concatenate(([0.0], np.cumsum(x * x)))
    sum_a, sum_b = c1[m], c1[n] - c1[lags]
    sq_a, sq_b = c2[m], c2[n] - c2[lags]
    var_a = sq_a - sum_a ** 2 / m
    var_b = sq_b - sum_b ** 2 / m
    denom = np.sqrt(np.clip(var_a * var_b, 1e-300, None))
    return (cross - sum_a * sum_b / m) / denom
