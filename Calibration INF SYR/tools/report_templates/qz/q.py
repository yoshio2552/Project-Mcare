"""แบบ Q — SPC record: ผังควบคุม X̄–s ของ flow รายรอบ + ตรวจกฎ Western Electric (ISO 7870-2)
แนวงาน QA อุตสาหกรรม: ตัวเลข mono, กรอบข้อมูลเอกสารตีเส้น, หัวข้อแยกด้วยเส้นหนา 2 px
"""
from common import (INFUSION as D, INF as K, INF_INSP as II, INF_QT as QT, INK, GREY, RULE, PAPER, BALANCE,
                    f, err, cycle_flows, series, mean, sd, Ax, T, L, R, PL, C, svg, fonts, dc)

HEADING = "แบบ Q — SPC record: ผังควบคุม X̄–s ของ flow รายรอบ ตรวจกฎ Western Electric ว่าปั๊มนิ่งระหว่างวัด (ISO 7870-2)"
NOTE_FILL = "blue"
NOTE = ("Q: ผังควบคุมบอกว่า \"ค่าเฉลี่ยที่รายงานเชื่อถือได้\" เพราะปั๊มอยู่ในสภาวะควบคุมตลอดการวัด\n"
        "เกณฑ์ ±5 % ใช้กับ flow เฉลี่ย ไม่ใช่รายรอบ — เส้นเกณฑ์ในผังจึงเป็นเส้นอ้างอิงจาง\n"
        "ใช้ข้อมูลรายรอบที่ DeltaM มีอยู่แล้ว ต้องเพิ่มแค่การคำนวณกฎ")

FONT = fonts("IBM+Plex+Sans:wght@400;500;600", "IBM+Plex+Sans+Thai:wght@400;500;600", "IBM+Plex+Mono:wght@400;500")
ROOT = ("color: #161718; font-family: 'IBM Plex Sans', 'IBM Plex Sans Thai', sans-serif; display: flex; "
        "flex-direction: column")
CSS = """
.m{font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums}
.l{font-size:12px;line-height:16px;color:#5C5F62}
.sec{display:flex;justify-content:space-between;align-items:baseline;border-top:2px solid #161718;padding-top:6px}
.sec h2{margin:0;font-size:14px;line-height:20px;font-weight:600}
.meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));border:1px solid #161718}
.meta div{padding:5px 10px;display:flex;flex-direction:column;border-right:1px solid #161718;border-bottom:1px solid #161718}
.meta div:nth-child(2n){border-right:0}
.meta div:nth-last-child(-n+2){border-bottom:0}
.meta b{font-family:'IBM Plex Mono',monospace;font-size:14px;line-height:20px;font-weight:500}
.kv{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));column-gap:18px}
.kv div{display:flex;flex-direction:column;gap:1px;font-size:13px;line-height:18px}
table{border-collapse:collapse;width:100%;font-size:13px;line-height:18px}
th{font-weight:500;color:#5C5F62;font-size:12px;text-align:right;padding:4px 6px;border-bottom:1px solid #161718}
td{text-align:right;padding:5px 6px;border-bottom:1px solid #DCDCD8;font-family:'IBM Plex Mono',monospace}
th:first-child,td:first-child{text-align:left}
td.t{font-family:'IBM Plex Sans','IBM Plex Sans Thai',sans-serif}
td.tl,th.tl{text-align:left}
svg text{font-family:'IBM Plex Sans','IBM Plex Sans Thai',sans-serif;font-variant-numeric:tabular-nums}
.sig{display:flex;flex-direction:column;gap:2px}
.sig div{height:30px;border-bottom:1px solid #161718}
"""

A3 = {3: 1.954, 4: 1.628}       # ค่าคงที่ผังควบคุม X̄–s (ISO 7870-2 ตาราง)
B4 = {3: 2.568, 4: 2.266}


def spc(flows, n):
    """ผัง X̄–s: แบ่งกลุ่มย่อยละ n รอบติดกัน (ทิ้งเศษท้าย) แล้วตรวจกฎ Western Electric 4 ข้อ"""
    groups = [flows[i:i + n] for i in range(0, len(flows) - n + 1, n)]
    xb = [mean(g) for g in groups]
    ss = [sd(g) for g in groups]
    cl, sbar = mean(xb), mean(ss)
    sig = A3[n] * sbar / 3                  # 1σ ของค่าเฉลี่ยกลุ่ม
    z = [(x - cl) / sig for x in xb]
    rules = {
        1: any(abs(v) > 3 for v in z),
        2: any(sum(1 for v in z[i:i + 3] if v > 2) >= 2 or sum(1 for v in z[i:i + 3] if v < -2) >= 2
               for i in range(len(z) - 2)),
        3: any(sum(1 for v in z[i:i + 5] if v > 1) >= 4 or sum(1 for v in z[i:i + 5] if v < -1) >= 4
               for i in range(len(z) - 4)),
        4: any(all(v > 0 for v in z[i:i + 8]) or all(v < 0 for v in z[i:i + 8]) for i in range(len(z) - 7)),
    }
    return dict(groups=groups, xb=xb, s=ss, cl=cl, sbar=sbar, ucl=cl + A3[n] * sbar, lcl=cl - A3[n] * sbar,
                sucl=B4[n] * sbar, rules=rules, n=n)


def flows_for(r, seed, n_sub):
    """flow รายรอบที่ทั้งชุดและเฉพาะกลุ่มย่อยเต็มมีค่าเฉลี่ย = ค่าในตาราง (เศษท้ายสมมาตรรอบค่าเฉลี่ย)"""
    full = r["n"] - r["n"] % n_sub
    s1 = r["meas"] * r["sd2"] / 200
    head = series(full, r["meas"], s1, seed, ar=0.15)
    tail = [r["meas"] + s1 * d for d in ((0.6, -0.6, 0.0)[:r["n"] % n_sub])]
    if len(tail) == 1:
        tail = [r["meas"]]
    return head + tail


SEEDS = [101, 202, 304]
SUB = [3, 4, 4]
FLOWS = [flows_for(r, s, n) for r, s, n in zip(D["rates"], SEEDS, SUB)]
CHARTS = [spc(fl, n) for fl, n in zip(FLOWS, SUB)]


def header(title, sub, cells):
    meta = "".join(f'<div><span class="l">{k}</span><b{" style=\"color: " + K["ink"] + "\"" if k == "Job No." else ""}>'
                   f"{v}</b></div>" for k, v in cells)
    return f"""
<header style="display: flex; justify-content: space-between; align-items: flex-end; gap: 24px">
  <div style="display: flex; flex-direction: column; gap: 2px">
    <span class="l" style="letter-spacing: .06em">[COMPANY NAME] · CALIBRATION LABORATORY</span>
    <span style="font-size: 28px; line-height: 34px; font-weight: 600; letter-spacing: -.01em">{title}</span>
    <span style="font-size: 13px; line-height: 18px; color: #3E4143">{sub}</span>
  </div>
  <div class="meta" style="width: 300px; flex: none">{meta}</div>
</header>"""


def item_row(extra_label="Infusion set", extra=D["set_label"]):
    return f"""
<div class="kv">
  <div><span class="l">Instrument</span><span>{D["brand"]} {D["model"]} · infusion</span></div>
  <div><span class="l">Serial · asset</span><span>{D["serial"]} · {D["asset"]}</span></div>
  <div><span class="l">Customer</span><span>{D["site"]} · {D["dept"]}</span></div>
  <div><span class="l">{extra_label}</span><span>{extra}</span></div>
</div>"""


def xbar_chart(ch, flows, w=706):
    """ผัง X̄ (บน) + ผัง s (ล่าง) ของ 50 ml/h"""
    r = D["rates"][1]
    n, G = ch["n"], len(ch["xb"])
    top = Ax(56, w - 64, 16, 176, 0, G * n, 47.0, 53.5)
    out = []
    lo, hi = r["set"] * 0.95, r["set"] * 1.05
    # เส้นเกณฑ์ (อ้างอิงจาง) — เกณฑ์ใช้กับ flow เฉลี่ย
    for v in (lo, hi):
        out.append(L(top.x0, top.sy(v), top.x1, top.sy(v), K["fill"], 1.5, "6 4"))
    out.append(T(top.x1 + 4, top.sy(hi) + 4, f"{hi:.1f}", fill=K["ink"]))
    out.append(T(top.x1 + 4, top.sy(lo) + 4, f"{lo:.1f}", fill=K["ink"]))
    for v in (47, 48, 49, 50, 51, 52, 53):
        out.append(L(top.x0 - 4, top.sy(v), top.x0, top.sy(v), INK))
        out.append(T(top.x0 - 8, top.sy(v) + 4, f"{v}", anchor="end"))
    out.append(L(top.x0, top.y0 - 6, top.x0, top.y1, INK))
    # จุดรายรอบ (เทาอ่อน) — ทุกรอบที่ใช้ในค่าเฉลี่ย
    for i, v in enumerate(flows[:G * n]):
        out.append(C(top.sx(i + 0.5), top.sy(v), 2, "#B5B8BA"))
    # CL, UCL, LCL
    out.append(L(top.x0, top.sy(ch["cl"]), top.x1, top.sy(ch["cl"]), INK, 1.5))
    out.append(L(top.x0, top.sy(ch["ucl"]), top.x1, top.sy(ch["ucl"]), INK, 1, "2 3"))
    out.append(L(top.x0, top.sy(ch["lcl"]), top.x1, top.sy(ch["lcl"]), INK, 1, "2 3"))
    out.append(T(top.x1 + 4, top.sy(ch["cl"]) + 4, f"{ch['cl']:.2f}", fill=INK, weight=500))
    out.append(T(top.x1 + 4, top.sy(ch["ucl"]) + 4, f"{ch['ucl']:.2f}", fill=INK))
    out.append(T(top.x1 + 4, top.sy(ch["lcl"]) + 4, f"{ch['lcl']:.2f}", fill=INK))
    xs = [(g + 0.5) * n for g in range(G)]
    out.append(PL(top.pts(xs, ch["xb"]), INK, 1.5))
    for x, v in zip(xs, ch["xb"]):
        out.append(R(top.sx(x) - 3.5, top.sy(v) - 3.5, 7, 7, INK))
    out.append(T(top.x0 + 6, top.y0 + 2, "X̄  subgroup mean, ml/h", fill=INK, weight=500))
    out.append(T(top.x0 + 220, top.y0 + 2, "UCL / LCL = CL ± A₃·s̄", fill=GREY))
    # ผัง s
    bot = Ax(56, w - 64, 214, 280, 0, G * n, 0, 1.5)
    out.append(L(bot.x0, bot.y0 - 6, bot.x0, bot.y1, INK))
    out.append(L(bot.x0, bot.y1, bot.x1, bot.y1, INK))
    for v in (0, 0.5, 1.0, 1.5):
        out.append(L(bot.x0 - 4, bot.sy(v), bot.x0, bot.sy(v), INK))
        out.append(T(bot.x0 - 8, bot.sy(v) + 4, f"{v:.1f}", anchor="end"))
    out.append(L(bot.x0, bot.sy(ch["sbar"]), bot.x1, bot.sy(ch["sbar"]), INK, 1.5))
    out.append(L(bot.x0, bot.sy(ch["sucl"]), bot.x1, bot.sy(ch["sucl"]), INK, 1, "2 3"))
    out.append(T(bot.x1 + 4, bot.sy(ch["sbar"]) + 4, f"{ch['sbar']:.2f}", fill=INK, weight=500))
    out.append(T(bot.x1 + 4, bot.sy(ch["sucl"]) + 4, f"{ch['sucl']:.2f}", fill=INK))
    out.append(PL(bot.pts(xs, ch["s"]), INK, 1.5))
    for x, v in zip(xs, ch["s"]):
        out.append(C(bot.sx(x), bot.sy(v), 3.5, "#ffffff", INK, 1.5))
    out.append(T(bot.x0 + 6, bot.y0 - 10, "s  subgroup standard deviation, ml/h", fill=INK, weight=500))
    for g in range(0, G + 1, 2):
        out.append(L(bot.sx(g * n), bot.y1, bot.sx(g * n), bot.y1 + 4, INK))
        out.append(T(bot.sx(g * n), bot.y1 + 18, f"{g * n}", anchor="middle"))
    out.append(T(bot.x1 + 14, bot.y1 + 18, "cycle", anchor="start"))
    out.append(T(bot.x0, bot.y1 + 34, "● single cycle   ■ mean of 4 cycles (≈ 1 min)   ··· control limit   – – flow limit ±5 %",
                 fill=GREY))
    return svg(w, 318, f"X-bar and s control chart at 50 ml/h, {G} subgroups of {n} cycles, no rule triggered",
               out)


def results_table():
    rows = []
    for r, fl, ch in zip(D["rates"], FLOWS, CHARTS):
        e = err(r)
        ok = not any(ch["rules"].values())
        rows.append(f"""<tr><td>{r["set"]:.1f}</td><td>{r["meas"]:.2f}</td><td>{f(e, 1, True)} %</td><td>{r["U"]:.1f} %</td>
<td>{r["n"]}</td><td>{sd(fl) / r["meas"] * 100:.1f} %</td><td>{len(ch["xb"])} × {ch["n"]}</td>
<td class="t">{"in control" if ok else "rule"}</td><td class="t"><b>{"Pass" if abs(e) <= D["limit"] else "Fail"}</b></td></tr>""")
    return f"""
<table>
  <thead><tr><th>Set ml/h</th><th>Measured ml/h</th><th>Error</th><th>U, k=2</th><th>Cycles</th><th>s cycle</th>
  <th>Subgroups</th><th>Control state</th><th>Result</th></tr></thead>
  <tbody>{"".join(rows)}</tbody>
</table>"""


def rules_block(ch):
    names = ["1 point beyond 3σ", "2 of 3 beyond 2σ, same side", "4 of 5 beyond 1σ, same side",
             "8 in a row on one side of CL"]
    cells = "".join(f"""<div style="display: flex; justify-content: space-between; border-bottom: 1px solid #DCDCD8; padding: 3px 0">
<span>Rule {i} · {nm}</span><b class="m" style="font-weight: 500">{"triggered" if ch["rules"][i] else "none"}</b></div>"""
                    for i, nm in enumerate(names, 1))
    return f'<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 24px; font-size: 13px; line-height: 18px">{cells}</div>'


def calibration():
    ch = CHARTS[1]
    body = f"""
{header("Calibration certificate", "with SPC record · ใบรับรองพร้อมผังควบคุม",
        [("Certificate No.", D["cert"]), ("Job No.", D["job"]), ("Calibrated", D["date"]), ("Page", "1 / 1")])}
{item_row()}
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="sec"><h2>1  Results</h2><span class="l">limit ±{D["limit"]:.1f} % of set · U at k = 2 (GUM) · simple acceptance</span></div>
  {results_table()}
  <span class="l">s cycle = standard deviation of single-cycle flow as % of the mean. A single cycle is not judged against the limit.</span>
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="sec"><h2>2  Control chart · 50 ml/h</h2><span class="l">X̄–s chart, ISO 7870-2 · {D["rates"][1]["n"]} cycles, period {D["rates"][1]["period"]} s</span></div>
  {xbar_chart(ch, FLOWS[1])}
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="sec"><h2>3  Stability rules · 50 ml/h</h2><span class="l">Western Electric · all rates checked, see column “Control state”</span></div>
  {rules_block(ch)}
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="sec"><h2>4  Method and traceability</h2><span class="l">ISO/IEC 17025 §7.8</span></div>
  <p style="margin: 0; font-size: 13px; line-height: 19px">Gravimetric method [WI-CAL-01], IEC 60601-2-24:2012, ISO 4787:2021. Balance {BALANCE}
  (cert. [—]), traceable to SI. Water {D["water"]} °C, {D["rh"]} %RH, {D["hpa"]} hPa. Each cycle runs peak to peak as captured by DeltaM.
  The pump was in statistical control at every rate, so the mean flow represents the whole run. Conforms at all rates.</p>
</section>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 170px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["operator"]}</b><span class="l">Calibrated by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">{D["approver"]}</b><span class="l">Approved by</span></div>
  <div style="border: 2px solid #161718; padding: 8px 12px; display: flex; flex-direction: column; align-items: center">
    <span class="l">Result</span><span style="font-size: 26px; line-height: 30px; font-weight: 600; letter-spacing: .08em">PASS</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Reproduce in full only · results relate only to the item calibrated</span><span class="m">FM-CAL-17 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Calibration Q", 794, 1123, FONT, CSS, ROOT + "; padding: 38px 44px 28px 44px; gap: 18px", body)


# ---------------------------------------------------------------- Inspection
INSP_FLOWS = series(II["n"], II["meas"], II["meas"] * 0.011, 404, ar=0.1)
REF_MEAN, REF_2S = 0.3, 1.6       # ข้อมูลอ้างอิงของรุ่น: error เฉลี่ย / ±2s จากการตรวจ 14 ครั้งก่อน
CHECKS = [
    ("V1", "Housing, labels, IFU", "no crack, labels legible", "OK"),
    ("V2", "Pole clamp and handle", "holds on 25 mm pole", "OK"),
    ("V3", "Power cord and plug", "no damage, strain relief", "OK"),
    ("F1", "Keypad, display, indicators", "all keys and segments", "OK"),
    ("F2", "Door and tube guide", "closes, latch detected", "OK"),
    ("F3", "Air-in-line detector", "alarm on 50 µl bubble", "OK"),
    ("F4", "Occlusion alarm, downstream", "alarm at level H", "OK"),
    ("F5", "Occlusion alarm, upstream", "alarm on clamp", "OK"),
    ("F6", "Battery operation", "≥ 30 min at 25 ml/h", "OK"),
    ("F7", "Audible and visual alarms", "all priorities", "OK"),
    ("F8", "Nurse call", "if fitted", "N/A"),
    ("S1", "Electrical safety IEC 62353", "analyser required", "N/P"),
]


def insp_chart(w=706):
    e = err(II)
    ax = Ax(56, w - 90, 24, 250, 0, II["n"], -4, 4)
    out = []
    # แถบอ้างอิงของรุ่น (พื้นจาง) + เส้นเกณฑ์
    out.append(R(ax.x0, ax.sy(REF_MEAN + REF_2S), ax.x1 - ax.x0, ax.sy(REF_MEAN - REF_2S) - ax.sy(REF_MEAN + REF_2S),
                 K["tint"]))
    out.append(L(ax.x0, ax.sy(REF_MEAN), ax.x1, ax.sy(REF_MEAN), K["ink"], 1, "4 3"))
    for v in (-4, -2, 0, 2, 4):
        out.append(L(ax.x0 - 4, ax.sy(v), ax.x0, ax.sy(v), INK))
        out.append(T(ax.x0 - 8, ax.sy(v) + 4, f(v, 0, True) if v else "0", anchor="end"))
    out.append(L(ax.x0, ax.y0, ax.x0, ax.y1, INK))
    out.append(L(ax.x0, ax.sy(0), ax.x1, ax.sy(0), GREY, 1))
    errs = [(v - II["set"]) / II["set"] * 100 for v in INSP_FLOWS]
    xs = [i + 0.5 for i in range(II["n"])]
    out.append(PL(ax.pts(xs, errs), INK, 1.5))
    for x, v in zip(xs, errs):
        out.append(C(ax.sx(x), ax.sy(v), 3.5, INK))
    out.append(L(ax.x0, ax.sy(e), ax.x1, ax.sy(e), INK, 1.5, "8 3"))
    out.append(T(ax.x1 + 6, ax.sy(e) + 4, f"{f(e, 1, True)} %", fill=INK, weight=500))
    out.append(T(ax.x0 + 8, ax.sy(REF_MEAN - REF_2S) - 6, f"{D['model']} model band, mean ± 2s", fill=K["ink"]))
    for i in range(0, II["n"] + 1, 2):
        out.append(T(ax.sx(i), ax.y1 + 18, f"{i}", anchor="middle"))
    out.append(T(ax.x0 + 8, ax.y0 + 4, "error % of each cycle", fill=INK))
    out.append(T(ax.x1, ax.y1 + 36, "cycle no. · – – mean of this run", anchor="end"))
    return svg(w, 292, f"Error of {II['n']} cycles at 25 ml/h, mean {f(e, 1, True)} %, inside model band", out)


def inspection():
    e = err(II)
    zval = (e - REF_MEAN) / (REF_2S / 2)
    rows = "".join(f"""<tr><td>{c}</td><td class="t tl">{a}</td><td class="t tl" style="color: #5C5F62">{b}</td>
<td class="t"><b style="{'' if r == 'OK' else 'color: #5C5F62'}">{r}</b></td></tr>""" for c, a, b, r in CHECKS)
    body = f"""
{header("Inspection report", "with model comparison · รายงานการตรวจสภาพเครื่อง",
        [("Report No.", D["insp"]), ("Job No.", D["job"]), ("Inspected", D["date"]), ("Page", "1 / 1")])}
{item_row("Next inspection", "May 2027 · 6 months")}
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="sec"><h2>1  Checks</h2><span class="l">10 OK · 1 N/A · 1 not performed (N/P)</span></div>
  <table><thead><tr><th>Code</th><th class="tl">Item</th><th class="tl">Criterion</th><th>Result</th></tr></thead>
  <tbody>{rows}</tbody></table>
</section>
<section style="display: flex; flex-direction: column; gap: 6px">
  <div class="sec"><h2>2  Flow check · {II["set"]:.0f} ml/h · {II["minutes"]} min</h2><span class="l">this device vs {D["model"]} reference from 14 earlier inspections</span></div>
  <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); column-gap: 18px; font-size: 13px; line-height: 18px">
    <div style="display: flex; flex-direction: column"><span class="l">Measured</span><b class="m" style="font-size: 18px; line-height: 24px; font-weight: 500">{II["meas"]:.2f} ml/h</b></div>
    <div style="display: flex; flex-direction: column"><span class="l">Error · limit ±{D["limit"]:.0f} %</span><b class="m" style="font-size: 18px; line-height: 24px; font-weight: 500">{f(e, 1, True)} %</b></div>
    <div style="display: flex; flex-direction: column"><span class="l">Model band (mean ± 2s)</span><b class="m" style="font-size: 18px; line-height: 24px; font-weight: 500">{f(REF_MEAN, 1, True)} ± {REF_2S} %</b></div>
    <div style="display: flex; flex-direction: column"><span class="l">Distance from model</span><b class="m" style="font-size: 18px; line-height: 24px; font-weight: 500">z = {f(zval, 1, True)}</b></div>
  </div>
  {insp_chart()}
</section>
<div style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 200px; column-gap: 24px; align-items: end">
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Technician name]</b><span class="l">Inspected by</span></div>
  <div class="sig"><div></div><b style="font-size: 13px; font-weight: 600">[Ward representative]</b><span class="l">Received by</span></div>
  <div style="border: 2px solid #161718; padding: 8px 12px; display: flex; flex-direction: column; align-items: center">
    <span class="l">Status</span><span style="font-size: 20px; line-height: 28px; font-weight: 600; letter-spacing: .04em; white-space: nowrap">FIT FOR USE</span></div>
</div>
<div style="display: flex; justify-content: space-between" class="l"><span>Balance {BALANCE} · water {D["water"]} °C</span><span class="m">FM-INS-17 Rev.00 · DeltaM 0.3.0</span></div>
"""
    return dc("Inspection Q", 794, 1123, FONT, CSS, ROOT + "; padding: 38px 44px 28px 44px; gap: 16px", body)


# ---------------------------------------------------------------- Quick Test (A5 แนวนอน)
QT_FLOWS = series(QT["n"], QT["meas"], QT["meas"] * 0.012, 505, ar=0.1)


def quicktest():
    e = (QT["meas"] - QT["set"]) / QT["set"] * 100
    w = 470
    ax = Ax(44, w - 52, 12, 300, 0, QT["n"], 46.5, 53.5)
    out = [R(ax.x0, ax.sy(52.5), ax.x1 - ax.x0, ax.sy(47.5) - ax.sy(52.5), K["tint"])]
    for v in (47.5, 50, 52.5):
        out.append(T(ax.x0 - 6, ax.sy(v) + 4, f"{v:.1f}", anchor="end", fill=K["ink"] if v != 50 else GREY))
    out.append(L(ax.x0, ax.sy(50), ax.x1, ax.sy(50), GREY, 1, "3 3"))
    m, s1 = mean(QT_FLOWS), sd(QT_FLOWS)
    for v in (m + 3 * s1, m - 3 * s1):
        out.append(L(ax.x0, ax.sy(v), ax.x1, ax.sy(v), INK, 1, "2 3"))
    out.append(L(ax.x0, ax.sy(m), ax.x1, ax.sy(m), INK, 1.5))
    out.append(T(ax.x1 + 4, ax.sy(m) + 4, f"{m:.2f}", fill=INK, weight=500))
    out.append(T(ax.x1 + 4, ax.sy(m + 3 * s1) + 4, "+3s", fill=INK))
    out.append(T(ax.x1 + 4, ax.sy(m - 3 * s1) + 4, "−3s", fill=INK))
    xs = [i + 0.5 for i in range(QT["n"])]
    out.append(PL(ax.pts(xs, QT_FLOWS), INK, 1.5))
    for x, v in zip(xs, QT_FLOWS):
        out.append(C(ax.sx(x), ax.sy(v), 3.5, INK))
    out.append(L(ax.x0, ax.y1, ax.x1, ax.y1, INK))
    for i in (0, 4, 8, 12):
        out.append(T(ax.sx(i), ax.y1 + 18, f"{i}", anchor="middle"))
    out.append(T(ax.x1, ax.y1 + 34, "cycle · shaded = ±5 % of set", anchor="end"))
    chart = svg(w, 340, f"Individuals chart of {QT['n']} cycles at 50 ml/h, mean {m:.2f}", out)
    body = f"""
<header style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #161718; padding-bottom: 8px">
  <div style="display: flex; flex-direction: column"><span class="l" style="letter-spacing: .06em">[COMPANY NAME] · QUICK FUNCTION TEST</span>
  <span style="font-size: 22px; line-height: 28px; font-weight: 600">{D["brand"]} {D["model"]} · S/N <span class="m">{QT["serial"]}</span></span>
  <span style="font-size: 13px; color: #3E4143">{D["site"]} · {QT["dept"]}</span></div>
  <div class="m" style="text-align: right; font-size: 13px; line-height: 19px">{QT["no"]}<br><b style="color: {K["ink"]}; font-weight: 500">{QT["job"]}</b><br><span class="l">{QT["date"]}</span></div>
</header>
<div style="display: grid; grid-template-columns: 200px 1fr; column-gap: 24px; flex: 1">
  <div style="display: flex; flex-direction: column; gap: 10px">
    <div style="display: flex; flex-direction: column"><span class="l">Measured at {QT["set"]:.0f} ml/h</span><span class="m" style="font-size: 30px; line-height: 36px; font-weight: 500">{QT["meas"]:.2f}</span></div>
    <div style="display: flex; flex-direction: column"><span class="l">Error · limit ±{D["limit"]:.0f} %</span><span class="m" style="font-size: 30px; line-height: 36px; font-weight: 500">{f(e, 1, True)} %</span></div>
    <div style="display: flex; flex-direction: column"><span class="l">Run</span><span class="m" style="font-size: 15px; line-height: 20px">{QT["minutes"]}:00 min · {QT["n"]} cycles</span></div>
    <div style="border: 2px solid #161718; padding: 6px 10px; display: flex; justify-content: space-between; align-items: baseline">
      <span class="l">Result</span><span style="font-size: 22px; font-weight: 600; letter-spacing: .08em">PASS</span></div>
  </div>
  <div style="display: flex; flex-direction: column; gap: 4px"><span style="font-size: 13px; font-weight: 600">Flow of each cycle, ml/h</span>{chart}</div>
</div>
<div style="display: flex; justify-content: space-between; align-items: flex-end; gap: 24px">
  <span class="l" style="max-width: 400px">Screening at one rate, balance {BALANCE}. Points stay inside ±3s: the pump ran steadily. Does not replace calibration. FM-QT-17.</span>
  <div class="sig" style="width: 210px"><div></div><span class="l">Tested by · [Technician]</span></div>
</div>
"""
    return dc("Quick Test Q", 794, 559, FONT, CSS, ROOT + "; padding: 26px 36px 22px 36px; gap: 14px", body)


def boards():
    return [
        dict(name="Q-Calibration.dc.html", w=794, h=1123, title="Q · Calibration SPC record", html=calibration()),
        dict(name="Q-Inspection.dc.html", w=794, h=1123, title="Q · Inspection vs model band", html=inspection()),
        dict(name="Q-QuickTest.dc.html", w=794, h=559, title="Q · Quick Test (A5 landscape)", html=quicktest()),
    ]


if __name__ == "__main__":
    for r, ch in zip(D["rates"], CHARTS):
        print(r["set"], len(ch["xb"]), ch["rules"], round(ch["cl"], 3), round(ch["ucl"], 3), round(ch["lcl"], 3))
