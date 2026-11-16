"""แบบ A4 — Summary band: แถบสรุปผลบนสุด (ตัวเลขใหญ่ราย rate + มาตรวัด ±U + ผลรวม) อ่านผลได้ใน 3 วินาที
ถัดลงมา ลูกค้า | เครื่อง | ตราชั่ง สามคอลัมน์ · ตัวหนังสือแบบ condensed · ใบเทคนิค: กราฟความสอดคล้องใหญ่ + small multiples รายช่วง
"""
from kit import (S, t, other, dt, sec, customer_rows, item_rows, balance_rows, env_rows, results_table,
                 conformity_chart, interval_chart, interval_rows, rows_html, correction_rows, record_rows, budget_table,
                 ref_table, sig_roles, checklist_tables, quant_table, parts_table, mmss, num_cls, CAL, INSP, QT, HOSP,
                 INFUSION, SYRINGE, INF, SYR, BASE_CSS, fonts, dc, f, svg, Ax, T, R, C)
from kit import LN

HEADING = "แบบ A4 — Summary band: แถบสรุปผลตัวเลขใหญ่ + มาตรวัด ±U บนสุด แล้วจึงรายละเอียด · ซ้าย = English, ขวา = ไทย"
FONT = fonts("IBM+Plex+Sans+Condensed:wght@400;500;600;700", "IBM+Plex+Sans+Thai:wght@400;500;600;700", "IBM+Plex+Mono:wght@400;500")
CSS = BASE_CSS + """
.lbl{font-size:12px;line-height:16px;color:#5A626C}
.val{font-size:13px;line-height:17px;color:#15181C;font-weight:500}
.sec{display:flex;align-items:baseline;gap:8px;border-bottom:2px solid #15181C;padding-bottom:3px;margin:0}
.sec-n{display:none}
.sec-t{font-size:13px;font-weight:700;letter-spacing:.05em;text-transform:uppercase}
.sec-th{font-size:12px;color:#5A626C;margin-left:auto}
.kv{display:grid;grid-template-columns:minmax(0,0.9fr) minmax(0,1.1fr);row-gap:2px;column-gap:8px}
table.t{width:100%;border-collapse:collapse}
table.t th{font-size:12px;font-weight:500;color:#5A626C;text-align:right;padding:3px 6px;border-bottom:1px solid #15181C;line-height:15px;vertical-align:bottom}
table.t th:first-child,table.t td:first-child{text-align:left;padding-left:0}
table.t td{font-size:13px;padding:3px 6px;border-bottom:1px solid #D5D9DE;text-align:right;color:#15181C;line-height:17px}
table.chk td:not(:first-child),table.chk th:not(:first-child){text-align:center;width:40px}
.pass{font-weight:700;letter-spacing:.05em}
.row{display:flex;justify-content:space-between;border-bottom:1px solid #E3E6EA;padding:2px 0;font-size:12px;line-height:16px}
.row span:first-child{color:#5A626C}
.row span:last-child{font-variant-numeric:tabular-nums;color:#15181C}
.band{display:grid;border-top:2px solid #15181C;border-bottom:2px solid #15181C;margin-top:12px}
.band>div{padding:8px 12px;display:flex;flex-direction:column;gap:1px}
.big{font-size:34px;line-height:38px;font-weight:600;font-variant-numeric:tabular-nums lining-nums;letter-spacing:-.01em}
.sig{display:flex;flex-direction:column;gap:1px}
.sig .line{height:28px;border-bottom:1px solid #15181C}
"""


def root(L):
    fam = "'IBM Plex Sans Condensed', 'IBM Plex Sans Thai'" if L == "en" else "'IBM Plex Sans Thai', 'IBM Plex Sans Condensed'"
    return f"color: #15181C; font-family: {fam}, sans-serif; display: flex; flex-direction: column; padding: 30px 44px 24px 44px; position: relative"


def gauge(e, u, lim, accent, w=150):
    """มาตรวัดเล็ก: แถบเกณฑ์ ±lim, จุด = error, เส้น = ±U"""
    ax = Ax(6, w - 6, 0, 0, -lim * 1.4, lim * 1.4, 0, 1)
    out = [R(ax.sx(-lim), 6, ax.sx(lim) - ax.sx(-lim), 12, accent["tint"]),
           LN(ax.sx(-lim), 2, ax.sx(-lim), 22, INK_, 1.5), LN(ax.sx(lim), 2, ax.sx(lim), 22, INK_, 1.5),
           LN(ax.sx(0), 4, ax.sx(0), 20, "#9AA2AC")]
    if u:
        out.append(LN(ax.sx(e - u), 12, ax.sx(e + u), 12, INK_, 2.5))
    out.append(C(ax.sx(e), 12, 4.5, INK_))
    out.append(T(ax.sx(-lim), 36, f"−{lim:g}", anchor="middle", fill="#5A626C"))
    out.append(T(ax.sx(lim), 36, f"+{lim:g}", anchor="middle", fill="#5A626C"))
    return svg(w, 40, f"error {e:+.1f} % within ±{lim:g} %", out)


INK_ = "#15181C"


def head(L, title_key, accent, kind, page):
    big = "font-size: 30px; line-height: 34px; letter-spacing: -.01em" if L == "en" else "font-size: 28px; line-height: 36px"
    return f"""<div style="position: absolute; left: 0; top: 0; width: 794px; height: 5px; background: {accent["fill"]}"></div>
<header style="display: flex; justify-content: space-between; align-items: flex-end; gap: 20px">
  <div style="display: flex; flex-direction: column"><span class="lbl" style="letter-spacing: .08em; text-transform: uppercase">{other(title_key, L)}</span>
  <span style="{big}; font-weight: 700">{t(title_key, L)}</span></div>
  <div style="display: flex; gap: 10px; align-items: center">
    <div style="display: flex; flex-direction: column; align-items: flex-end"><span style="font-size: 14px; font-weight: 600">{t("company", L)}</span>
    <span class="lbl">{t(kind, L)}</span><span class="lbl">{t("addr", L)}</span></div>
    <div style="width: 46px; height: 46px; border: 1px solid #9AA2AC; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #5A626C">LOGO</div>
  </div>
</header>
<div style="display: flex; gap: 22px; margin-top: 10px; font-size: 13px; line-height: 18px; flex-wrap: wrap">{page}</div>"""


def meta_line(L, items, accent):
    return "".join(f'<span><span class="lbl">{a}</span> <b class="{num_cls(L)}" style="font-weight: 600{"; color: " + accent["ink"] if acc else ""}">{b}</b></span>'
                   for a, b, acc in items)


def section(key, L, content, mt=12, alt=True):
    h = sec("", key, L)
    if not alt:
        h = h.replace(f'<span class="sec-th">{other(key, L)}</span>', "")
    return f'<section style="display: flex; flex-direction: column; gap: 5px; margin-top: {mt}px; min-width: 0">{h}{content}</section>'


def cols(*parts, tpl=None, gap=22):
    tpl = tpl or f"repeat({len(parts)}, minmax(0, 1fr))"
    return f'<div style="display: grid; grid-template-columns: {tpl}; column-gap: {gap}px; align-items: start">{"".join(parts)}</div>'


def kv(rows, L):
    return '<div class="kv">' + "".join(f'<span class="lbl">{a}</span><span class="val{" " + num_cls(L) if (o and o[0]) else ""}">{b}</span>'
                                        for a, b, *o in rows) + "</div>"


def sigs(roles):
    return ('<div style="display: grid; grid-template-columns: repeat(%d, minmax(0, 1fr)); column-gap: 22px; margin-top: auto; padding-top: 10px">' % len(roles)
            + "".join(f'<div class="sig"><span class="lbl">{a}</span><div class="line"></div><span class="val">{b}</span><span class="lbl">{c}</span></div>' for a, b, c in roles)
            + "</div>")


def foot(L, form, no, pg, note=True):
    n = f'<span class="lbl" style="color: #3D444C">{t("disclaimer", L)}</span>' if note else ""
    return (f'<div style="margin-top: 8px; padding-top: 5px; border-top: 1px solid #C4CAD1; display: flex; flex-direction: column; gap: 2px">{n}'
            f'<div style="display: flex; justify-content: space-between" class="lbl"><span class="mono">{form} · Rev. 00</span><span>{t("generated", L)}</span><span class="mono">{no} · {pg}</span></div></div>')


def overall(L, word_key="pass", sub=""):
    return (f'<div style="border-left: 2px solid #15181C; align-items: center; justify-content: center"><span class="lbl">{t("overall", L)}</span>'
            f'<span style="font-size: 30px; line-height: 34px; font-weight: 700; letter-spacing: .08em">{t(word_key, L)}</span><span class="lbl">{sub}</span></div>')


def cal_band(L, D=CAL, A=INF):
    cells = "".join(f"""<div style="{"border-left: 1px solid #C4CAD1" if k else ""}"><span class="lbl">{t("c_set", L)} <b class="{num_cls(L)}" style="color: #15181C">{r["set"]:g} ml/h</b></span>
<span class="big">{f(r["err"], 1, True)}<span style="font-size: 18px"> %</span></span>{gauge(r["err"], r["U"], INFUSION["limit"], A)}
<span class="lbl">U ±{r["U"]:.1f} % · {t("pass", L)}</span></div>""" for k, r in enumerate(D["rates"]))
    return f'<div class="band" style="grid-template-columns: repeat(3, minmax(0, 1fr)) 150px">{cells}{overall(L, sub=t("c_err", L) + " · ±5 %")}</div>'


def cal_p1(L):
    A, D = INF, CAL
    body = f"""{head(L, "cal_title", A, "lab", meta_line(L, [(t("cert_no", L), D["cert"], False), (t("job_no", L), D["job"], True), (t("date_cal", L), dt(D["date"], L), False),
                                                         (t("date_issue", L), dt(D["issue"], L), False), ("", t("page", L, a=1, b=2), False)], A))}
{cal_band(L)}
{cols(section("customer", L, kv(customer_rows(L) + [(t("received", L), dt(D["received"], L), True)], L), alt=False),
      section("item", L, kv(item_rows(L), L), alt=False), section("balance", L, kv(balance_rows(L), L), alt=False))}
{section("env", L, '<div style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr))">' + "".join(
    f'<div style="display: flex; flex-direction: column"><span class="lbl">{a}</span><span class="val">{b}</span></div>' for a, b, *_ in env_rows(L)) + "</div>")}
{section("results", L, results_table(L) + f'<span class="lbl">{t("err_def", L)} {t("u_def", L)}</span>')}
{section("conformity", L, f'<span style="font-size: 13px; line-height: 18px">{t("conf_text", L)}</span><span class="lbl">{t("trace", L)}</span>', alt=False)}
{sigs(sig_roles(L, "cal"))}
{foot(L, "FM-CAL-A4", D["cert"], "1/2")}"""
    return dc(f"A4 Calibration p1 {L}", 794, 1123, FONT, CSS, root(L), body)


def cal_p2(L):
    A, D = INF, CAL
    method = kv([(t("method", L), t("method_v", L)), (t("volume", L), t("volume_v", L)), (t("intervals", L), t("intervals_inf", L))], L).replace(
        'class="kv"', 'class="kv" style="grid-template-columns: 96px minmax(0, 1fr)"')
    small = "".join(f"""<div style="display: flex; flex-direction: column; gap: 2px"><span class="val {num_cls(L)}" style="font-size: 15px">{r["set"]:.1f} ml/h · {f(r["err"], 1, True)} %</span>
{interval_chart(L, r, 214, 112, legend=False)}{rows_html(interval_rows(L, r)[1:2] + interval_rows(L, r)[5:6])}</div>""" for r in D["rates"])
    body = f"""{head(L, "cal_tech", A, "lab", meta_line(L, [(t("cert_no", L), D["cert"], False), (t("job_no", L), D["job"], True), ("", t("page", L, a=2, b=2), False)], A))}
{section("conf_chart", L, conformity_chart(L, D, 706, 24), mt=12)}
{section("per_interval", L, cols(small, tpl="repeat(3, minmax(0, 1fr))", gap=20).replace("</div></div></div>", "</div></div></div>", 1) if False else
         '<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 20px">' + small + "</div>" + f'<span class="lbl">{t("legend", L)}</span>')}
{section("method_sec", L, cols(method, ref_table(L)))}
{cols(section("corrections", L, rows_html(correction_rows(L) + record_rows(L)[:3]), alt=False),
      section("budget", L, budget_table(L), alt=False), tpl="0.85fr 1.15fr")}
<div style="margin-top: auto; text-align: center; font-size: 12px; letter-spacing: .12em; color: #5A626C">— {t("end_cert", L)} —</div>
{foot(L, "FM-CAL-A4", D["cert"], "2/2", note=False)}"""
    return dc(f"A4 Calibration p2 {L}", 794, 1123, FONT, CSS, root(L), body)


def inspection(L):
    A, D = SYR, INSP
    e = (D["meas"] - D["set"]) / D["set"] * 100
    left, right = checklist_tables(L)
    acc = ", ".join(S["acc"][0 if L == "en" else 1])
    band = f"""<div class="band" style="grid-template-columns: 1fr 1.2fr 1fr 150px">
<div><span class="lbl">{t("qual", L)}</span><span class="big">9<span style="font-size: 18px; color: #5A626C"> / 9</span></span><span class="lbl">+1 {t("na", L)}</span></div>
<div style="border-left: 1px solid #C4CAD1"><span class="lbl">{t("q_flow", L)} · {D["set"]:g} ml/h</span><span class="big">{f(e, 1, True)}<span style="font-size: 18px"> %</span></span>{gauge(e, 0, D["limit"], A)}</div>
<div style="border-left: 1px solid #C4CAD1"><span class="lbl">{t("q_occ", L)}</span><span class="big">{D["occ"][1].split()[0]}</span><span class="lbl">{t("min", L)} · {D["occ"][2]}</span></div>
{overall(L, "pass", t("fit", L))}</div>"""
    body = f"""{head(L, "insp_title", A, "service", meta_line(L, [(t("report_no", L), D["no"], False), (t("job_no", L), D["job"], True), (t("date_insp", L), dt(D["date"], L), False),
                                                            (t("next_due", L), dt(D["due"], L), False)], A))}
{band}
{cols(section("customer", L, kv(customer_rows(L, D), L), alt=False), section("equipment", L, kv(item_rows(L, D, "syr"), L), alt=False),
      section("balance", L, kv(balance_rows(L, full=False), L), alt=False))}
{section("qual", L, cols(left, right))}
{section("quant", L, quant_table(L, D) + f'<span class="lbl">{t("np_note", L)}</span>')}
{cols(section("accessories", L, f'<span class="val" style="font-weight: 400">{acc}</span>', alt=False), section("parts", L, parts_table(L), alt=False), tpl="0.6fr 1.4fr")}
{section("conclusion", L, f'<span style="font-size: 13px; line-height: 18px">{t("concl_text", L)}</span>', alt=False)}
{sigs(sig_roles(L, "insp"))}
{foot(L, "FM-INS-A4", D["no"], "1/1", note=False)}"""
    return dc(f"A4 Inspection {L}", 794, 1123, FONT, CSS, root(L), body)


def quicktest(L):
    A, D, i = INF, QT, (0 if L == "en" else 1)
    e = (D["meas"] - D["set"]) / D["set"] * 100
    band = f"""<div class="band" style="grid-template-columns: repeat(3, minmax(0, 1fr)) 150px">
<div><span class="lbl">{t("qt_rate", L)} → {t("c_meas", L)}</span><span class="big">{D["meas"]:.2f}</span><span class="lbl">ml/h · {t("c_set", L)} {D["set"]:.1f}</span></div>
<div style="border-left: 1px solid #C4CAD1"><span class="lbl">{t("c_err", L)}</span><span class="big">{f(e, 1, True)}<span style="font-size: 18px"> %</span></span>{gauge(e, 0, 5.0, A)}</div>
<div style="border-left: 1px solid #C4CAD1"><span class="lbl">{t("qt_time", L)}</span><span class="big">{mmss(D["secs"])}</span><span class="lbl">{t("min", L)} · {D["n"]} {t("cycles", L)}</span></div>
{overall(L, "pass", f'{t("limit", L)} ±5.0 %')}</div>"""
    body = f"""{head(L, "qt_title", A, "service", meta_line(L, [(t("report_no", L), D["no"], False), (t("job_no", L), D["job"], True), (t("date", L), dt(D["date"], L), False)], A))}
{band}
{cols(section("customer", L, kv([(t("hospital", L), HOSP["name"][i]), (t("department", L), D["dept"]), (t("province", L), HOSP["province"][i])], L), alt=False),
      section("equipment", L, kv([(t("mfr_model", L), "Terumo · TE-171"), (t("bal_sn", L), D["serial"], True),
                                   (t("admin_set", L), "[Set brand / model]" if L == "en" else "[ยี่ห้อ / รุ่นชุดสาย]")], L), alt=False),
      section("balance", L, kv(balance_rows(L, full=False), L), alt=False))}
<p style="margin: 14px 0 0 0; font-size: 13px; line-height: 18px; color: #3D444C">{t("qt_note", L)}</p>
{cols(f'<div class="sig" style="margin-top: 20px"><span class="lbl">{t("tested_by", L)}</span><div class="line"></div><span class="val">{t("n_tech", L)}</span><span class="lbl">{t("r_svc", L)} · {dt(D["date"][:10], L)}</span></div>',
      f'<div class="sig" style="margin-top: 20px"><span class="lbl">{t("remarks", L)}</span><div class="line" style="border-color: #C4CAD1"></div><div class="line" style="height: 24px; border-color: #C4CAD1"></div></div>')}
<div style="margin-top: auto"></div>
{foot(L, "FM-QT-A4", D["no"], "1/1", note=False)}"""
    return dc(f"A4 Quick Test {L}", 794, 1123, FONT, CSS, root(L), body)


def boards():
    out = []
    for L, pre, tag in (("en", "A4-", "EN"), ("th", "A4TH-", "TH")):
        out += [dict(name=f"{pre}Calibration-p1.dc.html", w=794, h=1123, title=f"A4 {tag} · Calibration p1 (front)", html=cal_p1(L)),
                dict(name=f"{pre}Calibration-p2.dc.html", w=794, h=1123, title=f"A4 {tag} · Calibration p2 (technical)", html=cal_p2(L)),
                dict(name=f"{pre}Inspection.dc.html", w=794, h=1123, title=f"A4 {tag} · Inspection", html=inspection(L)),
                dict(name=f"{pre}QuickTest.dc.html", w=794, h=1123, title=f"A4 {tag} · Quick Test", html=quicktest(L))]
    return out
