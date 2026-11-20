"""เติมข้อมูลงานให้ทันทีจากฐานข้อมูลที่สะสม (ผู้ใช้ 2026-11-20 — ไม่ต้องรอ Tab) — ไม่มี Qt

ความสัมพันธ์ที่จำ (ค่าล่าสุดชนะ — ตาราง autofill_memory, DB v9):
    site       โรงพยาบาล/สถานที่            -> จังหวัด          (เปลี่ยนจังหวัด = ถามก่อนจำทับ — wizard)
    model      รุ่นเครื่อง                    -> ยี่ห้อ + ชนิดเครื่อง (รุ่นเฉพาะเจาะจงกว่ายี่ห้อ)
    accessory  ชนิด + รุ่นชุดสาย/syringe     -> ยี่ห้อชุดสาย
    device     S/N หรือ รหัสครุภัณฑ์           -> ข้อมูลตัวเครื่องทั้งหมด (โรงพยาบาล จังหวัด หน่วยงาน รุ่น ยี่ห้อ ชนิด ชุดสาย)
    โรงพยาบาล + รุ่นเครื่อง -> ชุดสาย ใช้ตาราง site_accessory_standards เดิม (เปลี่ยน = popup ชั่วคราว/ถาวร เดิม)
ไม่มีในตาราง -> ดูจากประวัติผลที่เก็บแล้ว (JobSuggester) — ข้อมูลเก่าเติมได้ทันทีโดยไม่ต้องย้าย
จำตอนกด "สร้างการทดสอบ" (ขั้นสุดท้ายของ wizard) — งานที่ยกเลิกกลางทางไม่ถูกจำ
ค่าที่จำต้องตรงทั้งคำ (ไม่สนตัวพิมพ์/ช่องว่างซ้ำ) จึงเติม — พิมพ์ยังไม่ครบไม่เติม
"""
from __future__ import annotations

DEVICE_FIELDS = ("site", "province", "department", "model", "brand", "pump_type", "accessory", "accessory_brand")
EMPTY = ("", "-", "–", "—", "--")


def norm(value) -> str:
    return " ".join(str(value or "").lower().split())


def has(value) -> bool:
    """มีข้อมูลจริง ("-" = ไม่มี)"""
    return str(value or "").strip() not in EMPTY


class Autofill:
    def __init__(self, repository, suggester):
        self._repo = repository
        self._history = suggester

    def _memory(self, kind: str, key: str) -> dict:
        try:
            return self._repo.memory(kind, key) or {}
        except Exception:                   # ฐานข้อมูลรุ่นเก่า/ทดสอบที่ไม่มีตาราง
            return {}

    # ------------------------------------------------------------ อ่าน
    def province(self, site: str) -> str:
        found = self._memory("site", norm(site)).get("province", "")
        return found if has(found) else self._history.latest("province", site=site)

    def model_info(self, model: str) -> dict:
        """{"brand", "pump_type"} ของรุ่น (ไม่พบ = ค่าว่าง)"""
        found = self._memory("model", norm(model))
        if has(found.get("brand")) or found.get("pump_type"):
            return {"brand": found.get("brand", ""), "pump_type": found.get("pump_type", "")}
        return self._history.infer_device(model) if norm(model) else {"brand": "", "pump_type": ""}

    def accessory_brand(self, accessory: str, pump_type: str) -> str:
        found = self._memory("accessory", f"{pump_type}|{norm(accessory)}").get("accessory_brand", "")
        return found if has(found) else (self._history.infer_accessory_brand(accessory) if norm(accessory) else "")

    def site_accessory(self, site: str, brand: str, model: str, pump_type: str) -> dict | None:
        """ชุดสายมาตรฐานของ โรงพยาบาล + รุ่นเครื่อง {iv_set, iv_set_brand} (ตารางเดิม)"""
        try:
            return self._repo.site_standard(site, brand, model, pump_type)
        except Exception:
            return None

    def device(self, serial_no: str = "", asset_id: str = "") -> dict:
        """ข้อมูลตัวเครื่องจาก S/N (ก่อน) หรือรหัสครุภัณฑ์ — {} = ไม่รู้จัก"""
        for kind, value in (("sn", serial_no), ("asset", asset_id)):
            found = self._memory("device", f"{kind}:{norm(value)}") if norm(value) else {}
            if found:
                return {k: found.get(k, "") for k in DEVICE_FIELDS}
        for kind, value in (("serial_no", serial_no), ("asset_id", asset_id)):
            if norm(value):
                found = self._history.known_device(**{kind: value})
                if found:
                    return {k: str(found.get(k) or "") for k in DEVICE_FIELDS}
        return {}

    # ------------------------------------------------------------ จำ
    def remember(self, job: dict, province_update: bool = True) -> None:
        """จำข้อมูลของงานที่สร้างการทดสอบแล้ว · province_update = False -> ไม่ทับจังหวัดเดิมของโรงพยาบาล (ใช้เฉพาะงานนี้)"""
        get = lambda name: str(job.get(name) or "").strip()        # noqa: E731
        site, province = get("site"), get("province")
        if has(site) and has(province) and (province_update or not self._memory("site", norm(site))):
            self._repo.remember("site", norm(site), {"site": site, "province": province})
        model, brand, pump = get("model"), get("brand"), get("pump_type")
        if has(model) and (has(brand) or pump):
            self._repo.remember("model", norm(model), {"model": model, "brand": brand if has(brand) else "", "pump_type": pump})
        accessory, accessory_brand = get("accessory"), get("accessory_brand")
        if has(accessory) and has(accessory_brand):
            self._repo.remember("accessory", f"{pump}|{norm(accessory)}",
                                {"accessory": accessory, "accessory_brand": accessory_brand})
        data = {k: get(k) if has(get(k)) else "" for k in DEVICE_FIELDS}
        if not province_update:                 # จังหวัดของงานนี้ใช้ชั่วคราว -> เครื่องจำจังหวัดเดิมของโรงพยาบาล
            data["province"] = self._memory("site", norm(site)).get("province", data["province"])
        for kind, value in (("sn", get("serial_no")), ("asset", get("asset_id"))):
            if has(value) and has(model):
                self._repo.remember("device", f"{kind}:{norm(value)}", data)
