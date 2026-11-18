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


def save_info(repository, job: ReportJob, info: ReportInfo) -> None:
    key = job.job_id or f"ref:{job.refs[0] if job.refs else ''}"
    repository.set_report_info(key, info.to_row())
    job.info = info
