"""แบบ V — Traceability & environment: แผนภาพสายการสอบกลับได้ (มวล / เวลา / อุณหภูมิ → flow) + log สภาพแวดล้อมระหว่างวัด
Inspection มีการตรวจตราชั่งด้วยตุ้มน้ำหนักก่อนใช้ (intermediate check, ISO/IEC 17025 ข้อ 6.4.10) · ตัวอย่าง Infusion
"""
from common import (cycle_flows, INFUSION as D, INF as K, INF_INSP as II, INF_QT as QT, INK, GREY, RULE, PAPER, BALANCE,
                    f, err, series, mean, Ax, T, L, R, PL, PG, C, svg, fonts, dc)

HEADING = "แบบ V — Traceability & environment: แผนภาพสายการสอบกลับได้ มวล/เวลา/อุณหภูมิ → flow + log อุณหภูมิ ความชื้น ความดันระหว่างวัด"
NOTE_FILL = "green"
NOTE = ("V: ตอบข้อกำหนด ISO/IEC 17025 ข้อ 6.5 (traceability) และ 6.3 (สภาวะแวดล้อม) เป็นภาพเดียว\n"
        "ต้องเพิ่มในโปรแกรม: ทะเบียนเครื่องมืออ้างอิง (เลขใบรับรอง วันครบกำหนด) และบันทึกสภาพแวดล้อมเป็นช่วง ๆ\n"
        "ตอนนี้ DeltaM เก็บอุณหภูมิ/ความชื้น/ความดันครั้งเดียวต่องาน")

FONT = fonts("Archivo:wght@400;500;600;700", "Noto+Sans+Thai:wght@400;500;600")
ROOT = ("color: #161718; font-family: 'Archivo', 'Noto Sans Thai', sans-serif; display: flex; flex-direction: column; "
        "font-variant-numeric: tabular-nums lining-nums")
CSS = """
.l{font-size:12px;line-height:16px;color:#5C5F62}
h2{margin:0;font-size:12px;line-height:16px;font-weight:700;letter-spacing:.1em;text-transform:uppercase}
.hd{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid #161718;padding-bottom:4px}
table{border-collapse:collapse;width:100%;font-size:13px;line-height:18px}
th{font-weight:500;color:#5C5F62;font-size:12px;text-align:right;padding:3px 6px;border-bottom:1px solid #161718}
td{text-align:right;padding:3px 6px;border-bottom:1px solid #DCDCD8}
th:first-child,td:first-child{text-align:left;padding-left:0}
td.tl,th.tl{text-align:left}
p{margin:0}
.sig{display:flex;flex-direction:column;gap:2px}
.sig div{height:28px;border-bottom:1px solid #161718}
svg text{font-family:'Archivo','Noto Sans Thai',sans-serif}
"""

# ---------------------------------------------------------------- ข้อมูลสภาพแวดล้อม (ค่าเฉลี่ย = ค่าในใบรับรอง)
SEG = [("10 ml/h", 0, 18.6), ("50 ml/h", 18.6, 36.0), ("200 ml/h", 36.0, 52.0)]   # นาทีเริ่ม-จบของแต่ละ rate
TMIN = list(range(0, 53))
ENV = [
    ("Water", "°C", series(53, D["water"], 0.07, 811, ar=0.9), (20.0, 25.0), 1),
    ("Air", "°C", series(53, 24.3, 0.12, 822, ar=0.9), (18.0, 28.0), 1),
    ("Humidity", "%RH", series(53, D["rh"], 0.8, 833, ar=0.9), (30.0, 75.0), 0),
    ("Pressure", "hPa", series(53, D["hpa"], 0.25, 844, ar=0.95), (950.0, 1050.0), 1),
]

EQUIP = [
    ("Balance", "A&amp;D GF-300 · S/N 14654769", "[cert. no.]", "[due]", "mass"),
    ("Check weights", "F1 set 20 g, 50 g · [ID]", "[cert. no.]", "[due]", "balance check"),
    ("Thermometer", "[model] · [ID], probe in water", "[cert. no.]", "[due]", "water density"),
    ("Hygro-barometer", "[model] · [ID]", "[cert. no.]", "[due]", "air density"),
    ("Time base", "PC clock vs NTP [server]", "logged offset", "each run", "time"),
]


def env_chart(w=706):
    """log สภาพแวดล้อม 4 แถบเรียงกัน แกนเวลาเดียวกัน — แถบสี = ช่วงที่วิธีทดสอบยอมรับ"""
    rows, out = len(ENV), []
    top, rh, gap = 28, 34, 8
    ax0 = Ax(110, w - 120, 0, 0, 0, 52, 0, 1)
    for name, a, b in SEG:
        out.append(L(ax0.sx(a), 6, ax0.sx(a), top + rows * (rh + gap) - gap, RULE))
        out.append(T((ax0.sx(a) + ax0.sx(b)) / 2, 18, name, anchor="middle", fill=INK, weight=600))
    out.append(L(ax0.sx(52), 6, ax0.sx(52), top + rows * (rh + gap) - gap, RULE))
    for i, (name, unit, vals, band, dec) in enumerate(ENV):
        y0 = top + i * (rh + gap)
        lo, hi = min(vals), max(vals)
        pad = max((hi - lo) * 0.6, 0.15 if dec else 1.0)
        ax = Ax(110, w - 120, y0, y0 + rh, 0, 52, lo - pad, hi + pad)
        # แถบยอมรับ: ส่วนที่อยู่ในกรอบกราฟ (ช่วงยอมรับกว้างกว่าที่แกว่งมาก จึงเต็มกรอบ)
        out.append(R(ax.x0, y0, ax.x1 - ax.x0, rh, K["tint"]))
        out.append(L(ax.x0, y0 + rh, ax.x1, y0 + rh, RULE))
        out.append(PL(ax.pts(TMIN, vals), INK, 1.5))
        out.append(T(0, y0 + 16, name, fill=INK, weight=600, size=13))
        out.append(T(0, y0 + 32, f"{unit} · {band[0]:g}–{band[1]:g}", fill=K["ink"]))
        fmt = (lambda v: f"{v:.1f}") if dec else (lambda v: f"{v:.0f}")
        out.append(T(ax.x1 + 10, y0 + 16, f"{fmt(lo)} – {fmt(hi)}", fill=INK))
        out.append(T(ax.x1 + 10, y0 + 32, f"mean {fmt(mean(vals))}", fill=GREY))
    yb = top + rows * (rh + gap) - gap
    for t in range(0, 53, 10):
        out.append(T(ax0.sx(t), yb + 16, f"{t}", anchor="middle"))
    out.append(T(ax0.sx(52), yb + 32, "time from start, min · blue range = allowed by [WI-CAL-01]", anchor="end"))
    return svg(w, yb + 38, "Water and air temperature, humidity and pressure logged every minute during the run", out)


def node(x, y, w, h, title, lines, strong=False):
    out = [R(x, y, w, h, INK if strong else "#ffffff", INK, 1.5 if strong else 1)]
    col = "#ffffff" if strong else INK
    sub = "#C9CACB" if strong else GREY
    out.append(T(x + 10, y + 18, title, fill=col, weight=600, size=13))
    for k, ln in enumerate(lines):
        out.append(T(x + 10, y + 34 + 15 * k, ln, fill=sub, size=12))
    return out


def arrow(x1, y1, x2, y2):
    out = [L(x1, y1, x2 - 6, y2, INK, 1.5)]
    out.append(f'<polygon points="{x2:.1f},{y2:.1f} {x2 - 8:.1f},{y2 - 4:.1f} {x2 - 8:.1f},{y2 + 4:.1f}" fill="{INK}"></polygon>')
    return out


def chain(w=706, u_text="U 0.6 % at 50 ml/h"):
    """แผนภาพสายการสอบกลับได้: 3 ปริมาณขาเข้า → DeltaM → ผลของปั๊ม"""
    out = []
    cw, ch, gx, gy = 130, 48, 18, 10
    cols = [0, cw + gx, 2 * (cw + gx)]
    rows_ = [(("kilogram", "mass"), ("NIMT", "national standard"), ("Balance", "[lab] cert. · U 0.6 mg")),
             (("second", "time"), ("NIMT", "UTC(NIMT) via NTP"), ("PC clock", "offset logged each run")),
             (("kelvin", "temperature"), ("NIMT", "ITS-90"), ("Thermometer", "[lab] cert. · U 0.1 °C"))]
    y = 20
    for c, head in enumerate(["SI unit", "National institute", "Calibrated reference"]):
        out.append(T(cols[c], 12, head, fill=GREY))
    for r, cells in enumerate(rows_):
        yy = y + r * (ch + gy)
        for c, (t1, t2) in enumerate(cells):
            out += node(cols[c], yy, cw, ch, t1, [t2])
        out += arrow(cols[0] + cw, yy + ch / 2, cols[1], yy + ch / 2)
        out += arrow(cols[1] + cw, yy + ch / 2, cols[2], yy + ch / 2)
    fx = 3 * (cw + gx)
    fw = 132
    fy = y + (ch + gy) - 8
    out.append(T(fx, 12, "Measurement", fill=GREY))
    out += node(fx, fy, fw, ch + 16, "DeltaM run", ["Q = Δm · Z / Δt", u_text], strong=True)
    for r in range(3):
        yy = y + r * (ch + gy) + ch / 2
        out += arrow(cols[2] + cw, yy, fx, fy + (ch + 16) / 2 + (r - 1) * 16)
    px = fx + fw + gx
    out.append(T(px, 12, "Item", fill=GREY))
    out += node(px, fy, w - px - 1, ch + 16, f"{D['model']}", [f"S/N {D['serial']}", "error ± U"])
    out += arrow(fx + fw, fy + (ch + 16) / 2, px, fy + (ch + 16) / 2)
    return svg(w, y + 3 * (ch + gy), "Traceability of mass, time and temperature to SI through the national institute to this result", out)


def header(title, sub, no_label, no):
    return f"""
<header style="display: grid; grid-template-columns: 64px minmax(0, 1fr) auto; column-gap: 16px; align-items: center">
  <div style="width: 64px; height: 64px; border: 1px solid #161718; display: flex; align-items: center; justify-content: center" class="l">LOGO</div>
  <div style="display: flex; flex-direction: column"><span class="l">[Company Name] · Calibration Laboratory · [address, province]</span>
  <span style="font-size: 26px; line-height: 32px; font-weight: 700; letter-spacing: -.01em">{title}</span>
  <span style="font-size: 13px; line-height: 18px; color: #3E4143">{sub}</span></div>
  <div style="text-align: right; font-size: 13px; line-height: 19px"><span class="l">{no_label}</span><br><b style="font-weight: 600">{no}</b><br>
  <b style="font-weight: 700; color: {K["ink"]}">{D["job"]}</b> · {D["date"]}</div>
</header>
<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-top: 2px solid #161718; border-bottom: 1px solid #161718; padding: 6px 0; font-size: 13px; line-height: 18px; column-gap: 14px">
  <div style="display: flex; flex-direction: column"><span class="l">Instrument</span><span>{D["brand"]} {D["model"]} · infusion</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Serial · asset</span><span>{D["serial"]} · {D["asset"]}</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Customer</span><span>{D["site"]} · {D["dept"]}</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Infusion set</span><span>{D["set_label"]}</span></div>
</div>"""


def footer(form):
    return (f'<div style="display: flex; justify-content: space-between" class="l"><span>Page 1 of 1 · reproduce in full only</span>'
            f'<span>{form} · DeltaM 0.3.0</span></div>')


def calibration():
    rows = "".join(f"""<tr><td>{r["set"]:.1f}</td><td>{r["meas"]:.2f}</td><td>{f(err(r), 1, True)} %</td><td>{r["U"]:.1f} %</td>
<td>±{D["limit"]:.0f} %</td><td><b style="font-weight: 600">Pass</b></td></tr>""" for r in D["rates"])
    eq = "".join(f'<tr><td>{a}</td><td class="tl">{b}</td><td class="tl">{c}</td><td>{d}</td><td class="tl">{e}</td></tr>' for a, b, c, d, e in EQUIP)
    body = f"""
{header("Calibration certificate", "with traceability and environment record · ใบรับรองพร้อมสายการสอบกลับได้", "Certificate No.", D["cert"])}
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>Results</h2><span class="l">gravimetric · U at k = 2 · simple acceptance (ILAC-G8)</span></div>
  <table><thead><tr><th>Set ml/h</th><th>Measured ml/h</th><th>Error</th><th>U, k = 2</th><th>Limit</th><th>Result</th></tr></thead><tbody>{rows}</tbody></table>
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>Metrological traceability</h2><span class="l">ISO/IEC 17025 §6.5 · ILAC P10</span></div>
  {chain()}
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>Environment during the run</h2><span class="l">logged every minute · ISO/IEC 17025 §6.3</span></div>
  {env_chart()}
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>Reference equipment</h2><span class="l">all within calibration interval on {D["date"]}</span></div>
  <table><thead><tr><th>Item</th><th class="tl">Model · ID</th><th class="tl">Certificate</th><th>Due</th><th class="tl">Used for</th></tr></thead><tbody>{eq}</tbody></table>
</section>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 150px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["operator"]}</b><span class="l">Calibrated by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["approver"]}</b><span class="l">Approved by</span></div>
  <div style="border: 2px solid #161718; padding: 6px; text-align: center; display: flex; flex-direction: column"><span class="l">Result</span><span style="font-size: 24px; line-height: 30px; font-weight: 700; letter-spacing: .08em">PASS</span></div>
</div>
{footer("FM-CAL-22 Rev.00")}
"""
    return dc("Calibration V", 794, 1123, FONT, CSS, ROOT + "; padding: 28px 44px 22px 44px; gap: 12px", body)


# ---------------------------------------------------------------- Inspection: ตรวจตราชั่งก่อนใช้ + checklist
CHECK_W = [("20 g", 20.0, 20.001, 0.003), ("50 g", 50.0, 50.000, 0.003), ("0 g, after tare", 0.0, 0.000, 0.002)]
CHECKS = [("Housing, labels, IFU", "OK"), ("Pole clamp and handle", "OK"), ("Power cord and plug", "OK"),
          ("Keypad, display, indicators", "OK"), ("Door and tube guide", "OK"), ("Air-in-line detector", "OK"),
          ("Occlusion alarm, downstream", "OK"), ("Occlusion alarm, upstream", "OK"), ("Battery ≥ 30 min", "OK"),
          ("Audible and visual alarms", "OK"), ("Nurse call", "N/A"), ("Electrical safety IEC 62353", "N/P")]


def check_bar(dev, tol, w=150):
    """แถบเล็กแสดงค่าเบี่ยงของตุ้มเทียบเกณฑ์ ±tol"""
    ax = Ax(4, w - 4, 0, 0, -tol * 1.4, tol * 1.4, 0, 1)
    out = [R(ax.sx(-tol), 3, ax.sx(tol) - ax.sx(-tol), 10, K["tint"]), L(ax.sx(0), 0, ax.sx(0), 16, GREY),
           L(ax.sx(-tol), 0, ax.sx(-tol), 16, INK), L(ax.sx(tol), 0, ax.sx(tol), 16, INK),
           R(ax.sx(dev) - 2, 2, 4, 12, INK)]
    return svg(w, 16, f"deviation {dev * 1000:+.0f} mg within ±{tol * 1000:.0f} mg", out)


def inspection():
    e = err(II)
    cw = "".join(f"""<tr><td>{n}</td><td>{nom:.3f}</td><td>{rd:.3f}</td><td>{f((rd - nom) * 1000, 0, True)} mg</td><td>±{tol * 1000:.0f} mg</td>
<td style="width: 160px">{check_bar(rd - nom, tol)}</td><td>OK</td></tr>""" for n, nom, rd, tol in CHECK_W)
    ckrow = lambda rows: "".join(f'<tr><td>{a}</td><td style="{"" if b == "OK" else "color: #5C5F62"}"><b style="font-weight: 600">{b}</b></td></tr>' for a, b in rows)
    half = len(CHECKS) // 2
    eq = "".join(f'<tr><td>{a}</td><td class="tl">{b}</td><td>{d}</td></tr>' for a, b, c, d, e2 in EQUIP)
    env = " · ".join(f"{n.lower()} {mean(v):.{d}f} {u}" for n, u, v, _, d in ENV)
    body = f"""
{header("Inspection report", "with reference check before use · รายงานการตรวจสภาพเครื่อง", "Report No.", D["insp"])}
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>1 · Balance check before use</h2><span class="l">intermediate check, ISO/IEC 17025 §6.4.10 · check weights F1</span></div>
  <table><thead><tr><th>Load</th><th>Nominal g</th><th>Reading g</th><th>Deviation</th><th>Tolerance</th><th></th><th>Result</th></tr></thead><tbody>{cw}</tbody></table>
</section>
<section style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 28px">
  <div style="display: flex; flex-direction: column; gap: 6px"><div class="hd"><h2>2 · Checks</h2><span class="l">10 OK</span></div>
  <table><tbody>{ckrow(CHECKS[:half])}</tbody></table></div>
  <div style="display: flex; flex-direction: column; gap: 6px"><div class="hd"><h2>&#8203;</h2><span class="l">N/A not fitted · N/P not performed</span></div>
  <table><tbody>{ckrow(CHECKS[half:])}</tbody></table></div>
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>3 · Flow check · {II["set"]:g} ml/h · {II["minutes"]} min</h2><span class="l">gravimetric, {II["n"]} pump cycles</span></div>
  <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); column-gap: 16px; font-size: 13px; line-height: 18px">
    <div style="display: flex; flex-direction: column"><span class="l">Measured</span><b style="font-size: 22px; line-height: 28px; font-weight: 700">{II["meas"]:.2f} ml/h</b></div>
    <div style="display: flex; flex-direction: column"><span class="l">Error · limit ±{D["limit"]:.0f} %</span><b style="font-size: 22px; line-height: 28px; font-weight: 700">{f(e, 1, True)} %</b></div>
    <div style="display: flex; flex-direction: column; grid-column: span 2"><span class="l">Conditions (mean of run)</span><span>{env}</span></div>
  </div>
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>4 · Traceability of this check</h2><span class="l">ISO/IEC 17025 §6.5 · certificates and due dates on file [register ref.]</span></div>
  {chain(u_text=f"U {II['U']} % at {II['set']:g} ml/h")}
</section>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 170px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Technician name]</b><span class="l">Inspected by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Ward representative]</b><span class="l">Received by</span></div>
  <div style="border: 2px solid #161718; padding: 6px; text-align: center; display: flex; flex-direction: column"><span class="l">Status · next May 2027</span><span style="font-size: 20px; line-height: 28px; font-weight: 700; letter-spacing: .04em">FIT FOR USE</span></div>
</div>
{footer("FM-INS-22 Rev.00")}
"""
    return dc("Inspection V", 794, 1123, FONT, CSS, ROOT + "; padding: 32px 44px 24px 44px; gap: 16px", body)


# ---------------------------------------------------------------- Quick Test: A5 แนวนอน
QT_FLOWS = cycle_flows(dict(n=QT["n"], meas=QT["meas"], sd2=2.4), 505)


def cycle_strip(w=722):
    """error รายรอบเรียงตามเวลา + เส้นค่าเฉลี่ย (= ค่าที่รายงาน)"""
    ax = Ax(60, w - 120, 8, 92, 0.5, QT["n"] + 0.5, -6, 6)
    out = [R(ax.x0, ax.sy(5), ax.x1 - ax.x0, ax.sy(-5) - ax.sy(5), K["tint"]), L(ax.x0, ax.sy(0), ax.x1, ax.sy(0), GREY, 1, "2 2")]
    es = [(q - QT["set"]) / QT["set"] * 100 for q in QT_FLOWS]
    m = sum(es) / len(es)
    out.append(L(ax.x0, ax.sy(m), ax.x1, ax.sy(m), INK, 1.5))
    for i, v in enumerate(es, 1):
        out.append(L(ax.sx(i), ax.sy(0), ax.sx(i), ax.sy(v), INK, 1))
        out.append(C(ax.sx(i), ax.sy(v), 3.5, INK))
        out.append(T(ax.sx(i), ax.y1 + 16, f"{i}", anchor="middle"))
    for v in (-5, 0, 5):
        out.append(T(ax.x0 - 8, ax.sy(v) + 4, f(v, 0, True) if v else "0", anchor="end"))
    out.append(T(ax.x1 + 8, ax.sy(m) + 4, f"mean {f(m, 1, True)} %", fill=INK, weight=600))
    out.append(T(0, ax.sy(2.5) + 4, "error %", fill=GREY))
    out.append(T(ax.x1 + 8, ax.y1 + 16, "cycle no.", fill=GREY))
    return svg(w, 112, f"Error of each of {QT['n']} pump cycles with mean {f(m, 1, True)} %", out)

def quicktest():
    e = (QT["meas"] - QT["set"]) / QT["set"] * 100
    w = 280
    ax = Ax(16, w - 16, 0, 0, -6, 6, 0, 1)
    out = [R(ax.sx(-5), 10, ax.sx(5) - ax.sx(-5), 18, K["tint"]), L(ax.sx(0), 6, ax.sx(0), 32, GREY, 1, "2 2"),
           L(ax.sx(-5), 6, ax.sx(-5), 32, INK, 1.5), L(ax.sx(5), 6, ax.sx(5), 32, INK, 1.5),
           C(ax.sx(e), 19, 6, INK), T(ax.sx(-5), 48, "−5 %", anchor="middle"), T(ax.sx(5), 48, "+5 %", anchor="middle"),
           T(ax.sx(e), 48, f(e, 1, True) + " %", anchor="middle", fill=INK, weight=600)]
    gauge = svg(w, 52, f"Error {f(e, 1, True)} % inside ±5 %", out)
    body = f"""
<header style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #161718; padding-bottom: 8px">
  <div style="display: flex; flex-direction: column"><span class="l">[Company Name] · Quick function test</span>
  <span style="font-size: 22px; line-height: 28px; font-weight: 700">{D["brand"]} {D["model"]} · S/N {QT["serial"]}</span>
  <span style="font-size: 13px">{D["site"]} · {QT["dept"]}</span></div>
  <div style="text-align: right; font-size: 13px; line-height: 19px">{QT["no"]}<br><b style="font-weight: 700; color: {K["ink"]}">{QT["job"]}</b><br><span class="l">{QT["date"]}</span></div>
</header>
<div style="display: flex; gap: 32px; align-items: flex-end; white-space: nowrap">
  <div style="display: flex; flex-direction: column"><span class="l">Set</span><span style="font-size: 30px; line-height: 36px; font-weight: 700">{QT["set"]:.1f}</span><span class="l">ml/h</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Measured</span><span style="font-size: 30px; line-height: 36px; font-weight: 700">{QT["meas"]:.2f}</span><span class="l">ml/h · {QT["n"]} cycles · {QT["minutes"]} min</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Error</span><span style="font-size: 30px; line-height: 36px; font-weight: 700">{f(e, 1, True)} %</span><span class="l">limit ±{D["limit"]:.0f} %</span></div>
  <div style="margin-left: auto">{gauge}</div>
</div>
<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 24px">
  <div style="display: flex; flex-direction: column; gap: 6px"><div class="hd"><h2>Balance check</h2></div>
    <table><tbody><tr><td>50 g F1</td><td>50.000</td><td>OK</td></tr><tr><td>0 g, tare</td><td>0.000</td><td>OK</td></tr></tbody></table></div>
  <div style="display: flex; flex-direction: column; gap: 6px"><div class="hd"><h2>Conditions</h2></div>
    <table><tbody><tr><td>Water</td><td>{D["water"]} °C</td></tr><tr><td>Air · RH</td><td>24.3 °C · {D["rh"]} %</td></tr></tbody></table></div>
  <div style="display: flex; flex-direction: column; gap: 6px"><div class="hd"><h2>Before use</h2></div>
    <table><tbody><tr><td>Housing, door</td><td>OK</td></tr><tr><td>Alarms, battery</td><td>OK</td></tr></tbody></table></div>
</div>
{cycle_strip()}
<p style="font-size: 13px; line-height: 19px">Last calibration DM-C-2510-0233 · next due Nov 2027. Traceable to SI: balance {BALANCE}, cert. [—], due [—]; thermometer [ID], cert. [—]. Set {D["set_label"]}.</p>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 140px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><span class="l">Tested by · [Technician]</span></div>
  <span class="l">Screening only · does not replace calibration · FM-QT-22</span>
  <div style="border: 2px solid #161718; padding: 4px; text-align: center"><span style="font-size: 22px; line-height: 30px; font-weight: 700; letter-spacing: .08em">PASS</span></div>
</div>
"""
    return dc("Quick Test V", 794, 559, FONT, CSS, ROOT + "; padding: 26px 36px 22px 36px; gap: 16px", body)


def boards():
    return [
        dict(name="V-Calibration.dc.html", w=794, h=1123, title="V · Calibration traceability & environment", html=calibration()),
        dict(name="V-Inspection.dc.html", w=794, h=1123, title="V · Inspection with balance check", html=inspection()),
        dict(name="V-QuickTest.dc.html", w=794, h=559, title="V · Quick Test (A5 landscape)", html=quicktest()),
    ]
