"""แบบ W — Fleet summary: สรุปทั้งโรงพยาบาลในงานเดียว (Infusion + Syringe) บน A4 แนวนอน
error ทุกเครื่องเป็น "% ของเกณฑ์" แกนเดียวกันได้ทั้ง ±5 % และ ±3 % · Inspection เป็นตาราง matrix · ป้ายสถานะ 10 ดวงต่อแผ่น
"""
from common import (INF, SYR, INFUSION, SYRINGE, INK, GREY, RULE, PAPER, f, Ax, T, L, R, PL, PG, C, svg, fonts, dc)

HEADING = "แบบ W — Fleet summary: สรุปทุกเครื่องของโรงพยาบาลในงานเดียว error เป็น % ของเกณฑ์ (เทียบ infusion/syringe ได้), matrix ตรวจสภาพ, แผ่นป้ายสถานะ"
NOTE_FILL = "orange"
NOTE = ("W: ใบปะหน้าชุดใบรับรองสำหรับผู้บริหาร/วิศวกรรมการแพทย์ของโรงพยาบาล — ดูทั้งชุดในหน้าเดียว\n"
        "เกณฑ์ต่างกัน (±5 % / ±3 %) จึงแสดงเป็น % ของเกณฑ์: เส้น ±100 % = ขอบเกณฑ์\n"
        "ต้องเพิ่มในโปรแกรม: รวมหลายงานของโรงพยาบาลเดียวกันเป็นชุด (batch) · ป้ายสถานะพิมพ์บนสติกเกอร์ A4")

FONT = fonts("Instrument+Sans:wght@400;500;600;700", "Noto+Sans+Thai:wght@400;500;600")
ROOT = ("color: #161718; font-family: 'Instrument Sans', 'Noto Sans Thai', sans-serif; display: flex; flex-direction: column; "
        "font-variant-numeric: tabular-nums lining-nums")
CSS = """
.l{font-size:12px;line-height:16px;color:#5C5F62}
h2{margin:0;font-size:14px;line-height:20px;font-weight:600}
table{border-collapse:collapse;width:100%;font-size:12.5px;line-height:16px}
th{font-weight:500;color:#5C5F62;font-size:12px;line-height:15px;text-align:right;padding:3px 5px;border-bottom:1px solid #161718;vertical-align:bottom}
td{text-align:right;padding:2px 5px;border-bottom:1px solid #DCDCD8;height:20px;white-space:nowrap}
th:first-child,td:first-child{text-align:left;padding-left:0}
.tl{text-align:left}
.tc{text-align:center}
.tile{display:flex;flex-direction:column;gap:0;border-top:2px solid #161718;padding-top:4px}
.tile b{font-size:28px;line-height:32px;font-weight:600}
svg text{font-family:'Instrument Sans','Noto Sans Thai',sans-serif}
"""

# ---------------------------------------------------------------- ข้อมูลสมมติของทั้งชุด (MCI-0142 และ MCS-0388 ตรงกับแบบอื่น)
INF_RATES, SYR_RATES = (10, 50, 200), (1, 5, 25)
FLEET = [
    # job, type, model, serial, dept, errors (3 rates), status
    ("MCI-0142", "I", "Terumo TE-171", "17110582", "ICU 2", (-1.3, 0.8, -2.0), "pass"),
    ("MCI-0143", "I", "Terumo TE-171", "17110590", "ICU 2", (-0.6, 0.4, -1.1), "pass"),
    ("MCI-0144", "I", "Terumo TE-171", "17110611", "ICU 1", (1.2, 1.9, 0.6), "pass"),
    ("MCI-0145", "I", "Terumo TE-171", "17110634", "ER", (-2.4, -1.6, -2.9), "pass"),
    ("MCI-0146", "I", "Terumo TE-171", "17110652", "Med 3", (0.3, -0.2, -0.9), "pass"),
    ("MCI-0147", "I", "Infusomat Space", "251377", "Med 3", (-3.1, -2.2, -3.8), "pass"),
    ("MCI-0148", "I", "Infusomat Space", "251402", "Surg 1", (-1.0, 0.2, 0.9), "pass"),
    ("MCI-0149", "I", "Infusomat Space", "251415", "Surg 1", (-3.9, -4.6, -6.1), "fail"),
    ("MCI-0150", "I", "Volumat Agilia", "60218874", "OR", (2.1, 1.4, 0.7), "pass"),
    ("MCI-0151", "I", "Terumo TE-171", "17110609", "ER", (-1.4, -0.8, -1.7), "pass"),
    ("MCI-0152", "I", "Volumat Agilia", "60218901", "PICU", (0.9, 0.5, -0.4), "pass"),
    ("MCI-0153", "I", "Volumat Agilia", "60218933", "PICU", (-0.2, -0.7, -1.5), "pass"),
    ("MCS-0388", "S", "Terumo TE-331", "33104417", "NICU", (-2.2, -1.8, 0.3), "pass"),
    ("MCS-0389", "S", "Terumo TE-331", "33104420", "NICU", (-1.6, -1.4, -0.2), "pass"),
    ("MCS-0390", "S", "Terumo TE-331", "33104452", "NICU", (-0.8, -0.3, 0.5), "pass"),
    ("MCS-0391", "S", "Perfusor Space", "184412", "ICU 2", (1.1, 0.6, 0.2), "pass"),
    ("MCS-0392", "S", "Perfusor Space", "184430", "OR", (-2.6, -1.2, -0.6), "pass"),
    ("MCS-0393", "S", "Injectomat Agilia", "60411023", "PICU", (0.4, 0.9, 1.3), "pass"),
]
LIMIT = {"I": INFUSION["limit"], "S": SYRINGE["limit"]}


def _certs():
    """เลขใบรับรองเรียงตามลำดับออก — MCI-0142 = 0042 และ MCS-0388 = 0051 ให้ตรงกับแบบอื่น"""
    order = ["MCI-0142", "MCI-0143", "MCI-0144", "MCI-0145", "MCI-0146", "MCI-0147", "MCI-0148", "MCI-0150",
             "MCI-0151", "MCS-0388", "MCI-0152", "MCI-0153", "MCS-0389", "MCS-0390", "MCS-0391", "MCS-0392", "MCS-0393"]
    return {job: f"DM-C-2611-{42 + i:04d}" for i, job in enumerate(order)}


CERT = _certs()
COL = {"I": INF, "S": SYR}
HOSP = "โรงพยาบาลตัวอย่าง"
BATCH = "B-2611-07"


def strip(errs, typ, w=230, h=20, axis=False):
    """จุด 3 rate ของหนึ่งเครื่องบนแกน % ของเกณฑ์ (−150..+150): วงกลม = ต่ำ, สี่เหลี่ยม = กลาง, สามเหลี่ยม = สูง"""
    ax = Ax(6, w - 6, 0, 0, -150, 150, 0, 1)
    out = [R(ax.sx(-100), 0, ax.sx(100) - ax.sx(-100), h, COL[typ]["tint"]),
           L(ax.sx(0), 0, ax.sx(0), h, "#B5B8BA", 1),
           L(ax.sx(-100), 0, ax.sx(-100), h, INK, 1), L(ax.sx(100), 0, ax.sx(100), h, INK, 1)]
    ink = COL[typ]["ink"]
    norm = [max(-148, min(148, e / LIMIT[typ] * 100)) for e in errs]
    out.append(L(ax.sx(min(norm)), h / 2, ax.sx(max(norm)), h / 2, ink, 1.5))
    x, y = ax.sx(norm[0]), h / 2
    out.append(C(x, y, 4, "#ffffff", ink, 1.5))
    x = ax.sx(norm[1])
    out.append(R(x - 3.5, y - 3.5, 7, 7, ink))
    x = ax.sx(norm[2])
    out.append(PG(f"{x:.1f},{y - 5:.1f} {x + 5:.1f},{y + 4:.1f} {x - 5:.1f},{y + 4:.1f}", ink))
    return svg(w, h, f"errors at three rates as % of limit", out, style="display: block")


def strip_axis(w=230):
    ax = Ax(6, w - 6, 0, 0, -150, 150, 0, 1)
    out = []
    for v in (-100, 0, 100):
        out.append(T(ax.sx(v), 13, f"{v:+d} %".replace("+0 %", "0").replace("-", "−"), anchor="middle", fill=INK if v else GREY))
    return svg(w, 16, "axis: error as percent of limit", out)


def header(title, sub, right):
    return f"""
<header style="display: flex; justify-content: space-between; align-items: flex-end; gap: 24px">
  <div style="display: flex; flex-direction: column"><span class="l">[Company Name] · Calibration Laboratory</span>
  <span style="font-size: 26px; line-height: 32px; font-weight: 600; letter-spacing: -.01em">{title}</span>
  <span style="font-size: 13px; line-height: 18px; color: #3E4143">{sub}</span></div>
  <div style="text-align: right; font-size: 13px; line-height: 19px">{right}</div>
</header>"""


def calibration():
    n_i = sum(1 for d in FLEET if d[1] == "I")
    n_s = len(FLEET) - n_i
    n_fail = sum(1 for d in FLEET if d[6] == "fail")
    rows = []
    for job, typ, model, sn, dept, errs, st in FLEET:
        ink = COL[typ]["ink"]
        es = "".join(f'<td>{f(e, 1, True)}</td>' for e in errs)
        worst = max(abs(e) / LIMIT[typ] * 100 for e in errs)
        res = '<b style="font-weight: 600">Pass</b>' if st == "pass" else \
            '<b style="font-weight: 700; background: #161718; color: #ffffff; padding: 0 6px">FAIL</b>'
        cert = CERT.get(job, "report only")
        rows.append(f"""<tr><td><b style="font-weight: 600; color: {ink}">{job}</b></td><td class="tl">{"Infusion" if typ == "I" else "Syringe"}</td>
<td class="tl">{model}</td><td>{sn}</td><td class="tl">{dept}</td>{es}<td>±{LIMIT[typ]:.0f}</td><td>{worst:.0f} %</td>
<td style="padding: 0 8px">{strip(errs, typ)}</td><td class="tc">{res}</td><td class="tl">{cert}</td></tr>""")
    body = f"""
{header("Calibration summary", f"ใบสรุปผลการสอบเทียบทั้งชุด · {HOSP} · [จังหวัด]",
        f'Batch <b style="font-weight: 600">{BATCH}</b> · 11–13 Nov 2026<br><span class="l">covers {len(FLEET)} certificates · page 1 / 1</span>')}
<div style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); column-gap: 20px">
  <div class="tile"><span class="l">Devices calibrated</span><b>{len(FLEET)}</b><span class="l"><span style="color: {INF["ink"]}">{n_i} infusion</span> · <span style="color: {SYR["ink"]}">{n_s} syringe</span></span></div>
  <div class="tile"><span class="l">Pass</span><b>{len(FLEET) - n_fail}</b><span class="l">certificate issued</span></div>
  <div class="tile"><span class="l">Fail</span><b>{n_fail}</b><span class="l">tagged “do not use”, sent for repair</span></div>
  <div class="tile"><span class="l">Asset list coverage</span><b>18 / 19</b><span class="l">ICU-IP-044 not found on wards</span></div>
  <div class="tile"><span class="l">Next due</span><b>Nov 2027</b><span class="l">12-month interval</span></div>
</div>
<table>
<thead><tr><th>Job</th><th class="tl">Type</th><th class="tl">Model</th><th>Serial</th><th class="tl">Ward</th>
<th>low</th><th>mid</th><th>high</th><th>Limit %</th><th>Worst</th>
<th style="padding: 0 8px; text-align: left">error as % of limit · ○ low ■ mid ▲ high rate {strip_axis()}</th><th class="tc">Result</th><th class="tl">Certificate</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table>
<div style="display: grid; grid-template-columns: 1.4fr 1fr 1fr; column-gap: 24px; font-size: 12.5px; line-height: 17px; margin-top: auto; align-items: end">
  <p style="margin: 0">Rates: infusion 10 / 50 / 200 ml/h, limit ±5 %; syringe 1 / 5 / 25 ml/h, limit ±3 % (error, %). “Worst” = largest |error| ÷ limit:
  100 % is the edge of the limit. Each device has its own certificate with U (k = 2) and the decision rule.</p>
  <div style="display: flex; flex-direction: column; gap: 2px"><div style="height: 26px; border-bottom: 1px solid #161718"></div><span class="l">[Approver name] · Approved by</span></div>
  <div style="display: flex; flex-direction: column; gap: 2px"><div style="height: 26px; border-bottom: 1px solid #161718"></div><span class="l">[Hospital engineer] · Received by</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Summary only; the individual certificates are the record of calibration</span><span>FM-SUM-23 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Calibration W", 1123, 794, FONT, CSS, ROOT + "; padding: 30px 38px 22px 38px; gap: 12px", body)


# ---------------------------------------------------------------- Inspection: matrix
COLS = ["Housing", "Clamp", "Cord", "Keys", "Door / plunger", "Air / size", "Occlusion", "Battery",
        "Alarms", "Nurse call", "IEC 62353"]
# ค่าพิเศษ: (job, คอลัมน์) -> ผล — ค่าอื่น = ✓ · nurse call ส่วนใหญ่ไม่มี (–) · IEC 62353 ทำได้เฉพาะวันที่ 12
SPECIAL = {("MCI-0149", "Occlusion"): "x", ("MCI-0149", "Battery"): "x", ("MCI-0145", "Clamp"): "r",
           ("MCS-0392", "Battery"): "r", ("MCI-0150", "Nurse call"): "ok", ("MCI-0152", "Nurse call"): "ok"}
SAFETY_DONE = {"MCI-0147", "MCI-0148", "MCI-0149", "MCI-0150", "MCS-0391", "MCS-0392"}
INSP_FLOW = {"I": 25, "S": 5}


def cell(job, col):
    v = SPECIAL.get((job, col))
    if col == "Nurse call" and v is None:
        v = "na"
    if col == "IEC 62353" and v is None:
        v = "ok" if job in SAFETY_DONE else "np"
    v = v or "ok"
    return {"ok": ('<td class="tc">✓</td>'), "na": '<td class="tc" style="color: #5C5F62">–</td>',
            "np": '<td class="tc" style="color: #5C5F62">N/P</td>',
            "r": '<td class="tc" style="font-weight: 700; border: 1.5px solid #161718">R</td>',
            "x": '<td class="tc" style="font-weight: 700; background: #161718; color: #ffffff">✗</td>'}[v]


def inspection():
    rows = []
    for job, typ, model, sn, dept, errs, st in FLEET:
        cells = "".join(cell(job, c) for c in COLS)
        # syringe ตรวจที่ 5 ml/h = rate กลาง → ค่าเดียวกับใบ Calibration · infusion ตรวจที่ 25 ml/h (ค่าใกล้เคียง 50 ml/h)
        e = errs[1] if typ == "S" or st != "pass" else errs[1] * 0.9
        status = "FIT" if st == "pass" else '<b style="background: #161718; color: #ffffff; padding: 0 6px">NOT FIT</b>'
        rows.append(f"""<tr><td><b style="font-weight: 600; color: {COL[typ]["ink"]}">{job}</b></td><td class="tl">{model}</td><td class="tl">{dept}</td>
{cells}<td>{INSP_FLOW[typ]} ml/h {f(e, 1, True)} %</td><td class="tc">{status}</td></tr>""")
    head = "".join(f'<th class="tc" style="width: 54px">{c}</th>' for c in COLS)
    ok = []
    for c in COLS:
        vals = [cell(d[0], c) for d in FLEET]
        bad = sum(1 for v in vals if "✗" in v)
        rep = sum(1 for v in vals if ">R<" in v)
        ok.append(f'<td class="tc" style="font-weight: 600">{bad if bad else "0"}{f" · R{rep}" if rep else ""}</td>')
    body = f"""
{header("Inspection summary", f"ตารางสรุปการตรวจสภาพทั้งชุด · {HOSP}",
        f'Batch <b style="font-weight: 600">{BATCH}</b> · 11–13 Nov 2026<br><span class="l">{len(FLEET)} devices · page 1 / 1</span>')}
<table>
<thead><tr><th>Job</th><th class="tl">Model</th><th class="tl">Ward</th>{head}<th>Flow check</th><th class="tc">Status</th></tr></thead>
<tbody>{"".join(rows)}
<tr><td colspan="3" style="font-weight: 600; border-top: 1px solid #161718">Failed · repaired</td>{"".join(ok)}<td></td><td></td></tr></tbody></table>
<div style="display: grid; grid-template-columns: 1.3fr 1fr; column-gap: 28px; margin-top: auto; font-size: 12.5px; line-height: 17px">
  <div style="display: flex; flex-direction: column; gap: 4px">
    <h2>Key</h2>
    <p style="margin: 0">✓ passed · <b style="border: 1.5px solid #161718; padding: 0 4px">R</b> repaired on site, then passed ·
    <b style="background: #161718; color: #ffffff; padding: 0 4px">✗</b> failed · – not fitted · N/P not performed (analyser on site 12 Nov only).
    Flow check at 25 ml/h infusion (±5 %), 5 ml/h syringe (±3 %).</p>
    <p style="margin: 0"><b style="font-weight: 600">MCI-0149</b>: occlusion alarm late and battery under 10 min — tagged “do not use”, quotation [no.] sent.
    <b style="font-weight: 600">MCI-0145</b>: pole clamp screw replaced. <b style="font-weight: 600">MCS-0392</b>: battery replaced, warranty from 12 Nov 2026.</p>
  </div>
  <div style="display: grid; grid-template-columns: 1fr 1fr; column-gap: 20px; align-items: end">
    <div style="display: flex; flex-direction: column; gap: 2px"><div style="height: 26px; border-bottom: 1px solid #161718"></div><span class="l">[Technician name] · Inspected by</span></div>
    <div style="display: flex; flex-direction: column; gap: 2px"><div style="height: 26px; border-bottom: 1px solid #161718"></div><span class="l">[Hospital engineer] · Received by</span></div>
  </div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Individual inspection reports hold the measured values</span><span>FM-SUM-24 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Inspection W", 1123, 794, FONT, CSS, ROOT + "; padding: 30px 38px 22px 38px; gap: 12px", body)


# ---------------------------------------------------------------- แผ่นป้ายสถานะ A4: 10 ดวง 90 × 50 มม.
LABEL_W, LABEL_H = 340, 189


def label(d):
    job, typ, model, sn, dept, errs, st = d
    c = COL[typ]
    if st == "fail":
        return f"""<div style="width: {LABEL_W}px; height: {LABEL_H}px; box-sizing: border-box; border: 3px solid #161718; padding: 10px 14px; display: flex; flex-direction: column; gap: 4px">
<div style="display: flex; justify-content: space-between"><span class="l" style="color: #161718">[Company] · {job}</span><span class="l">{dept}</span></div>
<span style="font-size: 26px; line-height: 30px; font-weight: 700; background: #161718; color: #ffffff; padding: 4px 8px; text-align: center; letter-spacing: .04em">DO NOT USE</span>
<span style="font-size: 13px; line-height: 17px">{model} · S/N {sn}</span>
<span style="font-size: 13px; line-height: 17px">Failed calibration 13 Nov 2026 · see report</span>
<span class="l" style="margin-top: auto">Remove only after repair and re-test · by ______</span></div>"""
    return f"""<div style="width: {LABEL_W}px; height: {LABEL_H}px; box-sizing: border-box; border: 1px solid #161718; padding: 10px 14px; display: flex; flex-direction: column; gap: 3px">
<div style="display: flex; justify-content: space-between; align-items: baseline"><span class="l" style="color: #161718">[Company] · Calibrated</span>
<b style="font-size: 14px; font-weight: 700; color: {c["ink"]}">{job}</b></div>
<div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #161718; border-bottom: 1px solid #161718; padding: 4px 0">
<div style="display: flex; flex-direction: column"><span style="font-size: 14px; line-height: 18px; font-weight: 600">{model}</span><span style="font-size: 13px; line-height: 17px">S/N {sn} · {dept}</span></div>
<span style="font-size: 24px; font-weight: 700; letter-spacing: .06em">PASS</span></div>
<div style="display: grid; grid-template-columns: 1fr 1fr; font-size: 13px; line-height: 17px">
<span class="l">Calibrated</span><span class="l">Next due</span><b style="font-weight: 600">13 Nov 2026</b><b style="font-weight: 600">Nov 2027</b></div>
<span style="font-size: 13px; line-height: 17px">Tested {" · ".join(str(r) for r in (INF_RATES if typ == "I" else SYR_RATES))} ml/h · limit ±{LIMIT[typ]:.0f} %</span>
<div style="margin-top: auto; display: flex; justify-content: space-between" class="l"><span>Cert. {CERT[job]}</span><span>by ______</span></div>
<div style="height: 6px; background: {c["fill"]}"></div></div>"""


def labels():
    picks = [d for d in FLEET if d[0] in ("MCI-0142", "MCI-0143", "MCI-0144", "MCI-0145", "MCI-0149",
                                          "MCI-0151", "MCS-0388", "MCS-0389", "MCS-0390", "MCS-0391")]
    cells = "".join(label(d) for d in picks)
    body = f"""
<div style="display: flex; justify-content: space-between; align-items: baseline" class="l"><span>Status labels · batch {BATCH} · {HOSP} · 10 × (90 × 50 mm) · print at 100 %, do not scale</span><span>sheet 1 / 2</span></div>
<div style="display: grid; grid-template-columns: repeat(2, {LABEL_W}px); grid-auto-rows: {LABEL_H}px; column-gap: 30px; row-gap: 18px; justify-content: center">{cells}</div>
<div class="l" style="text-align: center">Blue strip = infusion · pink strip = syringe · black label = not fit. Colour is a help only: type and status are printed in words.</div>
"""
    return dc("Labels W", 794, 1123, FONT, CSS, ROOT + "; padding: 26px 32px 20px 32px; gap: 14px", body)


def boards():
    return [
        dict(name="W-Calibration.dc.html", w=1123, h=794, title="W · Fleet calibration summary (A4 landscape)", html=calibration()),
        dict(name="W-Inspection.dc.html", w=1123, h=794, title="W · Fleet inspection matrix (A4 landscape)", html=inspection()),
        dict(name="W-QuickTest.dc.html", w=794, h=1123, title="W · Status label sheet (A4, 10 × 90 × 50 mm)", html=labels()),
    ]
