"""ข้อมูลของใบรายงาน 1 ใบ — รวมผลหลาย session (หลาย rate) ของงานเดียวกัน + ข้อมูลที่กรอกเพิ่มสำหรับใบ (ไม่มี Qt)

ทางเดินข้อมูล:
    Repository.list()/job_sessions()  -> summary dict ของแต่ละ rate
    group_jobs(sessions)              -> งานละ 1 กลุ่ม (job_id เดียวกัน = ใบเดียว; Quick Test ไม่มีใบ)
    collect(group, intervals_of, info_row, options) -> ReportJob   (เลือกผลที่ใช้ได้ราย rate + คำเตือน)
    layout.document(job, lang)        -> HTML

กติกาเลือกผลราย rate: ผลล่าสุดที่ทดสอบครบ (completed) และไม่ INVALID · rate ที่ไม่มีผลแบบนี้ไม่ลงใบ และมีคำเตือน
จำนวนรอบปั๊มในใบ = จำนวนช่วงของสาย A (วิธีจับรอบคู่มี 2 สายซ้อนกัน interval_count จึงเป็น ~2 เท่าของรอบจริง)
กราฟ flow รายช่วงใช้สาย A (รอบต่อเนื่องไม่ซ้อนกัน) · เส้นค่าเฉลี่ย = ค่าที่วัดได้ของผล (ทั้ง 2 สาย)
± ของเวลา/ปริมาตรต่อช่วง = 1 SD ของทุกช่วง
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, fields
from typing import Callable

from services.report import checklist
from services.report.signatures import default_slots

KINDS = ("inspection", "calibration")      # quick_test ไม่มีแบบเอกสาร


SERVICE_KINDS = ("pm", "repair", "calib")     # บำรุงรักษา · ซ่อม · สอบเทียบ


def auto_service_types(kind: str, parts_replaced=None) -> set[str]:
    """ประเภทงานที่คิดเอง (ผู้ใช้ 2026-11-20): บำรุงรักษาเสมอ (ทั้ง Inspection และ Calibration) · Calibration -> สอบเทียบ ด้วย
    · มีอะไหล่ที่เปลี่ยน -> ซ่อม ด้วย — แก้ได้ใน wizard ขั้น 4 (เดิม 2026-11-18: Calibration ติ๊กแค่สอบเทียบ)"""
    kinds = {"pm"}
    if kind == "calibration":
        kinds.add("calib")
    if any(str(p).strip() for p in (parts_replaced or [])):
        kinds.add("repair")
    return kinds


# ------------------------------------------------------------------ ค่าตั้งของใบ (จาก AppSettings)
@dataclass
class Signer:
    name: str = ""
    position: str = ""
    image: str = ""         # path ของภาพลายเซ็น PNG (ว่าง = ไม่มี เซ็นด้วยมือ)


@dataclass
class ReportOptions:
    mark: str = "M.Care"
    company: str = "M.Care Engineering Co., Ltd."
    address_th: str = "56-56/1 หมู่ 7 ต.เสาธงหิน อ.บางใหญ่ จ.นนทบุรี 11140"
    address_en: str = "56-56/1 Moo 7, Saothonghin, Bangyai, Nonthaburi 11140"
    logo: str = ""                     # path ของโลโก้ (ว่าง = ใช้ชื่อย่อตัวหนาแบบในแบบ)
    balance_model: str = "A&D GF-300"
    balance_serial: str = "14654769"
    balance_capacity: str = "310 g"
    balance_readability: str = "0.001 g"
    leak_limit_ua: float = 300.0
    supply_ref: str = "AC Supply 200-230VAC"     # อ้างอิงแรงดันไฟ (ว่าง = ไม่แสดง)
    balance_cal_date: str = ""                   # วันสอบเทียบตราชั่ง (ISO) — ใบ Calibration (ผู้ใช้ 2026-11-20)
    balance_due_date: str = ""                   # วันครบกำหนดสอบเทียบครั้งถัดไป
    signers: list = field(default_factory=list)   # list[Signer] — ค้นด้วยชื่อ (ผู้ทดสอบในงาน = ผู้ตรวจ/ผู้สอบเทียบ)
    reviewer: str = ""                 # ชื่อผู้ทวนสอบ (Calibration)
    approver: str = ""                 # ชื่อผู้อนุมัติ (Calibration)
    chart_style: str = "step"          # กราฟ flow รายช่วง: step = ขั้นบันได | points = จุดต่อเส้น
    chart_mean: bool = True            # เส้นค่าเฉลี่ยแนวนอน
    chart_moving: bool = False         # เส้นค่าเฉลี่ยสะสม
    # ---- ผู้ลงนาม + ช่องลายเซ็น (services/report/signatures.py — ผู้ใช้ 2026-11-20) · ภาพเป็น path เต็มแล้ว
    people: list = field(default_factory=list)          # list[Person]
    sign_insp: list = field(default_factory=lambda: default_slots("inspection"))     # list[SignSlot] หน้า 1
    sign_cal: list = field(default_factory=lambda: default_slots("calibration"))     # ใบรับรอง Calibration หน้า 2
    # ---- ปรับแต่งเนื้อหา (ค่าตั้ง report.*) — ไม่แสดง ≠ ลบข้อมูล
    footer_version: bool = True
    footer_trace: bool = True
    cal_pages: str = "all"             # all | no_uncertainty | certificate
    u_column: str = "ml_h"             # ml_h | pct | hide (ตารางผลใบรับรอง)
    cal_u: bool = True                 # ± U ที่มาตรวัด/กราฟ/Error% ± U ของใบ Calibration
    insp_u: bool = True
    cal_flow_2sd: bool = True
    insp_flow_2sd: bool = True
    cal_occl_2sd: bool = True

    def signer(self, name: str) -> Signer:
        key = " ".join(str(name or "").split()).lower()
        for item in self.signers:
            if key and " ".join(item.name.split()).lower() == key:
                return item
        return Signer(name=str(name or "").strip())


# ------------------------------------------------------------------ ข้อมูลที่กรอกเพิ่มสำหรับใบ
def _decimals(value: float) -> int:
    text = f"{value:.6f}".rstrip("0")
    return len(text.split(".", 1)[1]) if "." in text else 0


def occl_stats(runs) -> tuple[float, float, int] | None:
    """ความดันขณะเตือน 3 ครั้ง -> (ค่าเฉลี่ย, 2SD, ทศนิยมที่แสดง) — SD แบบตัวอย่าง (n−1), ค่าเดียว = 0
    ทศนิยม = มากกว่าค่าที่กรอก 1 ตำแหน่ง (0.7 -> 0.70 · 68 -> 69.3) ไม่เกิน 3"""
    values = [float(v) for v in (runs or []) if v is not None and v != ""]
    if not values:
        return None
    mean = sum(values) / len(values)
    sd = (sum((v - mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5 if len(values) > 1 else 0.0
    digits = min(3, max(_decimals(v) for v in values) + 1)
    return mean, 2.0 * sd, digits


@dataclass
class ReportInfo:
    """ข้อมูลของใบที่ไม่ใช่ผลวัด — ค่าตั้งต้นมาจาก JobInfo (wizard) แล้วทับด้วยที่แก้ภายหลัง (ตาราง job_reports)"""
    service_type: str = ""             # pm | repair | calib (ใบ Inspection)
    contact: str = ""
    contact_phone: str = ""
    checks: dict = field(default_factory=dict)        # "กลุ่ม.รหัส" -> pass | fail | na (services/report/checklist.py)
    check_notes: dict = field(default_factory=dict)   # "กลุ่ม.รหัส" -> รายละเอียดสั้น
    occl_level: str = ""               # ระดับที่ตั้ง เช่น "M"
    occl_runs: list = field(default_factory=lambda: [None, None, None])   # ความดันขณะเตือน 3 ครั้ง
    occl_low: float | None = None      # เกณฑ์ของผู้ผลิต
    occl_high: float | None = None
    occl_unit: str = "kPa"
    supply_v: float | None = None
    leak_ua: float | None = None
    whole_checked: bool = False
    label_attached: bool = False
    battery_rate: float | None = None      # อัตราที่ทดสอบแบตเตอรี่ (ml/h)
    battery_min: float | None = None       # ใช้งานได้นานกี่นาที
    check_weight_g: float | None = None    # ตุ้มน้ำหนักที่ใช้ตรวจตราชั่งก่อนใช้งาน
    check_reading_g: float | None = None

    _FROM_JOB = ("service_type", "contact", "contact_phone", "checks", "check_notes")

    @classmethod
    def merged(cls, job: dict | None, row: dict | None) -> "ReportInfo":
        """ข้อมูลงาน (ตาราง jobs / JobInfo) + ข้อมูลใบ (report_json) · ผลตรวจรายข้อขยายจากข้อยกเว้นเป็นครบทุกข้อ"""
        info = cls()
        job = job or {}
        for name in cls._FROM_JOB:
            value = job.get(name)
            if value:
                setattr(info, name, value)
        pump = str(job.get("pump_type") or "infusion")
        info.checks = checklist.expand(pump, job.get("checks") or {}, int(job.get("checks_version") or 0))
        names = {f.name for f in fields(cls)}
        # ค่าที่กรอกใน wizard (job.report) เป็นค่าตั้งต้น · ข้อมูลใบที่บันทึกภายหลัง (report_json) ทับ
        merged_row = dict(job.get("report") or {})
        merged_row.update(row or {})
        for name, value in merged_row.items():
            if name in names:
                setattr(info, name, value)
        runs = list(info.occl_runs or [])[:3]
        info.occl_runs = runs + [None] * (3 - len(runs))
        return info

    def to_row(self) -> dict:
        return asdict(self)

    # ---- ผลที่คิดได้
    def occl_values(self) -> list[float]:
        return [float(v) for v in self.occl_runs if v is not None and v != ""]

    def occl_mean(self) -> float | None:
        values = self.occl_values()
        return sum(values) / len(values) if values else None

    def occl_stats(self) -> tuple[float, float, int] | None:
        return occl_stats(self.occl_runs)

    def occl_status(self) -> str:
        """ผลการอุดตันจากตาราง 3 ครั้ง: pass | fail | "" (ไม่มีข้อมูล/ไม่มีเกณฑ์)"""
        mean = self.occl_mean()
        if mean is None or self.occl_low is None or self.occl_high is None:
            return ""
        return checklist.PASS if self.occl_low <= mean <= self.occl_high else checklist.FAIL

    def safety_status(self, limit: float) -> str:
        if self.leak_ua is None:
            return ""
        return checklist.PASS if float(self.leak_ua) <= limit else checklist.FAIL


# ------------------------------------------------------------------ ผลราย rate
@dataclass
class RateResult:
    set_rate: float
    method: str                 # cycle | time
    minutes: float
    n: int                      # รอบปั๊มจริง (สาย A) หรือจำนวนช่วงวัด
    n_intervals: int
    unit_s: float | None        # เวลาต่อช่วงเฉลี่ย ± SD
    unit_sd: float | None
    volume_ml: float | None     # ปริมาตรต่อช่วง ± SD
    volume_sd: float | None
    total_ml: float
    measured: float
    error: float
    sd2: float | None
    u: float | None             # ความไม่แน่นอน k=2 (%) — None = ยังไม่ได้ประเมิน
    tol: float
    verdict: str                # PASS | FAIL
    series: list = field(default_factory=list)   # [(นาทีเริ่ม, นาทีจบ, flow)] สำหรับกราฟ
    ref: str = ""
    started_at: str = ""
    summary: dict = field(default_factory=dict)
    set_minutes: float | None = None    # เวลาที่ตั้ง (จบตามเวลา) · None = จบตามจำนวนรอบ
    set_cycles: int | None = None       # จำนวนรอบที่ตั้ง (จบตามจำนวนรอบ)

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"


@dataclass
class ReportJob:
    kind: str                   # inspection | calibration
    pump: str                   # infusion | syringe
    job: dict                   # JobInfo เป็น dict
    job_id: str
    date_iso: str
    rates: list                 # list[RateResult] เรียงตาม rate
    info: ReportInfo
    options: ReportOptions
    env: dict = field(default_factory=dict)
    tol: float = 5.0
    refs: list = field(default_factory=list)        # ref ของทุก session ในงาน (รวมที่ไม่ได้ลงใบ)
    warnings: list = field(default_factory=list)    # (ข้อความอังกฤษ, ค่า) — แปลด้วย tr() ตอนแสดง
    step_count: int = 0

    @property
    def job_no(self) -> str:
        return str(self.job.get("job_no") or "").strip()

    @property
    def label(self) -> str:
        from services.report.layout import join_brand
        device = join_brand(self.job.get("brand"), self.job.get("model"))
        return " · ".join(p for p in (self.job_no or "—", self.kind.capitalize(), device) if p)

    def file_name(self, lang: str) -> str:
        stem = _safe_name(self.job_no or self.job.get("serial_no") or self.date_iso[:10] or "report")
        return f"{stem}_{self.kind.capitalize()}_{ {'en': 'EN', 'mix': 'TH-EN'}.get(lang, 'TH')}.pdf"

    # ---- ผลรวมของใบ
    def flow_status(self) -> str:
        if not self.rates:
            return ""
        return checklist.PASS if all(r.passed for r in self.rates) else checklist.FAIL

    def service_types(self) -> set[str]:
        """ประเภทงานในใบ: ติ๊กเองใน wizard ขั้น 4 / ข้อมูลใบรายงาน (JobInfo.service_kinds) — ไม่ได้แก้ = คิดเอง"""
        chosen = {str(k) for k in (self.job.get("service_kinds") or []) if str(k) in SERVICE_KINDS}
        return chosen or auto_service_types(self.kind, self.job.get("parts_replaced"))

    def check_status(self, key: str) -> str:
        """ผลของรายการตรวจ 1 ข้อ — ข้อที่คิดจากข้อมูลวัดได้ (การอุดตันที่กรอก 3 ครั้ง + เกณฑ์) ใช้ผลที่คิดได้ก่อน"""
        if key == "performance.occlusion":
            return self.info.occl_status() or self.info.checks.get(key, "")
        return self.info.checks.get(key, "")

    def overall_pass(self) -> bool:
        statuses = [self.check_status(key) for key in checklist.all_keys(self.pump)]
        statuses += [self.flow_status(), self.info.safety_status(self.options.leak_limit_ua)]
        statuses.append(self.info.occl_status())
        return checklist.FAIL not in statuses and self.flow_status() == checklist.PASS

    def missing(self) -> list[str]:
        """ข้อมูลของใบที่ยังไม่ได้กรอก (ข้อความอังกฤษ — แปลตอนแสดง)"""
        out = []
        count = checklist.summary(self.pump, {k: self.check_status(k) for k in checklist.all_keys(self.pump)})
        if count["blank"]:
            out.append(("{n} checklist items have no result", {"n": count["blank"]}))
        if self.info.leak_ua is None or self.info.supply_v is None:
            out.append(("Supply voltage / leakage current", {}))
        if self.kind == "calibration" and not self.info.occl_values():
            out.append(("Occlusion pressure (3 runs)", {}))
        return out


def _safe_name(text: str) -> str:
    bad = '<>:"/\\|?*'
    return "".join("_" if c in bad or ord(c) < 32 else c for c in str(text)).strip(" .") or "report"


# ------------------------------------------------------------------ รวมกลุ่ม / เลือกผล
def job_key(session: dict) -> str:
    """กุญแจของใบ: job_id (ทุก rate ของงานเดียวกัน) — ผลรุ่นเก่าที่ไม่มี job_id ใช้ ref ของตัวเอง"""
    config = session.get("config") or {}
    return str(config.get("job_id") or f"ref:{session.get('ref', '')}")


def group_jobs(sessions: list[dict]) -> list[list[dict]]:
    """แบ่ง session เป็นใบ (คงลำดับตามรายการที่ส่งมา) · ข้าม Quick Test"""
    groups: dict[str, list[dict]] = {}
    for session in sessions:
        if (session.get("config") or {}).get("run_mode") not in KINDS:
            continue
        groups.setdefault(job_key(session), []).append(session)
    return list(groups.values())


def _verdict(session: dict) -> str:
    from core.capture_check import effective_verdict
    return effective_verdict(session)


def _usable(session: dict) -> bool:
    return (session.get("end_reason") == "completed" and _verdict(session) in ("PASS", "FAIL")
            and session.get("mean_flow") is not None and session.get("error_pct") is not None)


def _sd(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))


def estimate_u(session: dict) -> float | None:
    """ความไม่แน่นอนขยาย U (k=2, %) ของ 1 rate — ยังไม่มีงบความไม่แน่นอน จึงคืน None (ใบแสดง "—")

    จุดต่อยอด: เมื่อทำงบความไม่แน่นอนแล้ว ให้คืนค่าจากที่นี่ ใบทุกส่วน (ตาราง มาตรวัด กราฟ) จะใช้เอง
    """
    value = session.get("uncertainty_pct")
    return float(value) if value is not None else None      # ไม่ปัด — ใบแสดง U % 3 ตำแหน่ง / ml/h 4 ตำแหน่ง


def rate_result(session: dict, intervals: list[dict]) -> RateResult:
    """ผล 1 rate จาก summary dict + ช่วงวัด (Repository.intervals)"""
    config = session.get("config") or {}
    target = float(config.get("target_flow") or 0.0)
    method = "cycle" if config.get("strategy") == "pump_cycle" else "time"
    chain_a = [iv for iv in intervals if int(iv.get("chain", 0)) == 0] or list(intervals)
    durations = [float(iv["duration_s"]) for iv in intervals]
    volumes = [float(iv["flow"]) * float(iv["duration_s"]) / 3600.0 for iv in intervals]
    series = []
    for iv in sorted(chain_a, key=lambda item: float(item["t"])):
        end = float(iv["t"]) / 60.0
        series.append((max(0.0, end - float(iv["duration_s"]) / 60.0), end, float(iv["flow"])))
    measured = float(session.get("mean_flow") or 0.0)
    # เวลาทดสอบ = จาก peak แรกถึงปลายรอบสุดท้าย (เวลาที่ใช้คำนวณจริง) — ไม่นับช่วงก่อน peak แรก/หลังรอบสุดท้าย
    # (เดิม max(เวลาตั้งแต่เริ่มวัด, ปลายรอบสุดท้าย) จึงรวมช่วงรอ peak แรกเข้าไปด้วย)
    if session.get("measured_s"):
        minutes = float(session["measured_s"]) / 60.0
    elif series:
        minutes = series[-1][1]
    else:
        minutes = float(session.get("duration_s") or 0.0) / 60.0
    unit = session.get("mean_duration_s")
    return RateResult(
        set_rate=target, method=method, minutes=minutes,
        n=len(chain_a) if method == "cycle" else len(intervals) or int(session.get("interval_count") or 0),
        n_intervals=int(session.get("interval_count") or len(intervals)),
        unit_s=(sum(durations) / len(durations)) if durations else (float(unit) if unit else None),
        unit_sd=_sd(durations),
        volume_ml=(sum(volumes) / len(volumes)) if volumes else None, volume_sd=_sd(volumes),
        total_ml=measured * minutes / 60.0, measured=measured, error=float(session.get("error_pct") or 0.0),
        sd2=session.get("sd2_pct"), u=estimate_u(session), tol=float(config.get("tolerance_pct") or 5.0),
        verdict=_verdict(session), series=series, ref=str(session.get("ref", "")),
        started_at=str(session.get("started_at", "")), summary=session,
        set_minutes=float(config.get("duration_min") or 0) or None if config.get("end_mode", "time") == "time" else None,
        set_cycles=int(config.get("cycle_count") or 0) or None if config.get("end_mode") == "count" else None,
    )


def _env(session: dict) -> dict:
    job = (session.get("config") or {}).get("job") or {}
    corr = session.get("correction") or {}
    return dict(
        water_t=job.get("temperature_c") if job.get("temperature_c") is not None else corr.get("liquid_temp_c"),
        air_t=corr.get("air_temp_c", job.get("air_temp_c")),
        rh=corr.get("humidity_pct", job.get("humidity_pct")),
        pressure=corr.get("pressure_hpa", job.get("pressure_hpa")),
        density=corr.get("water_density_g_per_ml") or session.get("density_g_per_ml"),
        per_gram=session.get("ml_per_g") or corr.get("ml_per_g"),
        evap=session.get("baseline_g_per_h"),
        # การระเหย (2026-11-20): วิธีที่ใช้ + ค่าแบบจำลอง (แสดงขีดฆ่าเมื่อใช้ evaporation trap) — ผลเก่าไม่มี = แบบเดิม
        evap_method=corr.get("evaporation_method") or "",
        evap_model=corr.get("evaporation_model_g_per_h"),
    )


def collect(group: list[dict], intervals_of: Callable[[str], list[dict]], info_row: dict | None,
            options: ReportOptions) -> ReportJob:
    """ประกอบใบ 1 ใบจาก session ของงานเดียวกัน (ทุก rate) — intervals_of(ref) คืนช่วงวัดของผลนั้น"""
    if not group:
        raise ValueError("empty job")
    first = min(group, key=lambda s: str(s.get("started_at", "")))
    config = first.get("config") or {}
    job = dict(config.get("job") or {})
    pump = str(job.get("pump_type") or "infusion")
    kind = str(config.get("run_mode") or "inspection")
    warnings: list = []
    by_rate: dict[float, list[dict]] = {}
    for session in group:
        rate = float((session.get("config") or {}).get("target_flow") or 0.0)
        by_rate.setdefault(rate, []).append(session)
    rates = []
    for rate in sorted(by_rate):
        candidates = sorted(by_rate[rate], key=lambda s: (str(s.get("started_at", "")), str(s.get("ref", ""))))
        usable = [s for s in candidates if _usable(s)]
        if not usable:
            state = _verdict(candidates[-1]) if candidates[-1].get("end_reason") == "completed" else "incomplete"
            warnings.append(("{rate:g} ml/h has no usable result ({state}) — left out of the report",
                             {"rate": rate, "state": state}))
            continue
        chosen = usable[-1]
        if len(candidates) > 1 and chosen is not candidates[-1]:
            warnings.append(("{rate:g} ml/h: the latest run is {state} — the earlier valid run is used",
                             {"rate": rate, "state": _verdict(candidates[-1])}))
        rates.append(rate_result(chosen, intervals_of(str(chosen.get("ref", "")))))
    step_count = max(int((s.get("config") or {}).get("step_count") or 1) for s in group)
    if rates and len(rates) < step_count:
        warnings.append(("Only {done} of {total} planned rates have a usable result", {"done": len(rates), "total": step_count}))
    if kind == "inspection" and len(rates) > 1:
        warnings.append(("This inspection has {n} rates — page 2 is repeated for each rate", {"n": len(rates)}))
    tol = rates[0].tol if rates else float(config.get("tolerance_pct") or 5.0)
    env_source = (rates[0].summary if rates else first)
    return ReportJob(
        kind=kind, pump=pump, job=job, job_id=str(config.get("job_id") or ""), date_iso=str(first.get("started_at", "")),
        rates=rates, info=ReportInfo.merged(job, info_row), options=options, env=_env(env_source), tol=tol,
        refs=[str(s.get("ref", "")) for s in group], warnings=warnings, step_count=step_count,
    )
