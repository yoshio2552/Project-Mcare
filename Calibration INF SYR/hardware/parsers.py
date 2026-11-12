"""ตัวอ่านบรรทัดข้อมูลของตราชั่ง

รูปแบบ A&D (ตระกูล GF/GX):   "ST,+0144.804  g" + CR LF
    2 ตัวแรก = สถานะ   ST นิ่ง · US ไม่นิ่ง · OL เกินพิกัด · QT/WT โหมดอื่น
    ตามด้วย "," เครื่องหมาย ตัวเลข ช่องว่าง และหน่วย

ข้อมูลจริงจาก GF-300 ของผู้ใช้ (2026-11-12, poll "Q", 2400 7E1): "ST,+0144.804  g" + CR LF (17 ไบต์)
    ตัวเลข 4 หลักหน้าจุด ละเอียด 1 mg · พบทั้ง ST และ US
    ยังไม่เคยเห็นบรรทัด OL / ค่าติดลบ / หน่วยอื่น / โหมด stream

บทเรียนจากข้อมูลจริง: ถ้ารอคำตอบไม่นานพอ จะได้ "ท่อน" ของบรรทัด เช่น "US,+01" หรือ "2.637  g"
ตัวอ่านแบบหลวม (เดาตัวเลขตัวแรก) จะรับท่อนเหล่านี้เป็นน้ำหนักผิดๆ (1.0 g, 2.637 g)
จึงแยกรูปแบบให้เลือก (SerialSettings.line_format) และค่าเริ่มต้นคือ "and" ที่รับเฉพาะบรรทัดครบรูปแบบ
(การตรวจว่าบรรทัดจบด้วย CR LF ครบ ทำในตัวอ่านพอร์ต hardware/serial_balance.read_line)

เพิ่มรูปแบบของตราชั่งยี่ห้ออื่น: เขียนฟังก์ชัน parse_xxx(line) -> Reading | None
แล้วลงทะเบียนใน LINE_FORMATS (จะขึ้นเป็นตัวเลือกในหน้าตั้งค่าเอง)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

_UNIT_TO_GRAM = {"g": 1.0, "mg": 0.001, "kg": 1000.0}
_AND_HEADER = re.compile(r"^\s*(ST|US|OL|QT|WT)\s*,")
# รูปแบบเต็ม: สถานะ , เครื่องหมาย ตัวเลข(มีจุดทศนิยม) ช่องว่าง หน่วย — ต้องครบทุกส่วน ไม่มีอะไรเกิน
_AND_STRICT = re.compile(r"^(ST|US|OL|QT|WT),([+-])\s*(\d+\.\d+)\s+([A-Za-z%]+)$")
_NUMBER = re.compile(r"[-+]?\s*\d*\.\d+|[-+]?\s*\d+")


@dataclass(frozen=True, slots=True)
class Reading:
    weight: float                   # กรัม
    stable: bool | None = None      # None = ตราชั่งไม่ได้บอก


def parse_and(line: str) -> Reading | None:
    """A&D แบบเข้มงวด: รับเฉพาะบรรทัดครบรูปแบบ (ท่อนที่ขาดหัว/ขาดหาง/ไม่มีหน่วย = None)"""
    match = _AND_STRICT.match(line.strip())
    if not match:
        return None
    header, sign, number, unit = match.groups()
    unit = unit.lower()
    if header == "OL" or unit not in _UNIT_TO_GRAM:
        return None                 # เกินพิกัด หรือหน่วยที่ไม่ใช่น้ำหนัก (เช่น นับชิ้น)
    weight = float(number) * _UNIT_TO_GRAM[unit] * (-1.0 if sign == "-" else 1.0)
    return Reading(weight, stable=header == "ST" if header in ("ST", "US") else None)


def parse_generic(line: str) -> Reading | None:
    """แบบหลวม: ตัวเลขตัวแรกของบรรทัด (สำหรับตราชั่งที่ยังไม่มีตัวอ่านเฉพาะ — เสี่ยงรับท่อนบรรทัด)"""
    match = _NUMBER.search(line)
    return Reading(float(match.group().replace(" ", ""))) if match else None


def parse_line(line: str) -> Reading | None:
    """อัตโนมัติ: ถ้าหน้าตาเป็น A&D ใช้แบบเข้มงวด ไม่งั้นใช้แบบหลวม — คืน None ถ้าใช้ไม่ได้"""
    line = line.strip()
    if not line:
        return None
    if _AND_HEADER.match(line):     # เป็นรูปแบบ A&D แน่ๆ: เชื่อผลของมัน (รวมกรณีเกินพิกัด/ไม่ครบ = ใช้ไม่ได้)
        return parse_and(line)
    return parse_generic(line)


# key -> (ฟังก์ชัน, ข้อความบนจอ)
LINE_FORMATS: dict[str, tuple[Callable[[str], Reading | None], str]] = {
    "and": (parse_and, "A&D (strict, recommended)"),
    "auto": (parse_line, "Auto (A&D, otherwise first number)"),
    "generic": (parse_generic, "First number in the line"),
}
DEFAULT_FORMAT = "and"


def get_parser(name: str) -> Callable[[str], Reading | None]:
    return LINE_FORMATS.get(name, LINE_FORMATS[DEFAULT_FORMAT])[0]


def format_choices() -> list[tuple[str, str]]:
    return [(key, label) for key, (_, label) in LINE_FORMATS.items()]
