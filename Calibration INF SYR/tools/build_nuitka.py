"""สร้าง exe ด้วย Nuitka (ดู docs/build-nuitka.md) — ค่าเริ่มต้นแค่พิมพ์คำสั่ง ไม่สร้าง

    python tools/build_nuitka.py              พิมพ์คำสั่ง (standalone = โฟลเดอร์ เปิดเร็วที่สุด)
    python tools/build_nuitka.py --onefile    พิมพ์คำสั่งแบบไฟล์เดียว
    python tools/build_nuitka.py --run        สร้างจริง (ต้องติดตั้ง nuitka + MSVC ก่อน)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.constants import APP_NAME, APP_VERSION  # noqa: E402


def command(onefile: bool) -> list[str]:
    args = [
        sys.executable, "-m", "nuitka",
        "--onefile" if onefile else "--standalone",
        "--enable-plugin=pyside6",
        "--include-package=pyqtgraph",
        "--include-data-dir=ui/assets=ui/assets",
        "--nofollow-import-to=tests,tools,_legacy,tkinter",
        "--windows-console-mode=disable",
        f"--output-filename={APP_NAME}.exe",
        "--output-dir=build",
        f"--product-name={APP_NAME}",
        f"--file-version={APP_VERSION}",
        f"--product-version={APP_VERSION}",
        "--assume-yes-for-downloads",
        "main.py",
    ]
    icon = ROOT / "ui" / "assets" / "deltam.ico"
    if icon.is_file():
        args.insert(-1, f"--windows-icon-from-ico={icon.relative_to(ROOT)}")
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--onefile", action="store_true", help="ไฟล์เดียว (เปิดช้ากว่า standalone)")
    parser.add_argument("--run", action="store_true", help="สร้างจริง")
    options = parser.parse_args()
    args = command(options.onefile)
    print(" ".join(args))
    if not options.run:
        return 0
    return subprocess.call(args, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
