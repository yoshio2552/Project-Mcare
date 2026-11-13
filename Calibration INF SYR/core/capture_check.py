"""ตรวจความสมเหตุสมผลของผลจับรอบปั๊มหลังจบ (ข้อ ฉ)

ทำไม: session id 11 (200 ml/h) ใช้หน้าต่าง 250/250 จุด จึงจับ "รอบ" ได้ทุก 90 วินาที แทนคาบจริง 2.1 วินาที
ได้ 1 ช่วงวัด แล้วยังตัดสิน PASS ได้ — ผลแบบนี้ต้องไม่ถูกตัดสิน และไม่ถูกนำไปเรียนรู้

เกณฑ์ (เฉพาะวิธีที่จับรอบปั๊ม):
    ช่วงวัด < MIN_INTERVALS                       -> "too_few"          ข้อมูลไม่พอ
    เวลาต่อรอบเฉลี่ย / คาบอ้างอิง นอก 0.7–1.4      -> "period_mismatch"  จับรอบไม่ตรงคาบ
    ไม่มีคาบอ้างอิง                                -> "unverified"       ตรวจไม่ได้ (ไม่ถือว่าผิด แต่บันทึกไว้)
คาบอ้างอิง: คาบจากโปรไฟล์ที่เรียนรู้จากผลที่ผ่านแล้ว (เชื่อถือกว่า) ไม่มีจึงใช้คาบที่วัดได้ก่อนเริ่ม
ผลที่ไม่ผ่าน: Verdict.INVALID — เก็บไว้สอบย้อนหลังได้ แต่ขั้นไม่เลื่อน ไม่เรียนรู้ ไม่ปรับหน้าต่าง
ผลเก่าที่บันทึกก่อนมีการตรวจนี้ ตรวจย้อนจาก summary ตอนเปิดดู (check_summary) โดยไม่แก้ฐานข้อมูล
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

MIN_INTERVALS = 4
RATIO_RANGE = (0.7, 1.4)
INVALID_STATUSES = ("too_few", "period_mismatch")


@dataclass(frozen=True, slots=True)
class CaptureCheck:
    status: str                         # ok | too_few | period_mismatch | unverified
    intervals: int = 0
    mean_duration_s: float | None = None
    reference_period_s: float | None = None
    reference_source: str = ""          # profile | measured
    ratio: float | None = None          # เวลาต่อรอบเฉลี่ย / คาบอ้างอิง
    retrospective: bool = False         # ตรวจย้อนหลังจากผลเก่า

    @property
    def invalid(self) -> bool:
        return self.status in INVALID_STATUSES

    def to_dict(self) -> dict:
        return asdict(self)

    def message(self) -> str:
        """ข้อความอังกฤษสำหรับ tr() (ค่าตัวเลขใส่ด้วย .format ของผู้เรียก — ดู message_values)"""
        return {
            "too_few": "Not enough pump cycles were captured ({n}, at least {min} needed) — the result cannot be judged",
            "period_mismatch": "Captured cycles do not match the pump cycle: {d:.1f} s per cycle vs {p:.2f} s "
                               "expected ({ratio:.2f} ×) — the result cannot be judged",
            "unverified": "The pump cycle was not known, so the captured cycles could not be checked",
            "ok": "Captured cycles match the pump cycle ({ratio:.2f} ×)",
        }[self.status]

    def message_values(self) -> dict:
        return {"n": self.intervals, "min": MIN_INTERVALS, "d": self.mean_duration_s or 0.0,
                "p": self.reference_period_s or 0.0, "ratio": self.ratio or 0.0}


def check_cycle_capture(interval_count: int, mean_duration_s: float | None, expected_period_s: float | None,
                        measured_period_s: float | None) -> CaptureCheck:
    reference, source = None, ""
    if expected_period_s and expected_period_s > 0:
        reference, source = expected_period_s, "profile"
    elif measured_period_s and measured_period_s > 0:
        reference, source = measured_period_s, "measured"
    ratio = mean_duration_s / reference if reference and mean_duration_s else None
    if interval_count < MIN_INTERVALS:
        status = "too_few"
    elif ratio is None:
        status = "unverified"
    elif not RATIO_RANGE[0] <= ratio <= RATIO_RANGE[1]:
        status = "period_mismatch"
    else:
        status = "ok"
    return CaptureCheck(status, interval_count, mean_duration_s, reference, source, ratio)


def uses_cycles(summary: dict) -> bool:
    return (summary.get("config") or {}).get("strategy") == "pump_cycle"


def check_summary(summary: dict) -> CaptureCheck | None:
    """ผลตรวจของผลที่บันทึกแล้ว: ใช้ที่บันทึกไว้ ถ้าไม่มี (ผลรุ่นเก่า) ตรวจย้อนจาก summary — None = ไม่ใช่การจับรอบปั๊ม"""
    if not uses_cycles(summary):
        return None
    stored = summary.get("capture_check") or {}
    if stored.get("status"):
        fields = CaptureCheck.__dataclass_fields__
        return CaptureCheck(**{k: v for k, v in stored.items() if k in fields})
    engine = summary.get("engine_settings") or {}
    reliable = engine.get("expected_period_source", "") in ("rate", "profile", "")
    check = check_cycle_capture(int(summary.get("interval_count") or 0), summary.get("mean_duration_s"),
                                (engine.get("expected_period_s") or None) if reliable else None,
                                summary.get("pump_period_s"))
    return CaptureCheck(check.status, check.intervals, check.mean_duration_s, check.reference_period_s,
                        check.reference_source, check.ratio, retrospective=True)


def effective_verdict(summary: dict) -> str:
    """ผลตัดสินที่ควรแสดง: ผลเก่าที่จับรอบผิด = INVALID แม้ในฐานข้อมูลจะบันทึก PASS/FAIL ไว้"""
    verdict = str(summary.get("verdict", ""))
    check = check_summary(summary)
    if check is not None and check.invalid:
        return "INVALID"
    return verdict
