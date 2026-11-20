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
from pathlib import Path

from services.report import checklist
from services.report.charts import (ERR_DP, PUMP, error_chart, flow_chart, gauge, num, trend_slope, u_text, vgauge)
from services.report import signatures
from core.models import format_duration
from services.report.model import ReportJob
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


def duration(seconds) -> str:
    """เวลาในใบ (ผู้ใช้ 2026-11-20 — แทน นาที:วินาที ที่สับสนกับ ชม:นาที): "10 min 54.28 s" · "14.20 s" """
    return format_duration(seconds)


def seconds(value) -> str:
    """เวลาต่อรอบ/ต่อช่วง: วินาทีล้วน "72.70 s" (อ่านง่ายกว่า 01:12.70)"""
    return "—" if value is None else f"{float(value):.2f} s"


def mmss(seconds) -> str:
    """(แบบเดิม — ไม่ใช้ในใบแล้ว คงไว้ให้ของเก่าเรียกได้) นาที:วินาที.xx"""
    if seconds is None:
        return "—"
    total = round(float(seconds), 2)
    minutes = int(total // 60)
    return f"{minutes:02d}:{total - minutes * 60:05.2f}"


def has_value(value) -> bool:
    """มีข้อมูลจริง — ว่าง หรือ "-" / "–" / "—" = ไม่มีข้อมูล"""
    return str(value or "").strip() not in ("", "-", "–", "—", "--")


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

    # ------------------------------------------------------------ ค่าตั้งของใบ (ผู้ใช้ 2026-11-20 — ไม่แสดง ≠ ลบข้อมูล)
    @property
    def is_cal(self) -> bool:
        return self.job.kind == "calibration"

    def u_of(self, r):
        """U (%) ที่ใช้ในมาตรวัด/กราฟ/Error% ± U — ปิดในค่าตั้ง = None (ตารางผลใบรับรองใช้ u_column แยก)"""
        return r.u if (self.o.cal_u if self.is_cal else self.o.insp_u) else None

    def flow_2sd(self) -> bool:
        return self.o.cal_flow_2sd if self.is_cal else self.o.insp_flow_2sd

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
        if self.lang == "th" and not w.mix:        # โหมด mix: ชื่อชนิดเครื่องอังกฤษอย่างเดียว (ศัพท์เทคนิค)
            device = f'{w.device_th(self.pump)} <span class="alt">{w.device(self.pump, lower=True)}</span>'
        return (f'<header class="hdr"><div class="co">{mark}<div class="cotext">'
                f'<div class="coname">{esc(self.o.company)}</div><div class="coaddr">{esc(self.address())}</div></div></div>'
                f'<div class="ttl"><h1>{w(title_key)}</h1><div class="kind">{w(kind_key)}</div>'
                f'<div class="sub">{device}</div><div class="pg">{w("page")} {page} / {pages}</div></div></header>')

    def footer(self, page, pages):
        """ท้ายกระดาษ: บริษัท · DeltaM เวอร์ชัน · เลขงาน + เลขหน้า · บรรทัดเลขผล·SHA-256 (ไม่มีคำนำหน้า — ผู้ใช้ 2026-11-20)"""
        from config.constants import APP_VERSION
        made = self.w("made_by", v=APP_VERSION) if self.o.footer_version else ""
        trace = self.trace_text() if self.o.footer_trace else ""
        return (f'<footer class="foot"><span>{esc(self.o.company)}</span>'
                f'<span class="made">{made}</span>'
                f'<span>{esc(self.job.job_no or "—")} · {self.w("page")} {page} / {pages}</span>{trace}</footer>')

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
        # ไม่มีข้อมูล หรือกรอก "-" = ไม่มี (ผู้ใช้ 2026-11-20) -> "—" แบบเดิม
        contact = " · ".join(p.strip() for p in (info.contact, info.contact_phone) if has_value(p))
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
                # ใบ Inspection: ไม่ใส่ค่าที่วัด บอกว่า "เตือนเมื่อมีการอุดตัน" (ผู้ใช้ 2026-11-19 — เดิม "ทำงานปกติ")
                # ค่าละเอียดอยู่ในใบ Calibration
                detail = w("occl_alarm_ok") if status == checklist.PASS else ""
            elif stats is not None:
                mean, sd2, digits = stats
                unit = self.info.occl_unit or "kPa"
                detail = (w("occl_detail", m=f"{mean:.{digits}f}", s=f"{sd2:.{digits}f}", u=unit) if self.o.cal_occl_2sd
                          else w("occl_detail_mean", m=f"{mean:.{digits}f}", u=unit))
            elif code == "occlusion":
                detail = w("occl_cal")
            elif code == "battery" and self.info.battery_min:
                # ไม่ใช่การทดสอบ: "ใช้งานด้วยแบตเตอรี่ได้มากกว่า 30 นาที" (อัตราทดสอบของงานเก่าไม่แสดง — ผู้ใช้ 2026-11-20)
                detail = w("battery_detail", m=f"{float(self.info.battery_min):g}")
            elif code == "battery" and not detail and status == checklist.PASS:
                detail = w("works_ok")          # ไม่ได้กรอกเวลา (งานเก่า) — ยังมีคำบรรยายใต้ชื่อข้อ
            elif not detail and status == checklist.PASS and code in checklist.PASS_DETAIL:
                detail = w.pick(*checklist.PASS_DETAIL[code])
            rows.append((w.term(th, en), detail, status))     # ชื่อรายการ = ศัพท์เทคนิค (mix = อังกฤษ)
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
        ref = (f'<em>{w("supply_ref", v=esc(self.o.supply_ref))}</em>' if self.o.supply_ref else "")   # ผู้ใช้ 2026-11-20
        return (f'<div class="safe3"><div><b>{w("supply")}</b><span>{dash(info.supply_v, "{:g} V")}</span>{ref}</div>'
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
        """กล่องผล: ข้อความสรุป (+ แถวผลอัตราการไหลแบบเรียบ — ใบ Inspection ที่ไม่ใช่ Calibration) · ผลรวมตัวใหญ่
        คำไม่ซ้ำ (ผู้ใช้ 2026-11-19): หัวซ้าย "ผลการตรวจ" · แถว rate "อยู่ในเกณฑ์/นอกเกณฑ์" · ขวา "สรุปผล" + ผ่าน/ไม่ผ่าน กลางกล่อง"""
        w, ok = self.w, self.job.overall_pass()
        lines = ""
        if flow and self.job.rates:
            rows = "".join(
                f'<tr><td>{r.set_rate:g}<i>ml/h</i></td><td>{self.flow_text(r)}<i>ml/h</i></td>'
                f'<td class="e">{num(r.error, ERR_DP, True)}<i>%</i></td><td>±{r.tol:g}<i>%</i></td>'
                f'<td class="{"pass" if r.passed else "fail"}">{w("in_tol") if r.passed else w("out_tol")}</td></tr>'
                for r in self.job.rates[:3])
            lines = (f'<table class="vfig"><thead><tr><th>{w("set_rate")}</th><th>{w("measured")}</th><th>Error%</th>'
                     f'<th>{w("tolerance")}</th><th>{w("verdict")}</th></tr></thead><tbody>{rows}</tbody></table>')
            if len(self.job.rates) > 3:
                lines += f'<div class="vmore">{w("see_pn", p=1 + len(self.job.rates))}</div>'
        return (f'<div class="verdict"><div class="vt"><b>{w("result" if ticks else "result_cal")}</b><p>{statement}</p>{lines}</div>'
                f'<div class="vr"><span class="vl">{w("verdict_overall")}</span>'
                f'<span class="vv{"" if ok else " fail"}">{w("ok") if ok else w("fail")}</span></div></div>')

    def signs(self, slots):
        """ช่องลายเซ็นตามค่าตั้ง (services/report/signatures.py — ผู้ใช้ 2026-11-20): บทบาท · ภาพลายเซ็น · ชื่อ-นามสกุล · ตำแหน่ง
        แบบเรียบ ชิดซ้าย ไม่มีเส้นเมื่อมีภาพลายเซ็น (มีเส้นบางเฉพาะช่องที่ต้องเซ็นมือ) · ไม่มีวันที่"""
        w, cells = self.w, []
        operator = str(self.job.job.get("operator") or "")
        for slot in [s for s in slots if s.show]:
            name, image_path = signatures.resolve(slot, self.o.people, operator, self.lang)
            image = _image_uri(image_path)
            # หัวช่อง: บทบาท + ตำแหน่ง ("Inspected by  PM Engineer") · ภาพลายเซ็น · ชื่อ-นามสกุล — สูงเท่าแบบเดิม 3 บรรทัด
            role = f'<span class="srole">{esc(slot.role(w.term_lang))}</span>'
            position = esc(slot.position(w.term_lang))
            head = role + (f'<span class="sen">{position}</span>' if position else "")
            pad = f'<img src="{image}" alt="">' if image else ""
            shown = esc(name) if name else f'<span class="sph">{w("name")}</span>'
            cells.append(f'<div class="sg4{" img" if image else ""}"><div class="shd">{head}</div>'
                         f'<div class="spad">{pad}</div>'
                         f'<div class="sname{" set" if name else ""}">{shown}</div></div>')
        if not cells:
            return ""
        return f'<div class="signs4 n{len(cells)}">{"".join(cells)}</div>'

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
        unit = (f"{r.unit_s:.2f} ± {r.unit_sd:.2f} s" if r.unit_sd is not None else seconds(r.unit_s)) \
            if r.unit_s is not None else "—"
        if r.volume_ml is not None:
            volume = f"{r.volume_ml:.3f}" + (f" ± {r.volume_sd:.3f}" if r.volume_sd is not None else "") + " ml"
        else:
            volume = "—"
        return [(w("measured"), f"{self.flow_text(r)} ml/h"), (w("n_cyc" if cyc else "n_tim"), str(r.n)),
                (w("t_cyc" if cyc else "t_tim"), unit if r.unit_s is not None else "—"),
                (w("t_all"), duration(r.minutes * 60.0) + self.set_text(r)),
                (w("v_cyc" if cyc else "v_tim"), volume), (w("v_all"), ml(r.total_ml))] + (
                [(w("spread"), dash(r.sd2, "{:.2f} %"))] if self.flow_2sd() else [])

    def trace_text(self) -> str:
        """ท้ายกระดาษ: เลขผล + SHA-256 ย่อของ raw.csv.gz ทุก rate — เปิดผลนั้นในโปรแกรมแล้วกด "ตรวจย้อน" ได้ทุกตัวเลข
        (อยู่ท้ายกระดาษ ไม่กินพื้นที่เนื้อหา · > 4 rate แสดงแค่เลขผล)"""
        items = []
        rates = self.job.rates
        for r in rates:
            if not r.ref:
                continue
            sha = str(r.summary.get("raw_sha256") or "")
            items.append(f"#{esc(r.ref)}" + (f"·{esc(sha[:8])}" if sha and len(rates) <= 4 else ""))
        # บรรทัดของตัวเองใต้แถวท้ายกระดาษ (เดิมอยู่กลางแถว -> ชื่อบริษัท/เลขงานถูกตัดเป็น … เมื่อหลาย rate)
        return f'<div class="ftrace"><b>{" ".join(items)}</b></div>' if items else ""

    def set_text(self, r) -> str:
        """ต่อท้ายเวลาที่วัด: ค่าที่ตั้ง (ผู้ใช้เห็น 10:54 ทั้งที่ตั้ง 10 นาที — บอกให้ชัดว่าวัดครบรอบเต็ม)"""
        if r.set_minutes:
            return f' <i class="setv">· {self.w("set_min", m=f"{r.set_minutes:g}")}</i>'
        if r.set_cycles:
            return f' <i class="setv">· {self.w("set_cyc", n=r.set_cycles)}</i>'
        return ""

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
                self.signs(self.o.sign_insp),
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
                f'<div class="gg">{gauge(self.pump, r.error, self.u_of(r), r.tol, 330, slim=True)}</div>')
        chart = flow_chart(w, self.pump, r.series, r.set_rate, r.measured, r.tol, bw, 236, u_pct=self.u_of(r),
                           **self.chart_options())
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
        sd2 = self.o.cal_occl_2sd
        if stats is None:
            mean = "—"
        else:
            mean = f"{stats[0]:.{stats[2]}f}" + (f" ± {stats[1]:.{stats[2]}f}" if sd2 else "")
        limit = (f"{info.occl_low:g} – {info.occl_high:g}" if info.occl_low is not None and info.occl_high is not None else "—")
        status = info.occl_status()
        result = (f'<td class="{"pass" if status == checklist.PASS else "fail"}">'
                  f'{w("ok") if status == checklist.PASS else w("fail")}</td>') if status else '<td class="na">—</td>'
        level = f'{esc(info.occl_level)} · ' if info.occl_level else ""
        return (f'<table class="tb"><thead><tr><th class="l">{w("occl_row")}</th><th>{w("occl_run")} 1</th>'
                f'<th>{w("occl_run")} 2</th><th>{w("occl_run")} 3</th><th>{w("mean_2sd" if sd2 else "mean")}</th><th>{w("occl_limit")}</th>'
                f'<th>{w("verdict")}</th></tr></thead>'
                f'<tbody><tr><td class="l">{w("occl_level")} {level}{esc(info.occl_unit or "kPa")}</td>'
                f'<td>{runs[0]}</td><td>{runs[1]}</td><td>{runs[2]}</td>'
                f'<td><b>{mean}</b></td><td>{limit}</td>{result}</tr></tbody></table>')

    def balance_dates(self) -> list:
        """แถววันสอบเทียบ/ครบกำหนดของตราชั่ง (ใบ Calibration — ผู้ใช้ 2026-11-20) · ไม่ได้ตั้ง = ไม่มีแถว"""
        w, o = self.w, self.o
        cal, due = (o.balance_cal_date or "").strip(), (o.balance_due_date or "").strip()
        if not (cal or due):
            return []
        rows = [(w("bal_cal"), esc(w.date(cal)))] if cal else []     # แยก 2 แถว — แถวเดียวยาวจนตัดบรรทัดกลางวันที่
        if due:
            rows.append((w("bal_due"), esc(w.date(due))))
        return rows

    def evaporation_cell(self) -> tuple[str, str]:
        """ค่าน้ำที่ระเหย + วิธี (ใช้ trap = ขีดฆ่าค่าประมาณ ไม่ชดเชย) และหมายเหตุเหตุผล — ผลเก่าแสดงแบบเดิม"""
        w, env = self.w, self.job.env
        method, evap, model = env.get("evap_method") or "", env.get("evap"), env.get("evap_model")
        if not method:                                  # ผลก่อน 2026-11-20 (self-check หรือไม่มี)
            return (f"{abs(evap):.3f} g/h" if evap else "—"), ""
        if method == "trap":
            struck = f'<s>{model:.3f} g/h</s> ' if model else ""
            return f'{struck}<i class="evm">{w("evap_trap")}</i>', w("evap_trap_note")
        if method == "self_check":
            return f'{abs(evap or 0.0):.3f} g/h <i class="evm">{w("evap_self")}</i>', ""
        if method == "model":
            return f'{(model or 0.0):.3f} g/h <i class="evm">{w("evap_model")}</i>', w("evap_model_note")
        return f'— <i class="evm">{w("evap_off")}</i>', ""

    def volume_strip(self):
        w, env = self.w, self.job.env
        water_t = dash(env.get("water_t"), "{:.1f} °C")
        evap, reason = self.evaporation_cell()
        cells = [(f'{w("density")} · {water_t}', dash(env.get("density"), "{:.4f} g/ml")),
                 (w("per_gram"), dash(env.get("per_gram"), "{:.4f} ml")),
                 (w("evap"), evap)]
        note = w("volume_note") + (" " + reason if reason else "")
        return ('<div class="env v3">' + "".join(f'<div><b>{a}</b><span>{b}</span></div>' for a, b in cells)
                + f'</div><p class="note">{note}</p>')

    @staticmethod
    def u_ml_h(r) -> float | None:
        """U เป็น ml/h ของ 1 rate: ค่าจากงบความไม่แน่นอนที่เก็บไว้ (ไม่ปัด) — ไม่มีงบแต่มี U % คิดจากค่าที่วัดได้"""
        budget = r.summary.get("uncertainty") or {}
        if budget.get("U_ml_h") is not None:
            return float(budget["U_ml_h"])
        return None if r.u is None else r.measured * r.u / 100.0

    def u_cell(self, r) -> str:
        """ช่อง U ในตารางผลใบรับรอง: ml/h 4 ตำแหน่ง หรือ % 3 ตำแหน่ง ตามค่าตั้ง (ผู้ใช้ 2026-11-20)"""
        if self.o.u_column == "pct":
            return ("±" + u_text(r.u)) if r.u is not None else "—"
        value = self.u_ml_h(r)
        return "—" if value is None else f"±{value:.4f}"

    def calibration_summary(self, page_no, pages):
        w, rates = self.w, self.job.rates
        show_u, show_sd = self.o.u_column != "hide", self.o.cal_flow_2sd
        rows = "".join(
            f'<tr><td class="l"><b>{r.set_rate:g}</b></td><td class="l mt">{w.method(r.method, tech=False)}</td>'
            f'<td>{duration(r.minutes * 60.0)}</td><td>{r.n}</td><td><b>{self.flow_text(r)}</b></td>'
            f'<td><b class="ev">{num(r.error, ERR_DP, True)}</b></td>'
            + (f'<td>{self.u_cell(r)}</td>' if show_u else "")
            + (f'<td>{dash(r.sd2, "{:.2f}")}</td>' if show_sd else "")
            + f'<td>±{r.tol:g}</td>'
            f'<td class="{"pass" if r.passed else "fail"}">{w("ok") if r.passed else w("fail")}</td></tr>' for r in rates)
        u_unit = "%" if self.o.u_column == "pct" else "ml/h"
        head = (f'<tr><th class="l">{w("set_rate")}<i>ml/h</i></th><th class="l">{w("split")}</th>'
                f'<th>{w("duration")}</th><th>n</th><th>{w("measured")}<i>ml/h</i></th>'
                f'<th>{w("error")}</th>'
                + (f'<th>U<i>{u_unit}</i></th>' if show_u else "")
                + (f'<th>±2SD<i>%</i></th>' if show_sd else "")
                + f'<th>{w("tolerance")}<i>%</i></th><th>{w("verdict")}</th></tr>')
        if not show_u:
            unc = ""
        elif any(r.u is not None for r in rates):
            unc = " · " + w("unc_note_mlh" if self.o.u_column == "ml_h" else "unc_note")
        else:
            unc = " · " + w("unc_none")
        table = (f'<table class="tb res"><thead>{head}</thead><tbody>{rows}</tbody></table>'
                 f'<p class="note">{w("err_note")}{unc}</p><p class="note">{w("time_note")}</p>'
                 f'<p class="note">{w("split_note")}</p>')
        o, info = self.o, self.info
        balance = kv([(w("balance"), esc(" · ".join(p for p in (o.balance_model, o.balance_serial) if p) or "—")),
                      (w("capacity"), esc(" · ".join(p for p in (o.balance_capacity, f'{w("readability")} {o.balance_readability}'
                                                                if o.balance_readability else "") if p) or "—"))]
                     + self.balance_dates(), "tight")
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
        body = [self.header("cal_kind", "cal_title", page_no, pages), self.meta("date_cal"), self.who("device_cal"),
                self.sec(1, w("results"), "results", table, "results"),
                self.sec(2, w("occl"), "occl", self.occlusion_table()),
                self.sec(3, w("tools"), "tools", tools),
                self.sec(4, w("volume"), "volume", self.volume_strip()),
                self.verdict(statement, ticks=False), self.signs(o.sign_cal), self.footer(page_no, pages)]
        return self.page("".join(body), "cal")

    def rate_block(self, r):
        w = self.w
        info = (f'<div class="rt"><b>{r.set_rate:g} ml/h</b>{self.result_word(r)}</div>'
                f'<div class="mt">{w.method(r.method)}</div>')
        u = self.u_of(r)
        if u is not None:
            info += (f'<div class="rerr lab"><em>{w("err_u")}</em><span><b>{num(r.error, ERR_DP, True)}</b>'
                     f'<i>± {u_text(u)}</i></span></div>')
        else:
            info += (f'<div class="rerr lab"><em>{w("error")}</em><span><b>{num(r.error, ERR_DP, True)}</b>'
                     f'</span></div>')
        info += self.rows_html(self.detail_rows(r), "tight")
        graph = (f'<div class="gv">{flow_chart(w, self.pump, r.series, r.set_rate, r.measured, r.tol, 328, 196, u_pct=u, **self.chart_options())}'
                 f'{vgauge(w, self.pump, r.error, u, r.tol, 196)}</div>')
        return f'<div class="rb"><div>{info}</div><div>{graph}</div></div>'

    def calibration_technical(self, rates, page_no, pages, first=True):
        w, tol = self.w, self.job.tol
        body = [self.header("cal_kind", "tech_title", page_no, pages)]
        no = 2              # หน้าเทคนิคถัดไป: หัวข้อ 2 ต่อจากหน้าแรก
        if first:
            chart, slope = error_chart(w, self.pump, self.job.rates, tol, 470, 176, show_u=self.o.cal_u)
            worst = max(self.job.rates, key=lambda r: abs(r.error))
            any_u = any(self.u_of(r) is not None for r in self.job.rates)
            margin = min(tol - abs(r.error) - (self.u_of(r) or 0.0) for r in self.job.rates)
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

    def uncertainty_page(self, page_no, pages):
        """หน้าสุดท้ายของใบ Calibration: U เป็น ml/h (4 ตำแหน่ง) และ % (3 ตำแหน่ง) + งบรายองค์ประกอบ + แบบจำลอง/ที่มา
        (ผู้ใช้ 2026-11-19: ตามสากลรายงาน U เป็นหน่วยของค่าที่วัด — % ใส่คู่กัน) · ค่าทุกตัวมาจาก summary.uncertainty ของแต่ละผล"""
        from services.report.text import UNC_NAMES
        w = self.w
        rates = [r for r in self.job.rates if (r.summary.get("uncertainty") or {}).get("components")]
        rows = "".join(
            f'<tr><td class="l"><b>{r.set_rate:g}</b></td><td>{self.flow_text(r)}</td><td>{num(r.error, ERR_DP, True)}</td>'
            f'<td><b>± {b["U_ml_h"]:.4f}</b></td><td>± {b["U_pct"]:.3f}</td><td>{b["k"]:.2f}</td><td>≈ 95 %</td></tr>'
            for r in rates for b in [r.summary["uncertainty"]])
        head = (f'<tr><th class="l">{w("set_rate")}<i>ml/h</i></th><th>{w("measured")}<i>ml/h</i></th><th>{w("error")}</th>'
                f'<th>{w("unc_U_mlh")}<i>ml/h</i></th><th>{w("unc_U_pct")}<i>%</i></th><th>{w("unc_k")}</th>'
                f'<th>{w("unc_conf")}</th></tr>')
        summary = f'<table class="tb res"><thead>{head}</thead><tbody>{rows}</tbody></table>'
        names: list[str] = []
        for r in rates:
            for c in r.summary["uncertainty"]["components"]:
                if c["name"] not in names:
                    names.append(c["name"])
        tables = []
        for start in range(0, len(rates), 6):          # rate มาก: แบ่งตารางละ 6 คอลัมน์
            part = rates[start:start + 6]
            head = f'<tr><th class="l">{w("unc_comp")}</th>' + "".join(f'<th>{r.set_rate:g}<i>ml/h</i></th>' for r in part) + "</tr>"
            body = []
            for name in names:
                cells = []
                for r in part:
                    comp = next((c for c in r.summary["uncertainty"]["components"] if c["name"] == name), None)
                    cells.append(f'<td>{comp["u_rel_pct"]:.4f}</td>' if comp else "<td>—</td>")
                label_th, label_en = UNC_NAMES.get(name, (name, name))
                body.append(f'<tr><td class="l">{w.term(label_th, label_en)}</td>{"".join(cells)}</tr>')
            for key, fmt_ in (("unc_uc", lambda b: f'{b["u_c_pct"]:.4f}'), ("unc_k", lambda b: f'{b["k"]:.2f}'),
                              ("unc_Upct_row", lambda b: f'{b["U_pct"]:.3f}'), ("unc_Umlh_row", lambda b: f'{b["U_ml_h"]:.4f}')):
                body.append(f'<tr class="tot"><td class="l"><b>{w(key)}</b></td>'
                            + "".join(f'<td><b>{fmt_(r.summary["uncertainty"])}</b></td>' for r in part) + "</tr>")
            tables.append(f'<table class="tb ub"><thead>{head}</thead><tbody>{"".join(body)}</tbody></table>')
        first = rates[0].summary["uncertainty"] if rates else {}
        settings = first.get("settings") or {}
        rep_lines = []
        for r in rates:
            budget_ = r.summary["uncertainty"]
            rep = budget_.get("repeatability") or {}
            old = next((c for c in budget_["components"] if c["name"] == "Repeatability (earlier runs)"), None)
            if rep:
                text = (f'2SD {rep["sd2_pct"]:.4f} % (± {rep["sd2_ml_h"]:.4f} ml/h) · '
                        + ", ".join(f'#{s["id"]}' for s in rep.get("studies", [])))
            elif old is not None:               # ผลเก่า (วิธีเดิม): บอกที่มาตามที่บันทึกไว้ ไม่คิดใหม่
                text = esc(old.get("source", ""))
            else:
                text = w("unc_rep_none")
            rep_lines.append(w("unc_rep", r=f"{r.set_rate:g}", s=text))
        notes = [w("unc_eq"), w("unc_method"),
                 w("unc_certs", b=esc(settings.get("balance_cert") or "—"), t=esc(settings.get("thermo_cert") or "—")),
                 " · ".join(rep_lines)]
        if any(r.summary["uncertainty"].get("simulated") for r in rates):
            notes.append(f'<b class="fail">{w("unc_sim")}</b>')
        model = "".join(f'<p class="note">{line}</p>' for line in notes)
        body = [self.header("cal_kind", "unc_title", page_no, pages),
                self.sec(1, w("unc_sum"), "unc_sum", summary),
                self.sec(2, w("unc_budget"), "unc_budget", "".join(tables)),
                self.sec(3, w("unc_model"), "unc_model", model),
                self.footer(page_no, pages)]
        return self.page("".join(body), "unc")

    def has_uncertainty(self) -> bool:
        return any((r.summary.get("uncertainty") or {}).get("components") for r in self.job.rates)

    # ------------------------------------------------------------ ทั้งใบ
    def pages(self) -> list[tuple[str, str]]:
        """[(ชื่อหน้า, HTML)]"""
        job = self.job
        if job.kind == "calibration":
            chunks, unc = cal_parts(job)
            total = 2 + len(chunks) + (1 if unc else 0)
            out = [("Calibration-p1-inspection", self.inspection_page(1, total, cal=True)),
                   ("Calibration-p2-summary", self.calibration_summary(2, total))]
            for index, chunk in enumerate(chunks):
                out.append((f"Calibration-p{3 + index}-technical",
                            self.calibration_technical(chunk, 3 + index, total, first=index == 0)))
            if unc:                     # หน้าสุดท้าย: ความไม่แน่นอน (มีเมื่อผลมีงบ — ผลเก่าไม่มี)
                out.append((f"Calibration-p{total}-uncertainty", self.uncertainty_page(total, total)))
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


def cal_parts(job: ReportJob) -> tuple[list[list], bool]:
    """หน้าของใบ Calibration หลัง 2 หน้าแรก ตามค่าตั้ง (ผู้ใช้ 2026-11-20): (กลุ่ม rate ของหน้าเทคนิค, มีหน้าความไม่แน่นอนไหม)
    all = ครบ · no_uncertainty = ไม่มีหน้าความไม่แน่นอน (1–3) · certificate = 2 หน้าแรก — ไม่แสดง ≠ ลบ (ผลในฐานข้อมูลครบเหมือนเดิม)"""
    pages_set = getattr(job.options, "cal_pages", "all")
    rates = job.rates
    chunks = [rates[:TECH_FIRST]] + [rates[i:i + TECH_MORE] for i in range(TECH_FIRST, len(rates), TECH_MORE)]
    chunks = [c for c in chunks if c] if rates else []
    unc = any((r.summary.get("uncertainty") or {}).get("components") for r in rates)
    if pages_set == "certificate":
        return [], False
    return chunks, unc and pages_set != "no_uncertainty"


def page_count(job: ReportJob) -> int:
    if job.kind == "calibration":
        chunks, unc = cal_parts(job)
        return 2 + len(chunks) + (1 if unc else 0)
    return 1 + len(job.rates)
