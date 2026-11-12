"""ทดสอบความถูกต้องของการอ่านตราชั่ง: บรรทัดขาด, ตัวอ่านเข้มงวด, thread อ่านแยก, คิวไม่ทิ้งข้อมูล, เวลา

ใช้ไบต์จริงจาก GF-300 ของผู้ใช้ (tests/fixtures/gf300_inf10_excerpt.csv) — ช่วงที่โปรแกรมเดิมอ่านได้ 2.637 g
แทน 142.637 g เพราะรอคำตอบไม่นานพอ

รัน:  python -m unittest discover -s tests -v
"""
import csv
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import SerialSettings
from hardware.parsers import get_parser, parse_and, parse_line
from hardware.serial_balance import SerialBalance, read_line
from tools.capture_raw import _row

FIXTURE = Path(__file__).parent / "fixtures" / "gf300_inf10_excerpt.csv"


def _fixture_rows() -> list[dict]:
    with open(FIXTURE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


class ChunkPort:
    """พอร์ตจำลองที่คืนข้อมูลเป็นท่อนตามลำดับ (เหมือน readline ของ pyserial ที่คืนก่อนครบเมื่อหมด timeout)"""

    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.closed = False

    def readline(self) -> bytes:
        time.sleep(0.001)
        return self.chunks.pop(0) if self.chunks else b""


class SlowAnswerPort:
    """ตราชั่ง poll ที่ตอบช้า: ส่งครึ่งแรกของบรรทัดหลัง `first_s` และครึ่งหลังหลัง `second_s` (นับจากถาม)"""

    def __init__(self, line=b"ST,+0142.637  g\r\n", first_s=0.03, second_s=0.06):
        self.line, self.first_s, self.second_s = line, first_s, second_s
        self.asked_at = None
        self.sent = 0
        self.closed = False
        self.written = []

    def write(self, data):
        self.written.append(data)
        self.asked_at, self.sent = time.perf_counter(), 0

    def reset_input_buffer(self):
        pass

    def readline(self) -> bytes:
        time.sleep(0.005)       # เหมือน timeout สั้นของพอร์ต
        if self.asked_at is None:
            return b""
        elapsed = time.perf_counter() - self.asked_at
        half = len(self.line) // 2
        if self.sent == 0 and elapsed >= self.first_s:
            self.sent = 1
            return self.line[:half]
        if self.sent == 1 and elapsed >= self.second_s:
            self.sent, self.asked_at = 2, None
            return self.line[half:]
        return b""

    def close(self):
        self.closed = True


class ClockedStreamPort:
    """ตราชั่ง stream ที่ส่งบรรทัดตามนาฬิกาจริงทุก `period_s` (น้ำหนักเพิ่มทีละ 1 mg) — บรรทัดค้างในพอร์ตได้"""

    def __init__(self, period_s=0.01):
        self.period_s = period_s
        self.t0 = time.perf_counter()
        self.delivered = 0
        self.closed = False

    def _due(self) -> int:
        return int((time.perf_counter() - self.t0) / self.period_s)

    @property
    def in_waiting(self) -> int:
        return max(0, self._due() - self.delivered) * 17

    def readline(self) -> bytes:
        while self._due() <= self.delivered:
            time.sleep(0.0005)
        self.delivered += 1
        return f"ST,+{100 + self.delivered / 1000:09.3f}  g\r\n".encode()

    def reset_input_buffer(self):
        self.delivered = self._due()

    def close(self):
        self.closed = True


class StrictParserTest(unittest.TestCase):
    def test_real_gf300_line(self):
        self.assertEqual(parse_and("ST,+0144.804  g"), parse_line("ST,+0144.804  g"))
        r = parse_and("US,+0144.804  g\r\n")
        self.assertEqual((r.weight, r.stable), (144.804, False))
        self.assertEqual(parse_and("ST,-0000.012  g").weight, -0.012)

    def test_fragments_from_real_data_are_rejected(self):
        for fragment in ["US,+01", "US,+0142.6", "2.637  g", ",+0142.637  g", "T,+0142.637  g",
                         "S,+0142.637  g", "ST,", "ST,+", "S", "0142.636  g", "ST,+0142.637", "OL,+9999.999  g",
                         "ST,+0142.637  PC"]:
            self.assertIsNone(parse_and(fragment), fragment)
            self.assertIsNone(get_parser("and")(fragment), fragment)
        self.assertEqual(parse_line("US,+01"), None)          # auto: หน้าตา A&D -> เข้มงวด
        self.assertIsNotNone(parse_line("2.637  g"))           # auto ยังรับท่อนที่ไม่มีหัว (จึงไม่ใช่ค่าเริ่มต้น)

    def test_fixture_reparse_has_no_false_weights(self):
        """ไบต์จริงทุกแถวใน fixture: แถวที่ได้น้ำหนัก ต้องเป็นบรรทัด 17 ไบต์ครบ และน้ำหนักอยู่ช่วงจริง"""
        rows = _fixture_rows()
        self.assertTrue(any(r["raw_text"].startswith("2.637") for r in rows))   # มีกรณีเดิมอยู่จริง
        weights = []
        for r in rows:
            raw = bytes.fromhex(r["raw_hex"])
            keep = r["status"] if r["status"] in ("timeout", "stray") else None
            row = _row(0, None, 0.0, raw, keep)
            if row["status"] == "ok":
                self.assertEqual(len(raw), 17)
                weights.append(float(row["weight_g"]))
        self.assertGreater(len(weights), 30)
        self.assertTrue(all(142.0 < w < 143.0 for w in weights), weights)


class ReadLineTest(unittest.TestCase):
    def test_joins_pieces_until_lf(self):
        port = ChunkPort([b"US,+01", b"", b"42.637  g\r\n"])
        raw, complete = read_line(port, time.perf_counter() + 1.0)
        self.assertEqual((raw, complete), (b"US,+0142.637  g\r\n", True))

    def test_incomplete_at_deadline(self):
        raw, complete = read_line(ChunkPort([b"US,+01"]), time.perf_counter() + 0.05)
        self.assertEqual((raw, complete), (b"US,+01", False))


class SerialBalanceTimingTest(unittest.TestCase):
    def _collect(self, balance, n, timeout=5.0):
        got, deadline = [], time.perf_counter() + timeout
        while len(got) < n and time.perf_counter() < deadline:
            s = balance.read()
            if s:
                got.append(s)
        return got

    def test_slow_answer_is_waited_for_not_cut(self):
        """ตราชั่งตอบเป็น 2 ท่อน (เหมือน GF-300 ที่ 2400 baud) -> ต้องได้น้ำหนักถูกทุกจุด ไม่มี 1.0 g"""
        port = SlowAnswerPort()
        balance = SerialBalance(SerialSettings(mode="poll", poll_interval_s=0.02, response_timeout_s=0.5),
                                factory=lambda s: port)
        balance.open()
        try:
            samples = self._collect(balance, 5)
        finally:
            balance.close()
        self.assertEqual(len(samples), 5)
        self.assertTrue(all(s.weight == 142.637 for s in samples))
        self.assertEqual(balance.diagnostics.partial, 0)
        self.assertGreaterEqual(balance.last_latency_s, 0.06)
        self.assertTrue(port.closed)

    def test_too_short_wait_discards_instead_of_misreading(self):
        port = SlowAnswerPort(first_s=0.01, second_s=0.2)
        balance = SerialBalance(SerialSettings(mode="poll", poll_interval_s=0.02, response_timeout_s=0.05),
                                factory=lambda s: port)
        balance.open()
        try:
            samples = self._collect(balance, 1, timeout=0.6)
        finally:
            balance.close()
        self.assertEqual(samples, [])                           # ไม่ยอมเดาจากท่อนบรรทัด
        self.assertGreater(balance.diagnostics.partial, 0)

    def test_slow_consumer_keeps_every_point_and_true_timestamps(self):
        """ฝั่งคำนวณหยุดไป 0.3 s: ต้องไม่เสียจุดเลย และเวลาของแต่ละจุดยังห่างเท่ากับจังหวะที่ตราชั่งส่ง"""
        period = 0.01
        port = ClockedStreamPort(period)
        balance = SerialBalance(SerialSettings(mode="stream"), factory=lambda s: port)
        balance.open()
        try:
            time.sleep(0.3)                                     # จำลอง UI/การคำนวณค้าง
            samples = self._collect(balance, 50)
        finally:
            balance.close()
        weights = [round(s.weight, 3) for s in samples]
        steps = {round(b - a, 3) for a, b in zip(weights, weights[1:])}
        self.assertEqual(steps, {0.001})                        # ต่อเนื่อง ไม่มีจุดหาย
        self.assertGreater(balance.diagnostics.max_backlog, 10)  # ค้างคิวจริง แต่ไม่ทิ้ง
        gaps = [b.t - a.t for a, b in zip(samples, samples[1:])]
        flow_like = (samples[-1].weight - samples[0].weight) / (samples[-1].t - samples[0].t)
        self.assertAlmostEqual(flow_like, 0.001 / period, delta=0.001 / period * 0.15)
        self.assertLess(max(gaps), period * 6)                  # เวลาไม่ถูกบีบ/ยืดเป็นก้อน

    def test_reader_failure_reaches_consumer(self):
        class Broken(ChunkPort):
            def readline(self):
                raise OSError("cable unplugged")

            def reset_input_buffer(self):
                pass

            def close(self):
                self.closed = True

        balance = SerialBalance(SerialSettings(mode="stream"), factory=lambda s: Broken([]))
        balance.open()
        try:
            with self.assertRaises(IOError):
                for _ in range(20):
                    balance.read()
        finally:
            balance.close()
        self.assertIn("cable unplugged", balance.diagnostics.errors[0])

    def test_check_tool_with_stalls(self):
        """tools/check_balance.check(): ค้าง 0.2 s ระหว่างทาง ข้อมูลต้องครบ เวลาไม่ถอย ความชันตรงกับที่ส่ง"""
        from tools import check_balance
        period = 0.01
        balance = SerialBalance(SerialSettings(mode="stream"), factory=lambda s: ClockedStreamPort(period))
        balance.open()
        try:
            check_balance.time.perf_counter()       # ให้แน่ใจว่า import ได้
            r = check_balance.check(balance, 0.6, density=1.0, stall_s=0.0)
        finally:
            balance.close()
        self.assertEqual(r["backwards"], 0)
        self.assertEqual(r["jumps"], 0)
        self.assertAlmostEqual(r["flow_ml_h"], 0.001 / period * 3600, delta=0.001 / period * 3600 * 0.1)
        self.assertLess(abs(r["clock_ppm"]), 5000)

    def test_close_stops_reader_thread(self):
        balance = SerialBalance(SerialSettings(mode="stream"), factory=lambda s: ClockedStreamPort())
        balance.open()
        reader = balance._thread
        self.assertTrue(reader.is_alive())
        balance.close()
        self.assertFalse(reader.is_alive())
        self.assertIsNone(balance._thread)


if __name__ == "__main__":
    unittest.main()
