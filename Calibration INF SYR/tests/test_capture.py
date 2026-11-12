"""ทดสอบเครื่องมือเก็บข้อมูลดิบ tools/capture_raw.py (ใช้พอร์ตจำลอง ไม่แตะ data/ จริง)

รัน:  python -m unittest discover -s tests -v
"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import ReplaySettings, SerialSettings
from hardware.replay import ReplayBalance, load_samples
from test_extensions import FakeSerial
from tools.capture_raw import Capture, reparse


def _rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


class StrayPort(FakeSerial):
    """พอร์ต poll ที่มีไบต์ค้างก่อนถามทุกครั้ง"""
    in_waiting = 4

    def read(self, n: int) -> bytes:
        return b"xx\r\n"[:n]


class CaptureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "cap.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def test_poll_keeps_raw_bytes_and_times(self):
        port = FakeSerial("poll", b"ST,+00012.345  g\r\n")
        Capture(port, SerialSettings(poll_interval_s=0.02), "poll", self.path, note="test").run(0.2)
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("# note test", text)
        self.assertIn("mode poll", text)
        rows = _rows(self.path)
        self.assertGreater(len(rows), 3)
        row = rows[0]
        self.assertEqual(row["status"], "ok")
        self.assertEqual(bytes.fromhex(row["raw_hex"]), b"ST,+00012.345  g\r\n")    # CR LF ต้องอยู่ครบ
        self.assertEqual(float(row["weight_g"]), 12.345)
        self.assertEqual(row["stable"], "1")
        t_send, t_recv = float(row["t_send_s"]), float(row["t_recv_s"])
        self.assertLessEqual(t_send, t_recv)
        self.assertAlmostEqual(float(row["t_s"]), (t_send + t_recv) / 2, places=3)
        self.assertEqual(set(port.written), {b"Q\r\n"})

    def test_poll_records_timeout_and_unparsed(self):
        Capture(FakeSerial("silent"), SerialSettings(poll_interval_s=0.02), "poll", self.path).run(0.1)
        self.assertTrue(all(r["status"] == "timeout" and r["weight_g"] == "" for r in _rows(self.path)))
        Capture(FakeSerial("stream", b"\x02??garbage\r\n"), SerialSettings(), "stream", self.path).run(0.05)
        rows = _rows(self.path)
        self.assertTrue(rows and all(r["status"] == "unparsed" for r in rows))
        self.assertEqual(bytes.fromhex(rows[0]["raw_hex"]), b"\x02??garbage\r\n")
        self.assertEqual(rows[0]["t_send_s"], "")                               # stream ไม่มีเวลาส่ง

    def test_poll_saves_stray_bytes(self):
        Capture(StrayPort("poll"), SerialSettings(poll_interval_s=0.02), "poll", self.path).run(0.1)
        statuses = [r["status"] for r in _rows(self.path)]
        self.assertEqual(statuses[0], "stray")
        self.assertIn("ok", statuses)

    def test_capture_file_replays_directly(self):
        Capture(FakeSerial("poll", b"US,+00001.500  g\r\n"), SerialSettings(poll_interval_s=0.02),
                "poll", self.path).run(0.15)
        samples = load_samples(self.path)
        self.assertEqual(len(samples), sum(r["status"] == "ok" for r in _rows(self.path)))
        self.assertTrue(all(w == 1.5 for _, w in samples))
        source = ReplayBalance(ReplaySettings(path=str(self.path), speed=1000))
        source.open()
        sample = None
        while sample is None:
            sample = source.read()
        self.assertEqual(sample.weight, 1.5)

    def test_reparse_rebuilds_from_raw_hex(self):
        Capture(FakeSerial("poll", b"ST,+00002.000  g\r\n"), SerialSettings(poll_interval_s=0.02),
                "poll", self.path).run(0.1)
        rows = _rows(self.path)
        with open(self.path, "w", newline="", encoding="utf-8") as f:     # ทำเหมือนตัวอ่านเดิมอ่านไม่ออก
            f.write("# original header\n")
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            for r in rows:
                writer.writerow({**r, "t_s": "", "weight_g": "", "status": "unparsed"})
        out = reparse(self.path)
        self.assertIn("# original header", out.read_text(encoding="utf-8"))
        again = _rows(out)
        self.assertEqual(len(again), len(rows))
        self.assertTrue(all(r["status"] == "ok" and float(r["weight_g"]) == 2.0 for r in again))


if __name__ == "__main__":
    unittest.main()
