"""แบบ FableF — หน้าตาของ A-TH ตัวจริง (CSS, สี, ฟอนต์, กราฟ ยกมาจาก tools/report_templates/ax/ath.py + kit.py)
กับโครงเนื้อหาชุดใหม่ (content.py): Inspection แยก Infusion / Syringe 2 หน้า · Calibration 3 หน้า · Occlusion 3 ครั้ง

ต่างจากแบบ FableA–E ตรงที่ไม่ใช้โครง HTML ร่วมของ blocks.py — เขียนหน้าเองทั้งหมดเพื่อให้ได้ "มิติ" แบบ A-TH:
  ตัวเลขใช้ IBM Plex Mono · แถบข้อมูล 4 ช่องใต้หัว · กล่องตัวเลขใหญ่ · บล็อกผลราย rate (ตารางค่าซ้าย กราฟขวา)
  กราฟ error รายช่วง: แถบเกณฑ์สีอ่อน เส้นประเกณฑ์ เส้นค่าเฉลี่ยสีส้ม · ลายเซ็นดันชิดล่าง (หน้าเต็มพอดี)
สิ่งที่ตัดออกจาก A-TH ตามที่ผู้ใช้สั่ง: เลขที่รายงาน/ใบรับรอง, บันทึกข้อมูลดิบ, วงเล็บ, "ก่อนแก้ / หลังแก้ / การแก้ค่าที่ใช้", Ground
"""
from content import ADDRESS, BALANCE, CAL_ROWS, CHECKS, COMPANY, CUSTOMER, DATE, ENV, JOBS, TEXT, series

INK, GREY, DIM = "#15181C", "#5A626C", "#9AA2AC"
PUMP = {"infusion": dict(ink="#0B6FA4", fill="#38BDF8", tint="#E0F2FE"),
        "syringe": dict(ink="#B0306A", fill="#F472B6", tint="#FCE7F3")}
ORANGE = "#E0731A"

CSS = """
* { box-sizing: border-box }
html, body { margin: 0 }
.ath { width: 794px; height: 1123px; position: relative; overflow: hidden; background: #fff; color: #15181C; margin: 0;
       font-family: 'IBM Plex Sans Thai', 'IBM Plex Sans', sans-serif; font-size: 13px; line-height: 19px;
       display: flex; flex-direction: column; padding: 0 48px 30px 48px }
.ath > * { flex-shrink: 0 }
.ath p { margin: 0 }
.mono { font-family: 'IBM Plex Mono', 'IBM Plex Sans Thai', monospace; font-variant-numeric: tabular-nums }
.lbl { font-size: 12px; line-height: 17px; color: #5A626C }
.val { font-size: 13px; line-height: 19px; color: #15181C; font-weight: 500 }
.bar { position: absolute; left: 0; top: 0; width: 794px; height: 6px }
.sec { display: flex; align-items: baseline; gap: 10px; border-bottom: 1px solid #15181C; padding-bottom: 5px; margin: 0 }
.sec-n { font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 500 }
.sec-t { font-size: 14px; font-weight: 600 }
.sec-th { font-size: 12px; color: #5A626C; margin-left: auto; letter-spacing: .06em; text-transform: uppercase }
.kv { display: grid; grid-template-columns: 104px minmax(0, 1fr); row-gap: 3px; column-gap: 12px }
.kv.nar { grid-template-columns: 92px minmax(0, 1fr) }
.two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 32px }
.blk { display: flex; flex-direction: column; gap: 7px }
table.t { width: 100%; border-collapse: collapse }
table.t th { font-size: 12px; font-weight: 500; color: #5A626C; text-align: right; padding: 5px 8px; background: #F3F5F7;
             border-bottom: 1px solid #C4CAD1; line-height: 16px; vertical-align: bottom }
table.t th:first-child, table.t td:first-child { text-align: left }
table.t td { font-size: 13px; padding: 6px 8px; border-bottom: 1px solid #D5D9DE; text-align: right; line-height: 18px }
table.t td.num { font-family: 'IBM Plex Mono', 'IBM Plex Sans Thai', monospace; font-variant-numeric: tabular-nums }
table.chk td:not(:first-child), table.chk th:not(:first-child) { text-align: center; width: 40px; padding-left: 2px; padding-right: 2px }
table.chk td { padding-top: 2px; padding-bottom: 2px }
table.perf td { padding-top: 4px; padding-bottom: 4px }
table.chk tr.grp td { font-size: 12px; font-weight: 600; color: #5A626C; letter-spacing: .04em; padding-top: 6px; padding-bottom: 2px; border-bottom: 1px solid #C4CAD1 }
.box { display: inline-flex; width: 13px; height: 13px; border: 1px solid #5A626C; vertical-align: middle; align-items: center;
       justify-content: center; font-size: 12px; line-height: 11px; font-weight: 700 }
.pass { font-weight: 600; color: #166534 }
.row { display: flex; justify-content: space-between; gap: 10px; border-bottom: 1px solid #E3E6EA; padding: 3px 0; font-size: 12px; line-height: 17px }
.row span:first-child { color: #5A626C }
.row span:last-child { font-family: 'IBM Plex Mono', 'IBM Plex Sans Thai', monospace; font-variant-numeric: tabular-nums; color: #15181C; text-align: right }
.row .tag { font-family: 'IBM Plex Sans Thai', sans-serif !important; font-weight: 600 }
.note { font-size: 12px; line-height: 17px; color: #3D444C }
svg text { font-family: 'IBM Plex Sans', 'IBM Plex Sans Thai', sans-serif }
.foot { margin-top: 10px; padding-top: 6px; border-top: 1px solid #C4CAD1; display: flex; justify-content: space-between; font-size: 12px; color: #5A626C }
"""

# ข้อความเฉพาะแบบนี้ (ไทย, อังกฤษ)
X = dict(
    service=("ศูนย์บริการเครื่องมือแพทย์", "Medical equipment service"),
    lab=("ห้องปฏิบัติการสอบเทียบเครื่องมือแพทย์", "Medical equipment calibration laboratory"),
    page=("หน้า {a} / {b}", "Page {a} / {b}"), made=("จัดทำโดย DeltaM 0.3.0", "Produced with DeltaM 0.3.0"),
    date_insp=("วันที่ตรวจ", "Inspection date"), date_cal=("วันที่สอบเทียบ", "Calibration date"),
    check=("ตรวจสภาพและการทำงาน", "Condition and function"), check_en="QUALITATIVE INSPECTION",
    grp_visual=("สภาพภายนอก", "Visual"), grp_function=("การทำงาน", "Function"),
    perf=("ทดสอบสมรรถนะ", "Performance tests"), perf_en="QUANTITATIVE TESTS",
    c_test=("รายการทดสอบ", "Test"), c_set=("ค่าตั้ง", "Setting"), c_meas=("ค่าที่วัดได้", "Measured"),
    c_limit=("เกณฑ์", "Limit"), c_res=("ผล", "Result"),
    q_flow=("ความแม่นยำอัตราการไหล", "Flow rate accuracy"), q_occl=("สัญญาณเตือนการอุดตัน", "Occlusion alarm"),
    q_air=("ตรวจจับฟองอากาศ", "Air-in-line detection"), q_batt=("การทำงานด้วยแบตเตอรี่", "Battery operation"),
    q_leak=("กระแสรั่วของเครื่อง", "Equipment leakage current"), q_size=("ตรวจจับขนาดกระบอกฉีด", "Syringe size detection"),
    q_empty=("เตือนยาใกล้หมด", "Nearly empty alarm"),
    three=("วัด 3 ครั้ง", "3 runs"), level=("ระดับ", "level"), alarms=("เครื่องเตือน", "alarm sounds"), must=("ต้องเตือน", "must alarm"),
    air_in=("ฟองอากาศในสาย", "air in the line"), at_mark=("ถึงระยะใกล้หมด", "at the near-empty mark"),
    reads=("อ่านได้", "reads"), same=("ตรงขนาด", "same size"), supply=("ไฟเข้า", "supply"),
    not_over=("ไม่เกิน", "not over"), at_least=("ไม่ต่ำกว่า", "at least"), see2=("ดูหน้า 2", "see page 2"),
    acc=("อุปกรณ์ที่รับมา", "Accessories"), svc_pm=("บำรุงรักษา", "Maintenance"), svc_cal=("สอบเทียบ", "Calibration"), acc_en="RECEIVED",
    parts=("อะไหล่ที่เปลี่ยน", "Parts replaced"), parts_en="PARTS REPLACED",
    claim=("เคลมประกัน", "warranty"), paid=("เปลี่ยนใหม่", "replaced"),
    parts_sum=("รวม {n} รายการ · เคลมประกัน {c} รายการ", "{n} parts · {c} under warranty"),
    concl=("สรุปผล", "Conclusion"), overall=("ผลรวม", "Overall"),
    fin1=("ตรวจความเรียบร้อยทั้งเครื่องแล้ว", "Whole unit checked"), fin2=("ติดป้ายตรวจสภาพแล้ว", "Inspection label attached"),
    big_rate=("ค่าที่ตั้ง", "Set rate"), big_meas=("ค่าที่วัดได้", "Measured"), big_err=("คลาดเคลื่อน", "Error"), big_time=("เวลาที่วัด", "Measuring time"),
    limit=("เกณฑ์", "limit"), cycles=("รอบปั๊ม", "pump cycles"), intervals=("ช่วงวัด", "intervals"),
    per=("ผลรายช่วงวัด", "Results per interval"), per_en="RESULTS PER INTERVAL",
    r_n_cycle=("จำนวนรอบปั๊ม", "Pump cycles"), r_n_time=("จำนวนช่วงวัด", "Intervals"),
    r_period=("เวลาต่อรอบเฉลี่ย", "Mean time per cycle"), r_length=("ความยาวช่วงวัด", "Interval length"),
    r_vol=("ปริมาตรต่อรอบ", "Volume per cycle"), r_vol_time=("ปริมาตรต่อช่วง", "Volume per interval"),
    r_meas=("ค่าที่วัดได้", "Measured"), r_err=("คลาดเคลื่อน", "Error"), r_sd=("การกระจาย ±2SD", "Spread ±2SD"), r_u=("ความไม่แน่นอน U", "Uncertainty U"),
    r_split=("การแบ่งช่วงวัด", "Intervals follow"), by_cycle=("ตามรอบปั๊ม", "the pump cycle"), by_time=("ตามเวลา", "time"),
    x_axis=("ช่วงวัดที่", "Interval"), legend=("— ค่าแต่ละช่วง   — ค่าเฉลี่ย   - - เกณฑ์ ±{t:g} %", "— each interval   — mean   - - limit ±{t:g} %"),
    occl=("สัญญาณเตือนการอุดตัน", "Occlusion alarm"), occl_en="OCCLUSION ALARM", run=("ครั้งที่", "Run"), mean=("ค่าเฉลี่ย", "Mean"),
    occl_set=("ระดับที่ตั้ง", "Level set"), occl_lim=("เกณฑ์ของผู้ผลิต", "Manufacturer's limit"),
    cond=("เครื่องชั่งและสภาวะขณะวัด", "Balance and conditions"), cond_en="STANDARD AND CONDITIONS",
    vol=("การคิดปริมาตรจากน้ำหนัก", "From weight to volume"), vol_en="WEIGHT TO VOLUME",
    bal=("เครื่องชั่งมาตรฐาน", "Reference balance"), bal_en="REFERENCE BALANCE",
    b_model=("รุ่น", "Model"), b_sn=("หมายเลขเครื่อง", "Serial no."), b_cap=("พิกัด", "Capacity"), b_read=("อ่านละเอียด", "Readability"),
    b_check=("ตรวจด้วยตุ้ม 50 g ก่อนใช้", "50 g check weight"),
    method=("วิธีและเครื่องมือมาตรฐาน", "Method and reference standard"), method_en="METHOD AND REFERENCE STANDARDS",
    m_how=("วิธีการ", "Method"), m_how_v=("วัดอัตราการไหลด้วยวิธีชั่งน้ำหนัก อ้างอิง IEC 60601-2-24", "Gravimetric flow measurement with reference to IEC 60601-2-24"),
    m_vol=("ปริมาตร", "Volume"), m_vol_v=("คิดจากน้ำหนักตาม ISO 4787", "From weight, to ISO 4787"),
    m_split=("ช่วงวัด", "Intervals"), m_split_v=("ตามรอบปั๊ม จากยอดถึงยอด", "Pump cycle, peak to peak"),
    std=("เครื่องมือมาตรฐาน", "Reference standard"), std_sn=("หมายเลขเครื่อง", "Serial no."), std_cap=("พิกัด · อ่านละเอียด", "Capacity · readability"),
    env=("สภาวะแวดล้อม", "Environmental conditions"), env_en="ENVIRONMENTAL CONDITIONS",
    res=("ผลการสอบเทียบ", "Calibration results"), res_en="RESULTS",
    conf=("ข้อความแสดงความสอดคล้อง", "Statement of conformity"),
    end_insp=("สิ้นสุดรายงาน", "End of report"), end_cal=("สิ้นสุดใบรับรอง", "End of certificate"),
    tech=("รายละเอียดทางเทคนิค", "Technical details"), meas_sub=("ผลวัดอัตราการไหล", "Flow rate measurement"),
    date_line=("วันที่ ....... / ....... / .......", "Date ....... / ....... / ......."),
)


class Doc:
    """ตัวช่วยของ 1 ภาษา × 1 ชนิดเครื่อง"""

    def __init__(self, lang, pump):
        self.lang, self.pump, self.i = lang, pump, 0 if lang == "th" else 1
        self.t, self.job, self.c = TEXT[lang], JOBS[pump], PUMP[pump]

    def x(self, key, **kw):
        text = X[key][self.i]
        return text.format(**kw) if kw else text

    def p(self, pair):
        return pair[self.i]

    def sec(self, n, key, en_key=None):
        en = X.get(en_key or key + "_en", "") if self.lang == "th" else ""
        right = f'<span class="sec-th">{en}</span>' if en else ""
        return (f'<h2 class="sec"><span class="sec-n" style="color: {self.c["ink"]}">{n:02d}</span>'
                f'<span class="sec-t">{self.x(key)}</span>{right}</h2>')

    def sec_t(self, n, title, en=""):
        right = f'<span class="sec-th">{en}</span>' if en and self.lang == "th" else ""
        return (f'<h2 class="sec"><span class="sec-n" style="color: {self.c["ink"]}">{n:02d}</span>'
                f'<span class="sec-t">{title}</span>{right}</h2>')


def minus(value, digits=1, sign=True):
    text = f"{abs(value):.{digits}f}"
    return ("−" if value < 0 else "+" if sign else "") + text


def kv(rows, cls="kv"):
    return f'<div class="{cls}">' + "".join(f'<span class="lbl">{a}</span><span class="val">{b}</span>' for a, b in rows) + "</div>"


def rows_html(rows):
    return "".join(f'<div class="row"><span>{a}</span><span>{b}</span></div>' for a, b in rows)


def head(d, title, sub, page, kind="service"):
    return f"""<div class="bar" style="background: {d.c["fill"]}"></div>
<header style="display: flex; justify-content: space-between; align-items: flex-start; padding-top: 28px; padding-bottom: 10px; border-bottom: 2px solid #15181C">
  <div style="display: flex; gap: 14px; align-items: center">
    <div style="width: 48px; height: 48px; border: 1px solid #9AA2AC; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #5A626C; letter-spacing: .08em">LOGO</div>
    <div style="display: flex; flex-direction: column; gap: 1px">
      <div style="font-size: 16px; font-weight: 600">{COMPANY}</div>
      <div class="lbl">{d.x(kind)}</div><div class="lbl">{ADDRESS[d.lang]}</div>
    </div>
  </div>
  <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 2px">
    <div style="font-size: 24px; font-weight: 700; letter-spacing: .02em">{title}</div>
    <div style="font-size: 12px; color: #5A626C; letter-spacing: .1em; text-transform: uppercase">{sub}</div>
    <div style="font-size: 12px; color: #5A626C; margin-top: 2px">{page}</div>
  </div>
</header>"""


def head_small(d, line, page):
    return f"""<div class="bar" style="background: {d.c["fill"]}"></div>
<header style="display: flex; justify-content: space-between; align-items: flex-end; padding-top: 32px; padding-bottom: 10px; border-bottom: 2px solid #15181C">
  <div style="display: flex; flex-direction: column"><span style="font-size: 14px; font-weight: 600">{COMPANY}</span><span class="lbl">{line}</span></div>
  <div style="display: flex; gap: 20px; font-size: 12px; color: #5A626C"><span>{d.t["job"]} <span class="mono" style="color: {d.c["ink"]}; font-weight: 500">{d.job["job"]}</span></span><span>{page}</span></div>
</header>"""


def meta(d, cells, cols=None):
    out = []
    for k, (lab, val, accent) in enumerate(cells):
        pad = "padding: 8px 12px 8px 0" if k == 0 else "padding: 8px 12px; border-left: 1px solid #D5D9DE"
        col = f"; color: {d.c['ink']}" if accent else ""
        out.append(f'<div style="{pad}; display: flex; flex-direction: column; gap: 1px"><span class="lbl">{lab}</span>'
                   f'<span style="font-size: 14px; font-weight: 500{col}">{val}</span></div>')
    cols = cols or f"repeat({len(cells)}, minmax(0, 1fr))"
    return f'<div style="display: grid; grid-template-columns: {cols}; border-bottom: 1px solid #D5D9DE">{"".join(out)}</div>'


def sigs(d, roles):
    cells = "".join(f"""<div style="display: flex; flex-direction: column; gap: 2px"><span class="lbl">{d.t[a]}</span>
<div style="height: 30px; border-bottom: 1px solid #15181C"></div><span class="val">{d.t[b]}</span><span class="lbl">{d.x("date_line")}</span></div>""" for a, b in roles)
    return f'<div style="display: grid; grid-template-columns: repeat({len(roles)}, minmax(0, 1fr)); column-gap: 32px; margin-top: auto; padding-top: 12px">{cells}</div>'


def foot(d, page):
    return (f'<footer class="foot"><span class="mono">{COMPANY}</span><span>{d.x("made")}</span>'
            f'<span class="mono">{d.job["job"]} · {page}</span></footer>')


def who(d, device_key):
    t, job = d.t, d.job
    customer = [(t["hospital"], d.p(CUSTOMER["hospital"])), (t["dept"], d.p(job["dept"])), (t["province"], d.p(CUSTOMER["province"])),
                (t["contact"], f'{d.p(CUSTOMER["contact"])} · {CUSTOMER["tel"]}')]
    device = [(t["brand"], job["brand"]), (t["serial"], job["serial"]), (t["asset"], job["asset"]),
              (t["ivset" if d.pump == "infusion" else "syr"], d.p(job["consumable"]))]
    return (f'<div class="two" style="margin-top: 12px"><section class="blk">{d.sec_t(1, t["customer"], "CUSTOMER")}{kv(customer)}</section>'
            f'<section class="blk">{d.sec_t(2, t[device_key], "EQUIPMENT")}{kv(device)}</section></div>')


def check_tables(d):
    """สภาพภายนอก (ซ้าย) + การทำงาน (ขวา) — หัวตารางเป็นชื่อกลุ่ม แบบตารางคู่ของ A-TH"""
    t = d.t
    lists = CHECKS[d.pump]
    def table(title, items):
        body = "".join(f'<tr><td>{d.p(item[:2])}</td><td><span class="box">✓</span></td><td><span class="box"></span></td>'
                       f'<td><span class="box"></span></td></tr>' for item in items)
        return (f'<table class="t chk"><thead><tr><th>{title}</th><th>{t["ok"]}</th><th>{t["fail"]}</th><th>{t["na"]}</th></tr></thead>'
                f'<tbody>{body}</tbody></table>')
    return (f'<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 24px; align-items: start">'
            f'{table(d.x("grp_visual"), lists["visual"])}{table(d.x("grp_function"), lists["function"])}</div>')


def perf_table(d, cal):
    job, x = d.job, d.x
    ok = f'<span class="pass">{d.t["ok"]}</span>'
    a, b, c = job["occl"]
    low, high = job["occl_limit"]
    if cal:
        flow = (x("q_flow"), "10 · 50 · 200 ml/h", x("see2"), f'±{job["tol"]:g} %')
    else:
        flow = (x("q_flow"), f'{job["rate"]:g} ml/h · {job["minutes"]:g} {d.t["minute"]}',
                f'{job["measured"]:.2f} ml/h · {minus(job["error"])} %', f'±{job["tol"]:g} %')
    rows = [flow, (x("q_occl"), f'{x("level")} {job["occl_level"]} · {x("three")}', f'{a} · {b} · {c} kPa', f'{low} – {high} kPa')]
    if d.pump == "infusion":
        rows += [(x("q_air"), x("air_in"), x("alarms"), x("must")),
                 (x("q_batt"), "25 ml/h", f'120 {d.t["minute"]}', f'{x("at_least")} 120 {d.t["minute"]}')]
    else:
        rows += [(x("q_size"), "50 ml", f'{x("reads")} 50 ml', x("same")),
                 (x("q_empty"), x("at_mark"), x("alarms"), x("must"))]
    rows.append((x("q_leak"), f'{x("supply")} {job["supply"]} V', f'{job["leak"]} µA', f'{x("not_over")} 500 µA'))
    cell = lambda v: f'<td class="num">{v}</td>' if any(ch.isdigit() for ch in v) else f'<td>{v}</td>'
    body = "".join(f'<tr><td>{r[0]}</td>{cell(r[1])}{cell(r[2])}{cell(r[3])}<td>{ok}</td></tr>' for r in rows)
    return (f'<table class="t perf"><thead><tr><th>{x("c_test")}</th><th>{x("c_set")}</th><th>{x("c_meas")}</th><th>{x("c_limit")}</th>'
            f'<th>{x("c_res")}</th></tr></thead><tbody>{body}</tbody></table>')


def parts(d):
    """อะไหล่: แถวแบบ .row ไหลเป็น 3 คอลัมน์ (เติมลงทีละคอลัมน์) + บรรทัดอุปกรณ์ที่รับมา และจำนวนรวม
    จำนวนมากขึ้นสูงขึ้นแค่ 1 แถวต่อ 3 รายการ (ตารางเดิมของ A-TH สูง 1 แถวต่อ 1 รายการ แล้วล้นหน้า)"""
    items = d.job["parts"]
    claims = sum(1 for _, claim in items if claim)
    per = (len(items) + 2) // 3
    def column(part, start):
        return "<div>" + "".join(
            f'<div class="row"><span style="color: #15181C"><span class="mono" style="color: #5A626C; margin-right: 8px">{start + k}</span>{d.p(name)}</span>'
            f'<span class="tag" style="color: {"#166534" if claim else "#5A626C"}">{d.x("claim" if claim else "paid")}</span></div>'
            for k, (name, claim) in enumerate(part)) + "</div>"
    columns = "".join(column(items[k:k + per], k + 1) for k in range(0, len(items), per))
    grid = f'<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 24px; align-items: start">{columns}</div>'
    received = " · ".join(d.p(item) for item in d.job["received"])
    return (grid + f'<div style="display: flex; justify-content: space-between; gap: 16px; font-size: 12px; line-height: 17px">'
            f'<span><span class="lbl" style="margin-right: 10px">{d.x("acc")}</span>{received}</span>'
            f'<span class="lbl">{d.x("parts_sum", n=len(items), c=claims)}</span></div>')


def result_box(d, title, text, extra=""):
    return f"""<div style="display: grid; grid-template-columns: minmax(0, 1fr) 160px; margin-top: 12px; border: 1px solid #15181C">
  <div style="padding: 9px 14px; display: flex; flex-direction: column; gap: 3px"><span style="font-size: 13px; font-weight: 600">{title}</span>
  <span style="font-size: 12.5px; line-height: 19px; color: #3D444C">{text}</span>{extra}</div>
  <div style="border-left: 1px solid #15181C; display: flex; flex-direction: column; align-items: center; justify-content: center"><span class="lbl">{d.x("overall")}</span>
  <span style="font-size: 30px; line-height: 38px; font-weight: 700; color: #166534">{d.t["ok"]}</span></div>
</div>"""


def error_chart(d, values, target, tol, mean_err, w=424, h=176):
    """error รายช่วง + ค่าเฉลี่ย + เกณฑ์ — โครงเดียวกับกราฟของ A-TH (kit.interval_chart) วาดที่ขนาดจริง ตัวอักษร 12 px"""
    errs = [(v - target) / target * 100 for v in values]
    x0, x1, y0, y1 = 40, w - 4, 6, h - 42
    top = tol * 2
    sx = lambda k: x0 + (x1 - x0) * (k - 1) / max(1, len(errs) - 1)
    sy = lambda v: y0 + (y1 - y0) * (top - v) / (2 * top)
    c = d.c
    line = lambda xa, ya, xb, yb, col, wd=1, dash="": (f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" stroke="{col}" stroke-width="{wd}"'
                                                       + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")
    text = lambda x, y, s, anchor="start": f'<text x="{x:.1f}" y="{y:.1f}" font-size="12" fill="{GREY}" text-anchor="{anchor}">{s}</text>'
    out = [f'<rect x="{x0}" y="{sy(tol):.1f}" width="{x1 - x0}" height="{sy(-tol) - sy(tol):.1f}" fill="{c["tint"]}"/>',
           line(x0, sy(tol), x1, sy(tol), c["ink"], 1, "4 3"), line(x0, sy(-tol), x1, sy(-tol), c["ink"], 1, "4 3"),
           line(x0, sy(0), x1, sy(0), DIM), line(x0, y0, x0, y1, DIM), line(x0, y1, x1, y1, DIM)]
    for v in (tol, 0, -tol):
        out.append(text(x0 - 6, sy(v) + 4, ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v):g}", "end"))
    out.append(text(x0 - 6, 14, "%", "end"))
    edge = top * 0.95
    points = " ".join(f"{sx(k):.1f},{sy(max(-edge, min(edge, e))):.1f}" for k, e in enumerate(errs, 1))
    out.append(f'<polyline points="{points}" fill="none" stroke="{INK}" stroke-width="1.2" stroke-linejoin="round"/>')
    out.append(line(x0, sy(mean_err), x1, sy(mean_err), ORANGE, 1.5))
    ty = y1 + 16
    out += [text(x0, ty, "1"), text(x1, ty, str(len(errs)), "end"), text((x0 + x1) / 2, ty, d.x("x_axis"), "middle"),
            text(x1, h - 6, d.x("legend", t=tol), "end")]
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="display: block">{"".join(out)}</svg>'


def rate_block(d, title, rows, chart, last=False):
    border = "" if last else "border-bottom: 1px solid #D5D9DE; "
    return f"""<div style="display: grid; grid-template-columns: 250px minmax(0, 1fr); column-gap: 24px; padding: 2px 0 10px 0; {border}">
<div style="display: flex; flex-direction: column"><div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px">
<span class="mono" style="font-size: 16px; font-weight: 500">{title}</span><span class="pass" style="font-size: 13px">{d.t["ok"]}</span></div>
{rows_html(rows)}</div>{chart}</div>"""


def occlusion_rows(d):
    job = d.job
    a, b, c = job["occl"]
    low, high = job["occl_limit"]
    return [(d.x("occl_set"), job["occl_level"]), (f'{d.x("run")} 1', f"{a} kPa"), (f'{d.x("run")} 2', f"{b} kPa"), (f'{d.x("run")} 3', f"{c} kPa"),
            (d.x("mean"), f"{(a + b + c) / 3:.0f} kPa"), (d.x("occl_lim"), f"{low} – {high} kPa"),
            (d.x("c_res"), f'<span class="tag pass">{d.t["ok"]}</span>')]


def volume_rows(d):
    t = d.t
    return [(t["water_t"], ENV["water_t"]), (t["density"], ENV["density"]), (t["per_gram"], ENV["per_gram"]),
            (t["evap"], "0.012 g/h")]


def balance_rows(d):
    return [(d.x("b_model"), BALANCE["model"]), (d.x("b_sn"), BALANCE["serial"]), (d.x("b_cap"), BALANCE["capacity"]),
            (d.x("b_read"), BALANCE["readability"]), (d.x("b_check"), "50.000 g")]


def env_strip(d):
    t = d.t
    cells = [(t["liquid"], t["water"]), (t["water_t"], ENV["water_t"]), (t["air_t"], ENV["air_t"]), (t["rh"], ENV["rh"]), (t["pressure"], ENV["pressure"])]
    return '<div style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr))">' + "".join(
        f'<div style="display: flex; flex-direction: column; gap: 1px{"; border-left: 1px solid #D5D9DE; padding-left: 12px" if k else ""}">'
        f'<span class="lbl">{a}</span><span class="val">{b}</span></div>' for k, (a, b) in enumerate(cells)) + "</div>"


def wrap(d, body):
    return f'<section class="page ath {d.pump}">{body}</section>'


# ------------------------------------------------------------------ หน้าเอกสาร
def inspection_page(lang, pump, page, pages, cal=False):
    d = Doc(lang, pump)
    t, x = d.t, d.x
    pg = x("page", a=page, b=pages)
    ticks = (f'<span style="font-size: 12.5px; line-height: 19px; color: #15181C; margin-top: 2px"><span class="box" style="margin-right: 6px">✓</span>{x("fin1")}'
             f'<span class="box" style="margin: 0 6px 0 18px">✓</span>{x("fin2")}</span>')
    body = f"""{head(d, t["insp_title"], "Inspection Report" if lang == "th" else t[pump], pg)}
{meta(d, [(t["job"], d.job["job"], True), (x("date_insp"), DATE[lang], False), (t["service"], x("svc_cal" if cal else "svc_pm"), False),
          (t["device_kind"], t[pump], False)], "0.8fr 0.9fr 1fr 1.5fr")}
{who(d, "device")}
<section class="blk" style="margin-top: 10px">{d.sec(3, "check")}{check_tables(d)}</section>
<section class="blk" style="margin-top: 10px">{d.sec(4, "perf")}{perf_table(d, cal)}</section>
<section class="blk" style="margin-top: 10px">{d.sec(5, "parts")}{parts(d)}</section>
{result_box(d, x("concl"), t["insp_statement"], ticks)}
{sigs(d, [("inspected_by", "engineer"), ("received_by", "hospital_side")])}
{foot(d, f"{page}/{pages}")}"""
    return wrap(d, body)


def measurement_page(lang, pump, page, pages):
    d = Doc(lang, pump)
    t, x, job = d.t, d.x, d.job
    by_cycle = job["by_cycle"]
    values = series(job["measured"], job["spread"], job["count"], 4711 if pump == "infusion" else 1213)
    big = lambda lab, v, u, b=True: (f'<div style="padding: 12px 14px; {"border-right: 1px solid #C4CAD1; " if b else ""}display: flex; flex-direction: column; gap: 2px">'
                                    f'<span class="lbl">{lab}</span><span class="mono" style="font-size: 30px; line-height: 36px; font-weight: 500">{v}</span><span class="lbl">{u}</span></div>')
    volume = job["measured"] * job["unit_time"] / 3600.0
    rows = [(x("r_n_cycle" if by_cycle else "r_n_time"), str(job["count"])),
            (x("r_period" if by_cycle else "r_length"), f'{job["unit_time"]:g} s'),
            (x("r_vol" if by_cycle else "r_vol_time"), f"{volume:.3f} ml"),
            (x("r_meas"), f'{job["measured"]:.2f} ml/h'), (x("r_err"), f'{minus(job["error"])} %'),
            (x("r_sd"), f'{job["spread"]:g} %'), (x("r_split"), f'<span class="tag" style="font-weight: 400">{x("by_cycle" if by_cycle else "by_time")}</span>')]
    chart = error_chart(d, values, job["rate"], job["tol"], job["error"])
    body = f"""{head_small(d, f'{t["insp_title"]} — {x("meas_sub")} · {t[pump]}', x("page", a=page, b=pages))}
{meta(d, [(t["hospital"], f'{d.p(CUSTOMER["hospital"])} · {d.p(job["dept"])}', False), (t["brand"], job["brand"], False),
          (t["serial"], job["serial"], False), (x("date_insp"), DATE[lang], False)], "1.6fr 1fr 0.9fr 0.9fr")}
<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)) 150px; border: 1px solid #15181C; margin-top: 20px">
  {big(x("big_rate"), f'{job["rate"]:.1f}', "ml/h")}{big(x("big_meas"), f'{job["measured"]:.2f}', "ml/h")}
  {big(x("big_err"), minus(job["error"]), f'% · {x("limit")} ±{job["tol"]:.1f} %')}
  {big(x("big_time"), f'{job["minutes"]:g}', f'{t["minute"]} · {job["count"]} {x("cycles" if by_cycle else "intervals")}', False)}
  <div style="border-left: 1px solid #15181C; display: flex; flex-direction: column; align-items: center; justify-content: center"><span class="lbl">{x("c_res")}</span>
  <span style="font-size: 30px; line-height: 38px; font-weight: 700; color: #166534">{t["ok"]}</span></div>
</div>
<p class="note" style="margin-top: 10px">{t["how_text"]}</p>
<section class="blk" style="margin-top: 18px; gap: 10px">{d.sec(1, "per")}{rate_block(d, f'{job["rate"]:.1f} ml/h', rows, chart, last=True)}</section>
<div class="two" style="margin-top: 14px">
  <section class="blk" style="gap: 6px">{d.sec(2, "occl")}<div>{rows_html(occlusion_rows(d))}</div></section>
  <section class="blk" style="gap: 6px">{d.sec(3, "bal")}<div>{rows_html(balance_rows(d))}</div></section>
</div>
<div class="two" style="margin-top: 18px">
  <section class="blk" style="gap: 6px">{d.sec(4, "vol")}<div>{rows_html(volume_rows(d))}</div><span class="note">{t["volume_note"]}</span></section>
  <section class="blk" style="gap: 6px">{d.sec(5, "env")}<div>{rows_html([(t["liquid"], f'<span class="tag" style="font-weight: 400">{t["water"]}</span>'), (t["air_t"], ENV["air_t"]), (t["rh"], ENV["rh"]), (t["pressure"], ENV["pressure"])])}</div></section>
</div>
<div style="margin-top: auto; text-align: center; font-size: 12px; letter-spacing: .1em; color: #5A626C">— {x("end_insp")} —</div>
{foot(d, f"{page}/{pages}")}"""
    return wrap(d, body)


def calibration_summary(lang, page, pages):
    d = Doc(lang, "infusion")
    t, x, job = d.t, d.x, d.job
    ok = f'<span class="pass">{t["ok"]}</span>'
    rows = "".join(f'<tr><td class="num"><b>{r[0]:.1f}</b></td><td class="num">{r[1]:.1f}</td><td class="num">{r[2]}</td><td class="num">{r[3]:.2f}</td>'
                   f'<td class="num">{minus(r[4])}</td><td class="num">{r[5]:.1f}</td><td class="num">{r[6]:.1f}</td><td class="num">±{job["tol"]:.1f}</td><td>{ok}</td></tr>'
                   for r in CAL_ROWS)
    results = (f'<table class="t"><thead><tr><th>{t["set_rate"]}<br>ml/h</th><th>{t["duration"]}<br>{t["minute"]}</th><th>{t["count"]}<br>n</th>'
               f'<th>{t["measured"]}<br>ml/h</th><th>{t["error"]}<br>%</th><th>±2SD<br>%</th><th>U k=2<br>%</th><th>{t["limit"]}<br>%</th><th>{t["verdict"]}</th></tr></thead>'
               f'<tbody>{rows}</tbody></table>')
    a, b, c = job["occl"]
    low, high = job["occl_limit"]
    occl = (f'<table class="t"><thead><tr><th>{t["occl_row"]}</th><th>{x("run")} 1</th><th>{x("run")} 2</th><th>{x("run")} 3</th><th>{x("mean")}</th>'
            f'<th>{x("occl_lim")}</th><th>{t["verdict"]}</th></tr></thead><tbody><tr><td>{x("occl_set")} {job["occl_level"]} · kPa</td>'
            f'<td class="num">{a}</td><td class="num">{b}</td><td class="num">{c}</td><td class="num"><b>{(a + b + c) / 3:.0f}</b></td>'
            f'<td class="num">{low} – {high}</td><td>{ok}</td></tr></tbody></table>')
    ref = (f'<table class="t"><thead><tr><th>{x("std")}</th><th>{x("std_sn")}</th><th>{x("std_cap")}</th></tr></thead><tbody>'
           f'<tr><td>{BALANCE["model"]}</td><td class="num">{BALANCE["serial"]}</td><td class="num" style="white-space: nowrap">{BALANCE["capacity"]} · {BALANCE["readability"]}</td></tr></tbody></table>')
    body = f"""{head(d, t["cal_title"], "Calibration Certificate" if lang == "th" else t["infusion"], x("page", a=page, b=pages), "lab")}
{meta(d, [(t["job"], job["job"], True), (x("date_cal"), DATE[lang], False), (t["device_kind"], t["infusion"], False), (t["brand"], job["brand"], False)])}
{who(d, "device_cal")}
<section class="blk" style="margin-top: 10px">{d.sec(3, "method")}
  <div class="two">{kv([(x("m_how"), x("m_how_v")), (x("m_vol"), x("m_vol_v")), (x("m_split"), x("m_split_v"))], "kv nar")}{ref}</div>
  <p class="note">{t["trace"]} · {t["balance_check"]}</p></section>
<section class="blk" style="margin-top: 10px">{d.sec(4, "env")}{env_strip(d)}</section>
<section class="blk" style="margin-top: 10px">{d.sec(5, "res")}{results}
  <div style="display: flex; flex-direction: column; gap: 2px" class="note"><span>{t["err_note"]}</span><span>{t["unc_note"]}</span></div></section>
<section class="blk" style="margin-top: 10px">{d.sec(6, "occl")}{occl}</section>
{result_box(d, x("conf"), t["cal_statement"])}
{sigs(d, [("calibrated_by", "engineer"), ("reviewed_by", "supervisor"), ("approved_by", "manager")])}
{foot(d, f"{page}/{pages}")}"""
    return wrap(d, body)


def calibration_technical(lang, page, pages):
    d = Doc(lang, "infusion")
    t, x, job = d.t, d.x, d.job
    blocks = []
    for k, r in enumerate(CAL_ROWS):
        values = series(r[3], r[5], r[2], 9001 + k * 77)
        volume = r[3] * r[7] / 3600.0
        rows = [(x("r_n_cycle"), str(r[2])), (x("r_period"), f"{r[7]:g} s"), (x("r_vol"), f"{volume:.3f} ml"),
                (x("r_meas"), f"{r[3]:.2f} ml/h"), (x("r_err"), f"{minus(r[4])} %"), (x("r_sd"), f"{r[5]:g} %"), (x("r_u"), f"{r[6]:g} %")]
        blocks.append(rate_block(d, f"{r[0]:.1f} ml/h", rows, error_chart(d, values, r[0], job["tol"], r[4])))
    body = f"""{head_small(d, f'{t["cal_title"]} — {x("tech")}', x("page", a=page, b=pages))}
<section class="blk" style="margin-top: 18px; gap: 10px">{d.sec(7, "per")}{"".join(blocks)}</section>
<div class="two" style="margin-top: 18px">
  <section class="blk" style="gap: 6px">{d.sec(8, "vol")}<div>{rows_html(volume_rows(d))}</div><span class="note">{t["volume_note"]}</span></section>
  <section class="blk" style="gap: 6px">{d.sec(9, "bal")}<div>{rows_html(balance_rows(d))}</div></section>
</div>
<div style="margin-top: auto; text-align: center; font-size: 12px; letter-spacing: .1em; color: #5A626C">— {x("end_cal")} —</div>
{foot(d, f"{page}/{pages}")}"""
    return wrap(d, body)


def document(lang, V=None):
    return [
        ("Inspection-Infusion-p1", inspection_page(lang, "infusion", 1, 2)),
        ("Inspection-Infusion-p2", measurement_page(lang, "infusion", 2, 2)),
        ("Inspection-Syringe-p1", inspection_page(lang, "syringe", 1, 2)),
        ("Inspection-Syringe-p2", measurement_page(lang, "syringe", 2, 2)),
        ("Calibration-p1-inspection", inspection_page(lang, "infusion", 1, 3, cal=True)),
        ("Calibration-p2-summary", calibration_summary(lang, 2, 3)),
        ("Calibration-p3-technical", calibration_technical(lang, 3, 3)),
    ]
