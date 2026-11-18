"""ชิ้นส่วนของหน้าเอกสาร FableA–E — โครง HTML เดียวกันทุกแบบ หน้าตาต่างกันที่ CSS ของแต่ละแบบ (styles.py)

แต่ละฟังก์ชันคืน HTML ของ 1 ส่วน · หน้า = <section class="page"> ขนาด A4 794 x 1123 px
V = ค่าของแบบ (styles.VARIANTS[...]): bw = ความกว้างเนื้อหา (px) สำหรับกราฟ, chart = สีของกราฟ, verdict_top
"""
from content import ADDRESS, BALANCE, CAL_ROWS, CHECKS, COMPANY, CUSTOMER, DATE, ENV, JOBS, TEXT, series

MINUS = "−"


def num(value: float, digits: int = 1, sign: bool = False) -> str:
    text = f"{abs(value):.{digits}f}"
    if value < 0:
        return MINUS + text
    return ("+" + text) if sign else text


def pick(pair, lang):
    return pair[0] if lang == "th" else pair[1]


# ------------------------------------------------------------------ กราฟ (SVG ขนาดจริง ไม่ย่อ/ขยาย — ตัวอักษร 12 px)
def _svg(w, h, body, st):
    return (f'<svg class="chart" xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{st["font"]}" font-size="12">{body}</svg>')


def interval_chart(values, target, tol, minutes, w, h, st, t, x_label=True):
    """flow ของแต่ละช่วงวัดเป็นขั้นบันได + แถบเกณฑ์ยอมรับ + เส้นค่าที่ตั้ง"""
    left, right, top, bottom = 50, 10, 8, 34 if x_label else 22
    span = target * tol / 100.0
    low, high = target - span * 1.7, target + span * 1.7
    low, high = min(low, min(values) - span * 0.1), max(high, max(values) + span * 0.1)
    pw, ph = w - left - right, h - top - bottom
    y = lambda v: top + ph * (high - v) / (high - low)
    x = lambda i: left + pw * i / len(values)
    out = [f'<rect x="{left}" y="{y(target + span):.1f}" width="{pw}" height="{y(target - span) - y(target + span):.1f}" fill="{st["band"]}"/>']
    for value in (target - span, target, target + span):
        dash = "" if value == target else ' stroke-dasharray="3 3"'
        out.append(f'<line x1="{left}" x2="{left + pw}" y1="{y(value):.1f}" y2="{y(value):.1f}" stroke="{st["mute"]}" stroke-width="0.8"{dash}/>')
        digits = 2 if target < 20 else 1 if target < 100 else 0
        out.append(f'<text x="{left - 6}" y="{y(value) + 4:.1f}" text-anchor="end" fill="{st["ink"]}">{value:.{digits}f}</text>')
    path = "".join(f'{"M" if i == 0 else "L"}{x(i):.1f},{y(v):.1f}H{x(i + 1):.1f}' for i, v in enumerate(values))
    out.append(f'<path d="{path}" fill="none" stroke="{st["acc"]}" stroke-width="1.5" stroke-linejoin="round"/>')
    out.append(f'<line x1="{left}" x2="{left}" y1="{top}" y2="{top + ph}" stroke="{st["ink"]}" stroke-width="1"/>')
    out.append(f'<line x1="{left}" x2="{left + pw}" y1="{top + ph}" y2="{top + ph}" stroke="{st["ink"]}" stroke-width="1"/>')
    step = 5 if minutes <= 20 else 10
    tick = 0
    while tick <= minutes + 0.01:
        tx = left + pw * tick / minutes
        out.append(f'<line x1="{tx:.1f}" x2="{tx:.1f}" y1="{top + ph}" y2="{top + ph + 4}" stroke="{st["ink"]}"/>')
        out.append(f'<text x="{tx:.1f}" y="{top + ph + 17}" text-anchor="middle" fill="{st["ink"]}">{tick}</text>')
        tick += step
    if x_label:
        out.append(f'<text x="{left + pw}" y="{h - 2}" text-anchor="end" fill="{st["mute"]}">{t["chart_x"]}</text>')
        out.append(f'<text x="{left + 6}" y="{y(target + span) + 14:.1f}" fill="{st["mute"]}">{t["chart_band"]}</text>')
    return _svg(w, h, "".join(out), st)


def error_chart(rows, tol, w, h, st, t):
    """ความคลาดเคลื่อนของแต่ละค่าที่ตั้ง พร้อมช่วง ±U เทียบแถบเกณฑ์"""
    left, right, top, bottom = 50, 14, 10, 38
    pw, ph = w - left - right, h - top - bottom
    limit = tol * 1.45
    y = lambda v: top + ph * (limit - v) / (2 * limit)
    out = [f'<rect x="{left}" y="{y(tol):.1f}" width="{pw}" height="{y(-tol) - y(tol):.1f}" fill="{st["band"]}"/>']
    for value in (-tol, 0, tol):
        dash = "" if value == 0 else ' stroke-dasharray="3 3"'
        out.append(f'<line x1="{left}" x2="{left + pw}" y1="{y(value):.1f}" y2="{y(value):.1f}" stroke="{st["mute"]}" stroke-width="0.8"{dash}/>')
        out.append(f'<text x="{left - 6}" y="{y(value) + 4:.1f}" text-anchor="end" fill="{st["ink"]}">{num(value, 0, value != 0)}</text>')
    out.append(f'<line x1="{left}" x2="{left}" y1="{top}" y2="{top + ph}" stroke="{st["ink"]}"/>')
    for i, row in enumerate(rows):
        cx = left + pw * (i + 0.5) / len(rows)
        err, u = row[4], row[6]
        out.append(f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{y(err + u):.1f}" y2="{y(err - u):.1f}" stroke="{st["acc"]}" stroke-width="1.6"/>')
        for edge in (err + u, err - u):
            out.append(f'<line x1="{cx - 7:.1f}" x2="{cx + 7:.1f}" y1="{y(edge):.1f}" y2="{y(edge):.1f}" stroke="{st["acc"]}" stroke-width="1.6"/>')
        out.append(f'<circle cx="{cx:.1f}" cy="{y(err):.1f}" r="4.2" fill="{st["acc"]}"/>')
        out.append(f'<text x="{cx + 12:.1f}" y="{y(err) + 4:.1f}" fill="{st["ink"]}" font-weight="600">{num(err, 1, True)} %</text>')
        out.append(f'<text x="{cx:.1f}" y="{top + ph + 17}" text-anchor="middle" fill="{st["ink"]}">{row[0]:g}</text>')
    out.append(f'<text x="{left + pw}" y="{h - 3}" text-anchor="end" fill="{st["mute"]}">{t["rate_axis"]}</text>')
    out.append(f'<text x="{left + 6}" y="{y(tol) + 14:.1f}" fill="{st["mute"]}">{t["chart_band"]}</text>')
    return _svg(w, h, "".join(out), st)


def gauge(error, tol, w, st):
    """มาตรวัดแนวนอน: ตำแหน่งของความคลาดเคลื่อนในช่วงเกณฑ์"""
    h, left, right = 46, 8, 8
    pw, limit = w - left - right, tol * 1.5
    x = lambda v: left + pw * (v + limit) / (2 * limit)
    out = [f'<line x1="{left}" x2="{left + pw}" y1="20" y2="20" stroke="{st["mute"]}" stroke-width="1"/>',
           f'<rect x="{x(-tol):.1f}" y="15" width="{x(tol) - x(-tol):.1f}" height="10" fill="{st["band"]}" stroke="{st["mute"]}" stroke-width="0.8"/>']
    for value in (-tol, 0, tol):
        out.append(f'<line x1="{x(value):.1f}" x2="{x(value):.1f}" y1="12" y2="28" stroke="{st["ink"]}" stroke-width="1"/>')
        out.append(f'<text x="{x(value):.1f}" y="42" text-anchor="middle" fill="{st["ink"]}">{num(value, 0, value != 0)} %</text>')
    cx = x(error)
    out.append(f'<path d="M{cx:.1f},18 l-6,-11 h12 z" fill="{st["acc"]}"/>')
    return _svg(w, h, "".join(out), st)


# ------------------------------------------------------------------ ชิ้นส่วนทั่วไป
def _english(title):
    """ชื่อหัวข้อภาษาอังกฤษของหัวข้อไทย (ป้ายกำกับด้านขวาแบบ A-TH) — เอกสารอังกฤษไม่มีป้ายนี้"""
    key = next((k for k, v in TEXT["th"].items() if v == title), None)
    return TEXT["en"][key].upper() if key else ""


def sec(no, title, body, cls=""):
    alt = _english(title)
    alt_html = f'<span class="en">{alt}</span>' if alt else ""
    return (f'<section class="sec {cls}"><h2><span class="no">{no}</span><span class="t">{title}</span>{alt_html}</h2>'
            f'<div class="body">{body}</div></section>')


def kv(pairs, cls=""):
    rows = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in pairs)
    return f'<dl class="kv {cls}">{rows}</dl>'


def header(t, lang, kind, title, pump, page, pages):
    pump_name = t[pump]
    other = t[pump + "_en"]
    sub = pump_name + (f' <span class="alt">{other}</span>' if other else "")
    return (f'<header class="hdr"><div class="co"><div class="mark">M.Care</div>'
            f'<div class="coname">{COMPANY}</div><div class="coaddr">{ADDRESS[lang]}</div></div>'
            f'<div class="ttl"><div class="kind">{t[kind]}</div><h1>{t[title]}</h1><div class="sub">{sub}</div></div>'
            f'<div class="pg">{t["page"]} {page} / {pages}</div></header>')


def footer(t, lang, job, page, pages):
    return (f'<footer class="foot"><span>{COMPANY} · {ADDRESS[lang]}</span>'
            f'<span>{job} · {t["page"]} {page} / {pages}</span></footer>')


def box(on=False):
    return f'<span class="bx{" on" if on else ""}"></span>'


def meta(t, lang, job, service):
    ticks = "".join(f'<span class="opt">{box(key == service)}{t[key]}</span>' for key in ("pm", "repair", "calib"))
    return (f'<div class="meta"><div><b>{t["job"]}</b><span class="jobno">{job["job"]}</span></div>'
            f'<div><b>{t["date"]}</b><span>{DATE[lang]}</span></div>'
            f'<div class="svc"><b>{t["service"]}</b><span class="opts">{ticks}</span></div></div>')


def who(t, lang, pump, job, device_title="device", brief=False):
    customer = [(t["hospital"], pick(CUSTOMER["hospital"], lang)), (t["dept"], pick(job["dept"], lang)),
                (t["province"], pick(CUSTOMER["province"], lang))]
    customer.append((t["contact"], f'{pick(CUSTOMER["contact"], lang)} · {CUSTOMER["tel"]}'))
    device = [(t["brand"], job["brand"]), (t["serial"], job["serial"]), (t["asset"], job["asset"]),
              (t["ivset" if pump == "infusion" else "syr"], pick(job["consumable"], lang))]
    def head(key):
        alt = _english(t[key])
        return f'<h3><span>{t[key]}</span>' + (f'<span class="en">{alt}</span>' if alt else "") + "</h3>"
    return (f'<div class="two who"><div>{head("customer")}{kv(customer)}</div>'
            f'<div>{head(device_title)}{kv(device)}</div></div>')


def checklist(t, lang, items, cols=2, head=True):
    """รายการตรวจ: ช่อง ผ่าน / ไม่ผ่าน / ไม่มี (CSS ของแต่ละแบบเลือกแสดงเป็นช่องติ๊กหรือเป็นคำ)"""
    show_head = head
    head = (f'<div class="hd"><span>{t["item"]}</span><span class="cols"><i>{t["ok"]}</i><i>{t["fail"]}</i>'
            f'<i>{t["na"]}</i></span></div>')
    rows = []
    for item in items:
        name = pick(item[:2], lang)
        detail = pick(item[2:4], lang) if len(item) > 2 else ""
        detail_html = f'<small>{detail}</small>' if detail else ""
        rows.append(f'<div class="it"><span class="nm">{name}{detail_html}</span>'
                    f'<span class="cols">{box(True)}{box()}{box()}</span><span class="word">{t["ok"]}</span></div>')
    return f'<div class="chk c{cols}{"" if show_head else " nohd"}">{head * cols if show_head else ""}{"".join(rows)}</div>'


def parts_block(t, lang, job):
    parts = job["parts"]
    if not parts:
        return f'<p class="none">{t["no_parts"]}</p>'
    claims = sum(1 for _, claim in parts if claim)
    tag = f' <i>{t["claim"]}</i>'
    items = "".join(f'<li>{pick(name, lang)}{tag if claim else ""}</li>' for name, claim in parts)
    summary = t["parts_n"].format(n=len(parts)) + (" · " + t["claim_n"].format(n=claims) if claims else "")
    return f'<p class="count">{summary}</p><ol class="parts">{items}</ol>'


def verdict(t, label, statement):
    ticks = f'<span class="vticks">{box(True)}{t["ok"]}{box()}{t["fail"]}</span>'
    return (f'<div class="verdict"><div class="vt"><b>{t[label]}</b><p>{statement}</p></div>'
            f'<div class="vr"><span class="vl">{t[label]}</span><span class="vv">{t["ok"]}</span>{ticks}</div></div>')


def signs(t, roles):
    cells = "".join(f'<div class="sg"><div class="ln"></div><b>{t[role]}</b><span class="hold">{t[who_]}</span>'
                    f'<span class="dt">{t["sign_date"]} ......... / ......... / .........</span></div>' for role, who_ in roles)
    return f'<div class="signs n{len(roles)}">{cells}</div>'


def occlusion(t, job):
    a, b, c = job["occl"]
    low, high = job["occl_limit"]
    mean = (a + b + c) / 3.0
    return (f'<table class="tb occl"><thead><tr><th class="l">{t["occl_row"]}</th><th>{t["time_no"]} 1</th><th>{t["time_no"]} 2</th>'
            f'<th>{t["time_no"]} 3</th><th>{t["mean"]}</th><th>{t["occl_limit"]}</th><th>{t["verdict"]}</th></tr></thead>'
            f'<tbody><tr><td class="l">{t["occl_level"]} {job["occl_level"]} · kPa</td><td>{a}</td><td>{b}</td><td>{c}</td>'
            f'<td><b>{mean:.0f}</b></td><td>{low} – {high}</td><td class="pass">{t["ok"]}</td></tr></tbody></table>')


def standard_and_conditions(t):
    balance = kv([(t["balance"], f'{BALANCE["model"]} · {BALANCE["serial"]}'),
                  (t["capacity"], BALANCE["capacity"]), (t["readability"], BALANCE["readability"])], "tight")
    cond = kv([(t["liquid"], t["water"]), (t["water_t"], ENV["water_t"]), (t["air_t"], ENV["air_t"]),
               (t["rh"], ENV["rh"]), (t["pressure"], ENV["pressure"])], "tight")
    return (f'<div class="two"><div><h3>{t["standard"]}</h3>{balance}<p class="note">{t["balance_check"]}</p></div>'
            f'<div><h3>{t["conditions"]}</h3>{cond}</div></div>')


def page(V, body, foot, cls=""):
    return f'<section class="page {cls}">{body}{foot}</section>'


# ------------------------------------------------------------------ หน้าเอกสาร
def inspection_page(lang, pump, V, page_no, pages, cal=False):
    """หน้ารายการตรวจสภาพ — cal=True: หน้า 1 ของชุด Calibration (ไม่มีผล rate ในหน้านี้)"""
    t, job = TEXT[lang], JOBS[pump]
    checks = {k: list(v) for k, v in CHECKS[pump].items()}
    flow = checks["performance"][-1]
    if cal:
        detail = (t["see_cal"], t["see_cal"])
    else:
        text = f'{job["rate"]:g} ml/h · {num(job["error"], 1, True)} % · {t["see_p2"]}'
        detail = (text, text)
    checks["performance"][-1] = (flow[0], flow[1], *detail)
    safety = (f'<div class="safe"><div><b>{t["supply"]}</b><span>{job["supply"]} V</span></div>'
              f'<div><b>{t["leak"]}</b><span>{job["leak"]} µA</span><em>{t["limit"]} {t["not_over"]} 500 µA</em></div>'
              f'<div class="sv"><b>{t["verdict"]}</b><span class="cols">{box(True)}</span><span class="word">{t["ok"]}</span>'
              f'<span class="okw">{t["ok"]}</span></div></div>')
    final = (f'<div class="fin"><span class="opt">{box(True)}{t["final_visual"]}</span>'
             f'<span class="opt">{box(True)}{t["final_label"]}</span></div>')
    received = " · ".join(pick(item, lang) for item in job["received"])
    extras = (f'<div class="extras"><div class="pt">{parts_block(t, lang, job)}</div>'
              f'<div class="rc"><b>{t["received"]}</b><span>{received}</span></div></div>')
    result = verdict(t, "result", t["insp_statement"])
    body = [header(t, lang, "insp_kind", "insp_title", pump, page_no, pages), meta(t, lang, job, "calib" if cal else "pm")]
    if V.get("verdict_top"):
        body.append(result)
    body += [who(t, lang, pump, job),
             sec(1, t["visual"], checklist(t, lang, checks["visual"])),
             sec(2, t["function"], checklist(t, lang, checks["function"], head=False)),
             sec(3, t["performance"], checklist(t, lang, checks["performance"], head=False)),
             f'<div class="pair">{sec(4, t["safety"], safety)}{sec(5, t["final"], final)}</div>',
             sec(6, t["parts"], extras, "extra")]
    if not V.get("verdict_top"):
        body.append(result)
    body.append(signs(t, [("inspected_by", "engineer"), ("received_by", "hospital_side")]))
    return page(V, "".join(body), footer(t, lang, job["job"], page_no, pages), f"insp {pump}")


def figures(t, job):
    cells = [(t["set_rate"], f'{job["rate"]:g}', "ml/h"), (t["measured"], f'{job["measured"]:.2f}', "ml/h"),
             (t["error"], num(job["error"], 1, True), "%"), (t["tolerance"], f'±{job["tol"]:g}', "%")]
    html = "".join(f'<div class="fig f{i}"><b>{label}</b><span>{value}</span><i>{unit}</i></div>'
                   for i, (label, value, unit) in enumerate(cells))
    return (f'<div class="figs">{html}<div class="fig fv"><b>{t["verdict"]}</b><span class="vv">{t["ok"]}</span></div></div>')


def measurement_page(lang, pump, V, page_no, pages):
    """หน้า 2 ของ Inspection: ผลวัด rate เดียว ครั้งเดียว + สัญญาณเตือนการอุดตัน 3 ครั้ง"""
    t, job = TEXT[lang], JOBS[pump]
    st, bw = V["chart"], V["bw"]
    values = series(job["measured"], job["spread"], job["count"], 4711 if pump == "infusion" else 1213)
    chart = interval_chart(values, job["rate"], job["tol"], job["minutes"], bw, 205, st, t)
    by_cycle = job["by_cycle"]
    details = kv([(t["duration"], f'{job["minutes"]:g} {t["minute"]}'),
                  (t["count" if by_cycle else "count_time"], str(job["count"])),
                  (t["cycle_time" if by_cycle else "interval_time"], f'{job["unit_time"]:g} {t["second"]}'),
                  (t["spread"], f'{job["spread"]:g} %')], "tight")
    ident = kv([(t["job"], job["job"]), (t["hospital"], f'{pick(CUSTOMER["hospital"], lang)} · {pick(job["dept"], lang)}'),
                (t["brand"], job["brand"]), (t["serial"], job["serial"])], "ident")
    method = (f'<div class="two"><div><h3>{t["how"]}</h3><p>{t["how_text"]}</p>'
              f'<p>{t["how_cycle" if by_cycle else "how_time"]}</p></div><div><h3>{t["detail"]}</h3>{details}</div></div>')
    body = [header(t, lang, "insp_kind", "meas_title", pump, page_no, pages), ident,
            sec(1, t["meas_title"], figures(t, job) + f'<div class="gg">{gauge(job["error"], job["tol"], min(bw, 420), st)}</div>', "hero"),
            sec(2, t["chart_flow" if by_cycle else "chart_flow_time"], chart, "plot"),
            sec(3, t["how_sec"], method),
            sec(4, t["occl"], f'<p class="lead">{t["occl_sub"]}</p>' + occlusion(t, job)),
            sec(5, t["tools"], standard_and_conditions(t)),
            f'<p class="fine">{t["validity"]} {t["method_ref"]}</p>']
    return page(V, "".join(body), footer(t, lang, job["job"], page_no, pages), f"meas {pump}")


def calibration_summary(lang, V, page_no, pages):
    t, job, pump = TEXT[lang], JOBS["infusion"], "infusion"
    rows = "".join(
        f'<tr><td class="l"><b>{r[0]:g}</b></td><td>{r[1]:g}</td><td>{r[2]}</td><td><b>{r[3]:.2f}</b></td>'
        f'<td><b>{num(r[4], 1, True)}</b></td><td>{r[5]:g}</td><td>{r[6]:g}</td><td>±{job["tol"]:g}</td>'
        f'<td class="pass">{t["ok"]}</td></tr>' for r in CAL_ROWS)
    table = (f'<table class="tb res"><thead><tr><th class="l">{t["set_rate"]}<i>ml/h</i></th><th>{t["duration"]}<i>{t["minute"]}</i></th>'
             f'<th>{t["count"]}</th><th>{t["measured"]}<i>ml/h</i></th><th>{t["error"]}<i>%</i></th><th>{t["spread"]}<i>%</i></th>'
             f'<th>{t["unc"]}<i>%</i></th><th>{t["tolerance"]}<i>%</i></th><th>{t["verdict"]}</th></tr></thead><tbody>{rows}</tbody></table>'
             f'<p class="note">{t["err_note"]} · {t["unc_note"]}</p>')
    result = verdict(t, "result_cal", t["cal_statement"])
    body = [header(t, lang, "cal_kind", "cal_title", pump, page_no, pages), meta(t, lang, job, "calib")]
    if V.get("verdict_top"):
        body.append(result)
    body += [who(t, lang, pump, job, "device_cal", brief=True),
             sec(1, t["results"], table, "results"),
             sec(2, t["occl"], f'<p class="lead">{t["occl_sub"]}</p>' + occlusion(t, job)),
             sec(3, t["tools"], standard_and_conditions(t) + f'<p class="note">{t["how_text"]} {t["trace"]}</p>')]
    if not V.get("verdict_top"):
        body.append(result)
    body.append(signs(t, [("calibrated_by", "engineer"), ("reviewed_by", "supervisor"), ("approved_by", "manager")]))
    return page(V, "".join(body), footer(t, lang, job["job"], page_no, pages), "cal")


def calibration_technical(lang, V, page_no, pages):
    t, job, pump = TEXT[lang], JOBS["infusion"], "infusion"
    st, bw = V["chart"], V["bw"]
    ident = kv([(t["job"], job["job"]), (t["hospital"], f'{pick(CUSTOMER["hospital"], lang)} · {pick(job["dept"], lang)}'),
                (t["brand"], job["brand"]), (t["serial"], job["serial"])], "ident")
    gap = 18
    small_w = (bw - 2 * gap) // 3
    multiples, stats = [], []
    for i, r in enumerate(CAL_ROWS):
        values = series(r[3], r[5], min(r[2], 90), 9001 + i * 77)
        chart = interval_chart(values, r[0], job["tol"], r[1], small_w, 170, st, t, x_label=False)
        multiples.append(f'<figure><figcaption><b>{r[0]:g} ml/h</b><span>{num(r[4], 1, True)} %</span></figcaption>{chart}</figure>')
        full = series(r[3], r[5], r[2], 9001 + i * 77)
        stats.append(f'<tr><td class="l"><b>{r[0]:g}</b></td><td>{r[2]}</td><td>{r[7]:g}</td><td>{min(full):.2f}</td>'
                     f'<td>{max(full):.2f}</td><td><b>{r[3]:.2f}</b></td><td>{r[5]:g}</td></tr>')
    stat_table = (f'<table class="tb"><thead><tr><th class="l">{t["set_rate"]}<i>ml/h</i></th><th>{t["count"]}</th>'
                  f'<th>{t["cycle_time"]}<i>{t["second"]}</i></th><th>{t["lowest"]}<i>ml/h</i></th><th>{t["highest"]}<i>ml/h</i></th>'
                  f'<th>{t["average"]}<i>ml/h</i></th><th>{t["spread"]}<i>%</i></th></tr></thead><tbody>{"".join(stats)}</tbody></table>')
    volume = kv([(t["water_t"], ENV["water_t"]), (t["density"], ENV["density"]), (t["per_gram"], ENV["per_gram"]),
                 (t["evap"], t["evap_v"])], "tight wide")
    body = [header(t, lang, "cal_kind", "tech_title", pump, page_no, pages), ident,
            sec(1, t["chart_err"], error_chart(CAL_ROWS, job["tol"], bw, 210, st, t), "plot"),
            sec(2, t["per_rate"], f'<div class="multi" style="gap:{gap}px">{"".join(multiples)}</div>', "plot"),
            sec(3, t["stats"], stat_table),
            sec(4, t["volume"], volume + f'<p class="note">{t["volume_note"]}</p>'),
            f'<p class="fine">{t["how_cycle"]} · {t["method_ref"]}</p>']
    return page(V, "".join(body), footer(t, lang, job["job"], page_no, pages), "tech")


def document(lang, V):
    """ทุกหน้าของ 1 ภาษา: [(ชื่อไฟล์ย่อย, html ของหน้า)]"""
    return [
        ("Inspection-Infusion-p1", inspection_page(lang, "infusion", V, 1, 2)),
        ("Inspection-Infusion-p2", measurement_page(lang, "infusion", V, 2, 2)),
        ("Inspection-Syringe-p1", inspection_page(lang, "syringe", V, 1, 2)),
        ("Inspection-Syringe-p2", measurement_page(lang, "syringe", V, 2, 2)),
        ("Calibration-p1-inspection", inspection_page(lang, "infusion", V, 1, 3, cal=True)),
        ("Calibration-p2-summary", calibration_summary(lang, V, 2, 3)),
        ("Calibration-p3-technical", calibration_technical(lang, V, 3, 3)),
    ]
