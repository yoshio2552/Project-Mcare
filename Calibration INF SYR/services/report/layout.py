"""หน้าเอกสาร HTML ของใบรายงาน (แบบ Main Fable-1) จากข้อมูลจริง (ReportJob) — ไม่มี Qt

ยกโครงจาก tools/report_templates/fable/a.py (ตัวเลือก main + rate_error + lab) — ชื่อ class/โครง HTML เหมือนเดิมทุกจุด
เพื่อให้ CSS ของแบบใช้ได้ตรงๆ · ข้อความของผู้ใช้ทุกช่องผ่าน html.escape

เอกสาร:
  Inspection   หน้า 1 รายการตรวจ + แถบผลอัตราการไหล · หน้า 2 ผลวัด (มีหลาย rate = หน้า 2 ซ้ำต่อ rate)
  Calibration  หน้า 1 รายการตรวจ · หน้า 2 ใบรับรอง (ตารางผล การอุดตัน เครื่องมือ ลายเซ็น 3 ช่อง)
               · หน้า 3 รายงานทางเทคนิค (กราฟรวม + 3 rate) · rate ที่ 4 ขึ้นไปอยู่หน้าเทคนิคถัดไป หน้าละ 4 rate
"""
from __future__ import annotations

import base64
import html
import math
from pathlib import Path

from services.report import checklist
from services.report.charts import (ERR_DP, PUMP, error_chart, flow_chart, gauge, num, trend_slope, u_text, vgauge)
from services.report.model import ReportJob, Signer
from services.report.style import stylesheet
from services.report.text import Words

TECH_FIRST = 3          # rate ต่อหน้าเทคนิคแรก (มีกราฟรวม)
TECH_MORE = 4           # rate ต่อหน้าเทคนิคถัดไป
PARTS_DENSE = 9         # อะไหล่เกินนี้ (เกิน 3 แถว) -> หน้า 1 ใช้ระยะแถวแน่นขึ้น


def join_brand(brand, model) -> str:
    """ยี่ห้อ + รุ่น ไม่ซ้ำคำ: "TOP" + "TOP-2300" -> "TOP-2300" · "ME" + "ME 20 Drops/ml" -> "ME 20 Drops/ml" """
    brand, model = str(brand or "").strip(), str(model or "").strip()
    if brand and model.lower().startswith(brand.lower()):
        rest = model[len(brand):]
        if not rest or rest[0] in " -_/.":
            return model
    return " ".join(p for p in (brand, model) if p)


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def dash(value, fmt="{}") -> str:
    if value is None or value == "":
        return "—"
    return fmt.format(value)


def mmss(seconds) -> str:
    """เวลาในใบ: นาที:วินาที.เสี้ยววินาที 2 ตำแหน่ง ("15:00.00", "00:14.20") — นาทีเกิน 59 ได้"""
    if seconds is None:
        return "—"
    total = round(float(seconds), 2)
    minutes = int(total // 60)
    return f"{minutes:02d}:{total - minutes * 60:05.2f}"


def ml(value) -> str:
    """ปริมาตรในใบ: ทศนิยม 3 ตำแหน่ง + หน่วย"""
    return "—" if value is None else f"{value:.3f} ml"


def box(on=False):
    return f'<span class="bx{" on" if on else ""}"></span>'


def kv(pairs, cls=""):
    rows = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in pairs)
    return f'<dl class="kv {cls}">{rows}</dl>'


def _image_uri(path: str) -> str:
    try:
        file = Path(path)
        if not path or not file.is_file() or file.stat().st_size > 2_000_000:
            return ""
        kind = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".svg": "svg+xml"}.get(file.suffix.lower())
        if not kind:
            return ""
        return f"data:image/{kind};base64," + base64.b64encode(file.read_bytes()).decode("ascii")
    except OSError:
        return ""


class Doc:
    """ตัวสร้างหน้าของ 1 ใบ × 1 ภาษา"""

    def __init__(self, job: ReportJob, lang: str):
        self.job, self.w = job, Words(lang)
        self.lang = self.w.lang
        self.pump = job.pump if job.pump in PUMP else "infusion"
        self.o = job.options
        self.info = job.info

    # ------------------------------------------------------------ ชิ้นส่วน
    def chart_options(self) -> dict:
        return dict(style=self.o.chart_style, show_mean=self.o.chart_mean, moving=self.o.chart_moving)

    def sec(self, no, title, en_key, body, cls=""):
        en = self.w.en(en_key)
        alt = f'<span class="en">{en}</span>' if en else ""
        return (f'<section class="sec {cls}"><h2><span class="no">{int(no):02d}</span><span class="t">{title}</span>{alt}</h2>'
                f'<div class="body">{body}</div></section>')

    def address(self):
        return self.o.address_th if self.lang == "th" else (self.o.address_en or self.o.address_th)

    def header(self, kind_key, title_key, page, pages):
        """หัวกระดาษ: กล่องโลโก้ + ชื่อบริษัท/ที่อยู่ (ซ้าย) · ชื่อใบ ชนิดใบ ชนิดเครื่อง เลขหน้า (ขวา)"""
        w = self.w
        logo = _image_uri(self.o.logo)
        mark = f'<img class="logo" src="{logo}" alt="">' if logo else f'<div class="mark">{esc(self.o.mark)}</div>'
        device = w.device(self.pump)
        if self.lang == "th":
            device = f'{w.device_th(self.pump)} <span class="alt">{w.device(self.pump, lower=True)}</span>'
        return (f'<header class="hdr"><div class="co">{mark}<div class="cotext">'
                f'<div class="coname">{esc(self.o.company)}</div><div class="coaddr">{esc(self.address())}</div></div></div>'
                f'<div class="ttl"><h1>{w(title_key)}</h1><div class="kind">{w(kind_key)}</div>'
                f'<div class="sub">{device}</div><div class="pg">{w("page")} {page} / {pages}</div></div></header>')

    def footer(self, page, pages):
        from config.constants import APP_VERSION
        return (f'<footer class="foot"><span>{esc(self.o.company)}</span>'
                f'<span class="made">{self.w("made_by", v=APP_VERSION)}</span>'
                f'<span>{esc(self.job.job_no or "—")} · {self.w("page")} {page} / {pages}</span></footer>')

    def meta(self, date_key, service=False):
        w, job = self.w, self.job.job
        cells = [f'<div><b>{w("job")}</b><span class="jobno">{esc(self.job.job_no or "—")}</span></div>',
                 f'<div><b>{w(date_key)}</b><span>{w.date(self.job.date_iso)}</span></div>']
        if service:
            kinds = self.job.service_types()            # คิดจากโหมด + อะไหล่ที่เปลี่ยน (ไม่ต้องเลือกเอง)
            ticks = "".join(f'<span class="opt">{box(key in kinds)}{w(key)}</span>'
                            for key in ("pm", "repair", "calib"))
            cells.append(f'<div class="svc"><b>{w("service")}</b><span class="opts">{ticks}</span></div>')
            cls = ""
        else:
            brand = join_brand(job.get("brand"), job.get("model"))
            cells.append(f'<div><b>{w("device_kind")}</b><span class="dev">{w.device(self.pump)}</span></div>')
            cells.append(f'<div><b>{w("brand")}</b><span>{esc(brand or "—")}</span></div>')
            cls = " m4"
        return f'<div class="meta{cls}">{"".join(cells)}</div>'

    def who(self, device_key="device"):
        w, job, info = self.w, self.job.job, self.info
        contact = " · ".join(p for p in (info.contact, info.contact_phone) if p)
        customer = [(w("hospital"), esc(job.get("site") or "—")), (w("dept"), esc(job.get("department") or "—")),
                    (w("province"), esc(job.get("province") or "—")), (w("contact"), esc(contact or "—"))]
        brand = join_brand(job.get("brand"), job.get("model"))
        device = [(w("brand"), esc(brand or "—")), (w("serial"), esc(job.get("serial_no") or "—")),
                  (w("asset"), esc(job.get("asset_id") or "—")), (self.consumable_label(), esc(self.consumable() or "—"))]

        def head(key, en):
            alt = f'<span class="en">{w.en(en)}</span>' if self.lang == "th" else ""
            return f'<h3><span>{w(key)}</span>{alt}</h3>'
        return (f'<div class="two who"><div>{head("customer", "customer")}{kv(customer)}</div>'
                f'<div>{head(device_key, device_key)}{kv(device)}</div></div>')

    def consumable(self) -> str:
        """ชุดให้สารละลาย / กระบอกฉีดที่ใช้: ยี่ห้อ + รุ่น"""
        return join_brand(self.job.job.get("accessory_brand"), self.job.job.get("accessory"))

    def consumable_label(self) -> str:
        return self.w("ivset" if self.pump == "infusion" else "syr")

    def check_rows(self, rows, head=True):
        """rows = [(ชื่อ, รายละเอียด, ผล pass|fail|na|"")] — ไหลเป็น 2 คอลัมน์"""
        w = self.w
        hd = (f'<div class="hd"><span>{w("item")}</span><span class="cols"><i>{w("ok")}</i><i>{w("fail")}</i>'
              f'<i>{w("na")}</i></span></div>')
        out = []
        for name, detail, status in rows:
            small = f'<small>{esc(detail)}</small>' if detail else ""
            boxes = "".join(box(status == s) for s in checklist.STATUSES)
            out.append(f'<div class="it"><span class="nm">{esc(name)}{small}</span><span class="cols">{boxes}</span></div>')
        return f'<div class="chk c2{"" if head else " nohd"}">{hd * 2 if head else ""}{"".join(out)}</div>'

    def item_rows(self, group, cal=False):
        w, rows = self.w, []
        for key, th, en in checklist.items(self.pump, group):
            status = self.job.check_status(key)
            code = key.split(".", 1)[1]
            detail = str(self.info.check_notes.get(key) or "").strip()
            stats = self.info.occl_stats() if code == "occlusion" and cal else None
            if code == "occlusion" and not cal:
                # ใบ Inspection: ไม่ใส่ค่าที่วัด บอกแค่ว่าทำงานปกติ (ผู้ใช้ 2026-11-19) — ค่าละเอียดอยู่ในใบ Calibration
                detail = w("works_ok") if status == checklist.PASS else ""
            elif stats is not None:
                mean, sd2, digits = stats
                detail = w("occl_detail", m=f"{mean:.{digits}f}", s=f"{sd2:.{digits}f}", u=self.info.occl_unit or "kPa")
            elif code == "occlusion":
                detail = w("occl_cal")
            elif code == "battery" and self.info.battery_rate:
                rate = f"{float(self.info.battery_rate):g}"
                detail = (w("battery_detail", m=f"{float(self.info.battery_min):g}", r=rate) if self.info.battery_min
                          else w("battery_rate", r=rate))
            elif code == "battery" and not detail and status == checklist.PASS:
                detail = w("works_ok")          # ไม่ได้กรอกอัตรา/เวลา (งานเก่า) — ยังมีคำบรรยายใต้ชื่อข้อ
            elif not detail and status == checklist.PASS and code in checklist.PASS_DETAIL:
                detail = w.pick(*checklist.PASS_DETAIL[code])
            rows.append((w.pick(th, en), detail, status))
        return rows

    def flow_detail(self, cal: bool) -> str:
        """รายละเอียดของข้อ "อัตราการไหล" ในหัวข้อสมรรถนะ: rate · Error% · หน้าที่มีรายละเอียด"""
        w, rates = self.w, self.job.rates
        if not rates:
            return "—"
        where = w("see_p2") if cal or len(rates) == 1 else w("see_pn", p=1 + len(rates))
        if cal:                                 # ใบ Calibration: แค่ rate ที่ตั้ง + ชี้ไปหน้า 2 (ผู้ใช้ 2026-11-19)
            return " · ".join(f"{r.set_rate:g}" for r in rates) + f" ml/h · {where}"
        if len(rates) <= 2:
            parts = [f"{r.set_rate:g} ml/h · Error% {num(r.error, ERR_DP, True)}" for r in rates]
            return " · ".join(parts + [where])
        worst = max(rates, key=lambda r: abs(r.error))
        return " · ".join([" · ".join(f"{r.set_rate:g}" for r in rates) + " ml/h",
                           w("err_max", e=num(worst.error, ERR_DP, True)), where])

    def safety_row(self):
        """04 ความปลอดภัยทางไฟฟ้า: แรงดัน · กระแสรั่ว + เกณฑ์ · ผล (ป้ายเหนือค่า)"""
        w, info = self.w, self.info
        status = info.safety_status(self.o.leak_limit_ua)
        verdict = (f'<span class="{"pass" if status == checklist.PASS else "fail"}">'
                   f'{w("ok") if status == checklist.PASS else w("fail")}</span>') if status else '<span class="na">—</span>'
        return (f'<div class="safe3"><div><b>{w("supply")}</b><span>{dash(info.supply_v, "{:g} V")}</span></div>'
                f'<div><b>{w("leak")}</b><span>{dash(info.leak_ua, "{:g} µA")}</span>'
                f'<em>{w("leak_lim", v=f"{self.o.leak_limit_ua:g}")}</em></div>'
                f'<div class="sv"><b>{w("verdict")}</b>{verdict}</div></div>')

    def final_block(self):
        """05 ตรวจขั้นสุดท้าย: 2 ช่องติ๊กเรียงลง"""
        w, info = self.w, self.info
        return (f'<div class="fin3"><span class="opt">{box(info.whole_checked)}{w("fin1")}</span>'
                f'<span class="opt">{box(info.label_attached)}{w("fin2")}</span></div>')

    def parts_block(self):
        """06 อะไหล่: บรรทัดสรุป · รายการ 3 คอลัมน์ (เคลมประกันมีป้าย) · อุปกรณ์ที่รับมากับเครื่อง"""
        w, job = self.w, self.job.job
        names = [str(p) for p in (job.get("parts_replaced") or []) if str(p).strip()]
        claimed = {str(p) for p in (job.get("parts_warranty") or [])}
        claims = sum(1 for name in names if name in claimed)
        received = " · ".join(esc(item) for item in (job.get("accessories") or []) if str(item).strip()) or "—"
        if names:
            head = f'<div class="pcount">{w("parts_n", n=len(names), c=claims)}</div>'
            rows = "".join(f'<li><span>{esc(name)}</span>' + (f'<i class="cl">{w("claim")}</i>' if name in claimed else "")
                           + "</li>" for name in names)
            items = f'<ol class="parts3">{rows}</ol>'
        else:
            head, items = f'<div class="pcount">{w("no_parts")}</div>', ""
        return f'{head}{items}<div class="precv"><b>{w("received")}</b>{received}</div>'

    def verdict(self, statement, ticks=True, flow=False):
        """กล่องผล: ข้อความสรุป (+ แถวผลอัตราการไหลแบบเรียบ — ใบ Inspection ที่ไม่ใช่ Calibration) · ผลรวมตัวใหญ่"""
        w, ok = self.w, self.job.overall_pass()
        lines = ""
        if flow and self.job.rates:
            rows = "".join(
                f'<tr><td>{r.set_rate:g}<i>ml/h</i></td><td>{self.flow_text(r)}<i>ml/h</i></td>'
                f'<td class="e">{num(r.error, ERR_DP, True)}<i>%</i></td><td>±{r.tol:g}<i>%</i></td>'
                f'<td class="{"pass" if r.passed else "fail"}">{w("ok") if r.passed else w("fail")}</td></tr>'
                for r in self.job.rates[:3])
            lines = (f'<table class="vfig"><thead><tr><th>{w("set_rate")}</th><th>{w("measured")}</th><th>Error%</th>'
                     f'<th>{w("tolerance")}</th><th>{w("verdict")}</th></tr></thead><tbody>{rows}</tbody></table>')
            if len(self.job.rates) > 3:
                lines += f'<div class="vmore">{w("see_pn", p=1 + len(self.job.rates))}</div>'
        return (f'<div class="verdict"><div class="vt"><b>{w("result" if ticks else "result_cal")}</b><p>{statement}</p>{lines}</div>'
                f'<div class="vr"><span class="vl">{w("result" if ticks else "result_cal")}</span>'
                f'<span class="vv{"" if ok else " fail"}">{w("ok") if ok else w("fail")}</span></div></div>')

    def signs(self, roles):
        """roles = [(บทบาท, ตำแหน่งเริ่มต้น, Signer|None)] — ลายมือชื่อเหนือเส้น · ชื่อ-นามสกุลใต้เส้น · ไม่มีวันที่ (ผู้ใช้ 2026-11-19)"""
        w, cells = self.w, []
        for role, position, signer in roles:
            signer = signer or Signer()
            image = _image_uri(signer.image)
            pad = f'<img src="{image}" alt="">' if image else ""
            name = esc(signer.name) if signer.name else w("name")
            cells.append(f'<div class="sg3"><div class="shd"><span class="srole">{w(role)}</span>'
                         f'<span class="sen">{esc(signer.position) if signer.position else w(position)}</span></div>'
                         f'<div class="spad">{pad}</div>'
                         f'<div class="sname{" set" if signer.name else ""}">{name}</div></div>')
        return f'<div class="signs3 n{len(roles)}">{"".join(cells)}</div>'

    def env_strip(self):
        w, env = self.w, self.job.env
        cells = [(w("liquid"), w("water")), (w("water_t"), dash(env.get("water_t"), "{:.1f} °C")),
                 (w("air_t"), dash(env.get("air_t"), "{:.1f} °C")), (w("rh"), dash(env.get("rh"), "{:.0f} %")),
                 (w("pressure"), dash(env.get("pressure"), "{:.0f} hPa"))]
        return '<div class="env">' + "".join(f'<div><b>{a}</b><span>{b}</span></div>' for a, b in cells) + "</div>"

    @staticmethod
    def rows_html(rows, cls=""):
        return (f'<div class="rows {cls}">' + "".join(f'<div class="row"><span>{a}</span><span>{b}</span></div>' for a, b in rows)
                + "</div>")

    @staticmethod
    def flow_text(r) -> str:
        return f"{r.measured:.{3 if r.set_rate < 1 else 2}f}"

    def detail_rows(self, r):
        """รายละเอียดของ 1 rate — เวลา/ปริมาตรต่อช่วง ± 1 SD และเวลารวม/ปริมาตรรวม"""
        w, cyc = self.w, r.method == "cycle"
        unit = mmss(r.unit_s) + (f" ± {r.unit_sd:.2f} s" if r.unit_sd is not None else "")
        if r.volume_ml is not None:
            volume = f"{r.volume_ml:.3f}" + (f" ± {r.volume_sd:.3f}" if r.volume_sd is not None else "") + " ml"
        else:
            volume = "—"
        return [(w("measured"), f"{self.flow_text(r)} ml/h"), (w("n_cyc" if cyc else "n_tim"), str(r.n)),
                (w("t_cyc" if cyc else "t_tim"), unit if r.unit_s is not None else "—"),
                (w("t_all"), mmss(r.minutes * 60.0)),
                (w("v_cyc" if cyc else "v_tim"), volume), (w("v_all"), ml(r.total_ml)),
                (w("spread"), dash(r.sd2, "{:.2f} %"))]

    def result_word(self, r):
        return f'<span class="{"pass" if r.passed else "fail"}">{self.w("ok") if r.passed else self.w("fail")}</span>'

    def page(self, body, cls):
        return f'<section class="page a2 {self.pump} {cls}">{body}</section>'

    def ident(self):
        """แถบข้อมูลใต้หัวของหน้าผลวัด: เลขงาน · โรงพยาบาล · ยี่ห้อรุ่น · S/N · ชุดสาย/กระบอกฉีดที่ใช้ (ผู้ใช้ 2026-11-19)"""
        w, job = self.w, self.job.job
        place = " · ".join(p for p in (job.get("site"), job.get("department")) if p)
        brand = join_brand(job.get("brand"), job.get("model"))
        return kv([(w("job"), f'<span class="jobno">{esc(self.job.job_no or "—")}</span>'),
                   (w("hospital"), esc(place or "—")), (w("brand"), esc(brand or "—")),
                   (w("serial"), esc(job.get("serial_no") or "—")),
                   (self.consumable_label(), esc(self.consumable() or "—"))], "ident i5")

    def inspection_page(self, page_no, pages, cal=False):
        """หน้า 1 (ทั้ง Inspection และ Calibration): 01 ภายนอก · 02 การทำงาน · 03 สมรรถนะ · 04 ไฟฟ้า | 05 ตรวจขั้นสุดท้าย
        · 06 อะไหล่ · กล่องผล · ลายเซ็น — ไม่มีแถบมาตรวัด (Inspection: แถวผลอัตราการไหลอยู่ในกล่องผล)"""
        w = self.w
        perf = self.item_rows("performance", cal)
        perf.append((w("flow_item"), self.flow_detail(cal), self.job.flow_status()))
        ok = self.job.overall_pass()
        statement = w("insp_statement") if ok else w("insp_statement_fail")
        operator = self.o.signer(self.job.job.get("operator"))
        many_parts = len(self.job.job.get("parts_replaced") or []) > PARTS_DENSE
        pair = (f'<div class="pair2">{self.sec(4, w("safety"), "safety", self.safety_row())}'
                f'{self.sec(5, w("final"), "final", self.final_block())}</div>')
        body = [self.header("insp_kind", "insp_title", page_no, pages),
                self.meta("date_insp", service=True), self.who(),
                self.sec(1, w("visual"), "visual", self.check_rows(self.item_rows("visual"))),
                self.sec(2, w("function"), "function", self.check_rows(self.item_rows("function"), head=False)),
                self.sec(3, w("performance"), "performance", self.check_rows(perf, head=False)),
                pair,
                self.sec(6, w("parts"), "parts", self.parts_block()),
                self.verdict(statement, flow=not cal),
                self.signs([("inspected_by", "engineer", operator), ("received_by", "hospital_side", None)]),
                self.footer(page_no, pages)]
        return self.page("".join(body), "insp" + (" dense" if many_parts else ""))

    def measurement_page(self, r, page_no, pages, first=True):
        """หน้าผลวัด (ภาพที่ 3 ของผู้ใช้): 01 ตัวเลขผล + มาตรวัดเส้นบาง · 02 กราฟ (เส้นดำ พื้นเกณฑ์สีตามชนิดเครื่อง)
        · 03 วิธีวัด | รายละเอียดการวัด · 04 การคิดปริมาตรจากน้ำหนัก (Inspection ไม่ได้วัดการอุดตันในหน้านี้ — ผลอยู่หน้า 1)
        · 05 เครื่องมือมาตรฐาน | สภาวะ (04–05 เฉพาะหน้าผลวัดแรก)"""
        w, bw = self.w, 698
        cells = [(w("set_rate"), f"{r.set_rate:g}", "ml/h"), (w("measured"), self.flow_text(r), "ml/h"),
                 ("Error%", num(r.error, ERR_DP, True), ""), (w("tolerance"), f"±{r.tol:g}", "%")]
        figs = "".join(f'<div class="fig f{i}"><b>{a}</b><span>{b}<i>{c}</i></span></div>' for i, (a, b, c) in enumerate(cells))
        word = w("ok") if r.passed else w("fail")
        hero = (f'<div class="figs five">{figs}<div class="fig fv"><b>{w("result_short")}</b>'
                f'<span class="vv{"" if r.passed else " fail"}">{word}</span></div></div>'
                f'<div class="gg">{gauge(self.pump, r.error, r.u, r.tol, 330, slim=True)}</div>')
        chart = flow_chart(w, self.pump, r.series, r.set_rate, r.measured, r.tol, bw, 236, **self.chart_options())
        how = (f'<div class="two"><div><h3>{w("how")}</h3><p class="note">{w("how_text")}</p>'
               f'<p class="note">{w("split_by")} {w.method(r.method, tech=False)}</p></div>'
               f'<div><h3>{w("meas_detail")}</h3>{self.rows_html(self.detail_rows(r), "tight")}</div></div>')
        body = [self.header("insp_kind", "meas_title", page_no, pages), self.ident(),
                self.sec(1, w("meas_title"), "flow", hero, "hero"),
                self.sec(2, w("chart_flow" if r.method == "cycle" else "chart_flow_time"),
                         "chart_cyc" if r.method == "cycle" else "chart", chart, "plot"),
                self.sec(3, w("how_sec"), "method", how)]
        if first:
            body += [self.sec(4, w("volume"), "volume", self.volume_strip()),
                     self.sec(5, w("std_cond"), "std", self.standard_block())]
        body += [f'<p class="fine">{w("validity")} {w("method_ref")}</p>', self.footer(page_no, pages)]
        return self.page("".join(body), "meas")

    def standard_block(self):
        """เครื่องมือมาตรฐาน | สภาวะขณะวัด (2 คอลัมน์ แถวป้าย-ค่า)"""
        w, o, info, env = self.w, self.o, self.info, self.job.env
        balance = [(w("balance"), esc(" · ".join(p for p in (o.balance_model, o.balance_serial) if p) or "—")),
                   (w("capacity"), esc(o.balance_capacity or "—")), (w("readability"), esc(o.balance_readability or "—"))]
        if info.check_weight_g is not None and info.check_reading_g is not None:
            balance.append((w("check_w", w=f"{info.check_weight_g:g}"), f"{info.check_reading_g:.3f} g"))
        conditions = [(w("liquid"), w("water")), (w("water_t"), dash(env.get("water_t"), "{:.1f} °C")),
                      (w("air_t"), dash(env.get("air_t"), "{:.1f} °C")), (w("rh"), dash(env.get("rh"), "{:.0f} %")),
                      (w("pressure"), dash(env.get("pressure"), "{:.0f} hPa"))]
        return (f'<div class="two"><div><h3>{w("standard")}</h3>{self.rows_html(balance, "tight")}</div>'
                f'<div><h3>{w("conditions")}</h3>{self.rows_html(conditions, "tight")}</div></div>')

    def occlusion_table(self):
        w, info = self.w, self.info
        runs = [dash(v, "{:g}") for v in info.occl_runs]
        stats = info.occl_stats()
        mean = "—" if stats is None else f"{stats[0]:.{stats[2]}f} ± {stats[1]:.{stats[2]}f}"
        limit = (f"{info.occl_low:g} – {info.occl_high:g}" if info.occl_low is not None and info.occl_high is not None else "—")
        status = info.occl_status()
        result = (f'<td class="{"pass" if status == checklist.PASS else "fail"}">'
                  f'{w("ok") if status == checklist.PASS else w("fail")}</td>') if status else '<td class="na">—</td>'
        level = f'{esc(info.occl_level)} · ' if info.occl_level else ""
        return (f'<table class="tb"><thead><tr><th class="l">{w("occl_row")}</th><th>{w("occl_run")} 1</th>'
                f'<th>{w("occl_run")} 2</th><th>{w("occl_run")} 3</th><th>{w("mean_2sd")}</th><th>{w("occl_limit")}</th>'
                f'<th>{w("verdict")}</th></tr></thead>'
                f'<tbody><tr><td class="l">{w("occl_level")} {level}{esc(info.occl_unit or "kPa")}</td>'
                f'<td>{runs[0]}</td><td>{runs[1]}</td><td>{runs[2]}</td>'
                f'<td><b>{mean}</b></td><td>{limit}</td>{result}</tr></tbody></table>')

    def volume_strip(self):
        w, env = self.w, self.job.env
        water_t = dash(env.get("water_t"), "{:.1f} °C")
        evap = env.get("evap")
        cells = [(f'{w("density")} · {water_t}', dash(env.get("density"), "{:.4f} g/ml")),
                 (w("per_gram"), dash(env.get("per_gram"), "{:.4f} ml")),
                 (w("evap"), f"{evap:.3f} g/h" if evap else "—")]
        return ('<div class="env v3">' + "".join(f'<div><b>{a}</b><span>{b}</span></div>' for a, b in cells)
                + f'</div><p class="note">{w("volume_note")}</p>')

    def calibration_summary(self, page_no, pages):
        w, rates = self.w, self.job.rates
        rows = "".join(
            f'<tr><td class="l"><b>{r.set_rate:g}</b></td><td class="l mt">{w.method(r.method, tech=False)}</td>'
            f'<td>{mmss(r.minutes * 60.0)}</td><td>{r.n}</td><td><b>{self.flow_text(r)}</b></td>'
            f'<td><b class="ev">{num(r.error, ERR_DP, True)}</b></td><td>{("±" + u_text(r.u)) if r.u is not None else "—"}</td>'
            f'<td>{dash(r.sd2, "{:.2f}")}</td><td>±{r.tol:g}</td>'
            f'<td class="{"pass" if r.passed else "fail"}">{w("ok") if r.passed else w("fail")}</td></tr>' for r in rates)
        head = (f'<tr><th class="l">{w("set_rate")}<i>ml/h</i></th><th class="l">{w("split")}</th>'
                f'<th>{w("duration")}<i>{w("mmss")}</i></th><th>n</th><th>{w("measured")}<i>ml/h</i></th>'
                f'<th>{w("error")}</th><th>U k=2<i>%</i></th><th>±2SD<i>%</i></th><th>{w("tolerance")}<i>%</i></th>'
                f'<th>{w("verdict")}</th></tr>')
        unc = w("unc_note") if any(r.u is not None for r in rates) else w("unc_none")
        table = (f'<table class="tb res"><thead>{head}</thead><tbody>{rows}</tbody></table>'
                 f'<p class="note">{w("err_note")} · {unc}</p><p class="note">{w("split_note")}</p>')
        o, info = self.o, self.info
        balance = kv([(w("balance"), esc(" · ".join(p for p in (o.balance_model, o.balance_serial) if p) or "—")),
                      (w("capacity"), esc(" · ".join(p for p in (o.balance_capacity, f'{w("readability")} {o.balance_readability}'
                                                                if o.balance_readability else "") if p) or "—"))], "tight")
        check = ""
        if info.check_weight_g is not None and info.check_reading_g is not None:
            check = f'<p class="note">{w("balance_check", w=f"{info.check_weight_g:g}", r=f"{info.check_reading_g:.3f}")}</p>'
        tools = (f'<div class="two"><div><h3>{w("standard")}</h3>{balance}{check}</div>'
                 f'<div><h3>{w("how")}</h3><p class="note" style="margin-top: 0">{w("how_text")} {w("trace")}</p></div></div>'
                 + self.env_strip())
        ok = self.job.overall_pass()
        if ok:
            statement = w("cal_statement") + (" " + w("cal_statement_occl") if info.occl_status() == checklist.PASS else "")
        else:
            statement = w("cal_statement_fail")
        roles = [("calibrated_by", "engineer", o.signer(self.job.job.get("operator"))),
                 ("reviewed_by", "supervisor", o.signer(o.reviewer) if o.reviewer else None),
                 ("approved_by", "manager", o.signer(o.approver) if o.approver else None)]
        body = [self.header("cal_kind", "cal_title", page_no, pages), self.meta("date_cal"), self.who("device_cal"),
                self.sec(1, w("results"), "results", table, "results"),
                self.sec(2, w("occl"), "occl", self.occlusion_table()),
                self.sec(3, w("tools"), "tools", tools),
                self.sec(4, w("volume"), "volume", self.volume_strip()),
                self.verdict(statement, ticks=False), self.signs(roles), self.footer(page_no, pages)]
        return self.page("".join(body), "cal")

    def rate_block(self, r):
        w = self.w
        info = (f'<div class="rt"><b>{r.set_rate:g} ml/h</b>{self.result_word(r)}</div>'
                f'<div class="mt">{w.method(r.method)}</div>')
        if r.u is not None:
            info += (f'<div class="rerr lab"><em>{w("err_u")}</em><span><b>{num(r.error, ERR_DP, True)}</b>'
                     f'<i>± {u_text(r.u)}</i></span></div>')
        else:
            info += (f'<div class="rerr lab"><em>{w("error")}</em><span><b>{num(r.error, ERR_DP, True)}</b>'
                     f'</span></div>')
        info += self.rows_html(self.detail_rows(r), "tight")
        graph = (f'<div class="gv">{flow_chart(w, self.pump, r.series, r.set_rate, r.measured, r.tol, 328, 196, **self.chart_options())}'
                 f'{vgauge(w, self.pump, r.error, r.u, r.tol, 196)}</div>')
        return f'<div class="rb"><div>{info}</div><div>{graph}</div></div>'

    def calibration_technical(self, rates, page_no, pages, first=True):
        w, tol = self.w, self.job.tol
        body = [self.header("cal_kind", "tech_title", page_no, pages)]
        no = 2              # หน้าเทคนิคถัดไป: หัวข้อ 2 ต่อจากหน้าแรก
        if first:
            chart, slope = error_chart(w, self.pump, self.job.rates, tol, 470, 176)
            worst = max(self.job.rates, key=lambda r: abs(r.error))
            any_u = any(r.u is not None for r in self.job.rates)
            margin = min(tol - abs(r.error) - (r.u or 0.0) for r in self.job.rates)
            legend = (f'<div class="lg"><span><i class="pt"></i>{w("legend_pt" if any_u else "legend_pt_nou")}</span>'
                      + (f'<span><i class="fit"></i>{w("legend_fit")}</span>' if slope is not None else "")
                      + f'<span><i class="tolb"></i>{w("legend_tol", t=tol)}</span></div>')
            side = self.rows_html([
                (w("trend"), w("trend_v", s=num(slope, 2, True)) if slope is not None else "—"),
                (w("worst"), w("worst_v", e=num(worst.error, ERR_DP, True), r=worst.set_rate)),
                (w("margin"), w("margin_v" if any_u else "margin_v_nou", m=num(margin, ERR_DP)))]) + legend
            body.append(self.sec(1, w("chart_err"), "err", f'<div class="errw">{chart}<div class="side">{side}</div></div>', "plot"))
        body.append(self.sec(no, w("rate_sec"), "rate", "".join(self.rate_block(r) for r in rates), "plot"))
        body.append(self.footer(page_no, pages))
        return self.page("".join(body), "tech" + ("" if first else " more"))

    # ------------------------------------------------------------ ทั้งใบ
    def pages(self) -> list[tuple[str, str]]:
        """[(ชื่อหน้า, HTML)]"""
        job = self.job
        if job.kind == "calibration":
            rates = job.rates
            chunks = [rates[:TECH_FIRST]] + [rates[i:i + TECH_MORE] for i in range(TECH_FIRST, len(rates), TECH_MORE)]
            chunks = [c for c in chunks if c] if rates else []
            total = 2 + len(chunks)
            out = [("Calibration-p1-inspection", self.inspection_page(1, total, cal=True)),
                   ("Calibration-p2-summary", self.calibration_summary(2, total))]
            for index, chunk in enumerate(chunks):
                out.append((f"Calibration-p{3 + index}-technical",
                            self.calibration_technical(chunk, 3 + index, total, first=index == 0)))
            return out
        total = 1 + len(job.rates)
        out = [("Inspection-p1", self.inspection_page(1, total))]
        for index, r in enumerate(job.rates):
            out.append((f"Inspection-p{2 + index}-{r.set_rate:g}mlh",
                        self.measurement_page(r, 2 + index, total, first=index == 0)))
        return out


def pages(job: ReportJob, lang: str) -> list[tuple[str, str]]:
    return Doc(job, lang).pages()


def html_document(jobs: list[ReportJob], lang: str, screen: bool = False, extra_head: str = "") -> str:
    """HTML ทั้งเอกสาร (หลายใบต่อกันได้ — แต่ละใบมีเลขหน้าของตัวเอง)"""
    body = "\n".join(page for job in jobs for _, page in pages(job, lang))
    title = esc(" · ".join(job.job_no or job.kind for job in jobs[:3]) or "DeltaM report")
    return (f'<!doctype html>\n<html lang="{"en" if lang == "en" else "th"}"><head><meta charset="utf-8">'
            f'<title>{title}</title><style>\n{stylesheet(screen)}\n</style>{extra_head}</head><body>\n{body}\n</body></html>\n')


def page_count(job: ReportJob) -> int:
    if job.kind == "calibration":
        n = len(job.rates)
        return 2 + (0 if n == 0 else 1 + math.ceil(max(0, n - TECH_FIRST) / TECH_MORE))
    return 1 + len(job.rates)
