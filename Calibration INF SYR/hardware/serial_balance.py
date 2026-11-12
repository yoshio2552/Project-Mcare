"""ตราชั่งผ่านพอร์ตอนุกรม (RS-232) รองรับ 2 โหมด

stream  ตราชั่งส่งค่าออกมาเองต่อเนื่อง เราแค่รอรับ — เวลาของจุด = เวลาที่บรรทัดมาครบ
poll    ตราชั่งรอคำสั่ง เราส่งคำสั่งถามค่า (ค่าเริ่มต้น "Q") เป็นจังหวะคงที่แล้วอ่านคำตอบ
        เวลาของจุด = กึ่งกลางระหว่างเวลาส่งกับเวลาที่คำตอบมาครบ
auto    ฟังก่อน 1 วินาที ถ้ามีข้อมูลไหลเข้า = stream ไม่งั้นลองถาม ถ้าตอบ = poll

ความถูกต้องของเวลา (สำคัญ — flow = Δน้ำหนัก / Δเวลา):
    - อ่านพอร์ตใน thread ของตัวเอง ทำหน้าที่แค่ "อ่าน + ประทับเวลา" แล้วใส่คิว
      การคำนวณ/บันทึกไฟล์/วาดกราฟที่ช้าลงชั่วขณะ จึงไม่ทำให้เวลาของจุดเพี้ยน (เวลาถูกประทับไปแล้ว)
    - คิวไม่จำกัดขนาด: ฝั่งคำนวณตามไม่ทันก็ไม่ทิ้งข้อมูล (นับขนาดค้างสูงสุดไว้ใน diagnostics)
    - รับเฉพาะบรรทัดที่จบด้วย LF ครบ ภายในเวลารอคำตอบ (response_timeout_s) — ท่อนบรรทัดทิ้งและนับไว้
    - stream: ล้าง buffer ตอนเปิด (บรรทัดเก่าที่ค้างจะได้เวลาผิด) และนับครั้งที่มีบรรทัดรอคิวในพอร์ต
      (แปลว่าบรรทัดนั้นถูกประทับเวลาช้ากว่าที่มาถึงจริง)
    - นาฬิกา = time.perf_counter() (QueryPerformanceCounter ความละเอียด 0.1 µs, ไม่ถูกปรับตามเวลาอินเทอร์เน็ต)

detect_settings() ใช้หาค่าพอร์ต (baud / bits / parity) และโหมดให้อัตโนมัติ
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field

from config.settings import SerialSettings
from core.models import Sample
from hardware.base import SOURCES, BalanceSource
from hardware.parsers import get_parser

LISTEN_S = 1.0
DETECT_RESPONSE_S = 0.5     # ตอนค้นหาตราชั่ง รอคำตอบสั้นกว่าปกติ (ลองหลายชุด)
MAX_LINE_BYTES = 128        # stream: สะสมเกินนี้โดยไม่เจอ LF = ขยะ ทิ้ง

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


def read_line(port, deadline: float | None, should_stop=None) -> tuple[bytes, bool]:
    """อ่านจนได้ 1 บรรทัดที่จบด้วย LF -> (ไบต์ทั้งหมด, ครบไหม)

    deadline = เวลา perf_counter ที่เลิกรอ (None = รอเรื่อยๆ จนกว่า should_stop() หรือยาวเกิน MAX_LINE_BYTES)
    port.readline() ของ pyserial คืนก่อนครบได้เมื่อหมดเวลา timeout ของพอร์ต จึงต้องสะสมเอง
    """
    buffer = b""
    while True:
        buffer += port.readline()
        if buffer.endswith(b"\n"):
            return buffer, True
        if deadline is not None and time.perf_counter() >= deadline:
            return buffer, False
        if len(buffer) > MAX_LINE_BYTES or (should_stop and should_stop()):
            return buffer, False
        if deadline is None and not buffer:
            return buffer, False        # stream: ยังไม่มีอะไรมา ให้ผู้เรียกวนใหม่ (เช็คหยุดได้)


def _waiting(port) -> int:
    try:
        return int(getattr(port, "in_waiting", 0) or 0)
    except Exception:
        return 0


def detect_mode(port, settings: SerialSettings, listen_s: float = LISTEN_S) -> tuple[str, str]:
    """ดูว่าตราชั่งที่ต่ออยู่ทำงานโหมดไหน คืน (โหมด, บรรทัดตัวอย่าง) — โยน IOError ถ้าไม่ตอบ"""
    parse = get_parser(settings.line_format)
    good, sample = 0, ""
    deadline = time.perf_counter() + listen_s
    while time.perf_counter() < deadline:
        raw, complete = read_line(port, deadline)
        if complete and parse(_decode(raw)) is not None:
            good, sample = good + 1, _decode(raw).strip()
            if good >= 2:
                return "stream", sample
    for _ in range(2):
        port.reset_input_buffer()
        port.write(_command(settings))
        raw, complete = read_line(port, time.perf_counter() + min(settings.response_timeout_s, DETECT_RESPONSE_S))
        if complete and parse(_decode(raw)) is not None:
            return "poll", _decode(raw).strip()
    raise IOError("The balance did not send or answer anything readable")


@dataclass
class Diagnostics:
    """ตัวนับคุณภาพการอ่าน (อ่านได้จากทุก thread — ค่าเป็น int ธรรมดา)"""
    samples: int = 0            # จุดที่ใช้ได้
    rejected: int = 0           # ได้บรรทัดครบแต่ตัวอ่านไม่รับ (รูปแบบผิด/เกินพิกัด)
    partial: int = 0            # บรรทัดไม่ครบภายในเวลารอ (ทิ้ง)
    timeouts: int = 0           # poll: ไม่มีคำตอบเลย
    stray_bytes: int = 0        # poll: ไบต์ค้างในพอร์ตก่อนส่งคำสั่ง (ทิ้ง)
    queued_lines: int = 0       # stream: บรรทัดที่มีบรรทัดถัดไปรออยู่แล้ว = เวลาอาจช้ากว่าจริง
    max_backlog: int = 0        # คิวรอคำนวณยาวสุด (จุด)
    latency_max_s: float = 0.0  # poll: รับ − ส่ง สูงสุด
    errors: list[str] = field(default_factory=list)

    def problems(self) -> int:
        return self.rejected + self.partial + self.timeouts + self.queued_lines


class SerialBalance(BalanceSource):
    def __init__(self, settings: SerialSettings, factory=_default_factory):
        self._settings = settings
        self._factory = factory
        self._parse = get_parser(settings.line_format)
        self._port = None
        self._queue: queue.Queue[Sample] = queue.Queue()      # ไม่จำกัดขนาด = ไม่ทิ้งข้อมูล
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._failure: BaseException | None = None
        self.mode = settings.mode
        self.last_latency_s = 0.0       # (รับครบ − ส่ง) ของการถามค่าครั้งล่าสุด
        self.diagnostics = Diagnostics()
        self._describe()

    def _describe(self) -> None:
        s = self._settings
        self.description = f"{s.port} · {s.baudrate} {s.bytesize}{s.parity}{s.stopbits} · {self.mode}"

    # ------------------------------------------------------------ BalanceSource
    def open(self) -> None:
        self._port = self._factory(self._settings)
        try:
            if self._settings.mode == "auto":
                self.mode, _ = detect_mode(self._port, self._settings)
            else:
                self.mode = self._settings.mode
            self._port.reset_input_buffer()     # บรรทัดเก่าที่ค้างอยู่จะถูกประทับเวลาผิด
        except Exception:
            self.close()
            raise
        self._describe()
        self._stop.clear()
        self._thread = threading.Thread(target=self._reader, name="balance-reader", daemon=True)
        self._thread.start()

    def read(self) -> Sample | None:
        """เอาจุดถัดไปจากคิว (รอได้ไม่เกิน 0.1 s) — โยน exception ต่อถ้า thread อ่านพัง"""
        try:
            sample = self._queue.get(timeout=0.1)
        except queue.Empty:
            if self._failure is not None:
                raise IOError(str(self._failure)) from self._failure
            return None
        backlog = self._queue.qsize()
        if backlog > self.diagnostics.max_backlog:
            self.diagnostics.max_backlog = backlog
        return sample

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=3.0)
        self._thread = None
        if self._port is not None:
            try:
                self._port.close()
            finally:
                self._port = None

    # ------------------------------------------------------------ reader thread
    def _reader(self) -> None:
        try:
            if self.mode == "poll":
                self._poll_loop()
            else:
                self._stream_loop()
        except Exception as exc:        # ส่งต่อให้ read() โยนใน thread ของผู้ใช้
            if not self._stop.is_set():
                self.diagnostics.errors.append(str(exc))
                self._failure = exc

    def _accept(self, t: float, raw: bytes) -> None:
        reading = self._parse(_decode(raw))
        if reading is None:
            self.diagnostics.rejected += 1
            return
        self.diagnostics.samples += 1
        self._queue.put(Sample(t, reading.weight, reading.stable))

    def _stream_loop(self) -> None:
        port, stopping = self._port, self._stop.is_set
        while not stopping():
            raw, complete = read_line(port, None, stopping)
            t = time.perf_counter()                 # ประทับเวลาทันทีที่บรรทัดครบ
            if not raw:
                continue
            if not complete:
                self.diagnostics.partial += 1
                continue
            if _waiting(port) >= len(raw):          # มีอีกบรรทัดรออยู่แล้ว: บรรทัดนี้มาถึงก่อนเวลาที่ประทับ
                self.diagnostics.queued_lines += 1
            self._accept(t, raw)

    def _poll_loop(self) -> None:
        port, s, stopping = self._port, self._settings, self._stop.is_set
        interval = max(s.poll_interval_s, 0.02)
        next_poll = time.perf_counter()
        while not stopping():
            wait = next_poll - time.perf_counter()
            if wait > 0:
                time.sleep(min(wait, 0.2))
                continue
            next_poll += interval
            if next_poll < time.perf_counter() - interval:  # ตามไม่ทัน (ตราชั่งตอบช้ากว่าจังหวะ): ตั้งใหม่ ไม่ยิงรัว
                next_poll = time.perf_counter() + interval

            stray = _waiting(port)
            if stray:
                self.diagnostics.stray_bytes += stray
            port.reset_input_buffer()                       # กันของค้างถูกอ่านเป็นคำตอบ
            t_send = time.perf_counter()
            port.write(_command(s))
            raw, complete = read_line(port, t_send + max(s.response_timeout_s, 0.05), stopping)
            t_receive = time.perf_counter()
            if not raw:
                self.diagnostics.timeouts += 1
                continue
            if not complete:
                self.diagnostics.partial += 1
                continue
            self.last_latency_s = t_receive - t_send
            self.diagnostics.latency_max_s = max(self.diagnostics.latency_max_s, self.last_latency_s)
            self._accept((t_send + t_receive) / 2.0, raw)


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
                                   timeout_s=base.timeout_s, poll_command=base.poll_command,
                                   response_timeout_s=base.response_timeout_s, line_format=base.line_format)
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
    parse = get_parser(settings.line_format)
    count, start = 0, time.perf_counter()
    while time.perf_counter() - start < window_s:
        if mode == "poll":
            port.write(_command(settings))
        raw, complete = read_line(port, time.perf_counter() + min(settings.response_timeout_s, DETECT_RESPONSE_S))
        if complete and parse(_decode(raw)) is not None:
            count += 1
    return count / (time.perf_counter() - start)
