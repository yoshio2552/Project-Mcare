"""การตั้งค่าทั้งหมดของแอป เก็บเป็น dataclass และบันทึก/โหลดจาก JSON

เพิ่มค่าตั้งใหม่ = เพิ่ม field ใน dataclass ที่เกี่ยวข้อง (ไฟล์ JSON เก่ายังโหลดได้
เพราะ field ที่ไม่มีในไฟล์จะใช้ค่า default)
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path

from config.constants import SETTINGS_FILE

log = logging.getLogger("deltam.settings")


@dataclass
class SerialSettings:
    """พอร์ตอนุกรมของตราชั่ง (ค่าเริ่มต้น = 9600 7E1 ตามที่ใช้อยู่เดิม)"""
    port: str = "COM3"
    baudrate: int = 9600
    bytesize: int = 7
    parity: str = "E"
    stopbits: int = 1
    timeout_s: float = 0.15         # รอบการรอของพอร์ตต่อครั้ง (สั้น เพื่อให้หยุดได้ไว) — ไม่ใช่เวลารอคำตอบ
    mode: str = "auto"              # auto | stream (ตราชั่งส่งเอง) | poll (เราส่งคำสั่งถามค่า)
    poll_command: str = "Q"         # คำสั่งถามค่าน้ำหนัก (ต่อท้ายด้วย CR LF ให้เอง)
    poll_interval_s: float = 0.1    # จังหวะถามค่าในโหมด poll
    # รอคำตอบ "ทั้งบรรทัด" ได้นานสุดเท่านี้ (GF-300 จริงตอบใน ~0.19 s ที่ 2400 baud — เดิมรอ 0.15 s จึงได้บรรทัดขาด)
    response_timeout_s: float = 1.0
    line_format: str = "and"        # รูปแบบบรรทัด: key ของ hardware.parsers.LINE_FORMATS


@dataclass
class SimulatorSettings:
    """ตราชั่งจำลอง สำหรับพัฒนา/สาธิตโดยไม่ต้องต่อเครื่องจริง"""
    sample_rate_hz: float = 10.0
    speed: float = 20.0            # เร่งเวลา (1 = เวลาจริง)
    error_pct: float = 1.5         # ความคลาดเคลื่อนของปั๊มจำลอง
    ripple_pct: float = 15.0       # ขนาดการแกว่งของ flow ตามรอบ finger pump
    cycle_period_s: float = 60.0   # คาบของรอบปั๊ม
    noise_g: float = 0.0002        # noise ของตราชั่ง (SD)
    evaporation_mg_h: float = 0.0  # การระเหยจำลอง (น้ำหนักหายต่อชั่วโมง)


@dataclass
class ReplaySettings:
    """เล่นซ้ำไฟล์ข้อมูลดิบที่บันทึกไว้ (raw.csv) เหมือนเป็นตราชั่ง"""
    path: str = ""
    speed: float = 20.0


@dataclass
class EngineSettings:
    """พารามิเตอร์ของการคำนวณ — คัดลอก 1 ชุดต่อการทดสอบ (แก้ระหว่างรันไม่มีผล)"""
    warmup_s: float = 2.0              # ทิ้งข้อมูลช่วงแรก
    regression_window: int = 250       # จำนวนจุดของ linear regression (slope)
    cycle_half_window: int = 250       # n_bar ของตัวจับ peak/valley
    slope_clamp_factor: float = 5.0    # จำกัด slope ไม่เกิน target x ค่านี้
    density_g_per_ml: float = 0.9982   # ใช้เมื่อไม่ได้กรอกอุณหภูมิในฟอร์ม
    auto_window_fraction: float = 0.4  # หน้าต่าง = คาบรอบปั๊ม x ค่านี้
    auto_tune_timeout_s: float = 300.0 # หาคาบไม่ได้ภายในเวลานี้ -> ใช้ค่ากำหนดเอง
    # วิธีจับรอบปั๊ม: 2 = จับรอบคู่ (สาย A ยอด→ยอด + สาย B ก้น→ก้น วัดคู่กัน) · 1 = จับรอบเดียว (สาย A อย่างเดียว)
    cycle_chains: int = 2

    # เกณฑ์ "flow นิ่ง" ของโหมดเริ่มวัดอัตโนมัติ
    stability_pct: float = 2.0         # ความแกว่งพื้นฐานที่ยอมรับ (% ของ flow เฉลี่ย)
    stability_window_s: float = 15.0   # ความยาว 1 ช่วงเทียบ (ถ้ารู้คาบรอบปั๊มจะใช้คาบแทน)
    stability_blocks: int = 4          # จำนวนช่วงติดกันที่นำมาเทียบ

    # ค่าที่โปรแกรมกำหนดเองต่อการทดสอบ (ไม่แสดงในหน้าตั้งค่า)
    window_mode: str = "manual"        # manual | auto (วัดคาบรอบปั๊มก่อนเริ่ม)
    baseline_g_per_h: float = 0.0      # อัตราน้ำหนักพื้นฐานจาก self-check (ระเหย = ค่าลบ)


@dataclass
class SelfCheckSettings:
    """เกณฑ์ผ่านของ self-check (วัดการระเหย + การไหลของค่าตราชั่ง)"""
    duration_min: float = 10.0
    # "ไม่นิ่ง" = ครึ่งแรก/ครึ่งหลังต่างกันเกิน max_halves_diff_mg_h และ เกิน max_halves_z เท่าของความไม่แน่นอน
    max_halves_diff_mg_h: float = 30.0   # ต่างกันไม่เกินนี้ ถือว่านิ่งเสมอ (เล็กจนไม่มีผล)
    max_halves_z: float = 3.0            # ความต่างต้องเกิน noise ของตราชั่งกี่เท่าจึงนับว่าเปลี่ยนจริง
    blocks: int = 10                     # จำนวนช่วงย่อยที่ใช้ประเมินความไม่แน่นอน
    max_abs_rate_mg_h: float = 500.0     # อัตราที่มากกว่านี้ถือว่าผิดปกติ (มีอะไรรั่ว/ไหล)


@dataclass
class CatalogSettings:
    """รายการกลางที่ใช้ในขั้นตรวจเครื่อง (แก้ได้ในหน้าตั้งค่า เพื่อให้สะกดตรงกันทุกครั้ง)"""
    accessories: list = field(default_factory=lambda: [
        "Power cord", "Pole clamp", "Drop sensor", "Battery", "Syringe holder", "Manual",
    ])
    parts: list = field(default_factory=lambda: [
        "Battery", "Door / latch", "Pumping mechanism", "Pressure sensor",
        "Air-in-line sensor", "Keypad", "Display", "Main board", "Power board",
    ])


@dataclass
class UiSettings:
    refresh_ms: int = 33               # รอบการวาดกราฟ (~30 FPS)
    rolling_window_s: int = 300        # ความกว้างแกนเวลาของกราฟแบบเลื่อน
    max_points: int = 40000            # จำนวนจุดสูงสุดต่อกราฟ
    language: str = "th"               # "th" | "en"
    sound_on_finish: bool = True
    confirm_stop: bool = True
    # กราฟ flow รายช่วง (เลือกได้ข้างกราฟ)
    interval_style: str = "step"       # step = ขั้นบันได | points = จุดต่อเส้น
    interval_moving_avg: bool = True   # เส้น Moving avg = ค่าเฉลี่ยสะสมตั้งแต่ช่วงแรกถึงช่วงนั้น (ค่าเริ่มต้น)
    interval_overall_mean: bool = False  # เส้นค่าเฉลี่ยรวมแนวนอน


@dataclass
class AppSettings:
    source: str = "serial"             # key ของ hardware.SOURCES
    serial: SerialSettings = field(default_factory=SerialSettings)
    simulator: SimulatorSettings = field(default_factory=SimulatorSettings)
    replay: ReplaySettings = field(default_factory=ReplaySettings)
    engine: EngineSettings = field(default_factory=EngineSettings)
    selfcheck: SelfCheckSettings = field(default_factory=SelfCheckSettings)
    catalog: CatalogSettings = field(default_factory=CatalogSettings)
    ui: UiSettings = field(default_factory=UiSettings)

    # ---------------------------------------------------------------- I/O
    @classmethod
    def load(cls, path: Path = SETTINGS_FILE) -> "AppSettings":
        settings = cls()
        if path.exists():
            try:
                _merge(settings, json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError) as exc:
                log.warning("Could not read settings, using defaults: %s", exc)
        return settings

    def save(self, path: Path = SETTINGS_FILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")

    def reset(self) -> None:
        """คืนค่าเริ่มต้นทั้งหมด (แก้ในตัว object เดิม เพื่อให้ทุกส่วนที่ถืออยู่เห็นตรงกัน)"""
        _merge(self, asdict(AppSettings()))


def _merge(target, data: dict) -> None:
    """เขียนค่าจาก dict ลง dataclass แบบทนทาน: ข้าม key ที่ไม่รู้จัก/ชนิดไม่ตรง"""
    for f in fields(target):
        if f.name not in data:
            continue
        current, value = getattr(target, f.name), data[f.name]
        if is_dataclass(current):
            if isinstance(value, dict):
                _merge(current, value)
            continue
        try:
            if isinstance(current, list):
                setattr(target, f.name, [str(item) for item in value])
            else:
                setattr(target, f.name, type(current)(value))
        except (TypeError, ValueError):
            log.warning("Invalid setting %s=%r ignored", f.name, value)
