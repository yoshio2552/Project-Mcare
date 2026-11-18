"""ประกอบใบรายงานจากของจริง: AppSettings -> ReportOptions, Repository -> ReportJob (ไม่มี Qt)

- jobs_for(repository, sessions, settings): session ที่เลือก (rate ใดก็ได้ของงาน) -> ใบละงาน ครบทุก rate ของงานนั้น
- language(settings): ภาษาเอกสารตามค่าตั้ง ("" = ตามภาษาโปรแกรม)
- save_info(repository, job, info): บันทึกข้อมูลที่กรอกเพิ่มของใบ (ตาราง job_reports)
"""
from __future__ import annotations

from pathlib import Path

from services.report.model import KINDS, ReportInfo, ReportJob, ReportOptions, Signer, collect, group_jobs, job_key


def options_from_settings(settings) -> ReportOptions:
    r, b = settings.report, settings.balance
    signers = []
    for line in r.signers or []:
        parts = [p.strip() for p in str(line).split("|")]
        if parts and parts[0]:
            signers.append(Signer(name=parts[0], position=parts[1] if len(parts) > 1 else "",
                                  image=parts[2] if len(parts) > 2 else ""))
    return ReportOptions(
        mark=r.company_mark, company=r.company_name, address_th=r.address_th, address_en=r.address_en, logo=r.logo,
        balance_model=b.model, balance_serial=b.serial_no, balance_capacity=b.capacity, balance_readability=b.readability,
        leak_limit_ua=float(r.leak_limit_ua or 300.0), signers=signers, reviewer=r.reviewer, approver=r.approver,
        chart_style=r.graph_style if r.graph_style in ("step", "points") else "step",
        chart_mean=bool(r.graph_mean), chart_moving=bool(r.graph_moving_avg),
    )


def language(settings) -> str:
    lang = (settings.report.language or settings.ui.language or "th").lower()
    return "en" if lang == "en" else "th"


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
EDITABLE_JOB_FIELDS = ("job_no", "site", "province", "department", "serial_no", "asset_id", "operator")


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
    report = {k: v for k, v in info.to_row().items() if k not in repository.JOB_REPORT_FIELDS}
    repository.save_job_record(key, stored, report)
    job.job = stored
    job.info = ReportInfo.merged(stored, report)
