"""แบบ A1 — Refined: ใกล้แบบ A ที่สุด กริดแน่นขึ้น PASS เป็นตัวดำในกรอบ (พิมพ์ขาวดำได้)
ใบหน้า: ลูกค้า + เครื่อง + ตราชั่ง + สภาวะ + ผล + ข้อความสอดคล้อง + ลายเซ็น 3 ช่อง · ใบเทคนิค: วิธี, กราฟ ±U, รายช่วง, การแก้ค่า, งบความไม่แน่นอน
"""
from kit import (S, t, other, dt, kv, sec, customer_rows, item_rows, balance_rows, env_rows, results_table,
                 conformity_chart, interval_chart, interval_rows, rows_html, correction_rows, record_rows, budget_table,
                 ref_table, sig_roles, checklist_tables, quant_table, parts_table, mmss, num_cls, CAL, INSP, QT, HOSP,
                 INF, SYR, BASE_CSS, fonts, dc, f)

HEADING = "แบบ A1 — Refined: ใกล้แบบ A ที่สุด กริดแน่นขึ้น บล็อกตราชั่ง + ลูกค้าครบ ลายเซ็น 3 ช่อง · ซ้าย = English, ขวา = ไทย"
FONT = fonts("IBM+Plex+Mono:wght@400;500", "IBM+Plex+Sans+Thai:wght@400;500;600;700", "IBM+Plex+Sans:wght@400;500;600;700")
CSS = BASE_CSS + """
.lbl{font-size:12px;line-height:16px;color:#5A626C}
.val{font-size:12.5px;line-height:17px;color:#15181C;font-weight:500}
.sec{display:flex;align-items:baseline;gap:9px;border-bottom:1px solid #15181C;padding-bottom:4px;margin:0}
.sec-n{font-family:'IBM Plex Mono',monospace;font-size:12px;font-weight:500}
.sec-t{font-size:12.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase}
.sec-th{font-size:12px;color:#5A626C;margin-left:auto}
.kv{display:grid;grid-template-columns:124px minmax(0,1fr);row-gap:3px;column-gap:10px}
table.t{width:100%;border-collapse:collapse}
table.t th{font-size:12px;font-weight:500;color:#5A626C;text-align:right;padding:4px 7px;border-top:1px solid #15181C;border-bottom:1px solid #15181C;line-height:15px;vertical-align:bottom}
table.t th:first-child,table.t td:first-child{text-align:left;padding-left:0}
table.t td{font-size:12.5px;padding:4px 7px;border-bottom:1px solid #D5D9DE;text-align:right;color:#15181C;line-height:17px}
table.chk td:not(:first-child),table.chk th:not(:first-child){text-align:center;width:40px;padding-left:2px;padding-right:2px}
table.chk td{padding-top:3px;padding-bottom:3px}
.pass{font-weight:700;letter-spacing:.06em}
.row{display:flex;justify-content:space-between;border-bottom:1px solid #E3E6EA;padding:2px 0;font-size:12px;line-height:16px}
.row span:first-child{color:#5A626C}
.row span:last-child{font-variant-numeric:tabular-nums;color:#15181C}
.sig{display:flex;flex-direction:column;gap:1px}
.sig .line{height:30px;border-bottom:1px solid #15181C}
"""


def root(L):
    fam = "'IBM Plex Sans', 'IBM Plex Sans Thai'" if L == "en" else "'IBM Plex Sans Thai', 'IBM Plex Sans'"
    return (f"position: relative; color: #15181C; font-family: {fam}, sans-serif; display: flex; flex-direction: column; "
            "padding: 0 46px 26px 46px")


def css(L):
    th = "" if L == "en" else ".sec-t{letter-spacing:0;text-transform:none;font-size:14px}.sec-th{text-transform:uppercase;letter-spacing:.06em}"
    return CSS + th


def head(L, title_key, sub_key, page, accent, kind="lab"):
    title = t(title_key, L)
    big = "font-size: 21px; letter-spacing: .1em; text-transform: uppercase" if L == "en" else "font-size: 25px"
    return f"""<div style="position: absolute; left: 0; top: 0; width: 794px; height: 5px; background: {accent["fill"]}"></div>
<header style="display: flex; justify-content: space-between; align-items: flex-start; padding-top: 28px; padding-bottom: 10px; border-bottom: 2px solid #15181C">
  <div style="display: flex; gap: 12px; align-items: center">
    <div style="width: 46px; height: 46px; border: 1px solid #9AA2AC; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #5A626C">LOGO</div>
    <div style="display: flex; flex-direction: column"><span style="font-size: 15px; font-weight: 600">{t("company", L)}</span>
    <span class="lbl">{t(kind, L)}</span><span class="lbl">{t("addr", L)}</span></div>
  </div>
  <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 1px">
    <span style="{big}; font-weight: 700; line-height: 30px">{title}</span>
    <span class="lbl">{other(title_key, L)}{" · " + t(sub_key, L) if sub_key else ""}</span>
    <span class="lbl {num_cls(L)}">{page}</span>
  </div>
</header>"""


def meta(L, cells, accent):
    out = []
    for k, (lab, val, acc) in enumerate(cells):
        pad = "padding: 7px 10px 7px 0" if k == 0 else "padding: 7px 10px; border-left: 1px solid #D5D9DE"
        out.append(f'<div style="{pad}; display: flex; flex-direction: column"><span class="lbl">{lab}</span>'
                   f'<span class="{num_cls(L)}" style="font-size: 13.5px; font-weight: 500{"; color: " + accent["ink"] if acc else ""}">{val}</span></div>')
    return f'<div style="display: grid; grid-template-columns: repeat({len(cells)}, minmax(0, 1fr)); border-bottom: 1px solid #D5D9DE">{"".join(out)}</div>'


def section(n, key, L, content, accent, mt=10, alt=True):
    h = sec(n, key, L)
    if not alt:
        h = h.replace(f'<span class="sec-th">{other(key, L)}</span>', "")
    h = h.replace('class="sec-n">', f'class="sec-n" style="color: {accent["ink"]}">')
    return f'<section style="display: flex; flex-direction: column; gap: 6px; margin-top: {mt}px">{h}{content}</section>'


def two(a, b, cols="1fr 1fr", gap=28):
    return f'<div style="display: grid; grid-template-columns: {cols}; column-gap: {gap}px; align-items: start">{a}{b}</div>'


def sigs(roles):
    cells = "".join(f'<div class="sig"><span class="lbl">{a}</span><div class="line"></div><span class="val">{b}</span><span class="lbl">{c}</span></div>'
                    for a, b, c in roles)
    return f'<div style="display: grid; grid-template-columns: repeat({len(roles)}, minmax(0, 1fr)); column-gap: 24px; margin-top: auto; padding-top: 10px">{cells}</div>'


def foot(L, form, no, pg, note=True):
    n = f'<span style="font-size: 12px; line-height: 16px; color: #3D444C">{t("disclaimer", L)}</span>' if note else ""
    return f"""<footer style="margin-top: 10px; padding-top: 6px; border-top: 1px solid #C4CAD1; display: flex; flex-direction: column; gap: 3px">{n}
<div style="display: flex; justify-content: space-between; font-size: 12px; color: #5A626C"><span class="mono">{form} · Rev. 00</span><span>{t("generated", L)}</span><span class="mono">{no} · {pg}</span></div></footer>"""


def verdict_box(L, title_key, text_key, word_key="pass"):
    return f"""<div style="display: grid; grid-template-columns: minmax(0, 1fr) 150px; border: 1.5px solid #15181C; margin-top: 10px">
<div style="padding: 8px 12px; display: flex; flex-direction: column; gap: 2px"><span style="font-size: 12.5px; font-weight: 600">{t(title_key, L)}</span>
<span style="font-size: 12px; line-height: 17px; color: #3D444C">{t(text_key, L)}</span></div>
<div style="border-left: 1.5px solid #15181C; display: flex; flex-direction: column; align-items: center; justify-content: center">
<span class="lbl">{t("overall", L)}</span><span style="font-size: 26px; line-height: 30px; font-weight: 700; letter-spacing: .08em">{t(word_key, L)}</span></div></div>"""


def env_strip(L, D=CAL):
    cells = "".join(f'<div style="display: flex; flex-direction: column{"; border-left: 1px solid #D5D9DE; padding-left: 10px" if k else ""}">'
                    f'<span class="lbl">{a}</span><span class="val">{b}</span></div>' for k, (a, b, *_) in enumerate(env_rows(L, D)))
    return f'<div style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr))">{cells}</div>'


def cal_p1(L):
    A, D, i = INF, CAL, (0 if L == "en" else 1)
    body = f"""{head(L, "cal_title", None, t("page", L, a=1, b=2), A)}
{meta(L, [(t("cert_no", L), D["cert"], False), (t("job_no", L), D["job"], True), (t("date_cal", L), dt(D["date"], L), False),
          (t("date_issue", L), dt(D["issue"], L), False)], A)}
{two(section("01", "customer", L, kv(customer_rows(L) + [(t("received", L), dt(D["received"], L), True)], L=L), A, 12),
     section("02", "item", L, kv(item_rows(L), L=L), A, 12))}
{two(section("03", "balance", L, kv(balance_rows(L), L=L), A), section("04", "env", L, kv(env_rows(L), L=L), A))}
{section("05", "results", L, results_table(L) + f'<div style="font-size: 12px; line-height: 16px; color: #3D444C">{t("err_def", L)} {t("u_def", L)}</div>', A)}
{verdict_box(L, "conformity", "conf_text")}
{sigs(sig_roles(L, "cal"))}
{foot(L, "FM-CAL-A1", D["cert"], "1/2")}"""
    return dc(f"A1 Calibration p1 {L}", 794, 1123, FONT, css(L), root(L), body)


def mini_interval(L, r):
    return f"""<div style="display: flex; flex-direction: column; gap: 2px">
<div style="display: flex; justify-content: space-between; align-items: baseline"><span class="{num_cls(L)}" style="font-size: 14px; font-weight: 600">{r["set"]:.1f} ml/h</span>
<span class="pass" style="font-size: 12px">{t("pass", L)}</span></div>
{interval_chart(L, r, 216, 132, legend=False)}
{rows_html(interval_rows(L, r)[1:3] + interval_rows(L, r)[5:6])}</div>"""


def cal_p2(L):
    A, D = INF, CAL
    method = kv([(t("method", L), t("method_v", L)), (t("volume", L), t("volume_v", L)), (t("intervals", L), t("intervals_inf", L))], L=L).replace('class="kv"', 'class="kv" style="grid-template-columns: 92px minmax(0, 1fr)"')
    body = f"""{head(L, "cal_title", "cal_tech", t("page", L, a=2, b=2), A)}
{section("06", "method_sec", L, two(method, ref_table(L), "1fr 1fr", 24) + f'<span class="lbl">{t("trace", L)}</span>', A, 12)}
{section("07", "conf_chart", L, conformity_chart(L, D, 702), A)}
{section("08", "per_interval", L, '<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 18px">' + "".join(mini_interval(L, r) for r in D["rates"]) + "</div>"
         + f'<span class="lbl">{t("legend", L)}</span>', A)}
{two("<div>" + section("09", "corrections", L, rows_html(correction_rows(L)), A, alt=False) + section("10", "record", L, rows_html(record_rows(L)[:3]), A, alt=False) + "</div>",
     section("11", "budget", L, budget_table(L), A, alt=False), "0.8fr 1.2fr", 24)}
<div style="margin-top: auto; text-align: center; font-size: 12px; letter-spacing: .12em; color: #5A626C">— {t("end_cert", L)} —</div>
{foot(L, "FM-CAL-A1", D["cert"], "2/2", note=False)}"""
    return dc(f"A1 Calibration p2 {L}", 794, 1123, FONT, css(L), root(L), body)


def inspection(L):
    A, D = SYR, INSP
    left, right = checklist_tables(L)
    acc = ", ".join(S["acc"][0 if L == "en" else 1])
    body = f"""{head(L, "insp_title", None, t("page", L, a=1, b=1), A, "service")}
{meta(L, [(t("report_no", L), D["no"], False), (t("job_no", L), D["job"], True), (t("date_insp", L), dt(D["date"], L), False),
          (t("next_due", L), dt(D["due"], L), False)], A)}
{two(section("01", "customer", L, kv(customer_rows(L, D), L=L), A, 12), section("02", "equipment", L, kv(item_rows(L, D, "syr"), L=L), A, 12))}
{section("03", "balance", L, kv(balance_rows(L, full=False)[:3], L=L).replace('class="kv"', 'class="kv" style="grid-template-columns: 124px 1fr 124px 1fr"') + f'<span class="lbl">{t("bal_check", L)}: {t("bal_check_v", L)}</span>', A)}
{section("04", "qual", L, two(left, right, "1fr 1fr", 22), A, 8)}
{section("05", "quant", L, quant_table(L, D) + f'<span class="lbl">{t("np_note", L)}</span>', A, 8)}
{two(section("06", "accessories", L, f'<span class="val" style="font-weight: 400">{acc}</span>', A, 8, alt=False), section("07", "parts", L, parts_table(L), A, 8), "0.6fr 1.4fr", 24)}
{verdict_box(L, "conclusion", "concl_text")}
{sigs(sig_roles(L, "insp"))}
{foot(L, "FM-INS-A1", D["no"], "1/1", note=False)}"""
    body = body.replace('class="sec-n">', f'class="sec-n" style="color: {A["ink"]}">')
    return dc(f"A1 Inspection {L}", 794, 1123, FONT, css(L), root(L), body)


def quicktest(L):
    A, D = INF, QT
    e = (D["meas"] - D["set"]) / D["set"] * 100
    i = 0 if L == "en" else 1
    cell = lambda lab, v, u: (f'<div style="padding: 10px 12px; border-right: 1px solid #C4CAD1; display: flex; flex-direction: column">'
                              f'<span class="lbl">{lab}</span><span class="mono" style="font-size: 30px; line-height: 36px; font-weight: 500">{v}</span><span class="lbl">{u}</span></div>')
    body = f"""{head(L, "qt_title", None, t("page", L, a=1, b=1), A, "service")}
{meta(L, [(t("report_no", L), D["no"], False), (t("job_no", L), D["job"], True), (t("date", L), dt(D["date"], L), False),
          (t("customer", L), f'{HOSP["name"][i]} · {D["dept"]}', False)], A)}
{meta(L, [(t("description", L), t("inf_desc", L).split(",")[0].split(" (")[0], False), (t("mfr_model", L), "Terumo · TE-171", False),
          (t("bal_sn", L), D["serial"], False), (t("admin_set", L), "[Set brand / model]" if L == "en" else "[ยี่ห้อ / รุ่นชุดสาย]", False)], A)}
<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)) 150px; border: 1.5px solid #15181C; margin-top: 18px">
{cell(t("qt_rate", L), f'{D["set"]:.1f}', "ml/h")}{cell(t("c_meas", L), f'{D["meas"]:.2f}', "ml/h")}
{cell(t("c_err", L), f(e, 1, True), f'% · {t("limit", L)} ±5.0 %')}{cell(t("qt_time", L), mmss(D["secs"]), f'{t("min", L)} · {D["n"]} {t("cycles", L)}')}
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center"><span class="lbl">{t("c_res", L)}</span>
<span style="font-size: 28px; font-weight: 700; letter-spacing: .08em">{t("pass", L)}</span></div></div>
{section("", "balance", L, kv(balance_rows(L, full=False), L=L), A, 18)}
<p style="margin: 10px 0 0 0; font-size: 12px; line-height: 17px; color: #3D444C">{t("qt_note", L)}</p>
{two(f'<div class="sig" style="margin-top: 22px"><span class="lbl">{t("tested_by", L)}</span><div class="line"></div><span class="val">{t("n_tech", L)}</span><span class="lbl">{t("r_svc", L)} · {dt(D["date"][:10], L)}</span></div>',
     f'<div class="sig" style="margin-top: 22px"><span class="lbl">{t("remarks", L)}</span><div class="line" style="border-color: #C4CAD1"></div><div class="line" style="height: 24px; border-color: #C4CAD1"></div></div>')}
<div style="margin-top: auto"></div>
{foot(L, "FM-QT-A1", D["no"], "1/1", note=False)}"""
    return dc(f"A1 Quick Test {L}", 794, 1123, FONT, css(L), root(L), body)


def boards():
    out = []
    for L, pre, tag in (("en", "A1-", "EN"), ("th", "A1TH-", "TH")):
        out += [dict(name=f"{pre}Calibration-p1.dc.html", w=794, h=1123, title=f"A1 {tag} · Calibration p1 (front)", html=cal_p1(L)),
                dict(name=f"{pre}Calibration-p2.dc.html", w=794, h=1123, title=f"A1 {tag} · Calibration p2 (technical)", html=cal_p2(L)),
                dict(name=f"{pre}Inspection.dc.html", w=794, h=1123, title=f"A1 {tag} · Inspection", html=inspection(L)),
                dict(name=f"{pre}QuickTest.dc.html", w=794, h=1123, title=f"A1 {tag} · Quick Test", html=quicktest(L))]
    return out
