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
    auto_window_fraction: float = 0.4  # หน้าต่าง regression = คาบรอบปั๊ม x ค่านี้ (ค่าเริ่มต้นของ rate ที่ยังไม่ได้ปรับ)
    auto_half_fraction: float = 0.0    # n_bar = คาบรอบปั๊ม x ค่านี้ (0 = เท่ากับ auto_window_fraction)

    @property
    def half_fraction(self) -> float:
        return self.auto_half_fraction or self.auto_window_fraction
    auto_tune_timeout_s: float = 300.0 # หาคาบไม่ได้ภายในเวลานี้ -> เดาจากปริมาตรต่อรอบเริ่มต้น (ถ้าตั้งไว้) หรือใช้ค่ากำหนดเอง
    # ปริมาตรต่อรอบที่ใช้ "เดา" คาบรอบปั๊มของรุ่นที่ยังไม่มีข้อมูล (คาบ = ค่านี้ x 3600 / rate) 0 = ไม่เดา
    # ข้อมูลจริงของผู้ใช้ 2026-11: TE-112 + TI*PU200L 0.199, LF-600 0.211, TE-112 + ME 20 drops 0.118 ml
    default_stroke_volume_ml: float = 0.16
    # วิธีจับรอบปั๊ม: 2 = จับรอบคู่ (สาย A ยอด→ยอด + สาย B ก้น→ก้น วัดคู่กัน) · 1 = จับรอบเดียว (สาย A อย่างเดียว)
    cycle_chains: int = 2

    # เกณฑ์ "flow นิ่ง" ของโหมดเริ่มวัดอัตโนมัติ — ค่าของการทดสอบนี้ถูกคัดลอกมาจาก PrerunCriteria ที่ตรงกับ
    # ชนิดเครื่อง × วิธีจับ (หรือค่าเฉพาะของรุ่น) ตอนเริ่ม (SessionController._prepare_settings)
    stability_pct: float = 2.0         # ความแกว่งพื้นฐานที่ยอมรับ (% ของ flow เฉลี่ย)
    stability_window_s: float = 15.0   # ความยาว 1 ช่วงเทียบ (โหมดเวลา)
    stability_blocks: int = 4          # จำนวนช่วงติดกันที่นำมาเทียบ
    stability_block_mode: str = "time" # time = วินาที | cycle = คาบรอบปั๊ม x stability_block_cycles
    stability_block_cycles: int = 1
    stability_min_block_mg: float = 0.0    # ยืดช่วงเทียบจนน้ำหนักต่อช่วงถึงค่านี้ (rate ต่ำ)
    stability_align_cycle: bool = False    # ปัดช่วงเทียบขึ้นเป็นจำนวนเต็มเท่าของคาบ (ถ้ารู้คาบ)
    stability_max_wait_s: float = 0.0      # รอนิ่งได้นานสุด แล้วเริ่มวัดเลย (0 = รอจนกว่าจะนิ่ง)
    stability_source: str = ""             # ที่มาของเกณฑ์ เช่น "settings:syringe_time" | "model:syringe_time"
    expected_period_s: float = 0.0         # คาบรอบปั๊มที่รู้ล่วงหน้า (จากโปรไฟล์) 0 = ไม่รู้
    expected_period_source: str = ""       # rate | profile | model_default (ใช้ตรวจผลหลังจบได้เฉพาะ rate/profile)

    # ค่าแก้แปลงน้ำหนักเป็นปริมาตรตาม ISO 4787 (ปัจจัย Z — ดู core/corrections.py)
    air_buoyancy: bool = True              # แก้แรงลอยตัวของอากาศ (ปิด = หารด้วยความหนาแน่นน้ำอย่างเดียว)
    default_humidity_pct: float = 50.0     # ใช้เมื่อไม่ได้กรอกความชื้นในฟอร์ม
    default_pressure_hpa: float = 1013.25  # ใช้เมื่อไม่ได้กรอกความดันอากาศในฟอร์ม
    reference_density_g_per_ml: float = 8.0   # ความหนาแน่นตุ้มน้ำหนักที่ใช้สอบเทียบตราชั่ง (เหล็กกล้า OIML)

    # ค่าที่โปรแกรมกำหนดเองต่อการทดสอบ (ไม่แสดงในหน้าตั้งค่า)
    window_mode: str = "manual"        # manual | auto (วัดคาบรอบปั๊มก่อนเริ่ม)
    window_fit: str = "default"        # ที่มาของสัดส่วนหน้าต่าง: tuned | manual | uncalibrated | interpolated | default | plan
    baseline_g_per_h: float = 0.0      # อัตราน้ำหนักพื้นฐานจาก self-check (ระเหย = ค่าลบ)
    ml_per_g: float = 0.0              # ปัจจัย Z ของการทดสอบนี้ (ml ต่อ g) — 0 = ใช้ 1/density_g_per_ml

    @property
    def volume_factor(self) -> float:
        """ตัวคูณแปลงน้ำหนัก (g) เป็นปริมาตร (ml) ที่ใช้คำนวณจริง"""
        return self.ml_per_g if self.ml_per_g > 0 else 1.0 / self.density_g_per_ml


@dataclass
class PrerunCriteria:
    """เกณฑ์ "flow นิ่ง" ของโหมดเริ่มวัดอัตโนมัติ 1 ชุด — แยกตามชนิดเครื่อง x วิธีจับ (และแยกต่อรุ่นได้)"""
    stability_pct: float = 2.0         # ความแกว่งที่ยอมรับ (% ของ flow) — บวกส่วนเผื่อความละเอียดตราชั่งให้เอง
    block_mode: str = "time"           # time = ช่วงเทียบเป็นวินาที | cycle = ช่วงเทียบ = คาบรอบปั๊ม
    block_cycles: int = 1              # โหมด cycle: กี่คาบต่อ 1 ช่วง
    block_s: float = 30.0              # โหมด time (และ cycle ที่ยังไม่รู้คาบ)
    min_block_mg: float = 20.0         # ยืดช่วงจนน้ำหนักต่อช่วงถึงค่านี้ (กัน rate ต่ำที่ตราชั่ง 1 mg หยาบเกิน)
    align_to_cycle: bool = False       # โหมด time: ปัดเป็นจำนวนเต็มเท่าของคาบ (infusion ที่จับตามเวลา)
    blocks: int = 4                    # จำนวนช่วงติดกันที่เทียบ
    max_wait_min: float = 15.0         # รอนิ่งได้นานสุด แล้วเริ่มวัด + บันทึกว่ายังไม่ยืนยันว่านิ่ง (0 = รอไปเรื่อยๆ)


# กลุ่มของเกณฑ์: ชนิดเครื่อง x วิธีจับ (syringe จับรอบปั๊มไม่ได้ — ถ้าเลือกจับรอบปั๊มจะใช้กลุ่ม infusion_cycle)
PRERUN_GROUPS = ("infusion_cycle", "infusion_time", "syringe_time")


def prerun_group(pump_type: str, uses_cycles: bool) -> str:
    if uses_cycles:
        return "infusion_cycle"
    return "syringe_time" if pump_type == "syringe" else "infusion_time"


@dataclass
class PrerunSettings:
    """ค่าเริ่มต้นของเกณฑ์ช่วงก่อนวัด 3 กลุ่ม (ข้อเสนอของ AI 2026-11-12 — ยังไม่ยืนยันกับเครื่องจริง)"""
    infusion_cycle: PrerunCriteria = field(default_factory=lambda: PrerunCriteria(
        block_mode="cycle", block_cycles=1, block_s=15.0, min_block_mg=0.0, blocks=3, max_wait_min=15.0))
    infusion_time: PrerunCriteria = field(default_factory=lambda: PrerunCriteria(
        block_mode="time", block_s=15.0, min_block_mg=20.0, align_to_cycle=True, blocks=3, max_wait_min=15.0))
    syringe_time: PrerunCriteria = field(default_factory=lambda: PrerunCriteria(
        block_mode="time", block_s=30.0, min_block_mg=20.0, align_to_cycle=False, blocks=4, max_wait_min=20.0))

    def group(self, key: str) -> PrerunCriteria:
        return getattr(self, key if key in PRERUN_GROUPS else "infusion_cycle")


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
class BalanceSettings:
    """ตราชั่งมาตรฐานที่ใช้ — บันทึกลงทุกผลอัตโนมัติ (ย้ายมาจากช่อง "รหัสตราชั่ง" ในฟอร์มงาน 2026-11-13)"""
    model: str = "GF300"
    serial_no: str = "14654769"

    @property
    def label(self) -> str:
        return "  ".join(part for part in (self.model.strip(), f"S/N {self.serial_no.strip()}" if self.serial_no.strip() else "") if part)


@dataclass
class WarrantySettings:
    """ประกันอะไหล่: นับจากวันที่อะไหล่ชนิดนั้นลงระบบครั้งแรกของเครื่อง (เคลมไม่เริ่มนับใหม่)"""
    months: int = 12
    grace_months: int = 1       # เกินประกันไม่เกินเท่านี้ = "late" ให้พิจารณาเคลม


@dataclass
class UiSettings:
    refresh_ms: int = 33               # รอบการวาดกราฟ (~30 FPS)
    rolling_window_s: int = 300        # ความกว้างของโหมด Auto ตอนยังไม่รู้คาบรอบปั๊ม
    graph_range: str = "auto"          # มุมมองแกนเวลา: full = ทั้งการทดสอบ | auto = ตามคาบ | zoom = ช่วงล่าสุดแคบ
    graph_auto_cycles: int = 6         # โหมด Auto: กว้างกี่รอบปั๊ม/ช่วงวัด
    graph_zoom_s: int = 60             # โหมด Zoom: กว้างกี่วินาที
    max_points: int = 40000            # จำนวนจุดสูงสุดต่อกราฟ
    language: str = "th"               # "th" | "en"
    sound_on_finish: bool = True
    confirm_stop: bool = True
    # กราฟ flow รายช่วง (เลือกได้ข้างกราฟ)
    interval_style: str = "step"       # step = ขั้นบันได | points = จุดต่อเส้น
    interval_moving_avg: bool = True   # เส้น Moving avg = ค่าเฉลี่ยสะสมตั้งแต่ช่วงแรกถึงช่วงนั้น (ค่าเริ่มต้น)
    interval_overall_mean: bool = False  # เส้นค่าเฉลี่ยรวมแนวนอน
    interval_uncorrected: bool = True    # เส้นค่าเฉลี่ยสะสมของ flow ที่ยังไม่แก้ (1 g = 1 ml) เทียบกับค่าสุทธิ


@dataclass
class AppSettings:
    source: str = "serial"             # key ของ hardware.SOURCES
    serial: SerialSettings = field(default_factory=SerialSettings)
    simulator: SimulatorSettings = field(default_factory=SimulatorSettings)
    replay: ReplaySettings = field(default_factory=ReplaySettings)
    engine: EngineSettings = field(default_factory=EngineSettings)
    selfcheck: SelfCheckSettings = field(default_factory=SelfCheckSettings)
    prerun: PrerunSettings = field(default_factory=PrerunSettings)
    catalog: CatalogSettings = field(default_factory=CatalogSettings)
    balance: BalanceSettings = field(default_factory=BalanceSettings)
    warranty: WarrantySettings = field(default_factory=WarrantySettings)
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
