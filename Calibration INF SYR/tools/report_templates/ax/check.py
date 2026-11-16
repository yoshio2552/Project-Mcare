"""ตรวจว่าหน้าไหนมีเนื้อหาล้นกระดาษ / ตัวหนังสือเล็กกว่า 12 px (วัดจริงด้วย Edge headless)
ใช้: python tools/report_templates/ax/check.py template/A2/source [template/A3/source ...]
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pack  # noqa: E402

JS = """<script>
window.addEventListener('load', () => setTimeout(() => {
  const page = document.querySelector('.page'); const pr = page.getBoundingClientRect();
  const over = [], small = new Set();
  for (const el of page.querySelectorAll('*')) {
    const r = el.getBoundingClientRect();
    if (r.width && r.height && (r.bottom > pr.bottom + 0.5 || r.right > pr.right + 0.5)) {
      const txt = (el.textContent || '').trim().slice(0, 40);
      if (!el.children.length || el.tagName === 'svg') over.push(Math.round(r.bottom - pr.bottom) + 'px ' + el.tagName + ' ' + txt);
    }
    if (el.childNodes.length && [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) {
      const fs = parseFloat(getComputedStyle(el).fontSize);
      if (fs < 11.95 && !el.closest('svg')) small.add(fs + 'px ' + el.textContent.trim().slice(0, 30));
    }
  }
  for (const tx of page.querySelectorAll('svg text')) {
    const sv = tx.ownerSVGElement, vb = sv.viewBox.baseVal;
    const k = vb && vb.height ? sv.getBoundingClientRect().height / vb.height : 1;   // ขนาดจริงหลังย่อ/ขยายด้วย viewBox
    const fs = parseFloat(tx.getAttribute('font-size') || getComputedStyle(tx).fontSize) * k;
    if (fs < 11.95) small.add('svg ' + fs + ' ' + tx.textContent.slice(0, 30));
  }
  document.body.setAttribute('data-check', JSON.stringify({over: over.slice(0, 6), small: [...small].slice(0, 6)}));
}, 1500));
</script>"""


def check(src):
    canvas = json.loads((src / "canvas.json").read_text(encoding="utf-8"))
    tmp = Path(tempfile.mkdtemp())
    bad = 0
    for name in sorted(p.name for p in src.glob("*.dc.html")):
        b = canvas["boards"][name]
        links, css, body = pack.page_parts(src, name, {})
        styles = [pack.dc2html.scope_css(c, ".pg1") for c in css]
        page = f'<div class="page pg1" style="width:{b["w"]}px;height:{b["h"]}px">{body}</div>'
        html = pack.doc("check", links, styles, [page], "").replace("</body>", JS + "</body>")
        f = tmp / "p.html"
        f.write_text(html, encoding="utf-8")
        out = subprocess.run([pack.EDGE, "--headless=new", "--disable-gpu", f"--user-data-dir={pack.PROFILE}",
                              "--virtual-time-budget=8000", "--dump-dom", f.as_uri()], capture_output=True, text=True,
                             encoding="utf-8", timeout=120).stdout
        m = re.search(r'data-check="([^"]*)"', out)
        res = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&")) if m else {"over": ["?"], "small": []}
        ok = not res["over"] and not res["small"]
        bad += not ok
        print(("OK  " if ok else "BAD ") + name, "" if ok else res)
    return bad


if __name__ == "__main__":
    sys.exit(sum(check(Path(a)) for a in sys.argv[1:]))
