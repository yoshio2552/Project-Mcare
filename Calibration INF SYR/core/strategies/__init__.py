"""วิธีคำนวณทั้งหมด — import ที่นี่เพื่อให้แต่ละวิธีลงทะเบียนกับ STRATEGIES"""
from core.strategies.base import STRATEGIES, FlowStrategy
from core.strategies import pump_cycle, time_based  # noqa: F401  (ลงทะเบียน)

__all__ = ["STRATEGIES", "FlowStrategy"]
