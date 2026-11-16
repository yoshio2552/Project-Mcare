"""แพ็กแบบเอกสารแต่ละแบบ -> template/<V>/ : PNG รายหน้า, HTML รวม, PDF รวม, source/
ใช้: python tools/report_templates/pack.py <project_dir> <template_dir> [V ...]
  project_dir = โฟลเดอร์ที่มี canvas.json + ไฟล์ .dc.html (โฟลเดอร์ project/ ของ canvas ที่ดาวน์โหลดมา
                หรือ template/<V>/source ของแบบนั้นเอง — กรณีหลังจะไม่คัดลอก source ทับตัวเอง)
ต้องมี Microsoft Edge (headless) และต่อเน็ตเพื่อโหลดฟอนต์ Google Fonts
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dc2html  # noqa: E402  (expand / scope_css / DATA)

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
# โปรไฟล์ Edge ชั่วคราว — ไม่แตะโปรไฟล์จริงของผู้ใช้
PROFILE = Path(tempfile.gettempdir()) / "deltam-template-edge"


def boards_of(version, canvas):
    return [n for n in canvas["order"] if dc2html.wanted(version, n)]


def page_parts(src, name, data):
    html = (src / name).read_text(encoding="utf-8")
    helmet = re.search(r"<helmet>(.*?)</helmet>", html, re.S).group(1)
    body = re.search(r"</helmet>(.*?)</x-dc>", html, re.S).group(1)
    links = re.findall(r"<link[^>]*>", helmet)
    css = re.findall(r"<style>(.*?)</style>", helmet, re.S)
    return links, css, dc2html.expand(body, data)


def doc(title, links, styles, pages, page_css):
    return f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{chr(10).join(dict.fromkeys(links))}
<style>
html, body {{ margin: 0; background: #E9ECEF }}
.page {{ background: #fff; overflow: hidden }}
{page_css}
{chr(10).join(styles)}
</style></head><body>
{chr(10).join(pages)}
</body></html>
"""


def edge(*args):
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-first-run",
                    f"--user-data-dir={PROFILE}", "--virtual-time-budget=10000", *args],
                   check=False, timeout=120)


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")


def pack(version, project, out):
    canvas = json.loads((project / "canvas.json").read_text(encoding="utf-8"))
    data_all = dc2html.DATA.get(version, lambda: {})()
    names = boards_of(version, canvas)
    (out / "png").mkdir(parents=True, exist_ok=True)
    src_dir = out / "source"
    # อ่านจาก source ของแบบนี้เองได้ — ไม่ลบ/คัดลอกทับ
    copy_source = project.resolve() != src_dir.resolve()
    if copy_source:
        if src_dir.exists():
            shutil.rmtree(src_dir)
        src_dir.mkdir()
        shutil.copy2(project / "canvas.json", src_dir / "canvas.json")

    all_links, all_styles, all_pages, named = [], [], [], []
    for i, name in enumerate(names, 1):
        if copy_source:
            shutil.copy2(project / name, src_dir / name)
        b = canvas["boards"][name]
        w, h = b["w"], b["h"]
        w = 794 if w == 791 else w   # กรอบหน้าแรกของแบบ A ถูกลากเล็กลง 3 px บน canvas
        links, css, body = page_parts(project, name, data_all.get(name, {}))
        scope = f".pg{i}"
        styles = [dc2html.scope_css(c, scope) for c in css]
        page = f'<div class="page pg{i}" style="width:{w}px;height:{h}px">{body}</div>'
        # PNG รายหน้า (ความละเอียด 2 เท่า)
        single = doc(f"{version} {i}", links, styles, [page], "")
        tmp = out / f"_page{i}.html"
        tmp.write_text(single, encoding="utf-8")
        png = out / "png" / f"{version}-{i:02d}-{slug(b.get('title', name))}.png"
        edge("--hide-scrollbars", f"--window-size={w},{h}", "--force-device-scale-factor=2",
             f"--screenshot={png}", tmp.resolve().as_uri())
        tmp.unlink()
        all_links += links
        all_styles += styles
        all_pages.append(page)
        named.append(f"@page p{i} {{ size: {w}px {h}px; margin: 0 }} .pg{i} {{ page: p{i} }}")

    screen = (".page { margin: 24px auto; box-shadow: 0 1px 4px rgba(0,0,0,.18) }\n"
              "@media print { html, body { background: #fff } .page { margin: 0; box-shadow: none; break-after: page } }\n"
              + "\n".join(named))
    combined = out / f"{version}.html"
    combined.write_text(doc(f"DeltaM report template {version}", all_links, all_styles, all_pages, screen),
                        encoding="utf-8")
    edge("--no-pdf-header-footer", f"--print-to-pdf={out / (version + '.pdf')}", combined.resolve().as_uri())
    return names


if __name__ == "__main__":
    project, template = Path(sys.argv[1]), Path(sys.argv[2])
    for v in sys.argv[3:]:
        names = pack(v, project, template / v)
        pngs = sorted((template / v / "png").glob("*.png"))
        print(v, len(names), "boards", len(pngs), "png", (template / v / f"{v}.pdf").exists())
