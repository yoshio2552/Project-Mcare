"""ตรวจย้อนผลจากข้อมูลดิบ (ไม่มี Qt) — คำนวณทุกตัวเลขใหม่จาก raw.csv แล้วเทียบกับที่บันทึก

ใช้: audit_folder(folder, summary) -> Audit · หน้ารายละเอียดผลมีปุ่ม "ตรวจย้อนจากข้อมูลดิบ" (ui/dialogs/session_detail.py)

ตรวจอะไรบ้าง (ทุกข้อคำนวณจาก raw.csv ตรงๆ ไม่ใช้ค่าที่โปรแกรมคำนวณไว้):
    1) ทุกช่วงวัด: จุดต้น-ปลายมีอยู่จริงใน raw.csv (เวลาตรงทุกหลัก) และน้ำหนักตรงกับที่บันทึก
       flow ดิบ = (w ปลาย − w ต้น) ÷ (t ปลาย − t ต้น) × 3600 · flow สุทธิ = (flow ดิบ − baseline) × Z
    2) ช่วงต่อกันในสายเดียวกัน (ปลายช่วงก่อน = ต้นช่วงถัดไป) — ไม่มีน้ำหนักตกหล่น/นับซ้ำ
    3) ค่าที่ใช้ตัดสิน = ปริมาตรรวม ÷ เวลารวม · Error% · 2SD · เวลาวัด · น้ำหนักรวมของสาย A
ผลรุ่นก่อน 2026-11-19 (intervals.csv ไม่มีจุดต้น-ปลาย): ใช้ origin_s + t_s ถ้ามี (เวลาอาจคลาด 0.001 s จากการปัด)
ไม่งั้นตรวจได้แค่ความสอดคล้องภายในไฟล์ (flow × เวลา = ปริมาตร)
ผลเก่าใช้ค่าเฉลี่ยธรรมดาของ flow รายช่วงตัดสิน — ตรวจเทียบตามวิธีที่ผลนั้นใช้ (ดูจาก summary)
"""
from __future__ import annotations

import csv
import gzip
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev

FLOW_TOL = 1e-3         # ml/h — ค่าที่บันทึก 4 ตำแหน่ง
REL_TOL = 1e-5          # สัดส่วน (ตัวเลขรวม)
TIME_TOL = 5e-5         # s — เวลาใน raw.csv 4 ตำแหน่ง


@dataclass
class Check:
    name: str               # อังกฤษ (ผ่าน tr ที่ UI)
    ok: bool
    detail: str = ""


@dataclass
class Audit:
    checks: list[Check] = field(default_factory=list)
    intervals: int = 0
    exact: bool = False     # ตรวจรายช่วงได้ตรงตัวจากจุดต้น-ปลาย (ผลรุ่นใหม่)

    @property
    def ok(self) -> bool:
        return bool(self.checks) and all(c.ok for c in self.checks)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(Check(name, bool(ok), detail))


def read_raw(folder: Path) -> list[tuple[str, float, float]]:
    """[(เวลาตามตัวอักษรในไฟล์, เวลา, น้ำหนัก)] — เก็บตัวอักษรไว้เทียบแบบตรงทุกหลัก"""
    packed, plain = folder / "raw.csv.gz", folder / "raw.csv"
    opener = (lambda: gzip.open(packed, "rt", encoding="utf-8", newline="")) if packed.is_file() else \
             (lambda: open(plain, newline="", encoding="utf-8")) if plain.is_file() else None
    if opener is None:
        return []
    with opener() as f:
        reader = csv.reader(f)
        next(reader, None)
        return [(r[0], float(r[0]), float(r[1])) for r in reader if len(r) >= 2]


def audit_folder(folder: Path, summary: dict) -> Audit:
    audit = Audit()
    folder = Path(folder)
    raw = read_raw(folder)
    path = folder / "intervals.csv"
    if not raw or not path.is_file():
        audit.add("Raw data and intervals file present", False, "raw.csv / intervals.csv missing")
        return audit
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    audit.intervals = len(rows)
    by_text = {text: w for text, _t, w in raw}
    times = [t for _text, t, _w in raw]
    cfg = summary.get("config") or {}
    target = float(cfg.get("target_flow") or 0.0)
    z = float(summary.get("ml_per_g") or 1.0)
    base = float(summary.get("baseline_g_per_h") or 0.0)
    origin = summary.get("origin_s")
    audit.exact = bool(rows) and bool(rows[0].get("t_start_s"))

    def weight_near(t: float) -> tuple[float, float]:
        from bisect import bisect_left
        i = min(max(bisect_left(times, t), 1), len(times) - 1)
        j = i if abs(times[i] - t) < abs(times[i - 1] - t) else i - 1
        return times[j], raw[j][2]

    worst_flow = worst_raw = worst_w = worst_t = worst_gap = 0.0
    missing = 0
    ends: dict[str, float] = {}
    flows, durations, volumes, mass_a, time_a, last_a = [], [], [], 0.0, 0.0, None
    for row in rows:
        flow, dur = float(row["flow_ml_h"]), float(row["duration_s"])
        # ผลรุ่นแรกสุดไม่มี flow ดิบ: ย้อนสูตรจากค่าแก้ที่บันทึก (เหมือน Repository._read_intervals)
        flow_raw = float(row["flow_raw_ml_h"]) if row.get("flow_raw_ml_h") else flow / z + base
        flows.append(flow)
        durations.append(dur)
        volumes.append(flow * dur / 3600.0)
        if audit.exact:
            ts, te = row["t_start_s"], row["t_end_s"]
            ws, we = by_text.get(ts), by_text.get(te)
            if ws is None or we is None:
                missing += 1
                continue
            worst_w = max(worst_w, abs(ws - float(row["w_start_g"])), abs(we - float(row["w_end_g"])))
            t0, t1 = float(ts), float(te)
            worst_t = max(worst_t, abs((t1 - t0) - dur))
        elif origin is not None:
            t1 = float(origin) + float(row["t_s"])
            t0 = t1 - dur
            (a0, ws), (a1, we) = weight_near(t0), weight_near(t1)
            worst_t = max(worst_t, abs(a0 - t0), abs(a1 - t1))
            t0, t1 = a0, a1
        else:
            continue
        chain = row["chain"]
        if chain in ends:
            worst_gap = max(worst_gap, abs(ends[chain] - t0))
        ends[chain] = t1
        recomputed_raw = (we - ws) / (t1 - t0) * 3600.0 if t1 > t0 else 0.0
        worst_raw = max(worst_raw, abs(recomputed_raw - flow_raw))
        worst_flow = max(worst_flow, abs((recomputed_raw - base) * z - flow))
        if chain == "A":
            mass_a += we - ws
            time_a += t1 - t0
            last_a = row

    if audit.exact or origin is not None:
        limit = FLOW_TOL if audit.exact else max(FLOW_TOL, target * 2e-4)     # ผลเก่า: เวลาปัด 3 ตำแหน่ง
        audit.add("Every interval start/end exists in raw data", missing == 0, f"{missing} not found")
        if audit.exact:
            audit.add("Interval weights match raw data", worst_w <= 5e-5, f"max {worst_w:.5f} g")
        audit.add("Interval times match raw data", worst_t <= (TIME_TOL if audit.exact else 2e-3), f"max {worst_t:.4f} s")
        audit.add("Uncorrected flow recomputed from raw", worst_raw <= limit, f"max {worst_raw:.5f} ml/h")
        audit.add("Net flow = (uncorrected − baseline) × Z", worst_flow <= limit, f"max {worst_flow:.5f} ml/h")
        audit.add("Intervals are contiguous (no gap, no overlap)", worst_gap <= 2e-3, f"max {worst_gap:.4f} s")
    else:
        audit.add("Interval positions in raw data", True, "older result — not recorded, file consistency only")
    # ปริมาตรบันทึกจากเวลาเต็มความละเอียด แต่เวลาในไฟล์ปัด (ผลเก่า 3 ตำแหน่ง / ใหม่ 4) -> เผื่อตามการปัดนั้น
    step = 5e-5 if audit.exact else 5e-4
    over = [abs(float(r["volume_ml"]) - v) - float(r["flow_ml_h"]) * step / 3600.0
            for r, v in zip(rows, volumes) if r.get("volume_ml")]
    audit.add("Volume = flow × time for every interval", max(over, default=0.0) <= 1e-5,
              f"max {max(over, default=0.0) + 1e-5:.6f} ml")

    weighted = "mean_flow_cycles" in summary        # ผลรุ่นใหม่: ปริมาตรรวม ÷ เวลารวม
    measured = sum(volumes) / sum(durations) * 3600.0 if weighted and sum(durations) > 0 else mean(flows) if flows else 0.0
    recorded = float(summary.get("mean_flow") or 0.0)
    audit.add("Measured flow = total volume ÷ total time" if weighted else "Measured flow = mean of interval flows",
              abs(measured - recorded) <= max(1e-4, abs(recorded) * REL_TOL), f"{measured:.4f} vs {recorded:.4f} ml/h")
    if target:
        error = (measured - target) / target * 100.0
        audit.add("Error% = (measured − set) ÷ set × 100", abs(error - float(summary.get("error_pct") or 0)) <= 1e-3,
                  f"{error:+.4f} %")
        if len(flows) > 1 and summary.get("sd2_pct") is not None:
            sd2 = 2 * stdev(flows) / target * 100.0
            audit.add("2SD of interval flows", abs(sd2 - float(summary["sd2_pct"])) <= 1e-3, f"{sd2:.4f} %")
    if summary.get("measured_s") is not None and last_a is not None:
        audit.add("Measuring time = last interval end since the first peak",
                  abs(float(last_a["t_s"]) - float(summary["measured_s"])) <= 2e-3, f"{float(summary['measured_s']):.3f} s")
    if summary.get("total_mass_g") is not None and (audit.exact or origin is not None):
        audit.add("Total weighed mass (chain A)", abs(mass_a - float(summary["total_mass_g"])) <= 2e-4,
                  f"{mass_a:.4f} g in {time_a:.2f} s")
    return audit
