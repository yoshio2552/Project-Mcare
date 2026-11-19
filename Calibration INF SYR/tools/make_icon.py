"""สร้างไอคอนโปรแกรมจาก ui/assets/deltam.svg -> deltam.ico (16–256 px หลายขนาดในไฟล์เดียว) + deltam.png (256 px)

    python tools/make_icon.py

.ico ใช้กับ exe ของ Nuitka (tools/build_nuitka.py --windows-icon-from-ico) · ตอนรัน python ใช้ svg ผ่าน ui/window_chrome.py
เปลี่ยนโลโก้: แก้ deltam.svg แล้วรันใหม่
"""
from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "ui" / "assets"
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def render_png(size: int) -> bytes:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    renderer = QSvgRenderer(str(ASSETS / "deltam.svg"))
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def write_ico(path: Path, images: list[tuple[int, bytes]]) -> None:
    """ไฟล์ .ico ที่เก็บ PNG ทุกขนาด (Windows Vista ขึ้นไปอ่านได้)"""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, png in images:
        side = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(png), offset + len(blobs))
        blobs += png
    path.write_bytes(header + entries + blobs)


def main() -> None:
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])   # noqa: F841 — QImage/QSvg ต้องมี app
    images = [(size, render_png(size)) for size in SIZES]
    write_ico(ASSETS / "deltam.ico", images)
    (ASSETS / "deltam.png").write_bytes(images[-1][1])
    print(ASSETS / "deltam.ico", ASSETS / "deltam.png")


if __name__ == "__main__":
    main()
