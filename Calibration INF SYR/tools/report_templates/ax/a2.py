"""แบบ A2 — Sidebar dossier: แถบซ้ายเก็บเลขเอกสาร ลูกค้า ตราชั่ง และลายเซ็น · คอลัมน์ขวาเป็นเนื้อหาผล
หัวเรื่อง serif · ใบเทคนิค: แถบซ้าย = วิธี/เครื่องมือ/การแก้ค่า, ขวา = รายช่วงทุก rate + งบความไม่แน่นอน
"""
from kit import (S, t, other, dt, sec, customer_rows, item_rows, balance_rows, env_rows, results_table,
                 conformity_chart, interval_chart, interval_rows, rows_html, correction_rows, record_rows, budget_table,
                 sig_roles, quant_table, parts_table, mmss, num_cls, CAL, INSP, QT, HOSP, CHECK_ITEMS, INF, SYR,
                 BASE_CSS, fonts, dc, f)

HEADING = "แบบ A2 — Sidebar dossier: แถบซ้ายเก็บเลขเอกสาร ลูกค้า ตราชั่ง ลายเซ็น · ขวาเป็นผล + กราฟ · ซ้าย = English, ขวา = ไทย"
FONT = fonts("IBM+Plex+Mono:wght@400;500", "IBM+Plex+Sans+Thai:wght@400;500;600", "IBM+Plex+Sans:wght@400;500;600",
             "IBM+Plex+Serif:wght@500;600", "Noto+Serif+Thai:wght@500;600")
CSS = BASE_CSS + """
.lbl{font-size:12px;line-height:16px;color:#5A626C}
.val{font-size:12.5px;line-height:17px;color:#15181C;font-weight:500}
.side{width:226px;flex:none;box-sizing:border-box;background:#F3F5F7;padding:30px 18px 24px 22px;display:flex;flex-direction:column;gap:14px}
.side h3{margin:0;font-size:12px;line-height:16px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;border-bottom:1px solid #15181C;padding-bottom:3px}
.stk{display:flex;flex-direction:column;gap:4px}
.stk div{display:flex;flex-direction:column}
.main{flex:1;min-width:0;padding:30px 40px 24px 28px;display:flex;flex-direction:column}
.serif{font-family:'IBM Plex Serif','Noto Serif Thai',serif}
.sec{display:flex;align-items:baseline;gap:9px;border-bottom:1px solid #15181C;padding-bottom:3px;margin:0}
.sec-n{font-family:'IBM Plex Mono',monospace;font-size:12px;font-weight:500}
.sec-t{font-family:'IBM Plex Serif','Noto Serif Thai',serif;font-size:15px;font-weight:600}
.sec-th{font-size:12px;color:#5A626C;margin-left:auto}
.kv{display:grid;grid-template-columns:118px minmax(0,1fr);row-gap:3px;column-gap:10px}
table.t{width:100%;border-collapse:collapse}
table.t th{font-size:12px;font-weight:500;color:#5A626C;text-align:right;padding:4px 6px;border-bottom:1.5px solid #15181C;line-height:15px;vertical-align:bottom}
table.t th:first-child,table.t td:first-child{text-align:left;padding-left:0}
table.t td{font-size:12.5px;padding:4px 6px;border-bottom:1px solid #D5D9DE;text-align:right;color:#15181C;line-height:17px}
table.chk td:not(:first-child),table.chk th:not(:first-child){text-align:center;width:46px}
table.chk td{padding-top:3px;padding-bottom:3px}
.pass{font-weight:700;letter-spacing:.05em}
.row{display:flex;justify-content:space-between;border-bottom:1px solid #E3E6EA;padding:2px 0;font-size:12px;line-height:16px}
.row span:first-child{color:#5A626C}
.row span:last-child{font-variant-numeric:tabular-nums;color:#15181C}
.sig{display:flex;flex-direction:column}
.sig .line{height:22px;border-bottom:1px solid #15181C}
"""


def root(L):
    fam = "'IBM Plex Sans', 'IBM Plex Sans Thai'" if L == "en" else "'IBM Plex Sans Thai', 'IBM Plex Sans'"
    return f"color: #15181C; font-family: {fam}, sans-serif; display: flex; position: relative"


def stack(rows, L):
    return '<div class="stk">' + "".join(
        f'<div><span class="lbl">{a}</span><span class="val{" " + num_cls(L) if (opt and opt[0]) else ""}">{b}</span></div>'
        for a, b, *opt in rows) + "</div>"


def side(L, accent, blocks, sigs=None):
    sg = ""
    if sigs:
        sg = '<div style="margin-top: auto; display: flex; flex-direction: column; gap: 10px">' + "".join(
            f'<div class="sig"><span class="lbl">{a}</span><div class="line"></div><span class="val">{b}</span><span class="lbl">{c}</span></div>'
            for a, b, c in sigs) + "</div>"
    logo = f"""<div style="display: flex; flex-direction: column; gap: 4px">
<div style="width: 44px; height: 44px; border: 1px solid #9AA2AC; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #5A626C; background: #ffffff">LOGO</div>
<span style="font-size: 14px; line-height: 18px; font-weight: 600">{t("company", L)}</span><span class="lbl">{t("addr", L)}</span></div>"""
    body = "".join(f'<div style="display: flex; flex-direction: column; gap: 6px"><h3>{h}</h3>{c}</div>' for h, c in blocks)
    return f'<aside class="side" style="border-left: 5px solid {accent["fill"]}">{logo}{body}{sg}</aside>'


def title(L, key, sub):
    return f"""<div style="display: flex; flex-direction: column; border-bottom: 2px solid #15181C; padding-bottom: 8px">
<span class="lbl" style="letter-spacing: .08em; text-transform: uppercase">{other(key, L)}</span>
<span class="serif" style="font-size: 30px; line-height: 38px; font-weight: 600">{t(key, L)}</span>
<span style="font-size: 12.5px; color: #3D444C">{sub}</span></div>"""


def section(n, key, L, content, accent, mt=12, alt=True):
    h = sec(n, key, L)
    if not alt:
        h = h.replace(f'<span class="sec-th">{other(key, L)}</span>', "")
    h = h.replace('class="sec-n">', f'class="sec-n" style="color: {accent["ink"]}">')
    return f'<section style="display: flex; flex-direction: column; gap: 6px; margin-top: {mt}px">{h}{content}</section>'


def kv(rows, L):
    return '<div class="kv">' + "".join(
        f'<span class="lbl">{a}</span><span class="val{" " + num_cls(L) if (opt and opt[0]) else ""}">{b}</span>'
        for a, b, *opt in rows) + "</div>"


def verdict(L, tk, xk):
    return f"""<div style="display: grid; grid-template-columns: minmax(0, 1fr) 128px; margin-top: 12px; border-top: 2px solid #15181C; border-bottom: 2px solid #15181C">
<div style="padding: 8px 12px 8px 0; display: flex; flex-direction: column; gap: 2px"><span class="serif" style="font-size: 14px; font-weight: 600">{t(tk, L)}</span>
<span style="font-size: 12px; line-height: 17px; color: #3D444C">{t(xk, L)}</span></div>
<div style="border-left: 1px solid #15181C; display: flex; flex-direction: column; align-items: center; justify-content: center">
<span class="lbl">{t("overall", L)}</span><span style="font-size: 24px; line-height: 30px; font-weight: 700; letter-spacing: .08em">{t("pass", L)}</span></div></div>"""


def foot(L, form, no, pg):
    return (f'<div style="margin-top: 10px; padding-top: 6px; border-top: 1px solid #C4CAD1; display: flex; justify-content: space-between; font-size: 12px; color: #5A626C">'
            f'<span class="mono">{form} · Rev. 00</span><span>{t("generated", L)}</span><span class="mono">{no} · {pg}</span></div>')


def doc_rows(L, rows):
    """เลขเอกสาร: ป้าย + ค่าในบรรทัดเดียวกัน (ประหยัดที่ในแถบซ้าย)"""
    return ('<div style="display: grid; grid-template-columns: 1fr auto; row-gap: 2px; column-gap: 8px">' + "".join(
        f'<span class="lbl">{a}</span><span class="val {num_cls(L)}" style="text-align: right">{b}</span>' for a, b in rows) + "</div>")


def cust_side(L, D, received=True):
    i = 0 if L == "en" else 1
    rows = [(t("hospital", L), HOSP["name"][i]), (t("department", L) + " · " + t("province", L), f'{D["dept"]} · {HOSP["province"][i]}'),
            (t("contact", L), f'{HOSP["contact"][i]} · {t("tel", L)} {HOSP["tel"]}')]
    extra = [(t("cust_ref", L), HOSP["ref"])] + ([(t("received", L), dt(D["received"], L))] if received else [])
    return stack(rows, L) + doc_rows(L, extra)


def cal_p1(L):
    A, D = INF, CAL
    sb = side(L, A, [
        (t("cal_title", L) if L == "en" else "เอกสาร", doc_rows(L, [(t("cert_no", L), D["cert"]), (t("job_no", L), f'<span style="color: {A["ink"]}">{D["job"]}</span>'),
                                                                 (t("date_cal", L), dt(D["date"], L)), (t("date_issue", L), dt(D["issue"], L))])),
        (t("customer", L), cust_side(L, D)),
    ], sig_roles(L, "cal"))
    main = f"""<div class="main">{title(L, "cal_title", t("lab", L))}
{section("01", "item", L, kv(item_rows(L), L), A)}
{section("02", "balance", L, kv(balance_rows(L), L), A)}
{section("03", "env", L, kv(env_rows(L)[:2], L).replace('class="kv"', 'class="kv" style="grid-template-columns: 118px 1fr 118px 1fr"').replace('</div>', '') +
          "".join(f'<span class="lbl">{a}</span><span class="val {num_cls(L)}">{b}</span>' for a, b, *_ in env_rows(L)[2:]) + "</div>", A)}
{section("04", "results", L, results_table(L) + f'<span class="lbl">{t("err_def", L)} {t("u_def", L)}</span>', A)}
{section("05", "conf_chart", L, conformity_chart(L, D, 500, 26), A)}
{verdict(L, "conformity", "conf_text")}
<span class="lbl" style="margin-top: auto">{t("disclaimer", L)}</span>
{foot(L, "FM-CAL-A2", D["cert"], "1/2")}</div>"""
    return dc(f"A2 Calibration p1 {L}", 794, 1123, FONT, CSS, root(L), sb + main)


def cal_p2(L):
    A, D = INF, CAL
    sb = side(L, A, [
        (t("method", L), stack([(t("method", L), t("method_v", L)), (t("volume", L), t("volume_v", L)), (t("intervals", L), t("intervals_inf", L))], L)),
        (t("ref_std", L), stack([("A&amp;D GF-300", "S/N 14654769 · [—] / [—]"), (t("thermometer", L), "[—] · [—] / [—]"), (t("thermo", L), "[—] · [—] / [—]")], L)
         + f'<span class="lbl">{t("trace", L)}</span>'),
        (t("corrections", L), stack([(a, b, True) for a, b in correction_rows(L)], L)),
        (t("record", L), stack([(a, b, True) for a, b in record_rows(L)[:3]], L)),
    ])
    blocks = "".join(f"""<div style="display: flex; flex-direction: column; gap: 2px; padding-bottom: 8px; border-bottom: 1px solid #D5D9DE">
<div style="display: flex; justify-content: space-between; align-items: baseline"><span class="serif" style="font-size: 16px; font-weight: 600">{r["set"]:.1f} ml/h</span><span class="pass" style="font-size: 12px">{t("pass", L)}</span></div>
{interval_chart(L, r, 500, 112)}
<div style="display: grid; grid-template-columns: 1fr 1fr; column-gap: 20px">{rows_html(interval_rows(L, r)[:3])}{rows_html(interval_rows(L, r)[3:6])}</div></div>""" for r in D["rates"])
    main = f"""<div class="main">{title(L, "cal_tech", f'{t("cert_no", L)} {D["cert"]} · {t("page", L, a=2, b=2)}')}
{section("06", "per_interval", L, blocks, A)}
{section("07", "budget", L, budget_table(L), A, alt=False)}
<div style="margin-top: auto; text-align: center; font-size: 12px; letter-spacing: .12em; color: #5A626C">— {t("end_cert", L)} —</div>
{foot(L, "FM-CAL-A2", D["cert"], "2/2")}</div>"""
    return dc(f"A2 Calibration p2 {L}", 794, 1123, FONT, CSS, root(L), sb + main)


def checklist(L):
    i = 0 if L == "en" else 1
    rows = "".join(f'<tr><td>{n[i]}</td>' + "".join(f'<td><span class="box">{"✓" if m == k else ""}</span></td>' for k in ("p", "f", "na")) + "</tr>"
                   for n, m in CHECK_ITEMS)
    return (f'<table class="t chk"><thead><tr><th>{t("c_item", L)}</th><th>{t("c_pass", L)}</th><th>{t("c_fail", L)}</th><th>{t("c_na", L)}</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def inspection(L):
    A, D = SYR, INSP
    sb = side(L, A, [
        (t("insp_title", L) if L == "en" else "เอกสาร", doc_rows(L, [(t("report_no", L), D["no"]), (t("job_no", L), f'<span style="color: {A["ink"]}">{D["job"]}</span>'),
                                                                  (t("date_insp", L), dt(D["date"], L)), (t("next_due", L), dt(D["due"], L))])),
        (t("customer", L), cust_side(L, D, False)),
        (t("balance", L), stack(balance_rows(L, full=False), L)),
    ], sig_roles(L, "insp"))
    acc = ", ".join(S["acc"][0 if L == "en" else 1])
    main = f"""<div class="main">{title(L, "insp_title", t("service", L))}
{section("01", "equipment", L, kv(item_rows(L, D, "syr"), L), A)}
{section("02", "qual", L, checklist(L), A)}
{section("03", "quant", L, quant_table(L, D) + f'<span class="lbl">{t("np_note", L)}</span>', A)}
{section("04", "accessories", L, f'<span class="val" style="font-weight: 400">{acc}</span>', A, alt=False)}
{section("05", "parts", L, parts_table(L), A)}
{verdict(L, "conclusion", "concl_text")}
<div style="margin-top: auto"></div>
{foot(L, "FM-INS-A2", D["no"], "1/1")}</div>"""
    return dc(f"A2 Inspection {L}", 794, 1123, FONT, CSS, root(L), sb + main)


def quicktest(L):
    A, D = INF, QT
    i = 0 if L == "en" else 1
    e = (D["meas"] - D["set"]) / D["set"] * 100
    sb = side(L, A, [
        (t("qt_title", L) if L == "en" else "เอกสาร", doc_rows(L, [(t("report_no", L), D["no"]), (t("job_no", L), f'<span style="color: {A["ink"]}">{D["job"]}</span>'),
                                                                (t("date", L), dt(D["date"], L))])),
        (t("customer", L), stack([(t("hospital", L), HOSP["name"][i]), (t("department", L), D["dept"]), (t("province", L), HOSP["province"][i])], L)),
        (t("balance", L), stack(balance_rows(L, full=False), L)),
    ], [(t("tested_by", L), t("n_tech", L), f'{t("r_svc", L)} · {dt(D["date"][:10], L)}')])
    big = lambda lab, v, u: (f'<div style="display: flex; flex-direction: column; border-top: 1.5px solid #15181C; padding-top: 4px"><span class="lbl">{lab}</span>'
                             f'<span class="serif" style="font-size: 40px; line-height: 46px; font-weight: 600">{v}</span><span class="lbl">{u}</span></div>')
    main = f"""<div class="main">{title(L, "qt_title", t("service", L))}
{section("01", "equipment", L, kv([(t("description", L), t("inf_desc", L)), (t("mfr_model", L), "Terumo · TE-171"), (t("bal_sn", L), D["serial"], True),
                                   (t("admin_set", L), "[Set brand / model]" if L == "en" else "[ยี่ห้อ / รุ่นชุดสาย]")], L), A)}
<div style="display: grid; grid-template-columns: 1fr 1fr; column-gap: 24px; row-gap: 16px; margin-top: 18px">
{big(t("qt_rate", L), f'{D["set"]:.1f}', "ml/h")}{big(t("c_meas", L), f'{D["meas"]:.2f}', "ml/h")}
{big(t("c_err", L), f(e, 1, True) + " %", f'{t("limit", L)} ±5.0 %')}{big(t("qt_time", L), mmss(D["secs"]), f'{t("min", L)} · {D["n"]} {t("cycles", L)}')}</div>
<div style="margin-top: 18px; border-top: 2px solid #15181C; border-bottom: 2px solid #15181C; padding: 10px 0; display: flex; justify-content: space-between; align-items: baseline">
<span class="serif" style="font-size: 15px; font-weight: 600">{t("c_res", L)}</span><span style="font-size: 30px; font-weight: 700; letter-spacing: .08em">{t("pass", L)}</span></div>
<p style="margin: 10px 0 0 0; font-size: 12px; line-height: 17px; color: #3D444C">{t("qt_note", L)}</p>
<div style="display: flex; flex-direction: column; gap: 2px; margin-top: 16px"><span class="lbl">{t("remarks", L)}</span>
<div style="height: 26px; border-bottom: 1px solid #C4CAD1"></div><div style="height: 26px; border-bottom: 1px solid #C4CAD1"></div></div>
<div style="margin-top: auto"></div>
{foot(L, "FM-QT-A2", D["no"], "1/1")}</div>"""
    return dc(f"A2 Quick Test {L}", 794, 1123, FONT, CSS, root(L), sb + main)


def boards():
    out = []
    for L, pre, tag in (("en", "A2-", "EN"), ("th", "A2TH-", "TH")):
        out += [dict(name=f"{pre}Calibration-p1.dc.html", w=794, h=1123, title=f"A2 {tag} · Calibration p1 (front)", html=cal_p1(L)),
                dict(name=f"{pre}Calibration-p2.dc.html", w=794, h=1123, title=f"A2 {tag} · Calibration p2 (technical)", html=cal_p2(L)),
                dict(name=f"{pre}Inspection.dc.html", w=794, h=1123, title=f"A2 {tag} · Inspection", html=inspection(L)),
                dict(name=f"{pre}QuickTest.dc.html", w=794, h=1123, title=f"A2 {tag} · Quick Test", html=quicktest(L))]
    return out
