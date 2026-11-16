"""แบบ R — Uncertainty & decision rule: งบความไม่แน่นอนพร้อมแท่ง Pareto + แผนภาพโซนตัดสิน (ILAC-G8, GUM)
แนวใบรับรองสถาบันมาตรวิทยา: หัวเรื่อง serif, ป้ายตัวพิมพ์เล็ก, ตารางเส้นบาง — ตัวอย่างเป็น Syringe (ชมพู)
"""
import math

from common import (series, SYRINGE as D, SYR as K, SYR_QT as QT, INK, GREY, RULE, BALANCE, f, err, Ax, T, L, R, C, svg,
                    fonts, dc)

HEADING = "แบบ R — Uncertainty & decision rule: งบความไม่แน่นอน + Pareto, โซนตัดสินแบบ guard band, ความน่าจะเป็นที่ผ่านจริง (ILAC-G8, GUM)"
NOTE_FILL = "pink"
NOTE = ("R: เทียบกฎตัดสิน 2 แบบในใบเดียว — simple acceptance (ผ่าน) กับ guarded (w = U)\n"
        "1 ml/h: error −2.2 % ± 1.2 % คร่อมเกณฑ์ ±3 % → ความน่าจะเป็นที่ผ่านจริง 91 %\n"
        "ต้องเพิ่มในโปรแกรม: งบความไม่แน่นอนราย rate + เลือกกฎตัดสินตามที่ตกลงกับลูกค้า")

FONT = fonts("Source+Serif+4:opsz,wght@8..60,400;8..60,600", "Source+Sans+3:wght@400;500;600",
             "Noto+Serif+Thai:wght@400;600", "Noto+Sans+Thai:wght@400;500")
ROOT = ("color: #161718; font-family: 'Source Sans 3', 'Noto Sans Thai', sans-serif; display: flex; "
        "flex-direction: column; font-variant-numeric: tabular-nums lining-nums")
CSS = """
.l{font-size:12px;line-height:16px;color:#5C5F62}
.sc{font-size:12px;line-height:16px;letter-spacing:.08em;text-transform:uppercase;color:#5C5F62}
.serif{font-family:'Source Serif 4','Noto Serif Thai',serif}
h2{margin:0;font-family:'Source Serif 4','Noto Serif Thai',serif;font-size:16px;line-height:22px;font-weight:600}
table{border-collapse:collapse;width:100%;font-size:13px;line-height:18px}
th{font-weight:500;color:#5C5F62;font-size:12px;line-height:15px;text-align:right;padding:4px 6px;border-top:1px solid #161718;border-bottom:1px solid #161718;vertical-align:bottom}
td{text-align:right;padding:3px 6px;border-bottom:1px solid #DCDCD8}
tr:last-child td{border-bottom:1px solid #161718}
th:first-child,td:first-child{text-align:left}
.dl{display:grid;grid-template-columns:130px minmax(0,1fr) 110px minmax(0,1fr);row-gap:4px;column-gap:12px;font-size:13px;line-height:18px}
.sig{display:flex;flex-direction:column;gap:2px}
.sig div{height:30px;border-bottom:1px solid #161718}
svg text{font-family:'Source Sans 3','Noto Sans Thai',sans-serif}
"""


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def pct(p):
    """แสดงความน่าจะเป็น — ไม่ปัดขึ้นเป็น 100 %"""
    return "> 99.9 %" if p > 0.9995 else f"{p * 100:.1f} %"


def p_conform(e, U, lim):
    """ความน่าจะเป็นที่ค่าจริงอยู่ในเกณฑ์ (การแจกแจงปกติ u = U/2)"""
    u = U / 2
    return phi((lim - e) / u) - phi((-lim - e) / u)


# งบความไม่แน่นอนของ 5 ml/h (% ของ flow) — ค่าสมมติ รวมแล้วได้ U = 0.7 %
BUDGET = [
    ("Repeatability of interval flow, s/√n", "A", "normal", 0.25, 19),
    ("Evaporation from the vessel", "B", "rectangular", 0.18, None),
    ("Balance calibration (certificate, k = 2)", "B", "normal", 0.10, None),
    ("Syringe and drive compliance", "B", "rectangular", 0.10, None),
    ("Balance resolution and linearity", "B", "rectangular", 0.08, None),
    ("Sample timing", "B", "rectangular", 0.02, None),
    ("Water density, ±0.5 °C", "B", "rectangular", 0.01, None),
    ("Air buoyancy", "B", "rectangular", 0.01, None),
]
UC = math.sqrt(sum(b[3] ** 2 for b in BUDGET))
NU_EFF = UC ** 4 / sum(b[3] ** 4 / b[4] for b in BUDGET if b[4])


def header(title, thai, cells):
    meta = "".join(f'<div style="display: flex; justify-content: space-between; gap: 16px"><span class="l">{k}</span>'
                   f'<b style="font-size: 13px; font-weight: 600{"; color: " + K["ink"] if k == "Job No." else ""}">{v}</b></div>'
                   for k, v in cells)
    return f"""
<div style="border-top: 3px solid #161718; border-bottom: 1px solid #161718; height: 4px"></div>
<header style="display: flex; justify-content: space-between; align-items: flex-end; gap: 24px">
  <div style="display: flex; flex-direction: column; gap: 2px">
    <span class="sc">[Company Name] · Calibration Laboratory</span>
    <span class="serif" style="font-size: 30px; line-height: 38px; font-weight: 600">{title}</span>
    <span class="serif" style="font-size: 14px; line-height: 20px; color: #3E4143">{thai}</span>
  </div>
  <div style="width: 240px; flex: none; display: flex; flex-direction: column; gap: 3px">{meta}</div>
</header>"""


def item(extra=("Syringe", D["set_label"])):
    return f"""
<div class="dl">
  <span class="sc">Instrument</span><span>{D["brand"]} {D["model"]} syringe pump</span>
  <span class="sc">Customer</span><span>{D["site"]} · {D["dept"]}</span>
  <span class="sc">Serial · asset</span><span>{D["serial"]} · {D["asset"]}</span>
  <span class="sc">{extra[0]}</span><span>{extra[1]}</span>
  <span class="sc">Conditions</span><span>water {D["water"]} °C · {D["rh"]} %RH · {D["hpa"]} hPa</span>
  <span class="sc">Reference</span><span>balance {BALANCE}</span>
</div>"""


def hatch(pid):
    # ลายเส้นทแยง = โซนไม่ผ่าน (อ่านได้เมื่อพิมพ์ขาวดำ)
    return (f'<defs><pattern id="{pid}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<line x1="0" y1="0" x2="0" y2="6" stroke="#8A8D90" stroke-width="1"></line></pattern></defs>')


def zone_track(ax, y, h, lim, w_guard, pid):
    """แถบโซนตัดสินหนึ่งแถว: ไม่ผ่าน (ลายเส้น) | guard band (ชมพูอ่อน) | ยอมรับ (ขาว)"""
    out = [R(ax.sx(ax.vx0), y, ax.sx(-lim) - ax.sx(ax.vx0), h, f"url(#{pid})"),
           R(ax.sx(lim), y, ax.sx(ax.vx1) - ax.sx(lim), h, f"url(#{pid})")]
    if w_guard:
        out += [R(ax.sx(-lim), y, ax.sx(-lim + w_guard) - ax.sx(-lim), h, K["tint"]),
                R(ax.sx(lim - w_guard), y, ax.sx(lim) - ax.sx(lim - w_guard), h, K["tint"])]
    out.append(R(ax.sx(ax.vx0), y, ax.sx(ax.vx1) - ax.sx(ax.vx0), h, "none", INK))
    for v in (-lim, lim):
        out.append(L(ax.sx(v), y - 4, ax.sx(v), y + h + 4, INK, 1.5))
    return out


def zone_figure(w=706):
    ax = Ax(150, w - 150, 0, 0, -5, 5, 0, 1)
    out = [hatch("hR")]
    y = 30
    for v in range(-5, 6):
        out.append(T(ax.sx(v), 18, f(v, 0, True) if v else "0", anchor="middle"))
    out.append(T(ax.sx(5) + 12, 18, "error %", fill=GREY))
    for r in D["rates"]:
        e = err(r)
        out += zone_track(ax, y, 26, D["limit"], r["U"], "hR")
        out.append(L(ax.sx(0), y, ax.sx(0), y + 26, GREY, 1, "2 2"))
        out.append(L(ax.sx(e - r["U"]), y + 13, ax.sx(e + r["U"]), y + 13, INK, 2.5))
        for v in (e - r["U"], e + r["U"]):
            out.append(L(ax.sx(v), y + 6, ax.sx(v), y + 20, INK, 2))
        out.append(C(ax.sx(e), y + 13, 5, "#ffffff", INK, 2))
        out.append(T(0, y + 13, f"{r['set']:g} ml/h", fill=INK, weight=600, size=13))
        out.append(T(0, y + 29, f"{f(e, 1, True)} ± {r['U']:.1f} %", fill=GREY))
        guarded = abs(e) <= D["limit"] - r["U"]
        out.append(T(w, y + 13, "Pass" if guarded else "Not proven", anchor="end", fill=INK, weight=600, size=13))
        out.append(T(w, y + 29, "P " + ("" if pct(p_conform(e, r['U'], D['limit'])).startswith(">") else "= ") + pct(p_conform(e, r['U'], D['limit'])), anchor="end", fill=GREY))
        y += 40
    # คำอธิบายสัญลักษณ์
    ly = y + 6
    out += [R(150, ly, 22, 14, "url(#hR)", INK), T(178, ly + 12, "reject: outside ±3 %"),
            R(330, ly, 22, 14, K["tint"], INK), T(358, ly + 12, "guard band w = U"),
            L(500, ly + 7, 530, ly + 7, INK, 2.5), C(515, ly + 7, 5, "#ffffff", INK, 2), T(538, ly + 12, "E ± U (k = 2)")]
    return svg(w, ly + 22, "Decision zones for 1, 5 and 25 ml/h with guard band equal to U", out)


def results():
    rows = []
    for r in D["rates"]:
        e = err(r)
        guarded = abs(e) <= D["limit"] - r["U"]
        rows.append(f"""<tr><td>{r["set"]:.1f}</td><td>{r["meas"]:.3f}</td><td>{f(e, 1, True)} %</td><td>{r["U"]:.1f} %</td>
<td>{f(e - r["U"], 1, True)} … {f(e + r["U"], 1, True)}</td><td>{pct(p_conform(e, r["U"], D["limit"]))}</td>
<td><b style="font-weight: 600">Pass</b></td><td>{"Pass" if guarded else "Not proven"}</td></tr>""")
    return f"""<table><thead><tr><th>Set<br>ml/h</th><th>Measured<br>ml/h</th><th>Error<br>E</th><th>U<br>k = 2</th>
<th>Interval<br>E − U … E + U</th><th>Probability<br>of conformance</th><th>Simple<br>acceptance</th><th>Guarded<br>w = U</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table>"""


def budget(scale=1.0):
    total = sum(b[3] ** 2 for b in BUDGET)
    cum, rows = 0.0, []
    for name, typ, dist, u, nu in BUDGET:
        share = u ** 2 / total * 100
        cum += share
        bar = (f'<svg width="150" height="12" viewBox="0 0 150 12" aria-hidden="true" style="display: block">'
               f'{R(0, 1, 150, 10, "#ffffff", RULE)}{R(0, 1, 150 * share / 100, 10, K["fill"])}'
               f'{L(150 * cum / 100, 0, 150 * cum / 100, 12, INK, 1.5)}</svg>')
        rows.append(f"""<tr><td>{name}</td><td style="text-align: center">{typ}</td><td style="text-align: left">{dist}</td>
<td>{u:.2f}</td><td>{nu if nu else "∞"}</td><td>{share:.1f}</td><td>{bar}</td></tr>""")
    return f"""<table><thead><tr><th>Source of uncertainty x<sub>i</sub></th><th style="text-align: center">Type</th>
<th style="text-align: left">Distribution</th><th>u(x<sub>i</sub>) %</th><th>ν<sub>i</sub></th><th>Share of u<sub>c</sub>² %</th>
<th style="text-align: left">Share · <span style="font-weight: 600">|</span> cumulative</th></tr></thead>
<tbody>{"".join(rows)}
<tr><td colspan="3"><b style="font-weight: 600">Combined standard uncertainty u<sub>c</sub></b> · ν<sub>eff</sub> = {NU_EFF:.0f} → k = 2.0</td>
<td><b style="font-weight: 600">{UC:.2f}</b></td><td></td><td colspan="2" style="text-align: left"><b style="font-weight: 600">U = k · u<sub>c</sub> = {2 * UC:.1f} %</b></td></tr>
</tbody></table>"""


def footer(form, what="certificate"):
    return f"""<div style="display: flex; justify-content: space-between; border-top: 1px solid #161718; padding-top: 6px" class="l">
<span>This {what} shall not be reproduced except in full · results relate only to the item {"calibrated" if what == "certificate" else "inspected"}</span><span>{form} · DeltaM 0.3.0</span></div>"""


def calibration():
    body = f"""
{header("Certificate of Calibration", "ใบรับรองผลการสอบเทียบ · ความไม่แน่นอนของการวัดและกฎการตัดสิน",
        [("Certificate No.", D["cert"]), ("Job No.", D["job"]), ("Date of calibration", D["date"]), ("Page", "1 of 1")])}
{item()}
<section style="display: flex; flex-direction: column; gap: 6px">
  <div style="display: flex; justify-content: space-between; align-items: baseline"><h2>1. Results</h2><span class="l">limit ±{D["limit"]:.1f} % of set · time-interval capture · {D["rates"][1]["n"]} × {D["rates"][1]["win"]} s at 5 ml/h</span></div>
  {results()}
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div style="display: flex; justify-content: space-between; align-items: baseline"><h2>2. Decision zones</h2><span class="l">ILAC-G8:09/2019 · P = probability that the true error lies within the limit</span></div>
  {zone_figure()}
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div style="display: flex; justify-content: space-between; align-items: baseline"><h2>3. Uncertainty budget · 5 ml/h</h2><span class="l">JCGM 100:2008 (GUM) · all c<sub>i</sub> = 1, values in % of flow</span></div>
  {budget()}
</section>
<section style="display: grid; grid-template-columns: 130px minmax(0, 1fr); column-gap: 12px; font-size: 13px; line-height: 19px">
  <span class="sc" style="padding-top: 2px">Statement</span>
  <p style="margin: 0">Decision rule agreed with the customer: <b style="font-weight: 600">simple acceptance</b> (ILAC-G8 §4.2.1) — conforms at all
  rates. At 1 ml/h E ± U crosses −3 %, so a guarded rule (w = U) would not prove conformity. Method [WI-CAL-02], IEC 60601-2-24, ISO 4787;
  traceable to SI via balance certificate [—].</p>
</section>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 160px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["operator"]}</b><span class="l">Calibrated by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["approver"]}</b><span class="l">Authorised signatory</span></div>
  <div style="border: 1px solid #161718; outline: 1px solid #161718; outline-offset: 2px; padding: 6px; text-align: center; display: flex; flex-direction: column">
    <span class="sc">Conformity</span><span class="serif" style="font-size: 22px; line-height: 28px; font-weight: 600">CONFORMS</span><span class="l">simple acceptance</span></div>
</div>
{footer("FM-CAL-18 Rev.00")}
"""
    return dc("Calibration R", 794, 1123, FONT, CSS, ROOT + "; padding: 30px 46px 24px 46px; gap: 13px", body)


# ---------------------------------------------------------------- Inspection
INSP_U = 1.1        # 5 นาที n = 5 → repeatability ใหญ่ขึ้น U จึงกว้างกว่าใบ Calibration
CHECKS_L = [("Housing and labels", "OK"), ("Pole clamp", "OK"), ("Power cord and plug", "OK"),
            ("Syringe clamp, plunger holder", "OK"), ("Battery operation, ≥ 60 min", "OK"), ("Keypad and display", "OK")]
CHECKS_R = [("Syringe size detection 10 / 20 / 50 ml", "OK"), ("Audible and visual alarms", "OK"),
            ("Nurse call", "N/A"), ("Electrical safety IEC 62353", "N/P")]
ALARMS = [("Occlusion alarm at 5 ml/h, level M", "time to alarm", "2 min 40 s", "≤ 5 min [mfr]"),
          ("Near-empty alarm, 50 ml syringe", "remaining volume", "3.0 ml", "3 ± 1 ml [mfr]"),
          ("End-of-infusion alarm", "plunger at stop", "alarm", "alarm"),
          ("KVO after end of infusion", "rate shown", "0.1 ml/h", "0.1 ml/h")]


def insp_zone(w=706):
    e = err(D["rates"][1])
    ax = Ax(14, w - 14, 0, 0, -5, 5, 0, 1)
    out = [hatch("hRi")]
    out += zone_track(ax, 26, 34, D["limit"], INSP_U, "hRi")
    out.append(L(ax.sx(0), 26, ax.sx(0), 60, GREY, 1, "2 2"))
    out.append(L(ax.sx(e - INSP_U), 43, ax.sx(e + INSP_U), 43, INK, 2.5))
    for v in (e - INSP_U, e + INSP_U):
        out.append(L(ax.sx(v), 35, ax.sx(v), 51, INK, 2))
    out.append(C(ax.sx(e), 43, 5.5, "#ffffff", INK, 2))
    for v in range(-5, 6):
        out.append(T(ax.sx(v), 16, f(v, 0, True) if v else "0", anchor="middle"))
    out.append(T(ax.sx(e), 80, f"E = {f(e, 1, True)} %, U = {INSP_U} %", anchor="middle", fill=INK, weight=600))
    out.append(T(ax.sx(-3) - 6, 80, "limit −3 %", anchor="end"))
    out.append(T(ax.sx(3) + 6, 80, "limit +3 %"))
    return svg(w, 88, "Flow check at 5 ml/h inside guarded acceptance zone", out)


INSP_FLOWS = series(5, D["rates"][1]["meas"], D["rates"][1]["meas"] * 0.011, 611)


def interval_table():
    head = "".join(f"<th>{i}</th>" for i in range(1, 6))
    fl = "".join(f"<td>{v:.3f}</td>" for v in INSP_FLOWS)
    er = "".join(f"<td>{f((v - 5) / 5 * 100, 1, True)} %</td>" for v in INSP_FLOWS)
    m = sum(INSP_FLOWS) / 5
    return f"""<table><thead><tr><th>Interval</th>{head}<th>Mean</th></tr></thead><tbody>
<tr><td>Flow ml/h</td>{fl}<td><b style="font-weight: 600">{m:.3f}</b></td></tr>
<tr><td>Error</td>{er}<td><b style="font-weight: 600">{f((m - 5) / 5 * 100, 1, True)} %</b></td></tr></tbody></table>"""


def inspection():
    e = err(D["rates"][1])
    pc_s = pct(p_conform(e, INSP_U, D["limit"]))
    ck = lambda rows: "".join(f'<tr><td>{a}</td><td style="{"" if b == "OK" else "color: #5C5F62"}"><b style="font-weight: 600">{b}</b></td></tr>' for a, b in rows)
    al = "".join(f"<tr><td>{a}</td><td style=\"text-align: left\">{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in ALARMS)
    body = f"""
{header("Inspection Report", "รายงานการตรวจสภาพเครื่อง · ผลวัด flow พร้อมความไม่แน่นอน",
        [("Report No.", D["insp"]), ("Job No.", D["job"]), ("Date of inspection", D["date"]), ("Page", "1 of 1")])}
{item(("Next due", "May 2027 · 6 months"))}
<section style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 28px">
  <div style="display: flex; flex-direction: column; gap: 6px"><h2>1. Visual and functional</h2><table><tbody>{ck(CHECKS_L)}</tbody></table></div>
  <div style="display: flex; flex-direction: column; gap: 6px"><h2>2. Detection and safety</h2><table><tbody>{ck(CHECKS_R)}</tbody></table>
  <span class="l">N/A not applicable · N/P not performed (analyser not on site)</span></div>
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <h2>3. Alarm tests with measured values</h2>
  <table><thead><tr><th>Test</th><th style="text-align: left">Quantity</th><th>Found</th><th>Criterion</th></tr></thead><tbody>{al}</tbody></table>
</section>
<section style="display: flex; flex-direction: column; gap: 8px">
  <div style="display: flex; justify-content: space-between; align-items: baseline"><h2>4. Flow check · 5 ml/h · 5 min</h2><span class="l">gravimetric · {D["rates"][1]["meas"]:.3f} ml/h measured</span></div>
  {insp_zone()}
  <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 18px; font-size: 13px; line-height: 18px">
    <div style="display: flex; flex-direction: column"><span class="sc">Probability of conformance</span><span class="serif" style="font-size: 22px; line-height: 28px; font-weight: 600">{pc_s}</span></div>
    <div style="display: flex; flex-direction: column"><span class="sc">Test uncertainty ratio</span><span class="serif" style="font-size: 22px; line-height: 28px; font-weight: 600">{D["limit"] / INSP_U:.1f} : 1</span><span class="l">limit ÷ U · below 4 : 1 a guard band is advised</span></div>
    <div style="display: flex; flex-direction: column"><span class="sc">Guarded decision</span><span class="serif" style="font-size: 22px; line-height: 28px; font-weight: 600">Pass</span><span class="l">|E| = {abs(e):.1f} % ≤ 3 − U = {D["limit"] - INSP_U:.1f} %</span></div>
  </div>
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <h2>5. Interval record · 5 × 60 s</h2>
  {interval_table()}
</section>
<section style="display: grid; grid-template-columns: 130px minmax(0, 1fr); column-gap: 12px; font-size: 13px; line-height: 19px">
  <span class="sc" style="padding-top: 2px">Remarks</span>
  <p style="margin: 0">Plunger clamp replaced under warranty claim (period counted from 2 Mar 2026, not restarted). Battery pack charged and
  run-tested. Guarded rule applied to the flow check because the test uncertainty ratio is below 4 : 1.</p>
</section>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 160px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Technician name]</b><span class="l">Inspected by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Ward representative]</b><span class="l">Received by</span></div>
  <div style="border: 1px solid #161718; outline: 1px solid #161718; outline-offset: 2px; padding: 6px; text-align: center; display: flex; flex-direction: column">
    <span class="sc">Status</span><span class="serif" style="font-size: 20px; line-height: 28px; font-weight: 600">FIT FOR USE</span></div>
</div>
{footer("FM-INS-18 Rev.00", "report")}
"""
    return dc("Inspection R", 794, 1123, FONT, CSS, ROOT + "; padding: 34px 46px 26px 46px; gap: 16px", body)


# ---------------------------------------------------------------- Quick Test: ป้าย 90 × 60 มม.
def quicktest():
    e = (QT["meas"] - QT["set"]) / QT["set"] * 100
    pc_s = pct(p_conform(e, INSP_U, D["limit"]))
    w = 304
    ax = Ax(0, w, 0, 0, -5, 5, 0, 1)
    out = [hatch("hRq")] + zone_track(ax, 4, 16, D["limit"], INSP_U, "hRq")
    out.append(L(ax.sx(e - INSP_U), 12, ax.sx(e + INSP_U), 12, INK, 2.5))
    out.append(C(ax.sx(e), 12, 4, "#ffffff", INK, 2))
    out.append(T(ax.sx(-3), 36, "−3 %", anchor="middle"))
    out.append(T(ax.sx(3), 36, "+3 %", anchor="middle"))
    bar = svg(w, 40, f"Error {f(e, 1, True)} % with U inside limit", out)
    body = f"""
<div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #161718; padding-bottom: 3px">
  <span class="sc" style="color: #161718">Quick test · [Company]</span><b style="font-size: 13px; font-weight: 600; color: {K["ink"]}">{QT["job"]}</b></div>
<div style="display: flex; justify-content: space-between; align-items: center">
  <div style="display: flex; flex-direction: column"><span style="font-size: 13px; line-height: 17px; font-weight: 600">{D["model"]} · S/N {QT["serial"]}</span>
  <span class="l">{D["site"]} {QT["dept"]}</span></div>
  <span class="serif" style="font-size: 24px; line-height: 28px; font-weight: 600; border: 1px solid #161718; outline: 1px solid #161718; outline-offset: 2px; padding: 0 8px">PASS</span>
</div>
<span style="font-size: 13px; line-height: 17px">5 ml/h · E = <b style="font-weight: 600">{f(e, 1, True)} %</b> ± {INSP_U} % · P = {pc_s}</span>
{bar}
<span class="l">5 × 60 s · guarded rule w = U · limit ±3 %</span>
<div style="margin-top: auto; display: flex; justify-content: space-between" class="l"><span>13 Nov 2026 · due May 2027</span><span>by ______</span></div>
"""
    return dc("Quick Test R", 340, 227, FONT, CSS, ROOT + "; padding: 12px 18px 10px 18px; gap: 5px; border: 1px solid #161718", body)


def boards():
    return [
        dict(name="R-Calibration.dc.html", w=794, h=1123, title="R · Calibration uncertainty & decision rule", html=calibration()),
        dict(name="R-Inspection.dc.html", w=794, h=1123, title="R · Inspection with guarded decision", html=inspection()),
        dict(name="R-QuickTest.dc.html", w=340, h=227, title="R · Quick Test label 90 × 60 mm", html=quicktest()),
    ]


if __name__ == "__main__":
    print("uc", UC, "nu_eff", NU_EFF)
    for r in D["rates"]:
        print(r["set"], err(r), p_conform(err(r), r["U"], D["limit"]))
