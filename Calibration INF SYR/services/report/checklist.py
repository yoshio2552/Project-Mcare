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
    "air_in_line": ("เตือนได้", "alarms"),
    "size_detect": ("ถูกต้อง", "correct"),
    "nearly_empty": ("เตือนได้", "alarms"),
    "occlusion": ("ตรวจจับได้", "detected"),
}
# ข้อที่ควรมีรายละเอียด (ช่องกรอกใน wizard) — แบตเตอรี่ = เวลาที่ทำงานได้ที่ rate ที่ทดสอบ
NOTE_ITEMS = {"performance.battery": ("เช่น 120 นาที ที่ 25 ml/h", "e.g. 120 min at 25 ml/h")}


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
