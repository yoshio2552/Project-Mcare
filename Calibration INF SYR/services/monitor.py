"""BalanceMonitor: อ่านตราชั่งตอน "ยังไม่ได้ทดสอบ" เพื่อแสดงน้ำหนักสด + สถานะการเชื่อมต่อ

ทำงานใน thread แยก และต้องหยุด (ปล่อยพอร์ต) ก่อนเริ่มการทดสอบจริงทุกครั้ง
ระหว่างนั้นวัด "ช่วงเวลาต่อจุด" ของตราชั่งไว้ด้วย (ใช้แปลงคาบรอบปั๊มเป็นจำนวนจุดของหน้าต่างคำนวณ)
"""
from __future__ import annotations

import statistics
import threading
import time
from collections import deque

from PySide6.QtCore import QObject, Signal, Slot

from hardware.base import BalanceSource

RETRY_S = 2.0
EMIT_EVERY_S = 0.25


class BalanceMonitor(QObject):
    status = Signal(bool, str)      # เชื่อมต่อได้ไหม, คำอธิบาย/ข้อผิดพลาด
    reading = Signal(float, object) # น้ำหนัก, ธงนิ่ง (True/False/None)
    sample_period = Signal(float)   # ช่วงเวลาต่อจุด (s)

    def __init__(self, source: BalanceSource):
        super().__init__()
        self._source = source
        self._stop = threading.Event()
        self.done = threading.Event()

    def request_stop(self) -> None:
        self._stop.set()

    @Slot()
    def run(self) -> None:
        last_error = None
        try:
            while not self._stop.is_set():
                try:
                    self._source.open()
                except Exception as exc:
                    if str(exc) != last_error:          # รายงานเฉพาะตอนสถานะเปลี่ยน
                        last_error = str(exc)
                        self.status.emit(False, last_error)
                    self._stop.wait(RETRY_S)
                    continue
                last_error = None
                self.status.emit(True, self._source.description)
                self._read_loop()
        finally:
            self.done.set()

    def _read_loop(self) -> None:
        last_emit = last_data = time.monotonic()
        receiving = True
        times: deque[float] = deque(maxlen=40)
        reported = 0
        try:
            while not self._stop.is_set():
                sample = self._source.read()
                now = time.monotonic()
                if sample is None:
                    if receiving and now - last_data > 3.0:
                        receiving = False
                        self.status.emit(False, "no data")
                    continue
                if not receiving:
                    receiving = True
                    self.status.emit(True, self._source.description)
                last_data = now
                times.append(sample.t)
                reported += 1
                if len(times) >= 20 and reported % 20 == 0:
                    gaps = [b - a for a, b in zip(times, list(times)[1:]) if b > a]
                    if gaps:
                        self.sample_period.emit(statistics.median(gaps))
                if now - last_emit >= EMIT_EVERY_S:
                    last_emit = now
                    self.reading.emit(sample.weight, sample.stable)
        except Exception as exc:
            self.status.emit(False, str(exc))
            self._stop.wait(RETRY_S)
        finally:
            try:
                self._source.close()
            except Exception:
                pass
