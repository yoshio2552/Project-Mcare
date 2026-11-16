"""แบบ T — Small multiples (แนว Tufte) บน A4 แนวนอน: กราฟเล็กหลายช่องสเกลเดียวกัน เทียบทุก rate ได้ทันที
แถวบน = error รายรอบ + ค่าเฉลี่ยสะสม, แถวล่าง = ค่าเฉลี่ยสะสมลู่เข้าหาผล ± U · แกนแบบ range-frame ตัวหนังสือ serif
"""
from common import (INFUSION as D, INF as K, INF_INSP as II, INF_QT as QT, INK, GREY, RULE, BALANCE,
                    f, err, cycle_flows, series, mean, Ax, T, L, R, PL, PG, C, svg, fonts, dc)

HEADING = "แบบ T — Small multiples (แนว Tufte) A4 แนวนอน: กราฟเล็กสเกลเดียวกันทุก rate — error รายรอบ และค่าเฉลี่ยสะสมที่ลู่เข้าหาผล"
NOTE_FILL = "purple"
NOTE = ("T: วางกราฟเล็กหลายช่องด้วยสเกลเดียวกัน เห็นทันทีว่า 200 ml/h รายรอบแกว่งมากกว่า แต่ค่าเฉลี่ยยังนิ่ง\n"
        "แถวล่างตอบคำถามผู้ตรวจประเมินว่า \"วัดนานพอไหม\" — เส้นเข้าแถบ ±U ก่อนหมดเวลา\n"
        "ใช้ข้อมูลรายรอบที่มีอยู่แล้วทั้งหมด")

FONT = fonts("Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400", "Noto+Serif+Thai:wght@400;600")
ROOT = ("color: #161718; font-family: 'Newsreader', 'Noto Serif Thai', serif; display: flex; "
        "font-variant-numeric: tabular-nums lining-nums")
CSS = """
.l{font-size:12px;line-height:16px;color:#5C5F62}
.it{font-style:italic}
h2{margin:0;font-size:15px;line-height:20px;font-weight:600}
.kv{display:grid;grid-template-columns:96px minmax(0,1fr);row-gap:2px;column-gap:10px;font-size:13px;line-height:18px}
.kv span:nth-child(odd){color:#5C5F62;font-size:12px}
table{border-collapse:collapse;width:100%;font-size:13px;line-height:18px}
th{font-weight:400;font-style:italic;color:#5C5F62;font-size:12px;text-align:right;padding:0 8px 3px 8px;border-bottom:1px solid #161718}
td{text-align:right;padding:3px 8px}
th:first-child,td:first-child{text-align:left;padding-left:0}
tbody tr:last-child td{border-bottom:1px solid #161718}
p{margin:0}
.sig{display:flex;flex-direction:column;gap:1px}
.sig div{height:26px;border-bottom:1px solid #161718}
svg text{font-family:'Newsreader','Noto Serif Thai',serif}
"""

FLOWS = [cycle_flows(r, s) for r, s in zip(D["rates"], (101, 202, 304))]


def errs_of(flows, set_rate):
    return [(q - set_rate) / set_rate * 100 for q in flows]


def running(e):
    out, s = [], 0.0
    for i, v in enumerate(e, 1):
        s += v
        out.append(s / i)
    return out


def range_frame_y(ax, ticks, fmt):
    """แกน y แบบ range-frame: เส้นแกนยาวเท่าช่วงข้อมูลที่แสดง"""
    out = [L(ax.x0 - 6, ax.sy(ticks[0]), ax.x0 - 6, ax.sy(ticks[-1]), INK)]
    for v in ticks:
        out.append(T(ax.x0 - 10, ax.sy(v) + 4, fmt(v), anchor="end"))
    return out


def grid(rates, flows, w, U_list, tmax_min=15.5, ylim=13, yconv=3.2, row_h=(150, 112), labels=True,
         yticks=(-10, -5, 0, 5, 10), cticks=(-3, 0, 3), xticks=(0, 5, 10, 15)):
    """ตาราง small multiples: คอลัมน์ = rate, แถว 1 = error รายรอบ, แถว 2 = ค่าเฉลี่ยสะสม"""
    ncol = len(rates)
    left, gap = 46, 22
    pw = (w - left - gap * (ncol - 1)) / ncol
    y1t, y1b = 26, 26 + row_h[0]
    y2t = y1b + 40
    y2b = y2t + row_h[1]
    out = []
    for c, (r, fl, U) in enumerate(zip(rates, flows, U_list)):
        x0 = left + c * (pw + gap)
        e = errs_of(fl, r["set"])
        run = running(e)
        tt = [(i + 1) * r["period"] / 60 for i in range(len(e))]
        lim = D["limit"]
        a = Ax(x0, x0 + pw, y1t, y1b, 0, tmax_min, -ylim, ylim)
        out.append(T(x0, 14, f"{r['set']:g} ml/h", fill=INK, weight=600, size=14))
        out.append(T(x0 + pw, 14, f"{len(e)} cycles · mean {f(run[-1], 1, True)} %", anchor="end", fill=GREY))
        out.append(R(x0, a.sy(lim), pw, a.sy(-lim) - a.sy(lim), K["tint"]))
        out.append(L(x0, a.sy(0), x0 + pw, a.sy(0), RULE))
        for x, v in zip(tt, e):
            vv = max(-ylim, min(ylim, v))
            out.append(C(a.sx(x), a.sy(vv), 1.8 if len(e) > 100 else 2.5, "#7A7D80"))
        out.append(PL(a.pts(tt, run), INK, 1.8))
        if c == 0:
            out += range_frame_y(a, list(yticks), lambda v: f(v, 0, True) if v else "0")
        b = Ax(x0, x0 + pw, y2t, y2b, 0, tmax_min, -yconv, yconv)
        out.append(R(x0, b.sy(run[-1] + U), pw, b.sy(run[-1] - U) - b.sy(run[-1] + U), K["tint"]))
        out.append(L(x0, b.sy(0), x0 + pw, b.sy(0), RULE))
        out.append(PL(b.pts(tt, [max(-yconv, min(yconv, v)) for v in run]), INK, 1.8))
        # จุดที่ค่าเฉลี่ยสะสมเข้าแถบ ±U และอยู่ต่อจนจบ
        k = len(run) - 1
        while k > 0 and abs(run[k - 1] - run[-1]) <= U:
            k -= 1
        out.append(L(b.sx(tt[k]), y2t, b.sx(tt[k]), y2b, INK, 1, "2 2"))
        out.append(T(b.sx(tt[k]) + 4, y2t + 12, f"inside ±U from {tt[k]:.1f} min", fill=INK))
        if c == 0:
            out += range_frame_y(b, list(cticks), lambda v: f(v, 0, True) if v else "0")
        for t in xticks:
            out.append(T(b.sx(t), y2b + 16, f"{t}", anchor="middle"))
    if labels:
        out.append(T(left, y1b + 22, "error of each cycle, % (dots) and running mean (line) · shaded = limit ±5 %", fill=GREY))
        out.append(T(left, y2b + 34, "running mean error, % · shaded = final result ± U (k = 2) · time, min", fill=GREY))
    return svg(w, y2b + 42, "Small multiples of per-cycle error and running mean for each rate", out)


def side(title, thai, no_label, no, extra_kv, statement, sig2):
    kv = "".join(f"<span>{k}</span><span>{v}</span>" for k, v in [
        ("Instrument", f"{D['brand']} {D['model']}, infusion pump"), ("Serial", D["serial"]), ("Asset", f"{D['asset']} · {D['dept']}"),
        ("Customer", D["site"]), *extra_kv])
    return f"""
<aside style="width: 292px; flex: none; display: flex; flex-direction: column; gap: 14px; border-right: 1px solid #161718; padding-right: 22px">
  <div style="display: flex; flex-direction: column; gap: 2px">
    <span class="l">[Company Name] · Calibration Laboratory</span>
    <span style="font-size: 30px; line-height: 34px; font-weight: 600; letter-spacing: -.01em">{title}</span>
    <span class="it" style="font-size: 14px; line-height: 20px; color: #3E4143">{thai}</span>
  </div>
  <div style="display: flex; flex-direction: column; font-size: 13px; line-height: 19px">
    <span>{no_label} <b style="font-weight: 600">{no}</b></span>
    <span>Job <b style="font-weight: 600; color: {K["ink"]}">{D["job"]}</b> · {D["date"]} · page 1 / 1</span>
  </div>
  <div class="kv">{kv}</div>
  <div style="display: flex; flex-direction: column; gap: 4px; font-size: 13px; line-height: 19px">{statement}</div>
  <div style="margin-top: auto; display: flex; flex-direction: column; gap: 10px">
    <div class="sig"><div></div><span style="font-size: 13px">{D["operator"] if "Calibration" in title else "[Technician name]"}</span><span class="l">{"Calibrated by" if "Calibration" in title else "Inspected by"}</span></div>
    <div class="sig"><div></div><span style="font-size: 13px">{sig2[0]}</span><span class="l">{sig2[1]}</span></div>
  </div>
</aside>"""


def calibration():
    rows = "".join(f"""<tr><td>{r["set"]:.1f}</td><td>{r["meas"]:.2f}</td><td>{f(err(r), 1, True)} %</td><td>{r["U"]:.1f} %</td>
<td>{r["n"]}</td><td>{r["period"]} s</td><td>{r["sd2"]:.1f} %</td><td>{r["pre"]}</td><td><b style="font-weight: 600">Pass</b></td></tr>""" for r in D["rates"])
    statement = f"""<h2>Statement of conformity</h2>
<p>All three rates are within ±{D["limit"]:.0f} % of the set rate (simple acceptance, ILAC-G8). The pump is fit for use.</p>
<h2 style="margin-top: 6px">Method</h2>
<p>Gravimetric [WI-CAL-01] after IEC 60601-2-24:2012 and ISO 4787:2021. Balance {BALANCE}, cert. [—], traceable to SI.
Water {D["water"]} °C, {D["rh"]} %RH, {D["hpa"]} hPa. U at k = 2 (GUM).</p>
<div style="margin-top: 14px; border-top: 1px solid #161718; border-bottom: 1px solid #161718; padding: 8px 0; display: flex; align-items: baseline; justify-content: space-between">
<span style="font-size: 34px; line-height: 40px; font-weight: 600; letter-spacing: .04em">PASS</span><span class="l" style="text-align: right">all rates<br>simple acceptance</span></div>"""
    main = f"""
<main style="flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 14px; padding-left: 26px">
  <div style="display: flex; justify-content: space-between; align-items: baseline"><h2>Each rate on the same scale</h2>
  <span class="l">one column per set rate · time from start of measurement</span></div>
  {grid(D["rates"], FLOWS, 723, [r["U"] for r in D["rates"]], row_h=(200, 150))}
  <table><thead><tr><th>Set ml/h</th><th>Measured ml/h</th><th>Error</th><th>U, k = 2</th><th>Cycles</th><th>Period</th><th>±2SD cycle</th><th>Pre-run</th><th>Result</th></tr></thead>
  <tbody>{rows}</tbody></table>
  <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 22px; font-size: 13px; line-height: 18px">
    <p><span class="it">Same scale.</span> Every panel uses the same axes, so the wider scatter at 200 ml/h is real: shorter cycles hold fewer balance readings.</p>
    <p><span class="it">Running mean.</span> The line is the average of all cycles so far; its last value is the reported error.</p>
    <p><span class="it">Long enough?</span> The dotted mark is when the running mean entered ±U and stayed; it should come well before the end.</p>
  </div>
  <div style="margin-top: auto; display: flex; justify-content: space-between" class="l"><span>Reproduce in full only · results relate only to the item calibrated</span><span>FM-CAL-20 Rev.00 · DeltaM 0.3.0</span></div>
</main>"""
    body = side("Calibration certificate", "ใบรับรองผลการสอบเทียบ", "Certificate", D["cert"],
                [("Infusion set", D["set_label"]), ("Water", f"{D['water']} °C · {D['rh']} %RH"), ("Next due", "Nov 2027")], statement, (D["approver"], "Approved by")) + main
    return dc("Calibration T", 1123, 794, FONT, CSS, ROOT + "; padding: 36px 40px 28px 40px", body)


# ---------------------------------------------------------------- Inspection (แนวนอน)
INSP_FLOWS = series(II["n"], II["meas"], II["meas"] * 0.011, 404, ar=0.1)
HISTORY = [("May 2024", -0.4), ("Nov 2024", 0.2), ("May 2025", 0.9), ("Nov 2025", 0.5), ("May 2026", 1.1),
           ("Nov 2026", round(err(II), 1))]
CHECKS = [("Housing, labels, IFU", "OK"), ("Pole clamp and handle", "OK"), ("Power cord and plug", "OK"),
          ("Keypad, display", "OK"), ("Door and tube guide", "OK"), ("Air-in-line detector", "OK"),
          ("Occlusion alarm, downstream", "OK"), ("Occlusion alarm, upstream", "OK"), ("Battery ≥ 30 min", "OK"),
          ("Audible and visual alarms", "OK"), ("Nurse call", "N/A"), ("Electrical safety IEC 62353", "N/P")]


def history_chart(w=330):
    ax = Ax(46, w - 30, 20, 150, -0.4, len(HISTORY) - 0.6, -5.5, 5.5)
    out = [R(ax.x0, ax.sy(5), ax.x1 - ax.x0, ax.sy(-5) - ax.sy(5), K["tint"]),
           L(ax.x0, ax.sy(0), ax.x1, ax.sy(0), RULE)]
    out += range_frame_y(ax, [-5, 0, 5], lambda v: f(v, 0, True) if v else "0")
    xs = list(range(len(HISTORY)))
    ys = [v for _, v in HISTORY]
    out.append(PL(ax.pts(xs, ys), INK, 1.5))
    for x, (lab, v) in zip(xs, HISTORY):
        last = x == xs[-1]
        out.append(C(ax.sx(x), ax.sy(v), 3.5 if last else 2.5, INK))
        out.append(T(ax.sx(x), ax.sy(v) - 9, f(v, 1, True), anchor="middle", fill=INK if last else GREY,
                     weight=600 if last else None))
        out.append(T(ax.sx(x), ax.y1 + 18, lab.split()[0], anchor="middle"))
        out.append(T(ax.sx(x), ax.y1 + 33, lab.split()[1], anchor="middle"))
    return svg(w, 190, "Flow error at 25 ml/h at the last six inspections, all inside ±5 %", out)


def inspection():
    e = err(II)
    rate = dict(set=II["set"], period=II["period"], meas=II["meas"])
    ck = "".join(f'<tr><td>{a}</td><td style="{"" if b == "OK" else "color: #5C5F62"}">{b}</td></tr>' for a, b in CHECKS)
    statement = f"""<h2>Status</h2><p>Fit for use. 10 checks OK, nurse call not fitted, electrical safety not performed
(analyser not on site). Next inspection May 2027.</p>
<div style="margin-top: 14px; border-top: 1px solid #161718; border-bottom: 1px solid #161718; padding: 8px 0; display: flex; align-items: baseline; justify-content: space-between">
<span style="font-size: 26px; line-height: 40px; font-weight: 600; letter-spacing: .04em">FIT FOR USE</span><span class="l" style="text-align: right">next due<br>May 2027</span></div>"""
    main = f"""
<main style="flex: 1; min-width: 0; display: grid; grid-template-columns: 230px minmax(0, 1fr); column-gap: 26px; padding-left: 26px">
  <section style="display: flex; flex-direction: column; gap: 6px"><h2>Checks</h2>
    <table><tbody>{ck}</tbody></table>
    <h2 style="margin-top: 10px">Parts and accessories</h2>
    <table><tbody><tr><td>Door latch spring</td><td>replaced</td></tr><tr><td>Warranty</td><td>to Nov 2027</td></tr>
    <tr><td>Received with</td><td>cord, clamp</td></tr></tbody></table>
    <h2 style="margin-top: 10px">Remarks</h2><p style="font-size: 13px; line-height: 18px">Keypad cleaned. Display contrast set to factory value.</p></section>
  <section style="display: flex; flex-direction: column; gap: 10px; min-width: 0">
    <div style="display: flex; justify-content: space-between; align-items: baseline"><h2>Flow check · {II["set"]:g} ml/h · {II["minutes"]} min</h2>
    <span style="font-size: 13px">measured <b style="font-weight: 600">{II["meas"]:.2f} ml/h</b> · error <b style="font-weight: 600">{f(e, 1, True)} %</b></span></div>
    {grid([rate], [INSP_FLOWS], 446, [II["U"]], tmax_min=5.3, ylim=6, yconv=3, row_h=(110, 80), labels=False,
         yticks=(-5, 0, 5), cticks=(-2, 0, 2), xticks=(0, 1, 2, 3, 4, 5))}
    <p class="l">Top: error of each pump cycle (dots) and running mean (line), % · shaded ±5 %. Bottom: running mean settles inside ±U.</p>
    <h2 style="margin-top: 6px">Error at {II["set"]:g} ml/h, last six inspections</h2>
    {history_chart(446)}
    <p class="l">Same rate and method every six months — a drift towards a limit shows here before the pump fails.</p>
  </section>
  <div style="grid-column: 1 / span 2; margin-top: auto; display: flex; justify-content: space-between" class="l"><span>Balance {BALANCE} · water {D["water"]} °C</span><span>FM-INS-20 Rev.00 · DeltaM 0.3.0</span></div>
</main>"""
    body = side("Inspection report", "รายงานการตรวจสภาพเครื่อง", "Report", D["insp"], [], statement,
                ("[Ward representative]", "Received by")) + main
    return dc("Inspection T", 1123, 794, FONT, CSS, ROOT + "; padding: 36px 40px 28px 40px", body)


# ---------------------------------------------------------------- Quick Test: A6 แนวตั้ง
QT_FLOWS = cycle_flows(dict(n=QT["n"], meas=QT["meas"], sd2=2.4), 505)


def quicktest():
    e = (QT["meas"] - QT["set"]) / QT["set"] * 100
    rate = dict(set=QT["set"], period=QT["period"], meas=QT["meas"])
    chart = grid([rate], [QT_FLOWS], 329, [1.0], tmax_min=3.2, ylim=6, yconv=3, row_h=(150, 100), labels=False,
                 yticks=(-5, 0, 5), cticks=(-2, 0, 2), xticks=(0, 1, 2, 3))
    body = f"""
<div style="display: flex; flex-direction: column; gap: 2px; border-bottom: 1px solid #161718; padding-bottom: 8px">
  <span class="l">[Company Name]</span>
  <span style="font-size: 24px; line-height: 28px; font-weight: 600">Quick test</span>
  <span style="font-size: 13px; line-height: 18px">{D["brand"]} {D["model"]} · S/N {QT["serial"]} · {QT["dept"]}</span>
  <span class="l">{QT["no"]} · <span style="color: {K["ink"]}">{QT["job"]}</span> · {QT["date"]}</span>
</div>
<div style="display: flex; justify-content: space-between; align-items: baseline">
  <span style="font-size: 13px">{QT["set"]:g} ml/h → <b style="font-size: 22px; font-weight: 600">{QT["meas"]:.2f}</b></span>
  <span style="font-size: 22px; font-weight: 600">{f(e, 1, True)} %</span>
</div>
{chart}
<p class="l">Dots: error of each of {QT["n"]} cycles · line: running mean · shaded ±5 % (top), ±1 % (bottom).</p>
<div style="margin-top: auto; display: flex; justify-content: space-between; align-items: flex-end; border-top: 1px solid #161718; padding-top: 6px">
  <span class="l">Screening only · FM-QT-20<br>Tested by ____________</span>
  <span style="font-size: 22px; font-weight: 600; letter-spacing: .06em">PASS</span>
</div>
"""
    return dc("Quick Test T", 397, 559, FONT, CSS, ROOT + "; flex-direction: column; padding: 22px 24px 18px 24px; gap: 10px", body)


def boards():
    return [
        dict(name="T-Calibration.dc.html", w=1123, h=794, title="T · Calibration small multiples (A4 landscape)", html=calibration()),
        dict(name="T-Inspection.dc.html", w=1123, h=794, title="T · Inspection with history (A4 landscape)", html=inspection()),
        dict(name="T-QuickTest.dc.html", w=397, h=559, title="T · Quick Test (A6)", html=quicktest()),
    ]
