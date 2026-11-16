"""แบบ Z — Syringe low-rate: start-up ของ syringe ที่ rate ต่ำ (เวลาจนนิ่ง, ปริมาตรที่ขาดช่วงเริ่ม, delay เทียบเท่า)
เหมาะกับ NICU / ยาออกฤทธิ์เร็ว · Inspection มีตารางความเข้ากันได้ของ syringe แต่ละยี่ห้อ/ขนาด · ป้าย 100 × 70 มม.
"""
import math

from common import (SYRINGE as D, SYR as K, SYR_QT as QT, INK, GREY, RULE, PAPER, BALANCE, f, err, Ax, T, L, R,
                    PL, PG, C, svg, fonts, dc)

HEADING = "แบบ Z — Syringe low-rate: start-up ที่ rate ต่ำ เวลาจนนิ่ง ปริมาตรที่ขาดช่วงเริ่ม delay เทียบเท่า + ตารางความเข้ากันได้ของ syringe"
NOTE_FILL = "pink"
NOTE = ("Z: สำหรับ NICU — ที่ 1 ml/h ปั๊มต้องใช้เวลากว่า syringe จะดันจริง ยาเข้าช้ากว่าที่สั่ง\n"
        "\"delay เทียบเท่า\" = ปริมาตรที่ขาด ÷ rate → พยาบาลเข้าใจทันที\n"
        "DeltaM มีช่วงก่อนวัด (pre-run) อยู่แล้ว ต้องเพิ่มการเก็บ/คำนวณเส้น start-up และตาราง syringe ต่อรุ่น")

FONT = fonts("Figtree:wght@400;500;600;700", "Noto+Sans+Thai:wght@400;500;600")
ROOT = ("color: #161718; font-family: 'Figtree', 'Noto Sans Thai', sans-serif; display: flex; flex-direction: column; "
        "font-variant-numeric: tabular-nums lining-nums")
CSS = """
.l{font-size:12px;line-height:16px;color:#5C5F62}
h2{margin:0;font-size:15px;line-height:20px;font-weight:700}
.hd{display:flex;justify-content:space-between;align-items:baseline;gap:16px}
table{border-collapse:collapse;width:100%;font-size:13px;line-height:18px}
th{font-weight:500;color:#5C5F62;font-size:12px;line-height:15px;text-align:right;padding:3px 6px;border-bottom:1.5px solid #161718;vertical-align:bottom}
td{text-align:right;padding:4px 6px;border-bottom:1px solid #DCDCD8}
th:first-child,td:first-child{text-align:left;padding-left:0}
.tl{text-align:left}
p{margin:0}
.sig{display:flex;flex-direction:column;gap:2px}
.sig div{height:28px;border-bottom:1px solid #161718}
svg text{font-family:'Figtree','Noto Sans Thai',sans-serif}
"""

# start-up: ช่วงตาย td (นาที, เก็บระยะคลอนของกลไก/syringe) + ค่าคงที่เวลา τ — นิ่ง (ถึง 99 % ของค่าสุดท้าย) ตรงกับเวลา pre-run ในตาราง
START = {1.0: (1.0, (14.0 - 1.0) / 4.6), 5.0: (0.3, (3.5 - 0.3) / 4.6), 25.0: (0.1, (1.0 - 0.1) / 4.6)}


def flow_pct(rate, t):
    """flow เป็น % ของค่าที่ตั้ง ที่เวลา t นาทีหลังกดเริ่ม"""
    r = next(x for x in D["rates"] if x["set"] == rate)
    td, tau = START[rate]
    if t <= td:
        return 0.0
    return r["meas"] / r["set"] * 100 * (1 - math.exp(-(t - td) / tau))


def deficit(rate, t_end=None):
    """ปริมาตรที่ขาด (ml) เทียบกับที่ตั้ง ช่วง 0..t_end นาที (ไม่รวม error คงที่หลังนิ่ง)"""
    td, tau = START[rate]
    return rate * (td + tau) / 60


def steady(rate):
    td, tau = START[rate]
    return td + 4.6 * tau


def mmss(minutes):
    s = round(minutes * 60)
    return f"{s // 60}:{s % 60:02d}"


def startup_chart(w=706, h=290, tmax=20, rates=(1.0, 5.0, 25.0)):
    ax = Ax(52, w - 110, 14, h - 44, 0, tmax, 0, 112)
    out = [R(ax.x0, ax.sy(103), ax.x1 - ax.x0, ax.sy(97) - ax.sy(103), K["tint"])]
    out += [L(ax.x0, ax.y0, ax.x0, ax.y1, INK), L(ax.x0, ax.y1, ax.x1, ax.y1, INK)]
    for v in (0, 25, 50, 75, 100):
        out.append(L(ax.x0 - 4, ax.sy(v), ax.x0, ax.sy(v), INK))
        out.append(T(ax.x0 - 8, ax.sy(v) + 4, f"{v}", anchor="end"))
    for t in range(0, tmax + 1, 2):
        out.append(T(ax.sx(t), ax.y1 + 18, f"{t}", anchor="middle"))
    out.append(T(ax.x1, ax.y1 + 34, "minutes after start", anchor="end"))
    out.append(T(ax.x0 + 8, ax.y0 + 4, "flow, % of set rate", fill=INK, weight=600))
    out.append(T(ax.x1 + 8, ax.sy(100) + 4, "±3 % band", fill=K["ink"]))
    styles = {1.0: ("", 2.4), 5.0: ("8 4", 2), 25.0: ("2 3", 2)}
    ts = [i * tmax / 400 for i in range(401)]
    for r in [x for x in D["rates"] if x["set"] in rates]:
        dash, sw = styles[r["set"]]
        out.append(PL(ax.pts(ts, [flow_pct(r["set"], t) for t in ts]), INK, sw, dash=dash or None))
        st = steady(r["set"])
        out.append(L(ax.sx(st), ax.sy(flow_pct(r["set"], st)) - 6, ax.sx(st), ax.y1, INK, 1, "2 2"))
        out.append(C(ax.sx(st), ax.sy(flow_pct(r["set"], st)), 4.5, K["fill"], INK, 1.5))
    # คำอธิบายเส้น (มุมขวาล่างที่ว่าง)
    lx, ly = ax.sx(tmax * 0.73), ax.sy(42)
    for k, rate in enumerate(rates):
        dash, sw = styles[rate]
        yy = ly + k * 20
        out.append(L(lx, yy - 4, lx + 34, yy - 4, INK, sw, dash or None))
        out.append(T(lx + 42, yy, f"{rate:g} ml/h · {mmss(steady(rate))}", fill=INK, weight=600))
    return svg(w, h, "Start-up curves at 1, 5 and 25 ml/h; steady after 14, 3.5 and 1 minutes", out)


def bedside_chart(w=706, h=220, tmax=30):
    """1 ml/h: ปริมาตรที่สั่ง vs ที่ส่งจริงในช่วงแรก — ช่องว่าง = ปริมาตรที่ขาด"""
    ax = Ax(52, w - 150, 14, h - 44, 0, tmax, 0, 0.55)
    ts = [i * tmax / 300 for i in range(301)]
    ordered = [t / 60 for t in ts]
    got, acc = [], 0.0
    for i, t in enumerate(ts):
        if i:
            dt = ts[i] - ts[i - 1]
            acc += (flow_pct(1.0, t) + flow_pct(1.0, ts[i - 1])) / 2 / 100 * dt / 60
        got.append(acc)
    poly = [f"{ax.sx(t):.1f},{ax.sy(v):.1f}" for t, v in zip(ts, ordered)] + \
           [f"{ax.sx(t):.1f},{ax.sy(v):.1f}" for t, v in zip(ts[::-1], got[::-1])]
    out = [PG(" ".join(poly), K["tint"]), L(ax.x0, ax.y0, ax.x0, ax.y1, INK), L(ax.x0, ax.y1, ax.x1, ax.y1, INK)]
    out.append(PL(ax.pts(ts, ordered), K["ink"], 1.5, dash="6 4"))
    out.append(PL(ax.pts(ts, got), INK, 2.2))
    for v in (0, 0.1, 0.2, 0.3, 0.4, 0.5):
        out.append(T(ax.x0 - 8, ax.sy(v) + 4, f"{v:.1f}", anchor="end"))
    for t in range(0, tmax + 1, 5):
        out.append(T(ax.sx(t), ax.y1 + 18, f"{t}", anchor="middle"))
    out.append(T(ax.x1, ax.y1 + 34, "minutes after start", anchor="end"))
    out.append(T(ax.x0 + 8, ax.y0 + 4, "volume, ml", fill=INK, weight=600))
    gap = ordered[-1] - got[-1]
    out.append(T(ax.x1 + 8, ax.sy(ordered[-1]) + 4, f"ordered {ordered[-1]:.3f}", fill=K["ink"]))
    out.append(T(ax.x1 + 8, ax.sy(got[-1]) + 16, f"delivered {got[-1]:.3f}", fill=INK, weight=600))
    start = round(deficit(1.0) * 1000)
    out.append(T(ax.sx(14), ax.sy(0.07), f"missing {gap * 1000:.0f} µl (shaded)", fill=INK, weight=600))
    out.append(T(ax.sx(14), ax.sy(0.07) + 16, f"= {start} µl start-up + {gap * 1000 - start:.0f} µl from the {f(err(D['rates'][0]), 1, True)} % error", fill=GREY))
    return svg(w, h, f"At 1 ml/h the first {tmax} minutes deliver {got[-1]:.3f} ml of {ordered[-1]:.3f} ml ordered", out), gap, got[-1]


def header(title, sub, no_label, no):
    return f"""
<header style="display: grid; grid-template-columns: minmax(0, 1fr) auto; column-gap: 24px; align-items: end">
  <div style="display: flex; flex-direction: column"><span class="l">[Company Name] · Calibration Laboratory</span>
  <span style="font-size: 28px; line-height: 34px; font-weight: 700; letter-spacing: -.01em">{title}</span>
  <span style="font-size: 13px; line-height: 18px; color: #3E4143">{sub}</span></div>
  <div style="display: flex; flex-direction: column; align-items: flex-end">
    <span style="font-size: 12px; line-height: 16px; letter-spacing: .12em; color: {K["ink"]}; font-weight: 700">SYRINGE PUMP</span>
    <span style="font-size: 24px; line-height: 28px; font-weight: 700; color: {K["ink"]}">{D["job"]}</span>
    <span style="font-size: 13px; line-height: 18px">{no_label} {no} · {D["date"]}</span></div>
</header>
<div style="display: grid; grid-template-columns: 1fr 1.1fr 1.2fr 1.2fr; border-top: 1.5px solid #161718; border-bottom: 1px solid #161718; padding: 6px 0; column-gap: 14px; font-size: 13px; line-height: 18px">
  <div style="display: flex; flex-direction: column"><span class="l">Pump</span><b style="font-weight: 600">{D["brand"]} {D["model"]}</b></div>
  <div style="display: flex; flex-direction: column"><span class="l">Serial · asset</span><span>{D["serial"]} · {D["asset"]}</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Customer</span><span>{D["site"]} · {D["dept"]}</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Syringe used</span><span>{D["set_label"]}, primed</span></div>
</div>"""


def calibration():
    chart_b, gap, got = bedside_chart()
    rows = "".join(f"""<tr><td>{r["set"]:.1f}</td><td>{r["meas"]:.3f}</td><td>{f(err(r), 1, True)} %</td><td>{r["U"]:.1f} %</td>
<td>{mmss(steady(r["set"]))}</td><td>{deficit(r["set"]) * 1000:.0f} µl</td><td>{mmss(START[r["set"]][0] + START[r["set"]][1])}</td>
<td><b style="font-weight: 700">Pass</b></td></tr>""" for r in D["rates"])
    body = f"""
{header("Calibration certificate", "low-rate and start-up record · ใบรับรองผลการสอบเทียบ syringe pump อัตราต่ำ", "Cert.", D["cert"])}
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>Results</h2><span class="l">limit ±{D["limit"]:.0f} % after steady flow · U at k = 2 · simple acceptance (ILAC-G8)</span></div>
  <table><thead><tr><th>Set ml/h</th><th>Measured ml/h</th><th>Error</th><th>U</th><th>Steady after<br>min:s</th><th>Volume missing<br>at start</th><th>Equivalent<br>delay</th><th>Result</th></tr></thead>
  <tbody>{rows}</tbody></table>
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>A · Start-up</h2><span class="l">gravimetric, from the moment Start is pressed · dot = steady (DeltaM auto pre-run)</span></div>
  {startup_chart()}
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>B · First 30 minutes at 1 ml/h</h2><span class="l">what the baby receives against what is ordered</span></div>
  {chart_b}
</section>
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 24px; font-size: 13px; line-height: 19px">
  <p><b style="font-weight: 600">Equivalent delay</b> = volume missing ÷ set rate. At 1 ml/h the drug arrives about {mmss(START[1.0][0] + START[1.0][1])} min
  later than ordered; the pump does not make up the missing {deficit(1.0) * 1000:.0f} µl. Priming the line and a smaller syringe shorten it.</p>
  <p>Gravimetric [WI-CAL-02], IEC 60601-2-24:2012, ISO 4787:2021. Balance {BALANCE}, cert. [—], traceable to SI.
  Water {D["water"]} °C, {D["rh"]} %RH, {D["hpa"]} hPa. Accuracy judged after steady flow: conforms at all rates.</p>
</div>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 150px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["operator"]}</b><span class="l">Calibrated by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["approver"]}</b><span class="l">Approved by</span></div>
  <div style="border: 2px solid #161718; padding: 6px; text-align: center; display: flex; flex-direction: column"><span class="l">Result</span><span style="font-size: 26px; line-height: 30px; font-weight: 700; letter-spacing: .08em">PASS</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Reproduce in full only · page 1 / 1</span><span>FM-CAL-27 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Calibration Z", 794, 1123, FONT, CSS, ROOT + "; padding: 30px 44px 22px 44px; gap: 14px", body)


# ---------------------------------------------------------------- Inspection: ความเข้ากันได้ของ syringe
SYRINGES = [
    ("Terumo", "10 ml", "yes", "10 ml", "1:05", "OK"),
    ("Terumo", "20 ml", "yes", "20 ml", "1:40", "OK"),
    ("Terumo", "50 ml", "yes", "50 ml", "2:40", "OK"),
    ("BD Plastipak", "20 ml", "yes", "20 ml", "1:45", "OK"),
    ("BD Plastipak", "50 ml", "yes", "50 ml", "2:55", "OK"),
    ("Nipro", "50 ml", "no", "—", "—", "not in library"),
]
CHECKS = [("Housing and labels", "OK"), ("Pole clamp", "OK"), ("Power cord and plug", "OK"),
          ("Syringe clamp, plunger holder", "OK"), ("Battery operation ≥ 60 min", "OK"), ("Keypad and display", "OK"),
          ("Near-empty and end alarm", "OK"), ("Audible and visual alarms", "OK"), ("Nurse call", "N/A"),
          ("Electrical safety IEC 62353", "N/P")]


def inspection():
    e = err(D["rates"][1])
    sy = "".join(f"""<tr><td>{b}</td><td class="tl">{s}</td><td class="tl">{lib}</td><td class="tl">{det}</td><td>{occ}</td>
<td><b style="font-weight: 700{"" if res == "OK" else "; border: 1.5px solid #161718; padding: 0 4px"}">{res}</b></td></tr>""" for b, s, lib, det, occ, res in SYRINGES)
    half = len(CHECKS) // 2
    ck = lambda rows: "".join(f'<tr><td>{a}</td><td style="{"" if b == "OK" else "color: #5C5F62"}"><b style="font-weight: 700">{b}</b></td></tr>' for a, b in rows)
    body = f"""
{header("Inspection report", "with syringe compatibility · รายงานการตรวจสภาพ พร้อมตาราง syringe ที่ใช้ได้", "Report", D["insp"])}
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>Syringes used on this ward</h2><span class="l">library = brands and sizes programmed in the pump · occlusion at 5 ml/h, level M</span></div>
  <table><thead><tr><th>Brand</th><th class="tl">Size</th><th class="tl">In library</th><th class="tl">Size detected</th><th>Occlusion alarm<br>min:s</th><th>Result</th></tr></thead><tbody>{sy}</tbody></table>
  <p style="font-size: 13px; line-height: 19px"><b style="font-weight: 600">Nipro 50 ml</b> is stocked by the ward but is not in the pump library: the pump will not accept it,
  or flow may be wrong if another brand is selected. Ask [biomedical engineering] to add it, or use a listed syringe.</p>
</section>
<section style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 28px">
  <div style="display: flex; flex-direction: column; gap: 6px"><h2>Checks</h2><table><tbody>{ck(CHECKS[:half])}</tbody></table></div>
  <div style="display: flex; flex-direction: column; gap: 6px"><h2>&#8203;</h2><table><tbody>{ck(CHECKS[half:])}</tbody></table></div>
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>Flow check · 5 ml/h · Terumo 50 ml</h2><span class="l">gravimetric · limit ±{D["limit"]:.0f} %</span></div>
  <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); column-gap: 16px">
    <div style="display: flex; flex-direction: column"><span class="l">Steady after</span><b style="font-size: 24px; line-height: 30px; font-weight: 700">{mmss(steady(5.0))}</b><span class="l">min:s from Start</span></div>
    <div style="display: flex; flex-direction: column"><span class="l">Measured</span><b style="font-size: 24px; line-height: 30px; font-weight: 700">{D["rates"][1]["meas"]:.3f}</b><span class="l">ml/h, 5 × 60 s</span></div>
    <div style="display: flex; flex-direction: column"><span class="l">Error</span><b style="font-size: 24px; line-height: 30px; font-weight: 700">{f(e, 1, True)} %</b><span class="l">limit ±{D["limit"]:.0f} %</span></div>
    <div style="display: flex; flex-direction: column"><span class="l">Equivalent delay</span><b style="font-size: 24px; line-height: 30px; font-weight: 700">{mmss(sum(START[5.0]))}</b><span class="l">min:s at start-up</span></div>
  </div>
  {startup_chart(706, 230, 8, rates=(5.0,))}
</section>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 170px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Technician name]</b><span class="l">Inspected by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Ward representative]</b><span class="l">Received by</span></div>
  <div style="border: 2px solid #161718; padding: 6px; text-align: center; display: flex; flex-direction: column"><span class="l">Status · 1 remark</span><span style="font-size: 18px; line-height: 26px; font-weight: 700">FIT FOR USE</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Balance {BALANCE} · water {D["water"]} °C · next inspection May 2027</span><span>FM-INS-27 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Inspection Z", 794, 1123, FONT, CSS, ROOT + "; padding: 30px 44px 22px 44px; gap: 16px", body)


# ---------------------------------------------------------------- Quick Test: ป้าย 100 × 70 มม.
def quicktest():
    e = (QT["meas"] - QT["set"]) / QT["set"] * 100
    body = f"""
<div style="display: flex; justify-content: space-between; align-items: baseline">
  <span style="font-size: 12px; letter-spacing: .12em; font-weight: 700; color: {K["ink"]}">SYRINGE · QUICK TEST</span>
  <b style="font-size: 15px; font-weight: 700; color: {K["ink"]}">{QT["job"]}</b></div>
<div style="display: flex; justify-content: space-between; align-items: flex-end; border-top: 1.5px solid #161718; border-bottom: 1px solid #161718; padding: 5px 0">
  <div style="display: flex; flex-direction: column"><b style="font-size: 15px; line-height: 19px; font-weight: 700">{D["brand"]} {D["model"]}</b>
  <span style="font-size: 13px; line-height: 17px">S/N {QT["serial"]} · {QT["dept"]}</span></div>
  <span style="font-size: 28px; line-height: 32px; font-weight: 700; letter-spacing: .06em">PASS</span></div>
<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 8px">
  <div style="display: flex; flex-direction: column"><span class="l">5 ml/h error</span><b style="font-size: 18px; line-height: 22px; font-weight: 700">{f(e, 1, True)} %</b></div>
  <div style="display: flex; flex-direction: column"><span class="l">Steady after</span><b style="font-size: 18px; line-height: 22px; font-weight: 700">{mmss(steady(5.0))}</b></div>
  <div style="display: flex; flex-direction: column"><span class="l">Syringe</span><b style="font-size: 14px; line-height: 22px; font-weight: 600">Terumo 50</b></div>
</div>
<span style="font-size: 13px; line-height: 17px">Equivalent start-up delay {mmss(sum(START[5.0]))} min · syringe primed</span>
<div style="margin-top: auto; display: flex; justify-content: space-between" class="l"><span>[Company] · 13 Nov 2026 · limit ±3 %</span><span>by ______</span></div>
<div style="height: 6px; background: {K["fill"]}"></div>
"""
    return dc("Quick Test Z", 378, 265, FONT, CSS, ROOT + "; padding: 12px 16px 10px 16px; gap: 7px; border: 1px solid #161718", body)


def boards():
    return [
        dict(name="Z-Calibration.dc.html", w=794, h=1123, title="Z · Calibration syringe low-rate & start-up", html=calibration()),
        dict(name="Z-Inspection.dc.html", w=794, h=1123, title="Z · Inspection with syringe compatibility", html=inspection()),
        dict(name="Z-QuickTest.dc.html", w=378, h=265, title="Z · Quick Test label 100 × 70 mm", html=quicktest()),
    ]


if __name__ == "__main__":
    for r in D["rates"]:
        print(r["set"], mmss(steady(r["set"])), deficit(r["set"]) * 1000, mmss(sum(START[r["set"]])))
