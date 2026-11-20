"""Google Sheet: ดึง ค้นหา และแก้ข้อมูลงาน (ผู้ใช้ 2026-11-20 — ออกแบบเดิมใน docs/google-sheet-sync.md)

แหล่งข้อมูลหลายลิงก์ (config.settings.SheetSettings.sources) — คอลัมน์เหมือนกันหรือต่างกันก็ได้ จับคู่คอลัมน์เองต่อแหล่ง
    csv     ลิงก์ Google Sheet ที่แชร์ "ทุกคนที่มีลิงก์ดูได้" หรือ "เผยแพร่เป็น CSV" — อ่านอย่างเดียว ไม่ต้องมีบัญชี/คีย์
    script  Apps Script Web App ของผู้ใช้ (โค้ดใน APPS_SCRIPT ด้านล่าง วางใน Sheet → ส่วนขยาย → Apps Script → ทำให้ใช้งานได้)
            อ่าน + แก้ค่าในแถว + เพิ่มคอลัมน์ใหม่ + เพิ่มแถว — ไม่ต้องเก็บรหัสผ่าน Google ในโปรแกรม (มีรหัสลับ token กันคนอื่นเรียก)
ข้อมูลที่ดึงมาเก็บสำเนาไว้ที่ data/sheets_cache.json (เปิดโปรแกรมตอนไม่มีเน็ตก็ยังค้นได้) — ไม่เขียนทับผลทดสอบใดๆ
ใช้ใน: ฟอร์มงานใหม่ (พิมพ์เลขงาน/S/N ที่มีใน Sheet -> เติมช่องที่ยังว่าง) · หน้าประวัติ (ค้นหา + แผงรายละเอียด + แก้ใน Sheet)

ชื่อช่องของ DeltaM ที่จับคู่ได้ = FIELDS · ช่องระบุงาน (ใช้จับคู่แถว) = KEY_FIELDS
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import threading
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from config.constants import DATA_DIR
from config.i18n import tr

log = logging.getLogger("deltam.sheets")

CACHE_FILE = DATA_DIR / "sheets_cache.json"
USER_AGENT = "DeltaM sheet sync"
# ช่องของ JobInfo ที่จับคู่กับคอลัมน์ใน Sheet ได้ (key -> ข้อความบนจอ)
FIELDS = {
    "job_no": "Job no.", "site": "Hospital / site", "province": "Province", "department": "Department",
    "pump_type": "Pump type", "brand": "Brand", "model": "Model", "serial_no": "Serial no.", "asset_id": "Asset ID",
    "accessory_brand": "IV set brand", "accessory": "IV set / syringe", "operator": "Operator",
    "contact": "Contact person", "contact_phone": "Contact phone", "notes": "Remark",
}
KEY_FIELDS = ("job_no", "serial_no", "asset_id")
# เดาการจับคู่จากหัวคอลัมน์ (ไทย/อังกฤษ) — ผู้ใช้แก้ได้ในหน้าตั้งค่า
GUESS = {
    "job_no": ("job no", "job", "เลขงาน", "เลขที่งาน", "index run", "run no"),
    "site": ("hospital", "site", "โรงพยาบาล", "สถานที่", "รพ"),
    "province": ("province", "จังหวัด"),
    "department": ("department", "dept", "หน่วยงาน", "แผนก", "ward"),
    "pump_type": ("type", "pump type", "ชนิด", "ประเภทเครื่อง"),
    "brand": ("brand", "ยี่ห้อ", "manufacturer"),
    "model": ("model", "รุ่น"),
    "serial_no": ("serial", "s/n", "sn", "serial no", "หมายเลขเครื่อง"),
    "asset_id": ("asset", "asset id", "ครุภัณฑ์", "เลขครุภัณฑ์"),
    "accessory_brand": ("iv set brand", "ยี่ห้อชุดสาย"),
    "accessory": ("iv set", "set iv", "ชุดสาย", "syringe"),
    "operator": ("operator", "engineer", "ผู้ทดสอบ", "ช่าง"),
    "contact": ("contact", "ผู้ติดต่อ"),
    "contact_phone": ("phone", "tel", "เบอร์", "โทร"),
    "notes": ("remark", "note", "notes", "หมายเหตุ"),
}

APPS_SCRIPT = r"""// DeltaM — Google Sheet connector (Apps Script Web App)
// 1) เปิด Google Sheet → ส่วนขยาย → Apps Script → วางโค้ดนี้ทั้งหมด → แก้ TOKEN เป็นรหัสลับของคุณ
// 2) ทำให้ใช้งานได้ → การทำให้ใช้งานได้รายการใหม่ → ประเภท "เว็บแอป" · เรียกใช้ในฐานะ "ฉัน" · ผู้มีสิทธิ์เข้าถึง "ทุกคน"
// 3) คัดลอกลิงก์เว็บแอป (ลงท้าย /exec) ไปใส่ใน DeltaM → ตั้งค่า → Google Sheet พร้อม TOKEN เดียวกัน
const TOKEN = 'change-me';

function doGet(e) { return handle_(e.parameter || {}); }
function doPost(e) { return handle_(JSON.parse((e.postData && e.postData.contents) || '{}')); }

function handle_(p) {
  if (TOKEN && p.token !== TOKEN) return out_({ok: false, error: 'bad token'});
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = p.sheet ? ss.getSheetByName(p.sheet) : ss.getSheets()[0];
  if (!sh) return out_({ok: false, error: 'sheet not found'});
  var data = sh.getDataRange().getDisplayValues();
  var headers = data.length ? data[0] : [];
  if (!p.action || p.action === 'read') {
    return out_({ok: true, sheet: sh.getName(), headers: headers, rows: data.slice(1)});
  }
  if (p.action === 'update') {
    var lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      var values = p.values || {};
      Object.keys(values).forEach(function (name) {          // คอลัมน์ใหม่ = เพิ่มหัวคอลัมน์ท้ายตาราง
        if (headers.indexOf(name) < 0) { headers.push(name); sh.getRange(1, headers.length).setValue(name); }
      });
      var keyCol = headers.indexOf(p.key_column);
      if (keyCol < 0) return out_({ok: false, error: 'key column not found'});
      var row = -1, key = String(p.key).trim().toLowerCase();
      for (var i = 1; i < data.length; i++) {
        if (String(data[i][keyCol]).trim().toLowerCase() === key) { row = i + 1; break; }
      }
      if (row < 0) {
        if (!p.append) return out_({ok: false, error: 'row not found'});
        row = sh.getLastRow() + 1;
        sh.getRange(row, keyCol + 1).setValue(p.key);
      }
      Object.keys(values).forEach(function (name) {
        sh.getRange(row, headers.indexOf(name) + 1).setValue(values[name]);
      });
      return out_({ok: true, row: row});
    } finally {
      lock.releaseLock();
    }
  }
  return out_({ok: false, error: 'unknown action'});
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
"""


@dataclass
class SheetSource:
    """1 ลิงก์ (ตรงกับ config.settings.SheetSource — เก็บใน settings.sheets.sources เป็น dict)"""
    id: str = ""
    name: str = ""
    kind: str = "csv"
    url: str = ""
    sheet: str = ""
    token: str = ""
    key_column: str = ""
    columns: dict = field(default_factory=dict)     # หัวคอลัมน์ -> ช่องของ DeltaM
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "SheetSource":
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        source = cls(**known)
        source.columns = dict(source.columns or {})
        if not source.id:
            source.id = datetime.now().strftime("s%Y%m%d%H%M%S%f")
        return source

    def label(self) -> str:
        return self.name or self.url[:48]

    def header_for(self, field_name: str) -> str | None:
        return next((h for h, f in self.columns.items() if f == field_name), None)

    @property
    def writable(self) -> bool:
        return self.kind == "script"

    def key_header(self) -> str | None:
        """คอลัมน์ที่ใช้หาแถวตอนแก้ข้อมูล: ที่ตั้งไว้ > คอลัมน์ที่จับคู่กับเลขงาน > S/N > ครุภัณฑ์"""
        if self.key_column:
            return self.key_column
        for name in KEY_FIELDS:
            header = self.header_for(name)
            if header:
                return header
        return None


def _norm(value) -> str:
    return " ".join(str(value or "").split()).lower()


def guess_columns(headers: list[str]) -> dict:
    """เดาการจับคู่หัวคอลัมน์ -> ช่องของ DeltaM (ตรงตัวก่อน แล้วค่อยคำที่มีอยู่ในหัวคอลัมน์)"""
    out: dict[str, str] = {}
    used: set[str] = set()
    for exact in (True, False):
        for header in headers:
            if header in out:
                continue
            h = _norm(header)
            for name, words in GUESS.items():
                if name in used:
                    continue
                if (exact and h in words) or (not exact and any(w in h for w in words if len(w) > 2)):
                    out[header] = name
                    used.add(name)
                    break
    return out


def csv_url(url: str) -> str:
    """ลิงก์ Google Sheet ทั่วไป -> ลิงก์ดาวน์โหลด CSV (ลิงก์ที่เป็น CSV อยู่แล้วคงเดิม)"""
    url = url.strip()
    if "output=csv" in url or "format=csv" in url or "/pub?" in url:
        return url
    match = re.search(r"docs\.google\.com/spreadsheets/d/([\w-]+)", url)
    if not match:
        return url
    gid = re.search(r"[#&?]gid=(\d+)", url)
    return f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=csv" + \
        (f"&gid={gid.group(1)}" if gid else "")


def _open(request, timeout: float) -> bytes:
    with urllib.request.urlopen(request, timeout=timeout) as response:      # noqa: S310 — ลิงก์ที่ผู้ใช้ตั้งเอง
        return response.read()


def fetch(source: SheetSource, timeout: float = 15.0, opener=_open) -> tuple[list[str], list[dict]]:
    """อ่านทั้งตาราง -> (หัวคอลัมน์, แถว [{หัวคอลัมน์: ค่า}]) — โยน IOError พร้อมเหตุผลถ้าไม่ได้"""
    if not source.url.strip():
        raise IOError(tr("No link"))
    try:
        if source.kind == "script":
            query = urllib.parse.urlencode({"action": "read", "sheet": source.sheet, "token": source.token})
            url = source.url + ("&" if "?" in source.url else "?") + query
            body = json.loads(opener(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout)
                              .decode("utf-8"))
            if not body.get("ok"):
                raise IOError(str(body.get("error") or "error"))
            headers = [str(h) for h in body.get("headers") or []]
            rows = [dict(zip(headers, [str(v) for v in row])) for row in body.get("rows") or []]
        else:
            raw = opener(urllib.request.Request(csv_url(source.url), headers={"User-Agent": USER_AGENT}), timeout)
            text = raw.decode("utf-8-sig", errors="replace")
            if text.lstrip().startswith("<"):
                raise IOError(tr("The link returned a web page, not CSV — share the sheet as "
                                 "'Anyone with the link' or publish it as CSV"))
            reader = csv.reader(io.StringIO(text))
            table = list(reader)
            headers = [h.strip() for h in (table[0] if table else [])]
            rows = [dict(zip(headers, row)) for row in table[1:]]
    except IOError:
        raise
    except Exception as exc:        # URLError / timeout / JSON เสีย
        raise IOError(str(getattr(exc, "reason", exc))) from exc
    rows = [row for row in rows if any(str(v).strip() for v in row.values())]
    return headers, rows


def write_row(source: SheetSource, key: str, values: dict, append: bool = False, timeout: float = 15.0,
              opener=_open) -> int:
    """แก้ค่าในแถวที่คอลัมน์กุญแจ = key (คอลัมน์ใหม่เพิ่มให้) · append = ไม่เจอแถวแล้วเพิ่มแถวใหม่ — คืนเลขแถว"""
    if not source.writable:
        raise IOError(tr("This link is read-only — use an Apps Script link to edit the sheet"))
    key_column = source.key_header()
    if not key_column:
        raise IOError(tr("Choose the key column (for example Job no.) for this sheet first"))
    payload = json.dumps({"action": "update", "sheet": source.sheet, "token": source.token, "key_column": key_column,
                          "key": key, "values": {str(k): str(v) for k, v in values.items()}, "append": append},
                         ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(source.url, data=payload, method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
    try:
        body = json.loads(opener(request, timeout).decode("utf-8"))
    except Exception as exc:
        raise IOError(str(getattr(exc, "reason", exc))) from exc
    if not body.get("ok"):
        raise IOError(str(body.get("error") or "error"))
    return int(body.get("row") or 0)


# ---------------------------------------------------------------- สำเนาข้อมูลที่ดึงมา + ค้นหา
class SheetStore:
    def __init__(self, path: Path = CACHE_FILE):
        self.path = path
        self._lock = threading.Lock()
        self._data: dict[str, dict] = {}
        self._sources: list[SheetSource] = []
        self._index: dict[tuple[str, str], list[tuple[str, dict]]] = {}
        self._load()

    def _load(self) -> None:
        try:
            self._data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {}
        except (OSError, ValueError):
            self._data = {}

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            log.warning("sheet cache not saved: %s", exc)

    def configure(self, sources: list[dict]) -> None:
        with self._lock:
            self._sources = [SheetSource.from_dict(s) for s in sources if isinstance(s, dict)]
            self._rebuild()

    @property
    def sources(self) -> list[SheetSource]:
        return list(self._sources)

    def source(self, source_id: str) -> SheetSource | None:
        return next((s for s in self._sources if s.id == source_id), None)

    def state(self, source_id: str) -> dict:
        return dict(self._data.get(source_id) or {})

    def put(self, source: SheetSource, headers: list[str], rows: list[dict], status: str = "ok") -> None:
        with self._lock:
            self._data[source.id] = {"headers": headers, "rows": rows, "status": status, "rows_count": len(rows),
                                     "synced_at": datetime.now().isoformat(timespec="seconds")}
            self._save()
            self._rebuild()

    def put_error(self, source: SheetSource, error: str) -> None:
        with self._lock:
            entry = self._data.setdefault(source.id, {})
            entry["status"] = error
            entry["failed_at"] = datetime.now().isoformat(timespec="seconds")
            self._save()

    def _rebuild(self) -> None:
        index: dict[tuple[str, str], list[tuple[str, dict]]] = {}
        for source in self._sources:
            if not source.enabled:
                continue
            for row in (self._data.get(source.id) or {}).get("rows") or []:
                for header, name in source.columns.items():
                    if name in KEY_FIELDS and _norm(row.get(header)):
                        index.setdefault((name, _norm(row.get(header))), []).append((source.id, row))
        self._index = index

    def has_rows(self) -> bool:
        return bool(self._index)

    def rows_for(self, job: dict) -> list[tuple[str, dict]]:
        """แถวของงาน/เครื่องนี้จากทุกแหล่ง -> [(ชื่อแหล่ง, แถว)] (จับคู่ด้วยเลขงาน > S/N > ครุภัณฑ์ — ไม่ซ้ำแถว)"""
        out, seen = [], set()
        for name in KEY_FIELDS:
            value = _norm(job.get(name))
            if not value:
                continue
            for source_id, row in self._index.get((name, value), []):
                if id(row) in seen:
                    continue
                seen.add(id(row))
                source = self.source(source_id)
                out.append((source.label() if source else source_id, row))
        return out

    def lookup(self, field_name: str, value: str) -> dict | None:
        """ฟอร์มงานใหม่: ค่าที่พิมพ์ในช่องระบุงาน (เลขงาน/S/N/ครุภัณฑ์) -> ค่าช่องอื่นของ DeltaM จากแถวแรกที่ตรง"""
        if field_name not in KEY_FIELDS or not _norm(value):
            return None
        for source_id, row in self._index.get((field_name, _norm(value)), []):
            source = self.source(source_id)
            if source is None:
                continue
            values = {name: str(row.get(header) or "").strip() for header, name in source.columns.items()
                      if name in FIELDS and str(row.get(header) or "").strip()}
            if values:
                values["_source"] = source.label()
                return values
        return None

    def update_cached(self, source: SheetSource, key_header: str, key: str, values: dict) -> None:
        """หลังเขียนกลับสำเร็จ: แก้สำเนาในเครื่องให้ตรงทันที (ไม่ต้องรอดึงใหม่)"""
        with self._lock:
            entry = self._data.setdefault(source.id, {"headers": [], "rows": []})
            headers = entry.setdefault("headers", [])
            for name in values:
                if name not in headers:
                    headers.append(name)
            rows = entry.setdefault("rows", [])
            row = next((r for r in rows if _norm(r.get(key_header)) == _norm(key)), None)
            if row is None:
                row = {key_header: key}
                rows.append(row)
            row.update({k: str(v) for k, v in values.items()})
            self._save()
            self._rebuild()


_store: SheetStore | None = None


def store() -> SheetStore:
    """สำเนาข้อมูล Sheet ทั้งโปรแกรม (สร้างครั้งแรกที่เรียก — ตั้งแหล่งด้วย configure จาก settings)"""
    global _store
    if _store is None:
        _store = SheetStore()
        try:
            from config.settings import AppSettings
            _store.configure(AppSettings.load().sheets.sources)
        except Exception:
            pass
    return _store


def set_store(value: SheetStore | None) -> None:
    """เทสต์: ใช้สำเนาชั่วคราว (ไม่แตะ data/sheets_cache.json จริง)"""
    global _store
    _store = value


def sync_all(settings, opener=_open) -> list[tuple[str, str]]:
    """ดึงทุกแหล่งที่เปิดอยู่ -> [(ชื่อแหล่ง, สถานะ)] (เรียกใน thread แยก)"""
    s = store()
    s.configure(settings.sheets.sources)
    results = []
    for source in s.sources:
        if not source.enabled or not source.url.strip():
            continue
        try:
            headers, rows = fetch(source, settings.sheets.timeout_s, opener)
            if not source.columns:
                source.columns = guess_columns(headers)
            s.put(source, headers, rows)
            results.append((source.label(), tr("{n} rows", n=len(rows))))
            log.info(tr("Google Sheet '{name}': {n} rows", name=source.label(), n=len(rows)))
        except IOError as exc:
            s.put_error(source, str(exc))
            results.append((source.label(), str(exc)))
            log.warning(tr("Google Sheet '{name}' could not be read: {error}", name=source.label(), error=exc))
    return results


def sync_in_background(settings, done=None) -> threading.Thread:
    """ดึงตอนเปิดโปรแกรม/กดปุ่ม โดยไม่ค้างหน้าจอ (ไม่มีเน็ต = เขียน log แล้วจบ)"""
    def run():
        results = sync_all(settings)
        if done is not None:
            done(results)
    thread = threading.Thread(target=run, name="sheet-sync", daemon=True)
    thread.start()
    return thread


def source_dicts(sources: list[SheetSource]) -> list[dict]:
    return [asdict(s) for s in sources]
