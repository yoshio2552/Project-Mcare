"""ตัวอ่านบรรทัดข้อมูลของตราชั่ง

รูปแบบ A&D มาตรฐาน (ตระกูล GF/GX):   "ST,+00012.345  g"
    2 ตัวแรก = สถานะ   ST นิ่ง · US ไม่นิ่ง · OL เกินพิกัด · QT/WT โหมดอื่น
    ตามด้วยเครื่องหมาย ตัวเลข และหน่วย
ถ้าบรรทัดไม่ตรงรูปแบบนี้ จะลองอ่านแบบทั่วไป (ตัวเลขตัวแรกของบรรทัด) แทน

หมายเหตุ: รูปแบบ A&D เขียนตามคู่มือทั่วไปของตระกูลนี้ ยังไม่ได้เทียบกับข้อมูลจริงจาก GF-300 ของผู้ใช้
เพิ่มรูปแบบของตราชั่งยี่ห้ออื่น: เขียนฟังก์ชัน parse_xxx(line) -> Reading | None แล้วเรียกใน parse_line
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_UNIT_TO_GRAM = {"": 1.0, "g": 1.0, "mg": 0.001, "kg": 1000.0}
_AND = re.compile(r"^\s*(ST|US|OL|QT|WT)\s*,\s*([+-]?\s*\d*\.?\d+)\s*([A-Za-z%]*)")
_NUMBER = re.compile(r"[-+]?\s*\d*\.\d+|[-+]?\s*\d+")


@dataclass(frozen=True, slots=True)
class Reading:
    weight: float                   # กรัม
    stable: bool | None = None      # None = ตราชั่งไม่ได้บอก


def parse_and(line: str) -> Reading | None:
    match = _AND.match(line)
    if not match:
        return None
    header, number, unit = match.group(1), match.group(2).replace(" ", ""), match.group(3).lower()
    if header == "OL" or unit not in _UNIT_TO_GRAM:
        return None                 # เกินพิกัด หรือหน่วยที่ไม่ใช่น้ำหนัก (เช่น นับชิ้น)
    return Reading(float(number) * _UNIT_TO_GRAM[unit], stable=header == "ST" if header in ("ST", "US") else None)


def parse_generic(line: str) -> Reading | None:
    match = _NUMBER.search(line)
    return Reading(float(match.group().replace(" ", ""))) if match else None


def parse_line(line: str) -> Reading | None:
    """อ่าน 1 บรรทัด คืน None ถ้าใช้ไม่ได้"""
    line = line.strip()
    if not line:
        return None
    if _AND.match(line):            # เป็นรูปแบบ A&D แน่ๆ: เชื่อผลของมัน (รวมกรณีเกินพิกัด = ใช้ไม่ได้)
        return parse_and(line)
    return parse_generic(line)
