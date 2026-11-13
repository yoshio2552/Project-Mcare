"""คลังข้อมูลของแอป (repository) — ตัวปัจจุบันคือ SQLite ไฟล์เดียว: data/deltam.db

ส่วนอื่นของระบบคุยกับ Repository เท่านั้น จะย้ายไปฐานข้อมูลอื่น (เช่น PostgreSQL เมื่อใช้หลายเครื่อง)
ก็สร้างคลาสใหม่ที่มี method ชุดเดียวกัน แล้วสลับที่ get_repository() จุดเดียว

สิ่งที่เก็บ
    sessions              ผลของแต่ละขั้นทดสอบ (แยกโหมดด้วยคอลัมน์ mode) + สรุปเต็มเป็น JSON
    profiles              โปรไฟล์ปั๊มต่อ ยี่ห้อ + รุ่น + ชุดสาย (ปริมาตรต่อรอบ)
    profile_observations  ข้อสังเกตรายครั้งที่ใช้สร้างโปรไฟล์ (rate, คาบที่วัดได้)
    self_checks           ผล self-check (การระเหย + การไหลของค่าตราชั่ง)
    window_tuning         หน้าต่าง regression / n̄ (สัดส่วนของคาบ) ต่อ ยี่ห้อ + รุ่น + ชนิด + ชุดสาย + rate
                          ที่มา (source): tuned = ปรับจากข้อมูลจริง (สอบเทียบแล้ว) · manual = ผู้ใช้แก้เอง
                          · uncalibrated = ค่าเริ่มต้นที่ผู้ใช้กดบันทึกไว้ (ยังไม่ได้สอบเทียบ — ยังเตือนทุกครั้ง)
    session_files         ลายนิ้วมือ SHA-256 ของทุกไฟล์ในโฟลเดอร์ผล (ตรวจว่าไม่ถูกแก้ภายหลัง)
ข้อมูลดิบไม่ได้อยู่ในฐานข้อมูล แต่อยู่ในโฟลเดอร์ของ session (raw.csv, intervals.csv)
เมื่อกด "เก็บ": raw.csv / prerun.csv ถูกบีบอัดเป็น .csv.gz (ไม่เสียข้อมูล — ค่าที่อ่านได้ครบทุกจุด) แล้วบันทึก SHA-256
สอบย้อนหลัง: summary.json มีค่าแก้ทั้งชุด (correction: อุณหภูมิ ความชื้น ความดัน ρw ρa Z baseline + ที่มา)
และ intervals.csv มี flow ทั้ง "สุทธิ" และ "ยังไม่แก้" ทุกช่วง — flow สุทธิ = (flow ยังไม่แก้ − baseline) × Z
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import logging
import math
import shutil
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from config.constants import APP_VERSION, DATA_DIR, SESSIONS_DIR
from core.corrections import SelfCheckResult
from core.models import Interval, SessionSummary
from core.profiles import MAX_DEVIATION, PumpProfile, profile_key, pump_key

log = logging.getLogger("deltam.store")

DATABASE_FILE = DATA_DIR / "deltam.db"
SCHEMA_VERSION = 4       # 2 = กุญแจมีชนิดเครื่อง · 3 = calibrated_at, การตัดสินใจของผู้ใช้, หน้าต่างแยก 2 ค่า, ตาราง intervals
#                          4 = window_tuning.source (tuned | manual | uncalibrated)
WINDOW_SOURCES = ("tuned", "manual", "uncalibrated")
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
    brand TEXT, model TEXT, pump_type TEXT, iv_set TEXT, stroke_volume_ml REAL, runs INTEGER, updated_at TEXT,
    calibrated_at TEXT DEFAULT '',
    PRIMARY KEY (brand, model, pump_type, iv_set)
);
CREATE TABLE IF NOT EXISTS profile_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT, model TEXT, iv_set TEXT, rate_ml_h REAL, period_s REAL, mean_flow REAL,
    stroke_volume_ml REAL, accepted INTEGER, session_id INTEGER, created_at TEXT, pump_type TEXT DEFAULT 'infusion',
    out_of_range INTEGER DEFAULT 0, decision TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS model_items (
    brand TEXT, model TEXT, kind TEXT, item TEXT, uses INTEGER DEFAULT 0, updated_at TEXT,
    PRIMARY KEY (brand, model, kind, item)
);
CREATE TABLE IF NOT EXISTS self_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    measured_at TEXT, passed INTEGER, rate_g_per_h REAL, result_json TEXT
);
CREATE TABLE IF NOT EXISTS window_tuning (
    brand TEXT, model TEXT, pump_type TEXT, iv_set TEXT, rate_ml_h REAL,
    regression_fraction REAL, half_fraction REAL, regression_points INTEGER, half_points INTEGER,
    sample_period_s REAL, score REAL, default_score REAL, sessions INTEGER, period_s REAL,
    result_json TEXT, updated_at TEXT, source TEXT DEFAULT 'tuned',
    PRIMARY KEY (brand, model, pump_type, iv_set, rate_ml_h)
);
-- ทุกช่วงวัดของทุกผลที่เก็บ (สำหรับหน้า Dashboard สถิติ: error, เวลาต่อรอบ, ปริมาตรต่อรอบ ข้ามการทดสอบ)
CREATE TABLE IF NOT EXISTS intervals (
    session_id INTEGER, idx INTEGER, chain INTEGER, t_s REAL, duration_s REAL, volume_ml REAL,
    flow_ml_h REAL, error_pct REAL, flow_raw_ml_h REAL, error_raw_pct REAL,
    PRIMARY KEY (session_id, idx)
);
CREATE TABLE IF NOT EXISTS prerun_criteria (
    brand TEXT, model TEXT, pump_type TEXT, iv_set TEXT, capture TEXT, criteria_json TEXT, updated_at TEXT,
    PRIMARY KEY (brand, model, pump_type, iv_set, capture)
);
CREATE TABLE IF NOT EXISTS session_files (
    session_id INTEGER, name TEXT, bytes INTEGER, sha256 TEXT, PRIMARY KEY (session_id, name)
);
"""
COMPRESSED = ("raw.csv", "prerun.csv")     # ไฟล์ที่บีบอัดหลังเก็บผล

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
    # index, chain, t, duration_s, flow, error_pct, flow_raw, error_raw_pct (+ raw_derived = คำนวณย้อนจากสูตร)
    intervals: list[dict] = field(default_factory=list)
    samples: list[tuple[float, float]] = field(default_factory=list)


class Repository:
    def __init__(self, path: Path = DATABASE_FILE, sessions_dir: Path = SESSIONS_DIR):
        self.path = path
        self.sessions_dir = sessions_dir
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.row_factory = sqlite3.Row
        self._migrate()
        self._db.executescript(_SCHEMA)
        self._db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self._db.commit()

    # ------------------------------------------------------------- migration
    def _columns(self, table: str) -> set[str]:
        return {row["name"] for row in self._db.execute(f"PRAGMA table_info({table})")}

    def _migrate(self) -> None:
        """ปรับฐานข้อมูลรุ่นเก่าให้ตรงกับโครงใหม่ โดยไม่ทิ้งข้อมูล (สำรองไฟล์ไว้ก่อนเปลี่ยนแต่ละรุ่น)

        v1 -> v2: profiles / profile_observations / window_tuning มีคอลัมน์ pump_type
                  ชนิดเครื่องของโปรไฟล์เดิม เอาจากผลทดสอบของรุ่น + ชุดสายนั้น (ไม่พบ = infusion เพราะเรียนรู้จากการจับรอบปั๊ม)
        v2 -> v3: profiles.calibrated_at, profile_observations.out_of_range/decision, window_tuning แยก r/h
                  (ค่าเดิมคำนวณซ้ำได้จากข้อมูลดิบ จึงสร้างใหม่), ตาราง intervals เติมจาก intervals.csv ของผลที่มีอยู่
        v3 -> v4: window_tuning.source — แถวเดิมทั้งหมดมาจากการปรับด้วยข้อมูลจริง จึงเป็น "tuned"
        """
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version >= SCHEMA_VERSION or not self._columns("profiles"):
            return                                      # ล่าสุดแล้ว หรือฐานข้อมูลใหม่
        if self.path.is_file():
            backup = self.path.with_name(f"{self.path.stem}.v{version}-backup{self.path.suffix}")
            if not backup.exists():
                self._db.commit()
                shutil.copy2(self.path, backup)
                log.info("Database backed up to %s before upgrading", backup.name)
        if "pump_type" not in self._columns("profiles"):
            self._migrate_v2()
        if version < 3:
            self._migrate_v3()
        self._migrate_v4()
        self._db.commit()
        log.info("Database upgraded to version %d", SCHEMA_VERSION)

    def _migrate_v3(self) -> None:
        if "calibrated_at" not in self._columns("profiles"):
            self._db.execute("ALTER TABLE profiles ADD COLUMN calibrated_at TEXT DEFAULT ''")
        observations = self._columns("profile_observations")
        if observations and "out_of_range" not in observations:
            self._db.execute("ALTER TABLE profile_observations ADD COLUMN out_of_range INTEGER DEFAULT 0")
            self._db.execute("ALTER TABLE profile_observations ADD COLUMN decision TEXT DEFAULT ''")
            self._db.execute("UPDATE profile_observations SET out_of_range = 1, decision = 'auto' WHERE accepted = 0")
        if self._columns("window_tuning") and "regression_fraction" not in self._columns("window_tuning"):
            self._db.execute("DROP TABLE window_tuning")
        self._db.executescript(_SCHEMA)                 # สร้างตารางใหม่ (intervals, window_tuning)
        for row in self._db.execute("SELECT id, folder, summary_json FROM sessions").fetchall():
            try:
                summary = json.loads(row["summary_json"])
                self._index_intervals(row["id"], Path(row["folder"] or ""), summary)
            except (OSError, ValueError, KeyError):
                continue

    def _migrate_v4(self) -> None:
        columns = self._columns("window_tuning")
        if columns and "source" not in columns:
            self._db.execute("ALTER TABLE window_tuning ADD COLUMN source TEXT DEFAULT 'tuned'")
            self._db.execute("UPDATE window_tuning SET source = 'tuned' WHERE source IS NULL OR source = ''")

    def _migrate_v2(self) -> None:
        types: dict[tuple, str] = {}
        for row in self._db.execute("SELECT brand, model, iv_set, pump_type FROM sessions ORDER BY started_at"):
            types[profile_key(row["brand"], row["model"], row["iv_set"])] = (row["pump_type"] or "infusion").lower()
        rows = self._db.execute("SELECT * FROM profiles").fetchall()
        self._db.execute("ALTER TABLE profiles RENAME TO profiles_v1")
        self._db.execute("CREATE TABLE profiles (brand TEXT, model TEXT, pump_type TEXT, iv_set TEXT, stroke_volume_ml REAL,"
                         " runs INTEGER, updated_at TEXT, PRIMARY KEY (brand, model, pump_type, iv_set))")
        for row in rows:
            kind = types.get((row["brand"], row["model"], row["iv_set"]), "infusion")
            self._db.execute("INSERT OR REPLACE INTO profiles VALUES (?,?,?,?,?,?,?)",
                             (row["brand"], row["model"], kind, row["iv_set"], row["stroke_volume_ml"], row["runs"],
                              row["updated_at"]))
        self._db.execute("DROP TABLE profiles_v1")
        if self._columns("profile_observations") and "pump_type" not in self._columns("profile_observations"):
            self._db.execute("ALTER TABLE profile_observations ADD COLUMN pump_type TEXT DEFAULT 'infusion'")
            self._db.execute("UPDATE profile_observations SET pump_type = COALESCE((SELECT lower(s.pump_type)"
                             " FROM sessions s WHERE s.id = profile_observations.session_id), 'infusion')")
        if self._columns("window_tuning") and "pump_type" not in self._columns("window_tuning"):
            self._db.execute("DROP TABLE window_tuning")      # ค่าที่คำนวณซ้ำได้จากข้อมูลดิบ

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
            writer.writerow(["index", "chain", "t_s", "duration_s", "flow_ml_h", "error_pct",
                             "flow_raw_ml_h", "error_raw_pct", "volume_ml"])
            for iv in intervals:
                writer.writerow([iv.index, "AB"[iv.chain], f"{iv.t:.3f}", f"{iv.duration_s:.3f}",
                                 f"{iv.flow:.4f}", f"{iv.error_pct:.4f}",
                                 f"{iv.flow_raw:.4f}", f"{iv.error_raw_pct:.4f}",
                                 f"{iv.flow * iv.duration_s / 3600.0:.5f}"])

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
        session_id = cursor.lastrowid
        self._index_intervals(session_id, folder, payload)
        try:
            self._seal(session_id, folder)
        except OSError as exc:
            log.warning("Could not compress/fingerprint %s: %s", folder, exc)
        self._db.commit()
        return str(session_id)

    def _index_intervals(self, session_id: int, folder: Path, summary: dict) -> None:
        """คัดลอกช่วงวัดลงตาราง intervals (Dashboard ค้นข้ามการทดสอบได้โดยไม่ต้องเปิดไฟล์)"""
        path = folder / "intervals.csv"
        if not path.is_file():
            return
        factor, baseline = volume_factor(summary), float(summary.get("baseline_g_per_h") or 0.0)
        target = float(summary.get("config", {}).get("target_flow") or 0.0)
        with open(path, newline="", encoding="utf-8") as f:
            for item in csv.DictReader(f):
                flow, duration = float(item["flow_ml_h"]), float(item["duration_s"])
                raw = float(item["flow_raw_ml_h"]) if item.get("flow_raw_ml_h") else flow / factor + baseline
                self._db.execute(
                    "INSERT OR REPLACE INTO intervals VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (session_id, int(item["index"]), "AB".index(item["chain"]), float(item["t_s"]), duration,
                     flow * duration / 3600.0, flow, float(item["error_pct"]), raw,
                     (raw - target) / target * 100.0 if target else None))

    # ------------------------------------------------- บีบอัด + ลายนิ้วมือ (สอบย้อนหลัง)
    @staticmethod
    def _compress(path: Path) -> None:
        """บีบอัดแบบไม่เสียข้อมูล (mtime=0 ให้ไฟล์เดิมได้ผลลัพธ์เดิมทุกครั้ง) แล้วลบต้นฉบับเมื่อสำเร็จ"""
        target = path.with_name(path.name + ".gz")
        with open(path, "rb") as src, open(target, "wb") as raw, \
                gzip.GzipFile(filename=path.name, mode="wb", fileobj=raw, compresslevel=9, mtime=0) as dst:
            shutil.copyfileobj(src, dst)
        path.unlink()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                digest.update(block)
        return digest.hexdigest()

    def _seal(self, session_id: int, folder: Path) -> None:
        for name in COMPRESSED:
            if (folder / name).is_file():
                self._compress(folder / name)
        for path in sorted(p for p in folder.iterdir() if p.is_file()):
            self._db.execute("INSERT OR REPLACE INTO session_files (session_id, name, bytes, sha256) VALUES (?,?,?,?)",
                             (session_id, path.name, path.stat().st_size, self._sha256(path)))

    def verify(self, ref: str) -> list[tuple[str, str]]:
        """ตรวจไฟล์ของผลนี้กับลายนิ้วมือตอนเก็บ: [(ชื่อไฟล์, ok | changed | missing)] — ว่าง = ผลรุ่นก่อนไม่มีบันทึก"""
        row = self._db.execute("SELECT folder FROM sessions WHERE id = ?", (ref,)).fetchone()
        if row is None:
            return []
        folder = Path(row["folder"] or "")
        checks = []
        for item in self._db.execute("SELECT name, sha256 FROM session_files WHERE session_id = ? ORDER BY name", (ref,)):
            path = folder / item["name"]
            status = "missing" if not path.is_file() else "ok" if self._sha256(path) == item["sha256"] else "changed"
            checks.append((item["name"], status))
        return checks

    @staticmethod
    def read_samples(folder: Path, name: str = "raw.csv") -> list[tuple[float, float]]:
        """อ่าน (เวลา, น้ำหนัก) จากไฟล์ที่บีบอัดแล้ว หรือไฟล์ปกติ (ผลรุ่นก่อน)"""
        packed, plain = folder / (name + ".gz"), folder / name
        opener = (lambda: gzip.open(packed, "rt", encoding="utf-8", newline="")) if packed.is_file() else \
                 (lambda: open(plain, newline="", encoding="utf-8")) if plain.is_file() else None
        if opener is None:
            return []
        with opener() as f:
            reader = csv.reader(f)
            next(reader, None)
            return [(float(r[0]), float(r[1])) for r in reader if len(r) >= 2]

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
        self._db.execute("DELETE FROM session_files WHERE session_id = ?", (ref,))
        self._db.execute("DELETE FROM intervals WHERE session_id = ?", (ref,))
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
        intervals_file = folder / "intervals.csv"
        factor, baseline = volume_factor(detail.summary), float(detail.summary.get("baseline_g_per_h") or 0.0)
        target = float(detail.summary.get("config", {}).get("target_flow") or 0.0)
        if intervals_file.is_file():
            with open(intervals_file, newline="", encoding="utf-8") as f:
                for item in csv.DictReader(f):
                    row = {
                        "index": int(item["index"]), "chain": "AB".index(item["chain"]),
                        "t": float(item["t_s"]), "duration_s": float(item["duration_s"]),
                        "flow": float(item["flow_ml_h"]), "error_pct": float(item["error_pct"]),
                        "raw_derived": not item.get("flow_raw_ml_h"),
                    }
                    if row["raw_derived"]:      # ผลรุ่นเก่า: ย้อนสูตรจากค่าแก้ที่บันทึกไว้
                        row["flow_raw"] = row["flow"] / factor + baseline
                    else:
                        row["flow_raw"] = float(item["flow_raw_ml_h"])
                    row["error_raw_pct"] = (row["flow_raw"] - target) / target * 100.0 if target else 0.0
                    detail.intervals.append(row)
        detail.samples = self.read_samples(folder)
        return detail

    def job_history(self, limit: int = 2000) -> list[dict]:
        """ข้อมูลงาน (JobInfo เป็น dict + started_at) ของงานที่เคยบันทึก ใหม่สุดก่อน 1 รายการต่องาน (ไม่นับซ้ำทุก rate)"""
        jobs, seen = [], set()
        for row in self._db.execute("SELECT started_at, job_id, summary_json FROM sessions"
                                    " ORDER BY started_at DESC, id DESC LIMIT ?", (limit,)):
            key = row["job_id"] or row["started_at"]
            if key in seen:
                continue
            seen.add(key)
            try:
                job = json.loads(row["summary_json"])["config"]["job"]
            except (ValueError, KeyError, TypeError):
                continue
            job["started_at"] = row["started_at"]
            jobs.append(job)
        return jobs

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
    # หมายเหตุ: ทุกเมธอดของสิ่งที่เรียนรู้รับ pump_type ด้วย (ค่าเริ่มต้น infusion) — กุญแจ = core.profiles.pump_key
    def get_profile(self, brand: str, model: str, iv_set: str, pump_type: str = "infusion") -> PumpProfile | None:
        if not (brand or model):
            return None
        row = self._db.execute("SELECT * FROM profiles WHERE brand = ? AND model = ? AND pump_type = ? AND iv_set = ?",
                               pump_key(brand, model, iv_set, pump_type)).fetchone()
        return PumpProfile(**dict(row)) if row else None

    def _calibrated_at(self, key: tuple) -> str:
        row = self._db.execute("SELECT calibrated_at FROM profiles WHERE brand = ? AND model = ? AND pump_type = ?"
                               " AND iv_set = ?", key).fetchone()
        return (row["calibrated_at"] or "") if row else ""

    def _same_rate_periods(self, key: tuple, rate: float) -> list[float]:
        """คาบที่เคยวัดที่ rate นี้ (เฉพาะที่ยอมรับ และหลัง Calibration ครั้งล่าสุด) ใหม่สุด 10 ครั้ง"""
        rows = self._db.execute(
            "SELECT period_s FROM profile_observations WHERE brand = ? AND model = ? AND pump_type = ? AND iv_set = ?"
            " AND accepted = 1 AND rate_ml_h BETWEEN ? AND ? AND COALESCE(created_at, '') >= ? ORDER BY id DESC LIMIT 10",
            (*key, rate * (1 - SAME_RATE_BAND), rate * (1 + SAME_RATE_BAND), self._calibrated_at(key)),
        ).fetchall()
        return [row["period_s"] for row in rows]

    def expected_period(self, brand: str, model: str, iv_set: str, rate: float,
                        pump_type: str = "infusion") -> float | None:
        return self.expected_period_info(brand, model, iv_set, rate, pump_type)[0]

    def expected_period_info(self, brand: str, model: str, iv_set: str, rate: float,
                             pump_type: str = "infusion") -> tuple[float | None, str]:
        """(คาบรอบปั๊มที่คาดไว้ ณ rate นี้, ที่มา)

        1) "rate"           เคยวัดที่ rate นี้ (±2 %) ใช้ค่าเฉลี่ยของที่เคยวัดจริง
        2) "profile"        คำนวณจากปริมาตรต่อรอบของโปรไฟล์ (สมมติฐานปริมาตรต่อรอบคงที่)
        3) "model_default"  ค่าเริ่มต้นที่ผู้ใช้กำหนดให้รุ่นนี้ใช้แทนไปก่อน (ยังไม่เคยวัด)
        """
        if not (brand or model) or rate <= 0:
            return None, ""
        periods = self._same_rate_periods(pump_key(brand, model, iv_set, pump_type), rate)
        if periods:
            return sum(periods) / len(periods), "rate"
        profile = self.get_profile(brand, model, iv_set, pump_type)
        if profile and profile.runs and profile.stroke_volume_ml > 0:
            return profile.period_s(rate), "profile"
        if profile and profile.provisional:
            return profile.period_s(rate), "model_default"
        return None, ""

    def set_model_default(self, brand: str, model: str, iv_set: str, stroke_volume_ml: float,
                          pump_type: str = "infusion") -> bool:
        """กำหนดปริมาตรต่อรอบ "ใช้แทนไปก่อน" ให้รุ่นที่ยังไม่เคยวัด (ไม่ทับโปรไฟล์ที่วัดจริงแล้ว)"""
        if not (brand or model) or stroke_volume_ml <= 0:
            return False
        existing = self.get_profile(brand, model, iv_set, pump_type)
        if existing is not None and existing.runs > 0:
            return False
        now = datetime.now().isoformat(timespec="seconds")
        self._db.execute(
            "INSERT INTO profiles (brand, model, pump_type, iv_set, stroke_volume_ml, runs, updated_at)"
            " VALUES (?,?,?,?,?,0,?) ON CONFLICT (brand, model, pump_type, iv_set) DO UPDATE SET"
            " stroke_volume_ml = excluded.stroke_volume_ml, updated_at = excluded.updated_at",
            (*pump_key(brand, model, iv_set, pump_type), stroke_volume_ml, now))
        self._db.commit()
        return True

    def check_observation(self, brand: str, model: str, iv_set: str, rate: float, period_s: float,
                          mean_flow: float, pump_type: str = "infusion") -> ObservationCheck:
        """เทียบคาบที่วัดได้กับข้อมูลเดิมของรุ่นนี้ (ไม่บันทึกอะไร) — ใช้ตัดสินว่าต้องถามผู้ใช้ไหม"""
        key = pump_key(brand, model, iv_set, pump_type)
        check = ObservationCheck(rate=rate, period_s=period_s, observed_ml=mean_flow * period_s / 3600.0)
        profile = self.get_profile(brand, model, iv_set, pump_type)
        same_rate = self._same_rate_periods(key, rate)
        if same_rate:
            usual = sum(same_rate) / len(same_rate)
            check.kind, check.expected_period_s, check.expected_ml = "rate", usual, mean_flow * usual / 3600.0
            check.deviation_pct = (period_s - usual) / usual * 100.0
        elif profile is not None and profile.runs and profile.stroke_volume_ml > 0:
            check.kind, check.expected_ml = "volume", profile.stroke_volume_ml
            check.expected_period_s = profile.period_s(rate)
            check.deviation_pct = (check.observed_ml - profile.stroke_volume_ml) / profile.stroke_volume_ml * 100.0
        else:
            check.status = "new"
            return check
        check.status = "out_of_range" if abs(check.deviation_pct) > MAX_DEVIATION * 100.0 else "ok"
        check.runs = profile.runs if profile else 0
        check.streak = self._out_of_range_streak(key)
        return check

    def _out_of_range_streak(self, key: tuple) -> int:
        """จำนวนครั้งติดกันล่าสุด (หลัง Calibration) ที่คาบไม่ตรงกับข้อมูลเดิม"""
        streak = 0
        for row in self._db.execute(
                "SELECT out_of_range FROM profile_observations WHERE brand = ? AND model = ? AND pump_type = ?"
                " AND iv_set = ? AND COALESCE(created_at, '') >= ? ORDER BY id DESC LIMIT 20", (*key, self._calibrated_at(key))):
            if not row["out_of_range"]:
                break
            streak += 1
        return streak

    def recalibrate(self, brand: str, model: str, iv_set: str, pump_type: str = "infusion", since: str = "") -> bool:
        """Calibration รอบปั๊มใหม่: ล้างปริมาตรต่อรอบ + หน้าต่างที่ปรับแล้วของรุ่นนี้ แล้วเริ่มเรียนรู้จากข้อมูลตั้งแต่ since
        (ข้อมูลเก่ายังอยู่ครบ แค่ไม่ถูกใช้ — สอบย้อนหลังได้)"""
        if not (brand or model):
            return False
        key = pump_key(brand, model, iv_set, pump_type)
        since = since or datetime.now().isoformat(timespec="microseconds")
        self._db.execute(
            "INSERT INTO profiles (brand, model, pump_type, iv_set, stroke_volume_ml, runs, updated_at, calibrated_at)"
            " VALUES (?,?,?,?,0,0,?,?) ON CONFLICT (brand, model, pump_type, iv_set) DO UPDATE SET"
            " stroke_volume_ml = 0, runs = 0, updated_at = excluded.updated_at, calibrated_at = excluded.calibrated_at",
            (*key, since, since))
        self._db.execute("DELETE FROM window_tuning WHERE brand = ? AND model = ? AND pump_type = ? AND iv_set = ?", key)
        self._db.commit()
        return True

    def add_observation(self, brand: str, model: str, iv_set: str, rate: float, period_s: float,
                        mean_flow: float, session_ref: str = "",
                        pump_type: str = "infusion", decision: str = "auto") -> tuple[PumpProfile | None, str]:
        """บันทึกคาบรอบปั๊มที่วัดได้ 1 ครั้ง คืน (โปรไฟล์ล่าสุด, สถานะ)

        decision: "auto"        ตัดสินเอง (คาบขัดกับ rate เดียวกัน = ไม่ใช้, ปริมาตรไม่ตรงโปรไฟล์ = ใช้เฉพาะ rate นี้)
                  "add"         ผู้ใช้ยืนยันให้เก็บรวม แม้ต่างจากข้อมูลเดิมเกินเกณฑ์
                  "skip"        ผู้ใช้ไม่เก็บ (บันทึกไว้แต่ไม่ใช้)
                  "calibration" ครั้งแรกหลัง Calibration ใหม่ (เริ่มโปรไฟล์จากค่านี้)
        สถานะ: "merged" รวมเข้าปริมาตรต่อรอบแล้ว · "rate_only" ใช้เฉพาะ rate นี้ · "rejected"/"declined" ไม่ใช้
               "" ไม่มีชื่อรุ่น/ข้อมูลไม่พอ จึงไม่ได้บันทึก
        """
        if not (brand or model) or period_s <= 0 or mean_flow <= 0:
            return None, ""
        key = pump_key(brand, model, iv_set, pump_type)
        profile = self.get_profile(brand, model, iv_set, pump_type) or PumpProfile(*key)
        observed = mean_flow * period_s / 3600.0
        check = self.check_observation(brand, model, iv_set, rate, period_s, mean_flow, pump_type)
        out_of_range = check.status == "out_of_range"
        same_rate_ok = not (check.kind == "rate" and out_of_range)
        if decision == "skip":
            accepted = False
        elif decision in ("add", "calibration"):
            accepted = True
        else:
            accepted = same_rate_ok
        merge = accepted and (decision == "calibration" or profile.accepts(observed))
        status = "merged" if merge else "rate_only" if accepted else "declined" if decision == "skip" else "rejected"

        now = datetime.now().isoformat(timespec="microseconds")     # ละเอียดพอเทียบกับเวลา Calibration
        self._db.execute(
            "INSERT INTO profile_observations (brand, model, pump_type, iv_set, rate_ml_h, period_s, mean_flow,"
            " stroke_volume_ml, accepted, session_id, created_at, out_of_range, decision)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (*key, rate, period_s, mean_flow, observed, int(accepted), session_ref or None, now,
             int(out_of_range and decision != "calibration"), decision),
        )
        if merge:
            profile.merge(observed)
            profile.updated_at = now
            self._db.execute(
                "INSERT INTO profiles (brand, model, pump_type, iv_set, stroke_volume_ml, runs, updated_at)"
                " VALUES (?,?,?,?,?,?,?) ON CONFLICT (brand, model, pump_type, iv_set) DO UPDATE SET"
                " stroke_volume_ml = excluded.stroke_volume_ml, runs = excluded.runs, updated_at = excluded.updated_at",
                (*key, profile.stroke_volume_ml, profile.runs, now),
            )
        self._db.commit()
        return profile, status

    # ------------------------------------------------- เกณฑ์ช่วงก่อนวัดเฉพาะรุ่น (ยี่ห้อ + รุ่น + ชนิด + ชุดสาย)
    def prerun_criteria(self, brand: str, model: str, iv_set: str, pump_type: str, group: str) -> dict | None:
        if not (brand or model):
            return None
        row = self._db.execute("SELECT criteria_json FROM prerun_criteria WHERE brand = ? AND model = ? AND pump_type = ?"
                               " AND iv_set = ? AND capture = ?", (*pump_key(brand, model, iv_set, pump_type), group)).fetchone()
        return json.loads(row["criteria_json"]) if row else None

    def save_prerun_criteria(self, brand: str, model: str, iv_set: str, pump_type: str, group: str,
                             criteria: dict | None) -> bool:
        """บันทึกเกณฑ์เฉพาะรุ่น (None = ลบ กลับไปใช้ค่าเริ่มต้นของกลุ่ม)"""
        if not (brand or model):
            return False
        key = (*pump_key(brand, model, iv_set, pump_type), group)
        if criteria is None:
            self._db.execute("DELETE FROM prerun_criteria WHERE brand = ? AND model = ? AND pump_type = ? AND iv_set = ?"
                             " AND capture = ?", key)
        else:
            self._db.execute("INSERT OR REPLACE INTO prerun_criteria VALUES (?,?,?,?,?,?,?)",
                             (*key, json.dumps(criteria), datetime.now().isoformat(timespec="seconds")))
        self._db.commit()
        return True

    # ------------------------------------------------- ปรับขนาดหน้าต่างจากข้อมูลย้อนหลัง
    def tuning_datasets(self, brand: str, model: str, iv_set: str, rate: float | None = None,
                        limit: int = 5, pump_type: str = "infusion") -> dict[float, list]:
        """ข้อมูลดิบของการทดสอบแบบจับรอบปั๊มที่ "ครบ" ของรุ่นนี้ {rate: [Dataset]} ใหม่สุดก่อน ไม่เกิน limit ต่อ rate"""
        from core.tuning import Dataset, reference_period
        key = pump_key(brand, model, iv_set, pump_type)
        from core.capture_check import check_summary
        query = ("SELECT id, folder, target_flow, brand, model, iv_set, pump_type, summary_json FROM sessions"
                 " WHERE end_reason = 'completed' AND verdict != 'INVALID'"
                 " AND json_extract(summary_json, '$.config.strategy') = 'pump_cycle' AND started_at >= ?")
        args: list = [self._calibrated_at(key)]          # เฉพาะข้อมูลหลัง Calibration รอบปั๊มครั้งล่าสุด
        if rate:
            query += " AND target_flow BETWEEN ? AND ?"
            args += [rate * (1 - SAME_RATE_BAND), rate * (1 + SAME_RATE_BAND)]
        groups: dict[float, list] = {}
        for row in self._db.execute(query + " ORDER BY started_at DESC", args):
            if pump_key(row["brand"], row["model"], row["iv_set"], row["pump_type"]) != key:
                continue
            try:                                         # ผลเก่าที่จับรอบผิด (ตรวจย้อนหลัง) ไม่ใช้ปรับหน้าต่าง
                check = check_summary(json.loads(row["summary_json"]))
            except ValueError:
                check = None
            if check is not None and check.invalid:
                continue
            group = next((r for r in groups if abs(r - row["target_flow"]) <= SAME_RATE_BAND * r), row["target_flow"])
            if len(groups.setdefault(group, [])) >= limit:
                continue
            folder = Path(row["folder"] or "")
            samples = self.read_samples(folder)
            durations = []
            if (folder / "intervals.csv").is_file():
                with open(folder / "intervals.csv", newline="", encoding="utf-8") as f:
                    durations = [float(item["duration_s"]) for item in csv.DictReader(f)]
            period = reference_period(samples, self.expected_period(brand, model, iv_set, group, pump_type), durations)
            if samples and period:
                groups[group].append(Dataset(samples, period, str(row["id"])))
        return {rate: data for rate, data in groups.items() if data}

    def save_tuning(self, brand: str, model: str, iv_set: str, result, pump_type: str = "infusion",
                    replace_manual: bool = False) -> bool:
        """บันทึกผลปรับหน้าต่างจากข้อมูลจริง (source = tuned) — คืน False ถ้าไม่ได้บันทึก

        ค่าที่ผู้ใช้แก้เอง (manual) ไม่ถูกทับ เว้นแต่ replace_manual (แผน Calibration รอบปั๊ม)
        ค่าเริ่มต้นที่บันทึกไว้ (uncalibrated) ถูกแทนที่เสมอ — ข้อมูลจริงดีกว่า
        """
        fractions = result.recommended()
        if fractions is None or not (brand or model):
            return False
        key = pump_key(brand, model, iv_set, pump_type)
        existing = self._window_row(key, result.rate)
        if existing is not None and existing["source"] == "manual" and not replace_manual:
            return False
        points = result.points(fractions)
        self._db.execute(
            "INSERT OR REPLACE INTO window_tuning (brand, model, pump_type, iv_set, rate_ml_h, regression_fraction,"
            " half_fraction, regression_points, half_points, sample_period_s, score, default_score, sessions, period_s,"
            " result_json, updated_at, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'tuned')",
            (*key, round(existing["rate_ml_h"] if existing is not None else result.rate, 3), fractions[0],
             fractions[1], points[0], points[1], result.sample_period_s, result.best.score, result.current_score,
             result.sessions, result.period_s, json.dumps(asdict(result)), datetime.now().isoformat(timespec="seconds")))
        self._db.commit()
        return True

    def _window_row(self, key: tuple, rate: float):
        """แถวหน้าต่างของ rate นี้ (±2 %) หรือ None"""
        return self._db.execute(
            "SELECT * FROM window_tuning WHERE brand = ? AND model = ? AND pump_type = ? AND iv_set = ?"
            " AND rate_ml_h BETWEEN ? AND ? ORDER BY abs(rate_ml_h - ?) LIMIT 1",
            (*key, rate * (1 - SAME_RATE_BAND), rate * (1 + SAME_RATE_BAND), rate)).fetchone()

    def save_window(self, brand: str, model: str, iv_set: str, pump_type: str, rate: float,
                    regression_fraction: float, half_fraction: float, source: str,
                    period_s: float | None = None, sample_period_s: float | None = None) -> bool:
        """บันทึกหน้าต่างของ 1 rate ที่ผู้ใช้กำหนด (source = manual | uncalibrated)

        เก็บเป็นสัดส่วนของคาบ (จำนวนจุดคำนวณใหม่ตามคาบ/ความถี่ตราชั่งจริงตอนวัด)
        uncalibrated ไม่ทับค่าที่สอบเทียบแล้วหรือที่ผู้ใช้แก้เอง · ค่าเดิมถูกเก็บไว้ใน result_json (สอบย้อนหลัง)
        """
        if not (brand or model) or rate <= 0 or source not in ("manual", "uncalibrated"):
            return False
        key = pump_key(brand, model, iv_set, pump_type)
        existing = self._window_row(key, rate)
        if existing is not None and source == "uncalibrated" and existing["source"] in ("tuned", "manual"):
            return False
        regression = half = None
        if period_s and sample_period_s:
            from core.windows import cycle_windows
            windows = cycle_windows(period_s, sample_period_s, regression_fraction, half_fraction)
            regression, half = windows.regression, windows.half
        previous = {k: existing[k] for k in existing.keys() if k != "result_json"} if existing is not None else None
        self._db.execute(
            "INSERT OR REPLACE INTO window_tuning (brand, model, pump_type, iv_set, rate_ml_h, regression_fraction,"
            " half_fraction, regression_points, half_points, sample_period_s, score, default_score, sessions, period_s,"
            " result_json, updated_at, source) VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL,0,?,?,?,?)",
            (*key, round(existing["rate_ml_h"] if existing is not None else rate, 3), regression_fraction,
             half_fraction, regression, half, sample_period_s, period_s,
             json.dumps({"source": source, "previous": previous}), datetime.now().isoformat(timespec="seconds"),
             source))
        self._db.commit()
        return True

    def delete_window(self, brand: str, model: str, iv_set: str, pump_type: str, rate: float) -> bool:
        key = pump_key(brand, model, iv_set, pump_type)
        cursor = self._db.execute(
            "DELETE FROM window_tuning WHERE brand = ? AND model = ? AND pump_type = ? AND iv_set = ?"
            " AND rate_ml_h BETWEEN ? AND ?", (*key, rate * (1 - SAME_RATE_BAND), rate * (1 + SAME_RATE_BAND)))
        self._db.commit()
        return cursor.rowcount > 0

    def calibration_models(self) -> list[dict]:
        """ทุก ยี่ห้อ + รุ่น + ชนิด + ชุดสาย ที่มีข้อมูลรอบปั๊ม/หน้าต่าง (สำหรับหน้าข้อมูลสอบเทียบในตั้งค่า)

        ชื่อที่แสดงเอาตัวสะกดล่าสุดจากผลทดสอบ (กุญแจในฐานข้อมูลเป็นตัวพิมพ์เล็ก)
        """
        models: dict[tuple, dict] = {}
        for row in self._db.execute("SELECT brand, model, pump_type, iv_set, stroke_volume_ml, runs, calibrated_at"
                                    " FROM profiles"):
            key = (row["brand"], row["model"], row["pump_type"], row["iv_set"])
            models[key] = {"stroke_volume_ml": row["stroke_volume_ml"], "runs": row["runs"],
                           "calibrated_at": row["calibrated_at"] or "", "rates": 0, "tuned": 0}
        for row in self._db.execute("SELECT brand, model, pump_type, iv_set, count(*) AS n,"
                                    " sum(source = 'tuned') AS tuned FROM window_tuning GROUP BY 1, 2, 3, 4"):
            key = (row["brand"], row["model"], row["pump_type"], row["iv_set"])
            entry = models.setdefault(key, {"stroke_volume_ml": 0.0, "runs": 0, "calibrated_at": "", "rates": 0, "tuned": 0})
            entry["rates"], entry["tuned"] = row["n"], row["tuned"] or 0
        names: dict[tuple, tuple] = {}
        for row in self._db.execute("SELECT brand, model, iv_set, pump_type FROM sessions ORDER BY started_at"):
            names[pump_key(row["brand"], row["model"], row["iv_set"], row["pump_type"])] = (
                row["brand"] or "", row["model"] or "", row["iv_set"] or "")
        result = []
        for key, entry in models.items():
            brand, model, iv_set = names.get(key, (key[0], key[1], key[3]))
            result.append({"brand": brand, "model": model, "pump_type": key[2], "iv_set": iv_set, **entry})
        return sorted(result, key=lambda m: (m["pump_type"], m["brand"].lower(), m["model"].lower(), m["iv_set"].lower()))

    def latest_sample_period(self) -> float | None:
        """ช่วงเวลาต่อจุดของตราชั่งจากผลล่าสุดที่บันทึกไว้ (ใช้ประมาณจำนวนจุดก่อนต่อตราชั่ง)"""
        row = self._db.execute("SELECT json_extract(summary_json, '$.sample_period_s') AS dt FROM sessions"
                               " WHERE json_extract(summary_json, '$.sample_period_s') > 0"
                               " ORDER BY started_at DESC LIMIT 1").fetchone()
        return float(row["dt"]) if row and row["dt"] else None

    def window_fractions(self, brand: str, model: str, iv_set: str, rate: float, default: tuple[float, float],
                         pump_type: str = "infusion") -> tuple[float, float, str]:
        """(r regression, h n_bar, ที่มา) ของ rate นี้ — ค่าแต่ละ rate แยกกัน ไม่ใช้ค่าเดียวทุก rate

        ที่มา: "tuned"        ปรับจากข้อมูลของ rate นี้เอง (± 2 %) = สอบเทียบแล้ว
               "manual"       ผู้ใช้แก้เองในหน้าข้อมูลสอบเทียบ (ยังเตือนให้สอบเทียบ)
               "uncalibrated" ค่าเริ่มต้นที่ผู้ใช้กดบันทึกไว้ (ยังไม่ได้สอบเทียบ)
               "interpolated" rate นี้ยังไม่มีค่า แต่อยู่ระหว่าง 2 rate ที่สอบเทียบแล้ว (เทียบสัดส่วนบนสเกล log ของ rate)
               "default"      ยังไม่มีข้อมูลของ rate นี้ — ใช้สัดส่วนเริ่มต้นจากหน้าตั้งค่า (ปรับเองหลังเก็บผลครั้งแรก)
        """
        if not (brand or model) or rate <= 0:
            return default[0], default[1], "default"
        rows = sorted(self._db.execute(
            "SELECT rate_ml_h, regression_fraction, half_fraction, source FROM window_tuning WHERE brand = ? AND model = ?"
            " AND pump_type = ? AND iv_set = ?", pump_key(brand, model, iv_set, pump_type)).fetchall(),
            key=lambda r: r["rate_ml_h"])
        same = next((r for r in rows if abs(r["rate_ml_h"] - rate) <= SAME_RATE_BAND * rate), None)
        if same is not None:
            return same["regression_fraction"], same["half_fraction"], same["source"] or "tuned"
        rows = [r for r in rows if (r["source"] or "tuned") == "tuned"]     # เทียบจาก rate ที่สอบเทียบแล้วเท่านั้น
        below = [r for r in rows if r["rate_ml_h"] < rate]
        above = [r for r in rows if r["rate_ml_h"] > rate]
        if below and above:
            low, high = below[-1], above[0]
            share = (math.log(rate) - math.log(low["rate_ml_h"])) / (math.log(high["rate_ml_h"]) - math.log(low["rate_ml_h"]))
            mix = lambda name: low[name] + (high[name] - low[name]) * share
            return round(mix("regression_fraction"), 3), round(mix("half_fraction"), 3), "interpolated"
        return default[0], default[1], "default"

    def tuned_windows(self, brand: str, model: str, iv_set: str, pump_type: str = "infusion") -> list[dict]:
        """ค่าหน้าต่างที่ปรับแล้วทุก rate ของรุ่นนี้ (สำหรับแสดงผล/Dashboard)"""
        rows = self._db.execute(
            "SELECT rate_ml_h, regression_fraction, half_fraction, regression_points, half_points, sample_period_s,"
            " score, default_score, sessions, period_s, updated_at, source FROM window_tuning WHERE brand = ? AND model = ?"
            " AND pump_type = ? AND iv_set = ? ORDER BY rate_ml_h", pump_key(brand, model, iv_set, pump_type))
        return [dict(row) for row in rows]

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


def volume_factor(summary: dict) -> float:
    """ปัจจัย Z (ml/g) ที่ผลนี้ใช้ — ผลรุ่นก่อนมี Z ใช้ 1/ความหนาแน่น (ตอนนั้นยังไม่แก้แรงลอยตัว)"""
    z = float(summary.get("ml_per_g") or 0.0)
    if z > 0:
        return z
    density = float(summary.get("density_g_per_ml") or 0.0)
    return 1.0 / density if density > 0 else 1.0


def raw_result(summary: dict) -> tuple[float | None, float | None, bool]:
    """(flow ยังไม่แก้, error ยังไม่แก้, คำนวณย้อนไหม) ของผล 1 รายการ — ผลเก่าที่ไม่ได้เก็บไว้ ย้อนสูตรให้"""
    target = float(summary.get("config", {}).get("target_flow") or 0.0)
    flow = summary.get("mean_flow_raw")
    derived = flow is None
    if derived and summary.get("mean_flow") is not None:
        flow = summary["mean_flow"] / volume_factor(summary) + float(summary.get("baseline_g_per_h") or 0.0)
    if flow is None:
        return None, None, derived
    error = summary.get("error_raw_pct")
    if error is None or derived:
        error = (flow - target) / target * 100.0 if target else None
    return flow, error, derived


@dataclass
class ObservationCheck:
    """ผลเทียบคาบรอบปั๊มครั้งนี้กับข้อมูลเดิมของรุ่น (ก่อนบันทึก)"""
    rate: float = 0.0
    period_s: float = 0.0
    observed_ml: float = 0.0            # ปริมาตรต่อรอบที่วัดได้
    status: str = "new"                 # new = ยังไม่มีข้อมูล · ok = ตรงเกณฑ์ · out_of_range = ต่างเกินเกณฑ์
    kind: str = ""                      # rate = เทียบกับคาบที่เคยวัดที่ rate นี้ · volume = เทียบกับปริมาตรต่อรอบ
    expected_period_s: float = 0.0
    expected_ml: float = 0.0
    deviation_pct: float = 0.0
    runs: int = 0                       # จำนวนครั้งที่โปรไฟล์เรียนรู้มา
    streak: int = 0                     # ครั้งก่อนหน้าติดกันที่ต่างเกินเกณฑ์ (ไม่รวมครั้งนี้)


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
