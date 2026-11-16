"""แปลง artboard .dc.html หลายไฟล์ -> HTML ไฟล์เดียวที่เปิดในเบราว์เซอร์และพิมพ์ A4 ได้
ใช้: python dc2html.py <version: A|B> <src_project_dir> <out_html> <title>
"""
import re
import sys
from pathlib import Path


def series(n, mean, spread, seed, y0=70.0, k=6.4, x0=40.0, w=380.0):
    # เหมือน renderVals ในไฟล์ CalibrationP2 (สุ่มแบบกำหนดได้)
    s = seed

    def rnd():
        nonlocal s
        s = (s * 16807) % 2147483647
        return s / 2147483647 - 0.5

    pts = []
    for i in range(n):
        e = mean + spread * (rnd() + rnd() + rnd()) / 1.5
        x = x0 + (w * i) / (n - 1)
        y = y0 - e * k
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def mark(name, r):
    return {"name": name, "p": "✓" if r == "p" else "", "f": "✓" if r == "f" else "", "na": "✓" if r == "na" else ""}


def data_a():
    def make(set_, n, period, vol, raw, flow, err, sd, pre, mean, spread, seed):
        return dict(set=set_, n=n, period=period, vol=vol, raw=raw, flow=flow, err=err, sd=sd, pre=pre,
                    pts=series(n, mean, spread, seed), meanY=f"{70 - mean * 6.4:.1f}",
                    aria=f"Error per interval at {set_} ml/h")
    return {
        "Main.dc.html": {"accent": "#38BDF8", "accentInk": "#0B6FA4"},
        "CalibrationP2.dc.html": {"rates": [
            make("10.0", 12, "71.4", "0.198", "9.83", "9.87", "−1.3", "3.1", "auto · 4:10 min", -1.3, 1.6, 11),
            make("50.0", 58, "15.2", "0.213", "50.20", "50.42", "+0.8", "2.4", "auto · 2:40 min", 0.8, 1.2, 29),
            make("200.0", 231, "3.9", "0.212", "195.4", "196.10", "−2.0", "7.8", "delay 60 s", -2.0, 3.6, 47),
        ]},
        "Inspection.dc.html": {
            "left": [mark("Housing and labels", "p"), mark("Pole clamp", "p"), mark("Power cord and plug", "p"),
                     mark("Battery operation", "p"), mark("Keypad and controls", "p")],
            "right": [mark("Display and indicators", "p"), mark("Syringe clamp and plunger holder", "p"),
                      mark("Syringe size detection", "p"), mark("Audible and visual alarms", "p"),
                      mark("Nurse call output", "na")],
        },
    }


DATA = {"A": data_a, **{v: (lambda: {}) for v in "BCDEF"}}


def wanted(version, name):
    # แบบ B ขึ้นต้นด้วย "B-" · แบบ A คือที่เหลือ
    return name.startswith(version + "-") if version != "A" else not (len(name) > 2 and name[1] == "-")


def lookup(ctx, path):
    cur = ctx
    for part in path.split("."):
        cur = cur[part]
    return str(cur)


def fill(text, ctx):
    return re.sub(r"\{\{\s*([\w.$]+)\s*\}\}", lambda m: lookup(ctx, m.group(1)) if _has(ctx, m.group(1)) else m.group(0), text)


def _has(ctx, path):
    try:
        lookup(ctx, path)
        return True
    except (KeyError, TypeError):
        return False


def expand(body, data):
    pat = re.compile(r'<sc-for list="\{\{\s*(\w+)\s*\}\}" as="(\w+)"[^>]*>(.*?)</sc-for>', re.S)

    def rep(m):
        items, var, inner = data[m.group(1)], m.group(2), m.group(3)
        return "".join(fill(inner, {**data, var: it}) for it in items)

    body = pat.sub(rep, body)
    return fill(body, data)


def scope_css(css, scope):
    out = []
    for rule in css.split("}"):
        if "{" not in rule:
            continue
        sel, decl = rule.split("{", 1)
        sels = []
        for s in sel.split(","):
            s = s.strip()
            if not s:
                continue
            sels.append(scope if s == "body" else f"{scope} {s}")
        out.append(f"{', '.join(sels)}{{{decl}}}")
    return "\n".join(out)


def convert(version, src, out, title):
    data_all = DATA[version]()
    canvas = __import__("json").loads((src / "canvas.json").read_text(encoding="utf-8"))
    links, styles, pages = [], [], []
    for i, name in enumerate(n for n in canvas["order"] if wanted(version, n)):
        html = (src / name).read_text(encoding="utf-8")
        helmet = re.search(r"<helmet>(.*?)</helmet>", html, re.S).group(1)
        body = re.search(r"</helmet>(.*?)</x-dc>", html, re.S).group(1)
        for link in re.findall(r"<link[^>]*>", helmet):
            if link not in links:
                links.append(link)
        for css in re.findall(r"<style>(.*?)</style>", helmet, re.S):
            styles.append(scope_css(css, f".pg{i}"))
        board = canvas["boards"][name]
        pages.append(f'<div class="page pg{i}" style="width:{board["w"]}px;height:{board["h"]}px">'
                     f"{expand(body, data_all.get(name, {}))}</div>")
    doc = f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{chr(10).join(links)}
<style>
@page {{ size: A4; margin: 0 }}
html, body {{ margin: 0; background: #E9ECEF }}
.page {{ margin: 24px auto; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.18); overflow: hidden }}
@media print {{ html, body {{ background: #fff }} .page {{ margin: 0; box-shadow: none; break-after: page }} }}
{chr(10).join(styles)}
</style>
</head>
<body>
{chr(10).join(pages)}
</body>
</html>
"""
    out.write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    convert(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])
