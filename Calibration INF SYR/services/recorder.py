"""RawRecorder: เขียนข้อมูลดิบลงดิสก์ "ระหว่างรัน" (ไม่รอจนจบ)

ถ้าโปรแกรมหรือไฟดับกลางการทดสอบ ข้อมูลที่เก็บมาแล้วยังอยู่ในโฟลเดอร์ของ session
    raw.csv      ช่วงวัดจริง
    prerun.csv   ช่วงก่อนวัด (สร้างเมื่อมีข้อมูล)
ทำงานใน thread ของการอ่านข้อมูล และ flush ลงดิสก์ทุก ~1 วินาที
"""
from __future__ import annotations

import time
from pathlib import Path

FLUSH_EVERY_S = 1.0


class RawRecorder:
    def __init__(self, folder: Path):
        self.folder = folder
        self._files: dict[str, object] = {}
        self._last_flush = time.monotonic()

    def write(self, prerun: bool, t: float, weight: float) -> None:
        name = "prerun.csv" if prerun else "raw.csv"
        handle = self._files.get(name)
        if handle is None:
            handle = open(self.folder / name, "w", newline="", encoding="utf-8")
            handle.write("t_s,weight_g\n")
            self._files[name] = handle
        handle.write(f"{t:.4f},{weight:.4f}\n")
        now = time.monotonic()
        if now - self._last_flush >= FLUSH_EVERY_S:
            self._last_flush = now
            for file in self._files.values():
                file.flush()

    def close(self) -> None:
        for file in self._files.values():
            try:
                file.close()
            except OSError:
                pass
        self._files.clear()
