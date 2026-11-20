"""ใบรายงานตัวอย่างจากโค้ดจริงของโปรแกรม (services/report) — ไว้เทียบกับแบบ template/Main Fable-1

ใช้: python tools/report_templates/real_sample.py            -> template/Report-sample/ (PDF ไทย/อังกฤษ + PNG รายหน้า)
     python tools/report_templates/real_sample.py --long     ข้อมูลยาวสุด (ตรวจการย่อให้พอดีหน้า)
ไม่ต้องใช้ Edge หรือเน็ต (QtWebEngine + ฟอนต์ที่ฝังในโปรแกรม) · ตัวเลขเป็นข้อมูลตัวอย่าง (services/report/demo.py)
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402


def main() -> int:
    app = QApplication.instance() or QApplication([])
    from PySide6.QtPdf import QPdfDocument
    from services.report import demo, layout, render
    long = "--long" in sys.argv
    out = ROOT / "template" / ("Report-sample-long" if long else "Report-sample")
    (out / "png").mkdir(parents=True, exist_ok=True)
    # ตัวอย่างแสดงค่าตั้ง/ข้อมูลรอบ 6.20: วันสอบเทียบ/ครบกำหนดตราชั่ง + การระเหยคำนวณจากแบบจำลอง (ใบ Calibration)
    # · ฉบับ "ไทย + ศัพท์เทคนิคอังกฤษ" (mix) — ตรวจล้นหน้าทั้ง 3 ภาษา
    from services.report.model import ReportOptions
    jobs = demo.jobs(long=long, options=ReportOptions(balance_cal_date="2026-01-12", balance_due_date="2027-01-12"))
    for job in jobs:
        if job.kind == "calibration":
            job.env.update(evap_method="model", evap_model=abs(job.env.get("evap") or 0.012))
    bad = 0
    for lang in ("th", "en", "mix"):
        data, checks = render.check_layout_sync(layout.html_document(jobs, lang))
        tag = "Report-TH-EN" if lang == "mix" else f"Report-{lang.upper()}"
        try:
            render.save_pdf(data, out / f"{tag}.pdf")
        except render.FileLockedError:
            print("BAD", tag, "PDF is open in a viewer — close it and run again")
            bad += 1
            continue
        for item in checks:
            problem = item.get("over") or item.get("small") or item.get("free", 0) < 0
            bad += bool(problem)
            print(("BAD " if problem else "ok  ") + f"{tag} page {item['page']:2d} free {item['free']:4d}px fit {item.get('fit')}")
        doc = QPdfDocument()
        doc.load(str(out / f"{tag}.pdf"))
        for index in range(doc.pageCount()):
            doc.render(index, doc.pagePointSize(index).toSize() * 2).save(str(out / "png" / f"{tag}-{index + 1}.png"))
    print("output:", out, "· pages with problems:", bad)
    del app
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
