"""คลังข้อมูลของแอป (repository) — ตัวปัจจุบันคือ SQLite ไฟล์เดียว: data/deltam.db

ส่วนอื่นของระบบคุยกับ Repository เท่านั้น จะย้ายไปฐานข้อมูลอื่น (เช่น PostgreSQL เมื่อใช้หลายเครื่อง)
ก็สร้างคลาสใหม่ที่มี method ชุดเดียวกัน แล้วสลับที่ get_repository() จุดเดียว

สิ่งที่เก็บ
    sessions              ผลของแต่ละขั้นทดสอบ (แยกโหมดด้วยคอลัมน์ mode) + สรุปเต็มเป็น JSON
    profiles              โปรไฟล์ปั๊มต่อ ยี่ห้อ + รุ่น + ชุดสาย (ปริมาตรต่อรอบ)
    profile_observations  ข้อสังเกตรายครั้งที่ใช้สร้างโปรไฟล์ (rate, คาบที่วัดได้)
    self_checks           ผล self-check (การระเหย + การไหลของค่าตราชั่ง)
ข้อมูลดิบ 10 Hz ไม่ได้อยู่ในฐานข้อมูล แต่อยู่ในโฟลเดอร์ของ session (raw.csv, intervals.csv)
"""
from __future__ import annotations

import csv
import json
import logging
import shutil
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from config.constants import APP_VERSION, DATA_DIR, SESSIONS_DIR
from core.corrections import SelfCheckResult
from core.models import Interval, SessionSummary
from core.profiles import MAX_DEVIATION, PumpProfile, profile_key

log = logging.getLogger("deltam.store")

DATABASE_FILE = DATA_DIR / "deltam.db"
SCHEMA_VERSION = 1
SAME_RATE_BAND = 0.02     # rate ที่ต่างกันไม่เกิน 2 % ถือเป็น rate เดียวกัน

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL, mode TEXT NOT NULL, job_id TEXT, step_index INTEGER, step_count INTEGER,
    pump_type TEXT, brand TEXT, model TEXT, iv_set TEXT, serial_no TEXT, asset_id TEXT,
    department TEXT, operator TEXT,
    target_flow REAL, mean_flow REAL, error_pct REAL, verdict TEXT, end_reason TEXT,
    folder TEXT, summary_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions (started_at);
CREATE INDEX IF NOT EXISTS idx_sessions_mode ON sessions (mode);
CREATE INDEX IF NOT EXISTS idx_sessions_serial ON sessions (serial_no);
CREATE TABLE IF NOT EXISTS profiles (
    brand TEXT, model TEXT, iv_set TEXT, stroke_volume_ml REAL, runs INTEGER, updated_at TEXT,
    PRIMARY KEY (brand, model, iv_set)
);
CREATE TABLE IF NOT EXISTS profile_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT, model TEXT, iv_set TEXT, rate_ml_h REAL, period_s REAL, mean_flow REAL,
    stroke_volume_ml REAL, accepted INTEGER, session_id INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS model_items (
    brand TEXT, model TEXT, kind TEXT, item TEXT, uses INTEGER DEFAULT 0, updated_at TEXT,
    PRIMARY KEY (brand, model, kind, item)
);
CREATE TABLE IF NOT EXISTS self_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    measured_at TEXT, passed INTEGER, rate_g_per_h REAL, result_json TEXT
);
"""

# ขอบเขตการค้นหาเครื่อง -> คอลัมน์ที่ค้น
SEARCH_SCOPES = {
    "all": ("brand", "model", "serial_no", "asset_id", "job_id", "department", "iv_set"),
    "job": ("job_id",),
    "serial": ("serial_no",),
    "code": ("asset_id",),
}


@dataclass
class SessionDetail:
    """ข้อมูลเต็มของ 1 session สำหรับหน้ารายละเอียด/รายงาน"""
    summary: dict
    intervals: list[dict] = field(default_factory=list)     # index, chain, t, duration_s, flow, error_pct
    samples: list[tuple[float, float]] = field(default_factory=list)


class Repository:
    def __init__(self, path: Path = DATABASE_FILE, sessions_dir: Path = SESSIONS_DIR):
        self.path = path
        self.sessions_dir = sessions_dir
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.row_factory = sqlite3.Row
        self._db.executescript(_SCHEMA)
        self._db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")   # จุดเริ่มสำหรับ migration ในอนาคต
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    # ------------------------------------------------------------- sessions
    def new_session_folder(self, summary_stamp: datetime, pump_type: str, target_flow: float) -> Path:
        """โฟลเดอร์สำหรับเขียนข้อมูลดิบระหว่างรัน (ยังไม่ถือว่าเป็นผลจนกว่าจะ save)"""
        folder = self.sessions_dir / f"{summary_stamp:%Y%m%d_%H%M%S}_{pump_type}_{target_flow:g}mlh"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def save(self, summary: SessionSummary, intervals: list[Interval], folder: Path) -> str:
        """บันทึกผล 1 ขั้น (ข้อมูลดิบอยู่ใน folder แล้ว) คืน ref ของ session"""
        payload = asdict(summary)
        payload["app_version"] = APP_VERSION
        text = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
        (folder / "summary.json").write_text(text, encoding="utf-8")
        with open(folder / "intervals.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "chain", "t_s", "duration_s", "flow_ml_h", "error_pct"])
            for iv in intervals:
                writer.writerow([iv.index, "AB"[iv.chain], f"{iv.t:.3f}", f"{iv.duration_s:.3f}",
                                 f"{iv.flow:.4f}", f"{iv.error_pct:.4f}"])

        config, job = summary.config, summary.config.job
        cursor = self._db.execute(
            "INSERT INTO sessions (started_at, mode, job_id, step_index, step_count, pump_type, brand, model,"
            " iv_set, serial_no, asset_id, department, operator, target_flow, mean_flow, error_pct, verdict,"
            " end_reason, folder, summary_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (summary.started_at, config.run_mode.value, config.job_id, config.step_index, config.step_count,
             job.pump_type.value, job.brand, job.model, job.accessory, job.serial_no, job.asset_id,
             job.department, job.operator, config.target_flow, summary.mean_flow, summary.error_pct,
             summary.verdict.value, summary.end_reason, str(folder), text),
        )
        self._db.commit()
        return str(cursor.lastrowid)

    def discard_folder(self, folder: Path) -> None:
        """ลบข้อมูลของการทดสอบที่ผู้ใช้ไม่เก็บ (ลบจริง ไม่มีถังพัก)"""
        shutil.rmtree(folder, ignore_errors=True)

    def delete(self, ref: str) -> None:
        row = self._db.execute("SELECT folder FROM sessions WHERE id = ?", (ref,)).fetchone()
        if row is None:
            return
        if row["folder"]:
            self.discard_folder(Path(row["folder"]))
        self._db.execute("DELETE FROM sessions WHERE id = ?", (ref,))
        self._db.commit()

    def list(self, mode: str | None = None) -> list[dict]:
        """สรุปผล เรียงใหม่ -> เก่า (แต่ละรายการมี key 'ref') — mode=None คือทุกโหมด"""
        query = "SELECT id, folder, summary_json FROM sessions"
        args: tuple = ()
        if mode:
            query, args = query + " WHERE mode = ?", (mode,)
        sessions = []
        for row in self._db.execute(query + " ORDER BY started_at DESC, id DESC", args):
            try:
                data = json.loads(row["summary_json"])
            except ValueError:
                continue
            data["ref"], data["folder"] = str(row["id"]), row["folder"]
            sessions.append(data)
        return sessions

    def load(self, ref: str) -> SessionDetail:
        row = self._db.execute("SELECT id, folder, summary_json FROM sessions WHERE id = ?", (ref,)).fetchone()
        if row is None:
            raise KeyError(f"session {ref} not found")
        detail = SessionDetail(summary=json.loads(row["summary_json"]))
        detail.summary["ref"], detail.summary["folder"] = str(row["id"]), row["folder"]
        folder = Path(row["folder"] or "")
        intervals_file, raw_file = folder / "intervals.csv", folder / "raw.csv"
        if intervals_file.is_file():
            with open(intervals_file, newline="", encoding="utf-8") as f:
                for item in csv.DictReader(f):
                    detail.intervals.append({
                        "index": int(item["index"]), "chain": "AB".index(item["chain"]),
                        "t": float(item["t_s"]), "duration_s": float(item["duration_s"]),
                        "flow": float(item["flow_ml_h"]), "error_pct": float(item["error_pct"]),
                    })
        if raw_file.is_file():
            with open(raw_file, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)
                detail.samples = [(float(r[0]), float(r[1])) for r in reader if len(r) >= 2]
        return detail

    def search_devices(self, text: str = "", scope: str = "all", limit: int = 15) -> list[dict]:
        """ค้นเครื่องที่เคยทดสอบ (ไม่ซ้ำเครื่อง ใหม่สุดก่อน) สำหรับช่องดึงข้อมูลใน wizard

        แต่ละรายการ = dict ของ JobInfo ครั้งล่าสุด + last_date, last_verdict, job_id
        """
        columns = SEARCH_SCOPES.get(scope, SEARCH_SCOPES["all"])
        query = "SELECT started_at, verdict, job_id, summary_json FROM sessions"
        args: list = []
        for word in text.lower().split():
            query += (" AND (" if args else " WHERE (") + " OR ".join(f"lower({c}) LIKE ?" for c in columns) + ")"
            args += [f"%{word}%"] * len(columns)
        devices: dict[tuple, dict] = {}
        for row in self._db.execute(query + " ORDER BY started_at DESC LIMIT 500", args):
            try:
                job = json.loads(row["summary_json"])["config"]["job"]
            except (ValueError, KeyError):
                continue
            key = (job.get("serial_no", ""), job.get("asset_id", ""), job.get("brand", ""), job.get("model", ""))
            if not any(key) or key in devices:
                continue
            job.update(last_date=row["started_at"][:10], last_verdict=row["verdict"], job_id=row["job_id"])
            devices[key] = job
            if len(devices) >= limit:
                break
        return list(devices.values())

    # ------------------------------------------------------------- profiles
    def get_profile(self, brand: str, model: str, iv_set: str) -> PumpProfile | None:
        if not (brand or model):
            return None
        row = self._db.execute("SELECT * FROM profiles WHERE brand = ? AND model = ? AND iv_set = ?",
                               profile_key(brand, model, iv_set)).fetchone()
        return PumpProfile(**dict(row)) if row else None

    def _same_rate_periods(self, key: tuple, rate: float) -> list[float]:
        rows = self._db.execute(
            "SELECT period_s FROM profile_observations WHERE brand = ? AND model = ? AND iv_set = ?"
            " AND accepted = 1 AND rate_ml_h BETWEEN ? AND ? ORDER BY id DESC LIMIT 10",
            (*key, rate * (1 - SAME_RATE_BAND), rate * (1 + SAME_RATE_BAND)),
        ).fetchall()
        return [row["period_s"] for row in rows]

    def expected_period(self, brand: str, model: str, iv_set: str, rate: float) -> float | None:
        """คาบรอบปั๊มที่คาดไว้ ณ rate นี้

        1) ถ้าเคยวัดที่ rate นี้ (±2 %) ใช้ค่าเฉลี่ยของที่เคยวัดจริง
        2) ไม่เคย: คำนวณจากปริมาตรต่อรอบของโปรไฟล์ (สมมติฐานปริมาตรต่อรอบคงที่)
        """
        if not (brand or model) or rate <= 0:
            return None
        periods = self._same_rate_periods(profile_key(brand, model, iv_set), rate)
        if periods:
            return sum(periods) / len(periods)
        profile = self.get_profile(brand, model, iv_set)
        return profile.period_s(rate) if profile and profile.runs else None

    def add_observation(self, brand: str, model: str, iv_set: str, rate: float, period_s: float,
                        mean_flow: float, session_ref: str = "") -> tuple[PumpProfile | None, str]:
        """บันทึกคาบรอบปั๊มที่วัดได้ 1 ครั้ง คืน (โปรไฟล์ล่าสุด, สถานะ)

        สถานะ: "merged"    รวมเข้าปริมาตรต่อรอบของโปรไฟล์แล้ว
               "rate_only" ไม่ตรงกับปริมาตรต่อรอบของโปรไฟล์ จึงจำไว้ใช้เฉพาะ rate นี้
               "rejected"  ขัดกับที่เคยวัดที่ rate เดียวกัน (น่าจะจับรอบพลาด) ไม่นำไปใช้
               ""          ไม่มีชื่อรุ่น/ข้อมูลไม่พอ จึงไม่ได้บันทึก
        """
        if not (brand or model) or period_s <= 0 or mean_flow <= 0:
            return None, ""
        key = profile_key(brand, model, iv_set)
        profile = self.get_profile(brand, model, iv_set) or PumpProfile(*key)
        observed = mean_flow * period_s / 3600.0
        same_rate = self._same_rate_periods(key, rate)
        if same_rate:
            usual = sum(same_rate) / len(same_rate)
            accepted = abs(period_s - usual) <= MAX_DEVIATION * usual
        else:
            accepted = True
        merge = accepted and profile.accepts(observed)
        status = "merged" if merge else "rate_only" if accepted else "rejected"

        now = datetime.now().isoformat(timespec="seconds")
        self._db.execute(
            "INSERT INTO profile_observations (brand, model, iv_set, rate_ml_h, period_s, mean_flow,"
            " stroke_volume_ml, accepted, session_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (*key, rate, period_s, mean_flow, observed, int(accepted), session_ref or None, now),
        )
        if merge:
            profile.merge(observed)
            profile.updated_at = now
            self._db.execute(
                "INSERT INTO profiles (brand, model, iv_set, stroke_volume_ml, runs, updated_at) VALUES (?,?,?,?,?,?)"
                " ON CONFLICT (brand, model, iv_set) DO UPDATE SET stroke_volume_ml = excluded.stroke_volume_ml,"
                " runs = excluded.runs, updated_at = excluded.updated_at",
                (*key, profile.stroke_volume_ml, profile.runs, now),
            )
        self._db.commit()
        return profile, status

    # ------------------------------------------------- รายการตรวจเครื่องของแต่ละรุ่น
    def model_items(self, brand: str, model: str, kind: str) -> list[tuple[str, int]]:
        """รายการที่รุ่นนี้เคยใช้ [(ชื่อ, จำนวนครั้งที่ถูกติ๊ก)] ใช้บ่อยสุดก่อน — kind: "accessory" | "part" """
        if not (brand or model):
            return []
        brand_key, model_key, _ = profile_key(brand, model, "")
        rows = self._db.execute(
            "SELECT item, uses FROM model_items WHERE brand = ? AND model = ? AND kind = ?"
            " ORDER BY uses DESC, item", (brand_key, model_key, kind)).fetchall()
        return [(row["item"], row["uses"]) for row in rows]

    def remember_items(self, brand: str, model: str, kind: str, listed: list[str], checked: list[str]) -> None:
        """จำรายการของรุ่นนี้: listed = ทุกรายการที่ผู้ใช้เพิ่มเอง, checked = ที่ถูกติ๊กครั้งนี้ (นับเพิ่ม 1)"""
        if not (brand or model):
            return
        brand_key, model_key, _ = profile_key(brand, model, "")
        now = datetime.now().isoformat(timespec="seconds")
        for item in dict.fromkeys([*listed, *checked]):
            self._db.execute(
                "INSERT INTO model_items (brand, model, kind, item, uses, updated_at) VALUES (?,?,?,?,?,?)"
                " ON CONFLICT (brand, model, kind, item) DO UPDATE SET uses = uses + excluded.uses, updated_at = excluded.updated_at",
                (brand_key, model_key, kind, item, int(item in checked), now))
        self._db.commit()

    def forget_item(self, brand: str, model: str, kind: str, item: str) -> None:
        brand_key, model_key, _ = profile_key(brand, model, "")
        self._db.execute("DELETE FROM model_items WHERE brand = ? AND model = ? AND kind = ? AND item = ?",
                         (brand_key, model_key, kind, item))
        self._db.commit()

    # ----------------------------------------------------------- self-check
    def add_self_check(self, result: SelfCheckResult) -> None:
        self._db.execute(
            "INSERT INTO self_checks (measured_at, passed, rate_g_per_h, result_json) VALUES (?,?,?,?)",
            (result.measured_at, int(result.passed), result.rate_g_per_h, json.dumps(asdict(result))),
        )
        self._db.commit()

    def latest_self_check(self, day: str | None = None) -> SelfCheckResult | None:
        """self-check ล่าสุดของวันที่กำหนด (YYYY-MM-DD, ค่าเริ่มต้น = วันนี้) ไม่ว่าจะผ่านหรือไม่"""
        day = day or datetime.now().strftime("%Y-%m-%d")
        row = self._db.execute(
            "SELECT result_json FROM self_checks WHERE substr(measured_at, 1, 10) = ? ORDER BY id DESC LIMIT 1",
            (day,),
        ).fetchone()
        return SelfCheckResult(**json.loads(row["result_json"])) if row else None


_repository: Repository | None = None


def get_repository() -> Repository:
    """คลังที่ทั้งแอปใช้ร่วมกัน (จุดสลับชนิดฐานข้อมูลในอนาคต)"""
    global _repository
    if _repository is None:
        _repository = Repository()
    return _repository


def set_repository(repository: Repository | None) -> None:
    """ใช้ในการทดสอบ: สลับคลังเป็นตัวชั่วคราว"""
    global _repository
    _repository = repository
