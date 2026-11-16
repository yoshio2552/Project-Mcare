"""แบบ U — Calculation sheet: ใบคำนวณแบบสมุดแล็บ แสดงทุกขั้นจากค่าดิบ → regression → Z (ISO 4787) → flow → ตัดสิน
ผู้ตรวจประเมินคำนวณตามได้ด้วยเครื่องคิดเลข · ตัวเลข/สูตรเป็น mono · ช่องหัวกระดาษแบบ calc pad · ตัวอย่าง Syringe
"""
import math

from common import (SYRINGE as D, SYR as K, SYR_QT as QT, INK, GREY, RULE, PAPER, BALANCE, f, err, series, mean,
                    Ax, T, L, R, PL, C, svg, fonts, dc)

HEADING = "แบบ U — Calculation sheet: ใบคำนวณแบบสมุดแล็บ ค่าดิบ → regression → Z (ISO 4787) → flow → ตัดสิน ตรวจทานด้วยมือได้ทุกขั้น"
NOTE_FILL = "orange"
NOTE = ("U: ผู้ตรวจประเมิน ISO/IEC 17025 ชอบแบบนี้ — เห็นสูตรและตัวเลขจริงทุกขั้น ตรวจซ้ำด้วยเครื่องคิดเลขได้\n"
        "ค่า Z, ความหนาแน่นน้ำ/อากาศ, baseline มีในโปรแกรมแล้ว (GravimetricCorrection)\n"
        "มีช่อง \"Checked by\" สำหรับการตรวจทานโดยอิสระ")

FONT = fonts("Sarabun:ital,wght@0,400;0,500;0,600;1,400", "JetBrains+Mono:wght@400;500;600")
ROOT = ("color: #161718; font-family: 'Sarabun', sans-serif; display: flex; flex-direction: column; "
        "font-variant-numeric: tabular-nums lining-nums")
CSS = """
.l{font-size:12px;line-height:16px;color:#5C5F62}
.m{font-family:'JetBrains Mono',monospace;font-size:12.5px}
.pad{display:grid;border:1.5px solid #161718}
.pad>div{padding:3px 8px;border-right:1px solid #161718;border-bottom:1px solid #161718;display:flex;flex-direction:column;min-width:0}
.pad b{font-size:13px;line-height:18px;font-weight:500}
.step{display:grid;grid-template-columns:54px minmax(0,1fr);column-gap:12px;border-top:1px solid #161718;padding-top:6px}
.step>.no{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:600}
.step h2{margin:0 0 4px 0;font-size:14px;line-height:19px;font-weight:600}
.eq{font-family:'JetBrains Mono',monospace;font-size:12.5px;line-height:20px;white-space:pre}
.res{font-family:'JetBrains Mono',monospace;font-weight:600}
table{border-collapse:collapse;font-size:12.5px;line-height:17px}
th{font-weight:500;color:#5C5F62;font-size:12px;text-align:right;padding:2px 8px;border-bottom:1px solid #161718;font-family:'Sarabun',sans-serif}
td{text-align:right;padding:2px 8px;border-bottom:1px solid #DCDCD8;font-family:'JetBrains Mono',monospace}
th:first-child,td:first-child{text-align:left;padding-left:0}
svg text{font-family:'JetBrains Mono',monospace}
.box{display:inline-block;width:12px;height:12px;border:1.5px solid #161718;vertical-align:-1px;margin-right:6px;text-align:center;font-size:11px;line-height:12px}
"""


# ---------------------------------------------------------------- การคำนวณจริงตาม ISO 4787
def rho_water(t):
    """ความหนาแน่นน้ำ (g/ml) สูตร Tanaka 2001"""
    a1, a2, a3, a4, a5 = -3.983035, 301.797, 522528.9, 69.34881, 999.974950
    return a5 * (1 - (t + a1) ** 2 * (t + a2) / (a3 * (t + a4))) / 1000


def rho_air(p_hpa, rh, t):
    """ความหนาแน่นอากาศ (g/ml) สูตรประมาณ CIPM"""
    return (0.34848 * p_hpa - 0.009 * rh * math.exp(0.061 * t)) / (273.15 + t) / 1000


RHO_B = 8.0          # ความหนาแน่นตุ้มน้ำหนักอ้างอิงของตราชั่ง g/ml
RW = rho_water(D["water"])
RA = rho_air(D["hpa"], D["rh"], D["water"])
Z = 1 / (RW - RA) * (1 - RA / RHO_B)
BASE = 0.006         # baseline จาก self-check (ระเหย/ลอย) g/h
R5 = D["rates"][1]
IFLOWS = series(R5["n"], R5["meas"], R5["meas"] * R5["sd2"] / 200, 707, ar=0.1)   # flow สุทธิรายช่วง ml/h
K_IDX = 6            # แสดงตัวอย่างช่วงที่ 7


def raw_slope(q):
    """flow สุทธิ ml/h -> slope ดิบ g/h"""
    return q / Z + BASE


def interval_signal(q, seed=909):
    """ค่าที่ตราชั่งอ่านทุก 1 s ใน 60 s (ปัดที่ 0.001 g เหมือน GF-300) + เส้น regression"""
    from common import Rng
    rng = Rng(seed)
    b = raw_slope(q) / 3600
    m0 = 21.3526 + K_IDX * 60 * b
    ts = list(range(0, 61))
    ms = [round(m0 + b * t + 0.0003 * rng.g(), 3) for t in ts]
    tb, mb = mean(ts), mean(ms)
    sxx = sum((t - tb) ** 2 for t in ts)
    slope = sum((t - tb) * (m - mb) for t, m in zip(ts, ms)) / sxx
    icpt = mb - slope * tb
    return ts, ms, slope, icpt


TS, MS, SLOPE, ICPT = interval_signal(IFLOWS[K_IDX])
# ให้ flow ช่วงที่ 7 ในตาราง = ค่าที่คำนวณจาก regression จริง (ค่าเฉลี่ยรวมคงเดิม — ชดเชยที่ช่วงถัดไป)
_q7 = (SLOPE * 3600 - BASE) * Z
IFLOWS[K_IDX + 1] -= _q7 - IFLOWS[K_IDX]
IFLOWS[K_IDX] = _q7


def pad(cells, cols):
    return (f'<div class="pad" style="grid-template-columns: {cols}">'
            + "".join(f'<div style="{st}"><span class="l">{k}</span><b>{v}</b></div>' for k, v, st in cells) + "</div>")


def header(title, sub, kind_no):
    return f"""
<div style="display: flex; justify-content: space-between; align-items: flex-end">
  <div style="display: flex; flex-direction: column"><span class="l">[Company Name] · Calibration Laboratory</span>
  <span style="font-size: 26px; line-height: 32px; font-weight: 600">{title}</span><span style="font-size: 13px; color: #3E4143">{sub}</span></div>
  <span class="m" style="font-size: 20px; font-weight: 600; color: {K["ink"]}">{D["job"]}</span>
</div>
{pad([("Customer", f"{D['site']} · {D['dept']}", ""), ("Item", f"{D['brand']} {D['model']} syringe", ""),
      ("Serial · asset", f"{D['serial']} · {D['asset']}", ""), (kind_no[0], kind_no[1], "border-right: 0"),
      ("Syringe", D["set_label"], "border-bottom: 0"), ("Reference", "GF-300 S/N 14654769", "border-bottom: 0"),
      ("Date", D["date"], "border-bottom: 0"), ("Sheet", "1 of 1", "border-right: 0; border-bottom: 0")],
     "1.3fr 1fr 1.1fr 0.9fr")}"""


def mass_chart(w=330):
    ax = Ax(62, w - 8, 10, 132, 0, 60, MS[0] - 0.004, MS[-1] + 0.004)
    out = [L(ax.x0, ax.y0, ax.x0, ax.y1, INK), L(ax.x0, ax.y1, ax.x1, ax.y1, INK)]
    for v in (MS[0], (MS[0] + MS[-1]) / 2, MS[-1]):
        out.append(T(ax.x0 - 6, ax.sy(v) + 4, f"{v:.3f}", anchor="end", size=12))
    for x, m in zip(TS, MS):
        out.append(C(ax.sx(x), ax.sy(m), 1.8, "#7A7D80"))
    out.append(L(ax.sx(0), ax.sy(ICPT), ax.sx(60), ax.sy(ICPT + SLOPE * 60), K["ink"], 1.5))
    for t in (0, 30, 60):
        out.append(T(ax.sx(t), ax.y1 + 16, f"{t}", anchor="middle"))
    out.append(T(ax.x0 + 6, ax.y0 + 6, "m, g", fill=INK))
    out.append(T(ax.x1 - 30, ax.y1 + 16, "t, s", anchor="end"))
    # residual mg
    res = [(m - (ICPT + SLOPE * t)) * 1000 for t, m in zip(TS, MS)]
    bx = Ax(62, w - 8, 184, 236, 0, 60, -1.0, 1.0)
    out += [L(bx.x0, bx.y0, bx.x0, bx.y1, INK), L(bx.x0, bx.sy(0), bx.x1, bx.sy(0), RULE)]
    for v in (-1, 0, 1):
        out.append(T(bx.x0 - 6, bx.sy(v) + 4, f(v, 1, True) if v else "0", anchor="end"))
    for x, v in zip(TS, res):
        out.append(L(bx.sx(x), bx.sy(0), bx.sx(x), bx.sy(v), INK, 1))
    out.append(T(bx.x0 + 6, bx.y0 - 4, "residual, mg (balance d = 1 mg)", fill=INK))
    return svg(w, 244, "Balance readings of interval 7 with regression line and residuals", out)


def interval_list():
    """Qᵢ ทั้ง 20 ช่วง เป็นตาราง 2 แถว"""
    rows = []
    for half in (0, 10):
        head = "".join(f"<th>Q{i + 1}</th>" for i in range(half, half + 10))
        vals = "".join(f"<td{' style=\"font-weight: 600\"' if i == K_IDX else ''}>{IFLOWS[i]:.3f}</td>" for i in range(half, half + 10))
        rows.append(f"<thead><tr>{head}</tr></thead><tbody><tr>{vals}</tr></tbody>")
    return f'<table style="width: 100%; margin-top: 6px">{"".join(rows)}</table>'


def calibration():
    q7 = IFLOWS[K_IDX]
    b7 = SLOPE * 3600
    excerpt = "".join(f"<tr><td>{TS[i]}</td><td>{MS[i]:.3f}</td></tr>" for i in range(0, 61, 10))
    summary = []
    for r in D["rates"]:
        bg = raw_slope(r["meas"])
        summary.append(f"""<tr><td>{r["set"]:.1f}</td><td>{r["n"]} × {r["win"]} s</td><td>{bg:.4f}</td><td>{BASE:.3f}</td><td>{Z:.5f}</td>
<td>{r["meas"]:.3f}</td><td>{f(err(r), 1, True)} %</td><td>{r["U"]:.1f} %</td><td>Pass</td></tr>""")
    body = f"""
{header("Calibration calculation sheet", "ใบคำนวณผลการสอบเทียบ · แนบท้ายใบรับรอง " + D["cert"], ("Certificate", D["cert"]))}
<div class="step"><span class="no">01</span><div><h2>Raw readings · 5 ml/h, interval 7 of {R5["n"]} ({R5["win"]} s)</h2>
<div style="display: grid; grid-template-columns: 120px 330px minmax(0, 1fr); column-gap: 14px; align-items: start">
<table><thead><tr><th>t, s</th><th>m, g</th></tr></thead><tbody>{excerpt}</tbody></table>
{mass_chart()}
<div class="eq">61 readings, 1 s

b = Σ(t−t̄)(m−m̄)
    / Σ(t−t̄)²
  = <span class="res">{SLOPE * 1e6:.2f} µg/s</span>
  = {b7:.4f} g/h

residuals within
the resolution
of 1 mg</div>
</div></div></div>
<div class="step"><span class="no">02</span><div><h2>Correction factor Z · ISO 4787:2021</h2>
<div class="eq">ρW = {RW:.6f} g/ml   water, Tanaka 2001, t = {D["water"]} °C
ρA = {RA:.6f} g/ml   air, CIPM approx., {D["hpa"]} hPa, {D["rh"]} %RH, {D["water"]} °C
ρB = {RHO_B:.1f} g/ml        reference weights of the balance
Z  = 1/(ρW − ρA) · (1 − ρA/ρB) = 1/{RW - RA:.6f} · {1 - RA / RHO_B:.6f} = <span class="res">{Z:.5f} ml/g</span></div></div></div>
<div class="step"><span class="no">03</span><div><h2>Flow of interval 7</h2>
<div class="eq">Q₇ = (b − baseline) · Z = ({b7:.4f} − {BASE:.3f}) g/h · {Z:.5f} ml/g = <span class="res">{q7:.3f} ml/h</span>
baseline = evaporation + drift from DeltaM self-check before the run</div></div></div>
<div class="step"><span class="no">04</span><div><h2>All intervals · 5 ml/h</h2>
<div class="eq">Q̄ = (1/{R5["n"]}) Σ Qᵢ = <span class="res">{mean(IFLOWS):.3f} ml/h</span>     E = (Q̄ − Qset)/Qset = ({mean(IFLOWS):.3f} − 5.000)/5.000 = <span class="res">{f(err(R5), 2, True)} %</span>
s(Qᵢ) = {R5["meas"] * R5["sd2"] / 200:.3f} ml/h → s/√n = {R5["meas"] * R5["sd2"] / 200 / math.sqrt(R5["n"]) / R5["meas"] * 100:.2f} %   (repeatability term of the budget)</div>
{interval_list()}</div></div>
<div class="step"><span class="no">05</span><div><h2>Summary and decision · limit ±{D["limit"]:.1f} %, simple acceptance (ILAC-G8)</h2>
<table style="width: 100%"><thead><tr><th>Set ml/h</th><th>Intervals</th><th>b̄ raw g/h</th><th>Baseline g/h</th><th>Z ml/g</th><th>Q̄ ml/h</th><th>E</th><th>U, k=2</th><th>Decision</th></tr></thead>
<tbody>{"".join(summary)}</tbody></table></div></div>
<div style="margin-top: auto; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1.5px solid #161718">
  <div style="padding: 4px 8px 6px 8px; border-right: 1px solid #161718; display: flex; flex-direction: column"><span class="l">Calculated by · DeltaM 0.3.0</span><div style="height: 30px"></div><span style="font-size: 13px">{D["operator"]}</span></div>
  <div style="padding: 4px 8px 6px 8px; border-right: 1px solid #161718; display: flex; flex-direction: column"><span class="l">Checked by (independent)</span><div style="height: 30px"></div><span style="font-size: 13px">[Checker name]</span></div>
  <div style="padding: 4px 8px 6px 8px; display: flex; flex-direction: column"><span class="l">Approved by</span><div style="height: 30px"></div><span style="font-size: 13px">{D["approver"]}</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Values computed from the stored raw file; SHA-256 [hash] · rounding only at the last step</span><span class="m" style="font-size: 12px">FM-CAL-21 Rev.00</span></div>
"""
    return dc("Calibration U", 794, 1123, FONT, CSS, ROOT + "; padding: 28px 40px 22px 40px; gap: 10px", body)


# ---------------------------------------------------------------- Inspection: แบบฟอร์มพิมพ์ค่าแล้ว
DM_INSP = 0.408       # มวลที่เพิ่มใน 300 s (g) อ่านละเอียด 0.001 g


def tick(ok):
    return f'<span class="box">{"✓" if ok else ""}</span>'


def field(label, value, w="1fr"):
    return (f'<div style="display: flex; flex-direction: column; min-width: 0"><span class="l">{label}</span>'
            f'<span class="m" style="border-bottom: 1px solid #161718; padding: 1px 2px; font-size: 13px">{value}</span></div>')


CHECKS = [("Housing and labels", 1), ("Pole clamp", 1), ("Power cord and plug", 1), ("Syringe clamp, plunger holder", 1),
          ("Battery operation ≥ 60 min", 1), ("Keypad and display", 1), ("Syringe size detection 10/20/50 ml", 1),
          ("Audible and visual alarms", 1)]


def inspection():
    q = round((DM_INSP * 12 - BASE) * Z, 2)     # ปัดก่อนคำนวณ E ให้ตรงกับที่พิมพ์ในสมการ
    e = (q - 5) / 5 * 100
    ck = "".join(f'<div style="display: flex; align-items: center; font-size: 13px; line-height: 22px">{tick(o)}{n}'
                 f'<span class="m" style="margin-left: auto">{"OK" if o else ""}</span></div>' for n, o in CHECKS)
    body = f"""
{header("Inspection work sheet", "ใบบันทึกการตรวจสภาพ · ค่าที่วัดจริงพิมพ์ลงช่อง", ("Report", D["insp"]))}
<div class="step"><span class="no">A</span><div><h2>Visual and functional checks</h2>
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 28px">{ck}
<div style="display: flex; align-items: center; font-size: 13px; line-height: 22px">{tick(0)}Nurse call<span class="m" style="margin-left: auto; color: #5C5F62">N/A</span></div>
<div style="display: flex; align-items: center; font-size: 13px; line-height: 22px">{tick(0)}Electrical safety IEC 62353<span class="m" style="margin-left: auto; color: #5C5F62">N/P</span></div>
</div></div></div>
<div class="step"><span class="no">B</span><div><h2>Alarm tests · measured</h2>
<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); column-gap: 14px; row-gap: 8px">
{field("Occlusion, 5 ml/h, level M · time", "2 min 40 s")}{field("criterion [mfr]", "≤ 5 min")}
{field("Near-empty · volume left", "3.0 ml")}{field("criterion [mfr]", "3 ± 1 ml")}
{field("End of infusion", "alarm")}{field("KVO rate shown", "0.1 ml/h")}
{field("Syringe size detection", "10 / 20 / 50 ml OK")}{field("Battery run time", "≥ 60 min")}
</div></div></div>
<div class="step"><span class="no">C</span><div><h2>Flow check · 5 ml/h · 300 s</h2>
<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); column-gap: 14px; row-gap: 8px; margin-bottom: 8px">
{field("m start, g", "21.347")}{field("m end, g", f"{21.347 + DM_INSP:.3f}")}{field("Δm, g", f"{DM_INSP:.3f}")}{field("Δt, s", "300")}
{field("water °C", D["water"])}{field("Z, ml/g", f"{Z:.5f}")}{field("baseline, g/h", f"{BASE:.3f}")}{field("limit", "±3.0 %")}
</div>
<div class="eq">Q = (Δm · 3600/Δt − baseline) · Z = ({DM_INSP:.3f} · 12 − {BASE:.3f}) · {Z:.5f} = <span class="res">{q:.2f} ml/h</span>
E = ({q:.2f} − 5.00)/5.00 = <span class="res">{f(e, 1, True)} %</span>          |E| ≤ 3.0 %  →  conforms</div>
<span class="l">Two-point check from the first and last reading. DeltaM also fits all 1 s readings: {D["rates"][1]["meas"]:.3f} ml/h, same decision.</span>
</div></div>
<div class="step"><span class="no">D</span><div><h2>Parts and remarks</h2>
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 14px; row-gap: 8px">
{field("Part replaced", "plunger clamp · warranty claim")}{field("Warranty counted from", "2 Mar 2026 · not restarted")}
{field("Remarks", "battery charged and run-tested")}{field("Next inspection", "May 2027")}
</div></div></div>
<div class="step"><span class="no">E</span><div><h2>Instruments used</h2>
<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 14px; row-gap: 8px">
{field("Balance · cert. due", "GF-300 · [due]")}{field("Thermometer · cert. due", "[ID] · [due]")}{field("Barometer / hygrometer", "[ID] · [due]")}
</div></div></div>
<div class="step"><span class="no">F</span><div><h2>Status</h2>
<div style="display: flex; gap: 28px; font-size: 14px; line-height: 22px; align-items: center">
<span>{tick(1)}<b style="font-weight: 600">Fit for use</b></span><span>{tick(0)}Fit with remarks</span><span>{tick(0)}Not fit · tag and remove</span></div></div></div>
<div style="margin-top: auto; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1.5px solid #161718">
  <div style="padding: 4px 8px 6px 8px; border-right: 1px solid #161718; display: flex; flex-direction: column"><span class="l">Inspected by</span><div style="height: 30px"></div><span style="font-size: 13px">[Technician name]</span></div>
  <div style="padding: 4px 8px 6px 8px; border-right: 1px solid #161718; display: flex; flex-direction: column"><span class="l">Checked by</span><div style="height: 30px"></div><span style="font-size: 13px">[Checker name]</span></div>
  <div style="padding: 4px 8px 6px 8px; display: flex; flex-direction: column"><span class="l">Received by (ward)</span><div style="height: 30px"></div><span style="font-size: 13px">[Ward representative]</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Balance {BALANCE} · water {D["water"]} °C · {D["rh"]} %RH · {D["hpa"]} hPa</span><span class="m" style="font-size: 12px">FM-INS-21 Rev.00</span></div>
"""
    return dc("Inspection U", 794, 1123, FONT, CSS, ROOT + "; padding: 32px 40px 24px 40px; gap: 12px", body)


# ---------------------------------------------------------------- Quick Test: การ์ด A6 แบบฟอร์ม
DM_QT = 0.410


def quicktest():
    q = round((DM_QT * 12 - BASE) * Z, 2)
    e = (q - QT["set"]) / QT["set"] * 100
    body = f"""
<div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1.5px solid #161718; padding-bottom: 4px">
  <span style="font-size: 18px; font-weight: 600">Quick test sheet</span><span class="m" style="font-weight: 600; color: {K["ink"]}">{QT["job"]}</span></div>
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 12px; row-gap: 7px">
{field("Item", f"{D['model']} S/N {QT['serial']}")}{field("Ward", f"NICU · [hospital]")}
{field("Date", "13 Nov 2026 15:05")}{field("Sheet", QT["no"])}
{field("Set rate", "5.0 ml/h")}{field("Δt", "300 s")}
{field("m start, g", "18.902")}{field("m end, g", f"{18.902 + DM_QT:.3f}")}
{field("Δm, g", f"{DM_QT:.3f}")}{field("Z · baseline", f"{Z:.5f} · {BASE:.3f}")}
</div>
<div class="eq" style="font-size: 12px; line-height: 18px; border: 1px solid #161718; padding: 6px 8px">Q = (Δm·12 − {BASE:.3f})·Z
  = <span class="res">{q:.2f} ml/h</span>
E = <span class="res">{f(e, 1, True)} %</span>   limit ±3.0 %</div>
<div style="display: flex; gap: 22px; font-size: 14px; line-height: 22px"><span>{tick(1)}<b style="font-weight: 600">PASS</b></span><span>{tick(0)}FAIL → full calibration</span></div>
<div style="display: flex; flex-direction: column"><span class="l">Remarks</span><div style="height: 24px; border-bottom: 1px solid #8A8D90"></div><div style="height: 24px; border-bottom: 1px solid #8A8D90"></div></div>
<div style="margin-top: auto; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 12px">
  <div style="display: flex; flex-direction: column"><div style="height: 26px; border-bottom: 1px solid #161718"></div><span class="l">Tested by</span></div>
  <div style="display: flex; flex-direction: column"><div style="height: 26px; border-bottom: 1px solid #161718"></div><span class="l">Checked by</span></div>
</div>
<span class="l">Screening only · balance GF-300 S/N 14654769 · FM-QT-21</span>
"""
    return dc("Quick Test U", 397, 559, FONT, CSS, ROOT + "; padding: 20px 22px 16px 22px; gap: 10px", body)


def boards():
    return [
        dict(name="U-Calibration.dc.html", w=794, h=1123, title="U · Calibration calculation sheet", html=calibration()),
        dict(name="U-Inspection.dc.html", w=794, h=1123, title="U · Inspection work sheet", html=inspection()),
        dict(name="U-QuickTest.dc.html", w=397, h=559, title="U · Quick test sheet (A6)", html=quicktest()),
    ]


if __name__ == "__main__":
    print("rhoW", RW, "rhoA", RA, "Z", Z, "q7", IFLOWS[K_IDX], "slope g/h", SLOPE * 3600, raw_slope(IFLOWS[K_IDX]))
    print("insp q", (DM_INSP * 12 - BASE) * Z, "qt q", (DM_QT * 12 - BASE) * Z)
