"""Registry กลาง = "ปุ่มต่อ Lego" ของระบบ

โมดูลใหม่ (ตราชั่งรุ่นใหม่, วิธีคำนวณใหม่) ลงทะเบียนตัวเองด้วย decorator
แล้วส่วนอื่นของระบบ (เช่น combo box บน UI) จะเห็นทันทีโดยไม่ต้องแก้โค้ดเดิม

    @STRATEGIES.register("my_method", label="My method")
    class MyStrategy(FlowStrategy): ...
"""
from __future__ import annotations

from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    def __init__(self, kind: str):
        self.kind = kind
        self._items: dict[str, Callable[..., T]] = {}
        self._labels: dict[str, str] = {}

    def register(self, key: str, *, label: str | None = None):
        def decorator(factory: Callable[..., T]):
            if key in self._items:
                raise KeyError(f"{self.kind} '{key}' ถูกลงทะเบียนซ้ำ")
            self._items[key] = factory
            self._labels[key] = label or key
            return factory
        return decorator

    def create(self, key: str, *args, **kwargs) -> T:
        if key not in self._items:
            raise KeyError(f"ไม่รู้จัก {self.kind} '{key}' (มี: {', '.join(self._items)})")
        return self._items[key](*args, **kwargs)

    def get(self, key: str) -> Callable[..., T]:
        """คืนตัว factory/คลาสที่ลงทะเบียนไว้ (ใช้อ่านคุณสมบัติของคลาส)"""
        if key not in self._items:
            raise KeyError(f"ไม่รู้จัก {self.kind} '{key}'")
        return self._items[key]

    def choices(self) -> list[tuple[str, str]]:
        """[(key, label)] สำหรับเติม combo box"""
        return [(key, self._labels[key]) for key in self._items]

    def __contains__(self, key: str) -> bool:
        return key in self._items
