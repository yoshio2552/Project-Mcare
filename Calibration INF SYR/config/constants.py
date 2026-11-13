"""ค่าคงที่ระดับแอป: ชื่อ เวอร์ชัน path และ preset ต่างๆ (ไม่มี logic)"""
import sys
from pathlib import Path

APP_NAME = "DeltaM"
APP_SUBTITLE = "Infusion & Syringe Pump Calibration"
APP_VERSION = "0.3.0"


def _app_dir() -> Path:
    """โฟลเดอร์ของโปรแกรม — data/ ต้องอยู่ข้าง exe ไม่ใช่ในโฟลเดอร์ชั่วคราวที่ exe แตกไฟล์ออกมา

    รันจากซอร์ส       -> โฟลเดอร์โปรเจ็ก (เหมือนเดิม)
    Nuitka            -> __compiled__.containing_dir (โฟลเดอร์ของ exe ทั้ง standalone และ onefile)
    PyInstaller       -> โฟลเดอร์ของ sys.executable
    (ดู docs/build-nuitka.md — ต้องยืนยันอีกครั้งตอนสร้าง exe จริง)
    """
    compiled = globals().get("__compiled__")
    if compiled is not None:
        containing = getattr(compiled, "containing_dir", None)
        return Path(containing) if containing else Path(sys.argv[0]).resolve().parent
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


ROOT_DIR = _app_dir()
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
