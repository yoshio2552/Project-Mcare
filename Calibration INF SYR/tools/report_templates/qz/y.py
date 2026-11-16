"""แบบ Y — Stability map: heatmap error รายช่วง (rate × เวลา รวมช่วงก่อนวัด) + Allan deviation (log-log) บอกว่าช่วงวัดยาวพอไหม
ทุกช่องมีตัวเลข · ความเข้ม 5 ระดับตาม |error| ÷ เกณฑ์ (พิมพ์ขาวดำยังแยกได้) · ตัวอย่าง Syringe
"""
import math

from common import (SYRINGE as D, SYR as K, SYR_QT as QT, INK, GREY, RULE, PAPER, BALANCE, f, err, series, mean,
                    Ax, T, L, R, PL, C, svg, fonts, dc)

HEADING = "แบบ Y — Stability map: heatmap error รายช่วง (rate × เวลา รวมช่วงก่อนวัด) + Allan deviation บอกว่าหน้าต่างวัดยาวพอหรือยัง"
NOTE_FILL = "pink"
NOTE = ("Y: เห็นทั้งช่วงก่อนวัด (ปั๊มยังไม่นิ่ง) และช่วงวัดในภาพเดียว — อธิบายได้ว่าทำไม DeltaM ตัดช่วงก่อนวัดทิ้ง\n"
        "Allan deviation ตอบว่า \"ต้องวัดนานเท่าไร\" แยกราย rate (ตรงกับกติกา ห้ามใช้ค่าเดียวทุก rate)\n"
        "ข้อมูลมีแล้ว (สัญญาณดิบ 1 วินาที + ช่วงวัด) ต้องเพิ่มการคำนวณ Allan")

FONT = fonts("Barlow:wght@400;500;600;700", "Noto+Sans+Thai:wght@400;500;600")
ROOT = ("color: #161718; font-family: 'Barlow', 'Noto Sans Thai', sans-serif; display: flex; flex-direction: column; "
        "font-variant-numeric: tabular-nums lining-nums")
CSS = """
.l{font-size:12px;line-height:16px;color:#5C5F62}
h2{margin:0;font-size:15px;line-height:20px;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.hd{display:flex;justify-content:space-between;align-items:baseline;gap:16px;border-bottom:1px solid #161718;padding-bottom:3px}
table{border-collapse:collapse;width:100%;font-size:13px;line-height:18px}
th{font-weight:500;color:#5C5F62;font-size:12px;text-align:right;padding:3px 6px;border-bottom:1px solid #161718}
td{text-align:right;padding:3px 6px;border-bottom:1px solid #DCDCD8}
th:first-child,td:first-child{text-align:left;padding-left:0}
p{margin:0}
.sig{display:flex;flex-direction:column;gap:2px}
.sig div{height:28px;border-bottom:1px solid #161718}
svg text{font-family:'Barlow','Noto Sans Thai',sans-serif}
"""

# ระดับความเข้ม: |E| ÷ เกณฑ์ -> (พื้น, ตัวหนังสือ) — ความสว่างต่างกันชัด พิมพ์ขาวดำได้
LEVELS = [(0.25, "#ffffff", INK), (0.5, "#FCE8F2", INK), (0.75, "#F2A9CF", INK), (1.0, "#C93A85", "#ffffff"),
          (99, "#161718", "#ffffff")]
PRE = {1.0: [-21.0, -8.4, -3.9], 5.0: [-9.6, -4.1, -2.6], 25.0: [-4.8, -1.9]}   # ช่วงก่อนวัด (ปั๊มยังไม่นิ่ง)
SEEDS = {1.0: 931, 5.0: 707, 25.0: 953}


def level(e):
    for lim, bg, fg in LEVELS:
        if abs(e) / D["limit"] < lim:
            return bg, fg
    return LEVELS[-1][1:]


def interval_errors(r):
    if r["set"] == 5.0:
        # 5 ml/h ใช้ชุดเดียวกับใบคำนวณแบบ U (Q1…Q20) ให้ตัวเลขตรงกันทุกแบบ
        from u import IFLOWS
        return [(q - r["set"]) / r["set"] * 100 for q in IFLOWS]
    fl = series(r["n"], r["meas"], r["meas"] * r["sd2"] / 200, SEEDS[r["set"]], ar=0.1)
    return [(q - r["set"]) / r["set"] * 100 for q in fl]


ERRS = {r["set"]: interval_errors(r) for r in D["rates"]}


CELL = 30.6      # ความกว้างช่องคงที่ทุกแถว (23 ช่องเต็มความกว้าง) — เวลาเทียบกันได้ตามลำดับช่วง


def heat_row(errs, pre, x0, w, y, h, cell=None):
    out = []
    n = len(errs) + len(pre)
    cw = cell or w / n
    for i, e in enumerate(pre + errs):
        x = x0 + i * cw
        if i < len(pre):
            out.append(R(x + 1, y + 1, cw - 2, h - 2, "#ffffff", GREY, 1, ' stroke-dasharray="3 2"'))
            out.append(T(x + cw / 2, y + h / 2 + 4, f(e, 0 if abs(e) >= 10 else 1), anchor="middle", fill=GREY, size=12))
        else:
            bg, fg = level(e)
            out.append(R(x, y, cw, h, bg, "#ffffff", 1))
            out.append(T(x + cw / 2, y + h / 2 + 4, f(e, 1), anchor="middle", fill=fg, size=12, weight=600))
    if pre:
        xp = x0 + len(pre) * cw
        out.append(L(xp, y - 4, xp, y + h + 4, INK, 2))
    return out


def legend(x, y, pre=True):
    out = []
    labels = ["< 25 %", "25–50", "50–75", "75–100", "> 100 % of limit"]
    for (lim, bg, fg), lab in zip(LEVELS, labels):
        out.append(R(x, y + 4, 22, 14, bg, INK, 1))
        out.append(T(x + 28, y + 16, lab, fill=GREY))
        x += 28 + len(lab) * 6.6 + 18
    if pre:
        out.append(R(x, y + 4, 22, 14, "#ffffff", GREY, 1, ' stroke-dasharray="3 2"'))
        out.append(T(x + 28, y + 16, "pre-run, not used", fill=GREY))
    return out


def heatmap(w=706):
    out, y = [], 0
    for r in D["rates"]:
        errs, pre = ERRS[r["set"]], PRE[r["set"]]
        out.append(T(0, y + 14, f"{r['set']:g} ml/h", fill=INK, weight=700, size=14))
        out.append(T(62, y + 14, f"{r['n']} windows × {r['win']} s after {len(pre)} pre-run windows", fill=GREY))
        out.append(T(w, y + 14, f"mean {f(mean(errs), 1, True)} %", anchor="end", fill=INK, weight=700, size=14))
        out += heat_row(errs, pre, 0, w, y + 22, 30, CELL)
        y += 62
    out += legend(0, y - 6)
    return svg(w, y + 18, "Heat map of error per interval for each rate, including pre-run windows", out)


# ---------------------------------------------------------------- Allan deviation (แบบจำลอง: เสียงตราชั่ง ∝ 1/τ, ปั๊ม ∝ 1/√τ, พื้น)
# a = เสียงตราชั่ง (σm 0.3 mg × √2 ÷ Q, %·s), b = ปั๊ม (%·√s), c = พื้น (%) — ตั้งให้ σ ที่หน้าต่างที่ใช้ = SD ของช่วงในตาราง
ALLAN = {1.0: (152.6, 5.06, 0.12), 5.0: (30.5, 7.5, 0.10), 25.0: (6.1, 4.22, 0.08)}


def adev(rate, tau):
    a, b, c = ALLAN[rate]
    return math.sqrt((a / tau) ** 2 + b ** 2 / tau + c ** 2)


def tau_for(rate, target):
    t = 1.0
    while adev(rate, t) > target and t < 1e5:
        t *= 1.02
    return t


TARGET = 0.3     # % — σ ที่ยอมรับต่อหน้าต่าง (≈ ¼ ของ U ที่ต้องการ)


def allan_plot(w=380, h=280):
    ax = Ax(52, w - 16, 14, h - 44, 5, 5000, 0.05, 20, logx=True, logy=True)
    out = [R(ax.x0, ax.y0, ax.x1 - ax.x0, ax.y1 - ax.y0, "#ffffff", INK)]
    for v in (10, 100, 1000):
        out.append(L(ax.sx(v), ax.y0, ax.sx(v), ax.y1, RULE))
        out.append(T(ax.sx(v), ax.y1 + 16, f"{v}", anchor="middle"))
    for v in (0.1, 1, 10):
        out.append(L(ax.x0, ax.sy(v), ax.x1, ax.sy(v), RULE))
        out.append(T(ax.x0 - 6, ax.sy(v) + 4, f"{v:g}", anchor="end"))
    out.append(L(ax.x0, ax.sy(TARGET), ax.x1, ax.sy(TARGET), K["ink"], 1.5, "6 4"))
    out.append(T(ax.x1 - 4, ax.sy(TARGET) - 6, f"target {TARGET} %", anchor="end", fill=K["ink"]))
    styles = {1.0: ("", 2.2), 5.0: ("8 4", 1.8), 25.0: ("2 3", 1.8)}
    taus = [5 * 1.08 ** k for k in range(0, 115) if 5 * 1.08 ** k <= 5000]
    side = {1.0: (10, -4), 5.0: (-10, -12), 25.0: (-10, 16)}
    for r in D["rates"]:
        dash, sw = styles[r["set"]]
        tt = [t for t in taus if adev(r["set"], t) <= 19]      # ตัดส่วนที่เกินกรอบบน
        out.append(PL(ax.pts(tt, [adev(r["set"], t) for t in tt]), INK, sw, dash=dash or None))
        tw = r["win"]
        out.append(C(ax.sx(tw), ax.sy(adev(r["set"], tw)), 4.5, K["fill"], INK, 1.5))
        dx, dy = side[r["set"]]
        out.append(T(ax.sx(tw) + dx, ax.sy(adev(r["set"], tw)) + dy, f"{r['set']:g} ml/h · {tw} s",
                     anchor="start" if dx > 0 else "end", fill=INK, weight=600))
    out.append(T(ax.x1, ax.y1 + 32, "averaging window τ, s", anchor="end"))
    out.append(T(ax.x0 - 6, ax.y1 + 32, "σ(τ), % of rate ↑", anchor="start", fill=INK, weight=600))
    return svg(w, h, "Allan deviation of flow against averaging window for 1, 5 and 25 ml/h", out)


def header(title, sub, no_label, no):
    return f"""
<header style="display: grid; grid-template-columns: minmax(0, 1fr) auto; column-gap: 20px; align-items: end; border-bottom: 3px solid #161718; padding-bottom: 8px">
  <div style="display: flex; flex-direction: column"><span class="l" style="letter-spacing: .06em">[COMPANY NAME] · CALIBRATION LABORATORY</span>
  <span style="font-size: 30px; line-height: 34px; font-weight: 700">{title}</span>
  <span style="font-size: 14px; line-height: 19px; color: #3E4143">{sub}</span></div>
  <div style="display: grid; grid-template-columns: auto auto; column-gap: 12px; font-size: 13px; line-height: 18px; text-align: right">
    <span class="l">{no_label}</span><b style="font-weight: 600">{no}</b><span class="l">Job</span><b style="font-weight: 700; color: {K["ink"]}">{D["job"]}</b>
    <span class="l">Date</span><span>{D["date"]}</span></div>
</header>
<div style="display: grid; grid-template-columns: 1.2fr 1fr 1.2fr 1fr; column-gap: 14px; font-size: 13px; line-height: 18px">
  <div style="display: flex; flex-direction: column"><span class="l">Syringe pump</span><b style="font-weight: 600">{D["brand"]} {D["model"]}</b></div>
  <div style="display: flex; flex-direction: column"><span class="l">Serial · asset</span><span>{D["serial"]} · {D["asset"]}</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Customer</span><span>{D["site"]} · {D["dept"]}</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Syringe</span><span>{D["set_label"]}</span></div>
</div>"""


def calibration():
    rows = "".join(f"""<tr><td>{r["set"]:.1f}</td><td>{r["meas"]:.3f}</td><td>{f(err(r), 1, True)} %</td><td>{r["U"]:.1f} %</td>
<td>{r["pre"]}</td><td>{r["n"]} × {r["win"]} s</td><td>{adev(r["set"], r["win"]):.2f} %</td><td>{tau_for(r["set"], TARGET):.0f} s</td><td><b style="font-weight: 700">Pass</b></td></tr>""" for r in D["rates"])
    body = f"""
{header("Calibration certificate", "stability map · ใบรับรองผลการสอบเทียบ พร้อมแผนที่ความนิ่ง", "Certificate", D["cert"])}
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>Results</h2><span class="l">limit ±{D["limit"]:.0f} % · U at k = 2 · simple acceptance (ILAC-G8) · time-interval capture</span></div>
  <table><thead><tr><th>Set ml/h</th><th>Measured</th><th>Error</th><th>U</th><th>Pre-run</th><th>Windows</th><th>σ per window</th><th>τ for σ ≤ {TARGET} %</th><th>Result</th></tr></thead><tbody>{rows}</tbody></table>
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="hd"><h2>Error of every window, %</h2><span class="l">dashed = pre-run, discarded until flow is steady · shade = |error| ÷ limit</span></div>
  {heatmap()}
</section>
<section style="display: grid; grid-template-columns: 380px minmax(0, 1fr); column-gap: 24px">
  <div style="display: flex; flex-direction: column; gap: 6px"><div class="hd"><h2>Allan deviation</h2></div>{allan_plot()}</div>
  <div style="display: flex; flex-direction: column; gap: 8px; font-size: 13px; line-height: 19px">
    <div class="hd"><h2>Reading the two charts</h2></div>
    <p>The heat map shows every window the result is built from. The pump starts slowly (dashed cells) and DeltaM waits until the flow is
    steady; the shaded cells after the thick line are the measurement.</p>
    <p>The Allan curve shows how the scatter of a single window falls as the window gets longer. At 1 ml/h the balance resolution dominates
    short windows, so each window must be long ({D["rates"][0]["win"]} s). The dot marks the window used at each rate.</p>
    <p>A single window may cross the limit (black cell); the decision uses the mean of all windows, and U already includes this scatter.
    Windows are chosen per rate and per model + syringe, never one value for all.</p>
  </div>
</section>
<p style="font-size: 13px; line-height: 19px">Gravimetric [WI-CAL-02], IEC 60601-2-24:2012, ISO 4787:2021. Balance {BALANCE}, cert. [—], traceable to SI.
Water {D["water"]} °C, {D["rh"]} %RH, {D["hpa"]} hPa. Conforms at all rates.</p>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 150px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["operator"]}</b><span class="l">Calibrated by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["approver"]}</b><span class="l">Approved by</span></div>
  <div style="border: 3px solid #161718; padding: 6px; text-align: center; display: flex; flex-direction: column"><span class="l">Result</span><span style="font-size: 26px; line-height: 30px; font-weight: 700; letter-spacing: .08em">PASS</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Reproduce in full only · page 1 / 1</span><span>FM-CAL-26 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Calibration Y", 794, 1123, FONT, CSS, ROOT + "; padding: 30px 44px 22px 44px; gap: 14px", body)


# ---------------------------------------------------------------- Inspection
INSP_FL = series(5, D["rates"][1]["meas"], D["rates"][1]["meas"] * 0.011, 611)   # ชุดเดียวกับแบบ R
INSP_E = [(q - 5) / 5 * 100 for q in INSP_FL]
CHECKS = [("Housing and labels", "OK"), ("Pole clamp", "OK"), ("Power cord and plug", "OK"),
          ("Syringe clamp, plunger holder", "OK"), ("Battery operation ≥ 60 min", "OK"), ("Keypad and display", "OK"),
          ("Syringe size detection 10 / 20 / 50 ml", "OK"), ("Occlusion alarm, 2 min 40 s", "OK"),
          ("Near-empty and end alarm", "OK"), ("Audible and visual alarms", "OK"), ("Nurse call", "N/A"),
          ("Electrical safety IEC 62353", "N/P")]


def strip_map(errs, pre, w=706, h=44):
    out = heat_row(errs, pre, 0, w, 18, h) + legend(0, h + 26, pre=w > 600)
    out.append(T(0, 12, "pre-run", fill=GREY))
    out.append(T(w * len(pre) / (len(pre) + len(errs)) + 6, 12, "measurement, 60 s each", fill=GREY))
    return svg(w, h + 50, "Error of each 60 s window of the flow check", out)


def inspection():
    half = len(CHECKS) // 2
    ck = lambda rows: "".join(f'<tr><td>{a}</td><td style="{"" if b == "OK" else "color: #5C5F62"}"><b style="font-weight: 700">{b}</b></td></tr>' for a, b in rows)
    m = mean(INSP_E)
    body = f"""
{header("Inspection report", "with stability strip · รายงานการตรวจสภาพเครื่อง", "Report", D["insp"])}
<section style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 28px">
  <div style="display: flex; flex-direction: column; gap: 6px"><div class="hd"><h2>Checks</h2><span class="l">10 OK</span></div><table><tbody>{ck(CHECKS[:half])}</tbody></table></div>
  <div style="display: flex; flex-direction: column; gap: 6px"><div class="hd"><h2>&#8203;</h2><span class="l">N/A not fitted · N/P not performed</span></div><table><tbody>{ck(CHECKS[half:])}</tbody></table></div>
</section>
<section style="display: flex; flex-direction: column; gap: 8px">
  <div class="hd"><h2>Flow check · 5 ml/h · 5 min</h2><span class="l">gravimetric · limit ±{D["limit"]:.0f} %</span></div>
  {strip_map(INSP_E, PRE[5.0])}
  <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); column-gap: 16px">
    <div style="display: flex; flex-direction: column"><span class="l">Measured</span><b style="font-size: 26px; line-height: 30px; font-weight: 700">{mean(INSP_FL):.3f}</b><span class="l">ml/h</span></div>
    <div style="display: flex; flex-direction: column"><span class="l">Error</span><b style="font-size: 26px; line-height: 30px; font-weight: 700">{f(m, 1, True)} %</b><span class="l">mean of 5 windows</span></div>
    <div style="display: flex; flex-direction: column"><span class="l">σ per 60 s window</span><b style="font-size: 26px; line-height: 30px; font-weight: 700">{adev(5.0, 60):.2f} %</b><span class="l">from the Allan curve</span></div>
    <div style="display: flex; flex-direction: column"><span class="l">Steady after</span><b style="font-size: 26px; line-height: 30px; font-weight: 700">3:30</b><span class="l">min from start</span></div>
  </div>
</section>
<section style="display: grid; grid-template-columns: 380px minmax(0, 1fr); column-gap: 24px">
  <div style="display: flex; flex-direction: column; gap: 6px"><div class="hd"><h2>Allan deviation</h2></div>{allan_plot(380, 320)}</div>
  <div style="display: flex; flex-direction: column; gap: 8px; font-size: 13px; line-height: 19px"><div class="hd"><h2>Remarks</h2></div>
  <p>Five 60 s windows are enough at 5 ml/h for an inspection: σ per window {adev(5.0, 60):.2f} %, mean of 5 → {adev(5.0, 60) / math.sqrt(5):.2f} %.
  At 1 ml/h use the full calibration procedure instead.</p>
  <p>Plunger clamp replaced under warranty claim, counted from 2 Mar 2026, not restarted. Next inspection May 2027.</p></div>
</section>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 170px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Technician name]</b><span class="l">Inspected by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Ward representative]</b><span class="l">Received by</span></div>
  <div style="border: 3px solid #161718; padding: 6px; text-align: center; display: flex; flex-direction: column"><span class="l">Status</span><span style="font-size: 20px; line-height: 28px; font-weight: 700; letter-spacing: .04em">FIT FOR USE</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Balance {BALANCE} · water {D["water"]} °C</span><span>FM-INS-26 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Inspection Y", 794, 1123, FONT, CSS, ROOT + "; padding: 30px 44px 22px 44px; gap: 16px", body)


# ---------------------------------------------------------------- Quick Test: A5 แนวตั้ง
QT_FL = series(QT["n"], QT["meas"], QT["meas"] * 0.011, 977)
QT_E = [(q - QT["set"]) / QT["set"] * 100 for q in QT_FL]


def quicktest():
    m = mean(QT_E)
    body = f"""
<header style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 3px solid #161718; padding-bottom: 6px">
  <div style="display: flex; flex-direction: column"><span class="l" style="letter-spacing: .06em">[COMPANY NAME] · QUICK TEST</span>
  <span style="font-size: 24px; line-height: 28px; font-weight: 700">{D["model"]} · S/N {QT["serial"]}</span><span style="font-size: 13px">{D["site"]} · {QT["dept"]}</span></div>
  <div style="text-align: right; font-size: 13px; line-height: 18px"><b style="font-weight: 700; color: {K["ink"]}">{QT["job"]}</b><br>{QT["no"]}<br><span class="l">{QT["date"]}</span></div>
</header>
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 16px">
  <div style="display: flex; flex-direction: column"><span class="l">Measured at {QT["set"]:g} ml/h</span><b style="font-size: 40px; line-height: 44px; font-weight: 700">{QT["meas"]:.2f}</b><span class="l">ml/h · 5 × 60 s</span></div>
  <div style="display: flex; flex-direction: column"><span class="l">Error · limit ±{D["limit"]:.0f} %</span><b style="font-size: 40px; line-height: 44px; font-weight: 700">{f(m, 1, True)} %</b><span class="l">mean of windows</span></div>
</div>
<div style="display: flex; flex-direction: column; gap: 4px"><div class="hd"><h2>Every window</h2></div>{strip_map(QT_E, PRE[5.0], 491, 56)}</div>
<table><tbody>
<tr><td>Steady after</td><td>3:30 min</td></tr><tr><td>σ per 60 s window</td><td>{adev(5.0, 60):.2f} %</td></tr>
<tr><td>Syringe</td><td>{D["set_label"]}</td></tr><tr><td>Balance</td><td>GF-300 S/N 14654769</td></tr></tbody></table>
<div style="display: flex; flex-direction: column; gap: 4px"><div class="hd"><h2>Is 60 s long enough at 5 ml/h?</h2></div>{allan_plot(491, 200)}</div>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 130px; column-gap: 20px; align-items: end">
  <div class="sig"><div></div><span class="l">Tested by · [Technician] · FM-QT-26 · screening only</span></div>
  <div style="border: 3px solid #161718; padding: 4px; text-align: center"><span style="font-size: 24px; line-height: 32px; font-weight: 700; letter-spacing: .08em">PASS</span></div>
</div>
"""
    return dc("Quick Test Y", 559, 794, FONT, CSS, ROOT + "; padding: 28px 34px 22px 34px; gap: 16px", body)


def boards():
    return [
        dict(name="Y-Calibration.dc.html", w=794, h=1123, title="Y · Calibration stability map", html=calibration()),
        dict(name="Y-Inspection.dc.html", w=794, h=1123, title="Y · Inspection with stability strip", html=inspection()),
        dict(name="Y-QuickTest.dc.html", w=559, h=794, title="Y · Quick Test (A5)", html=quicktest()),
    ]


if __name__ == "__main__":
    for r in D["rates"]:
        e = ERRS[r["set"]]
        print(r["set"], round(mean(e), 3), round(min(e), 2), round(max(e), 2), adev(r["set"], r["win"]), tau_for(r["set"], TARGET))
    print("insp", mean(INSP_FL), "qt", mean(QT_FL))
