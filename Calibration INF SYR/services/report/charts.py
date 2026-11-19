"""กราฟ SVG ของใบรายงาน (แบบ Main Fable-1) — ยกมาจาก tools/report_templates/fable/a.py แล้วปรับรับข้อมูลจริง

ต่างจากแบบตัวอย่าง:
  - flow_chart ใช้เวลาจริงของแต่ละช่วงวัด (นาทีเริ่ม-จบ) · แกน Y ±25 % ขยายเองเมื่อค่าเกิน (สูงสุด ±100 %)
    · ขีดแกนเวลาเลือกเองตามความยาว (รันหลายชั่วโมงได้)
  - U ไม่มีได้ (None = ยังไม่ได้ประเมิน) — ไม่วาดแถบ ± U
  - error_chart แกนอัตรา log ตามช่วงของ rate ที่มีจริง (0.1–1200 ml/h) · rate เดียวไม่มีเส้นแนวโน้ม · แกน Y ขยายตามค่า
ขนาดตัวอักษรในกราฟ 12 px เสมอ (ตัวตรวจล้นหน้าห้ามเล็กกว่า 12 px)
"""
from __future__ import annotations

import math

GREEN, RED, ORANGE, INK, MUTE, GRID, AXIS = "#166534", "#B42318", "#D9691A", "#141414", "#5C5F66", "#E6E9ED", "#9AA2AC"
MOVING = "#6D28D9"          # เส้นค่าเฉลี่ยสะสม (ม่วง — ต่างจากส้มของค่าเฉลี่ยและสีชนิดเครื่อง)
FONT = "'IBM Plex Sans Thai', 'Leelawadee UI', sans-serif"
LINE = INK              # เส้น flow รายช่วง: สีดำชัดกว่า — พื้นแถบเกณฑ์ยังเป็นสีตามชนิดเครื่อง (ผู้ใช้ 2026-11-19)
ERR_DP = 2              # ทศนิยมของ Error% ทุกจุดในใบ (ผู้ใช้ 2026-11-18)
MINUS = "−"
PLOT_LEFT, PLOT_RIGHT = 50, 10      # ขอบพื้นที่กราฟ — มาตรวัดใต้กราฟใช้ขอบเดียวกัน

PUMP = {"infusion": dict(acc="#0B6FA4", bar="#38BDF8", tint="#E0F2FE"),
        "syringe": dict(acc="#B0306A", bar="#F472B6", tint="#FCE7F3")}


def num(value: float, digits: int = 1, sign: bool = False) -> str:
    """ตัวเลขในเอกสาร: ลบใช้ − (ไม่ใช่ -) · sign=True ใส่ + ให้ค่าบวก"""
    text = f"{abs(value):.{digits}f}"
    if value < 0 and float(text) != 0:
        return MINUS + text
    return ("+" + text) if sign and float(text) != 0 else text


def u_text(u: float | None) -> str:
    return "—" if u is None else f"{u:g}"


def _svg(w, h, body):
    return (f'<svg class="chart" xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{FONT}" font-size="12">{body}</svg>')


def _line(x1, y1, x2, y2, color, width=1.0, dash=""):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}"{extra}/>'


def _text(x, y, s, anchor="start", fill=MUTE, weight=""):
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" fill="{fill}"{w}>{s}</text>'


TIME_STEPS = (0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 240, 480, 960)
MIN_LABEL_GAP = 34          # px ระหว่างป้ายนาที (ป้าย 3 หลัก + ช่องว่าง) — แคบกว่านี้ป้ายชนกัน


def _time_steps(minutes: float, width: float) -> tuple[float, float]:
    """(ระยะเส้นตาราง, ระยะป้าย) ของแกนนาที — ป้ายทุก 1 นาทีถ้าที่พอ (ผู้ใช้ขอ 2026-11-18) ไม่งั้นขยายเป็น 2/5/10/… ตามความกว้างจริง"""
    minutes = max(minutes, 1e-6)
    label = next((step for step in TIME_STEPS if width * step / minutes >= MIN_LABEL_GAP), TIME_STEPS[-1])
    if label < 1 and minutes >= 2:          # รันยาวกว่า 2 นาที ไม่ใช้ป้ายเศษนาที
        label = 1
    grid = label / 2 if label >= 10 else label
    return grid, label


def _flow_span(values: list[float], target: float) -> float:
    """ครึ่งช่วงแกน Y เป็น % ของค่าที่ตั้ง: ปกติ 25 · ค่าเกินขยายทีละ 5 % สูงสุด 100"""
    if not values or target <= 0:
        return 25.0
    worst = max(abs(v - target) / target * 100.0 for v in values)
    return 25.0 if worst <= 24 else min(100.0, 5 * math.ceil((worst + 3) / 5))


def flow_chart(w_, pump, series, target, mean, tol, w, h, style="step", show_mean=True, moving=False):
    """flow ของแต่ละช่วงวัด (ขั้นบันได) · แกน Y ตรึงค่าที่ตั้ง ±25 % · แกน X นาที · เส้นตารางจาง · เส้นค่าเฉลี่ยสีส้ม

    series = [(นาทีเริ่ม, นาทีจบ, flow)] · mean = ค่าที่วัดได้ของผล (เส้นส้ม)
    style = step (ขั้นบันได) | points (จุดต่อเส้น) · show_mean = เส้นค่าเฉลี่ยแนวนอน · moving = เส้นค่าเฉลี่ยสะสม
    (ค่าเริ่มต้นในหน้าตั้งค่า -> ใบรายงาน · เปลี่ยนได้ในหน้าต่างตัวอย่าง)
    """
    left, right, top, bottom = PLOT_LEFT, PLOT_RIGHT, 16, 22
    pw, ph = w - left - right, h - top - bottom
    span_pct = _flow_span([v for _, _, v in series], target)
    low, high = target * (1 - span_pct / 100), target * (1 + span_pct / 100)
    minutes = max([end for _, end, _ in series] or [1.0])
    minutes = max(minutes, 0.5)
    sx = lambda m: left + pw * m / minutes
    sy = lambda v: top + ph * (high - v) / (high - low)
    acc, tint = PUMP[pump]["acc"], PUMP[pump]["tint"]
    out = []
    grid_pct = 5 if span_pct <= 25 else 10 if span_pct <= 50 else 20
    k = -int(span_pct // grid_pct)
    while k * grid_pct <= span_pct + 1e-9:
        y = sy(target * (1 + k * grid_pct / 100))
        out.append(_line(left, y, left + pw, y, GRID, 0.8))
        k += 1
    grid_step, label_step = _time_steps(minutes, pw)
    m = 0.0
    while m <= minutes + 1e-6:
        out.append(_line(sx(m), top, sx(m), top + ph, GRID, 0.8))
        m += grid_step
    span = target * tol / 100
    out.append(f'<rect x="{left}" y="{sy(target + span):.1f}" width="{pw}" height="{sy(target - span) - sy(target + span):.1f}" '
               f'fill="{tint}" fill-opacity="0.75"/>')
    out += [_line(left, sy(target + span), left + pw, sy(target + span), acc, 0.9, "4 3"),
            _line(left, sy(target - span), left + pw, sy(target - span), acc, 0.9, "4 3"),
            _line(left, sy(target), left + pw, sy(target), AXIS, 1)]
    label_pct = 10 if span_pct <= 25 else 20 if span_pct <= 50 else 25 if span_pct <= 60 else 50
    steps = int(span_pct // label_pct)
    marks = [(k, target * (1 + k * label_pct / 100)) for k in range(-steps, steps + 1)]
    places = 0 if all(abs(v - round(v)) < 1e-9 for _, v in marks) else 1 if target >= 1 else 2
    for k, v in marks:
        out.append(_text(left - 6, sy(v) + 4, f"{v:.{places}f}", "end", INK if k == 0 else MUTE))
    out.append(_text(left + pw, sy(target + span) - 4, f"±{tol:g} %", "end", acc, "600"))
    if pw >= 450:                                   # ป้ายช่วงเกณฑ์เฉพาะกราฟใหญ่ (กราฟเล็กหน้าเทคนิคแน่นเกิน)
        out.append(_text(left + 6, sy(target + span) - 4, w_("band"), "start", acc))
    clip = lambda v: max(low, min(high, v))
    if style == "points":
        # จุดต่อเส้น: จุดที่เวลาจบของแต่ละช่วงวัด (เหมือนกราฟในโปรแกรม) — จุดมากเกินไปวาดแค่เส้น
        points = [(sx(end), sy(clip(value))) for _, end, value in series]
        if points:
            out.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
                       + f'" fill="none" stroke="{LINE}" stroke-width="1.1" stroke-linejoin="round"/>')
            if len(points) <= 400:
                out += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.1" fill="{LINE}"/>' for x, y in points]
    else:
        path, last_end = [], None
        for start, end, value in series:
            y = sy(clip(value))
            # ต่อเนื่อง = ช่วงถัดไปเริ่มที่ปลายช่วงก่อน — เวลาใน intervals.csv ปัดทศนิยม 3 ตำแหน่ง จึงยอมต่างได้ < 1 s หรือ 5 % ของช่วง
            # (เดิมเทียบ 1e-6 นาที -> แทบทุกรอยต่อถูกนับเป็นช่องว่าง เส้นตั้งหาย กราฟขาดเป็นท่อน — ผู้ใช้เจอ 2026-11-18)
            joined = last_end is not None and abs(start - last_end) <= max(1 / 60, 0.05 * (end - start))
            path.append(f"{'L' if joined else 'M'}{sx(start):.1f},{y:.1f}")
            path.append(f"H{sx(end):.1f}")
            last_end = end
        if path:
            out.append(f'<path d="{"".join(path)}" fill="none" stroke="{LINE}" stroke-width="1.2" stroke-linejoin="round"/>')
    legend = []
    if show_mean and mean is not None:
        out.append(_line(left, sy(clip(mean)), left + pw, sy(clip(mean)), ORANGE, 1.4))
        legend.append((ORANGE, w_("mean_line"), "", 1.6))
    if moving and series:
        # ค่าเฉลี่ยสะสม ตั้งแต่ช่วงแรกถึงช่วงนั้น (แบบเส้น Moving avg ในโปรแกรม)
        total, points = 0.0, []
        for index, (_, end, value) in enumerate(series, 1):
            total += value
            points.append(f"{sx(end):.1f},{sy(clip(total / index)):.1f}")
        out.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{MOVING}" stroke-width="1.6"/>')
        legend.append((MOVING, w_("moving_line"), "", 1.6))
    legend.append((LINE, w_("each"), "", 1.3))
    x = left
    for color, text, _, width in legend:          # คำอธิบายเส้นเรียงต่อกัน (ความกว้างตามจำนวนตัวอักษร)
        out.append(_line(x, top - 9, x + 18, top - 9, color, width))
        out.append(_text(x + 24, top - 5, text, "start", MUTE))
        x += 24 + len(text) * 6.4 + 22
    out += [_line(left, top, left, top + ph, AXIS), _line(left, top + ph, left + pw, top + ph, AXIS)]
    unit = w_("x_axis")
    room = len(unit) * 6.6 + 14                      # เว้นที่ท้ายแกนให้ป้ายหน่วย ("เวลา นาที") ไม่ทับตัวเลข
    m = 0.0
    while m <= minutes + 1e-6:
        if sx(m) < left + pw - room:
            out.append(_text(sx(m), top + ph + 16, f"{m:g}", "middle"))
        m += label_step
    out.append(_text(left + pw, top + ph + 16, unit, "end", INK, "600"))
    return _svg(w, h, "".join(out))


def gauge_limit(err, u, tol):
    """ขอบของมาตรวัด (± %) และค่าล้นขอบไหม — ปกติ ±1.6 × เกณฑ์ ขยายถึง ±4 × เกณฑ์ เกินนั้นลูกศรชี้ออกที่ปลาย"""
    need = abs(err) + (u or 0.0)
    limit = max(tol * 1.6, min(tol * 4.0, math.ceil(need + tol * 0.3)))
    return limit, need > limit


def gauge(pump, err, u, tol, w, slim=False):
    """มาตรวัดแนวนอน: แถบเกณฑ์ ±tol · ขีด −tol / 0 / +tol · ลูกศรชี้ค่าพร้อมตัวเลข · แถบจาง ± U (ถ้ามี)
    slim = แบบเล็กของหน้าผลวัด: พื้นเกณฑ์สีตามชนิดเครื่อง + แถบ ± U เหมือนเดิม แต่ไม่มีป้ายตัวเลขเหนือลูกศร (อยู่ในแถวผลแล้ว)"""
    if slim:
        return _slim_gauge(pump, err, u, tol, w)
    h, left, right = 52, PLOT_LEFT, PLOT_RIGHT
    limit, overflow = gauge_limit(err, u, tol)
    pw = w - left - right
    sx = lambda v: left + pw * (max(-limit, min(limit, v)) + limit) / (2 * limit)
    acc, tint = PUMP[pump]["acc"], PUMP[pump]["tint"]
    out = [_line(left, 31, left + pw, 31, AXIS, 1),
           f'<rect x="{sx(-tol):.1f}" y="26" width="{sx(tol) - sx(-tol):.1f}" height="10" fill="{tint}" stroke="{MUTE}" stroke-width="0.8"/>']
    if u is not None:
        out.append(f'<rect x="{sx(err - u):.1f}" y="28" width="{max(2.0, sx(err + u) - sx(err - u)):.1f}" height="6" '
                   f'fill="{acc}" fill-opacity="0.35"/>')
    for v in (-tol, 0, tol):
        out.append(_line(sx(v), 22, sx(v), 40, INK, 1))
        out.append(_text(sx(v), 51, f"{num(v, 0, v != 0)} %", "middle", INK))
    cx = sx(err)
    if overflow and abs(err) > limit:
        out.append(f'<path d="M{cx:.1f},31 l{9 if err < 0 else -9},-6 v12 z" fill="{acc}"/>')
    else:
        out.append(f'<path d="M{cx:.1f},25 l-6,-9 h12 z" fill="{acc}"/>')
    tail = f' <tspan fill="{MUTE}" font-weight="400">± {u:g}</tspan>' if u is not None else ""
    tx = max(left + 40, min(left + pw - 40, cx))
    out.append(f'<text x="{tx:.1f}" y="12" text-anchor="middle" fill="{acc}" font-weight="700">{num(err, ERR_DP, True)} %{tail}</text>')
    return _svg(w, h, "".join(out))


def _slim_gauge(pump, err, u, tol, w):
    h, left, right = 40, PLOT_LEFT, PLOT_RIGHT
    limit, overflow = gauge_limit(err, u, tol)
    pw = w - left - right
    sx = lambda v: left + pw * (max(-limit, min(limit, v)) + limit) / (2 * limit)
    acc, tint = PUMP[pump]["acc"], PUMP[pump]["tint"]
    out = [_line(left, 18, left + pw, 18, AXIS, 1),
           f'<rect x="{sx(-tol):.1f}" y="13" width="{sx(tol) - sx(-tol):.1f}" height="10" fill="{tint}" stroke="{MUTE}" stroke-width="0.8"/>']
    if u is not None:
        out.append(f'<rect x="{sx(err - u):.1f}" y="15" width="{max(2.0, sx(err + u) - sx(err - u)):.1f}" height="6" '
                   f'fill="{acc}" fill-opacity="0.35"/>')
    for v in (-tol, 0, tol):
        out.append(_line(sx(v), 10, sx(v), 26, INK, 1))
        out.append(_text(sx(v), 38, f"{num(v, 0, v != 0)} %", "middle", INK))
    cx = sx(err)
    if overflow and abs(err) > limit:
        out.append(f'<path d="M{cx:.1f},18 l{9 if err < 0 else -9},-6 v12 z" fill="{acc}"/>')
    else:
        out.append(f'<path d="M{cx:.1f},12 l-6,-9 h12 z" fill="{acc}"/>')
    return _svg(w, h, "".join(out))


def vgauge(w_, pump, err, u, tol, h, top=16, bottom=22, w=84):
    """มาตรวัดแนวตั้งข้างขวากราฟราย rate (องค์ประกอบเดียวกับมาตรวัดแนวนอน หมุน 90°) ไม่มีขีดย่อย"""
    limit, overflow = gauge_limit(err, u, tol)
    ax, ph = 30, h - top - bottom
    sy = lambda v: top + ph * (limit - max(-limit, min(limit, v))) / (2 * limit)
    acc, tint = PUMP[pump]["acc"], PUMP[pump]["tint"]
    out = [_line(0.5, top, 0.5, top + ph, GRID, 1), _line(ax, top, ax, top + ph, AXIS, 1),
           f'<rect x="{ax - 5}" y="{sy(tol):.1f}" width="10" height="{sy(-tol) - sy(tol):.1f}" fill="{tint}" stroke="{MUTE}" stroke-width="0.8"/>']
    if u is not None:
        out.append(f'<rect x="{ax - 3}" y="{sy(err + u):.1f}" width="6" height="{max(2.0, sy(err - u) - sy(err + u)):.1f}" '
                   f'fill="{acc}" fill-opacity="0.35"/>')
    for v in (tol, 0, -tol):
        out.append(_line(ax - 9, sy(v), ax + 9, sy(v), INK, 1))
        out.append(_text(ax + 14, sy(v) + 4, f"{num(v, 0, v != 0)} %", "start", INK))
    if overflow and abs(err) > limit:
        if err > 0:
            out.append(f'<path d="M{ax:.1f},{top - 2:.1f} l-6,10 h12 z" fill="{acc}"/>')
            out.append(_text(ax + 12, top + 7, f"{num(err, ERR_DP, True)} %", "start", acc, "700"))
        else:
            out.append(f'<path d="M{ax:.1f},{top + ph + 2:.1f} l-6,-10 h12 z" fill="{acc}"/>')
            out.append(_text(ax + 12, top + ph - 1, f"{num(err, ERR_DP, True)} %", "start", acc, "700"))
    else:
        out.append(f'<path d="M{ax - 6:.1f},{sy(err):.1f} l-9,-6 v12 z" fill="{acc}"/>')
    out.append(_text(3, top + ph + 16, w_("error"), "start", INK, "600"))
    return _svg(w, h, "".join(out))


def trend_slope(rows) -> float | None:
    """ความชันของเส้นแนวโน้ม error = a + b·log10(rate) (% ต่อ 10 เท่าของอัตรา) — ต้องมีอย่างน้อย 2 rate"""
    xs = [math.log10(r.set_rate) for r in rows if r.set_rate > 0]
    if len(set(xs)) < 2:
        return None
    ys = [r.error for r in rows if r.set_rate > 0]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)


def error_chart(w_, pump, rows, tol, w, h):
    """ความคลาดเคลื่อน ± U ของแต่ละค่าที่ตั้ง บนแกนอัตราแบบ log · แถบเกณฑ์ · เส้นแนวโน้ม linear regression"""
    left, right, top, bottom = 40, 12, 10, 34
    pw, ph = w - left - right, h - top - bottom
    rates = [r.set_rate for r in rows if r.set_rate > 0] or [1.0]
    lo, hi = math.log10(min(rates) / 1.7), math.log10(max(rates) * 1.65)
    if hi - lo < 1.0:                               # rate เดียว/ใกล้กัน: กว้างอย่างน้อย 1 decade
        mid = (hi + lo) / 2
        lo, hi = mid - 0.5, mid + 0.5
    need = max([abs(r.error) + (r.u or 0.0) for r in rows] or [0.0])
    limit = max(tol * 1.6, min(tol * 4.0, math.ceil(need + tol * 0.3)))
    sx = lambda r: left + pw * (math.log10(r) - lo) / (hi - lo)
    sy = lambda v: top + ph * (limit - max(-limit, min(limit, v))) / (2 * limit)
    acc, tint = PUMP[pump]["acc"], PUMP[pump]["tint"]
    out = []
    for decade in range(math.floor(lo) - 1, math.ceil(hi) + 1):
        for k in range(1, 10):
            r = k * 10.0 ** decade
            if lo <= math.log10(r) <= hi:
                out.append(_line(sx(r), top, sx(r), top + ph, GRID if k != 1 else "#D3D8DE", 0.8))
    step = 1 if limit <= 10 else 2 if limit <= 20 else 5
    for k in range(-int(limit // step), int(limit // step) + 1):
        out.append(_line(left, sy(k * step), left + pw, sy(k * step), GRID, 0.8))
    out.append(f'<rect x="{left}" y="{sy(tol):.1f}" width="{pw}" height="{sy(-tol) - sy(tol):.1f}" fill="{tint}" fill-opacity="0.75"/>')
    out += [_line(left, sy(tol), left + pw, sy(tol), acc, 0.9, "4 3"), _line(left, sy(-tol), left + pw, sy(-tol), acc, 0.9, "4 3"),
            _line(left, sy(0), left + pw, sy(0), "#C3C9D0", 0.8)]
    labels = [-tol, 0.0, tol]
    if limit >= 2.5 * tol:                          # แกนขยายเพราะค่าเกินมาก: เพิ่มป้ายทุก 5 / 10 % (ไม่ชิดป้ายเกณฑ์)
        lab = 5 if limit <= 15 else 10
        labels += [k * lab for k in range(-int(limit // lab), int(limit // lab) + 1)
                   if all(abs(k * lab - v) >= lab * 0.6 for v in (-tol, 0.0, tol))]
    for v in labels:
        out.append(_text(left - 6, sy(v) + 4, num(v, 0, v != 0), "end", INK if v in (-tol, 0.0, tol) else MUTE))
    out.append(_text(left - 6, top + 2, "%", "end"))
    slope = trend_slope(rows)
    if slope is not None:
        xs = [math.log10(r.set_rate) for r in rows if r.set_rate > 0]
        ys = [r.error for r in rows if r.set_rate > 0]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        fit = lambda r: my + slope * (math.log10(r) - mx)
        x0, x1 = 10 ** (lo + 0.03 * (hi - lo)), 10 ** (hi - 0.03 * (hi - lo))
        out.append(f'<line x1="{sx(x0):.1f}" y1="{sy(fit(x0)):.1f}" x2="{sx(x1):.1f}" y2="{sy(fit(x1)):.1f}" stroke="#fff" stroke-width="5"/>')
        out.append(_line(sx(x0), sy(fit(x0)), sx(x1), sy(fit(x1)), ORANGE, 2.2, "9 5"))
        ordered = sorted(rates)
        gap = math.sqrt(ordered[0] * ordered[1])
        tx = max(left + 70, min(left + pw - 70, sx(gap)))
        out.append(_text(tx, sy(fit(gap)) + 18, f'{w_("trend_tag")} {num(slope, 2, True)} %', "middle", ORANGE, "700"))
    for r in rows:
        if r.set_rate <= 0:
            continue
        cx, cy = sx(r.set_rate), sy(r.error)
        if r.u is not None:
            out.append(_line(cx, sy(r.error + r.u), cx, sy(r.error - r.u), acc, 1.6))
            for edge in (r.error + r.u, r.error - r.u):
                out.append(_line(cx - 5, sy(edge), cx + 5, sy(edge), acc, 1.6))
        color = acc if r.passed else "#B42318"
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.4" fill="{color}" stroke="#fff" stroke-width="1.2"/>')
        out.append(_text(cx, top + ph + 16, f"{r.set_rate:g}", "middle", INK, "600"))
    out += [_line(left, top, left, top + ph, AXIS), _line(left, top + ph, left + pw, top + ph, AXIS)]
    out.append(_text(left + pw, h - 2, w_("rate_x"), "end"))
    return _svg(w, h, "".join(out)), slope
