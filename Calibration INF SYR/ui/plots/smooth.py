"""SmoothScroller: แกนเวลาของกราฟสดเลื่อนต่อเนื่องระหว่างจุดข้อมูล (ผู้ใช้ 2026-11-20: "สมูธ 60 fps ไม่หน่วง รองรับ 5 Hz, 10 Hz")

ปัญหาเดิม: กราฟขยับเฉพาะตอนจุดใหม่มาถึง (5 Hz = กระโดด 5 ครั้ง/วินาที · ช่วงที่ตราชั่งให้ 10 Hz ลื่นกว่า -> ดูเหมือน fps ตก)
วิธี: ทุกเฟรม เลื่อนเฉพาะ "ช่วงแกนเวลา" ไปที่ เวลาจุดล่าสุด + เวลาที่ผ่านไปตั้งแต่จุดนั้นมาถึง (นาฬิกา perf_counter)
      ไม่เกิน LEAD_LIMIT × ช่วงเวลาต่อจุด (ข้อมูลมาช้า/ตราชั่งหยุด = กราฟหยุดรอ ไม่วิ่งเลยข้อมูลจริง)
      ไม่วาดเส้นใหม่ (เส้นวาดเฉพาะตอนข้อมูลมา) — ข้อมูลและเวลาของจุดไม่ถูกแตะ (แสดงผลอย่างเดียว)
เฟรมเรตปรับเอง: วัดเวลาที่ใช้วาดจริงทุกเฟรม แล้วตั้งช่วงห่างเฟรมให้ใช้เวลาหน้าจอไม่เกิน budget (ค่าตั้ง 40 %)
      เครื่องเร็ว = ได้ตามเป้า (60 fps) · เครื่องช้า/หน้าต่างใหญ่ = fps ลดเอง ไม่แย่งเวลากับการรับข้อมูล/ปุ่ม
ใช้เฉพาะโหมดมุมมอง อัตโนมัติ/ซูม ระหว่างทดสอบ (โหมดเต็มแกนแทบไม่ขยับอยู่แล้ว)
"""
from __future__ import annotations

import statistics
import time
from collections import deque

from PySide6.QtCore import QObject, Qt, QTimer

LEAD_LIMIT = 1.25           # เลื่อนนำจุดล่าสุดได้ไม่เกินกี่เท่าของช่วงเวลาต่อจุด
MIN_FPS = 8


class SmoothScroller(QObject):
    def __init__(self, plots, ui, parent=None):
        super().__init__(parent)
        self.plots = list(plots)
        self.ui = ui
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._arrival = 0.0                 # perf_counter ตอนจุดล่าสุดมาถึง
        self._last_t: float | None = None
        self._gaps: deque[float] = deque(maxlen=25)
        self._cost = 0.004                  # เวลาวาด 1 เฟรม (EMA, s)
        self.fps = 0.0                      # เฟรมเรตที่ใช้อยู่ (ดู/ทดสอบได้)

    # ------------------------------------------------------------ ควบคุม
    @property
    def enabled(self) -> bool:
        return bool(getattr(self.ui, "smooth_scroll", True))

    def start(self) -> None:
        for plot in self.plots:
            plot.smooth = self.enabled
        self._last_t = None
        self._gaps.clear()
        if self.enabled:
            self._schedule()
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        for plot in self.plots:
            plot.smooth = False

    def data_arrived(self, results) -> None:
        """หน้าทดสอบเรียกทุกครั้งที่ได้ผลชุดใหม่ (หลังป้อนกราฟแล้ว)"""
        if not results:
            return
        t = results[-1].t
        if self._last_t is not None and t > self._last_t:
            self._gaps.append((t - self._last_t) / max(1, len(results)))
        self._last_t = t
        self._arrival = time.perf_counter()

    @property
    def sample_period(self) -> float:
        return statistics.median(self._gaps) if len(self._gaps) >= 3 else 0.2

    # ------------------------------------------------------------ เฟรม
    def _schedule(self) -> None:
        target = max(MIN_FPS, float(getattr(self.ui, "smooth_fps", 60) or 60))
        budget = max(0.05, min(0.9, float(getattr(self.ui, "smooth_budget_pct", 40) or 40) / 100.0))
        interval = max(1.0 / target, self._cost / budget)           # ใช้เวลาวาดไม่เกิน budget ของเวลาทั้งหมด
        interval = min(interval, 1.0 / MIN_FPS)
        self.fps = 1.0 / interval
        self._timer.setInterval(max(1, int(round(interval * 1000))))

    def _tick(self) -> None:
        if self._last_t is None:
            return
        ahead = min(time.perf_counter() - self._arrival, LEAD_LIMIT * self.sample_period)
        start = time.perf_counter()
        moved = [plot for plot in self.plots if plot.smooth_advance(ahead)]
        for plot in moved:                  # วาดทันที (วัดเวลาวาดจริงของเฟรมนี้ได้)
            plot.plot.getViewWidget().repaint()
        if moved:
            cost = time.perf_counter() - start
            self._cost = 0.8 * self._cost + 0.2 * cost
            self._schedule()
