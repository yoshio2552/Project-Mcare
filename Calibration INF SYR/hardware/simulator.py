"""ตราชั่งจำลอง: สร้างน้ำหนักของปั๊มที่ flow แกว่งเป็นรอบแบบ finger pump

ใช้เวลาเสมือน (เร่งได้ด้วย speed) จึงทดสอบ session 5 นาทีได้ในไม่กี่วินาที
"""
from __future__ import annotations

import math
import random
import time

from config.settings import SimulatorSettings
from core.models import Sample
from hardware.base import SOURCES, BalanceSource


class SimulatedBalance(BalanceSource):
    def __init__(self, settings: SimulatorSettings, target_flow: float, density: float = 1.0, seed: int | None = None):
        self._s = settings
        self._rate_g_per_s = target_flow * (1.0 + settings.error_pct / 100.0) * density / 3600.0
        self._dt = 1.0 / max(settings.sample_rate_hz, 0.1)
        self._random = random.Random(seed)
        self._index = 0
        self._wall_start = 0.0
        self.description = f"Simulator x{settings.speed:g} ({settings.error_pct:+g}% error)"

    def weight_at(self, t: float) -> float:
        """น้ำหนักสะสม ณ เวลา t — อินทิเกรตของ rate x (1 + A sin(2πt/P))"""
        amplitude = min(abs(self._s.ripple_pct) / 100.0, 0.95)
        period = max(self._s.cycle_period_s, 1.0)
        omega = 2.0 * math.pi / period
        delivered = self._rate_g_per_s * (t + amplitude / omega * (1.0 - math.cos(omega * t)))
        return delivered - self._s.evaporation_mg_h / 1000.0 / 3600.0 * t

    def open(self) -> None:
        self._index = 0
        self._wall_start = time.perf_counter()

    def read(self) -> Sample | None:
        t = self._index * self._dt
        # รอให้ถึงเวลาจริงของ sample นี้ (ถ้าช้ากว่ากำหนดอยู่แล้วก็ส่งทันที)
        due = self._wall_start + t / max(self._s.speed, 0.01)
        delay = due - time.perf_counter()
        if delay > 0:
            time.sleep(min(delay, 0.2))
            if due - time.perf_counter() > 0:
                return None
        self._index += 1
        weight = self.weight_at(t) + self._random.gauss(0.0, self._s.noise_g)
        return Sample(t, round(weight, 4))

    def close(self) -> None:
        pass


@SOURCES.register("simulator", label="Simulator (no hardware)")
def _create(settings, config) -> SimulatedBalance:
    # ปั๊มจำลองจ่าย "ปริมาตร" ตาม error ที่ตั้ง -> น้ำหนักที่ตราชั่งเห็น = ปริมาตร / Z (ให้ผลสุทธิตรงกับที่ตั้ง)
    from core.corrections import gravimetric_correction
    z = gravimetric_correction(config.job, settings.engine).ml_per_g
    return SimulatedBalance(settings.simulator, config.target_flow, 1.0 / z)
