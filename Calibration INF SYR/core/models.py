"""โครงสร้างข้อมูลที่วิ่งระหว่างชั้นต่างๆ (hardware -> core -> services -> ui)

ทุกชั้นคุยกันด้วย dataclass ในไฟล์นี้เท่านั้น ไม่ใช้ dict ที่ต้องจำชื่อ key
หน่วย: เวลา = วินาที, น้ำหนัก = กรัม, flow = ml/h, error = %
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PumpType(str, Enum):
    INFUSION = "infusion"
    SYRINGE = "syringe"


class RunMode(str, Enum):
    CALIBRATION = "calibration"
    INSPECTION = "inspection"
    QUICK_TEST = "quick_test"


class EndMode(str, Enum):
    TIME = "time"       # จบเมื่อครบเวลา (วิธีจับรอบปั๊มจะรอให้รอบสุดท้ายจบจริงก่อน)
    COUNT = "count"     # จบเมื่อครบจำนวนรอบปั๊ม


class StartMode(str, Enum):
    IMMEDIATE = "immediate"   # เริ่มวัดทันที
    DELAY = "delay"           # ปล่อยรันก่อนตามเวลาที่ตั้ง แล้วเริ่มวัด
    AUTO = "auto"             # รอจน flow นิ่งแล้วเริ่มวัดเอง
    MANUAL = "manual"         # ผู้ใช้ดูกราฟแล้วกดเริ่มเอง


class Stage(str, Enum):
    PRERUN = "prerun"         # ช่วงก่อนวัด (ข้อมูลไม่ถูกนำไปคิดผล)
    WARMUP = "warmup"         # รอให้หน้าต่างคำนวณเต็ม
    SEARCHING = "searching"   # รอจับรอบปั๊มรอบแรก
    MEASURING = "measuring"


class SessionState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ERROR = "error"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NONE = "N/A"       # ข้อมูลยังไม่พอจะตัดสิน
    INVALID = "INVALID"   # จับรอบปั๊มไม่ตรงคาบ / ช่วงวัดไม่พอ — ไม่ตัดสิน (core/capture_check.py)


# ------------------------------------------------------------------ input
@dataclass(frozen=True, slots=True)
class Sample:
    """ค่าที่อ่านได้จากตราชั่ง 1 ครั้ง"""
    t: float        # เวลา (s) นาฬิกา monotonic ของแหล่งข้อมูล
    weight: float   # น้ำหนัก (g)
    stable: bool | None = None   # ธงนิ่งจากตราชั่ง (None = ตราชั่งไม่ได้บอก)


@dataclass
class JobInfo:
    """ข้อมูลของงาน: เครื่องที่ทดสอบ ผู้ทดสอบ สภาพแวดล้อม (เพิ่มช่องกรอกใหม่ที่นี่)"""
    pump_type: PumpType = PumpType.INFUSION
    brand: str = ""
    model: str = ""
    serial_no: str = ""
    asset_id: str = ""
    department: str = ""
    accessory: str = ""                 # ชนิด/ขนาด syringe หรือยี่ห้อชุดสาย (ใช้เป็นส่วนหนึ่งของโปรไฟล์ปั๊ม)
    operator: str = ""
    balance_id: str = ""                # รหัสตราชั่งมาตรฐานที่ใช้
    temperature_c: float | None = None  # อุณหภูมิของเหลว -> ความหนาแน่นน้ำ
    humidity_pct: float | None = None   # ความชื้นสัมพัทธ์ของอากาศ -> ความหนาแน่นอากาศ (แรงลอยตัว)
    air_temp_c: float | None = None     # อุณหภูมิอากาศ (ว่าง = ใช้อุณหภูมิของเหลว)
    pressure_hpa: float | None = None   # ความดันอากาศ (ว่าง = ค่าในหน้าตั้งค่า)
    notes: str = ""
    accessories: list = field(default_factory=list)     # อุปกรณ์ที่มากับเครื่อง
    parts_replaced: list = field(default_factory=list)  # อะไหล่ที่เปลี่ยน

    @property
    def device_label(self) -> str:
        name = " ".join(part for part in (self.brand, self.model) if part)
        serial = f"S/N {self.serial_no}" if self.serial_no else ""
        return "  ·  ".join(part for part in (name, serial) if part)


@dataclass
class StepConfig:
    """1 ขั้นของแผนทดสอบ = 1 rate"""
    target_flow: float = 50.0       # ml/h
    duration_min: float = 5.0
    cycle_count: int = 30           # ใช้เมื่อ end_mode = COUNT
    window_s: float = 30.0          # ความยาวช่วงของวิธี time_interval
    # หน้าต่างจับรอบปั๊มของ rate นี้ที่ผู้ใช้กำหนดสำหรับแผนนี้ (สัดส่วนของคาบ, 0 = ใช้ค่าที่จำไว้ของรุ่น)
    regression_fraction: float = 0.0
    half_fraction: float = 0.0


@dataclass
class SessionConfig:
    """ทุกอย่างที่ engine ต้องรู้เพื่อรัน 1 rate"""
    job: JobInfo = field(default_factory=JobInfo)
    run_mode: RunMode = RunMode.INSPECTION
    strategy: str = "pump_cycle"
    end_mode: EndMode = EndMode.TIME
    start_mode: StartMode = StartMode.IMMEDIATE
    start_delay_s: float = 30.0
    target_flow: float = 50.0
    duration_min: float = 5.0
    cycle_count: int = 30
    window_s: float = 30.0
    regression_fraction: float = 0.0    # ค่ากำหนดของแผนนี้ (0 = ใช้ค่าที่จำไว้ของรุ่น) — ดู StepConfig
    half_fraction: float = 0.0
    tolerance_pct: float = 5.0
    window_source: str = "profile"  # profile | measure | recalibrate (เฉพาะวิธีจับรอบปั๊ม; "manual" เก่า = profile)
    job_id: str = ""                # sessions ของงานเดียวกันมี job_id เดียวกัน
    step_index: int = 0
    step_count: int = 1

    @property
    def duration_s(self) -> float:
        return self.duration_min * 60.0


@dataclass
class TestPlan:
    """แผนทดสอบ = ข้อมูลงาน + วิธีวัด + รายการ rate ที่จะทดสอบต่อเนื่อง"""
    job: JobInfo = field(default_factory=JobInfo)
    run_mode: RunMode = RunMode.INSPECTION
    strategy: str = "pump_cycle"
    end_mode: EndMode = EndMode.TIME
    start_mode: StartMode = StartMode.IMMEDIATE
    start_delay_s: float = 30.0
    tolerance_pct: float = 5.0
    window_source: str = "profile"
    steps: list[StepConfig] = field(default_factory=lambda: [StepConfig()])
    job_id: str = ""

    def session_config(self, index: int) -> SessionConfig:
        step = self.steps[index]
        return SessionConfig(
            job=self.job, run_mode=self.run_mode, strategy=self.strategy,
            end_mode=self.end_mode, start_mode=self.start_mode, start_delay_s=self.start_delay_s,
            target_flow=step.target_flow, duration_min=step.duration_min,
            cycle_count=step.cycle_count, window_s=step.window_s,
            regression_fraction=step.regression_fraction, half_fraction=step.half_fraction,
            tolerance_pct=self.tolerance_pct, window_source=self.window_source, job_id=self.job_id,
            step_index=index, step_count=len(self.steps),
        )


# ----------------------------------------------------------------- output
@dataclass(frozen=True, slots=True)
class ExtremumPoint:
    """จุด peak/valley ของ slope (สำหรับพล็อต)"""
    t: float
    flow: float
    kind: str       # "TOP" | "DOWN"


@dataclass(frozen=True, slots=True)
class Interval:
    """ผลของ 1 ช่วงวัด (1 รอบปั๊ม หรือ 1 ช่วงเวลา)"""
    index: int
    chain: int          # 0 = สาย A, 1 = สาย B (pump_cycle มี 2 สายสลับกัน)
    t: float            # เวลาตั้งแต่จุดเริ่มของสายนั้น ถึงปลายช่วง
    duration_s: float
    flow: float                 # flow สุทธิ (แก้ Z + self-check แล้ว) — ใช้ตัดสิน
    error_pct: float
    flow_raw: float = 0.0       # flow ที่ยังไม่แก้: Δw/Δt โดยถือ 1 g = 1 ml (แบบ ARGOS)
    error_raw_pct: float = 0.0


@dataclass(frozen=True, slots=True)
class IntervalStats:
    """สถิติสะสมของทุก interval"""
    count: int
    mean_flow: float
    mean_error_pct: float
    ci95_pct: float             # ±CI95 ของ flow เป็น % ของ target
    sd2_pct: float              # ±2SD ของ flow เป็น % ของ target
    mean_duration_s: float
    ci95_duration_s: float
    sd2_duration_s: float
    mean_flow_raw: float = 0.0          # ค่าเฉลี่ยของ flow ที่ยังไม่แก้
    mean_error_raw_pct: float = 0.0


@dataclass(frozen=True, slots=True)
class Cumulative:
    """flow เฉลี่ยสะสมตั้งแต่จุดเริ่มของแต่ละสาย (None = ยังไม่มีข้อมูล)"""
    t: float
    flow_a: float | None = None
    flow_b: float | None = None
    flow_all: float | None = None
    err_a: float | None = None
    err_b: float | None = None
    err_all: float | None = None

    @property
    def best_error(self) -> float | None:
        """error ที่เป็นตัวแทนดีที่สุด ณ ตอนนี้ (ALL > A)"""
        return self.err_all if self.err_all is not None else self.err_a

    @property
    def best_flow(self) -> float | None:
        return self.flow_all if self.flow_all is not None else self.flow_a


@dataclass(frozen=True, slots=True)
class PreRunStatus:
    """สถานะของช่วงก่อนวัด"""
    elapsed_s: float
    countdown_s: float | None = None    # โหมด DELAY: เวลาที่เหลือ
    variation_pct: float | None = None  # โหมด AUTO: ความแกว่งของ flow ล่าสุด
    limit_pct: float | None = None      # โหมด AUTO: เกณฑ์ที่ใช้จริง (รวมผลของความละเอียดตราชั่ง)
    period_s: float | None = None       # คาบรอบปั๊มที่ประเมินได้
    tuning: bool = False                # กำลังหาคาบรอบปั๊มเพื่อปรับหน้าต่างคำนวณ
    waiting_user: bool = False          # รอผู้ใช้กดเริ่ม
    block_s: float | None = None        # โหมด AUTO: ความยาวช่วงเทียบที่ใช้
    max_wait_s: float | None = None     # โหมด AUTO: รอนิ่งได้นานสุด (0 = ไม่จำกัด)


@dataclass(slots=True)
class EngineResult:
    """ผลลัพธ์ต่อ 1 sample ที่ engine ส่งให้ UI"""
    t: float                                # เวลาตั้งแต่เริ่มช่วงปัจจุบัน (pre-run หรือ วัดจริง)
    weight: float
    stage: Stage = Stage.MEASURING
    eta_s: float | None = None              # เวลาที่ต้องรอโดยประมาณ (ช่วง WARMUP)
    prerun: PreRunStatus | None = None
    measurement_started: bool = False       # True ที่ sample แรกของการวัดจริง (UI ล้างกราฟ)
    slope_flow: float | None = None         # flow ขณะนั้นจาก regression
    extremum: ExtremumPoint | None = None   # มีเมื่อเจอ peak/valley ใหม่
    interval: Interval | None = None        # มีเมื่อจบ 1 ช่วงวัด
    stats: IntervalStats | None = None      # อัปเดตพร้อม interval
    cumulative: Cumulative | None = None
    progress: float = 0.0                   # 0..1
    finished: bool = False


@dataclass
class SessionSummary:
    """สรุปผลตอนจบ session (บันทึกลงไฟล์ + แสดงในหน้า History)"""
    config: SessionConfig
    started_at: str = ""
    end_reason: str = ""            # completed | stopped | error
    duration_s: float = 0.0
    prerun_s: float = 0.0
    sample_count: int = 0
    interval_count: int = 0
    mean_flow: float | None = None          # flow สุทธิ (ใช้ตัดสิน)
    error_pct: float | None = None
    mean_flow_raw: float | None = None      # ยังไม่แก้ (1 g = 1 ml, ไม่หัก self-check) — เก็บไว้สอบย้อนหลัง
    error_raw_pct: float | None = None
    ci95_pct: float | None = None
    sd2_pct: float | None = None
    verdict: Verdict = Verdict.NONE
    source: str = ""
    regression_window: int = 0      # ค่าที่ใช้จริง (กรณีปรับอัตโนมัติ)
    cycle_half_window: int = 0
    pump_period_s: float | None = None
    mean_duration_s: float | None = None        # เวลาต่อช่วงวัดเฉลี่ย (จับรอบปั๊ม = เวลาต่อรอบ) — สำหรับ Dashboard
    sd2_duration_s: float | None = None
    volume_per_interval_ml: float | None = None # ปริมาตรต่อช่วงวัด (จับรอบปั๊ม = ปริมาตรต่อรอบ, ml สุทธิ)
    window_source: str = ""         # ที่มาของขนาดหน้าต่าง: profile | measured | model_default | default | plan
    sample_period_s: float | None = None    # ช่วงเวลาต่อจุดของตราชั่งระหว่างวัด (ค่ากลาง)
    points_per_cycle: float | None = None   # จุดต่อรอบปั๊ม = คาบ / ช่วงเวลาต่อจุด (น้อย = จับ peak หยาบ)
    capture_check: dict = field(default_factory=dict)   # ผลตรวจความสมเหตุสมผลของการจับรอบ (CaptureCheck)
    stability_confirmed: bool | None = None   # โหมดเริ่มอัตโนมัติ: flow นิ่งก่อนเริ่มวัดไหม (None = ไม่ได้ใช้โหมดนี้)
    stable_after_s: float | None = None       # นิ่งหลังเริ่มปั๊มกี่วินาที
    density_g_per_ml: float = 0.0
    density_source: str = ""        # temperature | settings
    baseline_g_per_h: float = 0.0   # ค่าแก้จาก self-check ที่ใช้ (0 = ไม่ได้ใช้)
    ml_per_g: float = 0.0           # ปัจจัย Z ที่ใช้จริง: flow สุทธิ = (flow ดิบ − baseline) × Z
    correction: dict = field(default_factory=dict)   # ที่มาของ Z ทั้งหมด (GravimetricCorrection)
    engine_settings: dict = field(default_factory=dict)   # ค่าคำนวณทั้งชุดที่ใช้จริง
    notes: list[str] = field(default_factory=list)
