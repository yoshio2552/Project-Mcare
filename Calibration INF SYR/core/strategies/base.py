"""แม่แบบของ "วิธีแบ่งช่วงวัด" (strategy)

Engine ทำส่วนกลางให้แล้ว (warm-up, slope, สถิติ, สรุปผล) strategy มีหน้าที่อย่างเดียว:
ดูข้อมูลทีละจุดแล้วบอกว่า "จบ 1 ช่วงวัดแล้วหรือยัง" + flow สะสม + ความคืบหน้า

เพิ่มวิธีใหม่:
    1) สร้างไฟล์ใน core/strategies/  สืบทอด FlowStrategy
    2) ใส่ @STRATEGIES.register("key", label="ชื่อบนจอ")
    3) import ไฟล์นั้นใน core/strategies/__init__.py
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from config.settings import EngineSettings
from core.models import EngineResult, Interval, SessionConfig
from core.registry import Registry
from core.stats import flow_ml_per_h, percent_error


class FlowStrategy(ABC):
    # คุณสมบัติที่หน้าจอใช้ตัดสินว่าจะเปิดช่องตั้งค่าไหนบ้าง
    uses_cycles = False                 # อาศัยการจับรอบปั๊ม (peak/valley) ไหม
    uses_window = False                 # ต้องเลือกความยาวช่วงวัดไหม
    end_modes: tuple[str, ...] = ("time",)

    def __init__(self, config: SessionConfig, settings: EngineSettings):
        self.config = config
        self.settings = settings
        self._interval_count = 0

    @abstractmethod
    def update(self, t: float, weight: float, slope_flow: float, result: EngineResult) -> None:
        """รับข้อมูล 1 จุด แล้วเติม result.interval / cumulative / extremum / progress / finished"""

    # ------------------------------------------------ ตัวช่วยสำหรับคลาสลูก
    def _flow(self, delta_weight: float, delta_time: float) -> float:
        """flow สุทธิ = (Δw/Δt − baseline) × Z"""
        return flow_ml_per_h(delta_weight, delta_time, baseline_g_per_h=self.settings.baseline_g_per_h,
                             ml_per_g=self.settings.volume_factor)

    @staticmethod
    def _raw_flow(delta_weight: float, delta_time: float) -> float:
        """flow ที่ยังไม่แก้: ถือ 1 g = 1 ml ไม่หัก self-check (เก็บคู่ไว้สอบย้อนหลัง/เทียบโปรแกรมเดิม)"""
        return flow_ml_per_h(delta_weight, delta_time, ml_per_g=1.0)

    def _error(self, flow: float) -> float:
        return percent_error(flow, self.config.target_flow)

    def _make_interval(self, chain: int, t: float, duration: float, delta_weight: float) -> Interval:
        flow, raw = self._flow(delta_weight, duration), self._raw_flow(delta_weight, duration)
        interval = Interval(
            index=self._interval_count, chain=chain, t=t,
            duration_s=duration, flow=flow, error_pct=self._error(flow),
            flow_raw=raw, error_raw_pct=self._error(raw),
        )
        self._interval_count += 1
        return interval


STRATEGIES: Registry[FlowStrategy] = Registry("strategy")
