"""รายการตรวจของใบรายงาน (แบบ Main Fable-1) แยก Infusion / Syringe — ข้อมูลล้วน ไม่มี Qt

ผลรายข้อเก็บเป็น dict  "กลุ่ม.รหัส" -> "pass" | "fail" | "na"  ("" / ไม่มี key = ยังไม่ได้ตรวจ ช่องว่างทั้ง 3 ช่อง)
อยู่ใน JobInfo.checks (กรอกใน wizard ขั้น 2) และแก้ภายหลังได้ในข้อมูลใบรายงาน (ตาราง job_reports)
รายละเอียดสั้นท้ายชื่อ (เช่น แบตเตอรี่ "120 นาที ที่ 25 ml/h") อยู่ใน JobInfo.check_notes  "กลุ่ม.รหัส" -> ข้อความ
"""
from __future__ import annotations

PASS, FAIL, NA = "pass", "fail", "na"
STATUSES = (PASS, FAIL, NA)
GROUPS = ("visual", "function", "performance")

# (รหัส, ไทย, อังกฤษ) — ลำดับตามแบบ: รายการไหลลงเป็น 2 คอลัมน์ (ซ้ายก่อนขวา)
ITEMS: dict[str, dict[str, list[tuple[str, str, str]]]] = {
    "infusion": {
        "visual": [("pole_clamp", "ตัวยึดเสา", "Pole clamp"), ("tubing_clamp", "ตัวหนีบสาย", "Tubing clamp"),
                   ("rubber_foot", "ยางรองฐาน", "Rubber foot"), ("ac_inlet", "ช่องเสียบสายไฟ", "AC inlet plug"),
                   ("front_panel", "แผงหน้าเครื่อง", "Front panel"), ("housing", "ตัวเครื่องและฝาครอบ", "Chassis and housing"),
                   ("door_lock", "ตัวล็อกประตู", "Door lock knob"), ("power_switch", "สวิตช์เปิดปิด", "Power switch")],
        "function": [("finger", "ชุดนิ้วบีบสาย", "Peristaltic finger"), ("keys", "ปุ่มกด", "Key function"),
                     ("buzzer", "เสียงเตือน", "Buzzer"), ("ac_charging", "ไฟ AC และการชาร์จ", "AC line and charging"),
                     ("display", "จอแสดงผล", "Display segment")],
        "performance": [("air_in_line", "ตรวจจับฟองอากาศ", "Air in line"),
                        ("occlusion", "ตรวจจับการอุดตัน", "Occlusion detection"),
                        ("battery", "แบตเตอรี่", "Battery")],
    },
    "syringe": {
        "visual": [("pole_clamp", "ตัวยึดเสา", "Pole clamp"), ("clutch", "คลัตช์", "Clutch"),
                   ("rubber_foot", "ยางรองฐาน", "Rubber foot"), ("slider", "ตัวเลื่อนและยางหุ้ม", "Slider and boot"),
                   ("front_panel", "แผงหน้าเครื่อง", "Front panel"), ("ac_inlet", "ช่องเสียบสายไฟ", "AC inlet plug"),
                   ("syringe_clamp", "ตัวยึดกระบอกฉีด", "Syringe clamp"), ("casing", "ตัวเครื่อง", "Pump casing")],
        "function": [("display", "จอแสดงผล", "Display segment"), ("buzzer", "เสียงเตือน", "Buzzer"),
                     ("keys", "ปุ่มกด", "Key function"), ("purge", "การไล่อากาศ", "Purge"),
                     ("battery", "แบตเตอรี่", "Battery"), ("ac_charging", "ไฟ AC และการชาร์จ", "AC line and charging")],
        "performance": [("size_detect", "ตรวจจับขนาดกระบอกฉีด", "Syringe size detection"),
                        ("occlusion", "ตรวจจับการอุดตัน", "Occlusion detection"),
                        ("nearly_empty", "เตือนยาใกล้หมด", "Nearly empty detection")],
    },
}

# รายละเอียดสั้นที่ใส่ให้เองเมื่อผลเป็น "ผ่าน" และไม่ได้พิมพ์รายละเอียดไว้ (ไทย, อังกฤษ)
PASS_DETAIL = {
    "air_in_line": ("เตือนเมื่อมีฟองอากาศในสาย", "alarms on air in the line"),
    "size_detect": ("อ่านขนาดกระบอกฉีดถูกต้อง", "reads the syringe size correctly"),
    "nearly_empty": ("เตือนเมื่อยาใกล้หมด", "alarms when nearly empty"),
    "occlusion": ("ตรวจจับได้", "detected"),
}
# ข้อที่ควรมีรายละเอียด (ช่องกรอกใน wizard) — แบตเตอรี่ = เวลาที่ทำงานได้ที่ rate ที่ทดสอบ
# แบตเตอรี่ย้ายไปช่องตัวเลข (อัตราที่ทดสอบ + เวลาที่ใช้งานได้) ในค่าที่วัดด้วยมือ — ผู้ใช้ 2026-11-19
NOTE_ITEMS: dict = {}


def items(pump: str, group: str) -> list[tuple[str, str, str]]:
    """รายการ (key เต็ม "กลุ่ม.รหัส", ไทย, อังกฤษ) ของชนิดเครื่อง + กลุ่ม"""
    pump = pump if pump in ITEMS else "infusion"
    return [(f"{group}.{code}", th, en) for code, th, en in ITEMS[pump][group]]


def all_keys(pump: str) -> list[str]:
    return [key for group in GROUPS for key, _, _ in items(pump, group)]


def summary(pump: str, checks: dict) -> dict:
    """นับผลรายข้อ: {"pass": n, "fail": n, "na": n, "blank": n}"""
    out = {PASS: 0, FAIL: 0, NA: 0, "blank": 0}
    for key in all_keys(pump):
        status = (checks or {}).get(key, "")
        out[status if status in STATUSES else "blank"] += 1
    return out


# ------------------------------------------------------------------ เก็บเฉพาะข้อยกเว้น (ผู้ใช้เสนอ 2026-11-18)
# ทุกข้อตั้งต้น "ผ่าน" — เก็บแค่ข้อที่ไม่ใช่ผ่าน: {"กลุ่ม.รหัส": "fail" | "na" | "" (ยังไม่ตรวจ)} + รุ่นของรายการตรวจ
# รุ่น 0 = ไม่เคยบันทึก (งานเก่า -> ช่องว่างทั้งหมด ไม่เดาว่าผ่าน)
# เพิ่มรายการใหม่ภายหลัง: เพิ่ม CHECKLIST_VERSION และใส่รหัสของข้อใหม่ใน ADDED_IN[รุ่นใหม่]
#   -> งานที่บันทึกด้วยรุ่นเก่า ข้อใหม่จะเป็นช่องว่าง (ไม่ถูกนับว่าผ่านเอง)
CHECKLIST_VERSION = 1
ADDED_IN: dict[int, set[str]] = {}          # รุ่น -> {"กลุ่ม.รหัส"} ที่เพิ่มในรุ่นนั้น (รุ่น 1 = ทุกข้อใน ITEMS ตอนนี้)


def _since(key: str) -> int:
    return next((version for version, keys in sorted(ADDED_IN.items()) if key in keys), 1)


def compress(pump: str, full: dict) -> dict:
    """ผลครบทุกข้อ -> เฉพาะข้อยกเว้น (ไม่ใช่ผ่าน รวมข้อที่ยังไม่ตรวจเป็น "")"""
    return {key: (full or {}).get(key, "") for key in all_keys(pump) if (full or {}).get(key, "") != PASS}


def expand(pump: str, exceptions: dict, version: int) -> dict:
    """ข้อยกเว้น + รุ่น -> ผลครบทุกข้อ · รุ่น 0 = ข้อมูลเก่า (dict ครบอยู่แล้ว หรือว่าง = ไม่เคยบันทึก)"""
    exceptions = exceptions or {}
    if not version:
        return {k: v for k, v in exceptions.items() if v in STATUSES}
    out = {}
    for key in all_keys(pump):
        if key in exceptions:
            if exceptions[key] in STATUSES:
                out[key] = exceptions[key]
        elif _since(key) <= version:
            out[key] = PASS
    return out


def describe(pump: str, full: dict, lang: str = "th") -> str:
    """ข้อความสั้นของผลรายข้อ เช่น "ตัวล็อกประตู ไม่ผ่าน · แบตเตอรี่ ไม่มี" หรือ "ผ่านทุกข้อ" """
    names = {key: (th if lang == "th" else en) for group in GROUPS for key, th, en in items(pump, group)}
    words = {FAIL: ("ไม่ผ่าน", "fail"), NA: ("ไม่มี", "N/A")}
    parts = [f"{names[key]} {words[status][0 if lang == 'th' else 1]}" for key, status in (full or {}).items()
             if key in names and status in words]
    count = summary(pump, full)
    if not parts and not count["blank"]:
        return "ผ่านทุกข้อ" if lang == "th" else "all items pass"
    if count["blank"]:
        parts.append(f"ยังไม่ตรวจ {count['blank']} ข้อ" if lang == "th" else f"{count['blank']} not checked")
    return " · ".join(parts)
