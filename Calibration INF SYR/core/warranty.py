"""ประกันอะไหล่ (ไม่มี Qt) — กติกาของผู้ใช้ 2026-11-13

    • นับแยก "ต่อเครื่อง × ต่อชนิดอะไหล่" (เครื่อง = ยี่ห้อ + รุ่น + S/N) แต่ละชิ้นวันไม่เท่ากัน นับใครนับมัน
    • วันเริ่มประกัน = วันที่อะไหล่ชนิดนั้นลงระบบครั้งแรกของเครื่องนั้น
    • เปลี่ยนซ้ำ/เคลมระหว่างยังมีประกัน: บันทึกว่า "ประกัน ณ วันเดิม" — ห้ามเริ่มนับใหม่เด็ดขาด
    • ประกัน 12 เดือน (ตั้งได้) + late 1 เดือน (ตั้งได้): เกินประกันแต่ยังไม่พ้น late = ให้ผู้ใช้พิจารณาเคลม
    • หมดประกันแล้ว (พ้น late) และเปลี่ยนแบบไม่เคลม = อะไหล่ชิ้นใหม่ เริ่มประกันใหม่จากวันนั้น
      (ข้อนี้ AI ตัดสินเอง: กติกาของผู้ใช้ไม่ได้พูดถึงกรณีหมดประกันแล้ว — ปรับได้ที่ start_for())

สถานะ
    active   ยังอยู่ในประกัน (วันนี้ ≤ วันหมดประกัน)
    late     เกินประกันแล้ว แต่ไม่เกิน grace_months — แจ้งให้พิจารณาเคลม
    expired  พ้น late แล้ว — เคลมไม่ได้
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

ACTIVE, LATE, EXPIRED = "active", "late", "expired"


def add_months(day: date, months: int) -> date:
    """บวกเดือนแบบปฏิทิน (31 ม.ค. + 1 เดือน = 28/29 ก.พ.)"""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def parse_day(value) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class WarrantyStatus:
    start: date
    until: date             # วันสุดท้ายของประกัน
    late_until: date        # วันสุดท้ายที่ยังพิจารณาเคลมได้
    state: str              # active | late | expired
    days_left: int          # วันที่เหลือถึง until (ติดลบ = เกินมาแล้วกี่วัน)

    @property
    def claimable(self) -> bool:
        return self.state in (ACTIVE, LATE)


def status(start, today=None, months: int = 12, grace_months: int = 1) -> WarrantyStatus | None:
    start_day = parse_day(start)
    if start_day is None:
        return None
    today = parse_day(today) or date.today()
    until = add_months(start_day, months)
    late_until = add_months(until, grace_months)
    state = ACTIVE if today <= until else LATE if today <= late_until else EXPIRED
    return WarrantyStatus(start_day, until, late_until, state, (until - today).days)


@dataclass(frozen=True)
class PartRecord:
    """1 แถวของประวัติการเปลี่ยนอะไหล่ (จากตาราง part_replacements)"""
    part: str
    replaced_at: str        # วันที่เปลี่ยน (YYYY-MM-DD)
    warranty_start: str     # วันเริ่มประกันของอะไหล่ชนิดนี้ (ไม่เปลี่ยนเมื่อเคลม)
    claimed: bool = False   # เปลี่ยนครั้งนี้เป็นการเคลมประกัน


@dataclass(frozen=True)
class PartWarranty:
    """สรุปต่อชนิดอะไหล่ของเครื่อง 1 เครื่อง (ใช้ใน popup ตอนเครื่องกลับมาอีกครั้ง)"""
    part: str
    first_at: str           # วันเริ่มประกันปัจจุบัน
    last_at: str            # เปลี่ยนล่าสุดเมื่อ
    times: int              # เปลี่ยนมาแล้วกี่ครั้ง (ทุกช่วงประกัน)
    claims: int             # เคลมไปแล้วกี่ครั้งในช่วงประกันนี้
    status: WarrantyStatus


def _key(name: str) -> str:
    return " ".join(str(name or "").lower().split())


def summarize(records: list[PartRecord], today=None, months: int = 12, grace_months: int = 1) -> list[PartWarranty]:
    """ประวัติทั้งหมดของเครื่อง -> 1 แถวต่อชนิดอะไหล่ (ช่วงประกันล่าสุด) เรียงใกล้หมดประกันก่อน"""
    groups: dict[str, list[PartRecord]] = {}
    for record in sorted(records, key=lambda r: r.replaced_at):
        groups.setdefault(_key(record.part), []).append(record)
    result = []
    for items in groups.values():
        latest = items[-1]
        current = [r for r in items if r.warranty_start == latest.warranty_start]
        state = status(latest.warranty_start, today, months, grace_months)
        if state is None:
            continue
        result.append(PartWarranty(part=latest.part, first_at=latest.warranty_start, last_at=latest.replaced_at,
                                   times=len(items), claims=sum(r.claimed for r in current), status=state))
    order = {ACTIVE: 0, LATE: 1, EXPIRED: 2}
    return sorted(result, key=lambda w: (order[w.status.state], w.status.days_left))


def start_for(records: list[PartRecord], part: str, today=None, claimed: bool = False,
              months: int = 12, grace_months: int = 1) -> str:
    """วันเริ่มประกันของการเปลี่ยนอะไหล่ครั้งนี้

    ครั้งแรกของเครื่อง                         -> วันนี้ (เริ่มจับเวลา)
    เคลมประกัน (ยัง active / late)              -> วันเริ่มเดิม (ห้ามนับใหม่)
    ไม่เคลม แต่ประกันเดิมยัง active             -> วันเริ่มเดิม (ห้ามนับใหม่)
    ไม่เคลม และประกันเดิม late / expired แล้ว   -> วันนี้ (ชิ้นใหม่ที่ซื้อเปลี่ยน)
    """
    today_day = parse_day(today) or date.today()
    same = [r for r in records if _key(r.part) == _key(part)]
    if not same:
        return today_day.isoformat()
    latest = max(same, key=lambda r: r.replaced_at)
    state = status(latest.warranty_start, today_day, months, grace_months)
    if state is None:
        return today_day.isoformat()
    if (claimed and state.claimable) or state.state == ACTIVE:
        return state.start.isoformat()
    return today_day.isoformat()
