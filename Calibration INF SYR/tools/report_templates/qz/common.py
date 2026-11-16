"""ของใช้ร่วมของแบบ Q–Z: ข้อมูลสมมติชุดเดียว (ค่าในกราฟ = ค่าในตาราง), ตัวช่วยวาด SVG, ตัวห่อไฟล์ .dc.html
ข้อมูลทั้งหมดเป็นค่าสมมติ กำหนดได้ (seed คงที่) — สร้างใหม่กี่ครั้งก็ได้ค่าเดิม
"""
import math
from html import escape

MINUS = "−"
INK, GREY, MUTE, RULE, PAPER = "#161718", "#5C5F62", "#8A8D90", "#DCDCD8", "#F3F3F1"
# สีแยกชนิดเครื่อง: เส้น/พื้น และตัวหนังสือ
INF = dict(fill="#38BDF8", ink="#0B6FA4", tint="#E3F3FC", mid="#9BD6F5")
SYR = dict(fill="#F472B6", ink="#B3246F", tint="#FCE8F2", mid="#F2A9CF")


def f(x, d=1, sign=False):
    """ตัวเลขพร้อมเครื่องหมายลบแบบตัวพิมพ์ (−)"""
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    if float(s) == 0:          # ไม่แสดง −0.0
        s = s.replace("-", "+" if sign else "")
    return s.replace("-", MINUS)


def esc(s):
    return escape(str(s), quote=True)


class Rng:
    """สุ่มแบบกำหนดได้ (Park–Miller) — ค่าเดิมทุกครั้ง"""

    def __init__(self, seed):
        self.s = seed

    def u(self):
        self.s = (self.s * 16807) % 2147483647
        return self.s / 2147483647 - 0.5

    def g(self):
        # ผลรวม uniform 4 ตัว ปรับให้ความแปรปรวน = 1
        return (self.u() + self.u() + self.u() + self.u()) / math.sqrt(1 / 3)


def mean(v):
    return sum(v) / len(v)


def sd(v):
    m = mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def series(n, m, s, seed, ar=0.0):
    """ชุดค่าที่ค่าเฉลี่ยและ SD ตรงตามที่กำหนดเป๊ะ (ar = สหสัมพันธ์กับค่าก่อนหน้า)"""
    r, prev, raw = Rng(seed), 0.0, []
    for _ in range(n):
        prev = ar * prev + r.g()
        raw.append(prev)
    mm, ss = mean(raw), sd(raw)
    return [m + s * (x - mm) / ss for x in raw]


# ---------------------------------------------------------------- ข้อมูลสมมติ: Infusion (งาน MCI-0142)
INFUSION = dict(
    kind="Infusion", job="MCI-0142", cert="DM-C-2611-0042", insp="DM-I-2611-0104", date="13 Nov 2026",
    brand="Terumo", model="TE-171", serial="17110582", asset="ICU-IP-031", site="โรงพยาบาลตัวอย่าง",
    dept="ICU 2", province="[จังหวัด]", set_label="[Brand] [IV set model]", limit=5.0,
    water=23.4, rh=56, hpa=1008, operator="[Operator name]", approver="[Approver name]",
    rates=[
        # set, measured, U(k=2) %, รอบ, คาบ s, 2SD % ของ flow รายรอบ, ช่วงก่อนวัด
        dict(set=10.0, meas=9.87, U=0.9, n=12, period=72.2, sd2=3.1, pre="auto · 4:10"),
        dict(set=50.0, meas=50.42, U=0.6, n=58, period=15.2, sd2=2.4, pre="auto · 2:40"),
        dict(set=200.0, meas=196.10, U=0.7, n=231, period=3.9, sd2=7.8, pre="delay 60 s"),
    ],
)
# Inspection ของเครื่องเดียวกัน: ตรวจ flow 25 ml/h 5 นาที
INF_INSP = dict(set=25.0, meas=25.18, U=0.8, n=10, period=30.4, minutes=5)
# Quick Test (เครื่องอื่นในห้องฉุกเฉิน)
INF_QT = dict(job="MCI-0151", no="DM-Q-2611-0215", serial="17110609", dept="ER", date="13 Nov 2026 14:22",
              set=50.0, meas=49.61, n=12, period=15.2, minutes=3)

# ---------------------------------------------------------------- ข้อมูลสมมติ: Syringe (งาน MCS-0388)
SYRINGE = dict(
    kind="Syringe", job="MCS-0388", cert="DM-C-2611-0051", insp="DM-I-2611-0107", date="13 Nov 2026",
    brand="Terumo", model="TE-331", serial="33104417", asset="NICU-SP-007", site="โรงพยาบาลตัวอย่าง",
    dept="NICU", province="[จังหวัด]", set_label="Terumo 50 ml syringe", limit=3.0,
    water=23.1, rh=54, hpa=1009, operator="[Operator name]", approver="[Approver name]",
    rates=[
        # syringe จับตามเวลา: n = จำนวนช่วง, win = วินาทีต่อช่วง, start = เวลาเข้าเกณฑ์ (นาที)
        dict(set=1.0, meas=0.978, U=1.2, n=12, win=300, sd2=1.2, pre="auto · 14:00", start=14.0),
        dict(set=5.0, meas=4.910, U=0.7, n=20, win=60, sd2=2.2, pre="auto · 3:30", start=3.5),
        dict(set=25.0, meas=25.08, U=0.5, n=20, win=30, sd2=1.6, pre="auto · 1:00", start=1.0),
    ],
)
SYR_INSP = dict(set=5.0, meas=4.910, U=0.7, n=5, win=60, minutes=5)
SYR_QT = dict(job="MCS-0395", no="DM-Q-2611-0219", serial="33104420", dept="NICU", date="13 Nov 2026 15:05",
              set=5.0, meas=4.93, n=5, win=60, minutes=5)

BALANCE = "A&amp;D GF-300 S/N 14654769"


def err(r):
    """error % ของ rate"""
    return (r["meas"] - r["set"]) / r["set"] * 100


def cycle_flows(r, seed):
    """flow รายรอบ/รายช่วง (ml/h) ที่ค่าเฉลี่ย = ค่าในตาราง และ 2SD = ค่าในตาราง"""
    return series(r["n"], r["meas"], r["meas"] * r["sd2"] / 200, seed, ar=0.15)


# ---------------------------------------------------------------- ตัวช่วย SVG
class Ax:
    """แปลงค่าข้อมูล -> พิกัด px ในกรอบ (x0..x1, y0 บน..y1 ล่าง)"""

    def __init__(self, x0, x1, y0, y1, vx0, vx1, vy0, vy1, logx=False, logy=False):
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.vx0, self.vx1, self.vy0, self.vy1 = vx0, vx1, vy0, vy1
        self.logx, self.logy = logx, logy

    def sx(self, v):
        if self.logx:
            v, a, b = math.log10(v), math.log10(self.vx0), math.log10(self.vx1)
        else:
            a, b = self.vx0, self.vx1
        return self.x0 + (v - a) / (b - a) * (self.x1 - self.x0)

    def sy(self, v):
        if self.logy:
            v, a, b = math.log10(v), math.log10(self.vy0), math.log10(self.vy1)
        else:
            a, b = self.vy0, self.vy1
        return self.y1 - (v - a) / (b - a) * (self.y1 - self.y0)

    def pts(self, xs, ys):
        return " ".join(f"{self.sx(x):.1f},{self.sy(y):.1f}" for x, y in zip(xs, ys))


def T(x, y, s, size=12, anchor="start", fill=GREY, weight=None, extra=""):
    w = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}"{w}{extra}>'
            f"{s}</text>")


def L(x1, y1, x2, y2, stroke=INK, w=1, dash=None, extra=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
            f'stroke-width="{w}"{d}{extra}></line>')


def R(x, y, w, h, fill="none", stroke=None, sw=1, extra=""):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{s}{extra}></rect>'


def PL(points, stroke=INK, w=1.5, fill="none", dash=None, extra=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<polyline points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" '
            f'stroke-linejoin="round"{d}{extra}></polyline>')


def PG(points, fill, stroke=None, extra=""):
    s = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
    return f'<polygon points="{points}" fill="{fill}"{s}{extra}></polygon>'


def C(x, y, r, fill=INK, stroke=None, sw=1):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"{s}></circle>'


def svg(w, h, label, inner, style="display: block"):
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}" '
            f'style="{style}">{"".join(inner)}</svg>')


# ---------------------------------------------------------------- ตัวห่อไฟล์ .dc.html
def fonts(*families):
    q = "&amp;".join(f"family={fam}" for fam in families)
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            f'<link href="https://fonts.googleapis.com/css2?{q}&amp;display=swap" rel="stylesheet">')


def dc(title, w, h, font_links, css, root_style, body):
    """ไฟล์ artboard ของ canvas (โครงเดียวกับแบบ A–P)"""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{esc(title)}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
{font_links}
<style>
body{{margin:0;background:#ffffff}}
{css.strip()}
</style>
</helmet>
<div style="width: {w}px; height: {h}px; box-sizing: border-box; background: #ffffff; {root_style}">
{body.strip()}
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":{w},"height":{h}}}}}'>
class Component extends DCLogic {{
  renderVals() {{
    return {{}};
  }}
}}
</script>
</body>
</html>
"""
