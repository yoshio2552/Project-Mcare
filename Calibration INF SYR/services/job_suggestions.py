"""คำแนะนำสำหรับช่องกรอกข้อมูลงาน (smart autofill) — เรียนรู้จากงานที่เคยบันทึก ไม่มี Qt

หลักการ: ไม่กรอกให้เอง — แค่ "เสนอ" (หน้าจอแสดงเป็นตัวอักษรจาง/รายการ) ผู้ใช้กด Tab หรือ Enter จึงรับ
คำแนะนำดูบริบทจากช่องอื่นที่กรอกแล้ว:
    ยี่ห้อ        ที่เคยใช้กับชนิดเครื่องนี้ (infusion / syringe) ก่อน
    รุ่น          ของยี่ห้อนั้น + ชนิดนั้น
    ชุดสาย       ที่เคยใช้กับยี่ห้อ + รุ่น + ชนิดนั้น
    S/N, รหัส     ของรุ่นนั้น — ถ้า S/N หรือรหัสครุภัณฑ์ตรงกับเครื่องที่เคยทดสอบ ช่องอื่นของตัวเครื่องจะเสนอค่าของเครื่องนั้น
    ผู้ทดสอบ, ตราชั่ง, หน่วยงาน    ใช้บ่อย/ล่าสุดก่อน
    อุณหภูมิ ความชื้น ความดัน      เฉพาะค่าที่บันทึก "วันนี้" (สภาพอากาศเมื่อวานใช้ไม่ได้)
    หมายเหตุ, เลขงาน   ไม่แนะนำ (เลขงานไม่ซ้ำกัน — ผู้ใช้ 2026-11-13: ยังไม่ต้องเสนอเลข)
ลำดับ: พิมพ์ขึ้นต้นตรงกันก่อน แล้วจึงมีคำนั้นอยู่ข้างใน · ใช้บ่อยก่อน · ล่าสุดก่อนเมื่อเท่ากัน

เติมจากรุ่น (ชื่อรุ่นไม่ซ้ำข้ามยี่ห้อ/ชนิด): infer_device("TE-112") -> ยี่ห้อ + ชนิดเครื่องที่รุ่นนี้เคยบันทึก
และ infer_accessory_brand(รุ่นชุดสาย) -> ยี่ห้อของชุดสายนั้น — หน้าจอแสดงเป็นตัวจาง รอ Tab/Enter
"""
from __future__ import annotations

from datetime import date

DEVICE_FIELDS = ("brand", "model", "accessory", "accessory_brand", "serial_no", "asset_id", "department",
                 "site", "province")
SAME_DAY_FIELDS = ("temperature_c", "humidity_pct", "air_temp_c", "pressure_hpa")
NO_SUGGESTIONS = ("notes", "job_no")
MAX_ITEMS = 8


def _n(value) -> str:
    return " ".join(str(value or "").lower().split())


def _text(value) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value).strip()


class JobSuggester:
    def __init__(self, history: list[dict], today: str | None = None):
        """history = JobInfo (dict) ของงานที่เคยบันทึก ใหม่สุดก่อน แต่ละรายการมี started_at"""
        self._history = history
        self._today = today or date.today().isoformat()

    # --------------------------------------------------------------- ภายใน
    def _known_device(self, job: dict) -> dict | None:
        """เครื่องที่ S/N หรือรหัสครุภัณฑ์ตรงกับที่กรอก (ตัวล่าสุด)"""
        for key in ("serial_no", "asset_id"):
            value = _n(job.get(key))
            if value:
                match = next((h for h in self._history if _n(h.get(key)) == value), None)
                if match is not None:
                    return match
        return None

    def _pool(self, field: str, job: dict) -> list[dict]:
        """รายการประวัติที่เกี่ยวกับบริบทตอนนี้ (กว้างขึ้นทีละขั้นถ้าไม่พบ)"""
        wanted = {key: _n(job.get(key)) for key in ("pump_type", "brand", "model", "site", "accessory")}

        def where(*keys):
            return [h for h in self._history if all(not wanted[k] or _n(h.get(k)) == wanted[k] for k in keys)]

        if field == "brand":
            return where("pump_type") or self._history
        if field == "model":
            return where("pump_type", "brand") or where("brand") or where("pump_type")
        if field == "accessory":
            # โรงพยาบาลนี้ + เครื่องรุ่นนี้ก่อน แล้วจึงกว้างขึ้น
            return (where("site", "pump_type", "brand", "model") if wanted["site"] else []) \
                or where("pump_type", "brand", "model") or where("pump_type")
        if field == "accessory_brand":
            return where("accessory") or where("pump_type")
        if field == "province":
            return (where("site") if wanted["site"] else []) or self._history
        if field in ("serial_no", "asset_id"):
            return where("brand", "model") if (wanted["brand"] or wanted["model"]) else self._history
        if field in SAME_DAY_FIELDS:
            return [h for h in self._history if str(h.get("started_at", ""))[:10] == self._today]
        return self._history

    # --------------------------------------------------------------- เติมจากรุ่น
    def _most_common(self, items: list[dict], field: str) -> str:
        counts: dict[str, int] = {}
        first: dict[str, int] = {}
        canonical: dict[str, str] = {}
        for index, item in enumerate(items):
            value = _text(item.get(field))
            if not value:
                continue
            key = _n(value)
            counts[key] = counts.get(key, 0) + 1
            first.setdefault(key, index)
            canonical.setdefault(key, value)
        if not counts:
            return ""
        return canonical[min(counts, key=lambda k: (-counts[k], first[k]))]

    def infer_device(self, model: str) -> dict:
        """รุ่นนี้เคยบันทึกเป็นยี่ห้อ/ชนิดอะไร -> {"brand": ..., "pump_type": ...} (ไม่พบ = ค่าว่าง)"""
        key = _n(model)
        items = [h for h in self._history if key and _n(h.get("model")) == key]
        return {"brand": self._most_common(items, "brand"), "pump_type": self._most_common(items, "pump_type")}

    def infer_accessory_brand(self, accessory: str) -> str:
        """ยี่ห้อที่ชุดสาย/syringe รุ่นนี้เคยบันทึก"""
        key = _n(accessory)
        return self._most_common([h for h in self._history if key and _n(h.get("accessory")) == key], "accessory_brand")

    # --------------------------------------------------------------- ใช้งาน
    def suggest(self, field: str, job: dict, typed: str = "") -> list[str]:
        """คำแนะนำของช่อง field เรียงดีที่สุดก่อน (ไม่รวมค่าที่ตรงกับที่พิมพ์อยู่แล้ว)"""
        if field in NO_SUGGESTIONS:
            return []
        typed_n = _n(typed)
        ranked: list[str] = []
        device = self._known_device(job) if field in DEVICE_FIELDS else None
        if device is not None and _text(device.get(field)):
            ranked.append(_text(device.get(field)))         # เครื่องเดิม: ค่าของเครื่องนั้นมาก่อนเสมอ

        counts: dict[str, int] = {}
        first: dict[str, int] = {}
        canonical: dict[str, str] = {}
        for index, item in enumerate(self._pool(field, job)):
            value = _text(item.get(field))
            if not value:
                continue
            key = _n(value)
            counts[key] = counts.get(key, 0) + 1
            first.setdefault(key, index)
            canonical.setdefault(key, value)                 # การสะกดล่าสุด
        if field in SAME_DAY_FIELDS:                        # สภาพแวดล้อม: ค่าล่าสุดของวันนี้เท่านั้น
            order = sorted(counts, key=lambda k: first[k])[:1]
        else:
            order = sorted(counts, key=lambda k: (-counts[k], first[k]))
        ranked += [canonical[k] for k in order]

        unique, seen = [], set()
        for value in ranked:
            key = _n(value)
            if key in seen or key == typed_n:
                continue
            seen.add(key)
            unique.append(value)
        if typed_n:
            prefix = [v for v in unique if _n(v).startswith(typed_n)]
            inside = [v for v in unique if typed_n in _n(v) and v not in prefix]
            unique = prefix + inside
        return unique[:MAX_ITEMS]
