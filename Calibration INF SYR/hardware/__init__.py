"""แหล่งข้อมูลน้ำหนักทั้งหมด — import ที่นี่เพื่อให้แต่ละตัวลงทะเบียนกับ SOURCES"""
from hardware.base import SOURCES, BalanceSource
from hardware import replay, serial_balance, simulator  # noqa: F401  (ลงทะเบียน)

__all__ = ["SOURCES", "BalanceSource"]
