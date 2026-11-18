"""สร้างแบบเอกสาร FableA–E (ไทย + อังกฤษ) -> template/Fable?/  : HTML, PDF, PNG รายหน้า

ใช้: python tools/report_templates/fable/build.py            ทุกแบบ
     python tools/report_templates/fable/build.py FableA FableC --nopng     เฉพาะบางแบบ / ไม่ทำ PNG (เร็ว ใช้ตอนปรับหน้าตา)
ต้องมี Microsoft Edge (headless) และต่อเน็ตเพื่อโหลดฟอนต์ Google Fonts
ทุกครั้งที่สร้างจะตรวจด้วย Edge จริงว่าไม่มีหน้าไหนล้นกระดาษ และไม่มีตัวอักษรเล็กกว่า 12 px (พิมพ์ BAD ถ้ามี)
ไม่ผูกกับ canvas — แก้เนื้อหาที่ content.py, โครงหน้าที่ blocks.py, หน้าตาที่ styles.py แล้วรันใหม่
"""
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import importlib  # noqa: E402

import blocks  # noqa: E402
import styles  # noqa: E402

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PROFILES = Path(tempfile.gettempdir()) / "deltam-fable-edge"     # โปรไฟล์ชั่วคราว ไม่แตะโปรไฟล์จริงของผู้ใช้
W, H = 794, 1123

CHECK_JS = """<script>
window.addEventListener('load', () => document.fonts.ready.then(() => setTimeout(() => {
  try {
  const out = [];
  document.querySelectorAll('.page').forEach((page, index) => {
    const pr = page.getBoundingClientRect(), foot = page.querySelector('.foot').getBoundingClientRect();
    const over = [], small = new Set();
    if (foot.bottom > pr.bottom + 1) over.push('footer pushed off the page by ' + Math.round(foot.bottom - pr.bottom) + 'px');
    for (const el of page.querySelectorAll('*')) {
      if (el.closest('.foot')) continue;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      const leaf = !el.children.length || el.tagName === 'svg';
      if (leaf && (r.bottom > foot.top - 2 || r.right > pr.right - 20 || r.left < pr.left + 20) && !el.closest('.hdr, .meta, .kv.ident, .bar'))
        over.push(Math.round(r.bottom - foot.top) + 'px ' + el.tagName + ' ' + (el.textContent || '').trim().slice(0, 24));
      if (!el.closest('svg') && [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) {
        const fs = parseFloat(getComputedStyle(el).fontSize);
        if (fs < 11.95) small.add(fs + 'px ' + el.textContent.trim().slice(0, 20));
      }
    }
    const last = [...page.children].filter(c => !c.classList.contains('foot')).pop().getBoundingClientRect();
    out.push({page: index + 1, free: Math.round(foot.top - last.bottom), over: over.slice(0, 4), small: [...small].slice(0, 4)});
  });
  document.body.setAttribute('data-check', JSON.stringify(out));
  } catch (e) { document.body.setAttribute('data-check', JSON.stringify([{page: 0, free: -999, over: ['script error: ' + e], small: []}])); }
}, 400)));
</script>"""


def edge(profile: str, *args, capture=False):
    return subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={PROFILES / profile}",
                           "--virtual-time-budget=12000", *args], capture_output=capture, text=capture, encoding="utf-8",
                          check=False, timeout=180)


def _builder(V: dict):
    """โมดูลที่สร้างหน้า: blocks (โครงร่วมของ A–E) หรือโมดูลของแบบนั้นเอง เช่น f.py"""
    return importlib.import_module(V["builder"]) if V.get("builder") else blocks


def _css(V: dict) -> str:
    builder = _builder(V)
    if builder is blocks:
        return styles.BASE + V["css"]
    return builder.css_for(V) if hasattr(builder, "css_for") else builder.CSS


def html_doc(title: str, lang: str, V: dict, pages: list[str], screen: bool) -> str:
    extra = (".page { margin: 24px auto; box-shadow: 0 1px 5px rgba(0,0,0,.2) }\n"
             "@media print { html, body { background: #fff } .page { margin: 0; box-shadow: none; break-after: page } }"
             if screen else "html, body { background: #fff }")
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?{V["fonts"]}&display=swap" rel="stylesheet">
<style>
@page {{ size: {W}px {H}px; margin: 0 }}
{_css(V)}
{extra}
</style></head><body>
{chr(10).join(pages)}
</body></html>
"""


def build(name: str, png: bool = True) -> int:
    V = styles.VARIANTS[name]
    out = ROOT / "template" / V.get("folder", name)
    (out / "png").mkdir(parents=True, exist_ok=True)
    bad, jobs = 0, []
    for lang in ("th", "en"):
        tag = f"{name}-{lang.upper()}"
        pages = _builder(V).document(lang, V)
        combined = out / f"{tag}.html"
        combined.write_text(html_doc(f"{name} {V['name']} {lang.upper()}", lang, V, [p for _, p in pages], True), encoding="utf-8")
        pdf = out / (tag + ".pdf")
        before = pdf.stat().st_mtime if pdf.exists() else 0.0
        edge(tag, "--no-pdf-header-footer", f"--print-to-pdf={pdf}", combined.resolve().as_uri())
        if not pdf.exists() or pdf.stat().st_mtime <= before:
            # เจอจริง 2026-11-18: FableA-EN.pdf เปิดค้างในโปรแกรมอ่าน PDF -> Edge เขียนทับไม่ได้ ไฟล์เก่าค้างอยู่เงียบๆ
            print("BAD", tag, "PDF was not updated — close the PDF if it is open in a viewer, then build again")
            bad += 1
        # ตรวจล้นหน้า / ตัวอักษรเล็ก
        probe = out / f"_{tag}-check.html"
        probe.write_text(combined.read_text(encoding="utf-8").replace("</body>", CHECK_JS + "</body>"), encoding="utf-8")
        dom = edge(tag, "--dump-dom", probe.resolve().as_uri(), capture=True).stdout or ""
        probe.unlink()
        found = re.search(r'data-check="([^"]*)"', dom)
        report = json.loads(found.group(1).replace("&quot;", '"').replace("&amp;", "&")) if found else []
        if not report:
            print("BAD", tag, "no check result")
            bad += 1
        for (label, _), res in zip(pages, report):
            ok = not res["over"] and not res["small"] and res["free"] >= 0
            bad += not ok
            print(("ok  " if ok else "BAD ") + f"{tag} {label:28s} free {res['free']:4d}px", "" if ok else res)
        if png:
            for old in (out / "png").glob(f"{tag}-*.png"):
                old.unlink()
            for index, (label, page) in enumerate(pages, 1):
                jobs.append((tag, lang, V, index, label, page, out))
    if jobs:
        def shot(job):
            tag, lang, V, index, label, page, out = job
            single = out / f"_{tag}-{index}.html"
            single.write_text(html_doc(tag, lang, V, [page], False), encoding="utf-8")
            target = out / "png" / f"{tag}-{index}-{label}.png"
            for _ in range(3):                      # Edge headless พลาดเป็นบางครั้งเมื่อรันพร้อมกันหลายตัว — ลองซ้ำ
                edge(f"{tag}-p{index}", "--hide-scrollbars", f"--window-size={W},{H}", "--force-device-scale-factor=2",
                     f"--screenshot={target}", single.resolve().as_uri())
                if target.exists():
                    break
            single.unlink()
            return target.exists()
        with ThreadPoolExecutor(max_workers=4) as pool:
            done = list(pool.map(shot, jobs))
        print(name, "png", sum(done), "/", len(jobs))
    return bad


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    names = args or list(styles.VARIANTS)
    total = sum(build(n, png="--nopng" not in sys.argv) for n in names)
    print("pages with problems:", total)
    sys.exit(1 if total else 0)
