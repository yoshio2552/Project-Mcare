"""แบบ A3 — Ruled form: แบบฟอร์มทางการ ทุกหัวข้อเป็นกล่องตีเส้น ป้ายเล็กมุมบนของแต่ละช่อง
ผลตัดสินเป็นช่องติ๊ก · ลายเซ็นเป็นกล่องพร้อม ( ชื่อ ) ตำแหน่ง วันที่ + ช่องตราประทับ · ฟอนต์ Sarabun (เหมาะกับเอกสารไทย)
"""
from kit import (S, t, other, dt, customer_rows, item_rows, balance_rows, env_rows, conformity_chart, interval_chart,
                 correction_rows, record_rows, BUDGET, sig_roles, CHECK_ITEMS, mmss, CAL, INSP, QT, HOSP, INFUSION, INF, SYR,
                 BASE_CSS, fonts, dc, f)
import math

HEADING = "แบบ A3 — Ruled form: แบบฟอร์มทางการ กล่องตีเส้นทุกช่อง ผลเป็นช่องติ๊ก ลายเซ็นในกล่อง + ตราประทับ · ซ้าย = English, ขวา = ไทย"
FONT = fonts("Sarabun:wght@400;500;600;700")
CSS = BASE_CSS + """
.mono,.tnum{font-family:inherit;font-variant-numeric:tabular-nums lining-nums}
svg text{font-family:'Sarabun',sans-serif}
.lbl{font-size:12px;line-height:15px;color:#4A525B}
.val{font-size:13.5px;line-height:18px;color:#15181C;font-weight:500}
.box3{border:1.5px solid #15181C;margin-top:8px}
.bh{display:flex;justify-content:space-between;align-items:baseline;background:#EEF0F2;border-bottom:1px solid #15181C;padding:3px 8px}
.bh b{font-size:13.5px;font-weight:700}
.bh span{font-size:12px;color:#4A525B}
.cells{display:grid}
.cells>div{border-right:1px solid #9AA2AC;border-bottom:1px solid #9AA2AC;padding:2px 8px 3px 8px;display:flex;flex-direction:column;min-width:0}
table.r{width:100%;border-collapse:collapse}
table.r th,table.r td{border:1px solid #9AA2AC;padding:3px 6px;font-size:13px;line-height:17px;text-align:center}
table.r th{font-size:12px;font-weight:600;color:#4A525B;background:#F7F8F9;line-height:15px}
table.r td.l,table.r th.l{text-align:left}
table.r tr>*:first-child{border-left:0}
table.r tr>*:last-child{border-right:0}
table.r tbody tr:last-child td{border-bottom:0}
.tick{display:inline-flex;width:15px;height:15px;border:1.5px solid #15181C;align-items:center;justify-content:center;font-size:13px;font-weight:700;vertical-align:-3px;margin-right:6px}
"""


def root(L):
    return "color: #15181C; font-family: 'Sarabun', sans-serif; display: flex; flex-direction: column; padding: 26px 40px 20px 40px; position: relative"


def box(n, key, L, inner, mt=8):
    return (f'<div class="box3" style="margin-top: {mt}px"><div class="bh"><b>{n}. {t(key, L)}</b><span>{other(key, L)}</span></div>{inner}</div>')


def cells(items, cols, L):
    """ช่องตีเส้น: items = (ป้าย, ค่า, ช่วงคอลัมน์) — ขอบขวา/ล่างของช่องสุดท้ายในแถวถูกซ่อนด้วย margin"""
    out, col = [], 0
    for lab, val, *opt in items:
        span = opt[0] if opt else 1
        out.append(f'<div style="grid-column: span {span}"><span class="lbl">{lab}</span><span class="val">{val}</span></div>')
        col += span
    return (f'<div class="cells" style="grid-template-columns: repeat({cols}, minmax(0, 1fr)); margin: 0 -1px -1px 0">{"".join(out)}</div>')


def header(L, title_key, accent, kind="lab", page=""):
    return f"""<div style="position: absolute; left: 0; top: 0; width: 100%; height: 5px; background: {accent["fill"]}"></div>
<header style="display: grid; grid-template-columns: 58px minmax(0, 1fr) auto; column-gap: 12px; align-items: center">
  <div style="width: 58px; height: 58px; border: 1px solid #9AA2AC; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #4A525B">LOGO</div>
  <div style="display: flex; flex-direction: column"><span style="font-size: 16px; line-height: 20px; font-weight: 700">{t("company", L)}</span>
  <span class="lbl">{t(kind, L)} · {t("addr", L)}</span></div>
  <div style="display: flex; flex-direction: column; align-items: flex-end"><span style="font-size: 22px; line-height: 28px; font-weight: 700">{t(title_key, L)}</span>
  <span class="lbl">{other(title_key, L)}{" · " + page if page else ""}</span></div>
</header>"""


def results_ruled(L, D=CAL):
    head = (f'<tr><th>{t("c_set", L)}<br>ml/h</th><th>{t("c_dur", L)}<br>{t("min", L)}</th><th>{t("c_n", L)}</th><th>{t("c_meas", L)}<br>ml/h</th>'
            f'<th>{t("c_err", L)}<br>%</th><th>±2SD<br>%</th><th>{t("c_u", L)}<br>%</th><th>{t("c_tol", L)}<br>%</th><th>{t("c_res", L)}</th></tr>')
    rows = "".join(f'<tr><td style="font-weight: 600">{r["set"]:.1f}</td><td>{r["dur"]:.1f}</td><td>{r["n"]}</td><td>{r["meas"]:.2f}</td>'
                   f'<td>{f(r["err"], 1, True)}</td><td>{r["sd2"]:.1f}</td><td>{r["U"]:.1f}</td><td>±{INFUSION["limit"]:.1f}</td>'
                   f'<td style="font-weight: 700">{t("pass", L)}</td></tr>' for r in D["rates"])
    return f'<table class="r"><thead>{head}</thead><tbody>{rows}</tbody></table>'


def ticks(L, options, chosen=0):
    return '<div style="display: flex; gap: 20px; flex-wrap: wrap">' + "".join(
        f'<span style="font-size: 14px; line-height: 20px; font-weight: {700 if k == chosen else 400}"><span class="tick">{"✓" if k == chosen else ""}</span>{o}</span>'
        for k, o in enumerate(options)) + "</div>"


def sig_boxes(L, roles, stamp=True):
    cols = f'repeat({len(roles)}, minmax(0, 1fr))' + (" 112px" if stamp else "")
    cellz = "".join(f"""<div style="border-right: 1px solid #9AA2AC; padding: 4px 8px 6px 8px; display: flex; flex-direction: column; gap: 1px">
<span class="lbl" style="font-weight: 600; color: #15181C">{a}</span><div style="height: 30px"></div>
<span style="font-size: 13px; text-align: center">{t("sign", L)} ......................................</span>
<span style="font-size: 13px; text-align: center">( {b} )</span><span class="lbl" style="text-align: center">{c}</span></div>""" for a, b, c in roles)
    st = (f'<div style="display: flex; align-items: center; justify-content: center"><div style="width: 88px; height: 88px; border: 1px dashed #4A525B; border-radius: 50%; display: flex; align-items: center; justify-content: center; text-align: center" class="lbl">{t("stamp", L)}</div></div>'
          if stamp else "")
    return f'<div class="box3" style="display: grid; grid-template-columns: {cols}; margin-top: auto">{cellz.replace("border-right: 1px solid #9AA2AC", "border-right: 1px solid #9AA2AC", len(roles))}{st}</div>'


def footer(L, form, no, pg, note=True):
    n = f'<span class="lbl" style="color: #3D444C">{t("disclaimer", L)}</span>' if note else ""
    return (f'<div style="margin-top: 6px; display: flex; flex-direction: column; gap: 2px">{n}<div style="display: flex; justify-content: space-between" class="lbl">'
            f'<span>{form} · Rev. 00 · {t("generated", L)}</span><span>{no} · {pg}</span></div></div>')


def meta_cells(L, items):
    return f'<div class="box3" style="margin-top: 12px">{cells(items, len(items), L)}</div>'


def cal_p1(L):
    A, D, i = INF, CAL, (0 if L == "en" else 1)
    body = f"""{header(L, "cal_title", A, page=t("page", L, a=1, b=2))}
{meta_cells(L, [(t("cert_no", L), D["cert"]), (t("job_no", L), f'<span style="color: {A["ink"]}">{D["job"]}</span>'), (t("date_cal", L), dt(D["date"], L)),
                (t("date_issue", L), dt(D["issue"], L)), (t("received", L), dt(D["received"], L))])}
{box(1, "customer", L, cells([(t("hospital", L), HOSP["name"][i], 2), (t("department", L), D["dept"]), (t("province", L), HOSP["province"][i]),
                              (t("contact", L), HOSP["contact"][i], 2), (t("tel", L), HOSP["tel"]), (t("cust_ref", L), HOSP["ref"])], 4, L))}
{box(2, "item", L, cells([(a, b, 2 if k in (0, 3) else 1) for k, (a, b, *_) in enumerate(item_rows(L))], 3, L))}
{box(3, "balance", L, cells([(a, b) for a, b, *_ in balance_rows(L)[:6]] + [(balance_rows(L)[6][0], balance_rows(L)[6][1], 2)], 4, L))}
{box(4, "env", L, cells([(a, b) for a, b, *_ in env_rows(L)], 5, L))}
{box(5, "results", L, results_ruled(L) + f'<div class="lbl" style="padding: 3px 8px">{t("err_def", L)} {t("u_def", L)}</div>')}
{box(6, "conformity", L, f'<div style="padding: 6px 8px; display: flex; flex-direction: column; gap: 6px"><span style="font-size: 13px; line-height: 18px">{t("conf_text", L)}</span>'
     + ticks(L, [t("pass", L) + (" — conforms" if L == "en" else " — เป็นไปตามเกณฑ์"), t("fail", L)]) + "</div>")}
{sig_boxes(L, sig_roles(L, "cal"))}
{footer(L, "FM-CAL-A3", D["cert"], "1/2")}"""
    return dc(f"A3 Calibration p1 {L}", 794, 1123, FONT, CSS, root(L), body)


def interval_table(L, D=CAL):
    head = (f'<tr><th>{t("c_set", L)}<br>ml/h</th><th>{t("ri_n", L)}</th><th>{t("ri_period", L)}<br>s</th><th>{t("ri_vol", L)}<br>ml</th>'
            f'<th>{t("ri_raw", L)}<br>ml/h</th><th>{t("ri_flow", L)}<br>ml/h</th><th>{t("ri_err", L)}<br>%</th><th>{t("ri_pre", L)}</th></tr>')
    pre = lambda p: p if L == "en" else p.replace("auto", "อัตโนมัติ").replace("delay", "หน่วง").replace(" s", " วินาที")
    rows = "".join(f'<tr><td style="font-weight: 600">{r["set"]:.1f}</td><td>{r["n"]}</td><td>{r["period"]}</td><td>{r["vol"]:.3f}</td>'
                   f'<td>{r["raw"]:.2f}</td><td>{r["meas"]:.2f}</td><td>{f(r["err"], 1, True)} · {r["sd2"]}</td><td>{pre(r["pre"])}</td></tr>' for r in D["rates"])
    return f'<table class="r"><thead>{head}</thead><tbody>{rows}</tbody></table>'


def budget_ruled(L):
    uc = math.sqrt(sum(u * u for _, _, u in BUDGET))
    rows = "".join(f'<tr><td class="l">{t(k, L)}</td><td>{ty}</td><td>{u:.2f}</td><td>{u * u / uc / uc * 100:.0f} %</td></tr>' for k, ty, u in BUDGET)
    rows += f'<tr><td class="l" style="font-weight: 600">{t("b_uc", L)}</td><td></td><td style="font-weight: 600">{uc:.2f}</td><td style="font-weight: 600">U = {2 * uc:.1f} %</td></tr>'
    return (f'<table class="r"><thead><tr><th class="l">{t("b_src", L)}</th><th>{t("b_type", L)}</th><th>{t("b_u", L)}</th><th>{t("b_share", L)}</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def cal_p2(L):
    A, D = INF, CAL
    charts = "".join(f'<div style="padding: 4px 6px; border-right: 1px solid #9AA2AC"><span class="val">{r["set"]:.1f} ml/h</span>'
                     f'{interval_chart(L, r, 226, 94, legend=False)}</div>' for r in D["rates"])
    ref = (f'<table class="r"><thead><tr><th class="l">{t("ref_std", L)}</th><th>{t("bal_sn", L)}</th><th>{t("cert_due", L)}</th></tr></thead><tbody>'
           f'<tr><td class="l">A&amp;D GF-300</td><td>14654769</td><td>[—] / [—]</td></tr><tr><td class="l">{t("thermometer", L)}</td><td>[—]</td><td>[—] / [—]</td></tr>'
           f'<tr><td class="l">{t("thermo", L)}</td><td>[—]</td><td>[—] / [—]</td></tr></tbody></table>')
    body = f"""{header(L, "cal_title", A, page=f'{t("cal_tech", L)} · {t("page", L, a=2, b=2)}')}
{meta_cells(L, [(t("cert_no", L), D["cert"]), (t("job_no", L), f'<span style="color: {A["ink"]}">{D["job"]}</span>'), (t("date_cal", L), dt(D["date"], L))])}
{box(7, "method_sec", L, cells([(t("method", L), t("method_v", L), 2), (t("volume", L), t("volume_v", L)), (t("intervals", L), t("intervals_inf", L))], 4, L) + ref)}
{box(8, "per_interval", L, interval_table(L) + f'<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid #9AA2AC; margin-right: -1px">{charts}</div>'
     + f'<div class="lbl" style="padding: 2px 8px; border-top: 1px solid #9AA2AC">{t("legend", L)}</div>')}
{box(9, "conf_chart", L, '<div style="padding: 4px 8px">' + conformity_chart(L, D, 694, 22) + "</div>")}
<div style="display: grid; grid-template-columns: 1fr 1.3fr; column-gap: 8px">
{box(10, "corrections", L, cells([(a, b) for a, b in correction_rows(L)] + [(a, b) for a, b in record_rows(L)[:1]], 2, L))}
{box(11, "budget", L, budget_ruled(L))}</div>
<div class="box3" style="margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 1fr">
<div style="padding: 4px 8px; border-right: 1px solid #9AA2AC"><span class="lbl">{t("checked_by", L)} · {t("sign", L)}</span><div style="height: 24px"></div></div>
<div style="padding: 4px 8px; border-right: 1px solid #9AA2AC"><span class="lbl">{t("date", L)}</span><div style="height: 24px"></div></div>
<div style="padding: 4px 8px; display: flex; align-items: center; justify-content: center"><span class="lbl" style="letter-spacing: .1em">{t("end_cert", L)}</span></div></div>
{footer(L, "FM-CAL-A3", D["cert"], "2/2", note=False)}"""
    return dc(f"A3 Calibration p2 {L}", 794, 1123, FONT, CSS, root(L), body)


def checklist_ruled(L):
    i = 0 if L == "en" else 1
    half = (len(CHECK_ITEMS) + 1) // 2
    tick = lambda on: f'<span class="tick" style="margin: 0">{"✓" if on else ""}</span>'
    rows = ""
    for a, b in zip(CHECK_ITEMS[:half], CHECK_ITEMS[half:] + [None] * (2 * half - len(CHECK_ITEMS))):
        cell = lambda it: (f'<td class="l">{it[0][i]}</td>' + "".join(f'<td>{tick(it[1] == k)}</td>' for k in ("p", "f", "na"))) if it else '<td></td>' * 4
        rows += f"<tr>{cell(a)}{cell(b)}</tr>"
    h = f'<th class="l">{t("c_item", L)}</th><th>{t("c_pass", L)}</th><th>{t("c_fail", L)}</th><th>{t("c_na", L)}</th>'
    return f'<table class="r"><thead><tr>{h}{h}</tr></thead><tbody>{rows}</tbody></table>'


def quant_ruled(L, D=INSP):
    e = (D["meas"] - D["set"]) / D["set"] * 100
    o = D["occ"]
    return (f'<table class="r"><thead><tr><th class="l">{t("c_test", L)}</th><th>{t("c_setting", L)}</th><th>{t("c_meas", L)}</th><th>{t("c_err", L)}</th>'
            f'<th>{t("c_limit", L)}</th><th>{t("c_res", L)}</th></tr></thead><tbody>'
            f'<tr><td class="l">{t("q_flow", L)}</td><td>{D["set"]:g} ml/h · {D["minutes"]} {t("min", L)}</td><td>{D["meas"]:.3f} ml/h</td><td>{f(e, 1, True)} %</td><td>±{D["limit"]:.1f} %</td><td style="font-weight: 700">{t("pass", L)}</td></tr>'
            f'<tr><td class="l">{t("q_occ", L)}</td><td>{o[0]}</td><td>{o[1]}</td><td>—</td><td>{o[2]}</td><td style="font-weight: 700">{t("pass", L)}</td></tr>'
            f'<tr><td class="l">{t("q_es", L)}</td><td>Class I</td><td>—</td><td>—</td><td>[—]</td><td>{t("np", L)}</td></tr></tbody></table>')


def inspection(L):
    A, D, i = SYR, INSP, (0 if L == "en" else 1)
    acc = ", ".join(S["acc"][i])
    parts = (f'<table class="r"><thead><tr><th class="l">{t("c_part", L)}</th><th>{t("c_basis", L)}</th><th>{t("c_warr", L)}</th></tr></thead><tbody>'
             f'<tr><td class="l">{t("p1", L)}</td><td>{t("p1b", L)}</td><td>{t("p1w", L)}</td></tr><tr><td class="l">{t("p2", L)}</td><td>{t("p2b", L)}</td><td>{t("p2w", L)}</td></tr></tbody></table>')
    body = f"""{header(L, "insp_title", A, "service", t("page", L, a=1, b=1))}
{meta_cells(L, [(t("report_no", L), D["no"]), (t("job_no", L), f'<span style="color: {A["ink"]}">{D["job"]}</span>'), (t("date_insp", L), dt(D["date"], L)), (t("next_due", L), dt(D["due"], L))])}
{box(1, "customer", L, cells([(t("hospital", L), HOSP["name"][i], 2), (t("department", L), D["dept"]), (t("province", L), HOSP["province"][i]),
                              (t("contact", L), HOSP["contact"][i], 2), (t("tel", L), HOSP["tel"]), (t("cust_ref", L), HOSP["ref"])], 4, L))}
{box(2, "equipment", L, cells([(a, b, 2 if k == 0 else 1) for k, (a, b, *_) in enumerate(item_rows(L, D, "syr"))], 5, L))}
{box(3, "balance", L, cells([(a, b) for a, b, *_ in balance_rows(L, full=False)[:3]] + [(balance_rows(L, full=False)[3][0], balance_rows(L, full=False)[3][1], 2)], 5, L))}
{box(4, "qual", L, checklist_ruled(L))}
{box(5, "quant", L, quant_ruled(L) + f'<div class="lbl" style="padding: 2px 8px; border-top: 1px solid #9AA2AC">{t("np_note", L)}</div>')}
<div style="display: grid; grid-template-columns: 0.7fr 1.3fr; column-gap: 8px">{box(6, "accessories", L, f'<div style="padding: 4px 8px" class="val">{acc}</div>')}{box(7, "parts", L, parts)}</div>
{box(8, "conclusion", L, f'<div style="padding: 6px 8px; display: flex; flex-direction: column; gap: 6px"><span style="font-size: 13px">{t("concl_text", L)}</span>'
     + ticks(L, [t("fit", L), "Fit with remarks" if L == "en" else "ใช้งานได้ มีหมายเหตุ", "Not fit for use" if L == "en" else "ไม่พร้อมใช้งาน"]) + "</div>")}
{sig_boxes(L, sig_roles(L, "insp"), stamp=False)}
{footer(L, "FM-INS-A3", D["no"], "1/1", note=False)}"""
    return dc(f"A3 Inspection {L}", 794, 1123, FONT, CSS, root(L), body)


def quicktest(L):
    A, D, i = INF, QT, (0 if L == "en" else 1)
    e = (D["meas"] - D["set"]) / D["set"] * 100
    big = lambda lab, v, u: f'<div><span class="lbl">{lab}</span><span style="font-size: 32px; line-height: 40px; font-weight: 700">{v}</span><span class="lbl">{u}</span></div>'
    body = f"""{header(L, "qt_title", A, "service", t("page", L, a=1, b=1))}
{meta_cells(L, [(t("report_no", L), D["no"]), (t("job_no", L), f'<span style="color: {A["ink"]}">{D["job"]}</span>'), (t("date", L), dt(D["date"], L))])}
{box(1, "customer", L, cells([(t("hospital", L), HOSP["name"][i], 2), (t("department", L), D["dept"]), (t("province", L), HOSP["province"][i])], 4, L))}
{box(2, "equipment", L, cells([(t("description", L), t("inf_desc", L), 2), (t("mfr_model", L), "Terumo · TE-171"), (t("bal_sn", L), D["serial"])], 4, L))}
{box(3, "results", L, '<div class="cells" style="grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 0 -1px -1px 0">'
     + big(t("qt_rate", L), f'{D["set"]:.1f}', "ml/h") + big(t("c_meas", L), f'{D["meas"]:.2f}', "ml/h")
     + big(t("c_err", L), f(e, 1, True) + " %", f'{t("limit", L)} ±5.0 %') + big(t("qt_time", L), mmss(D["secs"]), f'{t("min", L)} · {D["n"]} {t("cycles", L)}') + "</div>"
     + '<div style="padding: 6px 8px">' + ticks(L, [t("pass", L), t("fail", L) + (" → send for calibration" if L == "en" else " → ส่งสอบเทียบ")]) + "</div>")}
{box(4, "balance", L, cells([(a, b) for a, b, *_ in balance_rows(L, full=False)[:3]] + [(balance_rows(L, full=False)[3][0], balance_rows(L, full=False)[3][1], 2)], 5, L))}
<p style="margin: 8px 0 0 0; font-size: 13px; line-height: 18px">{t("qt_note", L)}</p>
{box(5, "remarks" if False else "conclusion", L, '<div style="height: 60px"></div>')}
{sig_boxes(L, [(t("tested_by", L), t("n_tech", L), f'{t("r_svc", L)} · {dt(D["date"][:10], L)}')], stamp=False).replace("margin-top: auto", "margin-top: 12px; width: 50%")}
<div style="margin-top: auto"></div>
{footer(L, "FM-QT-A3", D["no"], "1/1", note=False)}"""
    return dc(f"A3 Quick Test {L}", 794, 1123, FONT, CSS, root(L), body)


def boards():
    out = []
    for L, pre, tag in (("en", "A3-", "EN"), ("th", "A3TH-", "TH")):
        out += [dict(name=f"{pre}Calibration-p1.dc.html", w=794, h=1123, title=f"A3 {tag} · Calibration p1 (front)", html=cal_p1(L)),
                dict(name=f"{pre}Calibration-p2.dc.html", w=794, h=1123, title=f"A3 {tag} · Calibration p2 (technical)", html=cal_p2(L)),
                dict(name=f"{pre}Inspection.dc.html", w=794, h=1123, title=f"A3 {tag} · Inspection", html=inspection(L)),
                dict(name=f"{pre}QuickTest.dc.html", w=794, h=1123, title=f"A3 {tag} · Quick Test", html=quicktest(L))]
    return out
