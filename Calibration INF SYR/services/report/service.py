"""ประกอบใบรายงานจากของจริง: AppSettings -> ReportOptions, Repository -> ReportJob (ไม่มี Qt)

- jobs_for(repository, sessions, settings): session ที่เลือก (rate ใดก็ได้ของงาน) -> ใบละงาน ครบทุก rate ของงานนั้น
- language(settings): ภาษาเอกสารตามค่าตั้ง ("" = ตามภาษาโปรแกรม)
- save_info(repository, job, info): บันทึกข้อมูลที่กรอกเพิ่มของใบ (ตาราง job_reports)
"""
from __future__ import annotations

from pathlib import Path

from services.report import signatures
from services.report.model import KINDS, ReportInfo, ReportJob, ReportOptions, collect, group_jobs, job_key


def options_from_settings(settings) -> ReportOptions:
    r, b = settings.report, settings.balance
    signatures.migrate(r)               # ค่าเก่า (signers/reviewer/approver) -> ผู้ลงนาม + ช่องลายเซ็น (ในหน่วยความจำ)
    people = signatures.people_from(r.people)
    for person in people:               # ภาพลายเซ็นเก็บสัมพัทธ์กับ data/ -> path เต็มสำหรับใบ
        person.image = signatures.image_file(person.image)
    return ReportOptions(
        mark=r.company_mark, company=r.company_name, address_th=r.address_th, address_en=r.address_en, logo=r.logo,
        balance_model=b.model, balance_serial=b.serial_no, balance_capacity=b.capacity, balance_readability=b.readability,
        leak_limit_ua=float(r.leak_limit_ua or 300.0), supply_ref=str(r.supply_ref or "").strip(), reviewer=r.reviewer, approver=r.approver,
        balance_cal_date=str(getattr(b, "cal_date", "") or ""), balance_due_date=str(getattr(b, "due_date", "") or ""),
        chart_style=r.graph_style if r.graph_style in ("step", "points") else "step",
        chart_mean=bool(r.graph_mean), chart_moving=bool(r.graph_moving_avg),
        chart_intervals=bool(getattr(r, "graph_intervals", True)),
        people=people, sign_insp=signatures.slots_from(r.sign_inspection, "inspection"),
        sign_cal=signatures.slots_from(r.sign_calibration, "calibration"),
        footer_version=bool(r.footer_version), footer_trace=bool(r.footer_trace),
        cal_pages=r.cal_pages if r.cal_pages in CAL_PAGES else "all",
        u_column=r.cal_u_column if r.cal_u_column in U_COLUMNS else "ml_h",
        cal_u=bool(r.cal_show_u), insp_u=bool(r.insp_show_u),
        cal_flow_2sd=bool(r.cal_show_flow_2sd), insp_flow_2sd=bool(r.insp_show_flow_2sd),
        cal_occl_2sd=bool(r.cal_show_occl_2sd),
    )


CAL_PAGES = ("all", "no_uncertainty", "certificate")
U_COLUMNS = ("ml_h", "pct", "hide")


def language(settings) -> str:
    """ภาษาเอกสาร: th | en | mix (ไทย + ศัพท์เทคนิคอังกฤษ — ผู้ใช้ 2026-11-20)"""
    lang = (settings.report.language or settings.ui.language or "th").lower()
    return lang if lang in ("en", "mix") else "th"


def default_folder(settings) -> Path:
    if settings.report.folder:
        return Path(settings.report.folder)
    documents = Path.home() / "Documents"
    return (documents if documents.is_dir() else Path.home()) / "DeltaM Reports"


def reportable(session: dict) -> bool:
    """ออกใบได้ไหม (Quick Test ไม่มีแบบเอกสาร)"""
    return (session.get("config") or {}).get("run_mode") in KINDS


def expand(repository, sessions: list[dict]) -> list[list[dict]]:
    """session ที่เลือก -> กลุ่มต่องาน โดยดึง rate อื่นของงานเดียวกันจากฐานข้อมูลมาครบ (คงลำดับของงานตามที่เลือก)"""
    groups = []
    for group in group_jobs(sessions):
        job_id = str((group[0].get("config") or {}).get("job_id") or "")
        full = repository.job_sessions(job_id) if job_id else []
        refs = {str(s.get("ref")) for s in full}
        groups.append(full + [s for s in group if str(s.get("ref")) not in refs] if full else group)
    return groups


def jobs_for(repository, sessions: list[dict], settings) -> list[ReportJob]:
    options = options_from_settings(settings)
    out = []
    for group in expand(repository, sessions):
        key = job_key(group[0])
        for session in group:           # SHA-256 ของ raw.csv.gz ตอนเก็บผล — พิมพ์ย่อในใบ (สอบย้อน)
            if "raw_sha256" not in session and hasattr(repository, "file_hash"):
                session["raw_sha256"] = repository.file_hash(str(session.get("ref", "")), "raw.csv.gz")
        out.append(collect(group, repository.intervals, repository.report_info(key), options))
        record = repository.job_record(key)
        if record:                      # ข้อมูลงานชุดเดียวของงาน (ทุก rate ใช้ชุดเดียวกัน)
            out[-1].job = dict(record[0])
            out[-1].info = ReportInfo.merged(record[0], record[1])
    return out


def job_for_plan(repository, job_id: str, settings) -> ReportJob | None:
    """ใบของงานที่เพิ่งทดสอบเสร็จ (หลังเก็บผลขั้นสุดท้าย)"""
    sessions = repository.job_sessions(job_id) if job_id else []
    jobs = jobs_for(repository, sessions, settings) if sessions else []
    return jobs[0] if jobs else None


def reload(repository, job: ReportJob, settings) -> ReportJob:
    """สร้างใบเดิมใหม่ (หลังแก้ข้อมูลใบ)"""
    sessions = [s for s in (repository.job_sessions(job.job_id) if job.job_id else [])] or \
        [s for s in repository.list() if str(s.get("ref")) in set(job.refs)]
    return jobs_for(repository, sessions, settings)[0]


# ข้อมูลเครื่อง/งานที่แก้ได้ภายหลังทีเดียวทั้งงาน (ยี่ห้อ รุ่น ชุดสาย ชนิดเครื่อง ไม่ให้แก้ — เป็นกุญแจของโปรไฟล์ปั๊มที่เรียนรู้แล้ว)
EDITABLE_JOB_FIELDS = ("job_no", "site", "province", "department", "serial_no", "asset_id", "operator",
                       # 2026-11-20 ข้อมูลใบแบบแท็บ: หมายเหตุ + ช่องขั้นสูง
                       "notes", "accessory_brand", "balance_id")


def job_key_of(job: ReportJob) -> str:
    return job.job_id or f"ref:{job.refs[0] if job.refs else ''}"


def save_info(repository, job: ReportJob, info: ReportInfo, device: dict | None = None) -> None:
    """บันทึกข้อมูลใบลงข้อมูลงานชุดเดียวของงาน (ตาราง jobs): ข้อมูลงาน + ผลตรวจแบบข้อยกเว้น -> job_json, ที่เหลือ -> report_json"""
    from services.report import checklist
    key = job_key_of(job)
    record = repository.job_record(key)
    stored = dict(record[0]) if record else dict(job.job)
    stored.update(service_type=info.service_type, contact=info.contact, contact_phone=info.contact_phone,
                  check_notes=dict(info.check_notes), checks=checklist.compress(job.pump, info.checks),
                  checks_version=checklist.CHECKLIST_VERSION)
    for name, value in (device or {}).items():
        if name in EDITABLE_JOB_FIELDS:
            stored[name] = str(value).strip()
        elif name in ("service_kinds", "accessories"):  # ประเภทงานที่ติ๊กเอง (ว่าง = คิดเอง) · อุปกรณ์ที่มากับเครื่อง
            stored[name] = [str(k) for k in (value or [])]
    report = {k: v for k, v in info.to_row().items() if k not in repository.JOB_REPORT_FIELDS}
    repository.save_job_record(key, stored, report)
    job.job = stored
    job.info = ReportInfo.merged(stored, report)
