"""เล่นซ้ำผลที่บันทึกไว้ "เหมือนรันสด ณ ตอนนั้น" (ผู้ใช้ 2026-11-20) — ไม่มี Qt

สร้างจากไฟล์ของผลเท่านั้น (ไม่รัน engine ใหม่ — ภาพตรงกับตัวเลขที่บันทึกทุกช่วง ไม่มีโอกาสต่างจากเดิม):
    raw.csv.gz      เวลา + น้ำหนักทุกจุด (เวลานับจากเริ่มวัด)
    intervals.csv   ทุกช่วงวัด: สาย เวลาเริ่ม/จบ น้ำหนักเริ่ม/จบ flow (สุทธิ/ดิบ) — จุดเริ่ม/จบของสาย A = peak, สาย B = valley
    summary.json    origin_s (peak แรก = เวลา 0), ปัจจัย Z, self-check B, หน้าต่าง regression ที่ใช้ตอนวัด
สิ่งที่คำนวณเพิ่มเพื่อแสดง (เหมือนจอทดสอบ):
    flow ขณะนั้น   regression แบบหน้าต่างเลื่อน ขนาด regression_window จุด เหมือน engine (ค่าออกที่ปลายหน้าต่าง)
                   (Q0 − B) × Z  — ยังไม่ครบหน้าต่าง = ไม่มีค่า (ตรงกับจอสดหลังแก้ 2026-11-20)
    ค่าเฉลี่ยสะสม  (น้ำหนักตอนนี้ − น้ำหนักที่จุดเริ่มสาย) ÷ เวลา ของแต่ละสาย แปลงด้วยสูตรเดียวกัน

ใช้: data = build(detail) -> ReplayData · data.results = รายการ EngineResult เรียงตามเวลา (ป้อนโมดูลกราฟเดิมได้เลย)
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from core.models import Cumulative, EngineResult, ExtremumPoint, Interval, IntervalStats, Stage
from services.session_store import volume_factor

DEFAULT_WINDOW = 20


@dataclass
class ReplayData:
    summary: dict
    results: list = field(default_factory=list)     # EngineResult เรียงตามเวลา (เวลา 0 = peak แรก)
    times: np.ndarray = field(default_factory=lambda: np.zeros(0))
    t_start: float = 0.0
    t_end: float = 0.0
    chains: int = 1
    target: float = 0.0
    tolerance: float = 5.0
    window: int = DEFAULT_WINDOW
    intervals: list = field(default_factory=list)   # dict ต่อช่วง (index chain t duration flow error ... start/end)

    def index_at(self, t: float) -> int:
        """จำนวนผลที่เกิดก่อนหรือที่เวลา t"""
        return int(np.searchsorted(self.times, t, side="right"))

    @property
    def duration(self) -> float:
        return max(0.0, self.t_end - self.t_start)


def read_intervals(folder: Path) -> list[dict]:
    path = Path(folder) / "intervals.csv"
    if not path.is_file():
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for item in csv.DictReader(f):
            def num(key, default=None):
                try:
                    return float(item[key]) if item.get(key) not in (None, "") else default
                except ValueError:
                    return default
            rows.append({
                "index": int(item["index"]), "chain": "AB".index(item["chain"]), "t": num("t_s", 0.0),
                "duration_s": num("duration_s", 0.0), "flow": num("flow_ml_h", 0.0), "error_pct": num("error_pct", 0.0),
                "flow_raw": num("flow_raw_ml_h"), "error_raw_pct": num("error_raw_pct"),
                "volume_ml": num("volume_ml"), "t_start": num("t_start_s"), "t_end": num("t_end_s"),
                "w_start": num("w_start_g"), "w_end": num("w_end_g"),
            })
    return rows


def rolling_slope(t: np.ndarray, w: np.ndarray, size: int) -> np.ndarray:
    """slope (g/s) ของ linear regression หน้าต่างเลื่อน size จุด ค่าออกที่จุดสุดท้ายของหน้าต่าง (NaN = ยังไม่ครบ)"""
    n = len(t)
    out = np.full(n, np.nan)
    size = max(3, int(size))
    if n < size:
        return out
    t0 = t - t[0]           # ลดขนาดตัวเลขก่อนยกกำลัง (ความแม่นยำ)
    w0 = w - w[0]
    c = lambda a: np.concatenate(([0.0], np.cumsum(a)))     # noqa: E731
    st, sw, stt, stw = c(t0), c(w0), c(t0 * t0), c(t0 * w0)
    end = np.arange(size, n + 1)
    begin = end - size
    sum_t, sum_w = st[end] - st[begin], sw[end] - sw[begin]
    sum_tt, sum_tw = stt[end] - stt[begin], stw[end] - stw[begin]
    denom = size * sum_tt - sum_t * sum_t
    with np.errstate(invalid="ignore", divide="ignore"):
        slope = (size * sum_tw - sum_t * sum_w) / denom
    out[size - 1:] = slope
    return out


def build(detail, samples=None) -> ReplayData:
    """detail = services.session_store.SessionDetail (summary + samples) — คืน ReplayData พร้อมเล่น"""
    summary = detail.summary
    config = summary.get("config") or {}
    target = float(config.get("target_flow") or 0.0)
    origin = float(summary.get("origin_s") or 0.0)
    z = volume_factor(summary)
    baseline = float(summary.get("baseline_g_per_h") or 0.0)
    window = int(summary.get("regression_window") or (summary.get("engine_settings") or {}).get("regression_window")
                 or DEFAULT_WINDOW)
    raw = samples if samples is not None else detail.samples
    data = ReplayData(summary=summary, target=target, tolerance=float(config.get("tolerance_pct") or 5.0),
                      window=window)
    if not raw:
        return data
    arr = np.asarray(raw, dtype=float)
    t_raw, w = arr[:, 0], arr[:, 1]
    flow = (rolling_slope(t_raw, w, window) * 3600.0 - baseline) * z
    intervals = read_intervals(Path(summary.get("folder") or "")) or [dict(row) for row in getattr(detail, "intervals", [])]
    intervals.sort(key=lambda row: (row.get("t_end") if row.get("t_end") is not None else row["t"] + origin))
    data.intervals = intervals
    data.chains = 2 if any(row["chain"] == 1 for row in intervals) else 1

    # จุดเริ่มของแต่ละสาย (ค่าเฉลี่ยสะสม) + จุดกลับตัว (peak/valley = ต้น/ปลายช่วงของสาย A/B)
    anchors: dict[int, tuple[float, float]] = {}
    extrema: list[tuple[float, ExtremumPoint]] = []
    cycle_based = (config.get("strategy") or "") == "pump_cycle"
    for row in intervals:
        first = row["chain"] not in anchors        # ช่วงแรกของสาย: จุดเริ่มก็เป็นจุดกลับตัวด้วย
        if row.get("t_start") is not None and row.get("w_start") is not None:
            anchors.setdefault(row["chain"], (row["t_start"], row["w_start"]))
        if cycle_based and row.get("t_end") is not None:
            kind = "TOP" if row["chain"] == 0 else "DOWN"
            for t_point in ([row["t_start"]] if first and row.get("t_start") is not None else []) + [row["t_end"]]:
                k = int(np.clip(np.searchsorted(t_raw, t_point), 0, len(t_raw) - 1))
                value = flow[k] if np.isfinite(flow[k]) else target
                extrema.append((t_point, ExtremumPoint(t_point - origin, float(value), kind)))
    extrema.sort(key=lambda item: item[0])

    # ผลรายช่วง แนบที่จุดตัวอย่างแรกที่ถึงเวลาจบของช่วง
    interval_at: dict[int, list] = {}
    volume = seconds = 0.0
    for row in intervals:
        end_raw = row["t_end"] if row.get("t_end") is not None else row["t"] + origin
        k = int(np.clip(np.searchsorted(t_raw, end_raw - 1e-9), 0, len(t_raw) - 1))
        volume += row["flow"] * row["duration_s"]
        seconds += row["duration_s"]
        mean = volume / seconds if seconds > 0 else row["flow"]
        flow_raw = row["flow_raw"] if row.get("flow_raw") is not None else row["flow"]
        interval = Interval(row["index"], row["chain"], row["t"], row["duration_s"], row["flow"], row["error_pct"],
                            flow_raw, row.get("error_raw_pct") or row["error_pct"])
        stats = IntervalStats(len([r for r in intervals if (r.get("t_end") or 0) <= end_raw]), mean,
                              (mean - target) / target * 100.0 if target else 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        interval_at.setdefault(k, []).append((interval, stats))

    results = []
    e_index = 0
    last_stats = None
    for i in range(len(t_raw)):
        ti = float(t_raw[i])
        cumulative = None
        if 0 in anchors and ti > anchors[0][0]:
            def cum(chain):
                if chain not in anchors or ti <= anchors[chain][0]:
                    return None
                t0, w0 = anchors[chain]
                return ((w[i] - w0) / (ti - t0) * 3600.0 - baseline) * z
            a, b = cum(0), cum(1) if data.chains == 2 else None
            both = (a + b) / 2.0 if a is not None and b is not None else None
            err = lambda v: None if v is None or not target else (v - target) / target * 100.0     # noqa: E731
            cumulative = Cumulative(t=ti - anchors[0][0], flow_a=a, flow_b=b, flow_all=both,
                                    err_a=err(a), err_b=err(b), err_all=err(both))
        events = interval_at.get(i) or [(None, None)]
        for n, (interval, stats) in enumerate(events):
            if stats is not None:
                last_stats = stats
            result = EngineResult(t=ti - origin, weight=float(w[i]), stage=Stage.MEASURING)
            if n == 0:
                value = flow[i]
                result.slope_flow = float(value) if np.isfinite(value) else None
                result.cumulative = cumulative
                while e_index < len(extrema) and extrema[e_index][0] <= ti:
                    result.extremum = extrema[e_index][1]
                    e_index += 1
                    if e_index < len(extrema) and extrema[e_index][0] <= ti:
                        results.append(result)          # มีจุดกลับตัวมากกว่า 1 ในจุดเดียว: ส่งทีละอัน
                        result = EngineResult(t=ti - origin, weight=float(w[i]), stage=Stage.MEASURING)
            result.interval = interval
            result.stats = stats if stats is not None else last_stats
            results.append(result)
    data.results = results
    data.times = np.array([r.t for r in results])
    data.t_start, data.t_end = float(data.times[0]), float(data.times[-1])
    return data


def frame_values(data: ReplayData, index: int) -> dict:
    """ตัวเลขบนการ์ดของจอเล่นซ้ำที่ตำแหน่ง index (จำนวนผลที่เล่นไปแล้ว)"""
    out = {"t": 0.0, "weight": None, "flow": None, "mean": None, "error": None, "count": 0}
    if index <= 0 or not data.results:
        return out
    last = data.results[min(index, len(data.results)) - 1]
    out["t"], out["weight"] = last.t, last.weight
    for result in reversed(data.results[max(0, index - 400):index]):
        if result.slope_flow is not None:
            out["flow"] = result.slope_flow
            break
    stats = last.stats
    if stats is not None:
        out["mean"], out["error"], out["count"] = stats.mean_flow, stats.mean_error_pct, stats.count
    return out
