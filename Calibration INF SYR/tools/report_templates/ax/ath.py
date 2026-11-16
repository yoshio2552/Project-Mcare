"""แบบ A-TH — แบบ A ฉบับภาษาไทย (แยกจากต้นฉบับ A ซึ่งไม่ถูกแตะ)
โครงหน้า สี ฟอนต์ ตามแบบ A ทุกอย่าง · ข้อมูลตามแบบ A เดิม · แก้เฉพาะที่ผิด: หน้า 1 ล้นกระดาษ, Quick Test 31 รอบ → 8 รอบ
"""
from kit import (S, t, other, dt, kv, sec, item_rows, env_rows, results_table, interval_chart, interval_rows,
                 rows_html, correction_rows, record_rows, ref_table, checklist_tables, quant_table, parts_table,
                 mmss, CAL_A, INSP_A, QT_A, HOSP, INFUSION, INF, SYR, BASE_CSS, fonts, dc, f, num_cls)

L = "th"
FONT = fonts("IBM+Plex+Mono:wght@400;500", "IBM+Plex+Sans+Thai:wght@400;500;600;700", "IBM+Plex+Sans:wght@400;500;600;700")
CSS = BASE_CSS + """
.lbl{font-size:12px;line-height:17px;color:#5A626C}
.val{font-size:13px;line-height:19px;color:#15181C;font-weight:500}
.sec{display:flex;align-items:baseline;gap:10px;border-bottom:1px solid #15181C;padding-bottom:5px;margin:0}
.sec-n{font-family:'IBM Plex Mono',monospace;font-size:12px;color:#0B6FA4;font-weight:500}
.sec-t{font-size:14px;font-weight:600;color:#15181C}
.sec-th{font-size:12px;color:#5A626C;margin-left:auto;letter-spacing:.06em;text-transform:uppercase}
.kv{display:grid;grid-template-columns:150px minmax(0,1fr);row-gap:3px;column-gap:12px}
.kv.nar{grid-template-columns:92px minmax(0,1fr)}
table.t{width:100%;border-collapse:collapse}
table.t th{font-size:12px;font-weight:500;color:#5A626C;text-align:right;padding:5px 8px;background:#F3F5F7;border-bottom:1px solid #C4CAD1;line-height:16px;vertical-align:bottom}
table.t th:first-child,table.t td:first-child{text-align:left}
table.t td{font-size:13px;padding:6px 8px;border-bottom:1px solid #D5D9DE;text-align:right;color:#15181C;line-height:18px}
table.chk td:not(:first-child),table.chk th:not(:first-child){text-align:center;width:40px;padding-left:2px;padding-right:2px}
table.chk td{padding-top:4px;padding-bottom:4px}
.pass{font-weight:600;color:#166534}
.row{display:flex;justify-content:space-between;border-bottom:1px solid #E3E6EA;padding:3px 0;font-size:12px;line-height:17px}
.row span:first-child{color:#5A626C}
.row span:last-child{font-family:'IBM Plex Mono','IBM Plex Sans Thai',monospace;font-variant-numeric:tabular-nums;color:#15181C}
"""
ROOT = ("position: relative; color: #15181C; font-family: 'IBM Plex Sans Thai', 'IBM Plex Sans', sans-serif; "
        "display: flex; flex-direction: column; padding: 0 48px 30px 48px")


def bar(color):
    return f'<div style="position: absolute; left: 0; top: 0; width: 794px; height: 6px; background: {color}"></div>'


def head(title_key, sub, page, kind="lab"):
    return f"""
<header style="display: flex; justify-content: space-between; align-items: flex-start; padding-top: 28px; padding-bottom: 10px; border-bottom: 2px solid #15181C">
  <div style="display: flex; gap: 14px; align-items: center">
    <div style="width: 48px; height: 48px; border: 1px solid #9AA2AC; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #5A626C; letter-spacing: .08em">LOGO</div>
    <div style="display: flex; flex-direction: column; gap: 1px">
      <div style="font-size: 16px; font-weight: 600">{t("company", L)}</div>
      <div class="lbl">{t(kind, L)}</div>
      <div class="lbl">{t("addr", L)}</div>
    </div>
  </div>
  <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 2px">
    <div style="font-size: 24px; font-weight: 700; letter-spacing: .02em">{t(title_key, L)}</div>
    <div style="font-size: 12px; color: #5A626C; letter-spacing: .1em; text-transform: uppercase">{sub}</div>
    <div style="font-size: 12px; color: #5A626C; margin-top: 2px">{page}</div>
  </div>
</header>"""


def meta(cells, ink):
    out = []
    for k, (lab, val, accent) in enumerate(cells):
        pad = "padding: 8px 12px 8px 0" if k == 0 else "padding: 8px 12px; border-left: 1px solid #D5D9DE"
        col = f"; color: {ink}" if accent else ""
        out.append(f'<div style="{pad}; display: flex; flex-direction: column; gap: 1px"><span class="lbl">{lab}</span>'
                   f'<span style="font-size: 14px; font-weight: 500{col}">{val}</span></div>')
    return f'<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-bottom: 1px solid #D5D9DE">{"".join(out)}</div>'


def sigs(roles):
    cells = "".join(f"""<div style="display: flex; flex-direction: column; gap: 2px"><span class="lbl">{a}</span>
<div style="height: 28px; border-bottom: 1px solid #15181C"></div><span class="val">{b}</span><span class="lbl">{c}</span></div>""" for a, b, c in roles)
    return f'<div style="display: grid; grid-template-columns: repeat({len(roles)}, minmax(0, 1fr)); column-gap: 32px; margin-top: auto; padding-top: 10px">{cells}</div>'


def foot(form, no, pg, note=True):
    n = f'<span style="font-size: 12px; line-height: 17px; color: #3D444C">{t("disclaimer", L)}</span>' if note else ""
    return f"""<footer style="margin-top: 10px; padding-top: 6px; border-top: 1px solid #C4CAD1; display: flex; flex-direction: column; gap: 4px">{n}
<div style="display: flex; justify-content: space-between; font-size: 12px; color: #5A626C"><span class="mono">{form} · Rev. 00</span><span>{t("generated", L)}</span><span class="mono">{no} · {pg}</span></div></footer>"""


def cal_p1():
    D = CAL_A
    body = f"""{bar(INF["fill"])}
{head("cal_title", "Calibration Certificate", t("page", L, a=1, b=2))}
{meta([(t("cert_no", L), D["cert"], False), (t("job_no", L), D["job"], True), (t("date_cal", L), dt(D["date"], L), False),
       (t("date_issue", L), dt(D["issue"], L), False)], INF["ink"])}
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 32px; margin-top: 12px">
  <section style="display: flex; flex-direction: column; gap: 6px">{sec("01", "customer", L)}
  {kv([(t("hospital", L), HOSP["name"][1]), (t("department", L), D["dept"]), (t("province", L), HOSP["province"][1]),
       (t("received", L), dt(D["received"], L))], L=L)}</section>
  <section style="display: flex; flex-direction: column; gap: 8px">{sec("02", "item", L)}{kv(item_rows(L, D), L=L)}</section>
</div>
<section style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px">{sec("03", "method_sec", L)}
  <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 32px">
    {kv([(t("method", L), t("method_v", L)), (t("volume", L), t("volume_v", L)), (t("intervals", L), t("intervals_inf", L))], cls="kv nar", L=L)}
    {ref_table(L).replace(f'<tr><td>{t("thermometer", L)}</td><td class="tnum">[—]</td><td class="tnum">[—] / [—]</td></tr>', "")}
  </div>
  <p style="margin: 0; font-size: 12px; line-height: 17px; color: #3D444C">{t("trace", L)}</p>
</section>
<section style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px">{sec("04", "env", L)}
  <div style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr))">{"".join(
      f'<div style="display: flex; flex-direction: column; gap: 1px{"; border-left: 1px solid #D5D9DE; padding-left: 12px" if k else ""}"><span class="lbl">{a}</span><span class="val">{b}</span></div>'
      for k, (a, b, *_) in enumerate(env_rows(L, D)))}</div>
</section>
<section style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px">{sec("05", "results", L)}
  {results_table(L, D)}
  <div style="display: flex; flex-direction: column; gap: 2px; font-size: 12px; line-height: 17px; color: #3D444C"><span>{t("err_def", L)}</span><span>{t("u_def", L)}</span></div>
</section>
<div style="display: grid; grid-template-columns: minmax(0, 1fr) 160px; margin-top: 14px; border: 1px solid #15181C">
  <div style="padding: 10px 14px; display: flex; flex-direction: column; gap: 3px"><span style="font-size: 13px; font-weight: 600">{t("conformity", L)}</span>
  <span style="font-size: 12.5px; line-height: 19px; color: #3D444C">{t("conf_text", L)}</span></div>
  <div style="border-left: 1px solid #15181C; display: flex; flex-direction: column; align-items: center; justify-content: center"><span class="lbl">{t("overall", L)}</span>
  <span style="font-size: 30px; font-weight: 700; color: #166534">{t("pass", L)}</span></div>
</div>
{sigs([(t("calibrated_by", L), t("n_cal", L), f'{t("r_cal", L)} · {dt(D["date"], L)}'),
       (t("approved_by", L), t("n_app", L), f'{t("r_tm", L)} · {dt(D["issue"], L)}')])}
{foot("FM-CAL-01", D["cert"], "1/2")}"""
    return dc("Calibration A-TH p1", 794, 1123, FONT, CSS, ROOT, body)


def cal_p2():
    D = CAL_A
    blocks = "".join(f"""<div style="display: grid; grid-template-columns: 250px minmax(0, 1fr); column-gap: 24px; padding: 2px 0 10px 0; border-bottom: 1px solid #D5D9DE">
<div style="display: flex; flex-direction: column"><div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px">
<span class="mono" style="font-size: 16px; font-weight: 500">{r["set"]:.1f} ml/h</span><span class="pass" style="font-size: 13px">{t("pass", L)}</span></div>
{rows_html(interval_rows(L, r))}</div>{interval_chart(L, r)}</div>""" for r in D["rates"])
    body = f"""{bar(INF["fill"])}
<header style="display: flex; justify-content: space-between; align-items: flex-end; padding-top: 32px; padding-bottom: 10px; border-bottom: 2px solid #15181C">
  <div style="display: flex; flex-direction: column"><span style="font-size: 14px; font-weight: 600">{t("company", L)}</span>
  <span class="lbl">{t("cal_title", L)} — {t("cal_tech", L)}</span></div>
  <div style="display: flex; gap: 20px; font-size: 12px; color: #5A626C"><span>{t("cert_no", L)} <span class="mono" style="color: #15181C; font-weight: 500">{D["cert"]}</span></span><span>{t("page", L, a=2, b=2)}</span></div>
</header>
<section style="display: flex; flex-direction: column; gap: 10px; margin-top: 18px">{sec("06", "per_interval", L)}{blocks}</section>
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 32px; margin-top: 18px">
  <section style="display: flex; flex-direction: column; gap: 6px">{sec("07", "corrections", L)}<div>{rows_html(correction_rows(L, D))}</div></section>
  <section style="display: flex; flex-direction: column; gap: 6px">{sec("08", "record", L)}<div>{rows_html(record_rows(L))}</div></section>
</div>
<div style="margin-top: auto; text-align: center; font-size: 12px; letter-spacing: .1em; color: #5A626C">— {t("end_cert", L)} —</div>
{foot("FM-CAL-01", D["cert"], "2/2", note=False)}"""
    return dc("Calibration A-TH p2", 794, 1123, FONT, CSS, ROOT, body)


def inspection():
    D = INSP_A
    left, right = checklist_tables(L)
    acc = "".join(f'<span class="val" style="font-weight: 400">{a}</span>' for a in S["acc"][1])
    body = f"""{bar(SYR["fill"])}
{head("insp_title", "Inspection Report", t("page", L, a=1, b=1), "service")}
{meta([(t("report_no", L), D["no"], False), (t("job_no", L), D["job"], True), (t("date_insp", L), dt(D["date"], L), False),
       (t("next_due", L), dt(D["due"], L), False)], SYR["ink"])}
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 32px; margin-top: 12px">
  <section style="display: flex; flex-direction: column; gap: 6px">{sec("01", "customer", L).replace("#0B6FA4", SYR["ink"])}
  {kv([(t("hospital", L), HOSP["name"][1]), (t("department", L), D["dept"]), (t("province", L), HOSP["province"][1])], L=L)}</section>
  <section style="display: flex; flex-direction: column; gap: 8px">{sec("02", "equipment", L)}{kv(item_rows(L, D, "syr"), L=L)}</section>
</div>
<section style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px">{sec("03", "qual", L)}
  <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 24px; align-items: start">{left}{right}</div></section>
<section style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px">{sec("04", "quant", L)}{quant_table(L, D)}
  <span class="lbl">{"ตราชั่งมาตรฐาน"} A&amp;D GF-300 S/N 14654769 · {"อุณหภูมิน้ำ"} 23.1 °C · {t("np_note", L)}</span></section>
<div style="display: grid; grid-template-columns: 170px minmax(0, 1fr); column-gap: 28px; margin-top: 10px">
  <section style="display: flex; flex-direction: column; gap: 6px">{sec("05", "accessories", L).replace('<span class="sec-th">Accessories received</span>', "")}<div style="display: flex; flex-direction: column">{acc}</div></section>
  <section style="display: flex; flex-direction: column; gap: 6px">{sec("06", "parts", L)}{parts_table(L)}</section>
</div>
<div style="display: grid; grid-template-columns: minmax(0, 1fr) 160px; margin-top: 10px; border: 1px solid #15181C">
  <div style="padding: 8px 14px; display: flex; flex-direction: column; gap: 2px"><span style="font-size: 13px; font-weight: 600">{t("conclusion", L)}</span>
  <span style="font-size: 12.5px; line-height: 19px; color: #3D444C">{t("concl_text", L)}</span></div>
  <div style="border-left: 1px solid #15181C; display: flex; flex-direction: column; align-items: center; justify-content: center"><span class="lbl">{t("overall", L)}</span>
  <span style="font-size: 30px; font-weight: 700; color: #166534">{t("pass", L)}</span></div>
</div>
{sigs([(t("inspected_by", L), t("n_tech", L), f'{t("r_svc", L)} · {dt(D["date"], L)}'), (t("received_by", L), t("n_cust", L), f'{t("r_pos", L)} · {t("date", L)}')])}
{foot("FM-INS-01", D["no"], "1/1", note=False)}"""
    body = body.replace('class="sec-n">', f'class="sec-n" style="color: {SYR["ink"]}">')
    return dc("Inspection A-TH", 794, 1123, FONT, CSS, ROOT, body)


def label(kind):
    ok = kind == "pass"
    col = "#166534" if ok else "#B91C1C"
    rows = ([(t("l_test", L), t("l_test_v", L)), (t("date", L), dt("2026-11-13", L)), (t("next_due", L), "[—]"), (t("l_by", L), t("l_by_v", L))]
            if ok else [(t("l_reason", L), t("l_reason_v", L)), (t("date", L), dt("2026-11-13", L)),
                        (t("l_contact", L), t("l_contact_v", L)), (t("l_by", L), t("l_by_v", L))])
    tail = f'{t("company", L)} · โทร [—]' if ok else S["l_dnu_note"][1]
    kvs = "".join(f'<span class="lbl">{a}</span><span style="font-size: 13px">{b}</span>' for a, b in rows)
    return f"""<div style="border: 2px solid #15181C; display: grid; grid-template-columns: 34px minmax(0, 1fr); height: 196px">
<div style="background: {col}; display: flex; align-items: center; justify-content: center"><span style="writing-mode: vertical-rl; transform: rotate(180deg); color: #ffffff; font-size: 12px; font-weight: 700; letter-spacing: .1em">{t("tested", L)}</span></div>
<div style="padding: 10px 14px; display: flex; flex-direction: column; gap: 6px">
<div style="display: flex; justify-content: space-between; align-items: baseline"><span style="font-size: 22px; font-weight: 700; color: {col}">{t("pass" if ok else "dnu", L)}</span><span class="mono" style="font-size: 12px; color: #5A626C">{QT_A["job"]}</span></div>
<div style="display: grid; grid-template-columns: 112px minmax(0, 1fr); row-gap: 2px">{kvs}</div>
<span class="lbl" style="margin-top: auto; border-top: 1px solid #D5D9DE; padding-top: 4px">{tail}</span></div></div>"""


def quicktest():
    D = QT_A
    e = (D["meas"] - D["set"]) / D["set"] * 100
    big = lambda lab, v, u, b=True: (f'<div style="padding: 12px 14px; {"border-right: 1px solid #C4CAD1; " if b else ""}display: flex; flex-direction: column; gap: 2px">'
                                    f'<span class="lbl">{lab}</span><span class="mono" style="font-size: 30px; line-height: 36px; font-weight: 500">{v}</span><span class="lbl">{u}</span></div>')
    i = 1
    body = f"""{bar(INF["fill"])}
{head("qt_title", "Quick Function Test", "", "service")}
<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-bottom: 1px solid #D5D9DE">
  {"".join(f'<div style="padding: 8px 12px{" 8px 0" if k == 0 else "; border-left: 1px solid #D5D9DE"}; display: flex; flex-direction: column; gap: 1px"><span class="lbl">{a}</span><span style="font-size: 14px; font-weight: 500{c}">{b}</span></div>'
           for k, (a, b, c) in enumerate([(t("report_no", L), D["no"], ""), (t("job_no", L), D["job"], f"; color: {INF['ink']}"),
                                          (t("date", L), dt(D["date"], L), ""), (t("customer", L), f'{HOSP["name"][i]} · {D["dept"]}', "")]))}
</div>
<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-bottom: 1px solid #D5D9DE">
  {"".join(f'<div style="padding: 8px 12px{" 8px 0" if k == 0 else "; border-left: 1px solid #D5D9DE"}; display: flex; flex-direction: column; gap: 1px"><span class="lbl">{a}</span><span style="font-size: 14px; font-weight: 500">{b}</span></div>'
           for k, (a, b) in enumerate([(t("description", L), "เครื่องให้สารละลาย"), (t("mfr_model", L), "Terumo · TE-171"),
                                       (t("bal_sn", L), D["serial"]), (t("admin_set", L), "[ยี่ห้อ / รุ่นชุดสาย]")]))}
</div>
<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)) 150px; border: 1px solid #15181C; margin-top: 20px">
  {big(t("qt_rate", L), f'{D["set"]:.1f}', "ml/h")}{big(t("c_meas", L), f'{D["meas"]:.2f}', "ml/h")}
  {big(t("c_err", L), f(e, 1, True), f'% · {t("limit", L)} ±5.0 %')}{big(t("qt_time", L), mmss(D["secs"]), f'{t("min", L)} · {D["n"]} {t("cycles", L)}', False)}
  <div style="border-left: 1px solid #15181C; display: flex; flex-direction: column; align-items: center; justify-content: center"><span class="lbl">{t("c_res", L)}</span>
  <span style="font-size: 30px; font-weight: 700; color: #166534">{t("pass", L)}</span></div>
</div>
<p style="margin: 12px 0 0 0; font-size: 12.5px; line-height: 19px; color: #3D444C">{t("qt_note", L)}</p>
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 32px; margin-top: 18px">
  <div style="display: flex; flex-direction: column; gap: 2px"><span class="lbl">{t("tested_by", L)}</span><div style="height: 34px; border-bottom: 1px solid #15181C"></div><span class="val">{t("n_tech", L)}</span></div>
  <div style="display: flex; flex-direction: column; gap: 2px"><span class="lbl">{t("remarks", L)}</span><div style="height: 34px; border-bottom: 1px solid #C4CAD1"></div><div style="height: 26px; border-bottom: 1px solid #C4CAD1"></div></div>
</div>
<div style="display: flex; align-items: center; gap: 10px; margin-top: 26px"><span style="font-size: 14px; color: #5A626C">✂</span>
<div style="flex: 1; border-top: 1px dashed #5A626C"></div><span class="lbl">{t("labels_cut", L)}</span></div>
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 32px; margin-top: 14px">{label("pass")}{label("dnu")}</div>
<span class="lbl" style="margin-top: 6px">{t("labels_note", L)}</span>
<div style="margin-top: auto"></div>
{foot("FM-QT-01", D["no"], "1/1", note=False)}"""
    return dc("Quick Test A-TH", 794, 1123, FONT, CSS, ROOT, body)


HEADING = "แบบ A-TH — แบบ A ฉบับภาษาไทย (ต้นฉบับ A ไม่แก้) · แก้เฉพาะหน้า 1 ที่ล้นกระดาษ และ Quick Test 31 รอบ → 8 รอบ"


def boards():
    return [
        dict(name="ATH-Calibration-p1.dc.html", w=794, h=1123, title="A-TH · Calibration p1 · ใบรับรองผลการสอบเทียบ", html=cal_p1()),
        dict(name="ATH-Calibration-p2.dc.html", w=794, h=1123, title="A-TH · Calibration p2 · รายละเอียดทางเทคนิค", html=cal_p2()),
        dict(name="ATH-Inspection.dc.html", w=794, h=1123, title="A-TH · Inspection · รายงานการตรวจสภาพ", html=inspection()),
        dict(name="ATH-QuickTest.dc.html", w=794, h=1123, title="A-TH · Quick Test · ทดสอบการทำงานเบื้องต้น", html=quicktest()),
    ]
