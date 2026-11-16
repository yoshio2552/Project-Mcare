"""แบบ X — Cycle fingerprint: ซ้อนทุกรอบปั๊มเป็นรูปคลื่นเดียว (phase-folded) + Poincaré plot ของคาบรอบ + ปริมาตรต่อรอบเทียบโปรไฟล์
ลายพิมพ์ของกลไกปั๊ม — เทียบกับรุ่นเดียวกันเพื่อจับสายยาง/นิ้วกดสึกก่อน error จะหลุดเกณฑ์ · ตัวอย่าง Infusion
"""
import math

from common import (INFUSION as D, INF as K, INF_INSP as II, INF_QT as QT, INK, GREY, RULE, PAPER, BALANCE,
                    f, err, cycle_flows, series, mean, sd, Rng, Ax, T, L, R, PL, PG, C, svg, fonts, dc)

HEADING = "แบบ X — Cycle fingerprint: ซ้อนทุกรอบปั๊มเป็นรูปคลื่นเดียว + Poincaré plot ของคาบรอบ + ปริมาตรต่อรอบเทียบโปรไฟล์ของรุ่น"
NOTE_FILL = "purple"
NOTE = ("X: ใช้จุดเด่นของ DeltaM (จับรอบปั๊มได้) ทำ \"ลายพิมพ์\" ของกลไกปั๊ม\n"
        "รูปคลื่นเฉลี่ยของเครื่องนี้เทียบกับของรุ่น → เห็นสายยาง/นิ้วกดสึกก่อน error หลุดเกณฑ์\n"
        "ข้อมูลมีอยู่แล้ว (สัญญาณดิบ + จุด peak) ต้องเพิ่มการพับเฟสและเก็บรูปคลื่นอ้างอิงในโปรไฟล์รุ่น")

FONT = fonts("Red+Hat+Text:wght@400;500;600;700", "Red+Hat+Mono:wght@400;500", "Noto+Sans+Thai:wght@400;500;600")
ROOT = ("color: #161718; font-family: 'Red Hat Text', 'Noto Sans Thai', sans-serif; display: flex; flex-direction: column; "
        "font-variant-numeric: tabular-nums lining-nums")
CSS = """
.l{font-size:12px;line-height:16px;color:#5C5F62}
.m{font-family:'Red Hat Mono',monospace}
h2{margin:0;font-size:15px;line-height:20px;font-weight:600}
.hd{display:flex;justify-content:space-between;align-items:baseline;gap:16px}
table{border-collapse:collapse;width:100%;font-size:13px;line-height:18px}
th{font-weight:500;color:#5C5F62;font-size:12px;text-align:right;padding:3px 6px;border-bottom:1.5px solid #161718}
td{text-align:right;padding:4px 6px;border-bottom:1px solid #DCDCD8}
th:first-child,td:first-child{text-align:left;padding-left:0}
p{margin:0}
.sig{display:flex;flex-direction:column;gap:2px}
.sig div{height:28px;border-bottom:1px solid #161718}
svg text{font-family:'Red Hat Text','Noto Sans Thai',sans-serif}
"""

N_PH = 120


def shape(x, wear=0.0):
    """รูปคลื่น flow ภายในหนึ่งรอบ (สัดส่วนของ flow เฉลี่ย) — มีช่วงไหลย้อนสั้น ๆ ตอนนิ้วกดยกขึ้น
    wear = ความสึก: ยอดต่ำลง ช่วงไหลย้อนลึกและยาวขึ้น"""
    base = 1 + (0.55 - 0.15 * wear) * math.sin(2 * math.pi * x - 1.0) + 0.18 * math.sin(4 * math.pi * x + 0.4)
    dip = (0.42 + 0.3 * wear) * math.exp(-((x - 0.86) / (0.045 + 0.02 * wear)) ** 2)
    return base - dip


def norm_wave(wear=0.0):
    xs = [i / N_PH for i in range(N_PH + 1)]
    ys = [shape(x, wear) for x in xs]
    m = sum(ys[:-1]) / N_PH
    return xs, [y / m for y in ys]


XS, WAVE = norm_wave()
_, REF_WAVE = norm_wave(0.08)        # รูปคลื่นอ้างอิงของรุ่น (ค่าเฉลี่ยหลายเครื่อง)


def cycles(flows, seed):
    """รูปคลื่นของแต่ละรอบ = flow ของรอบ × รูปคลื่นมาตรฐาน + สัญญาณรบกวน/เฟสคลาดเล็กน้อย"""
    rng, out = Rng(seed), []
    for q in flows:
        shift = 0.01 * rng.g()
        amp = 1 + 0.05 * rng.g()
        ys = []
        for x in XS:
            xx = (x + shift) % 1
            ys.append(q * (1 + amp * (shape(xx) / (sum(shape(i / N_PH) for i in range(N_PH)) / N_PH) - 1)) + 1.2 * rng.g())
        out.append(ys)
    return out


R50 = D["rates"][1]
FL50 = cycle_flows(R50, 202)
CYC = cycles(FL50, 515)
PERIODS = series(R50["n"], R50["period"], 0.07, 626, ar=0.35)


def band(ax, xs, lo, hi, fill):
    pts = [f"{ax.sx(x):.1f},{ax.sy(y):.1f}" for x, y in zip(xs, hi)] + \
          [f"{ax.sx(x):.1f},{ax.sy(y):.1f}" for x, y in zip(xs[::-1], lo[::-1])]
    return PG(" ".join(pts), fill)


def fingerprint(w=706, h=300, cyc=CYC, period=R50["period"], q=R50["meas"], ref=False, label=True):
    ax = Ax(52, w - 150, 14, h - 40, 0, 1, -0.3 * q, 2.1 * q)
    out = [L(ax.x0, ax.y0, ax.x0, ax.y1, INK), L(ax.x0, ax.sy(0), ax.x1, ax.sy(0), INK)]
    step = 25 if q > 30 else 10
    for v in range(0, int(2.1 * q) + 1, step):
        out.append(L(ax.x0 - 4, ax.sy(v), ax.x0, ax.sy(v), INK))
        out.append(T(ax.x0 - 8, ax.sy(v) + 4, f"{v}", anchor="end"))
    n = len(cyc)
    mu = [mean([c[i] for c in cyc]) for i in range(len(XS))]
    s2 = [2 * sd([c[i] for c in cyc]) for i in range(len(XS))]
    out.append(band(ax, XS, [m - s for m, s in zip(mu, s2)], [m + s for m, s in zip(mu, s2)], K["tint"]))
    for c in cyc:
        out.append(PL(ax.pts(XS[::2], c[::2]), "#B5B8BA", 1))
    if ref:
        out.append(PL(ax.pts(XS, [q * v for v in REF_WAVE]), K["ink"], 1.5, dash="6 4"))
    out.append(PL(ax.pts(XS, mu), INK, 2.2))
    out.append(L(ax.x0, ax.sy(q), ax.x1, ax.sy(q), INK, 1, "2 3"))
    out.append(T(ax.x1 + 8, ax.sy(q) + 4, f"mean {q:.2f}", fill=INK, weight=600))
    ipk = max(range(len(mu)), key=lambda i: mu[i])
    imn = min(range(len(mu)), key=lambda i: mu[i])
    out.append(T(ax.x1 + 8, ax.sy(mu[ipk]) + 4, f"peak {mu[ipk]:.0f}", fill=INK))
    out.append(T(ax.x1 + 8, ax.sy(mu[imn]) + 4, f"min {f(mu[imn], 0)}", fill=INK))
    if label:
        out.append(T(ax.sx(XS[imn]) - 14, ax.sy(mu[imn]) + 4, "brief back-flow as the finger lifts →", anchor="end", fill=GREY))
    for k in range(0, 5):
        x = k / 4
        out.append(L(ax.sx(x), ax.y1, ax.sx(x), ax.y1 + 4, INK))
        out.append(T(ax.sx(x), ax.y1 + 18, f"{x * period:.1f}" if k else "0", anchor="end" if k == 4 else "middle"))
    out.append(T(ax.x1, ax.y1 + 34, f"time within one cycle, s (period {period} s)", anchor="end"))
    out.append(T(ax.x0 + 8, ax.y0 + 4, "flow, ml/h", fill=INK, weight=600))
    leg = f"grey: each of {n} cycles · black: mean · shaded: ±2SD" + (" · – – model reference" if ref else "")
    out.append(T(ax.x0 + 8, ax.y0 + 20, leg, fill=GREY))
    return svg(w, h, f"{n} pump cycles folded onto one cycle, mean flow {q:.2f} ml/h", out)


def poincare(w=270):
    ps = PERIODS
    lo, hi = min(ps) - 0.06, max(ps) + 0.06
    ax = Ax(52, w - 12, 10, w - 52, lo, hi, lo, hi)
    out = [R(ax.x0, ax.y0, ax.x1 - ax.x0, ax.y1 - ax.y0, "#ffffff", INK)]
    out.append(L(ax.x0, ax.y1, ax.x1, ax.y0, RULE, 1))
    xs, ys = ps[:-1], ps[1:]
    d1 = [(b - a) / math.sqrt(2) for a, b in zip(xs, ys)]
    d2 = [(b + a) / math.sqrt(2) for a, b in zip(xs, ys)]
    sd1, sd2 = sd(d1), sd(d2)
    cx = cy = mean(ps)
    # วงรี SD1/SD2 หมุน 45°
    pts = []
    for k in range(73):
        t = 2 * math.pi * k / 72
        u, v = 2 * sd2 * math.cos(t), 2 * sd1 * math.sin(t)
        pts.append(f"{ax.sx(cx + (u - v) / math.sqrt(2)):.1f},{ax.sy(cy + (u + v) / math.sqrt(2)):.1f}")
    out.append(PG(" ".join(pts), K["tint"], K["ink"]))
    for a, b in zip(xs, ys):
        out.append(C(ax.sx(a), ax.sy(b), 2.6, INK))
    for v in [t / 10 for t in range(int(lo * 10) + 1, int(hi * 10) + 1)]:
        out.append(T(ax.sx(v), ax.y1 + 16, f"{v:.1f}", anchor="middle"))
        out.append(T(ax.x0 - 6, ax.sy(v) + 4, f"{v:.1f}", anchor="end"))
    out.append(T(ax.x1, ax.y1 + 32, "period n, s", anchor="end"))
    out.append(T(ax.x0 + 6, ax.y0 + 14, "period n + 1, s", fill=INK))
    return svg(w, w - 16, f"Poincare plot of successive pump periods, SD1 {sd1:.3f} s, SD2 {sd2:.3f} s", out), sd1, sd2


PROFILE = [0.197, 0.212, 0.212]      # ปริมาตรต่อรอบที่เก็บในโปรไฟล์ TE-171 + ชุดสายนี้ (ml)


def vol_strip(w=380):
    rows = []
    out = []
    ax = Ax(70, w - 60, 0, 0, 0.180, 0.230, 0, 1)
    for i, (r, prof, seed) in enumerate(zip(D["rates"], PROFILE, (101, 202, 304))):
        fl = cycle_flows(r, seed)
        vols = [q * r["period"] / 3600 for q in fl]
        y = 12 + i * 52
        out.append(R(ax.sx(prof * 0.97), y, ax.sx(prof * 1.03) - ax.sx(prof * 0.97), 30, K["tint"]))
        out.append(L(ax.sx(prof), y - 2, ax.sx(prof), y + 32, K["ink"], 1.5, "4 3"))
        rng = Rng(31 + i)
        for v in vols:
            out.append(C(ax.sx(max(0.181, min(0.229, v))), y + 15 + 9 * rng.u(), 1.8 if len(vols) > 100 else 2.4, "#6E7174"))
        mv = mean(vols)
        out.append(L(ax.sx(mv), y - 2, ax.sx(mv), y + 32, INK, 2))
        out.append(T(0, y + 13, f"{r['set']:g} ml/h", fill=INK, weight=600))
        out.append(T(0, y + 29, f"{len(vols)} cycles", fill=GREY))
        out.append(T(ax.x1 + 8, y + 13, f"{mv:.4f}", fill=INK, weight=600))
        out.append(T(ax.x1 + 8, y + 29, f"{(mv / prof - 1) * 100:+.1f} %".replace("-", "−"), fill=GREY))
        rows.append(mv)
    yb = 12 + 3 * 52
    for v in (0.19, 0.20, 0.21, 0.22):
        out.append(T(ax.sx(v), yb + 4, f"{v:.2f}", anchor="middle"))
    out.append(T(ax.x1, yb + 20, "ml per cycle · – – profile ± 3 %", anchor="end"))
    return svg(w, yb + 26, "Volume per pump cycle at each rate against the stored profile", out), rows


def header(title, sub, no_label, no):
    return f"""
<header style="display: flex; justify-content: space-between; align-items: flex-end; gap: 20px; border-bottom: 1.5px solid #161718; padding-bottom: 10px">
  <div style="display: flex; flex-direction: column"><span class="l">[Company Name] · Calibration Laboratory</span>
  <span style="font-size: 28px; line-height: 34px; font-weight: 700; letter-spacing: -.01em">{title}</span>
  <span style="font-size: 13px; line-height: 18px; color: #3E4143">{sub}</span></div>
  <div class="m" style="text-align: right; font-size: 13px; line-height: 19px">{no_label} {no}<br><b style="color: {K["ink"]}; font-weight: 500">{D["job"]}</b> · {D["date"]}<br><span class="l" style="font-family: 'Red Hat Text'">{D["brand"]} {D["model"]} · S/N {D["serial"]} · {D["dept"]}</span></div>
</header>"""


def calibration():
    pc_svg, sd1, sd2 = poincare()
    vs_svg, vols = vol_strip()
    rows = "".join(f"""<tr><td>{r["set"]:.1f}</td><td>{r["meas"]:.2f}</td><td>{f(err(r), 1, True)} %</td><td>{r["U"]:.1f} %</td>
<td>{r["n"]}</td><td>{r["period"]} s</td><td>{v:.4f} ml</td><td><b style="font-weight: 600">Pass</b></td></tr>""" for r, v in zip(D["rates"], vols))
    body = f"""
{header("Calibration certificate", "with pump cycle fingerprint · ใบรับรองพร้อมลายพิมพ์รอบปั๊ม", "No.", D["cert"])}
<table><thead><tr><th>Set ml/h</th><th>Measured ml/h</th><th>Error</th><th>U, k = 2</th><th>Cycles</th><th>Period</th><th>Volume / cycle</th><th>Result</th></tr></thead><tbody>{rows}</tbody></table>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>A · Fingerprint at 50 ml/h</h2><span class="l">every cycle cut peak to peak by DeltaM, then laid on top of each other</span></div>
  {fingerprint(706, 270)}
</section>
<section style="display: grid; grid-template-columns: 270px minmax(0, 1fr); column-gap: 26px">
  <div style="display: flex; flex-direction: column; gap: 6px"><h2>B · Rhythm</h2>{pc_svg}
  <p class="l">Each dot is one cycle against the next. A tight round cloud on the diagonal = steady drive. SD1 {sd1:.3f} s · SD2 {sd2:.3f} s.</p></div>
  <div style="display: flex; flex-direction: column; gap: 6px"><h2>C · Volume per cycle vs stored profile</h2>{vs_svg}
  <p class="l">Profile of {D["model"]} with this infusion set. A worn pumping segment shows here first: smaller volume per cycle, then a negative flow error.</p></div>
</section>
<p style="font-size: 13px; line-height: 19px">Gravimetric [WI-CAL-01], IEC 60601-2-24:2012, ISO 4787:2021. Balance {BALANCE}, cert. [—], traceable to SI. Water {D["water"]} °C,
{D["rh"]} %RH, {D["hpa"]} hPa. U at k = 2. Limit ±{D["limit"]:.0f} %, simple acceptance (ILAC-G8): conforms at all rates.</p>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 150px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["operator"]}</b><span class="l">Calibrated by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["approver"]}</b><span class="l">Approved by</span></div>
  <div style="background: #161718; color: #ffffff; padding: 8px; text-align: center; display: flex; flex-direction: column"><span style="font-size: 12px; color: #C9CACB">result</span><span style="font-size: 24px; line-height: 30px; font-weight: 700; letter-spacing: .08em">PASS</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Reproduce in full only · page 1 / 1</span><span class="m">FM-CAL-25 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Calibration X", 794, 1123, FONT, CSS, ROOT + "; padding: 30px 44px 22px 44px; gap: 14px", body)


# ---------------------------------------------------------------- Inspection: เทียบลายพิมพ์กับรุ่น
FL25 = series(II["n"], II["meas"], II["meas"] * 0.011, 404, ar=0.1)
CYC25 = cycles(FL25, 717)
CHECKS = [("Housing, labels, IFU", "OK"), ("Pole clamp and handle", "OK"), ("Power cord and plug", "OK"),
          ("Keypad, display, indicators", "OK"), ("Door and tube guide", "OK"), ("Air-in-line detector", "OK"),
          ("Occlusion alarm, downstream", "OK"), ("Occlusion alarm, upstream", "OK"), ("Battery ≥ 30 min", "OK"),
          ("Audible and visual alarms", "OK"), ("Nurse call", "N/A"), ("Electrical safety IEC 62353", "N/P")]


def corr(a, b):
    ma, mb = mean(a), mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return num / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))


def inspection():
    e = err(II)
    mu = [mean([c[i] for c in CYC25]) for i in range(len(XS))]
    ref = [II["meas"] * v for v in REF_WAVE]
    r = corr(mu, ref)
    vol = II["meas"] * II["period"] / 3600
    half = len(CHECKS) // 2
    ck = lambda rows: "".join(f'<tr><td>{a}</td><td style="{"" if b == "OK" else "color: #5C5F62"}"><b style="font-weight: 600">{b}</b></td></tr>' for a, b in rows)
    body = f"""
{header("Inspection report", "with fingerprint check against the model · รายงานการตรวจสภาพ", "No.", D["insp"])}
<section style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 28px">
  <table><tbody>{ck(CHECKS[:half])}</tbody></table><table><tbody>{ck(CHECKS[half:])}</tbody></table>
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>Flow check and fingerprint · {II["set"]:g} ml/h · {II["minutes"]} min</h2><span class="l">{II["n"]} cycles vs {D["model"]} reference waveform (32 devices)</span></div>
  {fingerprint(706, 360, CYC25, II["period"], II["meas"], ref=True, label=True)}
  <p class="l">A worn pumping segment or a different infusion set changes this shape before the flow error leaves the limit: the peak drops,
  the back-flow gets deeper and the similarity r falls. The reference is the mean waveform of 32 {D["model"]} pumps with the same set.</p>
</section>
<table><thead><tr><th>Quantity</th><th>This device</th><th>{D["model"]} reference</th><th>Watch when</th><th>Result</th></tr></thead><tbody>
<tr><td>Flow error · limit ±{D["limit"]:.0f} %</td><td>{f(e, 1, True)} %</td><td>{f(0.3, 1, True)} ± 1.6 %</td><td>outside limit</td><td><b style="font-weight: 600">OK</b></td></tr>
<tr><td>Period</td><td>{II["period"]} s</td><td>30.2 s</td><td>± 3 %</td><td><b style="font-weight: 600">OK</b></td></tr>
<tr><td>Volume per cycle</td><td>{vol:.4f} ml</td><td>0.2120 ml</td><td>below −3 %</td><td><b style="font-weight: 600">OK</b></td></tr>
<tr><td>Shape similarity, r</td><td>{r:.3f}</td><td>1.000</td><td>below 0.95</td><td><b style="font-weight: 600">OK</b></td></tr>
<tr><td>Deepest back-flow</td><td>{f(min(mu), 1)} ml/h</td><td>{f(min(ref), 1)} ml/h</td><td>below −20 % of mean</td><td><b style="font-weight: 600">OK</b></td></tr>
</tbody></table>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 170px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Technician name]</b><span class="l">Inspected by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Ward representative]</b><span class="l">Received by</span></div>
  <div style="background: #161718; color: #ffffff; padding: 8px; text-align: center; display: flex; flex-direction: column"><span style="font-size: 12px; color: #C9CACB">status · next May 2027</span><span style="font-size: 18px; line-height: 26px; font-weight: 700; letter-spacing: .04em">FIT FOR USE</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Balance {BALANCE} · water {D["water"]} °C</span><span class="m">FM-INS-25 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Inspection X", 794, 1123, FONT, CSS, ROOT + "; padding: 30px 44px 22px 44px; gap: 16px", body)


# ---------------------------------------------------------------- Quick Test: A5 แนวนอน
QFL = cycle_flows(dict(n=QT["n"], meas=QT["meas"], sd2=2.4), 505)
QCYC = cycles(QFL, 818)


def quicktest():
    e = (QT["meas"] - QT["set"]) / QT["set"] * 100
    body = f"""
<header style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1.5px solid #161718; padding-bottom: 8px">
  <div style="display: flex; flex-direction: column"><span class="l">[Company Name] · Quick function test</span>
  <span style="font-size: 22px; line-height: 28px; font-weight: 700">{D["brand"]} {D["model"]} · S/N {QT["serial"]}</span>
  <span style="font-size: 13px">{D["site"]} · {QT["dept"]}</span></div>
  <div class="m" style="text-align: right; font-size: 13px; line-height: 19px">{QT["no"]}<br><b style="font-weight: 500; color: {K["ink"]}">{QT["job"]}</b><br>{QT["date"]}</div>
</header>
<div style="display: grid; grid-template-columns: 180px minmax(0, 1fr); column-gap: 20px; flex: 1">
  <div style="display: flex; flex-direction: column; gap: 10px">
    <div style="display: flex; flex-direction: column"><span class="l">Measured at {QT["set"]:g} ml/h</span><span style="font-size: 30px; line-height: 36px; font-weight: 700">{QT["meas"]:.2f}</span></div>
    <div style="display: flex; flex-direction: column"><span class="l">Error · limit ±{D["limit"]:.0f} %</span><span style="font-size: 30px; line-height: 36px; font-weight: 700">{f(e, 1, True)} %</span></div>
    <div style="display: flex; flex-direction: column"><span class="l">Cycles · period</span><span style="font-size: 16px; line-height: 22px; font-weight: 600">{QT["n"]} · {QT["period"]} s</span></div>
    <div style="background: #161718; color: #ffffff; padding: 6px; text-align: center; margin-top: auto"><span style="font-size: 22px; line-height: 30px; font-weight: 700; letter-spacing: .08em">PASS</span></div>
  </div>
  <div style="display: flex; flex-direction: column; gap: 4px"><span style="font-size: 13px; font-weight: 600">Fingerprint · shape matches {D["model"]} reference</span>
  {fingerprint(526, 330, QCYC, QT["period"], QT["meas"], ref=True, label=False)}</div>
</div>
<div style="display: flex; justify-content: space-between; align-items: flex-end">
  <span class="l">Screening only · balance {BALANCE} · FM-QT-25</span>
  <div class="sig" style="width: 200px"><div></div><span class="l">Tested by · [Technician]</span></div>
</div>
"""
    return dc("Quick Test X", 794, 559, FONT, CSS, ROOT + "; padding: 24px 34px 20px 34px; gap: 12px", body)


def boards():
    return [
        dict(name="X-Calibration.dc.html", w=794, h=1123, title="X · Calibration cycle fingerprint", html=calibration()),
        dict(name="X-Inspection.dc.html", w=794, h=1123, title="X · Inspection fingerprint vs model", html=inspection()),
        dict(name="X-QuickTest.dc.html", w=794, h=559, title="X · Quick Test (A5 landscape)", html=quicktest()),
    ]
