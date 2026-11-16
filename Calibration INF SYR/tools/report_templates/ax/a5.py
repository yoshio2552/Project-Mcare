"""แบบ A5 — Compact two-column: ซ้ายเป็นข้อมูลอ้างอิง (ลูกค้า เครื่อง ตราชั่ง สภาวะ) แบบบรรทัดป้าย-ค่า, ขวาเป็นผล + กราฟ
ตาราง Results มี sparkline รายช่วงในแถว · ฟอนต์ Noto · ใบเทคนิค: ซ้าย = วิธี/เครื่องมือ/การแก้ค่า, ขวา = กราฟรายช่วง + งบความไม่แน่นอน
"""
from kit import (S, t, other, dt, customer_rows, item_rows, balance_rows, env_rows, conformity_chart, interval_chart,
                 interval_rows, correction_rows, record_rows, budget_table, sig_roles, checklist_tables, quant_table,
                 parts_table, mmss, num_cls, CAL, INSP, QT, HOSP, INFUSION, INF, SYR, CHECK_ITEMS, BASE_CSS, fonts, dc, f,
                 svg, Ax, R, PL)
from kit import LN

HEADING = "แบบ A5 — Compact two-column: ซ้ายข้อมูลอ้างอิง ขวาผล + กราฟ sparkline ในตาราง หน้าแน่นแต่ตัวอักษร ≥ 12 px · ซ้าย = English, ขวา = ไทย"
FONT = fonts("Noto+Sans:wght@400;500;600;700", "Noto+Sans+Thai:wght@400;500;600;700", "Noto+Sans+Mono:wght@400;500")
CSS = BASE_CSS + """
.mono{font-family:'Noto Sans Mono',monospace}
svg text{font-family:'Noto Sans','Noto Sans Thai',sans-serif}
.lbl{font-size:12px;line-height:16px;color:#5A626C}
.val{font-size:12.5px;line-height:17px;color:#15181C;font-weight:500}
.h{margin:0;font-size:12px;line-height:16px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#15181C;display:flex;justify-content:space-between;padding-bottom:2px;border-bottom:1px solid #15181C}
.h span{font-weight:400;letter-spacing:0;text-transform:none;color:#5A626C}
.ln{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid #E3E6EA;padding:2px 0;font-size:12px;line-height:16px}
.ln span:first-child{color:#5A626C;flex:none;max-width:48%}
.ln span:last-child{text-align:right;color:#15181C;font-weight:500}
table.t{width:100%;border-collapse:collapse}
table.t th{font-size:12px;font-weight:500;color:#5A626C;text-align:right;padding:3px 5px;border-bottom:1px solid #15181C;line-height:15px;vertical-align:bottom}
table.t th:first-child,table.t td:first-child{text-align:left;padding-left:0}
table.t td{font-size:12.5px;padding:3px 5px;border-bottom:1px solid #E3E6EA;text-align:right;color:#15181C;line-height:17px}
table.chk td:not(:first-child),table.chk th:not(:first-child){text-align:center;width:38px}
.pass{font-weight:700}
.col{display:flex;flex-direction:column;gap:10px;min-width:0}
.blk{display:flex;flex-direction:column;gap:3px}
.sig{display:flex;flex-direction:column;gap:1px}
.sig .line{height:28px;border-bottom:1px solid #15181C}
"""


def root(L):
    fam = "'Noto Sans', 'Noto Sans Thai'" if L == "en" else "'Noto Sans Thai', 'Noto Sans'"
    return f"color: #15181C; font-family: {fam}, sans-serif; display: flex; flex-direction: column; padding: 28px 36px 22px 36px; position: relative"


def blk(key, L, inner, alt=True):
    sub = f'<span>{other(key, L)}</span>' if alt else ""
    return f'<div class="blk"><h2 class="h">{t(key, L)}{sub}</h2>{inner}</div>'


def lines(rows, L):
    return "".join(f'<div class="ln"><span>{a}</span><span class="{num_cls(L) if (o and o[0]) else ""}">{b}</span></div>' for a, b, *o in rows)


def head(L, title_key, accent, kind, ticket):
    title = t(title_key, L)
    big = "font-size: 22px; line-height: 28px; letter-spacing: .04em; text-transform: uppercase" if L == "en" else "font-size: 24px; line-height: 32px"
    tk = "".join(f'<div style="display: flex; justify-content: space-between; gap: 14px"><span class="lbl">{a}</span>'
                 f'<span class="{num_cls(L)}" style="font-size: 12.5px; font-weight: 600{"; color: " + accent["ink"] if acc else ""}">{b}</span></div>' for a, b, acc in ticket)
    return f"""<header style="display: grid; grid-template-columns: minmax(0, 1fr) 236px; column-gap: 18px; align-items: stretch; border-bottom: 3px solid {accent["fill"]}; padding-bottom: 10px">
  <div style="display: flex; flex-direction: column; justify-content: space-between; gap: 8px">
    <div style="display: flex; gap: 10px; align-items: center"><div style="width: 38px; height: 38px; border: 1px solid #9AA2AC; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #5A626C">LOGO</div>
    <div style="display: flex; flex-direction: column"><span style="font-size: 13.5px; font-weight: 600">{t("company", L)}</span><span class="lbl">{t(kind, L)} · {t("addr", L)}</span></div></div>
    <div style="display: flex; flex-direction: column"><span style="{big}; font-weight: 700">{title}</span><span class="lbl">{other(title_key, L)}</span></div>
  </div>
  <div style="border: 1px solid #15181C; padding: 6px 10px; display: flex; flex-direction: column; gap: 1px; justify-content: center">{tk}</div>
</header>"""


def spark(r, accent, w=96, h=26):
    errs = [(q - r["set"]) / r["set"] * 100 for q in r["flows"]]
    ax = Ax(1, w - 1, 2, h - 2, 1, len(errs), -10, 10)
    out = [R(1, ax.sy(5), w - 2, ax.sy(-5) - ax.sy(5), accent["tint"]),
           PL(ax.pts(range(1, len(errs) + 1), [max(-9.5, min(9.5, e)) for e in errs]), "#15181C", 1),
           LN(1, ax.sy(r["err"]), w - 1, ax.sy(r["err"]), "#E0731A", 1.5)]
    return svg(w, h, f'error per interval at {r["set"]:g} ml/h', out, style="display: inline-block; vertical-align: middle")


def results_spark(L, D=CAL, A=INF):
    nc = num_cls(L)
    head = (f'<tr><th>{t("c_set", L)}<br>ml/h</th><th>n</th><th>{t("c_meas", L)}<br>ml/h</th><th>{t("c_err", L)}<br>%</th><th>±2SD<br>%</th>'
            f'<th>U<br>%</th><th style="text-align: center">{t("per_interval", L)}</th><th>{t("c_res", L)}</th></tr>')
    rows = "".join(f'<tr><td class="{nc}" style="font-weight: 600">{r["set"]:.1f}</td><td class="{nc}">{r["n"]}</td><td class="{nc}">{r["meas"]:.2f}</td>'
                   f'<td class="{nc}">{f(r["err"], 1, True)}</td><td class="{nc}">{r["sd2"]:.1f}</td><td class="{nc}">{r["U"]:.1f}</td>'
                   f'<td style="text-align: center; padding: 1px 4px">{spark(r, A)}</td><td class="pass">{t("pass", L)}</td></tr>' for r in D["rates"])
    return f'<table class="t"><thead>{head}</thead><tbody>{rows}</tbody></table>'


def sigs(roles, cols=None):
    n = cols or len(roles)
    return (f'<div style="display: grid; grid-template-columns: repeat({n}, minmax(0, 1fr)); column-gap: 20px; margin-top: auto; padding-top: 10px">'
            + "".join(f'<div class="sig"><span class="lbl">{a}</span><div class="line"></div><span class="val">{b}</span><span class="lbl">{c}</span></div>' for a, b, c in roles)
            + "</div>")


def foot(L, form, no, pg, note=True):
    n = f'<span class="lbl" style="color: #3D444C">{t("disclaimer", L)}</span>' if note else ""
    return (f'<div style="margin-top: 8px; padding-top: 5px; border-top: 1px solid #C4CAD1; display: flex; flex-direction: column; gap: 2px">{n}'
            f'<div style="display: flex; justify-content: space-between" class="lbl"><span class="mono">{form} · Rev. 00</span><span>{t("generated", L)}</span><span class="mono">{no} · {pg}</span></div></div>')


def verdict(L, tk, xk, sub=""):
    return f"""<div style="display: grid; grid-template-columns: minmax(0, 1fr) 112px; border: 1.5px solid #15181C">
<div style="padding: 6px 10px; display: flex; flex-direction: column; gap: 1px"><span style="font-size: 12.5px; font-weight: 700">{t(tk, L)}</span><span style="font-size: 12px; line-height: 17px; color: #3D444C">{t(xk, L)}</span></div>
<div style="border-left: 1.5px solid #15181C; display: flex; flex-direction: column; align-items: center; justify-content: center"><span class="lbl">{t("overall", L)}</span>
<span style="font-size: 24px; line-height: 28px; font-weight: 700; letter-spacing: .06em">{t("pass", L)}</span><span class="lbl">{sub}</span></div></div>"""


def body2(left, right, tpl="268px minmax(0, 1fr)"):
    return f'<div style="display: grid; grid-template-columns: {tpl}; column-gap: 22px; margin-top: 12px; align-items: start"><div class="col">{left}</div><div class="col">{right}</div></div>'


def cal_p1(L):
    A, D = INF, CAL
    left = (blk("customer", L, lines(customer_rows(L) + [(t("received", L), dt(D["received"], L), True)], L))
            + blk("item", L, lines(item_rows(L), L)) + blk("balance", L, lines(balance_rows(L), L)) + blk("env", L, lines(env_rows(L), L)))
    right = (blk("results", L, results_spark(L) + f'<span class="lbl">{t("err_def", L)} {t("u_def", L)}</span>')
             + blk("conf_chart", L, conformity_chart(L, D, 432, 24))
             + blk("method_sec", L, lines([(t("method", L), t("method_v", L)), (t("volume", L), t("volume_v", L)), (t("intervals", L), t("intervals_inf", L))], L)
                   + f'<span class="lbl">{t("trace", L)}</span>')
             + verdict(L, "conformity", "conf_text", "±5 %"))
    body = f"""{head(L, "cal_title", A, "lab", [(t("cert_no", L), D["cert"], False), (t("job_no", L), D["job"], True), (t("date_cal", L), dt(D["date"], L), False),
                                             (t("date_issue", L), dt(D["issue"], L), False), ("", t("page", L, a=1, b=2), False)])}
{body2(left, right)}
{sigs(sig_roles(L, "cal"))}
{foot(L, "FM-CAL-A5", D["cert"], "1/2")}"""
    return dc(f"A5 Calibration p1 {L}", 794, 1123, FONT, CSS, root(L), body)


def cal_p2(L):
    A, D = INF, CAL
    refs = lines([("A&amp;D GF-300 · S/N 14654769", "[—] / [—]"), (t("thermometer", L) + " · [—]", "[—] / [—]"), (t("thermo", L) + " · [—]", "[—] / [—]")], L)
    left = (blk("ref_std", L, f'<div class="ln"><span>{t("ref_std", L)}</span><span>{t("cert_due", L)}</span></div>' + refs, alt=False)
            + blk("corrections", L, lines(correction_rows(L), L)) + blk("record", L, lines(record_rows(L), L))
            + blk("budget", L, budget_table(L), alt=False))
    charts = "".join(f"""<div style="display: flex; flex-direction: column; gap: 1px">
<div style="display: flex; justify-content: space-between; align-items: baseline"><span class="{num_cls(L)}" style="font-size: 14px; font-weight: 600">{r["set"]:.1f} ml/h</span>
<span class="lbl">{" · ".join(f"{a} {b}" for a, b in interval_rows(L, r)[1:3])}</span></div>
{interval_chart(L, r, 438, 150, legend=False)}</div>""" for r in D["rates"])
    right = blk("per_interval", L, charts + f'<span class="lbl">{t("legend", L)}</span>')
    body = f"""{head(L, "cal_title", A, "lab", [(t("cert_no", L), D["cert"], False), (t("job_no", L), D["job"], True), ("", t("cal_tech", L), False),
                                             ("", t("page", L, a=2, b=2), False)])}
{body2(left, right, "250px minmax(0, 1fr)")}
<div style="margin-top: auto; text-align: center; font-size: 12px; letter-spacing: .12em; color: #5A626C">— {t("end_cert", L)} —</div>
{foot(L, "FM-CAL-A5", D["cert"], "2/2", note=False)}"""
    return dc(f"A5 Calibration p2 {L}", 794, 1123, FONT, CSS, root(L), body)


def checklist_one(L):
    i = 0 if L == "en" else 1
    rows = "".join(f'<tr><td>{n[i]}</td>' + "".join(f'<td><span class="box">{"✓" if m == k else ""}</span></td>' for k in ("p", "f", "na")) + "</tr>" for n, m in CHECK_ITEMS)
    return (f'<table class="t chk"><thead><tr><th>{t("c_item", L)}</th><th>{t("c_pass", L)}</th><th>{t("c_fail", L)}</th><th>{t("c_na", L)}</th></tr></thead><tbody>{rows}</tbody></table>')


def inspection(L):
    A, D = SYR, INSP
    acc = ", ".join(S["acc"][0 if L == "en" else 1])
    left = (blk("customer", L, lines(customer_rows(L, D), L)) + blk("equipment", L, lines(item_rows(L, D, "syr"), L))
            + blk("balance", L, lines(balance_rows(L, full=False), L)) + blk("accessories", L, f'<span class="val" style="font-weight: 400">{acc}</span>', alt=False))
    right = (blk("qual", L, checklist_one(L)) + blk("quant", L, quant_table(L, D) + f'<span class="lbl">{t("np_note", L)}</span>')
             + blk("parts", L, parts_table(L)) + verdict(L, "conclusion", "concl_text", t("fit", L)))
    body = f"""{head(L, "insp_title", A, "service", [(t("report_no", L), D["no"], False), (t("job_no", L), D["job"], True), (t("date_insp", L), dt(D["date"], L), False),
                                                  (t("next_due", L), dt(D["due"], L), False)])}
{body2(left, right)}
{sigs(sig_roles(L, "insp"))}
{foot(L, "FM-INS-A5", D["no"], "1/1", note=False)}"""
    return dc(f"A5 Inspection {L}", 794, 1123, FONT, CSS, root(L), body)


def quicktest(L):
    A, D, i = INF, QT, (0 if L == "en" else 1)
    e = (D["meas"] - D["set"]) / D["set"] * 100
    big = lambda lab, v, u: (f'<div style="display: flex; flex-direction: column; border-top: 1px solid #15181C; padding-top: 3px"><span class="lbl">{lab}</span>'
                             f'<span class="mono" style="font-size: 30px; line-height: 36px; font-weight: 500">{v}</span><span class="lbl">{u}</span></div>')
    left = (blk("customer", L, lines([(t("hospital", L), HOSP["name"][i]), (t("department", L), D["dept"]), (t("province", L), HOSP["province"][i])], L))
            + blk("equipment", L, lines([(t("mfr_model", L), "Terumo · TE-171"), (t("bal_sn", L), D["serial"], True),
                                         (t("admin_set", L), "[Set brand / model]" if L == "en" else "[ยี่ห้อ / รุ่นชุดสาย]")], L))
            + blk("balance", L, lines(balance_rows(L, full=False), L)))
    right = (f'<div style="display: grid; grid-template-columns: 1fr 1fr; column-gap: 18px; row-gap: 12px">'
             + big(t("qt_rate", L), f'{D["set"]:.1f}', "ml/h") + big(t("c_meas", L), f'{D["meas"]:.2f}', "ml/h")
             + big(t("c_err", L), f(e, 1, True) + " %", t("limit", L) + " ±5.0 %")
             + big(t("qt_time", L), mmss(D["secs"]), f'{t("min", L)} · {D["n"]} {t("cycles", L)}') + "</div>"
             + verdict(L, "c_res", "qt_note", t("limit", L) + " ±5 %"))
    body = f"""{head(L, "qt_title", A, "service", [(t("report_no", L), D["no"], False), (t("job_no", L), D["job"], True), (t("date", L), dt(D["date"], L), False)])}
{body2(left, right)}
<div style="display: grid; grid-template-columns: 1fr 1fr; column-gap: 20px; margin-top: 18px">
<div class="sig"><span class="lbl">{t("tested_by", L)}</span><div class="line"></div><span class="val">{t("n_tech", L)}</span><span class="lbl">{t("r_svc", L)} · {dt(D["date"][:10], L)}</span></div>
<div class="sig"><span class="lbl">{t("remarks", L)}</span><div class="line" style="border-color: #C4CAD1"></div><div class="line" style="height: 24px; border-color: #C4CAD1"></div></div></div>
<div style="margin-top: auto"></div>
{foot(L, "FM-QT-A5", D["no"], "1/1", note=False)}"""
    return dc(f"A5 Quick Test {L}", 794, 1123, FONT, CSS, root(L), body)


def boards():
    out = []
    for L, pre, tag in (("en", "A5-", "EN"), ("th", "A5TH-", "TH")):
        out += [dict(name=f"{pre}Calibration-p1.dc.html", w=794, h=1123, title=f"A5 {tag} · Calibration p1 (front)", html=cal_p1(L)),
                dict(name=f"{pre}Calibration-p2.dc.html", w=794, h=1123, title=f"A5 {tag} · Calibration p2 (technical)", html=cal_p2(L)),
                dict(name=f"{pre}Inspection.dc.html", w=794, h=1123, title=f"A5 {tag} · Inspection", html=inspection(L)),
                dict(name=f"{pre}QuickTest.dc.html", w=794, h=1123, title=f"A5 {tag} · Quick Test", html=quicktest(L))]
    return out
