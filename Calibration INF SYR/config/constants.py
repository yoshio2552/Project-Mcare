"""ค่าคงที่ระดับแอป: ชื่อ เวอร์ชัน path และ preset ต่างๆ (ไม่มี logic)"""
from pathlib import Path

APP_NAME = "DeltaM"
APP_SUBTITLE = "Infusion & Syringe Pump Calibration"
APP_VERSION = "0.3.0"

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
LOG_DIR = DATA_DIR / "logs"
SETTINGS_FILE = DATA_DIR / "settings.json"

# rate มาตรฐานที่ใช้สอบเทียบ (ml/h) แยกตามชนิดเครื่อง -> แสดงเป็นปุ่มลัดบนหน้าจอ
RATE_PRESETS = {
    "infusion": (10.0, 50.0, 200.0),
    "syringe": (10.0, 50.0, 100.0),
}

# เกณฑ์ยอมรับเริ่มต้น (± % ของ rate ที่ตั้ง)
DEFAULT_TOLERANCE_PCT = {
    "infusion": 5.0,
    "syringe": 3.0,
}

# วิธีคำนวณเริ่มต้นของแต่ละชนิดเครื่อง (key ของ core.strategies)
DEFAULT_STRATEGY = {
    "infusion": "pump_cycle",
    "syringe": "time_interval",
}

# ค่าเริ่มต้นของแต่ละโหมด (rates=None -> ใช้ RATE_PRESETS ตามชนิดเครื่อง)
MODE_DEFAULTS = {
    "calibration": {"rates": None, "duration_min": 15.0},
    "inspection": {"rates": (50.0,), "duration_min": 5.0},
    "quick_test": {"rates": (50.0,), "duration_min": 2.0},
}

# ความยาวช่วงวัด (วินาที) ที่ให้เลือก — หน้าจอจะกรองเหลือเฉพาะค่าที่หารเวลาทดสอบลงตัว
WINDOW_CHOICES_S = (10, 15, 20, 30, 60, 120, 300, 600)
