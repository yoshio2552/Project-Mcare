"""แบบ S — Volume delivery: ปริมาตรสะสมเทียบเส้นอุดมคติ + residual (ml) ที่เห็นจังหวะรอบปั๊ม, ความหมายทางคลินิกใน 24 ชม.
Inspection มีการทดสอบ occlusion + bolus ด้วยตราชั่ง · แนว clinical engineering: หัวข้ออยู่คอลัมน์ซ้าย (sidehead)
"""
import math

from common import (INFUSION as D, INF as K, INF_INSP as II, INF_QT as QT, INK, GREY, RULE, PAPER, BALANCE,
                    f, err, cycle_flows, Ax, T, L, R, PL, PG, C, svg, fonts, dc)

HEADING = "แบบ S — Volume delivery: ปริมาตรสะสมจริงเทียบอุดมคติ + residual (ml) เห็นจังหวะรอบปั๊ม, ผลต่อคนไข้ใน 24 ชม., occlusion และ bolus"
NOTE_FILL = "teal"
NOTE = ("S: พูดเป็น \"ปริมาตรยา\" ที่พยาบาลเข้าใจ — ส่งจริงกี่ ml เทียบที่ตั้ง และใน 24 ชม. ต่างกันเท่าไร\n"
        "residual เป็นฟันเลื่อยตามรอบปั๊ม (ข้อมูลรายรอบที่ DeltaM มีอยู่แล้ว)\n"
        "Inspection: occlusion + bolus หลังปลดสาย วัดด้วยตราชั่ง — โปรแกรมยังไม่มีโหมดนี้")

FONT = fonts("Public+Sans:wght@400;500;600;700", "Noto+Sans+Thai:wght@400;500;600")
ROOT = ("color: #161718; font-family: 'Public Sans', 'Noto Sans Thai', sans-serif; display: flex; "
        "flex-direction: column; font-variant-numeric: tabular-nums lining-nums")
CSS = """
.l{font-size:12px;line-height:16px;color:#5C5F62}
.row{display:grid;grid-template-columns:132px minmax(0,1fr);column-gap:20px;border-top:1px solid #161718;padding-top:8px}
.row>h2{margin:0;font-size:13px;line-height:18px;font-weight:600}
.row>h2 span{display:block;font-weight:400;color:#5C5F62;font-size:12px;line-height:16px;margin-top:2px}
table{border-collapse:collapse;width:100%;font-size:13px;line-height:18px}
th{font-weight:500;color:#5C5F62;font-size:12px;line-height:15px;text-align:right;padding:0 6px 4px 6px;border-bottom:1px solid #161718;vertical-align:bottom}
td{text-align:right;padding:4px 6px;border-bottom:1px solid #DCDCD8}
th:first-child,td:first-child{text-align:left;padding-left:0}
.fig{display:flex;flex-direction:column;gap:2px}
.sig{display:flex;flex-direction:column;gap:2px}
.sig div{height:30px;border-bottom:1px solid #161718}
svg text{font-family:'Public Sans','Noto Sans Thai',sans-serif}
"""

AMP = 0.6      # ความแกว่งของ flow ภายในรอบ (ปั๊ม peristaltic)


def g(x):
    """สัดส่วนปริมาตรที่ส่งแล้วภายในรอบ (0..1) — เพิ่มขึ้นตลอด ไม่ย้อน"""
    return x - AMP / (2 * math.pi) * math.sin(2 * math.pi * x)


def cumulative(flows, period, step=0.5):
    """ปริมาตรสะสม (ml) ทุก step วินาที จาก flow รายรอบ"""
    vols = [q * period / 3600 for q in flows]
    ts, vs, base = [], [], 0.0
    per = int(period / step)
    for i, v in enumerate(vols):
        for k in range(per):
            x = k / per                      # ตำแหน่งในรอบ 0..1 (เวลาจริง = i·คาบ + x·คาบ)
            ts.append((i + x) * period)
            vs.append(base + v * g(x))
        base += v
    ts.append(len(vols) * period)
    vs.append(base)
    return ts, vs


FLOWS = [cycle_flows(r, s) for r, s in zip(D["rates"], (101, 202, 304))]


def vol_rows():
    out = []
    for r in D["rates"]:
        dur = r["n"] * r["period"]
        exp_v, got = r["set"] * dur / 3600, r["meas"] * dur / 3600
        out.append(dict(r=r, dur=dur, exp=exp_v, got=got, dv=got - exp_v, day=(r["meas"] - r["set"]) * 24))
    return out


VR = vol_rows()


def axis_y(ax, ticks, fmt, side="left"):
    out = [L(ax.x0, ax.y0, ax.x0, ax.y1, INK)]
    for v in ticks:
        out.append(L(ax.x0 - 4, ax.sy(v), ax.x0, ax.sy(v), INK))
        out.append(T(ax.x0 - 8, ax.sy(v) + 4, fmt(v), anchor="end"))
    return out


def residual_parts(flows, period, set_rate):
    """residual (ส่งจริง − อุดมคติ, ml): ค่า ณ ปลายแต่ละรอบ + ช่วงแกว่งต่ำสุด/สูงสุดภายในรอบ"""
    ts, vs = cumulative(flows, period)
    per = int(period / 0.5)       # ต้องเท่ากับใน cumulative()
    ends_t, ends_v, hi, lo = [0.0], [0.0], [], []
    for i in range(len(flows)):
        seg = [(ts[k], vs[k] - set_rate * ts[k] / 3600) for k in range(i * per, (i + 1) * per + 1)]
        ends_t.append(seg[-1][0])
        ends_v.append(seg[-1][1])
        mid = (seg[0][0] + seg[-1][0]) / 2
        hi.append((mid, max(v for _, v in seg)))
        lo.append((mid, min(v for _, v in seg)))
    return ts, vs, ends_t, ends_v, hi, lo


def residual_plot(ax, parts, label_end=True):
    ts, vs, et, ev, hi, lo = parts
    band = [(et[0], 0.0)] + hi + [(et[-1], ev[-1])] + lo[::-1]
    out = [PG(" ".join(f"{ax.sx(x):.1f},{ax.sy(y):.1f}" for x, y in band), K["tint"])]
    out.append(L(ax.x0, ax.sy(0), ax.x1, ax.sy(0), K["ink"], 1.5, "6 4"))
    out.append(PL(ax.pts(et, ev), INK, 1.5))
    for x, y in zip(et[1:], ev[1:]):
        out.append(C(ax.sx(x), ax.sy(y), 2, INK))
    if label_end:
        out.append(T(ax.sx(et[-1]) + 6, ax.sy(ev[-1]) + 4, f(ev[-1], 3, True), fill=INK, weight=600))
    return out


def charts(w=554):
    r, vr = D["rates"][1], VR[1]
    parts = residual_parts(FLOWS[1], r["period"], r["set"])
    ts, vs = parts[0], parts[1]
    tmax = ts[-1]
    # A: ปริมาตรสะสม
    a = Ax(48, w - 70, 12, 132, 0, 900, 0, 13)
    out = axis_y(a, [0, 4, 8, 12], lambda v: f"{v:g}")
    out.append(L(a.x0, a.y1, a.x1, a.y1, INK))
    out.append(PL(a.pts([0, tmax], [0, r["set"] * tmax / 3600]), K["ink"], 1.5, dash="6 4"))
    out.append(PL(a.pts(ts[::6], vs[::6]), INK, 2))
    out.append(T(a.sx(tmax) + 6, a.sy(vs[-1]) + 4, f"{vr['got']:.3f}", fill=INK, weight=600))
    out.append(T(a.x0 + 8, a.y0 + 4, "A · delivered volume, ml", fill=INK, weight=600))
    out.append(T(a.x0 + 8, a.y0 + 20, "– – ideal at set rate", fill=K["ink"]))
    # B: residual
    lo_v = min(v for _, v in parts[5]) - 0.01
    hi_v = max(v for _, v in parts[4]) + 0.01
    b = Ax(48, w - 70, 176, 312, 0, 900, lo_v, hi_v)
    ticks = [v / 100 for v in range(-10, 30, 5) if lo_v <= v / 100 <= hi_v]
    out += axis_y(b, ticks, lambda v: f(v, 2, True) if v else "0")
    out += residual_plot(b, parts)
    out.append(T(b.x0 + 8, b.y0 + 4, "B · delivered − ideal, ml", fill=INK, weight=600))
    out.append(T(b.x0 + 8, b.y0 + 20, "● end of each pump cycle · shaded = swing within the cycle", fill=GREY))
    out.append(L(b.x0, b.y1, b.x1, b.y1, INK))
    for t in range(0, 901, 180):
        out.append(T(b.sx(t), b.y1 + 18, f"{t // 60}", anchor="middle"))
        out.append(T(a.sx(t), a.y1 + 18, f"{t // 60}", anchor="middle"))
    out.append(T(b.x1, b.y1 + 34, "time, min", anchor="end"))
    return svg(w, 348, f"Delivered volume at 50 ml/h reaches {vr['got']:.3f} ml against {vr['exp']:.3f} ml ideal", out)


def head(title, sub, no_label, no):
    return f"""
<header style="display: flex; justify-content: space-between; align-items: flex-start; gap: 24px">
  <div style="display: flex; flex-direction: column; gap: 4px">
    <span class="l">[Company Name] · Medical Equipment Calibration</span>
    <span style="font-size: 28px; line-height: 34px; font-weight: 700; letter-spacing: -.015em">{title}</span>
    <span style="font-size: 13px; line-height: 18px; color: #3E4143">{sub}</span>
  </div>
  <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 2px; text-align: right">
    <span style="font-size: 26px; line-height: 30px; font-weight: 700; color: {K["ink"]}">{D["job"]}</span>
    <span style="font-size: 13px; line-height: 18px">{no_label} {no}</span>
    <span class="l">{D["date"]} · page 1 / 1</span>
  </div>
</header>
<div style="display: grid; grid-template-columns: 1.1fr 1fr 1.3fr 1fr; column-gap: 16px; background: {PAPER}; padding: 10px 14px; font-size: 13px; line-height: 18px">
  <div style="display: flex; flex-direction: column"><span class="l">Infusion pump</span><b style="font-weight: 600">{D["brand"]} {D["model"]}</b></div>
  <div style="display: flex; flex-direction: column"><span class="l">Serial · asset</span><span style="white-space: nowrap">{D["serial"]} · {D["asset"]}</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Customer</span><span>{D["site"]} · {D["dept"]}</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Infusion set</span><span>{D["set_label"]}</span></div>
</div>"""


def calibration():
    rows = "".join(f"""<tr><td>{v["r"]["set"]:.1f}</td><td>{v["dur"] / 60:.1f}</td><td>{v["exp"]:.3f}</td><td>{v["got"]:.3f}</td>
<td>{f(v["dv"], 3, True)}</td><td>{f(err(v["r"]), 1, True)} %</td><td>{v["r"]["U"]:.1f} %</td><td><b style="font-weight: 600">Pass</b></td></tr>"""
                   for v in VR)
    day = "".join(f"""<tr><td>{v["r"]["set"]:.0f} ml/h</td><td>{v["r"]["set"] * 24:,.0f}</td><td>{v["r"]["meas"] * 24:,.0f}</td>
<td><b style="font-weight: 600">{f(v["day"], 0, True)} ml</b></td></tr>""" for v in VR)
    body = f"""
{head("Calibration certificate", "volume delivery record · ใบรับรองผลการสอบเทียบ แสดงปริมาตรที่ส่งจริง", "Certificate", D["cert"])}
<div class="row"><h2>Results<span>gravimetric, whole pump cycles</span></h2>
<table><thead><tr><th>Set ml/h</th><th>Run min</th><th>Ideal ml</th><th>Delivered ml</th><th>Difference ml</th><th>Error</th><th>U, k=2</th><th>Result</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<div class="row"><h2>Volume record<span>50 ml/h · {D["rates"][1]["n"]} cycles</span></h2>
<div style="display: flex; flex-direction: column; gap: 6px">
  {charts(554)}
  <p style="margin: 0; font-size: 13px; line-height: 19px">A hides the error at full scale; B shows it: the pump delivers in pulses and gains
  <b style="font-weight: 600">{f(VR[1]["dv"], 3, True)} ml</b> over {VR[1]["dur"] / 60:.1f} min ({f(err(D["rates"][1]), 1, True)} %).</p>
</div></div>
<div class="row"><h2>Over 24 hours<span>what the error means at the bedside</span></h2>
<div style="display: flex; flex-direction: column; gap: 6px">
<table><thead><tr><th>Set rate</th><th>Ordered ml</th><th>Delivered ml</th><th>Difference</th></tr></thead><tbody>{day}</tbody></table>
<p style="margin: 0; font-size: 13px; line-height: 19px">ปริมาตรที่ส่งจริงใน 24 ชม. เมื่อตั้งอัตราคงที่ — ทุกค่าอยู่ในเกณฑ์ ±{D["limit"]:.0f} %</p>
</div></div>
<div class="row"><h2>Method<span>ISO/IEC 17025 §7.8</span></h2>
<p style="margin: 0; font-size: 13px; line-height: 19px">Gravimetric [WI-CAL-01], IEC 60601-2-24:2012, ISO 4787:2021. Balance {BALANCE} (cert. [—]), traceable to SI.
Water {D["water"]} °C, {D["rh"]} %RH, {D["hpa"]} hPa. Volume = mass × Z (ISO 4787). Simple acceptance, ILAC-G8. Conforms at all rates.</p></div>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 150px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["operator"]}</b><span class="l">Calibrated by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["approver"]}</b><span class="l">Approved by</span></div>
  <div style="background: #161718; color: #ffffff; padding: 10px; display: flex; flex-direction: column; align-items: center">
    <span style="font-size: 12px; color: #C9CACB">result</span><span style="font-size: 24px; line-height: 30px; font-weight: 700; letter-spacing: .08em">PASS</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Reproduce in full only · results relate only to the item calibrated</span><span>FM-CAL-19 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Calibration S", 794, 1123, FONT, CSS, ROOT + "; padding: 32px 44px 26px 44px; gap: 14px", body)


# ---------------------------------------------------------------- Inspection: occlusion + bolus
OCC = dict(rate=25.0, clamp=60.0, alarm=52.0, release=150.0, bolus=0.12, level="M")


def occlusion_chart(w=706):
    """มวลบนตราชั่งระหว่างทดสอบ: ไหลปกติ → หนีบสาย (หยุดไหล) → เตือน → ปลด → bolus กระโดดขึ้น"""
    q = OCC["rate"] / 3600
    ts = [i * 0.5 for i in range(0, 481)]
    ms = []
    for t in ts:
        if t < OCC["clamp"]:
            m = q * t
        elif t < OCC["release"]:
            m = q * OCC["clamp"]
        else:
            dt = t - OCC["release"]
            m = q * OCC["clamp"] + OCC["bolus"] * (1 - math.exp(-dt / 1.6)) + q * dt
        ms.append(m)
    ax = Ax(56, w - 80, 16, 260, 0, 240, 0, 1.4)
    out = [R(ax.sx(OCC["clamp"]), ax.y0, ax.sx(OCC["release"]) - ax.sx(OCC["clamp"]), ax.y1 - ax.y0, PAPER)]
    out += axis_y(ax, [0, 0.4, 0.8, 1.2], lambda v: f"{v:.1f}")
    out.append(L(ax.x0, ax.y1, ax.x1, ax.y1, INK))
    out.append(PL(ax.pts(ts, ms), INK, 2))
    out.append(PL(ax.pts([0, 1.4 / q], [0, 1.4]), K["ink"], 1.5, dash="6 4"))   # ตัดที่ขอบบนกราฟ
    ta = OCC["clamp"] + OCC["alarm"]
    for x, lab in ((OCC["clamp"], "clamp"), (ta, "alarm"), (OCC["release"], "release")):
        out.append(L(ax.sx(x), ax.y0, ax.sx(x), ax.y1, INK, 1, "2 3"))
        out.append(T(ax.sx(x) + 4, ax.y0 + 10, lab, fill=INK, weight=600))
    out.append(L(ax.sx(OCC["clamp"]), ax.y1 - 14, ax.sx(ta), ax.y1 - 14, INK))
    out.append(T((ax.sx(OCC["clamp"]) + ax.sx(ta)) / 2, ax.y1 - 20, f"{OCC['alarm']:.0f} s to alarm", anchor="middle", fill=INK))
    base = q * OCC["clamp"]
    xb = ax.sx(OCC["release"] + 14)
    out.append(L(xb, ax.sy(base), xb, ax.sy(base + OCC["bolus"]), INK, 1.5))
    for y in (base, base + OCC["bolus"]):
        out.append(L(xb - 4, ax.sy(y), xb + 4, ax.sy(y), INK, 1.5))
    out.append(T(xb + 8, ax.sy(base + OCC["bolus"] / 2) + 4, f"bolus {OCC['bolus']:.2f} ml", fill=INK, weight=600))
    for t in range(0, 241, 30):
        out.append(T(ax.sx(t), ax.y1 + 18, f"{t}", anchor="middle"))
    out.append(T(ax.x1, ax.y1 + 34, "time, s · – – flow without occlusion", anchor="end"))
    out.append(T(ax.x0 - 8, ax.y0 - 4, "ml", anchor="end"))
    return svg(w, 298, "Volume on the balance during occlusion test: flat while clamped, bolus step after release", out)


CHECKS = [("Housing, labels, IFU", "OK"), ("Pole clamp and handle", "OK"), ("Power cord and plug", "OK"),
          ("Keypad, display, indicators", "OK"), ("Door and tube guide", "OK"), ("Air-in-line detector", "OK"),
          ("Battery operation ≥ 30 min", "OK"), ("Audible and visual alarms", "OK"), ("Nurse call", "N/A"),
          ("Electrical safety IEC 62353", "N/P")]


def inspection():
    e = err(II)
    ck = "".join(f'<div style="display: flex; justify-content: space-between; border-bottom: 1px solid #DCDCD8; padding: 3px 0">'
                 f'<span>{a}</span><b style="font-weight: 600{"" if b == "OK" else "; color: #5C5F62"}">{b}</b></div>' for a, b in CHECKS)
    vol = II["meas"] * II["n"] * II["period"] / 3600
    body = f"""
{head("Inspection report", "with occlusion and bolus test · รายงานการตรวจสภาพ พร้อมทดสอบการอุดตันและ bolus", "Report", D["insp"])}
<div class="row"><h2>Checks<span>10 items · 8 OK</span></h2>
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 24px; font-size: 13px; line-height: 18px">{ck}</div></div>
<div class="row"><h2>Occlusion and bolus<span>IEC 60601-2-24 · set {OCC["rate"]:.0f} ml/h, level {OCC["level"]}</span></h2>
<div style="display: flex; flex-direction: column; gap: 8px">
<table><thead><tr><th>Quantity</th><th>Found</th><th>Criterion</th><th>Result</th></tr></thead><tbody>
<tr><td>Time from clamp to occlusion alarm</td><td>{OCC["alarm"]:.0f} s</td><td>≤ [mfr spec] s</td><td><b style="font-weight: 600">OK</b></td></tr>
<tr><td>Bolus released after clamp is opened</td><td>{OCC["bolus"]:.2f} ml</td><td>≤ [mfr spec] ml</td><td><b style="font-weight: 600">OK</b></td></tr>
<tr><td>Flow resumes after release</td><td>yes</td><td>yes</td><td><b style="font-weight: 600">OK</b></td></tr></tbody></table>
{occlusion_chart(554)}
</div></div>
<div class="row"><h2>Flow check<span>{II["set"]:.0f} ml/h · {II["minutes"]} min</span></h2>
<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); column-gap: 16px; font-size: 13px; line-height: 18px">
  <div style="display: flex; flex-direction: column"><span class="l">Ideal volume</span><b style="font-size: 20px; line-height: 26px; font-weight: 600">{II["set"] * II["n"] * II["period"] / 3600:.3f} ml</b></div>
  <div style="display: flex; flex-direction: column"><span class="l">Delivered</span><b style="font-size: 20px; line-height: 26px; font-weight: 600">{vol:.3f} ml</b></div>
  <div style="display: flex; flex-direction: column"><span class="l">Flow</span><b style="font-size: 20px; line-height: 26px; font-weight: 600">{II["meas"]:.2f} ml/h</b></div>
  <div style="display: flex; flex-direction: column"><span class="l">Error · limit ±{D["limit"]:.0f} %</span><b style="font-size: 20px; line-height: 26px; font-weight: 600">{f(e, 1, True)} %</b></div>
</div></div>
<div class="row"><h2>How it is measured<span>gravimetric bolus</span></h2>
<p style="margin: 0; font-size: 13px; line-height: 19px">The line is clamped below the pump while the balance records. Bolus = volume step in the
first 30 s after release minus what the set rate would deliver in that time (mass × Z). Occlusion pressure is not measured: no transducer in the
set-up. Criteria come from the manufacturer's service manual [ref.].</p></div>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 170px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Technician name]</b><span class="l">Inspected by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Ward representative]</b><span class="l">Received by</span></div>
  <div style="background: #161718; color: #ffffff; padding: 10px; display: flex; flex-direction: column; align-items: center">
    <span style="font-size: 12px; color: #C9CACB">status</span><span style="font-size: 18px; line-height: 26px; font-weight: 700; letter-spacing: .04em">FIT FOR USE</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Balance {BALANCE} · water {D["water"]} °C · next inspection May 2027</span><span>FM-INS-19 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Inspection S", 794, 1123, FONT, CSS, ROOT + "; padding: 36px 44px 28px 44px; gap: 16px", body)


# ---------------------------------------------------------------- Quick Test: A5 แนวตั้ง
QT_FLOWS = cycle_flows(dict(n=QT["n"], meas=QT["meas"], sd2=2.4), 505)


def quicktest():
    dur = QT["n"] * QT["period"]
    exp_v, got = QT["set"] * dur / 3600, QT["meas"] * dur / 3600
    parts = residual_parts(QT_FLOWS, QT["period"], QT["set"])
    ts = parts[0]
    w = 491
    lo_v = min(v for _, v in parts[5]) - 0.008
    hi_v = max(v for _, v in parts[4]) + 0.012
    ax = Ax(52, w - 66, 34, 330, 0, ts[-1], lo_v, hi_v)
    out = [L(ax.x0, ax.y0, ax.x0, ax.y1, INK)]
    for v in (-0.03, -0.02, -0.01, 0, 0.01, 0.02):
        if lo_v <= v <= hi_v:
            out.append(T(ax.x0 - 8, ax.sy(v) + 4, f(v, 2, True) if v else "0", anchor="end"))
            out.append(L(ax.x0 - 4, ax.sy(v), ax.x0, ax.sy(v), INK))
    out += residual_plot(ax, parts)
    out.append(L(ax.x0, ax.y1, ax.x1, ax.y1, INK))
    for t in (0, 60, 120, 180):
        out.append(T(ax.sx(t), ax.y1 + 18, f"{t}", anchor="middle"))
    out.append(T(ax.x1, ax.y1 + 34, "time, s", anchor="end"))
    out.append(T(ax.x0 + 8, 12, "delivered − ideal, ml", fill=INK, weight=600))
    out.append(T(ax.x0 + 8, 28, "● end of each pump cycle · shaded = swing within the cycle", fill=GREY))
    chart = svg(w, 370, f"Difference from ideal volume over {QT['minutes']} min", out)
    e = (QT["meas"] - QT["set"]) / QT["set"] * 100
    body = f"""
<header style="display: flex; justify-content: space-between; align-items: flex-start">
  <div style="display: flex; flex-direction: column; gap: 2px"><span class="l">[Company Name]</span>
  <span style="font-size: 22px; line-height: 28px; font-weight: 700">Quick volume test</span></div>
  <div style="text-align: right; display: flex; flex-direction: column"><span style="font-size: 20px; line-height: 24px; font-weight: 700; color: {K["ink"]}">{QT["job"]}</span>
  <span class="l">{QT["no"]} · {QT["date"]}</span></div>
</header>
<div style="background: {PAPER}; padding: 8px 12px; font-size: 13px; line-height: 18px">{D["brand"]} {D["model"]} · S/N {QT["serial"]} · {D["site"]} {QT["dept"]}</div>
<div style="display: flex; flex-direction: column; gap: 2px">
  <span class="l">Delivered in {QT["n"]} pump cycles ({dur:.0f} s) at {QT["set"]:.0f} ml/h</span>
  <span style="font-size: 44px; line-height: 50px; font-weight: 700; letter-spacing: -.02em">{got:.3f} <span style="font-size: 20px">ml</span></span>
  <span style="font-size: 14px; line-height: 20px">of {exp_v:.3f} ml ideal · <b style="font-weight: 600">{f(got - exp_v, 3, True)} ml</b> · {f(e, 1, True)} % · limit ±{D["limit"]:.0f} %</span>
</div>
{chart}
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 130px; column-gap: 20px; align-items: end">
  <div class="sig"><div></div><span class="l">Tested by · [Technician] · balance {BALANCE}</span></div>
  <div style="background: #161718; color: #ffffff; padding: 8px; display: flex; flex-direction: column; align-items: center">
    <span style="font-size: 12px; color: #C9CACB">result</span><span style="font-size: 22px; line-height: 28px; font-weight: 700; letter-spacing: .08em">PASS</span></div>
</div>
<span class="l">Screening only, {QT["n"]} whole pump cycles. Does not replace calibration. FM-QT-19.</span>
"""
    return dc("Quick Test S", 559, 794, FONT, CSS, ROOT + "; padding: 28px 34px 22px 34px; gap: 14px", body)


def boards():
    return [
        dict(name="S-Calibration.dc.html", w=794, h=1123, title="S · Calibration volume delivery", html=calibration()),
        dict(name="S-Inspection.dc.html", w=794, h=1123, title="S · Inspection occlusion & bolus", html=inspection()),
        dict(name="S-QuickTest.dc.html", w=559, h=794, title="S · Quick volume test (A5)", html=quicktest()),
    ]
