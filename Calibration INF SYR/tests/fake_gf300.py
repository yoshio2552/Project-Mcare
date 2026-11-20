"""ตราชั่งจำลองระดับไบต์ แบบ A&D GF-300 โหมด poll (ใช้ในเทสต์ — 2026-11-20 รอบ 6.23)

พฤติกรรมที่จำลอง (ตามที่วัดจากเครื่องจริงของผู้ใช้ HISTORY 6.1 / 6.23):
    - รับคำสั่ง "Q" ทุกครั้งแล้วตอบทุกครั้ง (คำสั่งเข้าคิว — ไม่ทิ้งคำสั่งที่มาระหว่างกำลังตอบ)
    - ประมวลผล ~process_s แล้วส่ง "ST,+0150.238  g\\r\\n" (17 ไบต์) ที่ 2400 baud 7E1 = 10 บิต/ตัว -> ~71 ms ต่อบรรทัด
      รวมแล้วคำตอบครบที่ ~0.19 s หลังถาม (ตรงกับที่วัดได้ 175–208 ms)
    - น้ำหนักในคำตอบ = ค่า ณ เวลาที่ตราชั่งวัด (เวลาถาม + process_s) ของ weight_at(t)
    - reset_input_buffer ทิ้งเฉพาะไบต์ที่มาถึงแล้ว (ไบต์ที่ยังไม่ถึงยังจะมาต่อ — เหมือนพอร์ตจริง)
    - readline คืนเมื่อเจอ LF หรือหมด timeout ของพอร์ต
"""
from __future__ import annotations

import threading
import time


class FakeGF300:
    def __init__(self, weight_at=lambda t: 150.0 + t * 0.05, process_s: float = 0.12, baud: int = 2400,
                 timeout_s: float = 0.15, first_answer_extra_s: float = 0.0):
        self.weight_at = weight_at
        self.process_s = process_s
        self.char_s = 10.0 / baud
        self.timeout_s = timeout_s
        self.first_answer_extra_s = first_answer_extra_s     # คำตอบแรกหลังเปิดพอร์ตช้ากว่าปกติ
        self.t0 = time.perf_counter()
        self._bytes: list[tuple[float, int]] = []          # (เวลาที่ไบต์มาถึง, ไบต์) ที่ยังไม่ถูกอ่าน/ทิ้ง
        self._busy_until = 0.0
        self._answers = 0
        self._lock = threading.Lock()
        self.closed = False
        self.measured: list[tuple[float, float]] = []      # (เวลาที่วัดจริง perf_counter, น้ำหนัก) ของทุกคำตอบ

    # ------------------------------------------------------------ ด้านตราชั่ง
    def write(self, data: bytes) -> int:
        now = time.perf_counter()
        with self._lock:
            for _ in range(data.count(b"\n")):
                extra = self.first_answer_extra_s if self._answers == 0 else 0.0
                self._answers += 1
                measure_at = now + self.process_s + extra
                start = max(measure_at, self._busy_until)
                weight = self.weight_at(measure_at - self.t0)
                self.measured.append((measure_at, weight))
                line = f"ST,+{weight:08.3f}  g\r\n".encode("ascii")
                for i, byte in enumerate(line):
                    self._bytes.append((start + (i + 1) * self.char_s, byte))
                self._busy_until = start + len(line) * self.char_s
        return len(data)

    # ------------------------------------------------------------ ด้านพอร์ต (pyserial)
    @property
    def in_waiting(self) -> int:
        now = time.perf_counter()
        with self._lock:
            return sum(1 for at, _ in self._bytes if at <= now)

    def reset_input_buffer(self) -> None:
        now = time.perf_counter()
        with self._lock:
            self._bytes = [(at, b) for at, b in self._bytes if at > now]

    def readline(self) -> bytes:
        deadline = time.perf_counter() + self.timeout_s
        out = bytearray()
        while True:
            now = time.perf_counter()
            with self._lock:
                while self._bytes and self._bytes[0][0] <= now:
                    byte = self._bytes.pop(0)[1]
                    out.append(byte)
                    if byte == 0x0A:
                        return bytes(out)
            if now >= deadline:
                return bytes(out)
            time.sleep(0.002)

    def close(self) -> None:
        self.closed = True
