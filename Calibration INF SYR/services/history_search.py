"""ค้นหา / คัดกรองผลในหน้าประวัติ (ไม่มี Qt — ทดสอบได้ตรงๆ)

ค้นเร็ว (ช่องค้นหาช่องเดียว) — ทุกคำต้องเจอ (AND):
  - คำทั่วไป: หาในข้อมูลงานแทบทุกช่อง (โรงพยาบาล จังหวัด หน่วยงาน ยี่ห้อ รุ่น ชุดสาย S/N ครุภัณฑ์ ผู้ทดสอบ เลขงาน
    อุปกรณ์/อะไหล่ หมายเหตุ) + วันที่หลายแบบ (2026-11-18 · 18/11/2026 · 18/11/2569 · ปี 2569 / 2026 · พ.ย.) + rate
  - ชนิดเครื่อง: inf / infusion / mci / อินฟิวชั่น / เครื่องให้สารละลาย · syr / syringe / mcs / ไซริงค์ / กระบอกฉีด
  - ผล: ผ่าน / pass · ไม่ผ่าน / fail · ใช้ไม่ได้ / invalid (เทียบตรงตัว — "ผ่าน" ไม่เจอ "ไม่ผ่าน")
  - โหมด: calibration / สอบเทียบ · inspection / ตรวจสภาพ · quick
  - ระบุช่อง: สถานที่:ขอนแก่น · ผู้ทำ:สมชาย · รุ่น:TE-171 · ปี:2569 · rate:50 · ชุดสาย:terumo (ดู FIELD_ALIASES)
ช่องผลตรวจรายข้อ / ค่าของใบ (checks, report) ไม่ถูกค้น — คำว่า "fail" ในผลตรวจรายข้อทำให้เจอผิดงาน

คัดกรองขั้นสูง (AdvancedFilter) — เลือกจากค่าที่มีจริง: สถานที่ ชนิดเครื่อง ยี่ห้อ รุ่น ชุดสาย ผู้ทดสอบ ปี (พ.ศ.) ช่วงวันที่ ผล
"""
from __future__ import annotations

from dataclasses import dataclass, fields as dc_fields
from datetime import date, datetime

from core.capture_check import effective_verdict

THAI_MONTHS = ("ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.")
PUMP_WORDS = {
    "infusion": {"inf", "infusion", "mci", "อินฟิวชั่น", "อินฟิวชัน", "เครื่องให้สารละลาย"},
    "syringe": {"syr", "syringe", "mcs", "ไซริงค์", "ไซริ้งค์", "กระบอกฉีด", "เครื่องฉีดยา"},
}
VERDICT_WORDS = {
    "PASS": {"pass", "ผ่าน"},
    "FAIL": {"fail", "ไม่ผ่าน"},
    "INVALID": {"invalid", "ใช้ไม่ได้"},
}
MODE_WORDS = {
    "calibration": {"calibration", "cal", "สอบเทียบ"},
    "inspection": {"inspection", "ตรวจสภาพ"},
    "quick_test": {"quick", "quicktest", "quick_test"},
    "repeatability": {"repeat", "repeatability", "2sd", "ความซ้ำ"},
}
# ชื่อช่องที่พิมพ์นำหน้า ":" ได้ -> ช่องของ record
FIELD_ALIASES = {
    "site": ("site", "สถานที่", "รพ", "โรงพยาบาล", "hospital"),
    "province": ("province", "จังหวัด"),
    "department": ("dept", "department", "หน่วยงาน", "แผนก"),
    "pump": ("type", "ชนิด", "ชนิดเครื่อง"),
    "brand": ("brand", "ยี่ห้อ"),
    "model": ("model", "รุ่น"),
    "ivset": ("set", "iv", "ivset", "ชุดสาย", "syringe_set"),
    "operator": ("op", "operator", "ผู้ทำ", "ผู้ทดสอบ", "ช่าง"),
    "serial": ("sn", "serial", "s/n", "หมายเลขเครื่อง"),
    "asset": ("asset", "ครุภัณฑ์"),
    "job": ("job", "งาน", "เลขงาน"),
    "year": ("year", "ปี"),
    "rate": ("rate", "อัตรา"),
    "verdict": ("result", "ผล"),
    "mode": ("mode", "โหมด"),
    # 2026-11-20: หมายเหตุ / อะไหล่ / เคลมประกัน จากขั้นที่ 1–2 ของ wizard + ข้อมูลจาก Google Sheet
    "remark": ("note", "notes", "remark", "หมายเหตุ"),
    "parts": ("part", "parts", "อะไหล่"),
    "warranty": ("warranty", "claim", "ประกัน", "เคลม"),
    "sheet": ("sheet", "ชีต", "ชีท"),
}
_ALIAS_TO_FIELD = {alias: name for name, aliases in FIELD_ALIASES.items() for alias in aliases}
_NOT_SEARCHED = {"checks", "check_notes", "checks_version", "report", "accessory_usage", "pump_type"}


def _started(session: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(str(session.get("started_at") or ""))
    except ValueError:
        return None


def record(session: dict) -> dict:
    """ช่องที่ค้น/กรองได้ของ 1 ผล (ค่าตัวพิมพ์เล็ก ยกเว้น date/rate)"""
    config = session.get("config") or {}
    job = config.get("job") or {}
    when = _started(session)
    ivset = " ".join(str(p).strip() for p in (job.get("accessory_brand"), job.get("accessory")) if str(p or "").strip())
    return {
        "site": str(job.get("site") or "").strip(),
        "province": str(job.get("province") or "").strip(),
        "department": str(job.get("department") or "").strip(),
        "pump": str(job.get("pump_type") or "infusion"),
        "brand": str(job.get("brand") or "").strip(),
        "model": str(job.get("model") or "").strip(),
        "ivset": ivset,
        "operator": str(job.get("operator") or "").strip(),
        "serial": str(job.get("serial_no") or "").strip(),
        "asset": str(job.get("asset_id") or "").strip(),
        "job": " ".join(str(p) for p in (job.get("job_no"), config.get("job_id")) if p),
        "date": when.date() if when else None,
        "year": (when.year + 543) if when else None,
        "rate": float(config.get("target_flow") or 0.0),
        "verdict": effective_verdict(session),
        "mode": str(config.get("run_mode") or ""),
        "remark": str(job.get("notes") or "").strip(),
        "parts": ", ".join(str(p) for p in job.get("parts_replaced") or []),
        "warranty": ", ".join(str(p) for p in job.get("parts_warranty") or []),
        "sheet": "",            # หน้าประวัติเติมข้อความของแถว Google Sheet ที่จับคู่ได้ (services/sheets.py)
    }


def _date_words(when: date | None) -> list[str]:
    if when is None:
        return []
    be = when.year + 543
    return [when.isoformat(), f"{when.day:02d}/{when.month:02d}/{when.year}", f"{when.day}/{when.month}/{when.year}",
            f"{when.day:02d}/{when.month:02d}/{be}", f"{when.day}/{when.month}/{be}", str(be), str(when.year),
            THAI_MONTHS[when.month - 1], f"{when.year}-{when.month:02d}"]


def _haystack(session: dict, rec: dict) -> str:
    job = (session.get("config") or {}).get("job") or {}
    parts = []
    for name, value in job.items():
        if name in _NOT_SEARCHED or value in (None, ""):
            continue
        parts.append(" ".join(map(str, value)) if isinstance(value, (list, tuple)) else str(value))
    parts += [str((session.get("config") or {}).get("job_id") or ""), str(session.get("started_at") or "")]
    parts += _date_words(rec["date"])
    parts.append(f"{rec['rate']:g}")
    parts.append(str(rec.get("sheet") or ""))
    return " ".join(parts).lower()


def _alias_hit(word: str, table: dict) -> str | None:
    return next((key for key, words in table.items() if word in words), None)


def _field_match(rec: dict, name: str, value: str) -> bool:
    value = value.strip().lower()
    if not value:
        return True
    if name == "pump":
        pump = _alias_hit(value, PUMP_WORDS) or value
        return rec["pump"] == pump
    if name == "verdict":
        return rec["verdict"] == (_alias_hit(value, VERDICT_WORDS) or value.upper())
    if name == "mode":
        return rec["mode"] == (_alias_hit(value, MODE_WORDS) or value)
    if name == "year":
        if rec["year"] is None or not value.isdigit():
            return False
        year = int(value)
        return rec["year"] == (year + 543 if year < 2400 else year)       # ปี ค.ศ. ก็ได้
    if name == "rate":
        try:
            return abs(rec["rate"] - float(value)) < 1e-6
        except ValueError:
            return False
    return value in str(rec.get(name) or "").lower()


def quick_match(session: dict, text: str, rec: dict | None = None) -> bool:
    words = text.lower().split()
    if not words:
        return True
    rec = rec or record(session)
    haystack = None
    for word in words:
        key, sep, value = word.partition(":")
        if sep and key in _ALIAS_TO_FIELD:
            if not _field_match(rec, _ALIAS_TO_FIELD[key], value):
                return False
            continue
        pump = _alias_hit(word, PUMP_WORDS)
        if pump is not None:
            if rec["pump"] != pump:
                return False
            continue
        verdict = _alias_hit(word, VERDICT_WORDS)
        if verdict is not None:
            if rec["verdict"] != verdict:
                return False
            continue
        mode = _alias_hit(word, MODE_WORDS)
        if mode is not None:
            if rec["mode"] != mode:
                return False
            continue
        if haystack is None:
            haystack = rec.get("_hay")
            if haystack is None:                # สร้างครั้งเดียวต่อผล (พิมพ์ทีละตัวไม่ต้องสร้างใหม่ทุกครั้ง)
                haystack = rec["_hay"] = _haystack(session, rec)
        if word not in haystack:
            return False
    return True


@dataclass
class AdvancedFilter:
    """ตัวกรองขั้นสูง — ช่องว่าง/None = ไม่กรอง · ข้อความเทียบแบบมีคำนี้อยู่ (ไม่สนตัวพิมพ์)"""
    site: str = ""
    pump: str = ""              # infusion | syringe
    brand: str = ""
    model: str = ""
    ivset: str = ""
    operator: str = ""
    year: int | None = None     # พ.ศ.
    date_from: date | None = None
    date_to: date | None = None
    verdict: str = ""           # PASS | FAIL | INVALID

    def active(self) -> list[str]:
        """ชื่อช่องที่กำลังกรอง"""
        return [f.name for f in dc_fields(self) if getattr(self, f.name) not in ("", None)]

    def matches(self, rec: dict) -> bool:
        for name in ("site", "brand", "model", "ivset", "operator"):
            want = getattr(self, name).strip().lower()
            if want and want not in str(rec.get(name) or "").lower():
                return False
        if self.pump and rec["pump"] != self.pump:
            return False
        if self.verdict and rec["verdict"] != self.verdict:
            return False
        if self.year is not None and rec["year"] != self.year:
            return False
        if self.date_from is not None and (rec["date"] is None or rec["date"] < self.date_from):
            return False
        if self.date_to is not None and (rec["date"] is None or rec["date"] > self.date_to):
            return False
        return True


def distinct(records: list[dict], name: str, where: dict | None = None) -> list[str]:
    """ค่าที่มีจริงของช่องหนึ่ง (เรียงตัวอักษร ไม่ซ้ำ ไม่สนตัวพิมพ์) — where = กรองก่อน เช่น รุ่นของยี่ห้อที่เลือก"""
    seen: dict[str, str] = {}
    for rec in records:
        if where and any(value and str(rec.get(k) or "").lower() != value.lower() for k, value in where.items()):
            continue
        value = str(rec.get(name) or "").strip()
        if value and value.lower() not in seen:
            seen[value.lower()] = value
    return sorted(seen.values(), key=str.lower)


def years(records: list[dict]) -> list[int]:
    return sorted({rec["year"] for rec in records if rec["year"]}, reverse=True)
