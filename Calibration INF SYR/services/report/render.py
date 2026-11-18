"""HTML -> PDF ด้วย QtWebEngine (Chromium ตัวเดียวกับที่สร้างแบบ จึงหน้าตาเหมือนกัน) + บันทึกไฟล์อย่างปลอดภัย

- PdfRenderer: ทำทีละงานตามคิว ทำงานแบบ async (Chromium ทำงานใน process แยก) — จอไม่ค้าง
  HTML เขียนลงไฟล์ชั่วคราวแล้วเปิดด้วย load() เพราะ setHtml() รับได้ไม่เกิน 2 MB (ฟอนต์ฝัง + กราฟรันนานเกินได้)
- render_pdf_sync / check_layout_sync: แบบรอผล (ใช้ใน exporter และเทสต์) — ต้องมี QApplication แล้ว
- check_layout: ตัวตรวจล้นกระดาษ/ตัวอักษรเล็กกว่า 12 px แบบเดียวกับ CHECK_JS ของ tools/report_templates/fable/build.py
- save_pdf: เขียนไฟล์ชั่วคราวแล้วแทนที่ — ไฟล์ปลายทางเปิดค้างในโปรแกรมอ่าน PDF -> FileLockedError (ไฟล์เดิมไม่เสีย)
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEventLoop, QMarginsF, QObject, QTimer, QUrl
from PySide6.QtGui import QPageLayout, QPageSize

log = logging.getLogger(__name__)

_CHECK_JS = """(() => {
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
    out.push({page: index + 1, free: Math.round(foot.top - last.bottom), over: over.slice(0, 4), small: [...small].slice(0, 4),
              font: getComputedStyle(page).fontFamily,
              font_ok: document.fonts.check('13px ' + getComputedStyle(page).getPropertyValue('--ff').trim())});
  });
  return JSON.stringify(out);
  } catch (e) { return JSON.stringify([{page: 0, free: -999, over: ['script error: ' + e], small: []}]); }
})()"""


# ย่อหน้าที่ล้นทีละระดับ (fit1 ระยะห่าง -> fit2 ตัวอักษร 12 px -> fit3 อะไหล่เป็นข้อความต่อกัน) — หน้าที่พอดีไม่ถูกแตะ
_FIT_JS = """(() => {
  const levels = [];
  document.querySelectorAll('.page').forEach(page => {
    const over = () => {
      const foot = page.querySelector('.foot');
      if (!foot) return false;
      const top = foot.getBoundingClientRect().top;
      const last = [...page.children].filter(c => !c.classList.contains('foot')).pop();
      return last && last.getBoundingClientRect().bottom > top - 4;
    };
    let level = 0;
    while (over() && level < 3) { level++; page.classList.add('fit' + level); }
    levels.push(level);
  });
  return JSON.stringify(levels);
})()"""


class FileLockedError(OSError):
    """บันทึกทับไม่ได้ — ไฟล์เปิดค้างอยู่ในโปรแกรมอื่น (เช่น โปรแกรมอ่าน PDF)"""


def a4_layout() -> QPageLayout:
    return QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0))


class PdfRenderer(QObject):
    """แปลง HTML เป็น PDF ทีละงาน: render(html, done) -> done(pdf_bytes | None, ข้อความผิดพลาด, ผลตรวจรายหน้า)

    ก่อนสร้าง PDF: รอฟอนต์ -> ย่อหน้าที่ล้น (_FIT_JS) -> ตรวจล้นหน้า (_CHECK_JS, ใส่ระดับย่อไว้ใน "fit")
    """

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        from PySide6.QtWebEngineCore import QWebEnginePage     # import ช้า (~0.5 s) — โหลดเมื่อใช้จริงเท่านั้น
        self._page = QWebEnginePage(self)
        self._page.loadFinished.connect(self._on_loaded)
        self._queue: list[tuple[str, Callable]] = []
        self._current: tuple[str, Callable] | None = None
        self._levels: list = []
        self._dir = Path(tempfile.mkdtemp(prefix="deltam-report-"))
        self._file = self._dir / "report.html"
        self._polls = 0
        self._checks: list = []
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(lambda: self._finish(None, "timed out while building the PDF"))

    @property
    def busy(self) -> bool:
        return self._current is not None

    def render(self, html: str, done: Callable) -> None:
        self._queue.append((html, done))
        if self._current is None:
            self._next()

    def _next(self) -> None:
        if not self._queue:
            return
        self._current = self._queue.pop(0)
        self._checks, self._levels = [], []
        try:
            self._file.write_text(self._current[0], encoding="utf-8")
        except OSError as exc:
            self._finish(None, str(exc))
            return
        self._polls = 0
        self._timeout.start(90_000)
        self._page.load(QUrl.fromLocalFile(str(self._file)))

    def _on_loaded(self, ok: bool) -> None:
        if self._current is None:
            return
        if not ok:
            self._finish(None, "could not load the report page")
            return
        self._wait_fonts()

    def _wait_fonts(self) -> None:
        # ฟอนต์ฝังเป็น data URI — รอให้ document.fonts พร้อมก่อน (ไม่งั้นตัวอักษรหน้าแรกอาจเป็นฟอนต์สำรอง)
        self._page.runJavaScript("document.fonts.status", 0, self._on_font_status)

    def _on_font_status(self, status) -> None:
        if self._current is None:
            return
        self._polls += 1
        if status != "loaded" and self._polls < 100:
            QTimer.singleShot(50, self._wait_fonts)
            return
        self._page.runJavaScript(_FIT_JS, 0, self._on_fitted)

    def _on_fitted(self, result) -> None:
        try:
            self._levels = json.loads(result or "[]")
        except (TypeError, ValueError):
            self._levels = []
        self._page.runJavaScript(_CHECK_JS, 0, self._on_checked)

    def _on_checked(self, result) -> None:
        try:
            self._checks = json.loads(result or "[]")
        except (TypeError, ValueError):
            self._checks = [{"page": 0, "free": -999, "over": ["no check result"], "small": []}]
        for item, level in zip(self._checks, self._levels):
            item["fit"] = level
        self._print()

    def _print(self) -> None:
        self._page.printToPdf(self._on_pdf, a4_layout())

    def _on_pdf(self, data) -> None:
        payload = bytes(data)
        self._finish(payload if payload else None, "" if payload else "empty PDF")

    def _finish(self, data: bytes | None, error: str) -> None:
        current, self._current = self._current, None
        self._timeout.stop()
        if current is not None:
            try:
                current[1](data, error, self._checks)
            except Exception:       # ผู้เรียกพัง ไม่ให้คิวค้าง
                log.exception("report callback failed")
        QTimer.singleShot(0, self._next)

    def cleanup(self) -> None:
        try:
            for item in self._dir.iterdir():
                item.unlink()
            self._dir.rmdir()
        except OSError:
            pass


_shared: PdfRenderer | None = None


def shared_renderer() -> PdfRenderer:
    """ตัวสร้าง PDF ตัวเดียวของโปรแกรม (สร้างครั้งแรกที่ใช้)"""
    global _shared
    if _shared is None:
        _shared = PdfRenderer()
    return _shared


def _wait(start: Callable[[Callable], None], timeout_s: float):
    loop, box = QEventLoop(), {}

    def done(*args):
        box["args"] = args
        loop.quit()
    start(done)
    if "args" not in box:
        QTimer.singleShot(int(timeout_s * 1000), loop.quit)
        loop.exec()
    return box.get("args")


def render_pdf_sync(html: str, timeout_s: float = 120.0) -> bytes:
    """สร้าง PDF แบบรอผล (วนรอบ event loop ระหว่างรอ) — ผิดพลาด -> RuntimeError"""
    args = _wait(lambda done: shared_renderer().render(html, done), timeout_s)
    if not args or args[0] is None:
        raise RuntimeError(args[1] if args else "timed out while building the PDF")
    return args[0]


def check_layout_sync(html: str, timeout_s: float = 120.0) -> tuple[bytes | None, list]:
    """สร้าง PDF + ผลตรวจล้นหน้า [{page, free, over, small, font_ok}] แบบรอผล"""
    args = _wait(lambda done: shared_renderer().render(html, done), timeout_s)
    if not args:
        return None, [{"page": 0, "free": -999, "over": ["timed out"], "small": []}]
    return args[0], args[2]


def layout_problems(checks: list) -> list[str]:
    """ข้อความของหน้าที่มีปัญหา (ว่าง = ทุกหน้าพอดีกระดาษ)"""
    out = []
    for item in checks or []:
        if item.get("over") or item.get("small") or item.get("free", 0) < 0:
            out.append(f"page {item.get('page')}: free {item.get('free')}px over={item.get('over')} small={item.get('small')}")
    return out


def save_pdf(data: bytes, path: Path) -> Path:
    """บันทึก PDF: เขียนไฟล์ชั่วคราวในโฟลเดอร์เดียวกันแล้วแทนที่ (ไม่ทิ้งไฟล์ครึ่งๆ) — ไฟล์เปิดค้าง -> FileLockedError"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(prefix=".deltam-", suffix=".pdf", dir=str(path.parent))
    try:
        with os.fdopen(handle, "wb") as f:
            f.write(data)
        try:
            os.replace(temp, path)
        except PermissionError as exc:
            raise FileLockedError(exc.errno, f"{path.name} is open in another program", str(path)) from exc
    finally:
        if os.path.exists(temp):
            try:
                os.remove(temp)
            except OSError:
                pass
    return path


def unique_path(path: Path) -> Path:
    """ชื่อที่ยังไม่มีไฟล์: name.pdf -> name (2).pdf -> name (3).pdf"""
    path = Path(path)
    if not path.exists():
        return path
    for n in range(2, 1000):
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists():
            return candidate
    return path
