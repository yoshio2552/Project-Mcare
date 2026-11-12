"""เก็บข้อมูลดิบจากตราชั่ง (บรรทัดดิบทั้งบรรทัด + เวลาส่ง + เวลารับ) ลง CSV

ใช้เก็บข้อมูลจริงเพื่อนำมาปรับตัวอ่านบรรทัด (hardware/parsers.py) และอัลกอริทึม
ไม่ต้องเปิดโปรแกรมหลัก ไม่ใช้ Qt — ค่าพอร์ตอ่านจาก data/settings.json (สั่งทับได้ทางบรรทัดคำสั่ง)

    python tools/capture_raw.py --label inf50 --minutes 8
    python tools/capture_raw.py --port COM3 --baud 2400 --mode poll --interval 0.1
    python tools/capture_raw.py --reparse data/captures/xxx.csv      (อ่านซ้ำด้วย parsers.py ปัจจุบัน)

ไฟล์ออก: data/captures/YYYY-MM-DD_HHMMSS_<label>.csv
    บรรทัดหัวที่ขึ้นต้นด้วย "#" = ค่าพอร์ต โหมด เวลาเริ่ม เวอร์ชัน
    คอลัมน์ 2 ตัวแรก (t_s, weight_g) ตรงกับ raw.csv จึงเปิดด้วยแหล่งข้อมูล Replay ได้ทันที
    raw_hex = ไบต์ดิบทุกตัว (รวม CR/LF และตัวที่อ่านไม่ออก) ไม่มีการตัดทิ้ง

status ของแต่ละแถว:
    ok        อ่านน้ำหนักได้
    unparsed  ได้บรรทัดครบ (จบด้วย LF) แต่ตัวอ่านบรรทัดไม่รับ (ยังเก็บไว้ทั้งบรรทัด)
    partial   บรรทัดไม่ครบภายในเวลารอคำตอบ (response_timeout_s) — ไม่ใช้เป็นน้ำหนัก
    timeout   (poll) ส่งคำสั่งแล้วไม่มีคำตอบเลย
    stray     (poll) ไบต์ที่ค้างในพอร์ตก่อนส่งคำสั่ง (เช่น ท่อนท้ายของคำตอบที่มาช้า)

ใช้ตัวอ่านพอร์ต (read_line) และตัวอ่านบรรทัด (line_format) ชุดเดียวกับโปรแกรมหลัก
ต่างกันตรงที่เครื่องมือนี้วนอ่านใน thread เดียว และเขียนทุกแถว (รวมแถวที่ใช้ไม่ได้) ลงไฟล์
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.constants import APP_VERSION, DATA_DIR       # noqa: E402
from config.i18n import set_language, tr                  # noqa: E402
from config.settings import AppSettings, SerialSettings   # noqa: E402
from hardware.parsers import LINE_FORMATS, get_parser      # noqa: E402
from hardware.serial_balance import (                      # noqa: E402
    _command, _decode, _default_factory, _waiting, detect_mode, read_line,
)

CAPTURE_DIR = DATA_DIR / "captures"
COLUMNS = ["t_s", "weight_g", "stable", "t_send_s", "t_recv_s", "seq", "status", "raw_hex", "raw_text"]
FLUSH_S = 1.0


def _row(seq: int, t_send: float | None, t_recv: float, raw: bytes, status: str | None = None,
         parse=get_parser("and")) -> dict:
    """ประกอบ 1 แถว — เวลาของจุด: poll = กึ่งกลางส่ง-รับ (เหมือนโปรแกรมหลัก), stream = เวลารับ

    status ที่ไม่ระบุ: ไม่จบด้วย LF = partial, จบครบแต่ตัวอ่านไม่รับ = unparsed, ไม่งั้น ok
    """
    text = _decode(raw)
    complete = raw.endswith(b"\n")
    reading = parse(text) if raw and complete else None
    if status is None:
        status = "ok" if reading else ("unparsed" if complete else "partial")
    t = (t_send + t_recv) / 2.0 if t_send is not None else t_recv
    return {
        "t_s": f"{t:.4f}" if reading and status == "ok" else "",
        "weight_g": repr(reading.weight) if reading and status == "ok" else "",
        "stable": "" if not reading or reading.stable is None else int(reading.stable),
        "t_send_s": "" if t_send is None else f"{t_send:.4f}",
        "t_recv_s": f"{t_recv:.4f}",
        "seq": seq,
        "status": status,
        "raw_hex": raw.hex(" "),
        "raw_text": text.strip(),
    }


class Capture:
    """วนอ่านตราชั่งแล้วเขียนทุกแถวลงไฟล์ (port = object แบบ pyserial ที่เปิดแล้ว)"""

    def __init__(self, port, settings: SerialSettings, mode: str, path: Path, note: str = ""):
        self.port, self.settings, self.mode, self.path, self.note = port, settings, mode, path, note
        self.parse = get_parser(settings.line_format)
        self.counts = {"ok": 0, "unparsed": 0, "partial": 0, "timeout": 0, "stray": 0}
        self.last_row: dict | None = None
        self.last_latency_s = 0.0
        self._seq = 0
        self._t0 = 0.0

    def _now(self) -> float:
        return time.perf_counter() - self._t0

    def _header(self, f) -> None:
        s = self.settings
        lines = [
            f"DeltaM capture · version {APP_VERSION}",
            f"started {datetime.now().isoformat(timespec='seconds')}",
            f"port {s.port} · {s.baudrate} {s.bytesize}{s.parity}{s.stopbits} · timeout {s.timeout_s} s",
            f"mode {self.mode} · poll command {s.poll_command!r} · poll interval {s.poll_interval_s} s"
            f" · response timeout {s.response_timeout_s} s · line format {s.line_format}",
            "time = perf_counter seconds from start; poll t_s = (t_send + t_recv) / 2",
        ]
        if self.note:
            lines.append(f"note {self.note}")
        for line in lines:
            f.write(f"# {line}\n")

    def _write(self, writer, row: dict) -> None:
        writer.writerow(row)
        self.counts[row["status"]] += 1
        self.last_row = row
        self._seq += 1

    def _step_stream(self, writer) -> None:
        raw, _ = read_line(self.port, None)
        t = self._now()
        if raw:                                     # ว่าง = ตราชั่งยังไม่ส่ง ไม่ต้องเก็บ
            self._write(writer, _row(self._seq, None, t, raw, parse=self.parse))

    def _step_poll(self, writer, next_poll: float) -> float:
        wait = next_poll - self._now()
        if wait > 0:
            time.sleep(min(wait, 0.2))
            return next_poll
        interval = max(self.settings.poll_interval_s, 0.02)
        next_poll += interval
        if next_poll < self._now() - interval:      # ตามไม่ทัน: ตั้งจังหวะใหม่ ไม่ยิงรัว
            next_poll = self._now() + interval
        waiting = _waiting(self.port)
        if waiting:                                 # เก็บของค้างไว้ดูด้วย แทนที่จะทิ้งเฉยๆ
            self._write(writer, _row(self._seq, None, self._now(), self.port.read(waiting), "stray"))
        self.port.reset_input_buffer()
        t_send = self._now()
        self.port.write(_command(self.settings))
        raw, _ = read_line(self.port, self._t0 + t_send + max(self.settings.response_timeout_s, 0.05))
        t_recv = self._now()
        self.last_latency_s = t_recv - t_send
        self._write(writer, _row(self._seq, t_send, t_recv, raw, None if raw else "timeout", self.parse))
        return next_poll

    def run(self, duration_s: float | None = None, on_status=None, should_stop=None) -> None:
        """เก็บจนครบ duration_s (None = จนกว่า should_stop() คืน True หรือกด Ctrl+C)"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            self._header(f)
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            self._t0 = time.perf_counter()
            next_poll = 0.0
            last_flush = 0.0
            try:
                while duration_s is None or self._now() < duration_s:
                    if should_stop and should_stop():
                        break
                    if self.mode == "poll":
                        next_poll = self._step_poll(writer, next_poll)
                    else:
                        self._step_stream(writer)
                    if self._now() - last_flush >= FLUSH_S:   # ลงดิสก์จริงทุก ~1 s กันข้อมูลหายถ้าล่ม
                        f.flush()
                        os.fsync(f.fileno())
                        last_flush = self._now()
                        if on_status:
                            on_status(self)
            finally:
                f.flush()
                os.fsync(f.fileno())


def reparse(path: Path, line_format: str = "and") -> Path:
    """อ่านไฟล์ capture เดิมแล้วคำนวณ t_s/weight_g/status ใหม่จาก raw_hex ด้วย parsers.py ปัจจุบัน"""
    parse = get_parser(line_format)
    out = path.with_name(path.stem + ".reparsed.csv")
    with open(path, newline="", encoding="utf-8") as src, open(out, "w", newline="", encoding="utf-8") as dst:
        rows = []
        for line in src:
            if line.startswith("#"):
                dst.write(line)
            else:
                rows.append(line)
        dst.write(f"# reparsed {datetime.now().isoformat(timespec='seconds')} · version {APP_VERSION}"
                  f" · line format {line_format}\n")
        writer = csv.DictWriter(dst, fieldnames=COLUMNS)
        writer.writeheader()
        for old in csv.DictReader(rows):
            raw = bytes.fromhex(old["raw_hex"])
            keep = old["status"] if old["status"] in ("timeout", "stray") else None
            t_send = float(old["t_send_s"]) if old["t_send_s"] else None
            writer.writerow(_row(int(old["seq"]), t_send, float(old["t_recv_s"]), raw, keep, parse))
    return out


# ---------------------------------------------------------------- บรรทัดคำสั่ง
def _arguments(argv=None):
    p = argparse.ArgumentParser(description=tr("Record raw balance lines with send/receive times to CSV"))
    p.add_argument("--label", default="", help=tr("Short name added to the file name (e.g. inf50)"))
    p.add_argument("--minutes", type=float, default=None, help=tr("Stop after this many minutes (default: until Ctrl+C)"))
    p.add_argument("--port")
    p.add_argument("--baud", type=int)
    p.add_argument("--bits", type=int, choices=(7, 8))
    p.add_argument("--parity", choices=("N", "E", "O"))
    p.add_argument("--stopbits", type=int, choices=(1, 2))
    p.add_argument("--mode", choices=("auto", "stream", "poll"))
    p.add_argument("--interval", type=float, help=tr("Poll interval in seconds"))
    p.add_argument("--command", help=tr("Poll command (CR LF is added)"))
    p.add_argument("--wait", type=float, help=tr("Wait for a full answer up to this many seconds"))
    p.add_argument("--format", choices=list(LINE_FORMATS), help=tr("Line format"))
    p.add_argument("--note", default="", help=tr("Free text saved in the file header"))
    p.add_argument("--reparse", type=Path, help=tr("Re-read an existing capture file with the current parser"))
    return p.parse_args(argv)


def _serial_settings(args, base: SerialSettings) -> SerialSettings:
    changes = {"port": args.port, "baudrate": args.baud, "bytesize": args.bits, "parity": args.parity,
               "stopbits": args.stopbits, "mode": args.mode, "poll_interval_s": args.interval,
               "poll_command": args.command, "response_timeout_s": args.wait, "line_format": args.format}
    return replace(base, **{k: v for k, v in changes.items() if v is not None})


def _print_status(capture: Capture) -> None:
    c, row = capture.counts, capture.last_row or {}
    weight = row.get("weight_g") or "—"
    latency = f" · {tr('latency')} {capture.last_latency_s * 1000:.0f} ms" if capture.mode == "poll" else ""
    print(f"\r{capture._now():7.0f} s · {tr('rows')} {sum(c.values())} · {weight} g · "
          f"{tr('unreadable')} {c['unparsed']} · {tr('incomplete')} {c['partial']} · timeout {c['timeout']}{latency}   ",
          end="", flush=True)


def main(argv=None) -> int:
    app = AppSettings.load()
    set_language(app.ui.language)
    args = _arguments(argv)
    if args.reparse:
        print(tr("Saved: {path}", path=reparse(args.reparse, args.format or app.serial.line_format)))
        return 0

    settings = _serial_settings(args, app.serial)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = CAPTURE_DIR / f"{stamp}{'_' + args.label if args.label else ''}.csv"
    try:
        port = _default_factory(settings)
    except Exception as exc:
        print(tr("Could not open {port}: {error}", port=settings.port, error=exc))
        print(tr("If another program (e.g. ARGOS) is using the port, close it first."))
        return 1
    try:
        mode = settings.mode
        if mode == "auto":
            mode, sample = detect_mode(port, settings)
            print(tr("Detected mode: {mode} · sample line: {line}", mode=mode, line=sample))
        capture = Capture(port, settings, mode, path, args.note)
        print(tr("Recording to {path}", path=path))
        print(tr("Press Ctrl+C to stop."))
        try:
            capture.run(args.minutes * 60 if args.minutes else None, on_status=_print_status)
        except KeyboardInterrupt:
            pass
        _print_status(capture)
        print()
        print(tr("Saved: {path}", path=path))
        return 0
    except IOError as exc:
        print(tr(str(exc)))
        return 1
    finally:
        port.close()


if __name__ == "__main__":
    sys.exit(main())
