"""ระบบสองภาษาแบบเบา: ในโค้ดเขียนข้อความภาษาอังกฤษผ่าน tr("...")
ถ้าเลือกภาษาไทย จะแปลจากตารางใน config/lang_th.py (ไม่มีคำแปล = แสดงอังกฤษ)

เพิ่มภาษาใหม่: สร้าง config/lang_xx.py ที่มี dict ชื่อ TRANSLATIONS แล้วเพิ่มใน LANGUAGES
"""
from __future__ import annotations

import importlib

LANGUAGES = {"th": "ไทย", "en": "English"}

_table: dict[str, str] = {}
_language = "en"
_missing: set[str] = set()


def set_language(language: str) -> None:
    global _table, _language
    _language = language if language in LANGUAGES else "en"
    _table = {}
    if _language != "en":
        _table = importlib.import_module(f"config.lang_{_language}").TRANSLATIONS


def language() -> str:
    return _language


def tr(text: str, **values) -> str:
    """แปลข้อความ แล้วแทนค่า {ชื่อ} ด้วย values (ถ้ามี)"""
    translated = _table.get(text)
    if translated is None:
        if _table and text:
            _missing.add(text)
        translated = text
    return translated.format(**values) if values else translated


def missing() -> set[str]:
    """ข้อความที่ถูกเรียกใช้แต่ยังไม่มีคำแปลในภาษาปัจจุบัน"""
    return set(_missing)
