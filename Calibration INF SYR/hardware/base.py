"""สัญญากลางของ "แหล่งข้อมูลน้ำหนัก" (ตราชั่งจริง, ตัวจำลอง, ไฟล์ย้อนหลัง ฯลฯ)

เพิ่มตราชั่งรุ่นใหม่:
    1) สร้างไฟล์ใน hardware/ สืบทอด BalanceSource
    2) ใส่ @SOURCES.register("key", label="ชื่อบนจอ")
    3) import ไฟล์นั้นใน hardware/__init__.py
factory จะถูกเรียกแบบ factory(settings: AppSettings, config: SessionConfig)
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import Sample
from core.registry import Registry


class BalanceSource(ABC):
    description: str = ""

    @abstractmethod
    def open(self) -> None:
        """เปิดการเชื่อมต่อ (โยน exception ถ้าเปิดไม่ได้)"""

    @abstractmethod
    def read(self) -> Sample | None:
        """อ่าน 1 ค่า — ต้องคืนภายในเวลาสั้นๆ (คืน None ถ้ายังไม่มีข้อมูล)"""

    @abstractmethod
    def close(self) -> None:
        """ปิดการเชื่อมต่อ (เรียกซ้ำได้)"""


SOURCES: Registry[BalanceSource] = Registry("balance source")
