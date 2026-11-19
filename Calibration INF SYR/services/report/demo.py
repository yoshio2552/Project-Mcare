"""ข้อมูลตัวอย่างของใบรายงาน — ตัวเลขชุดเดียวกับแบบ Main Fable-1 (template/Main Fable-1) ในรูป summary dict + ช่วงวัด
แบบเดียวกับที่ Repository คืน ใช้เทียบหน้าตากับแบบ (tools/report_templates/fable/build.py Report) และในเทสต์

long_jobs() = ข้อมูลยาวสุดที่เป็นไปได้ (ชื่อยาว อะไหล่มาก 6 rate ค่าเกินเกณฑ์ รันนาน) สำหรับตรวจล้นกระดาษ
"""
from __future__ import annotations

from services.report.model import ReportOptions, collect, group_jobs


def series(mean: float, spread_pct: float, n: int, seed: int) -> list[float]:
    """flow รายช่วงสมมติแบบกำหนดได้ (สูตรเดียวกับ content.series ของแบบ)"""
    state, out = seed, []
    for _ in range(n):
        total = 0.0
        for _ in range(3):
            state = (state * 16807) % 2147483647
            total += state / 2147483647 - 0.5
        out.append(total * 2.0)
    centre = sum(out) / n
    sd = (sum((v - centre) ** 2 for v in out) / (n - 1)) ** 0.5
    scale = mean * spread_pct / 200.0 / sd
    return [mean + (v - centre) * scale for v in out]


INFO = dict(service_type="pm", contact="คุณสมหญิง ใจดี", contact_phone="043 000 000",
            supply_v=224, leak_ua=38, occl_level="M", occl_runs=[68, 71, 69], occl_low=40, occl_high=100,
            whole_checked=True, label_attached=True, check_weight_g=50, check_reading_g=50.0,
            battery_rate=25, battery_min=120)


def _job(pump, job_no, dept, brand, model, serial, asset, acc_brand, acc, parts, claimed, received, operator="สมชาย ตั้งใจ"):
    from services.report import checklist
    checks = {key: checklist.PASS for key in checklist.all_keys(pump)}
    notes = {"performance.battery": "120 นาที ที่ 25 ml/h"} if pump == "infusion" else {}
    return dict(pump_type=pump, job_no=job_no, site="โรงพยาบาลตัวอย่าง", province="ขอนแก่น", department=dept, brand=brand,
                model=model, serial_no=serial, asset_id=asset, accessory_brand=acc_brand, accessory=acc, operator=operator,
                temperature_c=23.4, accessories=received, parts_replaced=parts, parts_warranty=claimed,
                checks=checks, check_notes=notes, service_type="pm", contact=INFO["contact"],
                contact_phone=INFO["contact_phone"])


def _session(ref, job, mode, job_id, step, steps, rate, method, meas, sd2, unit_s, n, u, seed, minutes=None,
             verdict=None, tol=5.0, end="completed"):
    values = series(meas, sd2, n, seed)
    intervals, t = [], 0.0
    jitter = series(unit_s, 2.6 if method == "cycle" else 0.3, n, seed + 7)    # เวลาต่อรอบแกว่งเล็กน้อยแบบปั๊มจริง
    for index, flow in enumerate(values):
        duration = jitter[index] if n > 1 else unit_s
        t += duration
        intervals.append(dict(index=index, chain=0, t=t, duration_s=duration, flow=flow,
                              error_pct=(flow - rate) / rate * 100.0))
    error = (meas - rate) / rate * 100.0
    summary = dict(
        ref=str(ref), started_at=f"2026-11-17T09:{10 + step * 17:02d}:00", end_reason=end,
        duration_s=(minutes * 60.0) if minutes else n * unit_s, interval_count=n, mean_flow=meas, error_pct=error,
        sd2_pct=sd2, verdict=verdict or ("PASS" if abs(error) <= tol else "FAIL"), mean_duration_s=unit_s,
        density_g_per_ml=0.9975, ml_per_g=1.0036, baseline_g_per_h=0.012, uncertainty_pct=u,
        correction=dict(air_temp_c=24.1, humidity_pct=56, pressure_hpa=1008, water_density_g_per_ml=0.9975, ml_per_g=1.0036),
        config=dict(job=job, run_mode=mode, strategy="pump_cycle" if method == "cycle" else "time_interval",
                    target_flow=rate, tolerance_pct=tol, job_id=job_id, step_index=step, step_count=steps),
    )
    if mode == "calibration" and u is not None:
        # งบความไม่แน่นอนตัวอย่าง (หน้าสุดท้ายของใบ Calibration): คิดด้วย core/uncertainty.py จากน้ำหนัก/เวลารวมสมมติ
        # + 2SD ความซ้ำสมมติ ให้ U ใกล้ค่า u ของตัวอย่าง
        from config.settings import UncertaintySettings
        from core.uncertainty import budget
        summary["total_time_s"] = t
        summary["total_mass_g"] = meas * t / 3600.0 / 1.0036
        repeat = {"sd2_pct": u * 0.98, "sd2_ml_h": u * 0.98 / 100.0 * rate, "rate": rate,
                  "studies": [{"id": 3 + step, "kind": "measured", "sd2_pct": u * 0.98, "created_at": "", "runs": []}]}
        summary["uncertainty"] = budget(summary, UncertaintySettings(), repeat)
        summary["uncertainty_pct"] = summary["uncertainty"]["U_pct"]
    return summary, intervals


INF_PARTS = ["ชุดนิ้วบีบสาย", "แบตเตอรี่", "ตัวล็อกประตู", "เซนเซอร์ฟองอากาศ", "ยางรองฐาน 4 ชิ้น", "ฟิวส์", "แผ่นปุ่มกด"]


def sample_sessions() -> tuple[list[dict], dict]:
    """(sessions, intervals ตาม ref) ของ 4 ใบ: Inspection Infusion/Syringe · Calibration Infusion/Syringe"""
    inf = _job("infusion", "MCI-0142", "ICU 2", "Terumo", "TE-171", "17110582", "ICU-IP-031", "Terumo", "20 หยดต่อ ml",
               INF_PARTS, ["ชุดนิ้วบีบสาย", "เซนเซอร์ฟองอากาศ"], ["สายไฟ", "ตัวยึดเสา", "คู่มือการใช้งาน"])
    syr = _job("syringe", "MCS-0388", "NICU", "Terumo", "TE-331", "33104417", "NICU-SP-012", "Terumo", "50 ml",
               ["ตัวยึดกระบอกฉีด", "แบตเตอรี่"], ["ตัวยึดกระบอกฉีด"], ["สายไฟ", "ตัวยึดเสา"])
    rows = [
        (1, inf, "inspection", "J-INS-INF", 0, 1, 50.0, "cycle", 50.42, 2.4, 15.2, 58, 0.6, 4711, 14.7, 5.0),
        (2, syr, "inspection", "J-INS-SYR", 0, 1, 5.0, "time", 4.91, 1.9, 30.0, 60, 0.9, 1213, 30.0, 3.0),
        (3, inf, "calibration", "J-CAL-INF", 0, 3, 10.0, "time", 9.87, 3.1, 60.0, 14, 0.9, 9001, 14.0, 5.0),
        (4, inf, "calibration", "J-CAL-INF", 1, 3, 50.0, "cycle", 50.42, 2.4, 15.2, 58, 0.6, 9078, 14.7, 5.0),
        (5, inf, "calibration", "J-CAL-INF", 2, 3, 200.0, "cycle", 196.10, 7.8, 3.9, 231, 0.7, 9155, 15.0, 5.0),
        (6, syr, "calibration", "J-CAL-SYR", 0, 3, 1.0, "time", 0.988, 2.6, 60.0, 30, 1.1, 3301, 30.0, 3.0),
        (7, syr, "calibration", "J-CAL-SYR", 1, 3, 5.0, "time", 4.91, 1.9, 30.0, 60, 0.9, 3302, 30.0, 3.0),
        (8, syr, "calibration", "J-CAL-SYR", 2, 3, 20.0, "time", 20.12, 1.4, 30.0, 40, 0.5, 3303, 20.0, 3.0),
    ]
    sessions, intervals = [], {}
    for ref, job, mode, job_id, step, steps, rate, method, meas, sd2, unit, n, u, seed, minutes, tol in rows:
        summary, ivs = _session(ref, job, mode, job_id, step, steps, rate, method, meas, sd2, unit, n, u, seed, minutes, tol=tol)
        sessions.append(summary)
        intervals[str(ref)] = ivs
    return sessions, intervals


def long_sessions() -> tuple[list[dict], dict]:
    """ข้อมูลยาวสุด: ชื่อยาว อะไหล่ 15 รายการ (เคลมครึ่งหนึ่ง) อุปกรณ์หลายชิ้น 6 rate (บาง rate เกินเกณฑ์มาก) รัน 4 ชั่วโมง"""
    long_site = "โรงพยาบาลมหาราชนครเชียงใหม่ คณะแพทยศาสตร์ มหาวิทยาลัยเชียงใหม่ อาคารศูนย์การแพทย์ฉุกเฉิน"
    parts = [f"อะไหล่ทดแทนชุดควบคุมมอเตอร์ลำดับที่ {i}" for i in range(1, 16)]
    out_s, out_i = [], {}
    for pump, prefix, mode in (("infusion", "MCI", "inspection"), ("syringe", "MCS", "inspection"),
                               ("infusion", "MCI", "calibration"), ("syringe", "MCS", "calibration")):
        job = _job(pump, f"{prefix}-2569-11-000123-REV2", "หอผู้ป่วยวิกฤตศัลยกรรมระบบประสาทและสมอง ชั้น 12", "Fresenius Kabi",
                   "Agilia Volumat MC Agilia Plus" if pump == "infusion" else "Agilia SP MC WiFi Plus",
                   "SN-2024-ABCDEFG-0001234567", "ครุภัณฑ์ 6515-001-0001/2567-ICU", "B. Braun",
                   "Intrafix SafeSet 180 cm 20 หยดต่อ ml" if pump == "infusion" else "Omnifix 50 ml Luer Lock",
                   parts, parts[::2], ["สายไฟ", "ตัวยึดเสา", "คู่มือการใช้งาน", "แบตเตอรี่สำรอง", "กระเป๋า", "สาย RS-232"],
                   operator="นายสมชายผู้มีชื่อยาวมาก นามสกุลยาวมากเป็นพิเศษ")
        job["site"] = long_site
        job["province"] = "พระนครศรีอยุธยา"
        job["contact"] = "นางสาวสมหญิง ใจดีมีน้ำใจงาม หัวหน้าหน่วยเครื่องมือแพทย์"
        job["contact_phone"] = "02 123 4567 ต่อ 12345"
        job["check_notes"] = {"performance.battery": "ทำงานต่อเนื่อง 240 นาที ที่ 25 ml/h ไม่มีสัญญาณเตือน"}
        job_id = f"LONG-{pump}-{mode}"
        rates = [0.5, 1.0, 5.0, 25.0, 100.0, 1200.0] if mode == "calibration" else [25.0]
        for step, rate in enumerate(rates):
            meas = rate * (1.0 + (0.18 if step % 2 else -0.012))     # บาง rate คลาดเคลื่อน +18 % (เกินมาก)
            ref = f"{job_id}-{step}"
            unit = 3.0 if rate >= 100 else 30.0
            n = int(240 * 60 / unit) if step == 0 else 120
            summary, ivs = _session(ref, job, mode, job_id, step, len(rates), rate, "cycle" if rate >= 25 else "time",
                                    meas, 9.5, unit, n, None, 5000 + step, tol=5.0)
            out_s.append(summary)
            out_i[ref] = ivs
    return out_s, out_i


def jobs(long: bool = False, options: ReportOptions | None = None):
    sessions, intervals = long_sessions() if long else sample_sessions()
    return [collect(group, lambda ref: intervals.get(ref, []), INFO, options or ReportOptions())
            for group in group_jobs(sessions)]
