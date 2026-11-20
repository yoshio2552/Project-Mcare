"""ผู้ลงนามและช่องลายเซ็นของใบรายงาน (ไม่มี Qt) — ผู้ใช้ 2026-11-20

ผู้ลงนาม (Person): ชื่อไทย / อังกฤษ + ภาพลายเซ็น PNG พื้นใส (คัดลอกเข้า data/signatures/ ตอนเลือกไฟล์ในหน้าตั้งค่า)
ช่องลายเซ็น (SignSlot): บทบาท + ตำแหน่ง (ไทย/อังกฤษ) + ใครลงนาม — ตั้งแยกใบ Inspection (หน้า 1 ทั้งสองแบบ)
และใบรับรอง Calibration (หน้า 2)

ใครลงนาม (SignSlot.who):
    "operator"      ผู้ทดสอบของงาน — ใช้ภาพ/ชื่อของผู้ลงนามที่ชื่อตรงกับช่อง "ผู้ทดสอบ" (ไม่ตรง = ชื่อที่พิมพ์ ไม่มีภาพ)
    "person:<id>"   ผู้ลงนามคนนั้นเสมอ
    "blank"         เว้นว่าง เซ็นด้วยมือ

เก็บใน AppSettings.report เป็น list ของ dict (people, sign_inspection, sign_calibration) · ค่าเก่า (signers แบบบรรทัด
"ชื่อ | ตำแหน่ง | ไฟล์", reviewer, approver) ย้ายมาเป็นผู้ลงนามด้วย migrate() — ไม่ลบช่องเดิม
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, fields
from pathlib import Path

KINDS = ("inspection", "calibration")
SIGNATURE_FOLDER = "signatures"          # ใต้ data/ — ภาพลายเซ็นที่เลือกผ่านหน้าตั้งค่า


@dataclass
class Person:
    id: str = ""
    name_th: str = ""
    name_en: str = ""
    aliases: str = ""       # ชื่ออื่นที่พิมพ์ในช่องผู้ทดสอบ คั่นด้วย , (เช่น ชื่อเล่น/ชื่อสั้น)
    image: str = ""         # path ภาพลายเซ็น (สัมพัทธ์กับ data/ หรือเต็ม) — ว่าง = เซ็นด้วยมือ

    def name(self, lang: str) -> str:
        """ชื่อในเอกสารภาษานั้น — ไม่มีชื่อภาษานั้นใช้อีกภาษา"""
        first, second = (self.name_en, self.name_th) if lang == "en" else (self.name_th, self.name_en)
        return (first or second or "").strip()

    def label(self) -> str:
        """ชื่อสำหรับแสดงในโปรแกรม: ไทย · อังกฤษ"""
        return " · ".join(p for p in (self.name_th.strip(), self.name_en.strip()) if p) or "—"

    def names(self) -> set[str]:
        items = [self.name_th, self.name_en] + str(self.aliases or "").split(",")
        return {key for key in (_key(item) for item in items) if key}

    def matches(self, typed: str) -> bool:
        return bool(_key(typed)) and _key(typed) in self.names()


@dataclass
class SignSlot:
    role_th: str = ""
    role_en: str = ""
    pos_th: str = ""
    pos_en: str = ""
    who: str = "operator"
    show: bool = True

    def role(self, lang: str) -> str:
        return (self.role_en or self.role_th) if lang == "en" else (self.role_th or self.role_en)

    def position(self, lang: str) -> str:
        return (self.pos_en or self.pos_th) if lang == "en" else (self.pos_th or self.pos_en)


# ค่าเริ่มต้น (ผู้ใช้ 2026-11-20): ใบ Inspection = Inspected by · PM Engineer + Approved by · Engineering Manager
DEFAULT_SLOTS = {
    "inspection": [
        SignSlot("ผู้ตรวจสอบ", "Inspected by", "วิศวกรบำรุงรักษา", "PM Engineer", "operator"),
        SignSlot("ผู้อนุมัติ", "Approved by", "ผู้จัดการฝ่ายวิศวกรรม", "Engineering Manager", "blank"),
    ],
    "calibration": [
        SignSlot("ผู้สอบเทียบ", "Calibrated by", "วิศวกรบริการ", "Service Engineer", "operator"),
        SignSlot("ผู้ทวนสอบ", "Reviewed by", "หัวหน้าฝ่ายบริการ", "Service Supervisor", "blank"),
        SignSlot("ผู้อนุมัติ", "Approved by", "ผู้จัดการฝ่ายเทคนิค", "Technical Manager", "blank"),
    ],
}
MAX_SLOTS = {"inspection": 3, "calibration": 3}


def _key(text) -> str:
    return " ".join(str(text or "").split()).lower()


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def default_slots(kind: str) -> list[SignSlot]:
    return [SignSlot(**asdict(slot)) for slot in DEFAULT_SLOTS.get(kind, DEFAULT_SLOTS["inspection"])]


def _from_dict(cls, data: dict):
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in (data or {}).items() if k in names})


def people_from(raw) -> list[Person]:
    out = []
    for item in raw or []:
        if isinstance(item, dict):
            person = _from_dict(Person, item)
            if person.id:
                out.append(person)
    return out


def slots_from(raw, kind: str) -> list[SignSlot]:
    """ช่องลายเซ็นจากค่าตั้ง — ว่าง = ค่าเริ่มต้นของใบนั้น"""
    slots = [_from_dict(SignSlot, item) for item in (raw or []) if isinstance(item, dict)]
    return slots[:MAX_SLOTS.get(kind, 3)] or default_slots(kind)


def to_dicts(items) -> list[dict]:
    return [asdict(item) for item in items]


def find(people: list[Person], person_id: str) -> Person | None:
    return next((p for p in people if p.id == person_id), None)


def match(people: list[Person], typed: str) -> Person | None:
    """ผู้ลงนามที่ชื่อ (ไทย/อังกฤษ/ชื่ออื่น) ตรงกับที่พิมพ์ — ต้องตรงทั้งชื่อ (ไม่เดา กันลายเซ็นผิดคน)"""
    return next((p for p in people if p.matches(typed)), None)


def resolve(slot: SignSlot, people: list[Person], operator: str, lang: str) -> tuple[str, str]:
    """(ชื่อใต้ลายเซ็น, path ภาพ) ของช่องนี้ในงานนี้ — ("", "") = เว้นว่างให้เซ็นมือ"""
    if slot.who == "operator":
        person = match(people, operator)
        if person is not None:
            return person.name(lang) or str(operator or "").strip(), person.image
        return str(operator or "").strip(), ""
    if slot.who.startswith("person:"):
        person = find(people, slot.who.split(":", 1)[1])
        if person is not None:
            return person.name(lang), person.image
    return "", ""


def image_file(path: str, data_dir: Path | None = None) -> str:
    """path ภาพลายเซ็นที่เก็บในค่าตั้ง -> path เต็ม (สัมพัทธ์ = ใต้ data/)"""
    if not path:
        return ""
    file = Path(path)
    if file.is_absolute():
        return str(file)
    if data_dir is None:
        from config.constants import DATA_DIR
        data_dir = DATA_DIR
    return str(Path(data_dir) / file)


def _is_thai(text: str) -> bool:
    return any("฀" <= ch <= "๿" for ch in text)


def _person_for(people: list[Person], name: str, image: str = "") -> Person:
    """ผู้ลงนามที่ชื่อนี้ (มีอยู่แล้วใช้คนเดิม ไม่มีสร้างใหม่) — ใช้ตอนย้ายค่าเก่า"""
    found = match(people, name)
    if found is not None:
        if image and not found.image:
            found.image = image
        return found
    person = Person(id=new_id(), image=image)
    if _is_thai(name):
        person.name_th = name.strip()
    else:
        person.name_en = name.strip()
    people.append(person)
    return person


def migrate(report) -> bool:
    """ย้ายค่าเก่าของ AppSettings.report มาเป็นผู้ลงนาม + ช่องลายเซ็น (แก้ในตัว object · ทำซ้ำได้ไม่เปลี่ยนอะไร)
    คืน True ถ้ามีการเปลี่ยน — ไม่ลบช่องเก่า (signers, reviewer, approver) ไม่บันทึกไฟล์เอง"""
    changed = False
    people = people_from(getattr(report, "people", []))
    if not getattr(report, "people_migrated", False):
        for line in getattr(report, "signers", None) or []:
            parts = [p.strip() for p in str(line).split("|")]
            if parts and parts[0]:
                _person_for(people, parts[0], parts[2] if len(parts) > 2 else "")
        report.people_migrated = True
        changed = True
    reviewer, approver = str(getattr(report, "reviewer", "") or "").strip(), str(getattr(report, "approver", "") or "").strip()
    if not getattr(report, "sign_calibration", None):
        slots = default_slots("calibration")
        if reviewer:
            slots[1].who = "person:" + _person_for(people, reviewer).id
        if approver:
            slots[2].who = "person:" + _person_for(people, approver).id
        report.sign_calibration = to_dicts(slots)
        changed = True
    if not getattr(report, "sign_inspection", None):
        slots = default_slots("inspection")
        if approver:
            slots[1].who = "person:" + _person_for(people, approver).id
        report.sign_inspection = to_dicts(slots)
        changed = True
    if changed:
        report.people = to_dicts(people)
    return changed
