"""ตรวจความถูกต้องของการอ่านตราชั่งจริง ผ่านเส้นทางเดียวกับโปรแกรมหลัก (SerialBalance: thread อ่าน + คิว)

    python tools/check_balance.py --seconds 120
    python tools/check_balance.py --seconds 120 --stall 2      (จำลองโปรแกรมค้าง 2 s ทุก 10 s)

รายงาน:
    - อัตราอ่านจริง, ช่องว่างระหว่างจุดยาวสุด, เวลาตอบของตราชั่ง (poll)
    - บรรทัดขาด / บรรทัดถูกปฏิเสธ / ไม่ตอบ / เวลาอาจช้า / คิวค้างสูงสุด
    - นาฬิกา perf_counter เทียบนาฬิกา Windows (ppm) — ถ้าต่างมาก แปลว่าแกนเวลาเชื่อไม่ได้
    - flow จากความชันน้ำหนัก (ถ้าปั๊มเดินอยู่) และน้ำหนักขยับผิดปกติ
ไม่ต้องเปิดโปรแกรมหลัก — ต้องปิดโปรแกรมอื่นที่ใช้พอร์ตเดียวกัน (เช่น ARGOS) ก่อน
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np                                        # noqa: E402

from config.i18n import set_language, tr                  # noqa: E402
from config.settings import AppSettings                   # noqa: E402
from hardware.serial_balance import SerialBalance         # noqa: E402


def check(balance, seconds: float, density: float, stall_s: float = 0.0, on_tick=None) -> dict:
    """เก็บจุดจาก balance (เปิดแล้ว) เป็นเวลา seconds แล้วคืนตัวเลขสรุป"""
    samples = []
    p0, w0 = time.perf_counter(), time.time()
    next_stall = p0 + 10.0
    while time.perf_counter() - p0 < seconds:
        if stall_s and time.perf_counter() >= next_stall:
            time.sleep(stall_s)                     # ฝั่งผู้ใช้ค้าง: ข้อมูลต้องไม่หายและเวลาต้องไม่เพี้ยน
            next_stall = time.perf_counter() + 10.0
        sample = balance.read()
        if sample is not None:
            samples.append(sample)
            if on_tick:
                on_tick(len(samples), sample)
    perf_span, wall_span = time.perf_counter() - p0, time.time() - w0
    result = {"samples": len(samples), "perf_span_s": perf_span, "wall_span_s": wall_span,
              "clock_ppm": (perf_span / wall_span - 1.0) * 1e6 if wall_span > 0 else 0.0}
    if len(samples) >= 3:
        t = np.array([s.t for s in samples])
        w = np.array([s.weight for s in samples])
        gaps = np.diff(t)
        slope = np.polyfit(t, w, 1)[0]
        result.update(
            rate_hz=(len(t) - 1) / (t[-1] - t[0]),
            max_gap_s=float(gaps.max()),
            backwards=int((gaps <= 0).sum()),
            flow_ml_h=slope * 3600.0 / density,
            jumps=int((np.abs(np.diff(w)) > 0.05).sum()),
            weight_first=float(w[0]), weight_last=float(w[-1]),
        )
    return result


def main(argv=None) -> int:
    app = AppSettings.load()
    set_language(app.ui.language)
    p = argparse.ArgumentParser(description=tr("Check balance reading accuracy through the same path as the main program"))
    p.add_argument("--seconds", type=float, default=60.0)
    p.add_argument("--stall", type=float, default=0.0, help=tr("Simulate the program freezing this many seconds every 10 s"))
    p.add_argument("--port")
    p.add_argument("--mode", choices=("auto", "stream", "poll"))
    args = p.parse_args(argv)
    settings = replace(app.serial, **{k: v for k, v in {"port": args.port, "mode": args.mode}.items() if v})

    balance = SerialBalance(settings)
    try:
        balance.open()
    except Exception as exc:
        print(tr("Could not open {port}: {error}", port=settings.port, error=exc))
        print(tr("If another program (e.g. ARGOS) is using the port, close it first."))
        return 1
    print(balance.description)
    try:
        r = check(balance, args.seconds, app.engine.density_g_per_ml, args.stall,
                  on_tick=lambda n, s: print(f"\r{n:6d} · {s.weight:.3f} g   ", end="", flush=True))
    except IOError as exc:
        print()
        print(tr("Reading failed: {error} — check the connection in Settings", error=exc))
        return 1
    finally:
        balance.close()
    print()
    d = balance.diagnostics
    print(tr("Points: {n} · rate {hz:.2f} Hz · longest gap {gap:.2f} s · time going backwards: {back}",
             n=r["samples"], hz=r.get("rate_hz", 0.0), gap=r.get("max_gap_s", 0.0), back=r.get("backwards", 0)))
    print(tr("Answer time (poll): last {last:.0f} ms · longest {max:.0f} ms",
             last=balance.last_latency_s * 1000, max=d.latency_max_s * 1000))
    print(tr("Incomplete lines {partial} · rejected {rejected} · no answer {timeouts} · late timestamps {queued} · "
             "longest queue {backlog}", partial=d.partial, rejected=d.rejected, timeouts=d.timeouts,
             queued=d.queued_lines, backlog=d.max_backlog))
    print(tr("Clock check: perf_counter {perf:.3f} s vs Windows clock {wall:.3f} s ({ppm:+.0f} ppm)",
             perf=r["perf_span_s"], wall=r["wall_span_s"], ppm=r["clock_ppm"]))
    if "flow_ml_h" in r:
        print(tr("Weight {a:.3f} → {b:.3f} g · slope = {flow:.3f} ml/h · jumps > 50 mg: {jumps}",
                 a=r["weight_first"], b=r["weight_last"], flow=r["flow_ml_h"], jumps=r["jumps"]))
    ok = (d.partial == 0 and d.timeouts == 0 and r.get("backwards", 1) == 0 and r.get("jumps", 1) == 0
          and abs(r["clock_ppm"]) < 1000 and r["samples"] > 0)
    print(tr("Result: OK") if ok else tr("Result: check the items above"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
