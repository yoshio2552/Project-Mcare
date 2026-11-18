"""แบบ FableA รุ่นที่ 2 — หน้าตา Ledger ของ FableA + สีตามชนิดเครื่องและลูกเล่นสีตัวอักษรแบบ FableF

เงื่อนไขของผู้ใช้ (2026-11-18):
  - Infusion = ฟ้า, Syringe = ชมพู (แถบบน, เลขหัวข้อ, เลขงาน, ชื่อเครื่อง, กราฟ) · ป้ายหัวข้อภาษาอังกฤษชิดขวาในฉบับไทย
  - ชนิดเครื่องเขียน Infusion Pump / Syringe Pump ทั้งสองภาษา
  - Inspection หน้า 1: แถบผลอัตราการไหล (ค่าที่ตั้ง ค่าที่วัดได้ คลาดเคลื่อน ±U) · การอุดตันบอกแค่ตรวจจับได้หรือไม่
    · ตรวจขั้นสุดท้ายอยู่ในกล่องสรุปผล · กระแสรั่วเกณฑ์ไม่เกิน 300 µA
  - Inspection หน้า 2: ไม่มีเครื่องชั่งมาตรฐาน ไม่มีการอุดตัน
  - Calibration: ไม่มีช่องประเภทงาน · การอุดตันวัด 3 ครั้งอยู่ที่นี่เท่านั้น · วิธีแบ่งช่วงวัดแยกราย rate
  - กราฟ flow รายช่วง: แกน Y ตรึงที่ค่าที่ตั้ง ±25 % · แกน X เป็นนาที · เส้นตารางจาง · มาตรวัดความคลาดเคลื่อนใต้กราฟพร้อมค่าที่ชี้
  - กราฟความคลาดเคลื่อน: เล็กลง แกนอัตราแบบ log · ค่า ± U · เส้นแนวโน้ม linear regression เส้นประ
  - เวลาต่อรอบ / ปริมาตรต่อรอบ มี ± และมีเวลารวม / ปริมาตรรวม · ลายเซ็นมีช่องลายมือชื่อและชื่อ-นามสกุล ไม่มีวันที่
ตัวเลขเป็นข้อมูลสมมติ (ชุดเดียวกับแบบอื่น) — 10 ml/h ของ Calibration ใช้แบ่งช่วงเวลา 60 วินาที เป็นตัวอย่างของ rate ต่ำ
"""
import math

import styles
from blocks import box, kv, num, pick
from content import ADDRESS, BALANCE, CHECKS, COMPANY, CUSTOMER, DATE, ENV, JOBS, TEXT, series

PUMP = {"infusion": dict(acc="#0B6FA4", bar="#38BDF8", tint="#E0F2FE"),
        "syringe": dict(acc="#B0306A", bar="#F472B6", tint="#FCE7F3")}
GREEN, ORANGE, INK, MUTE, GRID, AXIS = "#166534", "#D9691A", "#141414", "#5C5F66", "#E6E9ED", "#9AA2AC"
FONT = "Sarabun, sans-serif"
LEAK_LIMIT = 300                    # µA — ผู้ใช้แจ้งตามมาตรฐาน (2026-11-18)

# ผล Calibration ราย rate: วิธีแบ่งช่วงวัดเลือกได้ต่อ rate (rate ต่ำใช้แบ่งช่วงเวลา)
CAL = [
    dict(set=10.0, method="time", minutes=14.0, n=14, unit=60.0, unit_sd=0.1, meas=9.87, err=-1.3, sd2=3.1, u=0.9, seed=9001),
    dict(set=50.0, method="cycle", minutes=14.7, n=58, unit=15.2, unit_sd=0.2, meas=50.42, err=0.8, sd2=2.4, u=0.6, seed=9078),
    dict(set=200.0, method="cycle", minutes=15.0, n=231, unit=3.9, unit_sd=0.1, meas=196.10, err=-2.0, sd2=7.8, u=0.7, seed=9155),
]
# Inspection: วัด rate เดียวครั้งเดียว (ค่าเพิ่มจาก content.JOBS)
INSP = {"infusion": dict(u=0.6, unit_sd=0.2, method="cycle"), "syringe": dict(u=0.9, unit_sd=0.1, method="time")}

# ตัวเลือกของแบบย่อยที่แยกจากตัวหลัก (styles.VARIANTS["FableA1".."FableA3"]["opts"]) — ตัวหลัก FableA ไม่มีตัวเลือก
#   control        เลขแบบฟอร์ม + ครั้งที่แก้ไขที่หัวและท้ายกระดาษ (เอกสารควบคุมตาม ISO/IEC 17025)
#   quiet          ลดสี/ป้ายซ้ำ: ไม่มีป้ายอังกฤษตัวพิมพ์ใหญ่ หัวข้อตัวพิมพ์ปกติ แถบผลไม่มีพื้นเทา ตัวเลขผลเป็นหมึกดำ
#   summary_top    กล่องสรุปผลขึ้นก่อนใต้แถบข้อมูลงาน (ผู้อ่านของโรงพยาบาลเห็นผลทันที)
#   inline_gauge   ตารางผลสอบเทียบมีมาตรวัดเล็กราย rate (ตำแหน่ง error ± U ในเกณฑ์)
#   compact_checks สภาพภายนอก/การทำงานเป็นตารางติ๊กแบบกระชับ 3 คอลัมน์
#   remarks        ช่องหมายเหตุ 2 บรรทัดก่อนกล่องสรุปผล (มีในใบงานเดิมของบริษัท)
#   main           Main Fable: แบบ quiet แต่คงสีของค่าคลาดเคลื่อน + ป้ายหัวข้อภาษาอังกฤษด้านขวาในฉบับไทย (แบบ FableA3)
#   rate_error     หน้าเทคนิค: ค่าคลาดเคลื่อน ± U ตัวใหญ่สีตามชนิดเครื่องที่หัวของแต่ละ rate
#   lab            Main Fable-1: ไม่ให้ค่าเดิมซ้ำในหน้าเทคนิค — ค่าคลาดเคลื่อน ± U ขึ้นที่เดียวต่อ rate (ในบล็อกของ rate)
#                  กราฟรวมไม่มีป้ายตัวเลข (เป็นภาพรวม ค่าอยู่ในตาราง) · ไม่มีมาตรวัดใต้กราฟราย rate (กราฟสูงขึ้นแทน)
#                  · ป้ายเส้นค่าเฉลี่ยไม่ซ้ำตัวเลขกับแถว "ค่าที่วัดได้" · เขียนแบบมาตรวิทยา "−1.3 ± 0.9 %" หน่วยเดียว
OPT: dict = {}
FORMS = {"insp_kind": "FM-INS-01", "cal_kind": "FM-CAL-01"}
_form = ["FM-INS-01"]

X = dict(
    device=dict(infusion=("Infusion Pump", "Infusion Pump"), syringe=("Syringe Pump", "Syringe Pump")),
    date_insp=("วันที่ตรวจ", "Inspection date"), date_cal=("วันที่สอบเทียบ", "Calibration date"),
    customer_en="CUSTOMER", device_en="EQUIPMENT",
    visual_en="VISUAL INSPECTION", function_en="FUNCTION INSPECTION", performance_en="PERFORMANCE INSPECTION",
    safety_en="ELECTRICAL SAFETY", parts_en="PARTS REPLACED", flow_en="FLOW RATE RESULT", chart_en="FLOW PER INTERVAL",
    method_en="METHOD AND DETAILS", remarks_en="REMARKS",
    form=("แบบฟอร์ม", "Form"), rev=("แก้ไขครั้งที่ 00", "Rev. 00"), remarks=("หมายเหตุ", "Remarks"),
    chk_legend=("ติ๊ก = ผ่าน · กากบาท = ไม่ผ่าน · ขีด = ไม่มีในเครื่องนี้", "tick = pass · cross = fail · dash = not fitted"),
    in_tol=("ตำแหน่งในเกณฑ์", "Within tolerance"),
    trend_tag=("แนวโน้ม", "trend"), cond_en="CONDITIONS", results_en="RESULTS", occl_en="OCCLUSION ALARM",
    tools_en="METHOD AND REFERENCE STANDARD", err_en="ERROR AGAINST TOLERANCE", rate_en="RESULTS PER SET RATE",
    volume_en="WEIGHT TO VOLUME",
    flow_strip=("อัตราการไหล · วัดที่อัตราเดียว", "Flow rate · measured at one rate"),
    details_p2=("รายละเอียดและกราฟหน้า 2", "details and chart on page 2"),
    set=("ค่าที่ตั้ง", "Set rate"), meas=("ค่าที่วัดได้", "Measured"), err=("คลาดเคลื่อน", "Error"),
    unc=("ความไม่แน่นอน", "Uncertainty"), tol=("เกณฑ์ยอมรับ", "Tolerance"), result=("ผล", "Result"),
    supply=("แรงดันไฟที่จ่าย", "Supply voltage"), leak=("กระแสรั่วของเครื่อง", "Equipment leakage current"),
    leak_lim=("เกณฑ์ ไม่เกิน {v} µA", "limit not over {v} µA"),
    claim=("เคลมประกัน", "warranty"), new=("เปลี่ยนใหม่", "new"),
    parts_n=("เปลี่ยน {n} รายการ · เคลมประกัน {c} รายการ", "{n} parts replaced · {c} under warranty"),
    received=("อุปกรณ์ที่รับมากับเครื่อง", "Accessories received"),
    fin1=("ตรวจความเรียบร้อยทั้งเครื่องแล้ว", "Whole unit checked"), fin2=("ติดป้ายตรวจสภาพแล้ว", "Inspection label attached"),
    overall=("ผลรวม", "Overall"),
    sign=("ลายมือชื่อ", "Signature"), name=("ชื่อ-นามสกุล", "Full name"),
    esign=("ลายมือชื่ออิเล็กทรอนิกส์", "Electronic signature"),
    occl_ok=("ตรวจจับได้", "detected"), occl_cal=("วัด 3 ครั้ง ดูหน้า 2", "3 runs, see page 2"), flow_cal=("3 อัตรา ดูหน้า 2", "3 rates, see page 2"),
    cyc=("จับรอบปั๊ม", "Pump cycle"), cyc_tech="Cycle-synchronous",
    tim=("แบ่งช่วงเวลา", "Time interval"), tim_tech="Fixed time interval",
    split=("การแบ่งช่วงวัด", "Interval method"),
    n_cyc=("จำนวนรอบปั๊ม", "Pump cycles"), n_tim=("จำนวนช่วงวัด", "Intervals"),
    t_cyc=("เวลาต่อรอบเฉลี่ย", "Mean time per cycle"), t_tim=("เวลาต่อช่วงเฉลี่ย", "Mean time per interval"),
    t_all=("เวลารวม", "Total time"),
    v_cyc=("ปริมาตรต่อรอบ", "Volume per cycle"), v_tim=("ปริมาตรต่อช่วง", "Volume per interval"), v_all=("ปริมาตรรวม", "Total volume"),
    spread=("การกระจาย ±2SD", "Spread ±2SD"), err_u=("คลาดเคลื่อน ± U", "Error ± U"),
    minute=("นาที", "min"), x_axis=("นาที", "min"), mean=("ค่าเฉลี่ย", "mean"), each=("ค่าแต่ละช่วงวัด", "each interval"),
    legend_pt=("ค่าที่วัดได้ ± U", "Measured ± U"), legend_fit=("แนวโน้ม linear regression", "Linear regression trend"),
    legend_tol=("เกณฑ์ ±{t:g} %", "Limit ±{t:g} %"),
    trend=("แนวโน้ม", "Trend"), trend_v=("{s} % ต่อ 10 เท่าของอัตรา", "{s} % per decade of rate"),
    worst=("ค่ามากสุด", "Largest error"), worst_v=("{e} % ที่ {r:g} ml/h", "{e} % at {r:g} ml/h"),
    margin=("เผื่อถึงขอบเกณฑ์", "Margin to limit"), margin_v=("{m} % รวม U แล้ว", "{m} % after U"),
    rate_x=("ค่าที่ตั้ง ml/h · สเกล log", "Set rate ml/h · log scale"),
    split_note=("จับรอบปั๊ม = Cycle-synchronous ตามรอบการทำงานของปั๊ม · แบ่งช่วงเวลา = Fixed time interval ใช้กับอัตราต่ำ",
                "Pump cycle = cycle-synchronous · Time interval = fixed time interval, used at low rates"),
    occl_run=("ครั้งที่", "Run"),
)


class D:
    """ข้อความของ 1 ภาษา × 1 ชนิดเครื่อง"""

    def __init__(self, lang, pump):
        self.lang, self.pump, self.i = lang, pump, 0 if lang == "th" else 1
        self.t, self.c = TEXT[lang], PUMP[pump]

    def x(self, key, **kw):
        text = X[key][self.i]
        return text.format(**kw) if kw else text

    def device(self):
        return X["device"][self.pump][self.i]

    def en(self, key):
        return X[key + "_en"] if self.lang == "th" else ""

    def method(self, kind, tech=True):
        name = self.x("cyc" if kind == "cycle" else "tim")
        tech_name = X["cyc_tech" if kind == "cycle" else "tim_tech"]
        if tech and self.lang == "en":            # ฉบับอังกฤษ: ชื่อเทคนิคอย่างเดียว (ไม่ซ้ำคำ)
            return tech_name
        return f'{name} · {tech_name}' if tech else name


# ------------------------------------------------------------------ กราฟ
def _svg(w, h, body):
    return (f'<svg class="chart" xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{FONT}" font-size="12">{body}</svg>')


def _line(x1, y1, x2, y2, color, width=1.0, dash=""):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}"{extra}/>'


def _text(x, y, s, anchor="start", fill=MUTE, weight=""):
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" fill="{fill}"{w}>{s}</text>'


PLOT_LEFT, PLOT_RIGHT = 50, 10      # ขอบของพื้นที่กราฟ — มาตรวัดใต้กราฟใช้ขอบเดียวกันให้แนวตรงกัน


def flow_chart(d, values, unit_s, target, tol, w, h):
    """flow ของแต่ละช่วงวัด (ขั้นบันได) · แกน Y ตรึงค่าที่ตั้ง ±25 % · แกน X นาที · เส้นตารางจาง · เส้นค่าเฉลี่ยสีส้ม"""
    left, right, top, bottom = PLOT_LEFT, PLOT_RIGHT, 16, 22
    pw, ph = w - left - right, h - top - bottom
    low, high = target * 0.75, target * 1.25
    minutes = len(values) * unit_s / 60.0
    sx = lambda m: left + pw * m / minutes
    sy = lambda v: top + ph * (high - v) / (high - low)
    acc, tint = d.c["acc"], d.c["tint"]
    digits = 2 if target < 20 else 1 if target < 100 else 0
    out = []
    # เส้นตารางจาง: แนวนอนทุก 5 % ของค่าที่ตั้ง · แนวตั้งทุก 1 / 2 / 5 นาที
    for k in range(-5, 6):
        out.append(_line(left, sy(target * (1 + k / 20)), left + pw, sy(target * (1 + k / 20)), GRID, 0.8))
    grid_step = 1 if minutes <= 16 else 2 if minutes <= 32 else 5
    label_step = 2 if minutes <= 16 else 5 if minutes <= 40 else 10
    m = 0
    while m <= minutes + 1e-6:
        out.append(_line(sx(m), top, sx(m), top + ph, GRID, 0.8))
        m += grid_step
    # แถบเกณฑ์ + เส้นเกณฑ์ประ + เส้นค่าที่ตั้ง
    span = target * tol / 100
    out.append(f'<rect x="{left}" y="{sy(target + span):.1f}" width="{pw}" height="{sy(target - span) - sy(target + span):.1f}" '
               f'fill="{tint}" fill-opacity="0.75"/>')
    out += [_line(left, sy(target + span), left + pw, sy(target + span), acc, 0.9, "4 3"),
            _line(left, sy(target - span), left + pw, sy(target - span), acc, 0.9, "4 3"),
            _line(left, sy(target), left + pw, sy(target), AXIS, 1)]
    marks = [target * (1 + k / 10) for k in (-2, -1, 0, 1, 2)]      # ป้ายที่ −20 / −10 / 0 / +10 / +20 % (เลขลงตัว)
    places = 0 if all(abs(v - round(v)) < 1e-9 for v in marks) else 1
    for k, v in zip((-2, -1, 0, 1, 2), marks):
        out.append(_text(left - 6, sy(v) + 4, f"{v:.{places}f}", "end", INK if k == 0 else MUTE))
    out.append(_text(left + pw, sy(target + span) - 4, f"±{tol:g} %", "end", acc, "600"))
    # ข้อมูล
    clip = lambda v: max(low, min(high, v))
    path = "".join(f'{"M" if i == 0 else "L"}{sx(i * unit_s / 60):.1f},{sy(clip(v)):.1f}H{sx((i + 1) * unit_s / 60):.1f}'
                   for i, v in enumerate(values))
    out.append(f'<path d="{path}" fill="none" stroke="{acc}" stroke-width="1.3" stroke-linejoin="round"/>')
    mean = sum(values) / len(values)
    out.append(_line(left, sy(mean), left + pw, sy(mean), ORANGE, 1.4))
    if OPT.get("lab"):
        # คำอธิบายเส้นแบบมีตัวอย่างเส้น (ค่าตัวเลขอยู่ในแถว "ค่าที่วัดได้" แล้ว ไม่ซ้ำ)
        out.append(_line(left, top - 9, left + 18, top - 9, ORANGE, 1.6))
        out.append(_text(left + 24, top - 5, d.x("mean"), "start", MUTE))
        out.append(_line(left + 90, top - 9, left + 108, top - 9, acc, 1.3))
        out.append(_text(left + 114, top - 5, d.x("each"), "start", MUTE))
    else:
        out.append(_text(left, top - 5, f'{d.x("mean")} {mean:.{digits + 1 if target < 100 else 2}f} ml/h', "start", ORANGE, "600"))
    # แกน
    out += [_line(left, top, left, top + ph, AXIS), _line(left, top + ph, left + pw, top + ph, AXIS)]
    m = 0
    while m <= minutes + 1e-6:
        if sx(m) < left + pw - 34:                   # เว้นที่ท้ายแกนให้ป้ายหน่วย
            out.append(_text(sx(m), top + ph + 16, f"{m:g}", "middle"))
        m += label_step
    out.append(_text(left + pw, top + ph + 16, d.x("x_axis"), "end", INK, "600"))
    return _svg(w, h, "".join(out))


def gauge_limit(err, u, tol):
    """ขอบของมาตรวัด (± %) และค่าล้นขอบไหม

    ปกติ ±1.6 × เกณฑ์ · ค่าคลาดเคลื่อน + U เกินนั้น -> ขยายขอบให้เห็นค่า (ปัดขึ้นเป็นจำนวนเต็ม) สูงสุด ±4 × เกณฑ์
    เกินกว่านั้นลูกศรไปอยู่ที่ขอบ เปลี่ยนเป็นลูกศรชี้ออก และเขียนค่าไว้ที่ปลาย (overflow = True)
    """
    need = abs(err) + u
    limit = max(tol * 1.6, min(tol * 4.0, math.ceil(need + tol * 0.3)))
    return limit, need > limit


def gauge(d, err, u, tol, w):
    """มาตรวัดตามแบบที่ผู้ใช้ส่งมา: แถบเกณฑ์ ±tol · ขีด −tol / 0 / +tol · ลูกศรชี้ค่าพร้อมตัวเลข · แถบจางแสดง ± U"""
    h, left, right = 52, PLOT_LEFT, PLOT_RIGHT
    limit, overflow = gauge_limit(err, u, tol)
    pw = w - left - right
    sx = lambda v: left + pw * (max(-limit, min(limit, v)) + limit) / (2 * limit)
    acc, tint = d.c["acc"], d.c["tint"]
    out = [_line(left, 31, left + pw, 31, AXIS, 1),
           f'<rect x="{sx(-tol):.1f}" y="26" width="{sx(tol) - sx(-tol):.1f}" height="10" fill="{tint}" stroke="{MUTE}" stroke-width="0.8"/>',
           f'<rect x="{sx(err - u):.1f}" y="28" width="{max(2.0, sx(err + u) - sx(err - u)):.1f}" height="6" fill="{acc}" fill-opacity="0.35"/>']
    for v in (-tol, 0, tol):
        out.append(_line(sx(v), 22, sx(v), 40, INK, 1))
        out.append(_text(sx(v), 51, f"{num(v, 0, v != 0)} %", "middle", INK))
    cx = sx(err)
    if overflow and abs(err) > limit:          # ล้นขอบ: ลูกศรชี้ออกนอกสเกลที่ปลาย
        out.append(f'<path d="M{cx:.1f},31 l{9 if err < 0 else -9},-6 v12 z" fill="{acc}"/>')
    else:
        out.append(f'<path d="M{cx:.1f},25 l-6,-9 h12 z" fill="{acc}"/>')
    label = f'{num(err, 1, True)} % <tspan fill="{MUTE}" font-weight="400">± {u:g}</tspan>'
    tx = max(left + 40, min(left + pw - 40, cx))
    out.append(f'<text x="{tx:.1f}" y="12" text-anchor="middle" fill="{acc}" font-weight="700">{label}</text>')
    return _svg(w, h, "".join(out))


def vgauge(d, err, u, tol, h, top=16, bottom=22, w=84):
    """มาตรวัดแนวตั้งข้างขวากราฟราย rate — องค์ประกอบเดียวกับมาตรวัดแนวนอนในใบ Inspection หมุน 90°

    เส้นแกน · กล่องเกณฑ์ ±tol สีอ่อนขอบเทา · ขีดหลัก −tol / 0 / +tol ตัดผ่านกล่องพร้อมตัวเลข · แถบ ± U · ลูกศรชี้ค่า
    ไม่มีขีดย่อย (ผู้ใช้ขอ) · ค่าเกินเกณฑ์: ขยายขอบเอง (gauge_limit) ถ้ายังล้นจะชี้ออกที่ปลายพร้อมตัวเลข
    แนวตั้งตรงกับพื้นที่กราฟ (top/bottom เดียวกับ flow_chart) · ตัวเลขของค่าปกติอยู่ในบล็อกข้อมูลแล้ว จึงไม่ซ้ำที่นี่
    """
    limit, overflow = gauge_limit(err, u, tol)
    ax, ph = 30, h - top - bottom
    sy = lambda v: top + ph * (limit - max(-limit, min(limit, v))) / (2 * limit)
    acc, tint = d.c["acc"], d.c["tint"]
    out = [_line(0.5, top, 0.5, top + ph, GRID, 1),                                   # เส้นคั่นจากกราฟ
           _line(ax, top, ax, top + ph, AXIS, 1),
           f'<rect x="{ax - 5}" y="{sy(tol):.1f}" width="10" height="{sy(-tol) - sy(tol):.1f}" fill="{tint}" stroke="{MUTE}" stroke-width="0.8"/>',
           f'<rect x="{ax - 3}" y="{sy(err + u):.1f}" width="6" height="{max(2.0, sy(err - u) - sy(err + u)):.1f}" '
           f'fill="{acc}" fill-opacity="0.35"/>']
    for v in (tol, 0, -tol):
        out.append(_line(ax - 9, sy(v), ax + 9, sy(v), INK, 1))
        out.append(_text(ax + 14, sy(v) + 4, f"{num(v, 0, v != 0)} %", "start", INK))
    y = sy(err)
    if overflow and abs(err) > limit:
        # ล้นขอบ: ลูกศรชี้ออกที่ปลายสเกล + ตัวเลขของค่า (ที่ปลาย ห่างจากป้ายเกณฑ์)
        if err > 0:     # ชี้ขึ้นที่ปลายบน
            out.append(f'<path d="M{ax:.1f},{top - 2:.1f} l-6,10 h12 z" fill="{acc}"/>')
            out.append(_text(ax + 12, top + 7, f"{num(err, 1, True)} %", "start", acc, "700"))
        else:           # ชี้ลงที่ปลายล่าง
            out.append(f'<path d="M{ax:.1f},{top + ph + 2:.1f} l-6,-10 h12 z" fill="{acc}"/>')
            out.append(_text(ax + 12, top + ph - 1, f"{num(err, 1, True)} %", "start", acc, "700"))
    else:
        out.append(f'<path d="M{ax - 6:.1f},{y:.1f} l-9,-6 v12 z" fill="{acc}"/>')
    out.append(_text(3, top + ph + 16, d.x("err"), "start", INK, "600"))
    return _svg(w, h, "".join(out))


def error_chart(d, rows, tol, w, h):
    """ความคลาดเคลื่อน ± U ของแต่ละค่าที่ตั้ง บนแกนอัตราแบบ log · แถบเกณฑ์ · เส้นแนวโน้ม linear regression (error กับ log อัตรา)"""
    left, right, top, bottom = 40, 12, 10, 34
    pw, ph = w - left - right, h - top - bottom
    lo, hi = math.log10(6), math.log10(330)
    limit = tol * 1.6
    sx = lambda r: left + pw * (math.log10(r) - lo) / (hi - lo)
    sy = lambda v: top + ph * (limit - v) / (2 * limit)
    acc, tint = d.c["acc"], d.c["tint"]
    out = []
    for decade in (1, 10, 100):                     # เส้นตารางจางแบบ log: 7 8 9 10 20 ... 300
        for k in range(1, 10):
            r = decade * k
            if 6 <= r <= 330:
                out.append(_line(sx(r), top, sx(r), top + ph, GRID if k != 1 else "#D3D8DE", 0.8))
    for k in range(-int(limit), int(limit) + 1):
        out.append(_line(left, sy(k), left + pw, sy(k), GRID, 0.8))
    out.append(f'<rect x="{left}" y="{sy(tol):.1f}" width="{pw}" height="{sy(-tol) - sy(tol):.1f}" fill="{tint}" fill-opacity="0.75"/>')
    out += [_line(left, sy(tol), left + pw, sy(tol), acc, 0.9, "4 3"), _line(left, sy(-tol), left + pw, sy(-tol), acc, 0.9, "4 3"),
            _line(left, sy(0), left + pw, sy(0), "#C3C9D0", 0.8)]
    for v in (-tol, 0, tol):
        out.append(_text(left - 6, sy(v) + 4, num(v, 0, v != 0), "end", INK))
    out.append(_text(left - 6, top + 2, "%", "end"))
    # เส้นแนวโน้ม: error = a + b·log10(rate)
    xs = [math.log10(r["set"]) for r in rows]
    ys = [r["err"] for r in rows]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    slope = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)
    fit = lambda r: my + slope * (math.log10(r) - mx)
    x0, x1 = 7, 300
    out.append(f'<line x1="{sx(x0):.1f}" y1="{sy(fit(x0)):.1f}" x2="{sx(x1):.1f}" y2="{sy(fit(x1)):.1f}" stroke="#fff" stroke-width="5"/>')
    out.append(_line(sx(x0), sy(fit(x0)), sx(x1), sy(fit(x1)), ORANGE, 2.2, "9 5"))     # ขอบขาวรองใต้ให้ลอยเหนือแถบเกณฑ์
    # ป้ายแนวโน้มอยู่ใต้เส้น กลางช่องว่างระหว่างค่าที่ตั้ง 2 ค่าแรก (ไม่ทับจุด/ขีด U)
    gap = math.sqrt(rows[0]["set"] * rows[1]["set"])
    out.append(_text(sx(gap), sy(fit(gap)) + 18, f'{d.x("trend_tag")} {num(slope, 2, True)} %', "middle", ORANGE, "700"))
    for r in rows:
        cx, cy = sx(r["set"]), sy(r["err"])
        out.append(_line(cx, sy(r["err"] + r["u"]), cx, sy(r["err"] - r["u"]), acc, 1.6))
        for edge in (r["err"] + r["u"], r["err"] - r["u"]):
            out.append(_line(cx - 5, sy(edge), cx + 5, sy(edge), acc, 1.6))
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.4" fill="{acc}" stroke="#fff" stroke-width="1.2"/>')
        lx = max(left + 40, min(left + pw - 40, cx))
        if not OPT.get("lab"):
            out.append(f'<text x="{lx:.1f}" y="{sy(r["err"] + r["u"]) - 6:.1f}" text-anchor="middle" fill="{INK}" font-weight="700">'
                       f'{num(r["err"], 1, True)}<tspan fill="{MUTE}" font-weight="400"> ± {r["u"]:g}</tspan></text>')
        out.append(_text(cx, top + ph + 16, f'{r["set"]:g}', "middle", INK, "600"))
    out += [_line(left, top, left, top + ph, AXIS), _line(left, top + ph, left + pw, top + ph, AXIS)]
    out.append(_text(left + pw, h - 2, d.x("rate_x"), "end"))
    return _svg(w, h, "".join(out)), slope


# ------------------------------------------------------------------ ชิ้นส่วน
def sec(d, no, title, en_key, body, cls=""):
    en = d.en(en_key)
    alt = f'<span class="en">{en}</span>' if en else ""
    return (f'<section class="sec {cls}"><h2><span class="no">{no}</span><span class="t">{title}</span>{alt}</h2>'
            f'<div class="body">{body}</div></section>')


def header(d, kind, title, page, pages):
    t = d.t
    _form[0] = FORMS[kind]
    if OPT.get("control"):
        page_html = f'{d.x("form")} {_form[0]} · {d.x("rev")} · {t["page"]} {page} / {pages}'
    else:
        page_html = f'{t["page"]} {page} / {pages}'
    return (f'<header class="hdr"><div class="co"><div class="mark">M.Care</div>'
            f'<div class="coname">{COMPANY}</div><div class="coaddr">{ADDRESS[d.lang]}</div></div>'
            f'<div class="ttl"><div class="kind">{t[kind]}</div><h1>{t[title]}</h1><div class="sub">{d.device()}</div></div>'
            f'<div class="pg">{page_html}</div></header>')


def footer(d, job, page, pages):
    if OPT.get("control"):
        return (f'<footer class="foot"><span>{_form[0]} · {d.x("rev")}</span><span>{COMPANY}</span>'
                f'<span><b class="fj">{job}</b> · {d.t["page"]} {page} / {pages}</span></footer>')
    return (f'<footer class="foot"><span>{COMPANY} · {ADDRESS[d.lang]}</span>'
            f'<span><b class="fj">{job}</b> · {d.t["page"]} {page} / {pages}</span></footer>')


def meta(d, job, date_key, service=None):
    """แถบบน — ใบ Inspection มีประเภทงาน · ใบชุด Calibration ไม่มี (ผู้ใช้ขอ)"""
    t = d.t
    cells = [f'<div><b>{t["job"]}</b><span class="jobno">{job}</span></div>', f'<div><b>{d.x(date_key)}</b><span>{DATE[d.lang]}</span></div>']
    if service:
        ticks = "".join(f'<span class="opt">{box(key == service)}{t[key]}</span>' for key in ("pm", "repair", "calib"))
        cells.append(f'<div class="svc"><b>{t["service"]}</b><span class="opts">{ticks}</span></div>')
        cls = ""
    else:
        cells.append(f'<div><b>{t["device_kind"]}</b><span class="dev">{d.device()}</span></div>')
        cells.append(f'<div><b>{t["brand"]}</b><span>{JOBS[d.pump]["brand"]}</span></div>')
        cls = " m4"
    return f'<div class="meta{cls}">{"".join(cells)}</div>'


def who(d, job, device_key="device"):
    t = d.t
    customer = [(t["hospital"], pick(CUSTOMER["hospital"], d.lang)), (t["dept"], pick(job["dept"], d.lang)),
                (t["province"], pick(CUSTOMER["province"], d.lang)),
                (t["contact"], f'{pick(CUSTOMER["contact"], d.lang)} · {CUSTOMER["tel"]}')]
    device = [(t["brand"], job["brand"]), (t["serial"], job["serial"]), (t["asset"], job["asset"]),
              (t["ivset" if d.pump == "infusion" else "syr"], pick(job["consumable"], d.lang))]
    head = lambda key, en: f'<h3><span>{t[key]}</span>' + (f'<span class="en">{X[en]}</span>' if d.lang == "th" else "") + "</h3>"
    return (f'<div class="two who"><div>{head("customer", "customer_en")}{kv(customer)}</div>'
            f'<div>{head(device_key, "device_en")}{kv(device)}</div></div>')


def checklist(d, items, head=True):
    t = d.t
    hd = (f'<div class="hd"><span>{t["item"]}</span><span class="cols"><i>{t["ok"]}</i><i>{t["fail"]}</i>'
          f'<i>{t["na"]}</i></span></div>')
    rows = []
    for item in items:
        name = pick(item[:2], d.lang)
        detail = pick(item[2:4], d.lang) if len(item) > 2 and item[2] else ""
        small = f'<small>{detail}</small>' if detail else ""
        rows.append(f'<div class="it"><span class="nm">{name}{small}</span><span class="cols">{box(True)}{box()}{box()}</span></div>')
    return f'<div class="chk c2{"" if head else " nohd"}">{hd * 2 if head else ""}{"".join(rows)}</div>'


def compact_checks(d, items, legend=False):
    """ตารางติ๊กแบบกระชับ 4 คอลัมน์ (ผ่าน = ช่องติ๊ก) — คำอธิบายสัญลักษณ์บรรทัดเดียวในหัวข้อแรก"""
    cells = "".join(f'<span class="ci">{box(True)}<span>{pick(item[:2], d.lang)}</span></span>' for item in items)
    lg = f'<p class="clg">{d.x("chk_legend")}</p>' if legend else ""
    return f'{lg}<div class="cchk">{cells}</div>'


def remarks_box(d):
    return '<div class="rmk"><i></i><i></i></div>'


def mini_gauge(d, err, u, tol, w=120, h=22):
    """มาตรวัดเล็กในตาราง: แถบเกณฑ์ · ขีด 0 · แถบ ± U · จุดที่ค่าคลาดเคลื่อน"""
    limit = tol * 1.6
    sx = lambda v: 4 + (w - 8) * (max(-limit, min(limit, v)) + limit) / (2 * limit)
    acc, tint = d.c["acc"], d.c["tint"]
    out = [_line(4, h / 2, w - 4, h / 2, AXIS, 0.8),
           f'<rect x="{sx(-tol):.1f}" y="{h / 2 - 5:.1f}" width="{sx(tol) - sx(-tol):.1f}" height="10" fill="{tint}" stroke="{MUTE}" stroke-width="0.6"/>',
           _line(sx(0), h / 2 - 7, sx(0), h / 2 + 7, INK, 0.8),
           f'<rect x="{sx(err - u):.1f}" y="{h / 2 - 2:.1f}" width="{max(2.0, sx(err + u) - sx(err - u)):.1f}" height="4" fill="{acc}" fill-opacity="0.45"/>',
           f'<circle cx="{sx(err):.1f}" cy="{h / 2:.1f}" r="3.6" fill="{acc}" stroke="#fff" stroke-width="1"/>']
    return _svg(w, h, "".join(out))


def flow_strip(d, job, extra):
    """แถบผลอัตราการไหลหน้า 1 ของ Inspection: ค่าที่ตั้ง · ค่าที่วัดได้ · คลาดเคลื่อน · ±U · มาตรวัด"""
    cells = [(d.x("set"), f'{job["rate"]:g}', "ml/h"), (d.x("meas"), f'{job["measured"]:.2f}', "ml/h"),
             (d.x("err"), num(job["error"], 1, True), "%"), (d.x("unc"), f'±{extra["u"]:g}', "%")]
    figs = "".join(f'<div class="fs"><b>{a}</b><span>{b}<i>{c}</i></span></div>' for a, b, c in cells)
    return (f'<div class="flow"><div class="fl"><b>{d.x("flow_strip")}</b><em>{d.x("details_p2")}</em></div>'
            f'<div class="figs4">{figs}</div><div class="fg">{gauge(d, job["error"], extra["u"], job["tol"], 250)}</div></div>')


def safety_row(d, job):
    return (f'<div class="safe2"><div><b>{d.x("supply")}</b><span>{job["supply"]} V</span></div>'
            f'<div><b>{d.x("leak")}</b><span>{job["leak"]} µA</span><em>{d.x("leak_lim", v=LEAK_LIMIT)}</em></div>'
            f'<div class="sv">{box(True)}<span class="pass">{d.t["ok"]}</span></div></div>')


def parts_block(d, job):
    items = job["parts"]
    claims = sum(1 for _, claim in items if claim)
    rows = "".join(f'<li><span>{pick(name, d.lang)}</span><i class="{"cl" if claim else "nw"}">{d.x("claim" if claim else "new")}</i></li>'
                   for name, claim in items)
    received = " · ".join(pick(item, d.lang) for item in job["received"])
    return (f'<ol class="parts2">{rows}</ol><div class="pfoot"><span><b>{d.x("received")}</b>{received}</span>'
            f'<span>{d.x("parts_n", n=len(items), c=claims)}</span></div>')


def verdict(d, statement, ticks=True):
    fin = (f'<span class="fin2"><span class="opt">{box(True)}{d.x("fin1")}</span><span class="opt">{box(True)}{d.x("fin2")}</span></span>'
           if ticks else "")
    return (f'<div class="verdict"><div class="vt"><b>{d.t["result" if ticks else "result_cal"]}</b><p>{statement}</p>{fin}</div>'
            f'<div class="vr"><span class="vl">{d.x("overall")}</span><span class="vv">{d.t["ok"]}</span></div></div>')


def signs(d, roles):
    """แผงลงนามแบบมาตรฐาน สำหรับลายเซ็น + ชื่ออิเล็กทรอนิกส์ (ไม่มีวันที่ — ผู้ใช้ขอ)

    กรอบบน = บทบาท + ตำแหน่ง และพื้นที่วางภาพลายเซ็น · เส้นล่างของกรอบคือเส้นลงนาม
    ใต้เส้น = ชื่อ-นามสกุลกึ่งกลาง — ตัวส่งออกจริงใส่ภาพลายเซ็นลง .spad และชื่อลง .sname
    """
    t = d.t
    cells = []
    for role, pos in roles:
        cells.append(f'<div class="sg3"><div class="sbox"><div class="shd"><span class="srole">{t[role]}</span><span class="sen">{t[pos]}</span></div>'
                     f'<div class="spad"><span>{d.x("esign")}</span></div></div>'
                     f'<div class="sname">{d.x("name")}</div></div>')
    return f'<div class="signs3 n{len(roles)}">{"".join(cells)}</div>'


def env_strip(d, with_water=True):
    t = d.t
    cells = [(t["liquid"], t["water"]), (t["water_t"], ENV["water_t"]), (t["air_t"], ENV["air_t"]), (t["rh"], ENV["rh"]),
             (t["pressure"], ENV["pressure"])]
    return '<div class="env">' + "".join(f'<div><b>{a}</b><span>{b}</span></div>' for a, b in cells) + "</div>"


def rows_html(rows, cls=""):
    return f'<div class="rows {cls}">' + "".join(f'<div class="row"><span>{a}</span><span>{b}</span></div>' for a, b in rows) + "</div>"


def detail_rows(d, method, n, unit, unit_sd, minutes, meas, sd2, err=None, u=None):
    """รายละเอียดของ 1 rate — เวลาต่อรอบ / ปริมาตรต่อรอบ มี ± และมีเวลารวม / ปริมาตรรวม"""
    cyc = method == "cycle"
    vol = meas * unit / 3600.0
    vol_sd = vol * sd2 / 200.0                      # ±2SD % -> SD ของปริมาตรต่อช่วง
    rows = []
    if err is not None:
        rows.append((d.x("err_u"), f'<b class="ev">{num(err, 1, True)}</b> ± {u:g} %'))
    rows += [(d.x("meas"), f"{meas:.2f} ml/h"), (d.x("n_cyc" if cyc else "n_tim"), str(n)),
             (d.x("t_cyc" if cyc else "t_tim"), f"{unit:.1f} ± {unit_sd:.1f} s"), (d.x("t_all"), f'{minutes:.1f} {d.x("minute")}'),
             (d.x("v_cyc" if cyc else "v_tim"), f"{vol:.{4 if vol < 0.1 else 3}f} ± {vol_sd:.{4 if vol < 0.1 else 3}f} ml"), (d.x("v_all"), f"{meas * minutes / 60:.2f} ml"),
             (d.x("spread"), f"{sd2:g} %")]
    return rows


def volume_strip(d):
    t = d.t
    cells = [(f'{t["density"]} · {ENV["water_t"]}', ENV["density"]), (t["per_gram"], ENV["per_gram"]), (t["evap"], "0.012 g/h")]
    return ('<div class="env v3">' + "".join(f'<div><b>{a}</b><span>{b}</span></div>' for a, b in cells)
            + f'</div><p class="note">{t["volume_note"]}</p>')


def occlusion_table(d, job):
    t = d.t
    a, b, c = job["occl"]
    low, high = job["occl_limit"]
    return (f'<table class="tb"><thead><tr><th class="l">{t["occl_row"]}</th><th>{d.x("occl_run")} 1</th><th>{d.x("occl_run")} 2</th>'
            f'<th>{d.x("occl_run")} 3</th><th>{t["mean"]}</th><th>{t["occl_limit"]}</th><th>{t["verdict"]}</th></tr></thead>'
            f'<tbody><tr><td class="l">{t["occl_level"]} {job["occl_level"]} · kPa</td><td>{a}</td><td>{b}</td><td>{c}</td>'
            f'<td><b>{(a + b + c) / 3:.0f}</b></td><td>{low} – {high}</td><td class="pass">{t["ok"]}</td></tr></tbody></table>')


def page(d, body, cls):
    return f'<section class="page a2 {d.pump} {cls}">{body}</section>'


# ------------------------------------------------------------------ หน้าเอกสาร
def inspection_page(lang, pump, page_no, pages, cal=False):
    d = D(lang, pump)
    t, job = d.t, JOBS[pump]
    perf = [list(item) for item in CHECKS[pump]["performance"] if item[1] != "Flow rate"]
    short = {"Air in line": ("เตือนได้", "alarms"), "Battery": ("120 นาที ที่ 25 ml/h", "120 min at 25 ml/h"),
             "Syringe size detection": ("ถูกต้อง", "correct"), "Nearly empty detection": ("เตือนได้", "alarms"),
             "Occlusion detection": X["occl_cal"] if cal else X["occl_ok"]}
    for item in perf:
        if item[1] in short:
            item[2:4] = list(short[item[1]])
    if cal:
        perf.append(["อัตราการไหล", "Flow rate", *X["flow_cal"]])
    perf_body = checklist(d, perf, head=False) + ("" if cal else flow_strip(d, job, INSP[pump]))
    compact = OPT.get("compact_checks")
    visual = compact_checks(d, CHECKS[pump]["visual"]) if compact else checklist(d, CHECKS[pump]["visual"])
    function = compact_checks(d, CHECKS[pump]["function"]) if compact else checklist(d, CHECKS[pump]["function"], head=False)
    result = verdict(d, t["insp_statement"])
    body = [header(d, "cal_kind" if cal else "insp_kind", "insp_title", page_no, pages),
            meta(d, job["job"], "date_insp", None if cal else "pm")]
    if OPT.get("summary_top"):
        body.append(result)
    body += [who(d, job),
             sec(d, 1, t["visual"], "visual", visual),
             sec(d, 2, t["function"], "function", function),
             sec(d, 3, t["performance"], "performance", perf_body),
             sec(d, 4, t["safety"], "safety", safety_row(d, job)),
             sec(d, 5, t["parts"], "parts", parts_block(d, job))]
    if OPT.get("remarks"):
        body.append(sec(d, 6, d.x("remarks"), "remarks", remarks_box(d)))
    if not OPT.get("summary_top"):
        body.append(result)
    body += [signs(d, [("inspected_by", "engineer"), ("received_by", "hospital_side")]),
             footer(d, job["job"], page_no, pages)]
    return page(d, "".join(body), "insp")


def measurement_page(lang, pump, page_no, pages):
    """หน้า 2 ของ Inspection: ผลวัด rate เดียว ครั้งเดียว — ไม่มีเครื่องชั่งมาตรฐาน ไม่มีการอุดตัน (ผู้ใช้ขอ)"""
    d = D(lang, pump)
    t, job, extra = d.t, JOBS[pump], INSP[pump]
    bw = 698
    values = series(job["measured"], job["spread"], job["count"], 4711 if pump == "infusion" else 1213)
    cells = [(d.x("set"), f'{job["rate"]:g}', "ml/h"), (d.x("meas"), f'{job["measured"]:.2f}', "ml/h"),
             (d.x("err"), num(job["error"], 1, True), "%"), (d.x("unc"), f'±{extra["u"]:g}', "%"),
             (d.x("tol"), f'±{job["tol"]:g}', "%")]
    figs = "".join(f'<div class="fig f{i}"><b>{a}</b><span>{b}</span><i>{c}</i></div>' for i, (a, b, c) in enumerate(cells))
    hero = f'<div class="figs six">{figs}<div class="fig fv"><b>{d.x("result")}</b><span class="vv">{t["ok"]}</span></div></div>'
    hero += f'<div class="gg">{gauge(d, job["error"], extra["u"], job["tol"], bw)}</div>'
    chart = flow_chart(d, values, job["unit_time"], job["rate"], job["tol"], bw, 290)
    ident = kv([(t["job"], f'<span class="jobno">{job["job"]}</span>'),
                (t["hospital"], f'{pick(CUSTOMER["hospital"], lang)} · {pick(job["dept"], lang)}'),
                (t["brand"], job["brand"]), (t["serial"], job["serial"])], "ident")
    method = extra["method"]
    rows = detail_rows(d, method, job["count"], job["unit_time"], extra["unit_sd"], job["minutes"], job["measured"], job["spread"])
    how = (f'<div class="two"><div><p>{t["how_text"]}</p><p class="mtag"><b>{d.x("split")}</b>{d.method(method)}</p>'
           f'<p class="note">{X["split_note"][d.i]}</p></div>{rows_html(rows)}</div>')
    body = [header(d, "insp_kind", "meas_title", page_no, pages), ident,
            sec(d, 1, t["meas_title"], "flow", hero, "hero"),
            sec(d, 2, t["chart_flow" if method == "cycle" else "chart_flow_time"], "chart", chart, "plot"),
            sec(d, 3, t["how_sec"], "method", how),
            sec(d, 4, t["conditions"], "cond", env_strip(d)),
            f'<p class="fine">{t["validity"]} {t["method_ref"]}</p>',
            footer(d, job["job"], page_no, pages)]
    return page(d, "".join(body), "meas")


def calibration_summary(lang, page_no, pages):
    d = D(lang, "infusion")
    t, job = d.t, JOBS["infusion"]
    if OPT.get("inline_gauge"):
        rows = "".join(
            f'<tr><td class="l"><b>{r["set"]:g}</b></td><td class="l mt">{d.method(r["method"], tech=False)}</td><td>{r["n"]}</td>'
            f'<td><b>{r["meas"]:.2f}</b></td><td><b class="ev">{num(r["err"], 1, True)}</b></td><td>±{r["u"]:g}</td>'
            f'<td class="gcell">{mini_gauge(d, r["err"], r["u"], job["tol"])}</td><td>±{job["tol"]:g}</td>'
            f'<td class="pass">{t["ok"]}</td></tr>' for r in CAL)
        head = (f'<tr><th class="l">{t["set_rate"]}<i>ml/h</i></th><th class="l">{d.x("split")}</th><th>n</th>'
                f'<th>{t["measured"]}<i>ml/h</i></th><th>{t["error"]}<i>%</i></th><th>U k=2<i>%</i></th>'
                f'<th class="gcell">{d.x("in_tol")}<i>± U</i></th><th>{t["tolerance"]}<i>%</i></th><th>{t["verdict"]}</th></tr>')
    else:
        head = ""
    rows = rows if OPT.get("inline_gauge") else "".join(
        f'<tr><td class="l"><b>{r["set"]:g}</b></td><td class="l mt">{d.method(r["method"], tech=False)}</td><td>{r["minutes"]:.1f}</td>'
        f'<td>{r["n"]}</td><td><b>{r["meas"]:.2f}</b></td><td><b class="ev">{num(r["err"], 1, True)}</b></td><td>±{r["u"]:g}</td>'
        f'<td>{r["sd2"]:g}</td><td>±{job["tol"]:g}</td><td class="pass">{t["ok"]}</td></tr>' for r in CAL)
    head = head or (f'<tr><th class="l">{t["set_rate"]}<i>ml/h</i></th><th class="l">{d.x("split")}</th>'
                    f'<th>{t["duration"]}<i>{t["minute"]}</i></th><th>n</th><th>{t["measured"]}<i>ml/h</i></th><th>{t["error"]}<i>%</i></th>'
                    f'<th>U k=2<i>%</i></th><th>±2SD<i>%</i></th><th>{t["tolerance"]}<i>%</i></th><th>{t["verdict"]}</th></tr>')
    table = (f'<table class="tb res"><thead>{head}</thead>'
             f'<tbody>{rows}</tbody></table>'
             f'<p class="note">{t["err_note"]} · {t["unc_note"]}</p><p class="note">{X["split_note"][d.i]}</p>')
    balance = kv([(t["balance"], f'{BALANCE["model"]} · {BALANCE["serial"]}'),
                  (t["capacity"], f'{BALANCE["capacity"]} · {t["readability"]} {BALANCE["readability"]}')], "tight")
    tools = (f'<div class="two"><div><h3>{t["standard"]}</h3>{balance}<p class="note">{t["balance_check"]}</p></div>'
             f'<div><h3>{t["how"]}</h3><p class="note" style="margin-top: 0">{t["how_text"]} {t["trace"]}</p></div></div>'
             + env_strip(d))
    result = verdict(d, t["cal_statement"], ticks=False)
    body = [header(d, "cal_kind", "cal_title", page_no, pages), meta(d, job["job"], "date_cal")]
    if OPT.get("summary_top"):
        body.append(result)
    body += [who(d, job, "device_cal"),
            sec(d, 1, t["results"], "results", table, "results"),
            sec(d, 2, t["occl"], "occl", occlusion_table(d, job)),
            sec(d, 3, t["tools"], "tools", tools),
            sec(d, 4, t["volume"], "volume", volume_strip(d))]
    if not OPT.get("summary_top"):
        body.append(result)
    body += [signs(d, [("calibrated_by", "engineer"), ("reviewed_by", "supervisor"), ("approved_by", "manager")]),
            footer(d, job["job"], page_no, pages)]
    return page(d, "".join(body), "cal")


def calibration_technical(lang, page_no, pages):
    d = D(lang, "infusion")
    t, job = d.t, JOBS["infusion"]
    tol = job["tol"]
    ident = kv([(t["job"], f'<span class="jobno">{job["job"]}</span>'),
                (t["hospital"], f'{pick(CUSTOMER["hospital"], lang)} · {pick(job["dept"], lang)}'),
                (t["brand"], job["brand"]), (t["serial"], job["serial"])], "ident")
    chart, slope = error_chart(d, CAL, tol, 470, 176 if OPT.get("rate_error") else 196)   # rate_error: บล็อกราย rate สูงขึ้น
    worst = max(CAL, key=lambda r: abs(r["err"]))
    margin = min(tol - abs(r["err"]) - r["u"] for r in CAL)
    legend = (f'<div class="lg"><span><i class="pt"></i>{d.x("legend_pt")}</span><span><i class="fit"></i>{d.x("legend_fit")}</span>'
              f'<span><i class="tolb"></i>{d.x("legend_tol", t=tol)}</span></div>')
    side = rows_html([(d.x("trend"), d.x("trend_v", s=num(slope, 2, True))),
                      (d.x("worst"), d.x("worst_v", e=num(worst["err"], 1, True), r=worst["set"])),
                      (d.x("margin"), d.x("margin_v", m=f"{margin:.1f}"))]) + legend
    blocks = []
    for r in CAL:
        values = series(r["meas"], r["sd2"], r["n"], r["seed"])
        info = (f'<div class="rt"><b>{r["set"]:g} ml/h</b><span class="pass">{t["ok"]}</span></div>'
                f'<div class="mt">{d.method(r["method"])}</div>')
        if OPT.get("rate_error"):
            # ค่าคลาดเคลื่อน ± U เด่นใต้ชื่อ rate: เส้นสีซ้าย ตัวเลขใหญ่สีตามชนิดเครื่อง ± U สีเทา
            if OPT.get("lab"):
                info += (f'<div class="rerr lab"><em>{d.x("err_u")}</em><span><b>{num(r["err"], 1, True)}</b>'
                         f'<i>± {r["u"]:g}</i><u>%</u></span></div>')
            else:
                info += (f'<div class="rerr"><em>{d.x("err_u")}</em><span><b>{num(r["err"], 1, True)} %</b>'
                         f'<i>± {r["u"]:g} %</i></span></div>')
        info += rows_html(detail_rows(d, r["method"], r["n"], r["unit"], r["unit_sd"], r["minutes"], r["meas"], r["sd2"]), "tight")
        if OPT.get("lab"):
            graph = (f'<div class="gv">{flow_chart(d, values, r["unit"], r["set"], tol, 372, 196)}'
                     f'{vgauge(d, r["err"], r["u"], tol, 196)}</div>')
        else:
            graph = flow_chart(d, values, r["unit"], r["set"], tol, 456, 150) + gauge(d, r["err"], r["u"], tol, 456)
        blocks.append(f'<div class="rb"><div>{info}</div><div>{graph}</div></div>')
    body = [header(d, "cal_kind", "tech_title", page_no, pages),
            sec(d, 1, t["chart_err"], "err", f'<div class="errw">{chart}<div class="side">{side}</div></div>', "plot"),
            sec(d, 2, "ผลรายค่าที่ตั้ง" if lang == "th" else "Results per set rate", "rate", "".join(blocks), "plot"),
            footer(d, job["job"], page_no, pages)]
    return page(d, "".join(body), "tech")


def document(lang, V=None):
    OPT.clear()
    OPT.update((V or {}).get("opts", {}))
    return [
        ("Inspection-Infusion-p1", inspection_page(lang, "infusion", 1, 2)),
        ("Inspection-Infusion-p2", measurement_page(lang, "infusion", 2, 2)),
        ("Inspection-Syringe-p1", inspection_page(lang, "syringe", 1, 2)),
        ("Inspection-Syringe-p2", measurement_page(lang, "syringe", 2, 2)),
        ("Calibration-p1-inspection", inspection_page(lang, "infusion", 1, 3, cal=True)),
        ("Calibration-p2-summary", calibration_summary(lang, 2, 3)),
        ("Calibration-p3-technical", calibration_technical(lang, 3, 3)),
    ]


CSS = styles.BASE + styles.A + """
.page.infusion { --acc: #0B6FA4; --bar: #38BDF8; --tint: #E0F2FE }
.page.syringe { --acc: #B0306A; --bar: #F472B6; --tint: #FCE7F3 }
.page.a2::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 6px; background: var(--bar) }
.page.a2 { --mt: 30px }
.a2 .sub { font-size: 15px; font-weight: 700; letter-spacing: .3px }
.a2 .jobno, .a2 .dev, .a2 .fj { color: var(--acc); font-weight: 700 }
.a2 .sec h2 .en, .a2 h3 .en { display: inline; margin-left: auto; font-size: 12px; font-weight: 600; letter-spacing: 1px; color: #5A626C }
.a2 h3 { display: flex; align-items: baseline; font-size: 13px; color: var(--ink); letter-spacing: 0; border-bottom: 1px solid var(--ink);
         padding-bottom: 2px; margin-bottom: 3px }
.a2 .who h3 span:first-child { font-weight: 700 }
.a2 .pass, .a2 .vv { color: #166534 }
.a2 .ev { color: var(--acc) }
.a2 .meta.m4 { grid-template-columns: 1fr 1fr 1.2fr 1.2fr }
.a2 .meta > div + div { padding-left: 12px; border-left: 1px solid var(--hair) }
.a2 .chk .it { min-height: 21px }
.a2 .nm small { display: inline; margin-left: 8px; font-size: 12px }
/* แถบผลอัตราการไหล (Inspection หน้า 1) */
.flow { display: grid; grid-template-columns: 1fr 250px; align-items: end; column-gap: 12px; margin-top: 5px;
        padding: 4px 0 2px 12px; border-left: 3px solid var(--acc); background: #F6F8FA }
.flow .fl { grid-column: 1 / -1; display: flex; gap: 10px; align-items: baseline }
.flow .fl b { font-size: 12px; color: var(--acc); font-weight: 700 } .flow .fl em { font-size: 12px; color: var(--mute) }
.figs4 { display: grid; grid-template-columns: repeat(4, auto); column-gap: 22px; justify-content: start; padding-bottom: 4px }
.fs b { display: block; font-size: 12px; font-weight: 400; color: var(--mute); line-height: 1.3 }
.fs span { font-size: 19px; font-weight: 700; line-height: 1.25 } .fs i { font-size: 12px; font-weight: 400; color: var(--mute); margin-left: 3px }
.fs:nth-child(3) span { color: var(--acc) }
/* ความปลอดภัยทางไฟฟ้า แถวเดียว */
.safe2 { display: grid; grid-template-columns: 1fr 1.6fr auto; align-items: baseline; padding-top: 3px; column-gap: 18px }
.safe2 b { font-size: 12px; font-weight: 400; color: var(--mute); margin-right: 8px } .safe2 span { font-weight: 700 }
.safe2 em { font-size: 12px; color: var(--mute); margin-left: 10px }
.safe2 .sv { display: flex; align-items: center; gap: 6px }
/* อะไหล่ */
ol.parts2 { list-style: none; display: grid; grid-template-columns: repeat(3, 1fr); column-gap: 22px; counter-reset: p }
ol.parts2 li { counter-increment: p; display: flex; justify-content: space-between; gap: 6px; border-bottom: 1px solid var(--hair); padding: 2px 0 }
ol.parts2 li span::before { content: counter(p) "."; color: var(--mute); display: inline-block; min-width: 20px }
ol.parts2 li i { font-size: 12px; font-weight: 600; white-space: nowrap }
ol.parts2 li i.cl { color: #166534 } ol.parts2 li i.nw { color: var(--mute) }
.pfoot { display: flex; justify-content: space-between; font-size: 12px; color: var(--mute); margin-top: 3px }
.pfoot b { font-weight: 600; margin-right: 8px } .pfoot span:first-child { color: var(--ink) } .pfoot span:first-child b { color: var(--mute) }
/* กล่องสรุปผล + ตรวจขั้นสุดท้าย */
.a2 .verdict { margin-top: 10px }
.a2 .vt b { display: block; font-size: 13px; font-weight: 700; color: var(--ink) }
.fin2 { display: flex; gap: 20px; margin-top: 4px } .fin2 .opt { margin: 0 }
/* ลายเซ็น: ลายมือชื่อ + ชื่อ-นามสกุล ไม่มีวันที่ */
.signs3 { display: grid; column-gap: 24px; margin-top: 10px } .signs3.n2 { grid-template-columns: 1fr 1fr }
.signs3.n3 { grid-template-columns: repeat(3, 1fr) }
.sbox { border: 1px solid var(--hair); border-bottom: 1.4px solid var(--ink); background: #FAFBFC }
.shd { display: flex; justify-content: space-between; align-items: baseline; padding: 3px 10px 0 }
.srole { font-size: 13px; font-weight: 700 } .sen { font-size: 12px; color: var(--mute) }
.spad { height: 34px; display: flex; align-items: center; justify-content: center }
.spad span { font-size: 12px; color: #B4BAC1; letter-spacing: .3px }
.sname { text-align: center; font-weight: 600; color: var(--mute); padding-top: 3px; line-height: 1.3 }
.spos { text-align: center; font-size: 12px; color: var(--mute); line-height: 1.3 }
.signs2 { display: grid; column-gap: 30px; margin-top: 10px } .signs2.n2 { grid-template-columns: 1fr 1fr } .signs2.n3 { grid-template-columns: repeat(3, 1fr) }
.sg2 .role { font-weight: 700 } .sg2 .role span { font-weight: 400; font-size: 12px; color: var(--mute); margin-left: 8px }
.sg2 .line { display: grid; grid-template-columns: auto 1fr; align-items: end; column-gap: 8px; height: 22px }
.sg2 .line.tall { height: 28px } .sg2 .line span { font-size: 12px; color: var(--mute); line-height: 1.2 }
.sg2 .line i { border-bottom: 1px solid var(--ink); height: 100% }
/* หน้า 2 */
.figs.six { grid-template-columns: repeat(5, 1fr) 1.1fr } .figs.six .fig:nth-child(3) span { color: var(--acc) }
.a2 .gg { margin-top: 2px }
.mtag { margin-top: 6px } .mtag b { display: block; font-size: 12px; font-weight: 400; color: var(--mute) } .mtag { font-weight: 700; color: var(--acc) }
.rows.tight .row { padding: 1px 0; font-size: 12px }
.rows .row { display: flex; justify-content: space-between; gap: 10px; border-bottom: 1px solid #E3E6EA; padding: 2px 0; font-size: 12.5px; line-height: 1.35 }
.rows .row span:first-child { color: var(--mute) } .rows .row span:last-child { font-weight: 600; text-align: right }
.env { display: grid; grid-template-columns: repeat(5, 1fr); margin-top: 4px } .env.v4 { grid-template-columns: repeat(4, 1fr) } .env.v3 { grid-template-columns: repeat(3, 1fr) }
.env > div { padding: 2px 10px } .env > div:first-child { padding-left: 0 } .env > div + div { border-left: 1px solid var(--hair) }
.env b { display: block; font-size: 12px; font-weight: 400; color: var(--mute) } .env span { font-weight: 600 }
/* Calibration */
.a2 .tb td.mt { font-size: 12px; color: var(--acc); font-weight: 600; white-space: nowrap }
.errw { display: grid; grid-template-columns: 470px 1fr; column-gap: 22px; align-items: start }
.side .rows { margin-top: 4px }
.lg { display: flex; flex-direction: column; gap: 3px; margin-top: 8px; font-size: 12px; color: var(--mute) }
.lg span { display: flex; align-items: center; gap: 8px }
.lg i { display: inline-block; flex: none } .lg .pt { width: 9px; height: 9px; border-radius: 50%; background: var(--acc) }
.lg .fit { width: 20px; border-top: 2.2px dashed #D9691A } .lg .tolb { width: 18px; height: 9px; background: var(--tint); border-top: 1px dashed var(--acc); border-bottom: 1px dashed var(--acc) }
.rb { display: grid; grid-template-columns: 220px 1fr; column-gap: 22px; padding: 6px 0 4px; border-bottom: 1px solid var(--hair) }
.rb:last-child { border-bottom: none }
.rb .rt { display: flex; justify-content: space-between; align-items: baseline } .rb .rt b { font-size: 18px; font-weight: 700 }
.rb .mt { font-size: 12px; color: var(--acc); font-weight: 600; margin-bottom: 2px }
.tech .sec, .cal .sec, .meas .sec { margin-top: 12px }
"""


# CSS ของตัวเลือก (เพิ่มต่อท้าย CSS หลักเฉพาะแบบที่เปิดตัวเลือกนั้น)
EXTRA_CSS = {
    "quiet": """
.a2 .sec h2 .en, .a2 h3 .en { display: none }
.a2 .sec h2 { text-transform: none; letter-spacing: 0; font-size: 14px }
.a2 .signs3 { margin-top: 7px }
.page.a2::before { height: 4px }
.a2 .flow { background: none; border: 1px solid var(--hair); border-left: 3px solid var(--acc) }
.a2 .ev, .a2 .fs:nth-child(3) span, .a2 .figs.six .fig:nth-child(3) span { color: var(--ink) }
.a2 .spad span { visibility: hidden }
.a2 .sbox { background: #fff }
""",
    "control": """
.a2 .pg { font-size: 12px; letter-spacing: .2px }
.a2 .foot span:nth-child(2) { color: var(--mute) }
""",
    "main": """
.a2 .sec h2 { text-transform: none; letter-spacing: 0; font-size: 14px }
.page.a2::before { height: 4px }
.a2 .flow { background: none; border: 1px solid var(--hair); border-left: 3px solid var(--acc) }
.a2 .spad span { visibility: hidden }
.a2 .sbox { background: #fff }
.a2 .signs3 { margin-top: 7px }
""",
    "rate_error": """
.rb .rerr { display: flex; justify-content: space-between; align-items: baseline; margin: 2px 0 4px; padding: 2px 0 2px 9px;
            border-left: 3px solid var(--acc) }
.rb .rerr em { font-size: 12px; color: var(--mute) }
.rb .rerr b { font-size: 20px; font-weight: 700; color: var(--acc); white-space: nowrap }
.rb .rerr i { font-size: 13px; font-weight: 600; color: var(--mute); margin-left: 6px; white-space: nowrap }
""",
    "lab": """
.gv { display: flex; justify-content: space-between; align-items: flex-start }
.rb .rerr.lab { border-left-width: 2px; padding-left: 8px; margin: 3px 0 5px }
.rb .rerr.lab b { font-size: 18px }
.rb .rerr.lab i { font-size: 15px; font-weight: 600; color: var(--ink); margin-left: 5px; font-style: normal }
.rb .rerr.lab u { text-decoration: none; font-size: 13px; color: var(--mute); margin-left: 4px }
""",
    "summary_top": """
.a2 .meta + .verdict { margin-top: 10px; margin-bottom: 2px }
""",
    "inline_gauge": """
.a2 .tb .gcell { text-align: center; padding-left: 4px; padding-right: 4px } .a2 .tb td.gcell svg { display: inline-block; vertical-align: middle }
""",
    "compact_checks": """
.cchk { display: grid; grid-template-columns: repeat(4, 1fr); column-gap: 20px }
.ci { display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--hair); padding: 2px 0; min-height: 22px }
.clg { font-size: 12px; color: var(--mute); margin: 0 0 2px }
""",
    "remarks": """
.rmk i { display: block; height: 21px; border-bottom: 1px solid var(--hair) }
""",
}


def css_for(V):
    opts = (V or {}).get("opts", {})
    return CSS + "".join(EXTRA_CSS[k] for k in opts if opts[k] and k in EXTRA_CSS)
