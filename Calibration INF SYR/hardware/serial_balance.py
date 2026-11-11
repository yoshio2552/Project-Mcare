"""ตราชั่งผ่านพอร์ตอนุกรม (RS-232) รองรับ 2 โหมด

stream  ตราชั่งส่งค่าออกมาเองต่อเนื่อง เราแค่รอรับ
poll    ตราชั่งรอคำสั่ง เราส่งคำสั่งถามค่า (ค่าเริ่มต้น "Q") เป็นจังหวะคงที่แล้วอ่านคำตอบ
        เวลาของจุด = กึ่งกลางระหว่างเวลาส่งกับเวลารับ
auto    ฟังก่อน 1 วินาที ถ้ามีข้อมูลไหลเข้า = stream ไม่งั้นลองถาม ถ้าตอบ = poll

detect_settings() ใช้หาค่าพอร์ต (baud / bits / parity) และโหมดให้อัตโนมัติ
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from config.settings import SerialSettings
from core.models import Sample
from hardware.base import SOURCES, BalanceSource
from hardware.parsers import parse_line

LISTEN_S = 1.0

# ค่าพอร์ตที่ลองตอนค้นหาอัตโนมัติ (baud, data bits, parity, stop bits)
CANDIDATES = [
    (9600, 7, "E", 1), (2400, 7, "E", 1), (9600, 8, "N", 1), (4800, 7, "E", 1),
    (19200, 7, "E", 1), (2400, 8, "N", 1), (19200, 8, "N", 1), (1200, 7, "E", 1),
]


def _default_factory(settings: SerialSettings):
    import serial   # import ตอนใช้จริง เพื่อให้โหมดจำลองทำงานได้แม้ไม่ได้ลง pyserial
    return serial.Serial(
        settings.port, settings.baudrate, bytesize=settings.bytesize, parity=settings.parity,
        stopbits=settings.stopbits, timeout=settings.timeout_s,
    )


def _decode(raw: bytes) -> str:
    return raw.decode("ascii", errors="ignore")


def _command(settings: SerialSettings) -> bytes:
    return settings.poll_command.encode("ascii", errors="ignore") + b"\r\n"


def detect_mode(port, settings: SerialSettings, listen_s: float = LISTEN_S) -> tuple[str, str]:
    """ดูว่าตราชั่งที่ต่ออยู่ทำงานโหมดไหน คืน (โหมด, บรรทัดตัวอย่าง) — โยน IOError ถ้าไม่ตอบ"""
    good, sample = 0, ""
    deadline = time.perf_counter() + listen_s
    while time.perf_counter() < deadline:
        line = _decode(port.readline())
        if parse_line(line) is not None:
            good, sample = good + 1, line.strip()
            if good >= 2:
                return "stream", sample
    for _ in range(2):
        port.reset_input_buffer()
        port.write(_command(settings))
        line = _decode(port.readline())
        if parse_line(line) is not None:
            return "poll", line.strip()
    raise IOError("The balance did not send or answer anything readable")


class SerialBalance(BalanceSource):
    def __init__(self, settings: SerialSettings, factory=_default_factory):
        self._settings = settings
        self._factory = factory
        self._port = None
        self.mode = settings.mode
        self.last_latency_s = 0.0       # (รับ − ส่ง) ของการถามค่าครั้งล่าสุด
        self._next_poll = 0.0
        self._describe()

    def _describe(self) -> None:
        s = self._settings
        self.description = f"{s.port} · {s.baudrate} {s.bytesize}{s.parity}{s.stopbits} · {self.mode}"

    def open(self) -> None:
        self._port = self._factory(self._settings)
        try:
            if self._settings.mode == "auto":
                self.mode, _ = detect_mode(self._port, self._settings)
            else:
                self.mode = self._settings.mode
        except Exception:
            self.close()
            raise
        self._next_poll = time.perf_counter()
        self._describe()

    def read(self) -> Sample | None:
        return self._read_poll() if self.mode == "poll" else self._read_stream()

    def _read_stream(self) -> Sample | None:
        raw = self._port.readline()
        t = time.perf_counter()
        reading = parse_line(_decode(raw)) if raw else None
        return None if reading is None else Sample(t, reading.weight, reading.stable)

    def _read_poll(self) -> Sample | None:
        wait = self._next_poll - time.perf_counter()
        if wait > 0:
            time.sleep(min(wait, 0.2))
            if self._next_poll - time.perf_counter() > 0:
                return None
        interval = max(self._settings.poll_interval_s, 0.02)
        self._next_poll += interval
        if self._next_poll < time.perf_counter() - interval:    # ตามไม่ทัน: ตั้งจังหวะใหม่ ไม่ยิงรัว
            self._next_poll = time.perf_counter() + interval

        self._port.reset_input_buffer()                         # กันบรรทัดค้างถูกอ่านเป็นคำตอบ
        t_send = time.perf_counter()
        self._port.write(_command(self._settings))
        raw = self._port.readline()
        t_receive = time.perf_counter()
        reading = parse_line(_decode(raw)) if raw else None
        if reading is None:
            return None
        self.last_latency_s = t_receive - t_send
        return Sample((t_send + t_receive) / 2.0, reading.weight, reading.stable)

    def close(self) -> None:
        if self._port is not None:
            try:
                self._port.close()
            finally:
                self._port = None


@SOURCES.register("serial", label="Balance (serial port)")
def _create(settings, config) -> SerialBalance:
    return SerialBalance(settings.serial)


# ---------------------------------------------------------------- auto detect
@dataclass
class Detection:
    port: str
    baudrate: int
    bytesize: int
    parity: str
    stopbits: int
    mode: str
    rate_hz: float
    sample_line: str


def list_ports() -> list[str]:
    """รายชื่อพอร์ตอนุกรมที่เครื่องมองเห็น"""
    try:
        from serial.tools import list_ports as _lp
        return sorted(p.device for p in _lp.comports())
    except Exception:
        return []


def detect_settings(base: SerialSettings, ports: list[str] | None = None, factory=_default_factory,
                    progress=None, should_stop=None) -> Detection | None:
    """ไล่ลองพอร์ตและค่าพอร์ตจนเจอชุดที่อ่านค่าตราชั่งได้ (ค่าปัจจุบันถูกลองก่อน)

    progress(text) ถูกเรียกก่อนลองแต่ละชุด, should_stop() คืน True เพื่อยกเลิก
    """
    current = (base.baudrate, base.bytesize, base.parity, base.stopbits)
    candidates = [current] + [c for c in CANDIDATES if c != current]
    names = [base.port] + [p for p in (ports if ports is not None else list_ports()) if p != base.port]
    for name in (n for n in names if n):
        for baud, bits, parity, stop in candidates:
            if should_stop and should_stop():
                return None
            trial = SerialSettings(port=name, baudrate=baud, bytesize=bits, parity=parity, stopbits=stop,
                                   timeout_s=base.timeout_s, poll_command=base.poll_command)
            if progress:
                progress(f"{name} · {baud} {bits}{parity}{stop}")
            try:
                port = factory(trial)
            except Exception:
                break                       # เปิดพอร์ตนี้ไม่ได้ ข้ามไปพอร์ตถัดไป
            try:
                mode, line = detect_mode(port, trial, listen_s=0.8)
                rate = _measure_rate(port, trial, mode)
                return Detection(name, baud, bits, parity, stop, mode, rate, line)
            except IOError:
                continue
            finally:
                port.close()
    return None


def _measure_rate(port, settings: SerialSettings, mode: str, window_s: float = 1.0) -> float:
    """จำนวนค่าที่อ่านได้ต่อวินาที (stream: อัตราที่ตราชั่งส่ง, poll: อัตราตอบสูงสุด)"""
    count, start = 0, time.perf_counter()
    while time.perf_counter() - start < window_s:
        if mode == "poll":
            port.write(_command(settings))
        if parse_line(_decode(port.readline())) is not None:
            count += 1
    return count / (time.perf_counter() - start)
